# -*- coding: utf-8 -*-
"""Linear Regression สำหรับคาดการณ์ปริมาณปลาทูจากฐานข้อมูล projecta."""


from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


# 1) ตั้งค่าหลัก
START_YEAR = 2562
REQUESTED_END_YEAR = 2569

# ปรับค่าได้: ช่วง decay ใช้ให้น้ำหนักข้อมูลปีใหม่มากกว่าปีเก่า decay < 1.00 ข้อมูลเก่ามีน้ำหนักลดลง,decay = 1.00 ข้อมูลทุกปีมีน้ำหนักเท่ากัน
DECAY_GRID = np.round(np.arange(0.70, 1.001, 0.05), 2)

# ปรับค่าได้: สัดส่วน Linear Regression เทียบกับค่าเฉลี่ยตามฤดูกาล ;ใกล้ 1 ข้าง regression
# 0.50 = ใช้ Regression 50% + Seasonal reference 50%
# Seasonal reference = ข้อมูลเฉลี่ยในเดือนเดียวกันและค่าสูงสุด
MODEL_WEIGHT_GRID = np.round(np.arange(0.50, 1.001, 0.025), 3)

# ปรับค่าได้: Alpha จำกัดค่าคาดการณ์ไม่ให้สูงเกิน seasonal maximum มากเกินไป ;1.00 = 100% SM
CAP_GRID = [None, 1.25, 1.50, 2.00, 3.00]

# ปรับค่าได้: ความแรงของ Bias correction
# 0.0 = ปิด Bias, 1.0 = ใช้ค่าชดเชยจาก median residual เต็มค่า
BIAS_STRENGTH = 1.0

# ปรับค่าได้: จำกัด Bias ไม่ให้เกินสัดส่วนนี้ของค่ากลางปริมาณจับ
# ใช้เพื่อป้องกัน Bias ที่สูงผิดปกติจาก outlier
BIAS_MAX_MEDIAN_RATIO = 0.90

# ปรับค่าได้: ให้น้ำหนัก Validation ปีใหม่มากขึ้นรายจังหวัด
# 1.0 = Walk-forward ปกติ
# >1.0 = ให้ Validation ปีล่าสุดมีอิทธิพลต่อการเลือก Parameter มากขึ้น
VALIDATION_RECENCY_BY_STATION = {
    1: 1.30,  # เพชรบุรี
    2: 1.00,  # สมุทรสงคราม
    3: 6.00,  # สมุทรสาคร
    4: 1.00,  # ชลบุรี
    5: 12.00, # สมุทรปราการ
}

# ปรับค่าได้: ระดับความแรงของ Bias ที่ทดลองเฉพาะจังหวัดที่ใช้ Recency tuning
BIAS_STRENGTH_GRID_BY_STATION = {
    1: [0.00, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50],
    3: [0.00, 0.50, 1.00],
    5: [0.00, 0.25, 0.50, 0.75, 1.00, 1.25, 1.50],
}

BASE_FEATURES = [
    "sst",
    "chlorophyll_a",
    "rainfall",
    "wind_speed",
    "air_temperature",
    "wind_dir_sin",
    "wind_dir_cos",
    "year_index",
]

SSS_FEATURES = [
    "sst",
    "chlorophyll_a",
    "sss",
    "rainfall",
    "wind_speed",
    "air_temperature",
    "wind_dir_sin",
    "wind_dir_cos",
    "year_index",
]

# ปรับค่าได้: เปิด/ปิด SSS 
USE_SSS_BY_STATION = {
    1: True,   # เพชรบุรี
    2: True,   # สมุทรสงคราม
    3: True,   # สมุทรสาคร
    4: True,  # ชลบุรี f
    5: True,  # สมุทรปราการ f
}

# ปรับค่าได้: เปิด/ปิด Sea Level Pressure (SLP) รายจังหวัด เปิดเพื่อให้ผลที่ดีกว่า
USE_SEA_LEVEL_PRESSURE_BY_STATION = {
    1: True,   # เพชรบุรี
    2: False,  # สมุทรสงคราม f
    3: False,  # สมุทรสาคร f
    4: True,   # ชลบุรี
    5: False,   # สมุทรปราการ
}

# Monsoon เป็นตัวแปรหมวดหมู่ (Northeast / Southwest / Transition) ไม่ได้ใช้เพราะมีข้อมูลเดือน Month One-Hot(เรียนรู้ตามฤดูกาลอยู่แล้ว)
USE_MONSOON_BY_STATION = {1: False, 2: False, 3: False, 4: False, 5: False}


OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MONTH_NAMES_TH = {
    1: "มกราคม",
    2: "กุมภาพันธ์",
    3: "มีนาคม",
    4: "เมษายน",
    5: "พฤษภาคม",
    6: "มิถุนายน",
    7: "กรกฎาคม",
    8: "สิงหาคม",
    9: "กันยายน",
    10: "ตุลาคม",
    11: "พฤศจิกายน",
    12: "ธันวาคม",
}


# 2) ฟังก์ชันพื้นฐาน
def configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def send_json(payload: Dict[str, Any]) -> None:
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
        )
    )


# 3) อ่านข้อมูลจากฐานข้อมูล
def connect_database():
    try:
        import mysql.connector
    except ImportError as exc:
        raise RuntimeError(
            "ไม่พบ mysql-connector-python กรุณารัน: "
            "pip install mysql-connector-python"
        ) from exc

    return mysql.connector.connect(
        host=os.getenv("PROJECTA_DB_HOST", "127.0.0.1"),
        database=os.getenv("PROJECTA_DB_NAME", "projecta"),
        user=os.getenv("PROJECTA_DB_USER", "root"),
        password=os.getenv("PROJECTA_DB_PASSWORD", ""),
        port=int(os.getenv("PROJECTA_DB_PORT", "3306")),
        charset="utf8mb4",
        use_unicode=True,
    )


def query_df(conn, sql: str, params: Sequence[Any] = ()) -> pd.DataFrame:
    cur = conn.cursor()
    try:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        columns = [x[0] for x in cur.description]
        return pd.DataFrame(rows, columns=columns)
    finally:
        cur.close()


