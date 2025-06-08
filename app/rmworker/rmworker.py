import json
import os
import logging
from pika import BlockingConnection
from rembg import remove, new_session
from rmworker.connection_params import queue_input_name, queue_result_name


def process_image(message):
    data = message
    user_id = data['user_id']
    filename = data['filename']
    output_path = data['output_path']
    input_file_path = data['input_file_path']
    output_file_path = data['output_file_path']
    try:
        os.makedirs(output_path, mode=777, exist_ok=True)
        with open(input_file_path, 'rb') as file:
            input_image = file.read()
        output_image = remove(input_image, session=new_session('u2netp'))
        with open(output_file_path, 'wb') as output_file:
            output_file.write(output_image)
        return f"Background removed from image {filename}."
    except Exception as error:
        return f"{input_file_path} Error processing image: {str(error)}"


def callback(channel, method, properties, body):
    message = json.loads(body)
    logging.info(f"Received message: {message}")

    result = process_image(message)

    channel.basic_publish(exchange='', routing_key='result_image_queue', body=result.encode())
    logging.info(f"Sent result: {result}")

    channel.basic_ack(
        delivery_tag=method.delivery_tag
    )


def worker_run(
    connection_params,
    queue_input: str = queue_input_name,
    queue_result: str = queue_result_name,
):
    connection = BlockingConnection(connection_params)

    channel = connection.channel()
    channel.queue_declare(queue=queue_input)
    channel.queue_declare(queue=queue_result)
    channel.basic_consume(queue=queue_input, on_message_callback=callback)
    logging.info("Waiting for messages. To exit, press Ctrl+C")
    channel.start_consuming()
