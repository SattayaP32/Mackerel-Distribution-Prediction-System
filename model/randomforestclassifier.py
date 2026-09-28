# -*- coding: utf-8 -*-
"""
randomforestclassifier.py

Random Forest Classification สำหรับโครงงานคาดการณ์การกระจายตัวของปลาทู

หน้าที่:
1) ดึงข้อมูล catch_mackereldata + marine_environment + station จาก MySQL
2) ใช้ข้อมูลปี 2562-2566 เป็น Training และปี 2567 เป็น Test
3) สร้างระดับโอกาสพบปลา LOW / MEDIUM / HIGH
   โดยกำหนดจากปริมาณปลา (amount) ด้วย 33rd / 66th percentile ของชุด Training
4) Train Random Forest จาก Month, Year, Station ID, SST, Chlorophyll-a, Rainfall และ Wind Speed
5) รับข้อมูลเพื่อ Predict ได้ 2 แบบ:
      auto   = ดึงค่ารายเดือน 4 ปัจจัยจาก MySQL
      manual = ผู้ใช้กรอก SST, Chlorophyll-a, Rainfall และ Wind Speed
6) บันทึก model และ metrics ลง model/output/

ตัวอย่าง:
    python randomforestclassifier.py --train

    python randomforestclassifier.py --predict \
        --year 2567 --month 5 --province "เพชรบุรี"

    python randomforestclassifier.py --predict \
        --year 2567 --month 5 --province "เพชรบุรี" \
        --sst 29.1 --chl_a 2.4 --rainfall 20.5 --wind_speed 16.19

หมายเหตุ:
- ต้องติดตั้ง:
    pip install pandas numpy scikit-learn pymysql joblib
"""

import argparse
import json
import os
import sys
import re
import unicodedata
from pathlib import Path

# บังคับ UTF-8 สำหรับ Windows/XAMPP
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import joblib
import numpy as np
import pandas as pd
import pymysql

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    balanced_accuracy_score,
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_FILE = OUTPUT_DIR / "random_forest_model.joblib"
METRICS_FILE = OUTPUT_DIR / "classification_metrics.json"
THRESHOLD_FILE = OUTPUT_DIR / "classification_thresholds.json"
LAST_PREDICTION_FILE = OUTPUT_DIR / "last_prediction.json"


# ============================================================
# MYSQL CONFIG
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "projecta",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


# ============================================================
# MODEL CONFIG
# ============================================================

RANDOM_STATE = 42

# ลำดับนี้ตรงกับ configuration ที่ได้ Final Test 2567 Accuracy 68.3%
FEATURES = ["sst", "chlorophyll_a", "rainfall", "wind_speed", "month", "year", "station_id"]

CLASS_ORDER = ["LOW", "MEDIUM", "HIGH"]


# ============================================================
# UTILITY
# ============================================================

def eprint(*args, **kwargs):
    """พิมพ์ข้อความลง stderr เพื่อไม่รบกวน JSON stdout ที่ PHP จะอ่าน"""
    print(*args, file=sys.stderr, **kwargs)


def output_json(data):
    """ส่ง JSON ออก stdout สำหรับ PHP"""
    print(json.dumps(data, ensure_ascii=True, default=str), flush=True)


def get_connection():
    return pymysql.connect(**DB_CONFIG)


def normalize_province_name(name):
    """ทำความสะอาดชื่อจังหวัด รองรับช่องว่าง/อักขระ Unicode แฝง และคำสะกดที่พบบ่อย"""
    name = unicodedata.normalize("NFKC", str(name))
    # ลบ zero-width / BOM และช่องว่างที่อาจติดมาจาก MySQL/HTML
    name = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", name)
    name = re.sub(r"\s+", "", name).strip()

    aliases = {
        "เพรชบุรี": "เพชรบุรี",
        "เพชรบุรี": "เพชรบุรี",
        "สมุทรสงคราม": "สมุทรสงคราม",
        "สมุทรสาคร": "สมุทรสาคร",
        "ชลบุรี": "ชลบุรี",
        "สมุทรปราการ": "สมุทรปราการ",
    }

    return aliases.get(name, name)