def load_database() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    conn = connect_database()
    try:
        stations = query_df(
            conn,
            """
            SELECT id AS station_id, station_name
            FROM station
            WHERE status = 1
              AND id BETWEEN 1 AND 5
            ORDER BY id
            """,
        )

        catch = query_df(
            conn,
            """
            SELECT
                station_id,
                year,
                month,
                SUM(amount) AS catch
            FROM catch_mackereldata
            WHERE status = 1
              AND station_id BETWEEN 1 AND 5
              AND year BETWEEN %s AND %s
            GROUP BY station_id, year, month
            ORDER BY station_id, year, month
            """,
            [START_YEAR, REQUESTED_END_YEAR],
        )

        env = query_df(
            conn,
            """
            SELECT
                station_id,
                year,
                month,
                AVG(sst) AS sst,
                AVG(chlorophyll_a) AS chlorophyll_a,
                AVG(sss) AS sss
            FROM marine_environment
            WHERE status = 1
              AND station_id BETWEEN 1 AND 5
              AND year BETWEEN %s AND %s
            GROUP BY station_id, year, month
            ORDER BY station_id, year, month
            """,
            [START_YEAR, REQUESTED_END_YEAR],
        )

        weather = query_df(
            conn,
            """
            SELECT
                station_id,
                year,
                month,
                AVG(rainfall) AS rainfall,
                AVG(wind_speed) AS wind_speed,
                AVG(sea_level_pressure) AS sea_level_pressure,
                AVG(air_temperature) AS air_temperature,
                AVG(wind_direction) AS wind_direction,
                MAX(monsoon) AS monsoon,
                MAX(season) AS season
            FROM weather_data
            WHERE status = 1
              AND station_id BETWEEN 1 AND 5
              AND year BETWEEN %s AND %s
            GROUP BY station_id, year, month
            ORDER BY station_id, year, month
            """,
            [START_YEAR, REQUESTED_END_YEAR],
        )
    finally:
        conn.close()

    if stations.empty:
        raise ValueError("ไม่พบข้อมูล station")
    if catch.empty:
        raise ValueError("ไม่พบข้อมูล catch_mackereldata")
    if env.empty:
        raise ValueError("ไม่พบข้อมูล marine_environment")
    if weather.empty:
        raise ValueError("ไม่พบข้อมูล weather_data")

    stations["station_id"] = pd.to_numeric(
        stations["station_id"], errors="raise"
    ).astype(int)
    stations["station_name"] = (
        stations["station_name"]
        .astype(str)
        .str.strip()
    )

    for frame, columns in [
        (catch, ["station_id", "year", "month", "catch"]),
        (env, ["station_id", "year", "month", "sst", "chlorophyll_a", "sss"]),
        (weather, [
            "station_id", "year", "month", "rainfall", "wind_speed",
            "sea_level_pressure", "air_temperature", "wind_direction"
        ]),
    ]:
        for column in columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    catch = catch.dropna(
        subset=["station_id", "year", "month", "catch"]
    ).copy()
    env = env.dropna(
        subset=["station_id", "year", "month", "sst", "chlorophyll_a", "sss"]
    ).copy()
    weather = weather.dropna(
        subset=[
            "station_id", "year", "month", "rainfall", "wind_speed",
            "sea_level_pressure", "air_temperature", "wind_direction", "monsoon"
        ]
    ).copy()

    for frame in [catch, env, weather]:
        frame[["station_id", "year", "month"]] = (
            frame[["station_id", "year", "month"]].astype(int)
        )

    catch["catch"] = catch["catch"].astype(float).clip(lower=0.0)
    env["sst"] = env["sst"].astype(float)
    env["chlorophyll_a"] = env["chlorophyll_a"].astype(float)
    env["sss"] = env["sss"].astype(float)
    weather["rainfall"] = weather["rainfall"].astype(float)
    weather["wind_speed"] = weather["wind_speed"].astype(float)
    weather["sea_level_pressure"] = weather["sea_level_pressure"].astype(float)
    weather["air_temperature"] = weather["air_temperature"].astype(float)
    weather["wind_direction"] = weather["wind_direction"].astype(float)
    weather["monsoon"] = weather["monsoon"].astype(str).str.strip()
    weather["season"] = weather["season"].astype(str)

    return stations, catch, env, weather


# 4) เตรียมและรวมข้อมูล
def station_for_province(stations: pd.DataFrame, province: str) -> Tuple[int, str]:
    province = str(province).strip()
    match = stations[stations["station_name"] == province]
    if match.empty:
        available = ", ".join(stations["station_name"].astype(str).tolist())
        raise ValueError(
            f"ไม่พบจังหวัด '{province}' ใน station; จังหวัดที่ใช้ได้: {available}"
        )
    row = match.iloc[0]
    return int(row["station_id"]), str(row["station_name"])


