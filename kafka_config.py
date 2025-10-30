from pathlib import Path

# Configuration Kafka
KAFKA_CONFIG = {
    "bootstrap_servers": ["localhost:9092"],
    "group_id": "data_lake_consumers",
    "auto_offset_reset": "earliest",  # 'earliest' ou 'latest'
    "enable_auto_commit": True,
    "auto_commit_interval_ms": 5000,
    "session_timeout_ms": 30000,
    "max_poll_records": 500,
    "max_poll_interval_ms": 300000,
}

# Configuration des Topics Kafka
KAFKA_TOPICS = {
    # Topics pour les streams (Data Lake uniquement)
    "streams": [
        {
            "topic": "transaction_stream",
            "feed_type": "stream",
            "destination": "data_lake",  # 'data_lake' ou 'both'
            "partitioning": "date",
            "storage_mode": "append",
            "enabled": True
        },
        {
            "topic": "transaction_flattened",
            "feed_type": "stream",
            "destination": "data_lake",
            "partitioning": "date",
            "storage_mode": "append",
            "enabled": True
        },
        {
            "topic": "transaction_stream_anonymized",
            "feed_type": "stream",
            "destination": "data_lake",
            "partitioning": "date",
            "storage_mode": "append",
            "enabled": True
        },
        {
            "topic": "transaction_stream_blacklisted",
            "feed_type": "stream",
            "destination": "data_lake",
            "partitioning": "date",
            "storage_mode": "append",
            "enabled": True
        }
    ],
    
    # Topics pour les tables (Data Lake + Data Warehouse)
    "tables": [
        {
            "topic": "user_transaction_summary",
            "feed_type": "table",
            "destination": "both",  # Data Lake + Data Warehouse
            "partitioning": "version",
            "storage_mode": "overwrite",
            "mysql_table": "fact_user_transaction_summary",
            "enabled": True
        },
        {
            "topic": "user_transaction_summary_eur",
            "feed_type": "table",
            "destination": "both",
            "partitioning": "version",
            "storage_mode": "overwrite",
            "mysql_table": "fact_user_transaction_summary_eur",
            "enabled": True
        },
        {
            "topic": "payment_method_totals",
            "feed_type": "table",
            "destination": "both",
            "partitioning": "version",
            "storage_mode": "overwrite",
            "mysql_table": "fact_payment_method_totals",
            "enabled": True
        },
        {
            "topic": "product_purchase_counts",
            "feed_type": "table",
            "destination": "both",
            "partitioning": "version",
            "storage_mode": "overwrite",
            "mysql_table": "fact_product_purchase_counts",
            "enabled": True
        }
    ]
}

# Configuration du batch processing
BATCH_CONFIG = {
    "batch_size": 200,  # Nombre de messages avant flush (simplifié)
    "batch_timeout_seconds": 10,  # Timeout avant flush (simplifié)
    "max_retries": 3,
    "retry_delay_seconds": 5
}

# Configuration des chemins
BASE_DIR = Path(__file__).parent
DATA_LAKE_ROOT = BASE_DIR / "data_lake"
LOGS_DIR = DATA_LAKE_ROOT / "logs"

# Configuration MySQL
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "database": "data_warehouse",
    "user": "root",
    "password": "",  # À configurer
    "charset": "utf8mb4",
    "use_unicode": True
}

# Configuration du logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"


def get_all_topics():
    # Retourne la liste de tous les topics Kafka
    topics = []
    for stream in KAFKA_TOPICS["streams"]:
        if stream["enabled"]:
            topics.append(stream["topic"])
    for table in KAFKA_TOPICS["tables"]:
        if table["enabled"]:
            topics.append(table["topic"])
    return topics


def get_topic_config(topic_name):
    # Retourne la configuration d'un topic spécifique
    # Chercher dans les streams
    for stream in KAFKA_TOPICS["streams"]:
        if stream["topic"] == topic_name:
            return stream
    
    # Chercher dans les tables
    for table in KAFKA_TOPICS["tables"]:
        if table["topic"] == topic_name:
            return table
    
    return None


def get_topics_for_destination(destination):
    # Retourne les topics pour une destination spécifique
    topics = []
    
    for stream in KAFKA_TOPICS["streams"]:
        if stream["enabled"] and stream["destination"] in [destination, "both"]:
            topics.append(stream["topic"])
    
    for table in KAFKA_TOPICS["tables"]:
        if table["enabled"] and table["destination"] in [destination, "both"]:
            topics.append(table["topic"])
    
    return topics


##
