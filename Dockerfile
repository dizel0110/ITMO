FROM apache/airflow:2.9.0

RUN pip install pandas dvc[s3] loguru==0.5.3 scikit-learn~=1.4.1 \
    apache-airflow==2.9.0 joblib==1.4.0 clearml==1.16.2 \
