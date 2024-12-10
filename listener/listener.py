from datetime import datetime
import logging
import os
import pika
import json
import time
from clickhouse_driver import Client

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("info")


class RabbitMQListener:
    def __init__(self, rabbit_host, rabbit_port, rabbit_user, rabbit_password, queues, clickhouse_config):
        self.rabbit_host = rabbit_host
        self.rabbit_port = rabbit_port
        self.rabbit_user = rabbit_user
        self.rabbit_password = rabbit_password
        self.queues = queues
        self.connection = None
        self.channel = None
        self.clickhouse_client = Client(**clickhouse_config)  # Настройка ClickHouse клиента

    def connect(self):
        """Подключение к RabbitMQ с повторными попытками."""
        connected = False
        while not connected:
            try:
                credentials = pika.PlainCredentials(self.rabbit_user, self.rabbit_password)
                parameters = pika.ConnectionParameters(
                    host=self.rabbit_host,
                    port=self.rabbit_port,
                    credentials=credentials,
                    heartbeat=60
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                for queue in self.queues:
                    self.channel.queue_declare(queue=queue, durable=True)
                    logger.info(f"Очередь {queue} создана или уже существует")
                connected = True
                logger.info(f"Успешное подключение к RabbitMQ")
            except Exception as e:
                logger.error(f"Не удалось подключиться к RabbitMQ: {e}. Повторная попытка через 5 секунд...")
                time.sleep(5)

    def callback_logs(self, ch, method, properties, body):
        """Обработчик для очереди logs."""
        try:
            message = json.loads(body)
            logger.info(f"[logs] Получено сообщение: {message}")

            created_dt = datetime.strptime(message.get("created_dt"), "%Y-%m-%d %H:%M:%S.%f")
            # Вставляем данные в таблицу logs
            self.clickhouse_client.execute(
                """
                INSERT INTO rabbit_logger.logs (
                    uuid, created_dt, pathname, funcName, lineno, message, exc_text,
                    created, filename, levelname, levelno, module, msecs, msg,
                    name, process, processName, relativeCreated, stack_info,
                    thread, threadName, server_name
                ) VALUES
                """,
                [
                    (
                        message.get("uuid"),
                        created_dt,
                        message.get("pathname"),
                        message.get("funcName"),
                        message.get("lineno"),
                        message.get("message"),
                        message.get("exc_text"),
                        message.get("created"),
                        message.get("filename"),
                        message.get("levelname"),
                        message.get("levelno"),
                        message.get("module"),
                        message.get("msecs"),
                        message.get("msg"),
                        message.get("name"),
                        message.get("process"),
                        message.get("processName"),
                        message.get("relativeCreated"),
                        message.get("stack_info"),
                        message.get("thread"),
                        message.get("threadName"),
                        message.get("server_name"),
                    )
                ]
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"[logs] Ошибка при обработке сообщения: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def callback_apm(self, ch, method, properties, body):
        """Обработчик для очереди apm."""
        try:
            message = json.loads(body)
            logger.info(f"[apm] Получено сообщение: {message}")
            created_dt = datetime.strptime(message.get("created_dt"), "%Y-%m-%d %H:%M:%S")

            # Вставляем данные в таблицу apm
            self.clickhouse_client.execute(
                """
                INSERT INTO rabbit_logger.apm (
                    uuid, func_path, func_name, exec_time,
                    cpu_used, ram_used, created_dt, server_name
                ) VALUES
                """,
                [
                    (
                        message.get("uuid"),
                        message.get("func_path"),
                        message.get("func_name"),
                        message.get("exec_time"),
                        message.get("cpu_used"),
                        message.get("ram_used"),
                        created_dt,
                        message.get("server_name"),
                    )
                ]
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.error(f"[apm] Ошибка при обработке сообщения: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_listening(self):
        """Начало прослушивания очередей."""
        try:
            # Добавляем обработчики для каждой очереди
            self.channel.basic_consume(queue="logs", on_message_callback=self.callback_logs, auto_ack=True)
            self.channel.basic_consume(queue="apm", on_message_callback=self.callback_apm, auto_ack=True)

            logger.info("Слушаю очереди: logs, apm")
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"Ошибка при прослушивании очередей: {e}")
        finally:
            if self.connection and self.connection.is_open:
                self.connection.close()
                logger.info("Соединение с RabbitMQ закрыто")


if __name__ == "__main__":
    RABBIT_HOST = "localhost"
    RABBIT_PORT = int(os.environ.get("RABBIT_PORT", 5672))
    RABBIT_USER = os.environ.get("RABBITMQ_DEFAULT_USER", "user")
    RABBIT_PASSWORD = os.environ.get("RABBITMQ_DEFAULT_PASS", "password")
    QUEUES = ["logs", "apm"]
    CLICKHOUSE_USER=os.environ.get("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD=os.environ.get("CLICKHOUSE_PASSWORD", "")

    CLICKHOUSE_CONFIG = {
        "host": "localhost",
        "port": 9000,
        "user": CLICKHOUSE_USER,
        "password": CLICKHOUSE_PASSWORD,
        "database": "rabbit_logger",
    }

    listener = RabbitMQListener(RABBIT_HOST, RABBIT_PORT, RABBIT_USER, RABBIT_PASSWORD, QUEUES, CLICKHOUSE_CONFIG)
    logger.info("Запускаем Listener...")
    listener.connect()
    listener.start_listening()
