"""Run one-factor-at-a-time thesis experiments against local projecta MySQL.
Install: py -m pip install pandas numpy scikit-learn pymysql
Run: py chapter43_run_on_my_pc.py
If using password: set PROJECTA_DB_PASSWORD=... (Windows CMD) before run.
Output: chapter43_results_local.zip. Does not change MySQL or production model.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import numpy as np
import pandas as pd
import pymysql
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_recall_fscore_support,
                             classification_report, confusion_matrix)
KEY = ['station_id', 'year', 'month']
BASE = ['sst', 'chlorophyll_a', 'rainfall', 'wind_speed', 'month', 'year', 'station_id']
LABELS = ['LOW', 'MEDIUM', 'HIGH']
RF = dict(n_estimators=300, max_depth=None, min_samples_split=2,
          min_samples_leaf=1, class_weight='balanced', random_state=42, n_jobs=-1)
FOLDS = [(2562, 2563), (2562, 2564), (2562, 2565), (2562, 2566)]


def labels(values, cuts):
    return np.select([values <= cuts[0], values <= cuts[1]], LABELS[:2], default=LABELS[2])


def model(name, params=None):
    if name == 'RF': return RandomForestClassifier(**(RF if params is None else params))
    raise ValueError(name)


def score(actual, predicted):
    p,r,f,_ = precision_recall_fscore_support(actual,predicted, labels=LABELS, average='macro', zero_division=0)
    return dict(accuracy=accuracy_score(actual,predicted), macro_precision=p, macro_recall=r,
                macro_f1=f, balanced_accuracy=balanced_accuracy_score(actual,predicted))


def evaluate(df, train, valid, quantiles, features, name='RF', params=None):
    cuts = train.amount.quantile(list(quantiles)).to_numpy()
    if cuts[0] >= cuts[1]: raise ValueError('Identical class thresholds')
    ytrain, yvalid = labels(train.amount, cuts), labels(valid.amount, cuts)
    fitted = model(name, params).fit(train[features], ytrain)
    predicted = fitted.predict(valid[features])
    return score(yvalid, predicted), fitted, cuts, yvalid, predicted


def validation(df, options):
    rows, folds = [], []
    for option in options:
        fold_rows=[]
        for start, end in FOLDS:
            train=df[df.year.between(start,end-1)]
            valid=df[df.year.eq(end)]
            if len(train)==0 or len(valid)==0: continue
            metric,*_ = evaluate(df,train,valid,option['threshold'],option['features'],option['model'],option.get('params'))
            item=dict(id=option['id'], validation_year=end, train_rows=len(train), validation_rows=len(valid), **metric)
            fold_rows.append(item)
            folds.append(item)
        if not fold_rows: raise ValueError('No validation folds available')
        summary=dict(id=option['id'], folds=len(fold_rows), **{k:float(np.mean([r[k] for r in fold_rows])) for k in
          ['accuracy','macro_precision','macro_recall','macro_f1','balanced_accuracy']})
        rows.append(summary)
    return pd.DataFrame(rows), pd.DataFrame(folds)


def select(frame):
    return frame.sort_values(['macro_f1','balanced_accuracy','accuracy','id'],
                             ascending=[False,False,False,True]).iloc[0]['id']



def load_mysql(args):
    conn=pymysql.connect(host=args.host,port=args.port,user=args.user,
        password=os.environ.get(args.password_env,''),database=args.database,
        charset='utf8mb4',cursorclass=pymysql.cursors.DictCursor)
    queries={
      'catch':"SELECT station_id,year,month,SUM(amount) amount FROM catch_mackereldata WHERE status=1 AND year BETWEEN 2562 AND 2567 GROUP BY station_id,year,month",
      'marine':"SELECT station_id,year,month,AVG(sst) sst,AVG(chlorophyll_a) chlorophyll_a,AVG(sss) sss FROM marine_environment WHERE status=1 AND year BETWEEN 2562 AND 2567 GROUP BY station_id,year,month",
      'weather':"SELECT station_id,year,month,AVG(rainfall) rainfall,AVG(wind_speed) wind_speed,AVG(sea_level_pressure) sea_level_pressure,AVG(air_temperature) air_temperature,AVG(wind_direction) wind_direction FROM weather_data WHERE status=1 AND year BETWEEN 2562 AND 2567 GROUP BY station_id,year,month"}
    tables={}
    try:
        with conn.cursor() as cursor:
            for name,sql in queries.items():
                cursor.execute(sql)
                tables[name]=pd.DataFrame(cursor.fetchall())
    finally: conn.close()
    if any(t.empty for t in tables.values()): raise RuntimeError('One or more source tables have no active rows')
    for t in tables.values():
        for col in t.columns: t[col]=pd.to_numeric(t[col],errors='coerce')
    df=tables['catch'].merge(tables['marine'],on=KEY,how='inner').merge(tables['weather'],on=KEY,how='left')
    df=df.dropna(subset=BASE+['amount']).sort_values(KEY).reset_index(drop=True)
    if df.empty: raise RuntimeError('No complete merged rows')
    return df

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--host',default='localhost'); ap.add_argument('--port',type=int,default=3306); ap.add_argument('--user',default='root'); ap.add_argument('--database',default='projecta'); ap.add_argument('--out',default='chapter43_results_local'); ap.add_argument('--password-env',default='PROJECTA_DB_PASSWORD')
    args=ap.parse_args(); out=Path(args.out); out.mkdir(exist_ok=True,parents=True)
    df=load_mysql(args)
    if not all((df.year==year).any() for year in range(2562,2568)):
        raise RuntimeError('Missing data in one or more years 2562–2567')
    train=df[df.year.between(2562,2566)]; test=df[df.year.eq(2567)]
    original=dict(id='ORIGINAL',threshold=(.33,.66),features=BASE,model='RF')
    core=['sst','chlorophyll_a','rainfall','wind_speed']
    threshold=[original]+[dict(original,id=f'T{int(a*100)}_{int(b*100)}',threshold=(a,b)) for a,b in
                          [(.25,.75),(.30,.70),(.35,.65),(.40,.60)]]
    feature=[dict(original,id='CORE4',features=core),original]
    feature += [dict(original,id='CORE4_PLUS_'+x.upper(),features=core+[x]) for x in
                ['month','year','station_id','sss','sea_level_pressure','air_temperature','wind_direction']]
    feature += [dict(original,id='ORIGINAL_PLUS_'+x.upper(),features=BASE+[x]) for x in
                ['sss','sea_level_pressure','air_temperature','wind_direction']]
    params=[original]+[dict(original,id=id,params=setting) for id,setting in [
        ('P100',dict(RF,n_estimators=100)),('P500',dict(RF,n_estimators=500)),
        ('DEPTH5',dict(RF,max_depth=5)),('DEPTH10',dict(RF,max_depth=10)),
        ('LEAF2',dict(RF,min_samples_leaf=2)),('LEAF4',dict(RF,min_samples_leaf=4)),
        ('SPLIT5',dict(RF,min_samples_split=5)),('MAXFEATURES_ALL',dict(RF,max_features=None)),
        ('WEIGHT_NONE',dict(RF,class_weight=None))]]
    overview=[]
    for category,options in [('threshold',threshold),('features',feature),('parameters',params)]:
        options=[o for o in options if not df[o['features']].isna().any().any()]
        dev,folds=validation(df,options)
        finals=[]
        for o in options:
            scores,fit,cuts,actual,pred=evaluate(df,train,test,o['threshold'],o['features'],o['model'],o.get('params'))
            finals.append(dict(id=o['id'],test_rows=len(test),low_cut=cuts[0],high_cut=cuts[1],**scores))
            if o['id']=='ORIGINAL' and category=='threshold':
                pd.DataFrame(classification_report(actual,pred,labels=LABELS,output_dict=True,zero_division=0)).T.to_csv(out/'original_class_report.csv')
                pd.DataFrame(confusion_matrix(actual,pred,labels=LABELS),index=LABELS,columns=LABELS).to_csv(out/'original_confusion.csv')
                pd.DataFrame({'feature':BASE,'importance':fit.feature_importances_}).sort_values('importance',ascending=False).to_csv(out/'original_importance.csv',index=False)
                result=test[['station_id','year','month','amount']].copy(); result['actual']=actual; result['predicted']=pred
                proba=fit.predict_proba(test[BASE]); result['confidence']=proba.max(axis=1)
                for label in LABELS: result['prob_'+label]=proba[:,list(fit.classes_).index(label)]
                result.to_csv(out/'original_predictions.csv',index=False)
        dev=dev.rename(columns={m:'validation_'+m for m in ['accuracy','macro_precision','macro_recall','macro_f1','balanced_accuracy']})
        final=pd.DataFrame(finals).rename(columns={m:'test_'+m for m in ['accuracy','macro_precision','macro_recall','macro_f1','balanced_accuracy']})
        merged=dev.merge(final,on='id')
        merged.insert(1,'features',merged.id.map({o['id']:', '.join(o['features']) for o in options}))
        merged.to_csv(out/(category+'.csv'),index=False)
        folds.to_csv(out/(category+'_folds.csv'),index=False)
        overview.append({'category':category,'options':len(options),'best_validation_macro_f1':merged.loc[merged.validation_macro_f1.idxmax(),'id']})
    (out/'method.json').write_text(json.dumps({'train_rows':len(train),'test_rows':len(test),'rows_per_year':df.year.value_counts().sort_index().to_dict(),
       'validation_years':[2563,2564,2565,2566], 'threshold_label_note':'Threshold comparisons change label definition.',
       'principle':'Each category starts at the original model; no category carries a selected option into the next.',
       'overview':overview},ensure_ascii=False,indent=2),encoding='utf-8')
    meta={'python':sys.version.split()[0],'sklearn':sklearn.__version__,'numpy':np.__version__,'pandas':pd.__version__, 'database':args.database,'host':args.host, 'rows_by_year':{str(k):int(v) for k,v in df.year.value_counts().sort_index().items()}, 'note':'test 2567 is descriptive; choose configurations using validation only'}
    (out/'runtime.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    with ZipFile(str(out)+'.zip','w',ZIP_DEFLATED) as zipout:
        for file in sorted(out.glob('*')): zipout.write(file,file.name)
    print('DONE:', str(out)+'.zip')
    print('Baseline and experiments:', json.dumps(overview,ensure_ascii=False))

if __name__=='__main__': main()
