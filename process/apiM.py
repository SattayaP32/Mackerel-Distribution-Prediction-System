import requests
import pandas as pd
import numpy as np
import mysql.connector
import time
from datetime import date, timedelta


# ============================================================
# DATABASE
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "projecta"
}


# ============================================================
# STATIONS
# ============================================================

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


# ============================================================
# OPEN-METEO
# ============================================================

API_URL = (
    "https://archive-api.open-meteo.com/v1/archive"
)

START_DATE = "2019-01-01"

# เผื่อ ERA5 มี delay
END_DATE = (
    date.today() - timedelta(days=7)
).strftime("%Y-%m-%d")


# ============================================================
# MONSOON
# ============================================================

def get_monsoon(month):
    """
    เกณฑ์รายเดือนสำหรับอ่าวไทย

    Northeast:
        November - February

    Transition:
        March - April

    Southwest:
        May - September

    Transition:
        October

    October ถูกจัด Transition เนื่องจากเป็นเดือน
    ที่โดยปกติเกิดการเปลี่ยน SW -> NE ประมาณกลางเดือน
    """

    if month in [11, 12, 1, 2]:
        return "Northeast"

    elif month in [3, 4]:
        return "Transition"

    elif month in [5, 6, 7, 8, 9]:
        return "Southwest"

    elif month == 10:
        return "Transition"

    return None


# ============================================================
# WIND VECTOR
# ============================================================

def calculate_monthly_wind(group):
    """
    คำนวณลมรายเดือนด้วย U/V vector

    Open-Meteo wind direction เป็นทิศที่ลมพัด "มา"

    u = -speed * sin(direction)
    v = -speed * cos(direction)

    วิธีนี้ดีกว่าการเฉลี่ยองศาตรง ๆ
    """

    speed = pd.to_numeric(
        group["wind_speed"],
        errors="coerce"
    )

    direction = pd.to_numeric(
        group["wind_direction"],
        errors="coerce"
    )

    valid = (
        speed.notna()
        &
        direction.notna()
    )

    speed = speed[valid]
    direction = direction[valid]

    if len(speed) == 0:
        return np.nan, np.nan

    radians = np.deg2rad(direction)

    # Meteorological wind vector
    u = -speed * np.sin(radians)
    v = -speed * np.cos(radians)

    mean_u = u.mean()
    mean_v = v.mean()

    # --------------------------------------------
    # Vector mean speed
    # --------------------------------------------

    vector_speed = np.sqrt(
        mean_u ** 2 +
        mean_v ** 2
    )

    # --------------------------------------------
    # Direction FROM
    # --------------------------------------------

    direction_rad = np.arctan2(
        -mean_u,
        -mean_v
    )

    vector_direction = (
        np.degrees(direction_rad)
        + 360
    ) % 360

    return (
        round(float(vector_speed), 2),
        round(float(vector_direction), 2)
    )


# ============================================================
# DOWNLOAD OPEN-METEO
# ============================================================

def download_station(
    station_id,
    station
):

    print()
    print("=" * 65)

    print(
        f"{station['name']} "
        f"({station['lat']}, {station['lon']})"
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

        # ใช้ ERA5 ชุดเดียวตลอด
        "models":
            "era5",

        # km/h
        "wind_speed_unit":
            "kmh",

        "timezone":
            "Asia/Bangkok",

        # จุดศึกษาอยู่บริเวณทะเลอ่าวไทย
        "cell_selection":
            "sea"
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


    df = pd.DataFrame({

        "time":
            data["hourly"]["time"],

        "wind_speed":
            data["hourly"][
                "wind_speed_10m"
            ],

        "wind_direction":
            data["hourly"][
                "wind_direction_10m"
            ]
    })


    df["time"] = pd.to_datetime(
        df["time"]
    )


    df["year"] = (
        df["time"].dt.year + 543
    )

    df["month"] = (
        df["time"].dt.month
    )


    # ========================================================
    # MONTHLY
    # ========================================================

    monthly_rows = []


    for (
        year,
        month
    ), group in df.groupby(
        ["year", "month"]
    ):


        # --------------------------------------------
        # ค่า wind speed เฉลี่ยรายเดือน
        #
        # ใช้ mean hourly speed เป็น feature หลัก
        # --------------------------------------------

        monthly_mean_speed = (
            pd.to_numeric(
                group["wind_speed"],
                errors="coerce"
            )
            .mean()
        )


        # --------------------------------------------
        # Vector direction
        # --------------------------------------------

        vector_speed, vector_direction = (
            calculate_monthly_wind(
                group
            )
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

            # ML wind speed
            "wind_speed":
                round(
                    float(
                        monthly_mean_speed
                    ),
                    2
                ),

            # ทิศทางลมจาก vector
            "wind_direction":
                vector_direction,

            # เก็บไว้ตรวจสอบใน CSV
            "vector_speed":
                vector_speed,

            "monsoon":
                get_monsoon(
                    int(month)
                )
        })


    monthly = pd.DataFrame(
        monthly_rows
    )


    print(
        f"สำเร็จ {len(monthly)} เดือน"
    )


    return monthly


