from datetime import datetime
import logging
import os
import json

import socket
from clickhouse_driver import Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class UDPListener:
    def __init__(self, udp_host, udp_port, clickhouse_config):
        self.udp_host = udp_host
        self.udp_port = udp_port
        self.clickhouse_client = Client(**clickhouse_config)

        # Создаем UDP сокет для приёма
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.udp_host, self.udp_port))
        logging.info(f"UDP Listener запущен на {self.udp_host}:{self.udp_port}")

    def listen(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(65535)  # Максимальный размер датаграммы
                message = json.loads(data.decode("utf-8"))
                logging.info(f"Получено сообщение от {addr}: {message}")

                # Определяем, это логи или APM данные, исходя из содержимого.
                # Можно по полю или по договоренности. Предположим, что наличие полей func_name, func_path - это APM,
                # а их отсутствие - обычный лог.
                if "exec_time" in message:
                    self.process_apm(message)
                else:
                    self.process_logs(message)

            except Exception as e:
                logging.error(f"Ошибка при обработке датаграммы: {e}")

    def process_logs(self, message):      
        created_dt_str = message.get("created_dt")
        # Если в логе нет миллисекунд, можно использовать другой формат
        # Предположим, есть миллисекунды:
        if '.' in created_dt_str:
            created_dt = datetime.strptime(created_dt_str, "%Y-%m-%d %H:%M:%S.%f")
        else:
            created_dt = datetime.strptime(created_dt_str, "%Y-%m-%d %H:%M:%S")

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

    def process_apm(self, message):
        created_dt_str = message.get("created_dt")
        created_dt = datetime.strptime(created_dt_str, "%Y-%m-%d %H:%M:%S.%f")

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
                    message.get("cpu_used"),  # Если эти поля не обязательны, можно поставить None
                    message.get("ram_used"),
                    created_dt,
                    message.get("server_name"),
                )
            ]
        )

if __name__ == "__main__":
    UDP_HOST = "0.0.0.0"
    UDP_PORT = 9999

    CLICKHOUSE_USER = os.environ.get("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "")

    CLICKHOUSE_CONFIG = {
        "host": "localhost",
        "port": 9000,
        "user": CLICKHOUSE_USER,
        "password": CLICKHOUSE_PASSWORD,
        "database": "rabbit_logger",
    }

    listener = UDPListener(UDP_HOST, UDP_PORT, CLICKHOUSE_CONFIG)
    listener.listen()
