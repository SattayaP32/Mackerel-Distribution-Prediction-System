import requests
import pandas as pd
import numpy as np
import mysql.connector
import time
from datetime import date, timedelta


# ============================================================
# CONFIG
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "projecta"
}


# พิกัดที่ใช้ในโครงงาน
STATIONS = {
    1: {
        "name": "เพชรบุรี",
        "lat": 13.00,
        "lon": 100.18
    },
    2: {
        "name": "สมุทรสงคราม",
        "lat": 13.30,
        "lon": 100.10
    },
    3: {
        "name": "สมุทรสาคร",
        "lat": 13.40,
        "lon": 100.30
    },
    4: {
        "name": "ชลบุรี",
        "lat": 13.20,
        "lon": 100.82
    },
    5: {
        "name": "สมุทรปราการ",
        "lat": 13.45,
        "lon": 100.70
    }
}


API_URL = "https://archive-api.open-meteo.com/v1/archive"

START_DATE = "2019-01-01"

# ERA5 อาจไม่ได้มีข้อมูลถึงวันปัจจุบันทันที
END_DATE = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")


# ============================================================
# CIRCULAR MEAN
# ============================================================

def circular_mean_direction(directions):
    """
    ค่าเฉลี่ยทิศทางลมแบบ Circular Mean

    ตัวอย่าง:
    350° + 10°
    ต้องได้ประมาณ 0°
    ไม่ใช่ 180°
    """

    values = pd.to_numeric(
        pd.Series(directions),
        errors="coerce"
    ).dropna()

    if len(values) == 0:
        return np.nan

    radians = np.deg2rad(values)

    sin_mean = np.mean(np.sin(radians))
    cos_mean = np.mean(np.cos(radians))

    # ถ้า vector เกือบหักล้างกันทั้งหมด
    if (
        abs(sin_mean) < 1e-12
        and abs(cos_mean) < 1e-12
    ):
        return np.nan

    angle = np.degrees(
        np.arctan2(
            sin_mean,
            cos_mean
        )
    )

    return (angle + 360) % 360


# ============================================================
# ANGULAR DIFFERENCE
# ============================================================

def angular_difference(a, b):
    """
    ความแตกต่างขององศาแบบวงกลม

    350° กับ 10°
    = ต่างกัน 20°
    ไม่ใช่ 340°
    """

    if pd.isna(a) or pd.isna(b):
        return np.nan

    return abs(
        (a - b + 180) % 360 - 180
    )


# ============================================================
# LOAD MYSQL
# ============================================================

def load_sql_data():

    print("\nกำลังเชื่อมต่อ MySQL...")

    conn = mysql.connector.connect(
        **DB_CONFIG
    )

    query = """
        SELECT
            station_id,
            year,
            month,
            wind_speed,
            wind_direction
        FROM weather_data
        WHERE status = 1
        ORDER BY
            station_id,
            year,
            month
    """

    cursor = conn.cursor(dictionary=True)

    cursor.execute(query)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    df = pd.DataFrame(rows)

    # บังคับ numeric
    numeric_columns = [
        "station_id",
        "year",
        "month",
        "wind_speed",
        "wind_direction"
    ]

    for col in numeric_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    print(
        f"อ่านข้อมูล SQL สำเร็จ "
        f"{len(df)} records"
    )

    return df


# ============================================================
# DOWNLOAD OPEN-METEO
# ============================================================

