# -*- coding: utf-8 -*-

import os
import pandas as pd
import mysql.connector

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.decomposition import PCA

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

from scipy.stats import f_oneway


# DATABASE CONNECTION
conn = mysql.connector.connect(
    host=os.getenv("PROJECTA_DB_HOST", "127.0.0.1"),
    database=os.getenv("PROJECTA_DB_NAME", "projecta"),
    user=os.getenv("PROJECTA_DB_USER", "root"),
    password=os.getenv("PROJECTA_DB_PASSWORD", ""),
    port=int(os.getenv("PROJECTA_DB_PORT", "3306")),
    charset="utf8mb4",
    use_unicode=True,
)


# OUTPUT
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

ELBOW_GRAPH = os.path.join(
    OUTPUT_DIR,
    "kmeans_evaluation.png"
)

PCA_GRAPH = os.path.join(
    OUTPUT_DIR,
    "kmeans_pca.png"
)


# LOAD DATA
sql = """
SELECT
    station_id,
    year,
    month,
    equipment_id,

    SUM(amount) AS amount,

    AVG(sst) AS sst,
    AVG(chlorophyll_a) AS chlorophyll_a,
    AVG(rainfall) AS rainfall,
    AVG(wind_speed) AS wind_speed,
    AVG(sea_level_pressure) AS sea_level_pressure

FROM dataset_ml

GROUP BY
    station_id,
    year,
    month,
    equipment_id

ORDER BY
    year,
    month,
    station_id,
    equipment_id
"""

df = pd.read_sql(sql, conn)

print("\n=== ข้อมูลจาก dataset_ml ===")
print("จำนวนข้อมูล =", len(df))
print(df.head())


# CLEAN DATA
features = [
    "sst",
    "chlorophyll_a",
    "rainfall",
    "sea_level_pressure"
]

df = df.dropna(
    subset=features
).copy()


# AREA-LEVEL DATA
df_area = (
    df.groupby(
        [
            "station_id",
            "year",
            "month"
        ]
    )
    .agg({
        "sst": "mean",
        "chlorophyll_a": "mean",
        "rainfall": "mean",
        "sea_level_pressure": "mean",
        "amount": "mean"
    })
    .reset_index()
)


print("\n=== ข้อมูลพื้นที่สำหรับ Clustering ===")
print(
    "จำนวน Area Records =",
    len(df_area)
)


# CHECK DATA
if len(df_area) < 3:
    raise RuntimeError(
        "ข้อมูลไม่เพียงพอสำหรับทำ K-Means"
    )


# K-MEANS FEATURES
X = df_area[
    features
].copy()

# STANDARDIZATION
scaler = StandardScaler()

X_scaled = scaler.fit_transform(
    X
)


# FIND BEST K
best_k = None
best_score = -1

wcss = []
silhouette_scores = []
dbi_scores = []

max_k = min(
    8,
    len(df_area) - 1
)

print("\n=== ทดสอบจำนวน Cluster ===")


for k in range(
    2,
    max_k + 1
):

    kmeans_test = KMeans(
        n_clusters=k,
        random_state=42,
        n_init=20
    )

    labels = kmeans_test.fit_predict(
        X_scaled
    )

    wcss.append(
        kmeans_test.inertia_
    )

    score = silhouette_score(
        X_scaled,
        labels
    )

    dbi = davies_bouldin_score(
        X_scaled,
        labels
    )

    silhouette_scores.append(
        score
    )

    dbi_scores.append(
        dbi
    )

    print(
        f"K = {k} | "
        f"WCSS = {kmeans_test.inertia_:.2f} | "
        f"Silhouette = {score:.4f} | "
        f"DBI = {dbi:.4f}"
    )

    if score > best_score:
        best_score = score
        best_k = k


print("\n================================")
print("Best K =", best_k)
print(
    "Best Silhouette Score =",
    round(best_score, 4)
)
print("================================")


# EVALUATION GRAPH
fig, axs = plt.subplots(
    1,
    3,
    figsize=(18, 5)
)


# Elbow
axs[0].plot(
    range(2, max_k + 1),
    wcss,
    marker="o"
)

axs[0].set_title(
    "Elbow Method"
)

axs[0].set_xlabel(
    "Number of Clusters (K)"
)

axs[0].set_ylabel(
    "WCSS (Inertia)"
)

axs[0].grid(True)


# Silhouette
axs[1].plot(
    range(2, max_k + 1),
    silhouette_scores,
    marker="o"
)

