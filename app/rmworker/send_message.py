from pika import BlockingConnection
from rmworker.connection_params import connection_params, queue_input_name


def send_message(message, conn_params=connection_params, queue_name=queue_input_name):
    connection = BlockingConnection(conn_params)

    channel = connection.channel()
    channel.queue_declare(queue=queue_name)
    channel.basic_publish(exchange="", routing_key=queue_name, body=message)
    connection.close()