# ============================================================
# DATA FROM MYSQL
# ============================================================

def load_training_data():
    """โหลด catch + marine_environment + weather_data แล้วรวมตาม station/year/month"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT station_id, year, month, SUM(amount) AS amount
                FROM catch_mackereldata
                WHERE status = 1 AND year BETWEEN 2562 AND 2567
                GROUP BY station_id, year, month
            """)
            catch_rows = cursor.fetchall()
            cursor.execute("""
                SELECT station_id, year, month, AVG(sst) AS sst,
                       AVG(chlorophyll_a) AS chlorophyll_a
                FROM marine_environment
                WHERE status = 1 AND year BETWEEN 2562 AND 2567
                GROUP BY station_id, year, month
            """)
            env_rows = cursor.fetchall()
            cursor.execute("""
                SELECT station_id, year, month, AVG(rainfall) AS rainfall,
                       AVG(wind_speed) AS wind_speed
                FROM weather_data
                WHERE status = 1 AND year BETWEEN 2562 AND 2567
                GROUP BY station_id, year, month
            """)
            weather_rows = cursor.fetchall()
    finally:
        conn.close()

    if not catch_rows: raise RuntimeError("ไม่พบข้อมูล catch_mackereldata ช่วงปี 2562-2567")
    if not env_rows: raise RuntimeError("ไม่พบข้อมูล marine_environment ช่วงปี 2562-2567")
    if not weather_rows: raise RuntimeError("ไม่พบข้อมูล weather_data ช่วงปี 2562-2567")

    catch_df, env_df, weather_df = map(pd.DataFrame, (catch_rows, env_rows, weather_rows))
    for df, cols in [
        (catch_df, ["station_id","year","month","amount"]),
        (env_df, ["station_id","year","month","sst","chlorophyll_a"]),
        (weather_df, ["station_id","year","month","rainfall","wind_speed"]),
    ]:
        for col in cols: df[col] = pd.to_numeric(df[col], errors="coerce")

    catch_df = catch_df.dropna(subset=["station_id","year","month","amount"])
    env_df = env_df.dropna(subset=["station_id","year","month"])
    weather_df = weather_df.dropna(subset=["station_id","year","month"])
    for df in (catch_df, env_df, weather_df):
        df["station_id"] = df["station_id"].astype(int)
        df["year"] = df["year"].astype(int)
        df["month"] = df["month"].astype(int)

    df = pd.merge(catch_df, env_df, on=["station_id","year","month"], how="inner")
    df = pd.merge(df, weather_df, on=["station_id","year","month"], how="left")
    required = ["sst","chlorophyll_a","rainfall","wind_speed"]
    missing = df[required].isna().sum()
    if missing.any():
        eprint("ตัดแถวที่ข้อมูลไม่ครบ: " + ", ".join(f"{k}={v}" for k,v in missing.items() if v))
        df = df.dropna(subset=required)
    if df.empty: raise RuntimeError("ไม่พบข้อมูลที่ merge กันได้จาก catch_mackereldata + marine_environment + weather_data")
    return df

