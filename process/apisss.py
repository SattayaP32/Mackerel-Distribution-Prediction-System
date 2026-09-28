import requests
import pandas as pd
import mysql.connector

# =========================
# พิกัดสถานี
# =========================

lat = 13.45
lon = 100.70

station_id = 5

start_date = "2026-01-01"
end_date = "2026-08-31"


# =========================
# Open-Meteo Historical API
# Sea Level Pressure
# =========================

url = (
    "https://archive-api.open-meteo.com/v1/archive"
    f"?latitude={lat}"
    f"&longitude={lon}"
    f"&start_date={start_date}"
    f"&end_date={end_date}"
    "&hourly=pressure_msl"
    "&timezone=Asia/Bangkok"
    "&models=era5"
)

print("กำลังโหลดข้อมูล Sea Level Pressure...")
print(url)


# =========================
# Request
# =========================

response = requests.get(
    url,
    timeout=60
)

print("HTTP Status:", response.status_code)

response.raise_for_status()

data = response.json()


# =========================
# ตรวจสอบข้อมูล
# =========================

if "hourly" not in data:
    print(data)
    raise Exception("ไม่พบข้อมูล hourly จาก Open-Meteo")


print("โหลดข้อมูลสำเร็จ")


# =========================
# DataFrame
# =========================

df = pd.DataFrame({
    "time": data["hourly"]["time"],
    "sea_level_pressure": data["hourly"]["pressure_msl"]
})


print("\nข้อมูลตัวอย่าง")
print(df.head())

print("\nจำนวนข้อมูล:", len(df))


# =========================
# แปลงเวลา
# =========================

df["time"] = pd.to_datetime(
    df["time"]
)

df["sea_level_pressure"] = pd.to_numeric(
    df["sea_level_pressure"],
    errors="coerce"
)


# =========================
# ลบข้อมูลที่ไม่มีค่า
# =========================

df = df.dropna(
    subset=["sea_level_pressure"]
)


# =========================
# เพิ่มปี / เดือน
# =========================

df["year"] = df["time"].dt.year
df["month"] = df["time"].dt.month


# =========================
# ค่าเฉลี่ย Sea Level Pressure รายเดือน
# =========================

monthly = (
    df.groupby(
        ["year", "month"]
    )["sea_level_pressure"]
    .mean()
    .reset_index()
)


print("\nSea Level Pressure รายเดือน")
print(monthly)


# =========================
# เชื่อม MySQL
# =========================

conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="",
    database="projecta",
    use_pure=True
)

cursor = conn.cursor()


# =========================
# UPDATE weather_data
# =========================

sql = """
UPDATE weather_data
SET sea_level_pressure = %s
WHERE station_id = %s
AND year = %s
AND month = %s
"""


success = 0


for _, row in monthly.iterrows():

    # Open-Meteo = ค.ศ.
    # Database = พ.ศ.
    db_year = int(row["year"]) + 543

    values = (
        float(row["sea_level_pressure"]),
        station_id,
        db_year,
        int(row["month"])
    )

    print(values)

    cursor.execute(
        sql,
        values
    )

    print(
        "rowcount =",
        cursor.rowcount
    )

    if cursor.rowcount > 0:
        success += cursor.rowcount


# =========================
# Commit
# =========================

conn.commit()

print(
    f"\nอัปเดต Sea Level Pressure สำเร็จ "
    f"{success} เดือน"
)


cursor.close()
conn.close()