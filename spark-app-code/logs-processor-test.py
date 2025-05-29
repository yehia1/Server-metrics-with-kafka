from pyspark.sql import SparkSession
from pyspark.sql.functions import col, window, regexp_extract, when , to_timestamp 

spark = SparkSession.builder \
    .appName("Load Balancer Logs") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.2") \
    .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
    .config("spark.hadoop.dfs.client.rpc.max-size", "134217728") \
    .getOrCreate()

# Use container hostnames instead of localhost
KAFKA_BOOTSTRAP_SERVERS = "broker1:29092,broker2:29093"

HDFS_OUTPUT_PATH = "hdfs://namenode:8020/user/spark/logs_output"
HDFS_CHECKPOINT_PATH = "hdfs://namenode:8020/user/spark/checkpoints"


spark.sparkContext.setLogLevel("WARN")

# Read from Kafka
kafka_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", "loadbalancer-logs") \
    .option("startingOffsets", "latest") \
    .load()

log_pattern = r'(\d+\.\d+\.\d+\.\d+) - (\d+) \[([^\]]+)\] (GET|POST) (\S+) (\d{3}) (\d+)'

logs_df = kafka_stream.selectExpr("CAST(value AS STRING) as raw_log") \
    .select(
        regexp_extract("raw_log", log_pattern, 1).alias("ip"),
        regexp_extract("raw_log", log_pattern, 2).alias("user_id"),
        regexp_extract("raw_log", log_pattern, 3).alias("timestamp"),
        regexp_extract("raw_log", log_pattern, 4).alias("method"),
        regexp_extract("raw_log", log_pattern, 5).alias("filename"),
        regexp_extract("raw_log", log_pattern, 6).alias("status_code"),
        regexp_extract("raw_log", log_pattern, 7).alias("size")
    ) \
    .withColumn("user_id", col("user_id").cast("int")) \
    .withColumn("status_code", col("status_code").cast("int")) \
    .withColumn("size", col("size").cast("long")) \
    .withColumn("timestamp", to_timestamp("timestamp", "dd/MMM/yyyy:HH:mm:ss Z"))

# logs_with_window = logs_df.withColumn("window", window("timestamp", "5 minutes"))
logs_with_window = logs_df \
    .withWatermark("timestamp", "10 minutes") \
    .withColumn("window", window("timestamp", "5 minutes"))

logs_with_flags = logs_with_window \
    .withColumn("operation", col("method")) \
    .withColumn("status_flag", when(col("status_code") == 200, "success").otherwise("fail"))

result_df = logs_with_flags.groupBy("window","operation", "status_flag").count()

debug_df = kafka_stream.selectExpr("CAST(value AS STRING) as raw_log") \
    .select(
        col("raw_log"),
        regexp_extract("raw_log", log_pattern, 1).alias("ip"),
        regexp_extract("raw_log", log_pattern, 2).alias("user_id"),
        regexp_extract("raw_log", log_pattern, 3).alias("timestamp"),
        regexp_extract("raw_log", log_pattern, 4).alias("method"),
        regexp_extract("raw_log", log_pattern, 5).alias("filename"),
        regexp_extract("raw_log", log_pattern, 6).alias("status_code"),
        regexp_extract("raw_log", log_pattern, 7).alias("size")
    )

debug_query = debug_df.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()
