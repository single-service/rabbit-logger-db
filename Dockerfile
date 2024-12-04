FROM python:3.9-slim AS base

# Установка общих зависимостей
RUN apt-get update && apt-get install -y \
    supervisor \
    nginx \
    default-jre-headless \
    curl wget \
    rabbitmq-server \
    cron \
    && apt-get clean

# ==========================
# Конфигурация Listener
# ==========================
WORKDIR /app
COPY listener/listener.py /app/
COPY listener/requirements.txt /app/
COPY clean_logs.py /app/
RUN pip install --no-cache-dir -r requirements.txt

# ==========================
# Настройка Cron
# ==========================
# Копируем cron задание
COPY cronjobs /etc/cron.d/clean_logs
# Устанавливаем права на cron задание
RUN chmod 0644 /etc/cron.d/clean_logs
# Применяем cron задание
RUN crontab /etc/cron.d/clean_logs
# Создаем файл логов для cron
RUN touch /var/log/cron.log

# ==========================
# Настройка Supervisor
# ==========================
RUN mkdir -p /etc/supervisor/conf.d
COPY supervisord.conf /etc/supervisor/supervisord.conf

# ==========================
# Установка ClickHouse
# ==========================
FROM yandex/clickhouse-server:latest AS clickhouse
COPY clickhouse/schema.sql /docker-entrypoint-initdb.d/schema.sql

# ==========================
# Финальная сборка
# ==========================
FROM base

# Создание директории для инициализационных файлов
RUN mkdir -p /docker-entrypoint-initdb.d

# Копируем ClickHouse
COPY --from=clickhouse /usr/bin/clickhouse-server /usr/bin/clickhouse-server
COPY --from=clickhouse /usr/bin/clickhouse-client /usr/bin/clickhouse-client
COPY --from=clickhouse /etc/clickhouse-server /etc/clickhouse-server
COPY --from=clickhouse /var/lib/clickhouse /var/lib/clickhouse
COPY --from=clickhouse /docker-entrypoint-initdb.d /docker-entrypoint-initdb.d

# Копируем init-clickhouse.sh
COPY clickhouse/init-clickhouse.sh /usr/local/bin/init-clickhouse.sh

# Делаем скрипт исполняемым
RUN chmod +x /usr/local/bin/init-clickhouse.sh

# Указываем тома для сохранения данных
VOLUME /var/lib/clickhouse
VOLUME /var/lib/rabbitmq

# Указываем Supervisor как команду запуска
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