def common_feature_rows(env: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """รวมข้อมูลสิ่งแวดล้อม + อากาศ รวม SLP และ Monsoon สำหรับทดลองโมเดล"""
    feature_rows = env[
        ["station_id", "year", "month", "sst", "chlorophyll_a", "sss"]
    ].merge(
        weather[
            [
                "station_id",
                "year",
                "month",
                "rainfall",
                "wind_speed",
                "sea_level_pressure",
                "air_temperature",
                "wind_direction",
                "monsoon",
                "season",
            ]
        ],
        on=["station_id", "year", "month"],
        how="inner",
    )

    for column in [
        "sst",
        "chlorophyll_a",
        "sss",
        "rainfall",
        "wind_speed",
        "sea_level_pressure",
        "air_temperature",
        "wind_direction",
    ]:
        feature_rows = feature_rows[
            feature_rows[column].notna()
            & np.isfinite(feature_rows[column])
        ]

    feature_rows = feature_rows[
        (feature_rows["sst"] > 0)
        & (feature_rows["chlorophyll_a"] > 0)
        & (feature_rows["sss"] > 0)
        & (feature_rows["rainfall"] >= 0)
        & (feature_rows["wind_speed"] >= 0)
        & (feature_rows["sea_level_pressure"] > 0)
        & (feature_rows["air_temperature"] > 0)
        & (feature_rows["wind_direction"].between(0, 360))
        & feature_rows["monsoon"].notna()
    ].copy()

    feature_rows["monsoon"] = (
        feature_rows["monsoon"].astype(str).str.strip()
    )

    radians = np.deg2rad(
        feature_rows["wind_direction"].astype(float)
    )
    feature_rows["wind_dir_sin"] = np.sin(radians)
    feature_rows["wind_dir_cos"] = np.cos(radians)

    return feature_rows.drop_duplicates(
        ["station_id", "year", "month"]
    ).sort_values(["station_id", "year", "month"])


def choose_holdout_year(
    catch: pd.DataFrame,
    features: pd.DataFrame,
    station_count: int,
) -> int:
    catch_max_year = int(catch["year"].max())
    expected = station_count * 12

    counts = (
        features[features["year"] <= catch_max_year]
        .groupby("year")
        .size()
        .to_dict()
    )

    possible = [
        int(year)
        for year, count in counts.items()
        if int(year) >= START_YEAR + 2 and int(count) == expected
    ]

    if not possible:
        raise ValueError(
            "ไม่พบปีที่มี marine_environment และ weather_data ครบทุกจังหวัด/เดือน "
            "สำหรับใช้เป็น Holdout"
        )

    return max(possible)


def build_supervised_data(
    stations: pd.DataFrame,
    catch: pd.DataFrame,
    env: pd.DataFrame,
    weather: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    features = common_feature_rows(env, weather)
    label_end_year = int(catch["year"].max())

    data = features[
        features["year"].between(START_YEAR, label_end_year)
    ].merge(
        catch,
        on=["station_id", "year", "month"],
        how="left",
    )

    zero_filled = int(data["catch"].isna().sum())
    data["catch"] = data["catch"].fillna(0.0).clip(lower=0.0)
    data["year_index"] = data["year"] - START_YEAR

    data = data.merge(stations, on="station_id", how="left")
    data = data.sort_values(
        ["station_id", "year", "month"]
    ).reset_index(drop=True)

    holdout_year = choose_holdout_year(
        catch,
        features,
        len(stations),
    )

    summary = {
        "catch_min_year": int(catch["year"].min()),
        "catch_max_year": label_end_year,
        "environment_min_year": int(env["year"].min()),
        "environment_max_year": int(env["year"].max()),
        "sss_min": float(env["sss"].min()),
        "sss_max": float(env["sss"].max()),
        "sss_mean": float(env["sss"].mean()),
        "weather_min_year": int(weather["year"].min()),
        "weather_max_year": int(weather["year"].max()),
        "holdout_year": int(holdout_year),
        "training_feature_rows": int(len(data)),
        "zero_filled_catch_months": zero_filled,
        "future_feature_rows": int((features["year"] > label_end_year).sum()),
    }

    return data, features, summary


# 5) สร้างและประเมินโมเดล
def calculate_metrics(y_true, y_pred) -> Dict[str, float]:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    return {
        "mae": float(mean_absolute_error(y, p)),
        "rmse": float(mean_squared_error(y, p) ** 0.5),
        "r2": float(r2_score(y, p)),
    }


def calculate_nrmse_percent(y_true, rmse: float) -> float:
    """
    NRMSE (%) = RMSE / Mean(Actual) × 100

    ใช้สำหรับเปรียบเทียบความคลาดเคลื่อนข้ามจังหวัดที่มี Scale
    ของปริมาณปลาทูแตกต่างกันมาก
    """
    y = np.asarray(y_true, dtype=float)
    mean_actual = float(np.mean(y)) if len(y) else 0.0

    if not np.isfinite(mean_actual) or mean_actual <= 0:
        return float("nan")

    return float((float(rmse) / mean_actual) * 100.0)


def make_model(use_sss: bool, station_id: int) -> Pipeline:
    """
    สร้าง Linear Regression รายจังหวัด
    - SLP เลือกใช้ได้รายจังหวัด
    - Monsoon เข้ารหัสแบบ One-Hot และเลือกใช้ได้รายจังหวัด
    """
    feature_columns = list(
        SSS_FEATURES if use_sss else BASE_FEATURES
    )

    use_slp = bool(
        USE_SEA_LEVEL_PRESSURE_BY_STATION.get(
            int(station_id),
            False,
        )
    )
    use_monsoon = bool(
        USE_MONSOON_BY_STATION.get(
            int(station_id),
            False,
        )
    )

    if use_slp:
        feature_columns.append("sea_level_pressure")

    transformers = [
        ("numeric", "passthrough", feature_columns),
        (
            "month",
            OneHotEncoder(
                drop="first",
                handle_unknown="ignore",
            ),
            ["month"],
        ),
    ]

    if use_monsoon:
        transformers.append(
            (
                "monsoon",
                OneHotEncoder(
                    drop="first",
                    handle_unknown="ignore",
                ),
                ["monsoon"],
            )
        )

    preprocessor = ColumnTransformer(
        transformers
    )

    return Pipeline(
        [
            ("preprocessor", preprocessor),
            ("linear_regression", LinearRegression()),
        ]
    )


def fit_raw(
    train: pd.DataFrame,
    test: pd.DataFrame,
    decay: float,
    use_sss: bool,
) -> Tuple[np.ndarray, Pipeline]:
    station_id = int(train["station_id"].iloc[0])
    model = make_model(
        use_sss,
        station_id,
    )

    sample_weight = np.power(
        float(decay),
        train["year"].max() - train["year"].to_numpy(dtype=float),
    )

    model.fit(
        train,
        train["catch"],
        linear_regression__sample_weight=sample_weight,
    )

    prediction = np.maximum(model.predict(test), 0.0)
    return prediction, model


def seasonal_reference(
    train: pd.DataFrame,
    test: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray]:
    seasonal_mean: List[float] = []
    seasonal_max: List[float] = []

    for row in test.itertuples(index=False):
        values = train.loc[train["month"] == int(row.month), "catch"]
        if values.empty:
            values = train["catch"]
        seasonal_mean.append(float(values.mean()))
        seasonal_max.append(float(values.max()))

    return np.asarray(seasonal_mean), np.asarray(seasonal_max)


def apply_calibration(
    raw_prediction: np.ndarray,
    seasonal_mean: np.ndarray,
    seasonal_max: np.ndarray,
    model_weight: float,
    cap_multiplier,
) -> np.ndarray:
    prediction = (
        float(model_weight) * raw_prediction
        + (1.0 - float(model_weight)) * seasonal_mean
    )

    if cap_multiplier is not None:
        prediction = np.minimum(
            prediction,
            seasonal_max * float(cap_multiplier),
        )

    return np.maximum(prediction, 0.0)


def apply_bias_correction(
    prediction: np.ndarray,
    bias: float,
) -> np.ndarray:
    """ชดเชยค่าคาดการณ์ด้วย Bias ที่เรียนรู้จาก Walk-forward residual."""
    return np.maximum(
        np.asarray(prediction, dtype=float) + float(bias),
        0.0,
    )


def estimate_robust_bias(
    actual: Sequence[float],
    predicted: Sequence[float],
) -> Tuple[float, float]:
    """หา Bias แบบ robust โดยใช้ median residual เพื่อลดผลของ outlier."""
    y = np.asarray(actual, dtype=float)
    p = np.asarray(predicted, dtype=float)

    residual = y - p
    raw_bias = float(np.median(residual))

    # จำกัดขนาด Bias จากข้อมูล validation เท่านั้น จึงไม่ใช้ข้อมูล Holdout
    catch_median = float(np.median(np.abs(y))) if len(y) else 0.0
    bias_limit = max(1.0, catch_median * float(BIAS_MAX_MEDIAN_RATIO))

    bias = float(np.clip(
        raw_bias * float(BIAS_STRENGTH),
        -bias_limit,
        bias_limit,
    ))

    return bias, raw_bias


# 6) ปรับ Weight / Bias แบบ Walk-forward
def tuning_years_for_holdout(holdout_year: int) -> List[int]:
    years = list(
        range(
            max(START_YEAR + 2, int(holdout_year) - 3),
            int(holdout_year),
        )
    )
    if not years:
        raise ValueError("มีจำนวนปีไม่เพียงพอสำหรับ Walk-forward validation")
    return years


def tune_station_standard(
    station_data: pd.DataFrame,
    tuning_years: List[int],
) -> Dict[str, Any]:
    station_id = int(station_data["station_id"].iloc[0])
    use_sss = bool(USE_SSS_BY_STATION.get(station_id, True))

    decay_results = []
    cached: Dict[float, Dict[int, Tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]]] = {}

    for decay in DECAY_GRID:
        actual: List[float] = []
        predicted: List[float] = []
        cached[float(decay)] = {}

        for validation_year in tuning_years:
            train = station_data[station_data["year"] < validation_year]
            test = station_data[station_data["year"] == validation_year]

            if train.empty or test.empty:
                continue

            raw, _ = fit_raw(train, test, float(decay), use_sss)
            seasonal_mean, seasonal_max = seasonal_reference(train, test)

            cached[float(decay)][validation_year] = (
                test,
                raw,
                seasonal_mean,
                seasonal_max,
            )

            actual.extend(test["catch"].tolist())
            predicted.extend(raw.tolist())

        if not actual:
            continue

        result = calculate_metrics(actual, predicted)
        decay_results.append({"decay": float(decay), **result})

    if not decay_results:
        raise ValueError("ไม่สามารถทำ Walk-forward validation ได้")

    decay_results.sort(key=lambda x: (x["rmse"], x["mae"]))
    best_decay = float(decay_results[0]["decay"])

    candidates = []

    for model_weight in MODEL_WEIGHT_GRID:
        for cap_multiplier in CAP_GRID:
            actual: List[float] = []
            predicted: List[float] = []

            for validation_year in tuning_years:
                if validation_year not in cached[best_decay]:
                    continue

                test, raw, seasonal_mean, seasonal_max = cached[best_decay][validation_year]
                pred = apply_calibration(
                    raw,
                    seasonal_mean,
                    seasonal_max,
                    float(model_weight),
                    cap_multiplier,
                )

                actual.extend(test["catch"].tolist())
                predicted.extend(pred.tolist())

            if not actual:
                continue

            result = calculate_metrics(actual, predicted)
            candidates.append(
                {
                    "decay": best_decay,
                    "model_weight": float(model_weight),
                    "seasonal_weight": 1.0 - float(model_weight),
                    "cap_multiplier": cap_multiplier,
                    **result,
                }
            )

    if not candidates:
        raise ValueError("ไม่สามารถเลือก calibration ได้")

    # เลือก Weight/Cap จาก Walk-forward validation โดยไม่แตะ Holdout year
    candidates.sort(key=lambda x: (x["rmse"], x["mae"]))
    best = dict(candidates[0])

    # หลังเลือก Weight แล้ว คำนวณ Bias จาก residual ของ validation ทั้งหมด
    # ใช้ median แทน mean เพราะข้อมูลปริมาณจับมี outlier ค่อนข้างมาก
    bias_actual: List[float] = []
    bias_predicted: List[float] = []

    for validation_year in tuning_years:
        if validation_year not in cached[best_decay]:
            continue

        test, raw, seasonal_mean, seasonal_max = cached[best_decay][validation_year]
        pred = apply_calibration(
            raw,
            seasonal_mean,
            seasonal_max,
            best["model_weight"],
            best["cap_multiplier"],
        )

        bias_actual.extend(test["catch"].tolist())
        bias_predicted.extend(pred.tolist())

    bias, raw_bias = estimate_robust_bias(
        bias_actual,
        bias_predicted,
    )

    best["bias"] = float(bias)
    best["raw_bias"] = float(raw_bias)
    best["bias_strength"] = float(BIAS_STRENGTH)
    best["bias_method"] = "median_walk_forward_residual"
    best["use_sss"] = bool(use_sss)
    best["feature_mode"] = "with_sss" if use_sss else "without_sss"

    return best



def calculate_weighted_metrics(
    y_true: Sequence[float],
    y_pred: Sequence[float],
    sample_weight: Sequence[float],
) -> Dict[str, float]:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(y_pred, dtype=float)
    w = np.asarray(sample_weight, dtype=float)

    if len(y) == 0 or len(y) != len(p) or len(y) != len(w):
        raise ValueError("ข้อมูลสำหรับ Weighted metrics ไม่ถูกต้อง")

    error = y - p
    mae = float(np.average(np.abs(error), weights=w))
    rmse = float(np.sqrt(np.average(error ** 2, weights=w)))

    weighted_mean = float(np.average(y, weights=w))
    ss_res = float(np.sum(w * (y - p) ** 2))
    ss_tot = float(np.sum(w * (y - weighted_mean) ** 2))
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else float("nan")

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
    }


