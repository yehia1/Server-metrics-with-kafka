# Servers Metrics & Logs
## Project Overview:
We have a cluste of 10 servers hosting a cloud storage website where users can upload and store different types of files. Beside these 10 servers we have a load balancer that acts as the main gateway for our website. We have deployed agents to these 10 servers and load balancer to collect metrics and logs.

Design a **Multi Node Kafka Cluster** where you would have two topics. One topic for the agents of the 10 servers which monitor resources consumption, the other topic for the agent of the load balancer which monitor logs. We have provided you with a java program which should simulate the agents sending data to the two topics.

After that, you need to build a consumers - in whatever language you would prefer- for the metrics that should send them to a relational database. For the logs, write a spark application that consumes them and calculate a moving windows count of every operation (no of successful GET operations, no of successful POST operations, no of failed GET operations, no of failed POST operations) every 5 mins and store the result into a hadoop system.

## Resources:
Java program to simulate the agents. You just need to install maven on your system and then run ```mvn exec:java``` to run the program

# Steps
---

## ✅ Phase 1: Kafka Cluster Setup (Multi-Broker)

### Step 1: Pre-requisites
- Installed Java JDK 11+
- Downloaded and extracted Kafka 3.6.0
- Confirmed environment variable setup

### Step 2: Start Zookeeper
```cmd
bin\windows\zookeeper-server-start.bat config\zookeeper.properties
```

### Step 3: Configure Multiple Kafka Brokers
Created:
- `server-1.properties` (port 9092)
- `server-2.properties` (port 9093)

Each with unique `broker.id`, `listeners`, and `log.dirs`.

### Step 4: Start Kafka Brokers
```cmd
bin\windows\kafka-server-start.bat config\server-1.properties
bin\windows\kafka-server-start.bat config\server-2.properties
```

### Step 5: Verify Brokers
```cmd
bin\windows\zookeeper-shell.bat localhost:2181 ls /brokers/ids
```
✅ Expected output: `[1, 2]`

### Step 6: Create Topics
```cmd
kafka-topics.bat --create --topic server-metrics --bootstrap-server localhost:9092 --partitions 2 --replication-factor 1
kafka-topics.bat --create --topic loadbalancer-logs --bootstrap-server localhost:9092 --partitions 2 --replication-factor 1
```

---

## ✅ Phase 2: Java Agent Simulation Setup

### Files Provided:
- `App.java` – Main launcher
- `Server.java` – Sends server metrics
- `Balancer.java` – Sends load balancer logs

### Setup:
- Created Maven project with `pom.xml`
- Added dependencies for Kafka clients
- Set topic names in Java: `server-metrics` and `loadbalancer-logs`

### Run the App:
```bash
mvn clean compile
mvn exec:java -Dexec.mainClass="com.monitoring.device.App"
```

---

## ✅ Phase 3: Python Kafka Consumer.

[`test_kafka_consumer.py`](test_kafka_consumer.py)

### Stack:
- Python
- kafka-python
- MySQL

[Schema](Schema.sql)

### Behavior:
- Connects to `server-metrics`
- Parses JSON messages
- Inserts metrics into `server_metrics` MySQL table
- Inserts logs into `loadbalancer_logs` MySQL table
- Using threads to add both metrics and logs into db

### Issues Solved:
- Fixed `NoBrokersAvailable` error by confirming broker ports
- Verified topic with Kafka console tools
- Debugged JSON format with escaped strings using regular expressions


## Phase 4 – Docker Environment Setup

This phase sets up the infrastructure required for the pipeline using Docker and Docker Compose.

### 🧱 Services in `docker-compose.yml`
[docker-compose file](docker-compose.yaml)

#### 🔹 Kafka Cluster
- **Zookeeper**
- **Kafka Broker 1**
- **Kafka Broker 2**

Each kafka broker got inside and outside ips to connect
depending on the zookepeer in the port 2181

#### 🔹 Hadoop Cluster
- **NameNode**
- **DataNode**

Each One got it's own volume 
```yaml
volumes:
  hadoop_namenode:
  hadoop_datanode:
```

Connecting over the inside ip 8080 and accessible to the system in localhost:9864

#### 🔹 Spark Cluster
- **Spark Master**
- **Spark Worker(s)**

#### 🔹 Additional Services
- **MySQL** (Optional for metrics ingestion)

If want create the db inside docker with same network and running schema.sql after copying it inside the volume 
```yaml
volumes:
    mysql_data
```

### 🧩 Docker Compose Network

Ensure all containers are in the same Docker network to allow inter-service communication.

```yaml
networks:
  hadoop-net:
    driver: bridge
```

## Phase 5 – Spark Streaming + Monitoring Logs Pipeline

This phase builds the **real-time log monitoring pipeline** using Spark Structured Streaming, Kafka, and Hadoop (HDFS).

[spark-streaming code](spark-apps/logs_processor.py)

### 🔄 Streaming Flow

1. **Kafka Topic (`loadbalancer-logs`)**
   - Sends raw log lines from the load balancer.

2. **Spark Streaming Job**
   - Reads logs from Kafka.
   - Parses logs using regex.
   - Applies a 5-minute **moving window**.
   - Counts successful/failed GET and POST operations.
   - Stores results to HDFS in Parquet format.

3. **HDFS**
   - Stores processed logs for future analysis.

---

### 🧪 Debugging and Tips

### Kafka Topic Errors:
Use the following commands inside `broker1` to create a topic:
```bash
# Enter container
docker exec -it broker1 bash

# Create topic
kafka-topics.sh --create \
  --topic loadbalancer-logs \
  --bootstrap-server broker1:29092 \
  --partitions 1 \
  --replication-factor 1
```

### Spark code run
```bash
docker exec spark-master spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.2 --master spark://spark-master:7077 /opt/spark-apps/logs_processor.py

```

### Spark Resource Issues:
If you see:
```
Initial job has not accepted any resources
```
still under investgation

### Permissions Error:
If you see:
```
AccessControlException: Permission denied: user=spark, access=WRITE
```
Then set HDFS permissions inside `namenode`:
```bash
docker exec -it namenode bash
hdfs dfs -chmod -R 777 /
```
