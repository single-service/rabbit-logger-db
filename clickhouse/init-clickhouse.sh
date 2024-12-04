#!/bin/bash

FLAG_FILE="/var/lib/clickhouse/user_initialized.flag"

if [ -f "$FLAG_FILE" ]; then
    echo "Инициализация уже выполнена ранее. Запуск ClickHouse..."
    /usr/bin/clickhouse-server --config-file=/etc/clickhouse-server/config.xml
    exit 0
fi

# Генерация файла users.xml для временного пользователя default
cat <<EOF > /etc/clickhouse-server/users.xml
<clickhouse>
    <profiles>
        <default>
            <max_memory_usage>10000000000</max_memory_usage>
            <load_balancing>random</load_balancing>
        </default>
    </profiles>

    <users>
        <default>
            <password></password>
            <networks>
                <ip>::/0</ip>
            </networks>
            <profile>default</profile>
            <quota>default</quota>
            <access_management>1</access_management>
        </default>
    </users>
</clickhouse>
EOF

# Запуск ClickHouse
/usr/bin/clickhouse-server --config-file=/etc/clickhouse-server/config.xml &
CLICKHOUSE_PID=$!

# Ожидание запуска ClickHouse
echo "Ожидание запуска ClickHouse..."
until clickhouse-client --query="SELECT 1" >/dev/null 2>&1; do
    echo "ClickHouse is not ready yet. Retrying in 1 second..."
    sleep 1
done

# Создание постоянного пользователя
echo "Создание постоянного пользователя ClickHouse..."
clickhouse-client --query="CREATE USER IF NOT EXISTS '${CLICKHOUSE_USER}' IDENTIFIED BY '${CLICKHOUSE_PASSWORD}';" || echo "Ошибка создания пользователя."
clickhouse-client --query="GRANT ALL ON *.* TO '${CLICKHOUSE_USER}';" || echo "Ошибка предоставления привилегий."

# Выполнение SQL-скрипта
echo "Выполнение schema.sql..."
cat /docker-entrypoint-initdb.d/schema.sql | clickhouse-client --user="${CLICKHOUSE_USER}" --password="${CLICKHOUSE_PASSWORD}" --multiquery || echo "Ошибка выполнения schema.sql."

# Удаление временного пользователя default из users.xml
echo "Удаление временного пользователя default..."
cat <<EOF > /etc/clickhouse-server/users.xml
<clickhouse>
    <profiles>
        <default>
            <max_memory_usage>10000000000</max_memory_usage>
            <load_balancing>random</load_balancing>
        </default>
    </profiles>

    <users>
        <${CLICKHOUSE_USER}>
            <password>${CLICKHOUSE_PASSWORD}</password>
            <networks>
                <ip>::/0</ip>
            </networks>
            <profile>default</profile>
            <quota>default</quota>
            <access_management>1</access_management>
        </${CLICKHOUSE_USER}>
    </users>
</clickhouse>
EOF

# Перезапуск ClickHouse для применения новой конфигурации
echo "Перезапуск ClickHouse для удаления временного пользователя..."
# kill $CLICKHOUSE_PID
# wait $CLICKHOUSE_PID

/usr/bin/clickhouse-server --config-file=/etc/clickhouse-server/config.xml &
CLICKHOUSE_PID=$!

# Устанавливаем флаг, чтобы повторная инициализация не выполнялась
echo "Инициализация завершена. Устанавливаем флаг."
touch "$FLAG_FILE"

# Завершаем процесс ClickHouse, если скрипт завершился
trap "kill $CLICKHOUSE_PID; wait $CLICKHOUSE_PID" EXIT