def tune_station_recency(
    station_data: pd.DataFrame,
    tuning_years: List[int],
    recency_factor: float,
) -> Dict[str, Any]:
    """
    Tune Decay + Weight + Alpha + Bias พร้อมกัน
    โดยให้น้ำหนัก Validation ปีล่าสุดมากขึ้น
    """
    station_id = int(station_data["station_id"].iloc[0])
    use_sss = bool(USE_SSS_BY_STATION.get(station_id, True))

    bias_strength_grid = BIAS_STRENGTH_GRID_BY_STATION.get(
        station_id,
        [0.0, 0.5, 1.0],
    )

    cached = {}

    for decay in DECAY_GRID:
        decay_value = float(decay)
        cached[decay_value] = {}

        for validation_year in tuning_years:
            train = station_data[station_data["year"] < validation_year]
            test = station_data[station_data["year"] == validation_year]

            if train.empty or test.empty:
                continue

            raw, _ = fit_raw(
                train,
                test,
                decay_value,
                use_sss,
            )

            seasonal_mean, seasonal_max = seasonal_reference(
                train,
                test,
            )

            cached[decay_value][validation_year] = (
                test,
                raw,
                seasonal_mean,
                seasonal_max,
            )

    best = None

    for decay in DECAY_GRID:
        decay_value = float(decay)

        for model_weight in MODEL_WEIGHT_GRID:
            weight_value = float(model_weight)

            for cap_multiplier in CAP_GRID:
                actual = []
                predicted = []
                validation_weights = []

                for year_index, validation_year in enumerate(tuning_years):
                    if validation_year not in cached[decay_value]:
                        continue

                    test, raw, seasonal_mean, seasonal_max = (
                        cached[decay_value][validation_year]
                    )

                    pred = apply_calibration(
                        raw,
                        seasonal_mean,
                        seasonal_max,
                        weight_value,
                        cap_multiplier,
                    )

                    actual.extend(test["catch"].tolist())
                    predicted.extend(pred.tolist())

                    year_weight = (
                        float(recency_factor)
                        ** int(year_index)
                    )

                    validation_weights.extend(
                        [year_weight] * len(test)
                    )

                if not actual:
                    continue

                y = np.asarray(actual, dtype=float)
                p = np.asarray(predicted, dtype=float)

                residual = y - p
                raw_bias = float(np.median(residual))

                catch_median = (
                    float(np.median(np.abs(y)))
                    if len(y)
                    else 0.0
                )

                bias_limit = max(
                    1.0,
                    catch_median * float(BIAS_MAX_MEDIAN_RATIO),
                )

                for bias_strength in bias_strength_grid:
                    bias = float(
                        np.clip(
                            raw_bias * float(bias_strength),
                            -bias_limit,
                            bias_limit,
                        )
                    )

                    calibrated = np.maximum(
                        p + bias,
                        0.0,
                    )

                    result = calculate_weighted_metrics(
                        y,
                        calibrated,
                        validation_weights,
                    )

                    candidate = {
                        "decay": decay_value,
                        "model_weight": weight_value,
                        "seasonal_weight": 1.0 - weight_value,
                        "cap_multiplier": cap_multiplier,
                        "bias": bias,
                        "raw_bias": raw_bias,
                        "bias_strength": float(bias_strength),
                        "bias_method": "median_walk_forward_residual_recency_weighted",
                        "validation_recency_factor": float(recency_factor),
                        "use_sss": bool(use_sss),
                        "feature_mode": (
                            "with_sss"
                            if use_sss
                            else "without_sss"
                        ),
                        **result,
                    }

                    if best is None or (
                        candidate["rmse"],
                        candidate["mae"],
                    ) < (
                        best["rmse"],
                        best["mae"],
                    ):
                        best = candidate

    if best is None:
        raise ValueError("ไม่สามารถ Tune แบบ Recency-weighted ได้")

    return best


def tune_station(
    station_data: pd.DataFrame,
    tuning_years: List[int],
) -> Dict[str, Any]:
    station_id = int(station_data["station_id"].iloc[0])

    recency_factor = float(
        VALIDATION_RECENCY_BY_STATION.get(
            station_id,
            1.0,
        )
    )

    if recency_factor <= 1.0:
        config = tune_station_standard(
            station_data,
            tuning_years,
        )

        config["validation_recency_factor"] = 1.0
        config["bias_strength"] = float(BIAS_STRENGTH)

        return config

    return tune_station_recency(
        station_data,
        tuning_years,
        recency_factor,
    )