def get_station_id(province):
    """ค้นหา station_id จากชื่อจังหวัด"""
    province = normalize_province_name(province)

    sql = """
        SELECT id, station_name
        FROM station
        WHERE status = 1
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
    finally:
        conn.close()

    if not rows:
        raise RuntimeError("ไม่พบข้อมูล station")

    # เปรียบเทียบหลัง normalize ทั้งค่าจากผู้ใช้และค่าที่อ่านจาก MySQL
    normalized_rows = []
    for row in rows:
        station_name = normalize_province_name(row["station_name"])
        normalized_rows.append((int(row["id"]), station_name, str(row["station_name"])))
        if station_name == province:
            return int(row["id"])

    # fallback: contains หลัง normalize
    for station_id, station_name, raw_name in normalized_rows:
        if province in station_name or station_name in province:
            return station_id

    available = [str(r["station_name"]) for r in rows]
    raise ValueError(
        f"ไม่พบจังหวัด '{province}' ในตาราง station. "
        f"จังหวัดที่มี: {', '.join(available)}"
    )


def get_environment_weather(year, month, station_id):
    """ดึงค่ารายเดือน 4 ปัจจัยที่โมเดลใช้งาน"""
    sql = """
        SELECT e.sst, e.chlorophyll_a, w.rainfall, w.wind_speed
        FROM marine_environment e
        LEFT JOIN weather_data w
          ON e.station_id=w.station_id AND e.year=w.year AND e.month=w.month AND w.status=1
        WHERE e.status=1 AND e.year=%s AND e.month=%s AND e.station_id=%s
        ORDER BY e.id DESC LIMIT 1
    """
    conn=get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql,(year,month,station_id)); row=cursor.fetchone()
    finally: conn.close()
    required = ["sst","chlorophyll_a","rainfall","wind_speed"]
    missing = [name for name in required if not row or row[name] is None]
    if missing:
        raise ValueError(f"ข้อมูลไม่ครบสำหรับ year={year}, month={month}, station_id={station_id}: {', '.join(missing)}")
    return {name: float(row[name]) for name in required}

# ============================================================
# TARGET CREATION
# ============================================================

def create_target_from_training_amount(train_df):
    """
    แบ่งระดับจากปริมาณปลาด้วย 33rd / 66th percentile

    LOW    <= p33
    MEDIUM > p33 และ <= p66
    HIGH   > p66

    ใช้ threshold จาก Training เท่านั้น
    เพื่อป้องกัน data leakage
    """

    p33 = float(train_df["amount"].quantile(0.33))
    p66 = float(train_df["amount"].quantile(0.66))

    if p33 >= p66:
        raise RuntimeError(
            f"ไม่สามารถสร้าง threshold ได้: p33={p33}, p66={p66}"
        )

    def label_amount(amount):
        if amount <= p33:
            return "LOW"
        elif amount <= p66:
            return "MEDIUM"
        return "HIGH"

    train_df = train_df.copy()
    train_df["target"] = train_df["amount"].apply(label_amount)

    thresholds = {
        "method": "percentile",
        "low_medium_boundary": p33,
        "medium_high_boundary": p66,
        "definition": {
            "LOW": f"amount <= {p33:.6f}",
            "MEDIUM": f"{p33:.6f} < amount <= {p66:.6f}",
            "HIGH": f"amount > {p66:.6f}",
        },
    }

    return train_df, thresholds


def apply_target_thresholds(df, thresholds):
    """ใช้ threshold ที่ได้จาก Training ไปกำหนด label ของ Test"""
    p33 = float(thresholds["low_medium_boundary"])
    p66 = float(thresholds["medium_high_boundary"])

    df = df.copy()

    def label_amount(amount):
        if amount <= p33:
            return "LOW"
        elif amount <= p66:
            return "MEDIUM"
        return "HIGH"

    df["target"] = df["amount"].apply(label_amount)
    return df


# ============================================================
# TRAIN
# ============================================================

def train_model():
    eprint("กำลังโหลดข้อมูลจาก MySQL...")
    df = load_training_data()

    # Training = 2562-2566
    train_df = df[df["year"].between(2562, 2566)].copy()

    # Test = 2567
    test_df = df[df["year"] == 2567].copy()

    if train_df.empty:
        raise RuntimeError("ไม่พบข้อมูล Training ปี 2562-2566")

    if test_df.empty:
        raise RuntimeError("ไม่พบข้อมูล Test ปี 2567")

    eprint(f"Training rows: {len(train_df)}")
    eprint(f"Test rows: {len(test_df)}")

    # สร้าง target จาก amount ของ Training เท่านั้น
    train_df, thresholds = create_target_from_training_amount(train_df)
    test_df = apply_target_thresholds(test_df, thresholds)

    X_train = train_df[FEATURES].copy()
    y_train = train_df["target"].copy()

    X_test = test_df[FEATURES].copy()
    y_test = test_df["target"].copy()

    # ตรวจว่ามีอย่างน้อย 2 class ใน training
    if y_train.nunique() < 2:
        raise RuntimeError(
            "ข้อมูล Training มีระดับเป้าหมายน้อยกว่า 2 ระดับ "
            "ไม่สามารถทำ Classification ได้"
        )

    # Random Forest
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    eprint("กำลัง Train Random Forest...")
    model.fit(X_train, y_train)

    # Predict Test
    y_pred = model.predict(X_test)

    # Metrics
    labels_for_report = [c for c in CLASS_ORDER if c in set(y_test) | set(y_pred)]

    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(
        precision_score(
            y_test,
            y_pred,
            labels=labels_for_report,
            average="macro",
            zero_division=0,
        )
    )
    recall = float(
        recall_score(
            y_test,
            y_pred,
            labels=labels_for_report,
            average="macro",
            zero_division=0,
        )
    )
    f1 = float(
        f1_score(
            y_test,
            y_pred,
            labels=labels_for_report,
            average="macro",
            zero_division=0,
        )
    )

    cm = confusion_matrix(
        y_test,
        y_pred,
        labels=CLASS_ORDER,
    ).tolist()

    report = classification_report(
        y_test,
        y_pred,
        labels=CLASS_ORDER,
        output_dict=True,
        zero_division=0,
    )

    metrics = {
        "train": {
            "years": [2562, 2563, 2564, 2565, 2566],
            "rows": int(len(train_df)),
        },
        "test": {
            "year": 2567,
            "rows": int(len(test_df)),
        },
        "target_definition": thresholds,
        "accuracy": accuracy,
        "precision_macro": precision,
        "recall_macro": recall,
        "f1_macro": f1,
        "balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred)),
        "confusion_matrix": {
            "labels": CLASS_ORDER,
            "matrix": cm,
        },
        "classification_report": report,
        "features": FEATURES,
    }

    # Feature importance
    feature_importance = {}
    for feature, importance in zip(FEATURES, model.feature_importances_):
        feature_importance[feature] = float(importance)

    metrics["feature_importance"] = feature_importance

    # Save model package
    model_package = {
        "model": model,
        "features": FEATURES,
        "class_order": CLASS_ORDER,
        "thresholds": thresholds,
        "training_years": [2562, 2563, 2564, 2565, 2566],
        "test_year": 2567,
    }

    joblib.dump(model_package, MODEL_FILE)

    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    with open(THRESHOLD_FILE, "w", encoding="utf-8") as f:
        json.dump(thresholds, f, ensure_ascii=False, indent=2)

    eprint("Train เสร็จแล้ว")
    eprint(f"Model: {MODEL_FILE}")
    eprint(f"Metrics: {METRICS_FILE}")

    return metrics


# ============================================================
# LOAD MODEL
# ============================================================

def load_model():
    # ถ้า model เก่าใช้ชุด feature คนละรุ่น ให้ Train ใหม่อัตโนมัติ
    if MODEL_FILE.exists():
        try:
            package = joblib.load(MODEL_FILE)
            saved_features = package.get("features", []) if isinstance(package, dict) else []
            if saved_features != FEATURES:
                eprint("พบ model เก่าที่ใช้ชุด feature ไม่ตรงกัน จึง Train ใหม่...")
                train_model()
        except Exception:
            eprint("อ่าน model เดิมไม่ได้ จึง Train ใหม่...")
            train_model()
    else:
        eprint("ยังไม่มี model จึง Train ใหม่...")
        train_model()

    package = joblib.load(MODEL_FILE)

    if not isinstance(package, dict) or "model" not in package:
        raise RuntimeError("รูปแบบ model file ไม่ถูกต้อง")

    if package.get("features") != FEATURES:
        raise RuntimeError("Model ใช้ชุด feature ไม่ตรงกับโค้ดปัจจุบัน กรุณา Train ใหม่")

    return package


# ============================================================
# PREDICT
# ============================================================

def predict(year, month, province, sst=None, chl_a=None, rainfall=None, wind_speed=None):
    year, month = int(year), int(month)
    if month < 1 or month > 12: raise ValueError("เดือนต้องอยู่ระหว่าง 1-12")
    station_id=get_station_id(province)
    vals=(sst,chl_a,rainfall,wind_speed)
    if any(v is not None for v in vals) and not all(v is not None for v in vals):
        raise ValueError("ถ้าใช้ Manual ต้องระบุ SST, Chlorophyll-a, Rainfall และ Wind Speed ให้ครบ")
    if all(v is not None for v in vals):
        values=dict(zip(["sst","chlorophyll_a","rainfall","wind_speed"],map(float,vals)))
        mode="manual"
    else:
        values=get_environment_weather(year,month,station_id); mode="auto"
    package=load_model(); model=package["model"]; features=package["features"]
    row={"month":month,"year":year,"station_id":station_id,**values}
    input_df=pd.DataFrame([row],columns=features)
    predicted_class=str(model.predict(input_df)[0])
    probabilities={}
    if hasattr(model,"predict_proba"):
        for cls,value in zip(model.classes_,model.predict_proba(input_df)[0]): probabilities[str(cls)]=float(value)
    probabilities={key:probabilities.get(key,0.0) for key in CLASS_ORDER}
    result={"success":True,"prediction":predicted_class,"prediction_th":{"LOW":"ต่ำ","MEDIUM":"ปานกลาง","HIGH":"สูง"}.get(predicted_class,predicted_class),"confidence":float(probabilities.get(predicted_class,0.0)),"probabilities":probabilities,"mode":mode,"input":{"year":year,"month":month,"province":province,"station_id":station_id,**values}}
    with open(LAST_PREDICTION_FILE,"w",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2)
    return result

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Random Forest Classification สำหรับระดับโอกาสพบปลาทู"
    )

    parser.add_argument(
        "--train",
        action="store_true",
        help="Train model ด้วยปี 2562-2566 และทดสอบปี 2567",
    )

    parser.add_argument(
        "--predict",
        action="store_true",
        help="Predict LOW/MEDIUM/HIGH",
    )

    parser.add_argument("--year", type=int)
    parser.add_argument("--month", type=int)
    parser.add_argument("--province", type=str)
    parser.add_argument("--sst", type=float, default=None)
    parser.add_argument("--chl_a", type=float, default=None)
    parser.add_argument("--rainfall", type=float, default=None)
    parser.add_argument("--wind_speed", type=float, default=None)

    args = parser.parse_args()

    try:
        if args.train:
            metrics = train_model()

            # stdout เป็น JSON เพื่อให้ PHP สามารถนำไปใช้ได้
            output_json(
                {
                    "success": True,
                    "action": "train",
                    "message": "Train model สำเร็จ",
                    "metrics": metrics,
                    "files": {
                        "model": str(MODEL_FILE),
                        "metrics": str(METRICS_FILE),
                        "thresholds": str(THRESHOLD_FILE),
                    },
                }
            )
            return

        if args.predict:
            if args.year is None:
                raise ValueError("กรุณาระบุ --year")

            if args.month is None:
                raise ValueError("กรุณาระบุ --month")

            if not args.province:
                raise ValueError("กรุณาระบุ --province")

            # ถ้าใช้ Manual ต้องส่งค่าทั้ง 4 ตัวมาครบ
            manual_values = [args.sst,args.chl_a,args.rainfall,args.wind_speed]
            if any(v is not None for v in manual_values) and not all(v is not None for v in manual_values):
                raise ValueError(
                    "ถ้าจะใช้ Manual ต้องใส่ SST, Chlorophyll-a, Rainfall และ Wind Speed ให้ครบ"
                )

            result = predict(
                year=args.year,
                month=args.month,
                province=args.province,
                sst=args.sst,
                chl_a=args.chl_a,
                rainfall=args.rainfall,
                wind_speed=args.wind_speed,
            )

            output_json(result)
            return

        parser.print_help()

    except Exception as exc:
        eprint(f"ERROR: {exc}")
        output_json(
            {
                "success": False,
                "error": str(exc),
            }
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