# ============================================================
# DATABASE SETUP
# ============================================================

def prepare_database(conn):

    cursor = conn.cursor()


    # --------------------------------------------------------
    # BACKUP
    # --------------------------------------------------------

    backup_table = (
        "weather_data_backup_before_monsoon"
    )


    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS
        {backup_table}
        LIKE weather_data
        """
    )


    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM {backup_table}
        """
    )

    backup_count = (
        cursor.fetchone()[0]
    )


    # Backup เฉพาะครั้งแรก
    if backup_count == 0:

        cursor.execute(
            f"""
            INSERT INTO {backup_table}
            SELECT *
            FROM weather_data
            """
        )

        print(
            "Backup weather_data สำเร็จ"
        )

    else:

        print(
            "พบ Backup เดิมแล้ว "
            "จึงไม่เขียนทับ"
        )


    # --------------------------------------------------------
    # MONSOON COLUMN
    # --------------------------------------------------------

    cursor.execute(
        """
        SHOW COLUMNS
        FROM weather_data
        LIKE 'monsoon'
        """
    )


    if cursor.fetchone() is None:

        cursor.execute(
            """
            ALTER TABLE weather_data
            ADD COLUMN monsoon
            VARCHAR(20)
            NULL
            AFTER wind_direction
            """
        )

        print(
            "เพิ่ม column monsoon สำเร็จ"
        )

    else:

        print(
            "มี column monsoon อยู่แล้ว"
        )


    conn.commit()

    cursor.close()


# ============================================================
# UPDATE MYSQL
# ============================================================

def update_database(
    conn,
    all_data
):

    cursor = conn.cursor()


    sql = """
        UPDATE weather_data

        SET
            wind_speed = %s,
            wind_direction = %s,
            monsoon = %s

        WHERE
            station_id = %s
            AND year = %s
            AND month = %s
    """


    updated = 0
    not_found = 0


    for _, row in all_data.iterrows():

        values = (

            float(
                row["wind_speed"]
            ),

            float(
                row["wind_direction"]
            ),

            row["monsoon"],

            int(
                row["station_id"]
            ),

            int(
                row["year"]
            ),

            int(
                row["month"]
            )
        )


        cursor.execute(
            sql,
            values
        )


        if cursor.rowcount > 0:

            updated += 1

        else:

            not_found += 1


    conn.commit()

    cursor.close()


    print()
    print("=" * 65)

    print(
        f"UPDATE สำเร็จ: "
        f"{updated} records"
    )

    print(
        f"ไม่พบแถวใน SQL: "
        f"{not_found} records"
    )

    print("=" * 65)


# ============================================================
# MAIN
# ============================================================

print()
print("=" * 70)
print(" GULF OF THAILAND MONSOON DATA UPDATE")
print("=" * 70)

print(
    f"API period: "
    f"{START_DATE} - {END_DATE}"
)

print(
    "Model: ERA5"
)

print(
    "Wind speed: km/h"
)

print(
    "Grid preference: sea"
)


# ============================================================
# DOWNLOAD
# ============================================================

results = []


for station_id, station in STATIONS.items():

    try:

        station_data = (
            download_station(
                station_id,
                station
            )
        )

        results.append(
            station_data
        )

        time.sleep(1)


    except Exception as e:

        print(
            f"ERROR "
            f"{station['name']}: "
            f"{e}"
        )


if len(results) == 0:

    raise RuntimeError(
        "ไม่สามารถดึงข้อมูล "
        "Open-Meteo ได้"
    )


all_data = pd.concat(
    results,
    ignore_index=True
)


# ============================================================
# SAVE BEFORE UPDATE
# ============================================================

all_data.to_csv(

    "era5_monsoon_before_update.csv",

    index=False,

    encoding="utf-8-sig"
)


print()
print(
    "สร้าง "
    "era5_monsoon_before_update.csv"
)


# ============================================================
# PREVIEW
# ============================================================

print()
print("=" * 100)
print("PREVIEW")
print("=" * 100)

print(
    all_data.to_string(
        index=False
    )
)


# ============================================================
# MYSQL
# ============================================================

print()
print(
    "กำลังเชื่อมต่อ MySQL..."
)


conn = mysql.connector.connect(
    **DB_CONFIG
)


# ============================================================
# BACKUP + COLUMN
# ============================================================

prepare_database(
    conn
)


# ============================================================
# UPDATE
# ============================================================

update_database(
    conn,
    all_data
)


conn.close()


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("MONSOON SUMMARY")
print("=" * 70)


summary = (

    all_data.groupby(
        [
            "province",
            "monsoon"
        ]
    )

    .size()

    .unstack(
        fill_value=0
    )
)


print(summary)


print()
print("=" * 70)
print("เสร็จเรียบร้อย")
print("=" * 70)

print(
    "Backup table: "
    "weather_data_backup_before_monsoon"
)

print(
    "CSV: "
    "era5_monsoon_before_update.csv"
)

print()
print(
    "หลังจากนี้ควร Train Machine Learning ใหม่ "
    "เนื่องจาก wind_speed ถูกเปลี่ยนวิธีคำนวณ"
)