axs[1].set_title(
    "Silhouette Score"
)

axs[1].set_xlabel(
    "Number of Clusters (K)"
)

axs[1].set_ylabel(
    "Score"
)

axs[1].grid(True)


# DBI
axs[2].plot(
    range(2, max_k + 1),
    dbi_scores,
    marker="o"
)

axs[2].set_title(
    "Davies-Bouldin Index"
)

axs[2].set_xlabel(
    "Number of Clusters (K)"
)

axs[2].set_ylabel(
    "Index Value"
)

axs[2].grid(True)


plt.tight_layout()

plt.savefig(
    ELBOW_GRAPH,
    dpi=150,
    bbox_inches="tight"
)

plt.close()


# FINAL K-MEANS
kmeans = KMeans(
    n_clusters=best_k,
    random_state=42,
    n_init=20
)

df_area["cluster"] = (
    kmeans.fit_predict(
        X_scaled
    )
)


# SORT CLUSTER BY AMOUNT
cluster_amount = (
    df_area
    .groupby("cluster")["amount"]
    .mean()
    .sort_values()
)


mapping = {
    old_cluster: new_cluster
    for new_cluster, old_cluster
    in enumerate(
        cluster_amount.index
    )
}


df_area["cluster"] = (
    df_area["cluster"]
    .map(mapping)
)


# PCA
pca = PCA(
    n_components=2
)

pca_components = (
    pca.fit_transform(
        X_scaled
    )
)


df_area["PC1"] = (
    pca_components[:, 0]
)

df_area["PC2"] = (
    pca_components[:, 1]
)


variance_ratio = (
    pca.explained_variance_ratio_
    * 100
)


print(
    "\n=== PCA Explained Variance ==="
)

print(
    f"PC1 = {variance_ratio[0]:.2f}%"
)

print(
    f"PC2 = {variance_ratio[1]:.2f}%"
)

print(
    f"รวม = {variance_ratio.sum():.2f}%"
)


# PCA GRAPH
plt.figure(
    figsize=(8, 6)
)

for cluster in sorted(
    df_area["cluster"].unique()
):

    subset = df_area[
        df_area["cluster"] == cluster
    ]

    plt.scatter(
        subset["PC1"],
        subset["PC2"],
        label=f"Cluster {cluster}",
        s=80,
        alpha=0.8
    )


plt.title(
    f"PCA Scatter Plot of Area Clusters (K={best_k})"
)

plt.xlabel(
    f"PC1 ({variance_ratio[0]:.2f}%)"
)

plt.ylabel(
    f"PC2 ({variance_ratio[1]:.2f}%)"
)

plt.legend(
    title="Cluster"
)

plt.grid(
    True,
    linestyle="--",
    alpha=0.5
)

plt.tight_layout()

plt.savefig(
    PCA_GRAPH,
    dpi=150,
    bbox_inches="tight"
)

plt.close()


# =========================================================
# CLUSTER SUMMARY
# =========================================================

print(
    "\n=== Cluster Summary ==="
)

summary = (
    df_area
    .groupby("cluster")
    .agg({
        "amount": "mean",
        "sst": "mean",
        "chlorophyll_a": "mean",
        "rainfall": "mean",
        "sea_level_pressure": "mean",
    })
)

print(
    summary.to_string()
)


# ANOVA
print(
    "\n========== ANOVA Test =========="
)


for var in features:

    groups = [
        group[var].values
        for _, group
        in df_area.groupby("cluster")
    ]

    if len(groups) >= 2:

        F, p = f_oneway(
            *groups
        )

        print(
            f"{var:20s} "
            f"F = {F:10.3f}  "
            f"p-value = {p:.5f}"
        )


# UPDATE DATABASE
cursor = conn.cursor()

for _, row in df_area.iterrows():

    cursor.execute(
        """
        UPDATE dataset_ml
        SET cluster = %s
        WHERE station_id = %s
          AND year = %s
          AND month = %s
        """,
        (
            int(row["cluster"]),
            int(row["station_id"]),
            int(row["year"]),
            int(row["month"])
        )
    )


conn.commit()

print(
    "\nบันทึก Cluster กลับลง database เรียบร้อย"
)

print(
    "Evaluation graph:",
    ELBOW_GRAPH
)

print(                                  
    "PCA graph:",
    PCA_GRAPH
)

print(
    "Finish"
)


# CLOSE DATABASE
cursor.close()
conn.close()