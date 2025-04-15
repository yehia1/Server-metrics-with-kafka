from kafka import KafkaConsumer
import mysql.connector
import threading
import re
from datetime import datetime

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="kafka-server-metrics"
)
cursor = db.cursor()

# --- Consumer for 'server-metrics' ---
def consume_server_metrics():
    consumer = KafkaConsumer(
        'server-metrics',
        bootstrap_servers=['127.0.0.1:9092', '127.0.0.1:9093'],
        auto_offset_reset='earliest',
        group_id=None,
        value_deserializer=lambda x: x.decode('utf-8')
    )
    
    print("[server-metrics] Listening...")

    for message in consumer:
        try:
            data = dict(item.strip().split(":") for item in message.value.split(","))
            print(f"[server-metrics] Received: {data}")
            cursor.execute(''' 
                INSERT INTO server_metrics (server_id, cpu, ram, disk) 
                VALUES (%s, %s, %s, %s) 
            ''', ( 
                int(data['id']), 
                int(data['cpu']), 
                int(data['mem']), 
                int(data['disk'])
            )) 
            db.commit()
        except Exception as e:
            print(f"[server-metrics] ❌ Error: {e}")


log_pattern = re.compile(
    r'(?P<ip>\d+\.\d+\.\d+\.\d+) - (?P<user_id>\d+) \[(?P<timestamp>[^\]]+)\] '
    r'(?P<method>GET|POST) (?P<filename>\S+) (?P<status>\d{3}) (?P<size>\d+)'
)

def consume_loadbalancer_logs():
    consumer = KafkaConsumer(
        'loadbalancer-logs',
        bootstrap_servers=['127.0.0.1:9092', '127.0.0.1:9093'],
        auto_offset_reset='latest',
        value_deserializer=lambda x: x.decode('utf-8')
    )
    print("[load-balancer] Listening..")
    for message in consumer:
        raw_log = message.value
        match = log_pattern.match(raw_log)
        if match:
            print(f"[load-balancer] Received: {match.groupdict()}")
            data = match.groupdict()
            # Parse timestamp
            dt_obj = datetime.strptime(data['timestamp'], "%a, %d %b %Y %H:%M:%S %Z")
            cursor.execute('''
                INSERT INTO loadbalancer_logs (ip_address, user_id, timestamp, method, filename, status_code, file_size)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                data['ip'],
                int(data['user_id']),
                dt_obj,
                data['method'],
                data['filename'],
                int(data['status']),
                int(data['size'])
            ))
            db.commit()
        else:
            print("[Logs] Skipped invalid log format")

# --- Run both consumers in separate threads ---
t1 = threading.Thread(target=consume_server_metrics)
t2 = threading.Thread(target=consume_loadbalancer_logs)

t1.start()
t2.start()

t1.join()
t2.join()