def download_open_meteo(
    station_id,
    station
):

    print()
    print("=" * 65)

    print(
        f"กำลังดึงข้อมูล: "
        f"{station['name']}"
    )

    print(
        f"พิกัด: "
        f"{station['lat']}, "
        f"{station['lon']}"
    )

    print("=" * 65)


    params = {

        "latitude":
            station["lat"],

        "longitude":
            station["lon"],

        "start_date":
            START_DATE,

        "end_date":
            END_DATE,

        "hourly":
            "wind_speed_10m,"
            "wind_direction_10m",

        # ใช้ ERA5 ให้เหมือนกันทุกปี
        "models":
            "era5",

        # กำหนดหน่วยชัดเจน
        "wind_speed_unit":
            "kmh",

        "timezone":
            "Asia/Bangkok"
    }


    response = requests.get(
        API_URL,
        params=params,
        timeout=180
    )


    response.raise_for_status()

    data = response.json()


    if "hourly" not in data:

        raise RuntimeError(
            f"ไม่พบ hourly data: {data}"
        )


    # ========================================================
    # RAW HOURLY DATA
    # ========================================================

    df = pd.DataFrame({

        "time":
            data["hourly"]["time"],

        "wind_speed_api":
            data["hourly"][
                "wind_speed_10m"
            ],

        "wind_direction_api":
            data["hourly"][
                "wind_direction_10m"
            ]
    })


    df["time"] = pd.to_datetime(
        df["time"]
    )


    df["wind_speed_api"] = (
        pd.to_numeric(
            df["wind_speed_api"],
            errors="coerce"
        )
    )


    df["wind_direction_api"] = (
        pd.to_numeric(
            df["wind_direction_api"],
            errors="coerce"
        )
    )


    # ค.ศ.
    df["year_ad"] = (
        df["time"].dt.year
    )

    # พ.ศ.
    df["year"] = (
        df["year_ad"] + 543
    )

    df["month"] = (
        df["time"].dt.month
    )


    # ========================================================
    # HOURLY -> MONTHLY
    # ========================================================

    monthly_rows = []


    for (
        year,
        month
    ), group in df.groupby(
        ["year", "month"]
    ):


        # --------------------------------------------
        # WIND SPEED
        # --------------------------------------------

        mean_speed = (
            group["wind_speed_api"]
            .mean()
        )


        # --------------------------------------------
        # WIND DIRECTION
        # --------------------------------------------

        mean_direction = (
            circular_mean_direction(
                group[
                    "wind_direction_api"
                ]
            )
        )


        # จำนวนข้อมูลรายชั่วโมง
        valid_speed_count = (
            group["wind_speed_api"]
            .notna()
            .sum()
        )

        valid_direction_count = (
            group["wind_direction_api"]
            .notna()
            .sum()
        )


        monthly_rows.append({

            "station_id":
                station_id,

            "province":
                station["name"],

            "year":
                int(year),

            "month":
                int(month),

            "api_wind_speed":
                round(
                    mean_speed,
                    2
                ),

            "api_wind_direction":
                round(
                    mean_direction,
                    2
                ),

            "api_speed_hours":
                int(
                    valid_speed_count
                ),

            "api_direction_hours":
                int(
                    valid_direction_count
                )
        })


    monthly = pd.DataFrame(
        monthly_rows
    )


    print(
        f"สำเร็จ: "
        f"{len(monthly)} เดือน"
    )


    return monthly


# ============================================================
# SPEED DIFFERENCE
# ============================================================

def speed_difference(
    sql_speed,
    api_speed
):

    if (
        pd.isna(sql_speed)
        or
        pd.isna(api_speed)
    ):
        return np.nan

    return abs(
        sql_speed - api_speed
    )


# ============================================================
# SPEED PERCENT DIFFERENCE
# ============================================================

def speed_percent_difference(
    sql_speed,
    api_speed
):

    if (
        pd.isna(sql_speed)
        or
        pd.isna(api_speed)
        or
        api_speed == 0
    ):
        return np.nan

    return (
        abs(
            sql_speed - api_speed
        )
        /
        abs(api_speed)
        *
        100
    )


# ============================================================
# CLASSIFY SPEED
# ============================================================

def classify_speed(diff):

    if pd.isna(diff):
        return "NO DATA"

    # เกณฑ์ตรวจสอบเบื้องต้น
    # ไม่ใช่มาตรฐาน Open-Meteo

    if diff <= 2:
        return "OK"

    elif diff <= 5:
        return "CHECK"

    else:
        return "HIGH DIFFERENCE"


# ============================================================
# CLASSIFY DIRECTION
# ============================================================

def classify_direction(diff):

    if pd.isna(diff):
        return "NO DATA"

    # เกณฑ์ตรวจสอบเบื้องต้น
    # ไม่ใช่มาตรฐาน Open-Meteo

    if diff <= 10:
        return "OK"

    elif diff <= 30:
        return "CHECK"

    else:
        return "HIGH DIFFERENCE"


