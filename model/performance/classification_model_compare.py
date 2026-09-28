"""Compare five classifiers on projecta. Run: python classification_model_compare.py
Dependencies: pip install pandas numpy scikit-learn pymysql
Optional DB settings: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.
"""
import csv
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

FEATURES = ['sst', 'chlorophyll_a', 'rainfall', 'wind_speed', 'month', 'year', 'station_id']
LABELS = ['LOW', 'MEDIUM', 'HIGH']
OUTPUT = Path('classification_model_compare_results')


def load_data():
    connection = pymysql.connect(host=os.getenv('DB_HOST', 'localhost'),
                                 port=int(os.getenv('DB_PORT', '3306')),
                                 user=os.getenv('DB_USER', 'root'),
                                 password=os.getenv('DB_PASSWORD', ''),
                                 database=os.getenv('DB_NAME', 'projecta'),
                                 charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    # Mirror the original model: SUM active catch records and AVG active
    # environmental records per station/year/month before merging.
    queries = [
        '''SELECT station_id, year, month, SUM(amount) AS amount
           FROM catch_mackereldata WHERE status=1 AND year BETWEEN 2562 AND 2567
           GROUP BY station_id, year, month''',
        '''SELECT station_id, year, month, AVG(sst) AS sst,
                  AVG(chlorophyll_a) AS chlorophyll_a
           FROM marine_environment WHERE status=1 AND year BETWEEN 2562 AND 2567
           GROUP BY station_id, year, month''',
        '''SELECT station_id, year, month, AVG(rainfall) AS rainfall,
                  AVG(wind_speed) AS wind_speed
           FROM weather_data WHERE status=1 AND year BETWEEN 2562 AND 2567
           GROUP BY station_id, year, month''',
    ]
    try:
        with connection.cursor() as cursor:
            tables = []
            for query in queries:
                cursor.execute(query)
                tables.append(pd.DataFrame(cursor.fetchall()))
    finally:
        connection.close()
    if any(table.empty for table in tables):
        raise ValueError('No active data in one or more source tables for years 2562–2567.')
    keys = ['station_id', 'year', 'month']
    df = tables[0].merge(tables[1], on=keys, how='inner').merge(tables[2], on=keys, how='left')
    for col in FEATURES + ['amount']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    before = len(df)
    df = df.dropna(subset=FEATURES + ['amount']).copy()
    print(f'Joined rows: {before}; complete rows: {len(df)}; dropped: {before-len(df)}')
    duplicates = df.duplicated(['station_id', 'year', 'month'], keep=False)
    if duplicates.any():
        raise ValueError(f'{duplicates.sum()} duplicate station/year/month rows after join; check source table keys before comparison.')
    print('Rows by year:', df.groupby('year').size().to_dict())
    if len(df[df.year < 2567]) != 263 or len(df[df.year == 2567]) != 60:
        raise ValueError('Row counts differ from verified report (263 development, 60 final test). Check SQL joins and data version.')
    # Keep catch query/merge order, as in randomforestclassifier.py. RF's
    # fixed seed still depends on training row order when bootstrap sampling.
    return df


def classifiers():
    return {
        'Random Forest': RandomForestClassifier(n_estimators=300, max_depth=None,
            max_features='sqrt', min_samples_split=2, min_samples_leaf=1,
            class_weight='balanced', random_state=42, n_jobs=-1),
        'Logistic Regression': make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, random_state=42)),
        'Decision Tree': DecisionTreeClassifier(random_state=42, class_weight='balanced'),
        'KNN': make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5)),
        'SVM': make_pipeline(StandardScaler(), SVC(kernel='rbf', C=1.0, gamma='scale')),
    }


def label(amount, low, high):
    return np.where(amount <= low, 'LOW', np.where(amount <= high, 'MEDIUM', 'HIGH'))


def evaluate(train, test, name, estimator, split):
    low, high = np.percentile(train.amount.to_numpy(), [33, 66])
    y_train = label(train.amount.to_numpy(), low, high)
    y_test = label(test.amount.to_numpy(), low, high)
    if len(set(y_train)) < 3:
        raise ValueError(f'{split}: training data lacks one or more classes')
    estimator.fit(train[FEATURES], y_train)
    predicted = estimator.predict(test[FEATURES])
    p, r, f, support = precision_recall_fscore_support(y_test, predicted, labels=LABELS, zero_division=0)
    macro = precision_recall_fscore_support(y_test, predicted, labels=LABELS, average='macro', zero_division=0)
    weighted = precision_recall_fscore_support(y_test, predicted, labels=LABELS, average='weighted', zero_division=0)
    metrics = dict(model=name, split=split, train_rows=len(train), test_rows=len(test),
        low_cut=float(low), high_cut=float(high), accuracy=accuracy_score(y_test, predicted),
        precision=macro[0], recall=macro[1], f1=macro[2], weighted_f1=weighted[2])
    detail = dict(metrics=metrics, confusion_matrix=confusion_matrix(y_test, predicted, labels=LABELS).tolist(),
        class_report={key: dict(precision=float(p[i]), recall=float(r[i]), f1=float(f[i]), support=int(support[i]))
                      for i, key in enumerate(LABELS)})
    return metrics, detail


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    df = load_data()
    folds, details = [], {}
    for year in (2563, 2564, 2565, 2566):
        train, test = df[df.year < year], df[df.year == year]
        if train.empty or test.empty:
            raise ValueError(f'Missing data for fold {year}')
        for name, model in classifiers().items():
            metric, detail = evaluate(train, test, name, model, f'validation_{year}')
            folds.append(metric)
            details[f'{name}/validation_{year}'] = detail
    final = []
    for name, model in classifiers().items():
        metric, detail = evaluate(df[df.year <= 2566], df[df.year == 2567], name, model, 'final_2567')
        final.append(metric)
        details[f'{name}/final_2567'] = detail
    summary = []
    for row in final:
        validation = [x for x in folds if x['model'] == row['model']]
        summary.append(dict(model=row['model'], val_accuracy=np.mean([x['accuracy'] for x in validation]),
            val_precision=np.mean([x['precision'] for x in validation]),
            val_recall=np.mean([x['recall'] for x in validation]),
            val_f1=np.mean([x['f1'] for x in validation]),
            test_accuracy=row['accuracy'], test_precision=row['precision'],
            test_recall=row['recall'], test_f1=row['f1'], test_weighted_f1=row['weighted_f1']))
    OUTPUT.mkdir(exist_ok=True)
    write_csv(OUTPUT / 'model_comparison.csv', summary)
    write_csv(OUTPUT / 'validation_folds.csv', folds)
    write_csv(OUTPUT / 'final_test.csv', final)
    (OUTPUT / 'details.json').write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding='utf-8')
    rf = next(row for row in summary if row['model'] == 'Random Forest')
    print('\nComparison (percent):')
    print(pd.DataFrame(summary).to_string(index=False, formatters={key: lambda x: f'{x:.2%}' for key in summary[0] if key != 'model'}))
    print(f'\nSaved four files in {OUTPUT.resolve()}')
    if abs(rf['test_accuracy'] - 41/60) > 1e-9 or abs(rf['val_f1'] - .4143) > .00015:
        print('WARNING: Random Forest does not reproduce verified baseline (Val F1 41.43%, Test Accuracy 68.33%). Do not use this comparison in thesis until data/protocol is reconciled.')
    else:
        print('Random Forest baseline matches verified Val F1 and final Test Accuracy.')
    print('Note: final test scores are descriptive; select models using development validation, not year 2567 results.')


if __name__ == '__main__':
    main()
