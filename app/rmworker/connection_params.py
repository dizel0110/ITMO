from pika import ConnectionParameters, PlainCredentials
from decouple import config

user = config('RABBITMQ_USER')
password = config('RABBITMQ_PASSWORD')

connection_params = ConnectionParameters(
    host='rabbitmq',
    port=5672,
    virtual_host='/',
    credentials=PlainCredentials(
        username=user,
        password=password,
    ),
    heartbeat=30,
    blocked_connection_timeout=2,
)

queue_input_name = 'input_image_queue'
queue_result_name = 'result_image_queue'