# ============================================================
# MAIN
# ============================================================

print()
print("=" * 70)
print(" OPEN-METEO WEATHER_DATA CHECKER")
print("=" * 70)

print(
    f"ช่วงข้อมูล API: "
    f"{START_DATE} ถึง {END_DATE}"
)

print(
    "Wind speed unit: km/h"
)


# ============================================================
# LOAD SQL
# ============================================================

sql_df = load_sql_data()


# ============================================================
# DOWNLOAD ALL STATIONS
# ============================================================

api_results = []


for station_id, station in STATIONS.items():

    try:

        station_df = (
            download_open_meteo(
                station_id,
                station
            )
        )

        api_results.append(
            station_df
        )

        # ไม่ยิง API ติดกันเกินไป
        time.sleep(1)


    except Exception as e:

        print()
        print(
            f"ERROR: "
            f"{station['name']}"
        )

        print(e)


if len(api_results) == 0:

    raise RuntimeError(
        "ไม่สามารถดึงข้อมูล "
        "Open-Meteo ได้"
    )


api_df = pd.concat(
    api_results,
    ignore_index=True
)


# ============================================================
# MERGE
# ============================================================

compare = sql_df.merge(

    api_df,

    on=[
        "station_id",
        "year",
        "month"
    ],

    how="left"
)


# ============================================================
# WIND SPEED CHECK
# ============================================================

compare[
    "speed_difference"
] = compare.apply(

    lambda row:
        speed_difference(
            row["wind_speed"],
            row["api_wind_speed"]
        ),

    axis=1
)


compare[
    "speed_difference"
] = compare[
    "speed_difference"
].round(2)


compare[
    "speed_difference_percent"
] = compare.apply(

    lambda row:
        speed_percent_difference(
            row["wind_speed"],
            row["api_wind_speed"]
        ),

    axis=1
)


compare[
    "speed_difference_percent"
] = compare[
    "speed_difference_percent"
].round(2)


compare[
    "speed_result"
] = compare[
    "speed_difference"
].apply(
    classify_speed
)


# ============================================================
# WIND DIRECTION CHECK
# ============================================================

compare[
    "direction_difference"
] = compare.apply(

    lambda row:
        angular_difference(
            row["wind_direction"],
            row["api_wind_direction"]
        ),

    axis=1
)


compare[
    "direction_difference"
] = compare[
    "direction_difference"
].round(2)


compare[
    "direction_result"
] = compare[
    "direction_difference"
].apply(
    classify_direction
)


# ============================================================
# OVERALL RESULT
# ============================================================

def overall_result(row):

    speed = row[
        "speed_result"
    ]

    direction = row[
        "direction_result"
    ]


    if (
        speed == "NO DATA"
        or
        direction == "NO DATA"
    ):

        return "NO DATA"


    if (
        speed == "HIGH DIFFERENCE"
        or
        direction == "HIGH DIFFERENCE"
    ):

        return "HIGH DIFFERENCE"


    if (
        speed == "CHECK"
        or
        direction == "CHECK"
    ):

        return "CHECK"


    return "OK"


compare[
    "overall_result"
] = compare.apply(
    overall_result,
    axis=1
)


# ============================================================
# RENAME SQL COLUMNS
# ============================================================

compare = compare.rename(

    columns={

        "wind_speed":
            "sql_wind_speed",

        "wind_direction":
            "sql_wind_direction"
    }
)


# ============================================================
# COLUMN ORDER
# ============================================================

compare = compare[

    [
        "station_id",
        "province",
        "year",
        "month",

        # SPEED
        "sql_wind_speed",
        "api_wind_speed",
        "speed_difference",
        "speed_difference_percent",
        "speed_result",

        # DIRECTION
        "sql_wind_direction",
        "api_wind_direction",
        "direction_difference",
        "direction_result",

        # API QUALITY
        "api_speed_hours",
        "api_direction_hours",

        # OVERALL
        "overall_result"
    ]
]


# ============================================================
# DISPLAY
# ============================================================

print()
print("=" * 110)
print("ผลการตรวจสอบ")
print("=" * 110)

print(
    compare.to_string(
        index=False
    )
)