def evaluate_holdout(
    data: pd.DataFrame,
    holdout_year: int,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[int, Dict[str, Any]]]:
    """
    ประเมินโมเดลบน Holdout year พร้อมตัวชี้วัดเพิ่มเติม

    NRMSE:
        RMSE / Mean(Actual) × 100

    Mean Baseline:
        ใช้ค่าเฉลี่ย Catch ของข้อมูล Train ของจังหวัดนั้น
        เป็นค่าคาดการณ์ทุกเดือนใน Holdout
        โดยไม่ใช้ข้อมูล Holdout ในการสร้าง Baseline
    """
    tuning_years = tuning_years_for_holdout(holdout_year)

    metric_rows = []
    prediction_rows = []
    configs: Dict[int, Dict[str, Any]] = {}

    overall_actual: List[float] = []
    overall_prediction: List[float] = []
    overall_baseline_prediction: List[float] = []

    for station_id in sorted(data["station_id"].unique()):
        station_data = data[data["station_id"] == station_id].copy()

        config = tune_station(station_data, tuning_years)
        configs[int(station_id)] = config

        train = station_data[station_data["year"] < holdout_year]
        test = station_data[station_data["year"] == holdout_year]

        if train.empty or test.empty:
            continue

        raw, _ = fit_raw(
            train,
            test,
            config["decay"],
            bool(config.get("use_sss", True)),
        )

        seasonal_mean, seasonal_max = seasonal_reference(
            train,
            test,
        )

        prediction = apply_calibration(
            raw,
            seasonal_mean,
            seasonal_max,
            config["model_weight"],
            config["cap_multiplier"],
        )

        prediction = apply_bias_correction(
            prediction,
            config.get("bias", 0.0),
        )

        # ----------------------------
        # Model metrics
        # ----------------------------
        metric = calculate_metrics(
            test["catch"],
            prediction,
        )

        nrmse_percent = calculate_nrmse_percent(
            test["catch"],
            metric["rmse"],
        )

        # ----------------------------
        # Mean Baseline
        # ----------------------------
        baseline_mean = float(
            train["catch"].mean()
        )

        baseline_prediction = np.full(
            len(test),
            baseline_mean,
            dtype=float,
        )

        baseline_metric = calculate_metrics(
            test["catch"],
            baseline_prediction,
        )

        province = str(
            station_data["station_name"].iloc[0]
        )

        metric_rows.append(
            {
                "station_id": int(station_id),
                "province": province,
                "train_years": f"{START_YEAR}-{holdout_year - 1}",
                "test_year": int(holdout_year),
                "mae": metric["mae"],
                "rmse": metric["rmse"],
                "nrmse_percent": nrmse_percent,
                "r2": metric["r2"],
                "baseline_mae": baseline_metric["mae"],
                "baseline_rmse": baseline_metric["rmse"],
                "baseline_mean": baseline_mean,
                # Alpha = prediction cap multiplier
                "alpha": config["cap_multiplier"],
                "weight": config["model_weight"],
                "bias": config.get("bias", 0.0),
                "decay": config["decay"],
                "use_sss": bool(config.get("use_sss", True)),
            }
        )

        for index, row in enumerate(
            test.itertuples(index=False)
        ):
            prediction_rows.append(
                {
                    "station_id": int(station_id),
                    "province": province,
                    "year": int(row.year),
                    "month": int(row.month),
                    "sst": float(row.sst),
                    "chlorophyll_a": float(row.chlorophyll_a),
                    "sss": float(row.sss),
                    "rainfall": float(row.rainfall),
                    "wind_speed": float(row.wind_speed),
                    "air_temperature": float(row.air_temperature),
                    "wind_direction": float(row.wind_direction),
                    "actual_catch": float(row.catch),
                    "predicted_catch": float(prediction[index]),
                    "baseline_prediction": float(
                        baseline_prediction[index]
                    ),
                    "absolute_error": abs(
                        float(row.catch)
                        - float(prediction[index])
                    ),
                    "baseline_absolute_error": abs(
                        float(row.catch)
                        - float(baseline_prediction[index])
                    ),
                }
            )

        overall_actual.extend(
            test["catch"].tolist()
        )
        overall_prediction.extend(
            prediction.tolist()
        )
        overall_baseline_prediction.extend(
            baseline_prediction.tolist()
        )

    # ----------------------------
    # Overall metrics
    # ----------------------------
    overall = calculate_metrics(
        overall_actual,
        overall_prediction,
    )

    overall_baseline = calculate_metrics(
        overall_actual,
        overall_baseline_prediction,
    )

    overall_nrmse = calculate_nrmse_percent(
        overall_actual,
        overall["rmse"],
    )

    metric_rows.append(
        {
            "station_id": None,
            "province": "OVERALL",
            "train_years": f"{START_YEAR}-{holdout_year - 1}",
            "test_year": int(holdout_year),
            "mae": overall["mae"],
            "rmse": overall["rmse"],
            "nrmse_percent": overall_nrmse,
            "r2": overall["r2"],
            "baseline_mae": overall_baseline["mae"],
            "baseline_rmse": overall_baseline["rmse"],
            "baseline_mean": None,
            "alpha": None,
            "weight": None,
            "bias": None,
            "decay": None,
            "use_sss": None,
        }
    )

    return (
        pd.DataFrame(metric_rows),
        pd.DataFrame(prediction_rows),
        configs,
    )


# 7) เทรนโมเดลใช้งานจริง
def build_month_reference(train: pd.DataFrame) -> Dict[int, Dict[str, float]]:
    reference: Dict[int, Dict[str, float]] = {}
    for month in range(1, 13):
        values = train.loc[train["month"] == month, "catch"]
        if values.empty:
            values = train["catch"]
        reference[month] = {
            "mean": float(values.mean()),
            "max": float(values.max()),
        }
    return reference


