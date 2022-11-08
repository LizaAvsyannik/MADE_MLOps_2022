from datetime import datetime

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sensors.python import PythonSensor
from docker.types import Mount
from utils import LOCAL_DATA_DIR, default_args, wait_for_file


with DAG(
    'predict',
    default_args=default_args,
    schedule_interval='@daily',
    start_date=datetime(2022, 11, 1)
) as dag:
    wait_data = PythonSensor(
        task_id='wait-for-predict-data',
        python_callable=wait_for_file,
        op_args=['/opt/airflow/data/raw/{{ ds }}/data.csv'],
        poke_interval=30,
        retries=100
    )

    wait_model = PythonSensor(
        task_id='wait-for-model',
        python_callable=wait_for_file,
        op_args=['/opt/airflow/data/models/{{ var.value.model }}'],
        poke_interval=30,
        retries=100
    )

    preprocess = DockerOperator(
        image='airflow-preprocess',
        command='--input-dir /data/raw/{{ ds }} --output-dir /data/processed/{{ ds }}',
        network_mode='bridge',
        task_id='docker-airflow-predict_preprocess',
        do_xcom_push=False,
        auto_remove=True,
        mounts=[Mount(source=LOCAL_DATA_DIR, target='/data', type='bind')]
        )

    predict = DockerOperator(
        image='airflow-predict',
        command='--input-dir /data/processed/{{ ds }} --model-dir /data/models/{{ var.value.model }} --output-dir /data/predictions/{{ ds }}',
        network_mode='bridge',
        task_id='docker-airflow-predict',
        do_xcom_push=False,
        auto_remove=True,
        mounts=[Mount(source=LOCAL_DATA_DIR, target='/data', type='bind')]
    )

    [wait_data, wait_model] >> preprocess >> predict