# ============================================================
# SUMMARY SPEED
# ============================================================

print()
print("=" * 70)
print("WIND SPEED SUMMARY")
print("=" * 70)

speed_summary = (

    compare.groupby(
        [
            "province",
            "speed_result"
        ]
    )

    .size()

    .unstack(
        fill_value=0
    )
)

print(speed_summary)


# ============================================================
# SUMMARY DIRECTION
# ============================================================

print()
print("=" * 70)
print("WIND DIRECTION SUMMARY")
print("=" * 70)

direction_summary = (

    compare.groupby(
        [
            "province",
            "direction_result"
        ]
    )

    .size()

    .unstack(
        fill_value=0
    )
)

print(direction_summary)


# ============================================================
# OVERALL SUMMARY
# ============================================================

print()
print("=" * 70)
print("OVERALL SUMMARY")
print("=" * 70)

overall_summary = (

    compare.groupby(
        [
            "province",
            "overall_result"
        ]
    )

    .size()

    .unstack(
        fill_value=0
    )
)

print(overall_summary)


# ============================================================
# STATISTICS
# ============================================================

print()
print("=" * 70)
print("AVERAGE DIFFERENCE")
print("=" * 70)


stats = (

    compare.groupby(
        "province"
    )

    .agg(

        speed_mean_difference=(
            "speed_difference",
            "mean"
        ),

        speed_mean_percent=(
            "speed_difference_percent",
            "mean"
        ),

        direction_mean_difference=(
            "direction_difference",
            "mean"
        )
    )

    .round(2)
)


print(stats)


# ============================================================
# PROBLEM ROWS
# ============================================================

problem = compare[

    compare[
        "overall_result"
    ].isin(
        [
            "CHECK",
            "HIGH DIFFERENCE"
        ]
    )

].copy()


# ============================================================
# HIGH DIFFERENCE ONLY
# ============================================================

high_problem = compare[

    compare[
        "overall_result"
    ]
    ==
    "HIGH DIFFERENCE"

].copy()


# ============================================================
# SQL DIRECTION = 100
# ============================================================

direction_100 = compare[

    compare[
        "sql_wind_direction"
    ]
    ==
    100

].copy()


# ============================================================
# MISSING API
# ============================================================

missing_api = compare[

    (
        compare[
            "api_wind_speed"
        ].isna()
    )

    |

    (
        compare[
            "api_wind_direction"
        ].isna()
    )

].copy()


# ============================================================
# SAVE CSV
# ============================================================

compare.to_csv(

    "weather_comparison_all.csv",

    index=False,

    encoding="utf-8-sig"
)


problem.to_csv(

    "weather_comparison_check.csv",

    index=False,

    encoding="utf-8-sig"
)


high_problem.to_csv(

    "weather_comparison_high_difference.csv",

    index=False,

    encoding="utf-8-sig"
)


direction_100.to_csv(

    "wind_direction_100_check.csv",

    index=False,

    encoding="utf-8-sig"
)


missing_api.to_csv(

    "weather_missing_api.csv",

    index=False,

    encoding="utf-8-sig"
)


stats.to_csv(

    "weather_difference_summary.csv",

    encoding="utf-8-sig"
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("เสร็จสิ้น")
print("=" * 70)

print(
    f"ตรวจสอบทั้งหมด: "
    f"{len(compare)} records"
)

print(
    f"CHECK/HIGH: "
    f"{len(problem)} records"
)

print(
    f"HIGH DIFFERENCE: "
    f"{len(high_problem)} records"
)

print(
    f"wind_direction = 100: "
    f"{len(direction_100)} records"
)

print(
    f"API missing: "
    f"{len(missing_api)} records"
)


print()
print("สร้างไฟล์:")

print(
    "1. weather_comparison_all.csv"
)

print(
    "2. weather_comparison_check.csv"
)

print(
    "3. weather_comparison_high_difference.csv"
)

print(
    "4. wind_direction_100_check.csv"
)

print(
    "5. weather_missing_api.csv"
)

print(
    "6. weather_difference_summary.csv"
)


print()
print(
    "โปรแกรมนี้ไม่ได้ UPDATE, INSERT "
    "หรือ DELETE ข้อมูลใน MySQL"
)