def train_final_models(
    data: pd.DataFrame,
    configs: Dict[int, Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    bundles: Dict[int, Dict[str, Any]] = {}

    for station_id, config in configs.items():
        train = data[data["station_id"] == station_id].copy()
        if train.empty:
            continue

        # เทรนโมเดลสุดท้ายด้วยข้อมูลทั้งหมด
        _, model = fit_raw(train, train.iloc[:1].copy(), config["decay"], bool(config.get("use_sss", True)))

        bundles[int(station_id)] = {
            "model": model,
            "config": config,
            "month_reference": build_month_reference(train),
            "station_name": str(train["station_name"].iloc[0]),
            "train_start_year": int(train["year"].min()),
            "train_end_year": int(train["year"].max()),
        }

    return bundles


def predict_with_bundle(
    bundle: Dict[str, Any],
    feature_frame: pd.DataFrame,
) -> np.ndarray:
    raw = np.maximum(bundle["model"].predict(feature_frame), 0.0)

    means = np.asarray(
        [
            bundle["month_reference"][int(month)]["mean"]
            for month in feature_frame["month"]
        ],
        dtype=float,
    )
    maximums = np.asarray(
        [
            bundle["month_reference"][int(month)]["max"]
            for month in feature_frame["month"]
        ],
        dtype=float,
    )

    config = bundle["config"]
    prediction = apply_calibration(
        raw,
        means,
        maximums,
        config["model_weight"],
        config["cap_multiplier"],
    )

    return apply_bias_correction(
        prediction,
        config.get("bias", 0.0),
    )


def metric_dict_for_station(
    metrics_df: pd.DataFrame,
    station_id: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    province_row = metrics_df[
        metrics_df["station_id"] == station_id
    ]
    overall_row = metrics_df[
        metrics_df["province"] == "OVERALL"
    ]

    if province_row.empty:
        raise ValueError("ไม่พบ Performance ของจังหวัดที่เลือก")

    p = province_row.iloc[0]
    o = overall_row.iloc[0]

    province_metrics = {
        "mae": round(float(p["mae"]), 6),
        "rmse": round(float(p["rmse"]), 6),
        "nrmse_percent": round(float(p["nrmse_percent"]), 6),
        "r2": round(float(p["r2"]), 6),
        "baseline_mae": round(float(p["baseline_mae"]), 6),
        "baseline_rmse": round(float(p["baseline_rmse"]), 6),
        "baseline_mean": round(float(p["baseline_mean"]), 6),
        "rows": 12,
    }

    overall_metrics = {
        "mae": round(float(o["mae"]), 6),
        "rmse": round(float(o["rmse"]), 6),
        "nrmse_percent": round(float(o["nrmse_percent"]), 6),
        "r2": round(float(o["r2"]), 6),
        "baseline_mae": round(float(o["baseline_mae"]), 6),
        "baseline_rmse": round(float(o["baseline_rmse"]), 6),
        "rows": int(
            metrics_df[metrics_df["province"] != "OVERALL"].shape[0] * 12
        ),
    }

    return province_metrics, overall_metrics


def prepare_runtime():
    stations, catch, env, weather = load_database()
    data, feature_rows, source_summary = build_supervised_data(
        stations,
        catch,
        env,
        weather,
    )

    holdout_year = int(source_summary["holdout_year"])
    metrics_df, holdout_predictions, configs = evaluate_holdout(
        data,
        holdout_year,
    )
    bundles = train_final_models(data, configs)

    return {
        "stations": stations,
        "catch": catch,
        "env": env,
        "weather": weather,
        "feature_rows": feature_rows,
        "data": data,
        "source_summary": source_summary,
        "metrics": metrics_df,
        "holdout_predictions": holdout_predictions,
        "configs": configs,
        "bundles": bundles,
    }


# 8) เตรียมผลลัพธ์สำหรับหน้าเว็บ
def actual_catch_for_month(
    catch: pd.DataFrame,
    station_id: int,
    year: int,
    month: int,
):
    match = catch[
        (catch["station_id"] == station_id)
        & (catch["year"] == year)
        & (catch["month"] == month)
    ]
    if match.empty:
        return None
    return float(match["catch"].iloc[0])


def model_json(
    runtime: Dict[str, Any],
    station_id: int,
) -> Dict[str, Any]:
    province_metrics, overall_metrics = metric_dict_for_station(
        runtime["metrics"],
        station_id,
    )
    config = runtime["configs"][station_id]
    summary = runtime["source_summary"]

    use_sss = bool(config.get("use_sss", True))
    feature_names = [
        "SST",
        "Chlorophyll-a",
    ]
    if use_sss:
        feature_names.append("Sea Surface Salinity (SSS)")
    feature_names.extend([
        "Rainfall",
        "Wind Speed",
        "Air Temperature",
        "Wind Direction sin/cos",
        "Year Index",
        "Month One-Hot",
    ])

    use_slp = bool(
        USE_SEA_LEVEL_PRESSURE_BY_STATION.get(station_id, False)
    )
    use_monsoon = bool(
        USE_MONSOON_BY_STATION.get(station_id, False)
    )

    if use_slp:
        feature_names.append("Sea Level Pressure")
    if use_monsoon:
        feature_names.append("Monsoon One-Hot")

    return {
        "name": "Hybrid Linear Regression (Selective SLP; Monsoon tested but disabled)",
        "features": feature_names,
        "validation_metrics": province_metrics,
        "overall_metrics": overall_metrics,
        "r2_note": "R² รายจังหวัดอาจติดลบได้เมื่อ Test มีเพียง 12 เดือน; หน้าเว็บจะแสดง Overall R² สำหรับภาพรวมระบบ",
        "holdout_year": int(summary["holdout_year"]),
        "train_years": f"{START_YEAR}-{int(summary['holdout_year']) - 1}",
        "alpha": config["cap_multiplier"],
        "weight": float(config["model_weight"]),
        "bias": float(config.get("bias", 0.0)),
        "bias_strength": float(config.get("bias_strength", BIAS_STRENGTH)),
        "bias_method": config.get("bias_method", "none"),
        "decay": float(config["decay"]),
        "validation_recency_factor": float(
            config.get("validation_recency_factor", 1.0)
        ),
        "use_sss": use_sss,
        "use_sea_level_pressure": use_slp,
        "use_monsoon": use_monsoon,
        "sss_note": (
            "ใช้ SSS ในโมเดลจังหวัดนี้"
            if use_sss
            else "ไม่ใช้ SSS ในโมเดลจังหวัดนี้ เพราะผลเปรียบเทียบเดิมแย่ลง"
        ),
        "final_train_years": (
            f"{START_YEAR}-{int(summary['catch_max_year'])}"
        ),
    }


# 9) สร้างกราฟ Actual vs Prediction
def generate_graphs_for_year(
    runtime: Dict[str, Any],
    station_id: int,
    year: int,
) -> bool:
    
    """
    สร้างกราฟ Actual vs Prediction
    """
    feature_rows = runtime["feature_rows"]

    year_rows = feature_rows[
        (feature_rows["station_id"] == station_id)
        & (feature_rows["year"] == year)
    ].copy()

    if year_rows.empty:
        return False

    year_rows["year_index"] = year_rows["year"] - START_YEAR
    year_rows = year_rows.sort_values("month").reset_index(drop=True)

    # ใช้ผล Prediction จากโมเดลเดิมโดยตรง
    # ส่วนนี้ไม่ได้แก้สูตรหรือค่า Parameter ของโมเดล
    prediction = predict_with_bundle(
        runtime["bundles"][station_id],
        year_rows,
    )

    actual_rows = runtime["catch"][
        (runtime["catch"]["station_id"] == station_id)
        & (runtime["catch"]["year"] == year)
    ][["month", "catch"]].copy()

    plot_frame = year_rows.merge(
        actual_rows,
        on="month",
        how="left",
    )

    plot_frame["predicted"] = prediction

    # --------------------------------------------------------
    # Missing Actual ไม่เท่ากับ 0
    # --------------------------------------------------------
    # หากฐานข้อมูลไม่มีข้อมูล catch ของเดือนนั้น ให้คงเป็น NaN
    # Matplotlib จะเว้นเส้น Actual ในเดือนดังกล่าวโดยอัตโนมัติ
    # การแก้ส่วนนี้มีผลเฉพาะ "กราฟ" เท่านั้น
    plot_frame["catch"] = pd.to_numeric(
        plot_frame["catch"],
        errors="coerce",
    )

    plot_frame.loc[
        plot_frame["catch"].notna(),
        "catch",
    ] = (
        plot_frame.loc[
            plot_frame["catch"].notna(),
            "catch",
        ]
        .astype(float)
        .clip(lower=0.0)
    )

    missing_months = (
        plot_frame.loc[
            plot_frame["catch"].isna(),
            "month",
        ]
        .astype(int)
        .tolist()
    )

    try:
        import matplotlib

        matplotlib.use("Agg")

        import matplotlib.pyplot as plt

    except Exception:
        return False

    # --------------------------------------------------------
    # กราฟ Actual vs Prediction
    # --------------------------------------------------------
    fig, ax = plt.subplots(
        figsize=(10, 5.2)
    )

    # Prediction แสดงต่อเนื่องครบทุกเดือนที่มี Feature
    ax.plot(
        plot_frame["month"],
        plot_frame["predicted"],
        marker="o",
        linewidth=2,
        label="Prediction",
    )

    # Actual: ให้เชื่อมเส้นข้ามเดือนที่ไม่มีข้อมูล
    # แนวคิดคือ plot เฉพาะจุดที่มีข้อมูลจริง (non-NaN)
    # ทำให้เส้นเชื่อมจากเดือนก่อนหน้าไปยังเดือนถัดไปที่มีข้อมูล
    actual_valid_frame = plot_frame.loc[
        plot_frame["catch"].notna(),
        ["month", "catch"]
    ].copy()

    if not actual_valid_frame.empty:
        ax.plot(
            actual_valid_frame["month"],
            actual_valid_frame["catch"],
            marker="o",
            linewidth=2,
            label="Actual",
        )
    else:
        # กรณีไม่มีข้อมูลจริงเลยทั้งปี ให้ยังคงมี legend
        ax.plot(
            [],
            [],
            marker="o",
            linewidth=2,
            label="Actual",
        )

    # --------------------------------------------------------
    # ปรับแกน Y โดยไม่ให้ NaN กระทบ Scale
    # --------------------------------------------------------
    actual_valid = plot_frame["catch"].dropna()

    y_candidates = [
        float(
            np.nanmax(
                plot_frame["predicted"].to_numpy(
                    dtype=float
                )
            )
        ),
        1.0,
    ]

    if not actual_valid.empty:
        y_candidates.append(
            float(
                actual_valid.max()
            )
        )

    y_max = max(
        y_candidates
    )

    ax.set_ylim(
        0,
        y_max * 1.12,
    )

    # --------------------------------------------------------
    # แสดงค่าจริงที่สูงผิดปกติ
    # --------------------------------------------------------
    if not actual_valid.empty:

        peak_index = actual_valid.idxmax()

        peak_value = float(
            plot_frame.loc[
                peak_index,
                "catch",
            ]
        )

        peak_month = int(
            plot_frame.loc[
                peak_index,
                "month",
            ]
        )

        non_peak = actual_valid.drop(
            index=peak_index
        )

        reference = (
            float(
                non_peak.max()
            )
            if not non_peak.empty
            else 0.0
        )

        if peak_value > max(
            reference * 2.5,
            30.0,
        ):
            ax.annotate(
                f"Actual {peak_value:.0f} t",
                xy=(
                    peak_month,
                    peak_value,
                ),
                xytext=(
                    0,
                    12,
                ),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )

    # --------------------------------------------------------
    # แสดงข้อความ No data ตรงเดือนที่ไม่มี Actual
    # --------------------------------------------------------
    # วางข้อความใต้แกน X เพื่อไม่ให้ถูกเข้าใจว่าเป็นค่า 0 ตัน
    for month in missing_months:
        ax.text(
            month,
            -0.10,
            "No data",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=8,
            rotation=45,
        )

    # --------------------------------------------------------
    # รูปแบบกราฟ
    # --------------------------------------------------------
    ax.set_title(
        f"Mackerel Catch - {year}"
    )

    ax.set_xlabel(
        "Month"
    )

    ax.set_ylabel(
        "Ton"
    )

    ax.set_xticks(
        range(1, 13)
    )

    ax.set_xlim(
        0.5,
        12.5,
    )

    ax.grid(
        True,
        alpha=0.25,
    )

    ax.legend()

    if missing_months:
        missing_text = ", ".join(
            str(month)
            for month in missing_months
        )

        fig.text(
            0.5,
            0.015,
            (
                "Actual data unavailable for month(s): "
                f"{missing_text} — not treated as 0"
            ),
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(
            rect=[
                0,
                0.08,
                1,
                1,
            ]
        )

    else:
        fig.tight_layout()

    fig.savefig(
        OUTPUT_DIR
        / "regression_fish.png",
        dpi=140,
    )

    plt.close(
        fig
    )

    # ลบกราฟสิ่งแวดล้อมเก่าที่อาจค้างจากเวอร์ชันก่อน
    for old_graph in [
        "regression_sst.png",
        "regression_chlor.png",
        "regression_sss.png",
    ]:
        old_path = (
            OUTPUT_DIR
            /
            old_graph
        )

        if old_path.exists():
            try:
                old_path.unlink()

            except OSError:
                pass

    return True


# 10) คาดการณ์จากข้อมูลฐานข้อมูล
def predict_database_mode(
    province: str,
    year: int,
    month: int,
) -> Dict[str, Any]:
    runtime = prepare_runtime()
    station_id, province_name = station_for_province(
        runtime["stations"],
        province,
    )

    if year < START_YEAR or year > REQUESTED_END_YEAR:
        raise ValueError(
            f"ปีต้องอยู่ระหว่าง {START_YEAR}-{REQUESTED_END_YEAR}"
        )
    if month < 1 or month > 12:
        raise ValueError("เดือนต้องอยู่ระหว่าง 1-12")

    feature = runtime["feature_rows"]
    row = feature[
        (feature["station_id"] == station_id)
        & (feature["year"] == year)
        & (feature["month"] == month)
    ].copy()

    if row.empty:
        raise ValueError(
            f"ไม่มี marine_environment/weather_data สำหรับ {province_name} "
            f"ปี {year} เดือน {MONTH_NAMES_TH.get(month, month)}"
        )

    row["year_index"] = row["year"] - START_YEAR
    prediction = float(
        predict_with_bundle(runtime["bundles"][station_id], row)[0]
    )

    actual = actual_catch_for_month(
        runtime["catch"],
        station_id,
        year,
        month,
    )

    graphs_generated = generate_graphs_for_year(
        runtime,
        station_id,
        year,
    )

    r = row.iloc[0]
    return {
        "status": "success",
        "mode": "database",
        "province": province_name,
        "year": int(year),
        "month": int(month),
        "month_name": MONTH_NAMES_TH.get(month, str(month)),
        "ton": round(prediction, 6),
        "sst": round(float(r["sst"]), 6),
        "chlor_a": round(float(r["chlorophyll_a"]), 6),
        "sss": round(float(r["sss"]), 6),
        "sss_used": bool(runtime["configs"][station_id].get("use_sss", True)),
        "rainfall": round(float(r["rainfall"]), 6),
        "wind_speed": round(float(r["wind_speed"]), 6),
        "sea_level_pressure": round(float(r["sea_level_pressure"]), 6),
        "monsoon": str(r["monsoon"]),
        "air_temperature": round(float(r["air_temperature"]), 6),
        "wind_direction": round(float(r["wind_direction"]), 6),
        "actual_ton": None if actual is None else round(actual, 6),
        "graphs_generated": bool(graphs_generated),
        "model": model_json(runtime, station_id),
        "source_summary": runtime["source_summary"],
    }


# 11) คาดการณ์จากค่าที่ผู้ใช้กำหนด
def custom_weather_row(
    weather: pd.DataFrame,
    station_id: int,
    year: int,
    month: int,
) -> Tuple[float, float, float, float, float, str, str]:
    """
    คืน Rainfall, Wind Speed, SLP, Air Temperature,
    Wind Direction, Monsoon และแหล่งข้อมูล
    """
    exact = weather[
        (weather["station_id"] == station_id)
        & (weather["year"] == year)
        & (weather["month"] == month)
    ]

    if not exact.empty:
        return (
            float(exact["rainfall"].iloc[0]),
            float(exact["wind_speed"].iloc[0]),
            float(exact["sea_level_pressure"].iloc[0]),
            float(exact["air_temperature"].iloc[0]),
            float(exact["wind_direction"].iloc[0]),
            str(exact["monsoon"].iloc[0]),
            "database_exact_month",
        )

    same_month = weather[
        (weather["station_id"] == station_id)
        & (weather["month"] == month)
    ]

    if same_month.empty:
        same_month = weather[
            weather["station_id"] == station_id
        ]

    if same_month.empty:
        raise ValueError(
            "ไม่มี weather_data สำหรับจังหวัดที่เลือก"
        )

    wind_rad = np.deg2rad(
        same_month["wind_direction"].to_numpy(dtype=float)
    )
    wind_direction = float(
        (
            np.rad2deg(
                np.arctan2(
                    np.sin(wind_rad).mean(),
                    np.cos(wind_rad).mean(),
                )
            )
            + 360.0
        )
        % 360.0
    )

    monsoon_mode = (
        same_month["monsoon"]
        .astype(str)
        .mode()
    )
    monsoon = (
        str(monsoon_mode.iloc[0])
        if not monsoon_mode.empty
        else "Transition"
    )

    return (
        float(same_month["rainfall"].median()),
        float(same_month["wind_speed"].median()),
        float(same_month["sea_level_pressure"].median()),
        float(same_month["air_temperature"].median()),
        wind_direction,
        monsoon,
        "historical_station_month_median",
    )



def predict_custom_mode(
    province: str,
    year: int,
    month: int,
    sst: float,
    chlor_a: float,
    sss: float,
) -> Dict[str, Any]:
    runtime = prepare_runtime()
    station_id, province_name = station_for_province(
        runtime["stations"],
        province,
    )

    if year < START_YEAR or year > REQUESTED_END_YEAR:
        raise ValueError(
            f"ปีต้องอยู่ระหว่าง {START_YEAR}-{REQUESTED_END_YEAR}"
        )
    if month < 1 or month > 12:
        raise ValueError("เดือนต้องอยู่ระหว่าง 1-12")
    if not np.isfinite(sst) or sst <= 0:
        raise ValueError("SST ต้องเป็นตัวเลขมากกว่า 0")
    if not np.isfinite(chlor_a) or chlor_a <= 0:
        raise ValueError("Chlorophyll-a ต้องเป็นตัวเลขมากกว่า 0")
    if not np.isfinite(sss) or sss <= 0:
        raise ValueError("SSS ต้องเป็นตัวเลขมากกว่า 0")

    (
        rainfall,
        wind_speed,
        sea_level_pressure,
        air_temperature,
        wind_direction,
        monsoon,
        weather_source,
    ) = custom_weather_row(
        runtime["weather"],
        station_id,
        year,
        month,
    )

    row = pd.DataFrame(
        [
            {
                "station_id": station_id,
                "year": int(year),
                "month": int(month),
                "sst": float(sst),
                "chlorophyll_a": float(chlor_a),
                "sss": float(sss),
                "rainfall": float(rainfall),
                "wind_speed": float(wind_speed),
                "sea_level_pressure": float(sea_level_pressure),
                "air_temperature": float(air_temperature),
                "wind_direction": float(wind_direction),
                "monsoon": str(monsoon),
                "wind_dir_sin": float(np.sin(np.deg2rad(wind_direction))),
                "wind_dir_cos": float(np.cos(np.deg2rad(wind_direction))),
                "year_index": int(year) - START_YEAR,
            }
        ]
    )

    prediction = float(
        predict_with_bundle(runtime["bundles"][station_id], row)[0]
    )

    return {
        "status": "success",
        "mode": "custom",
        "province": province_name,
        "year": int(year),
        "month": int(month),
        "month_name": MONTH_NAMES_TH.get(month, str(month)),
        "ton": round(prediction, 6),
        "sst": round(float(sst), 6),
        "chlor_a": round(float(chlor_a), 6),
        "sss": round(float(sss), 6),
        "sss_used": bool(runtime["configs"][station_id].get("use_sss", True)),
        "sss_source": "manual_input",
        "rainfall": round(float(rainfall), 6),
        "wind_speed": round(float(wind_speed), 6),
        "sea_level_pressure": round(float(sea_level_pressure), 6),
        "monsoon": str(monsoon),
        "air_temperature": round(float(air_temperature), 6),
        "wind_direction": round(float(wind_direction), 6),
        "weather_source": weather_source,
        "actual_ton": None,
        "graphs_generated": False,
        "model": model_json(runtime, station_id),
        "source_summary": runtime["source_summary"],
    }


# 12) แสดง Performance และรับคำสั่ง CLI
def decode_province(value: str, use_b64: bool) -> str:
    if not use_b64:
        return str(value).strip()
    try:
        decoded = base64.b64decode(value).decode("utf-8")
    except Exception as exc:
        raise ValueError("ไม่สามารถถอดรหัสชื่อจังหวัดได้") from exc
    return decoded.strip()


def format_metric(value, decimals: int) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "-"
    return f"{float(value):.{decimals}f}"


def print_performance_table() -> None:
    runtime = prepare_runtime()
    metrics_df = runtime["metrics"].copy()
    summary = runtime["source_summary"]

    metrics_path = OUTPUT_DIR / "regression_model_evaluation.csv"
    metrics_df.to_csv(
        metrics_path,
        index=False,
        encoding="utf-8-sig",
    )

    holdout_path = OUTPUT_DIR / "regression_holdout_predictions.csv"
    runtime["holdout_predictions"].to_csv(
        holdout_path,
        index=False,
        encoding="utf-8-sig",
    )

    # ========================================================
    # ตารางที่ 1: Model Performance เดิม
    # ========================================================
    width = 100
    print()
    print("=" * width)
    print("LINEAR REGRESSION PERFORMANCE")
    print("=" * width)

    header = (
        f"{'Province':<22}"
        f"{'MAE':>12}"
        f"{'RMSE':>12}"
        f"{'R²':>12}"
        f"{'Alpha':>12}"
        f"{'Weight':>12}"
        f"{'Bias':>12}"
    )

    print(header)
    print("-" * width)

    for row in metrics_df.itertuples(index=False):
        if str(row.province) == "OVERALL":
            continue

        print(
            f"{str(row.province):<22}"
            f"{format_metric(row.mae, 2):>12}"
            f"{format_metric(row.rmse, 2):>12}"
            f"{format_metric(row.r2, 4):>12}"
            f"{format_metric(row.alpha, 4):>12}"
            f"{format_metric(row.weight, 3):>12}"
            f"{format_metric(row.bias, 2):>12}"
        )

    overall = metrics_df[
        metrics_df["province"] == "OVERALL"
    ].iloc[0]

    print("-" * width)
    print(
        f"{'OVERALL':<22}"
        f"{format_metric(overall['mae'], 2):>12}"
        f"{format_metric(overall['rmse'], 2):>12}"
        f"{format_metric(overall['r2'], 4):>12}"
        f"{'-':>12}"
        f"{'-':>12}"
        f"{'-':>12}"
    )
    print("=" * width)

    # ========================================================
    # ตารางที่ 2: Normalized Error / Mean Baseline
    # ========================================================
    width2 = 86
    print()
    print("=" * width2)
    print("NORMALIZED ERROR / MEAN BASELINE COMPARISON")
    print("=" * width2)

    header2 = (
        f"{'Province':<22}"
        f"{'NRMSE (%)':>14}"
        f"{'Baseline MAE':>16}"
        f"{'Baseline RMSE':>17}"
        f"{'Model vs Base':>17}"
    )

    print(header2)
    print("-" * width2)

    for row in metrics_df.itertuples(index=False):
        model_vs_base = (
            "BETTER"
            if float(row.rmse) < float(row.baseline_rmse)
            else "WORSE"
        )

        print(
            f"{str(row.province):<22}"
            f"{format_metric(row.nrmse_percent, 2):>14}"
            f"{format_metric(row.baseline_mae, 2):>16}"
            f"{format_metric(row.baseline_rmse, 2):>17}"
            f"{model_vs_base:>17}"
        )

    print("=" * width2)

    print(
        "NRMSE (%) = RMSE / Mean(Actual) × 100 | "
        "ค่าต่ำกว่าดีกว่า"
    )
    print(
        "Mean Baseline = ใช้ค่าเฉลี่ย Catch ของ Train "
        "ของจังหวัดนั้นทำนายทุกเดือนใน Holdout"
    )
    print(
        "Model vs Base = เปรียบเทียบ RMSE ของโมเดลกับ Baseline; "
        "BETTER หมายถึง RMSE โมเดลต่ำกว่า"
    )
    print()

    print(
        f"Train: {START_YEAR}-{int(summary['holdout_year']) - 1} | "
        f"Test: {int(summary['holdout_year'])} | "
        f"Final train: {START_YEAR}-{int(summary['catch_max_year'])}"
    )
    print(
        "Features: SST, Chlorophyll-a, SSS, Rainfall, Wind Speed, "
        "Sea Level Pressure (selected), Air Temperature, Wind Direction sin/cos, "
        "Year Index, Month One-Hot, Monsoon One-Hot (selected)"
    )
    print(
        f"SSS range in database: {summary['sss_min']:.3f}-"
        f"{summary['sss_max']:.3f} PSU | mean {summary['sss_mean']:.3f} PSU"
    )
    print(
        "Weight = สัดส่วนผลจาก Linear Regression | "
        "Bias = ค่าชดเชยจาก median residual ของ Walk-forward validation"
    )
    print(
        "Recency factor: "
        + ", ".join(
            f"station {station_id}={factor:g}"
            for station_id, factor
            in VALIDATION_RECENCY_BY_STATION.items()
        )
    )
    print()


def parse_cli_and_run() -> None:
    args = sys.argv[1:]

    if not args or args == ["--performance"]:
        print_performance_table()
        return

    use_b64 = "--b64" in args
    args = [value for value in args if value != "--b64"]

    if args and args[0] == "--custom":
        if len(args) != 7:
            raise ValueError(
                "Custom usage: --custom <province> <year> <month> <sst> <chlor_a> <sss> [--b64]"
            )

        province = decode_province(args[1], use_b64)
        year = int(args[2])
        month = int(args[3])
        sst = float(args[4])
        chlor_a = float(args[5])
        sss = float(args[6])

        send_json(
            predict_custom_mode(
                province,
                year,
                month,
                sst,
                chlor_a,
                sss,
            )
        )
        return

    if len(args) != 3:
        raise ValueError(
            "Usage: <province> <year> <month> [--b64]"
        )

    province = decode_province(args[0], use_b64)
    year = int(args[1])
    month = int(args[2])

    send_json(
        predict_database_mode(
            province,
            year,
            month,
        )
    )


def main() -> None:
    configure_stdout()
    parse_cli_and_run()


if __name__ == "__main__":
    configure_stdout()
    try:
        main()
    except Exception as exc:
        # ส่ง error เป็น JSON ให้ PHP
        if len(sys.argv) > 1 and sys.argv[1] != "--performance":
            send_json(
                {
                    "status": "error",
                    "message": str(exc),
                }
            )
        else:
            print()
            print("=" * 72)
            print("ไม่สามารถสร้าง LINEAR REGRESSION PERFORMANCE ได้")
            print("=" * 72)
            print(str(exc))
            print()
            print(
                "ตรวจสอบว่า MySQL ทำงานอยู่ และฐานข้อมูล projecta มีตาราง "
                "station, catch_mackereldata, marine_environment และ weather_data"
            )
            sys.exit(1)
