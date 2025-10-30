import json
import logging
import sys
from datetime import datetime, date
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from kafka_config import (
    KAFKA_CONFIG, KAFKA_TOPICS, BATCH_CONFIG,
    DATA_LAKE_ROOT, LOGS_DIR, LOG_FORMAT, LOG_LEVEL,
    get_topics_for_destination, get_topic_config
)
from data_lake_config import (
    STREAMS_DIR, TABLES_DIR, PARQUET_COMPRESSION,
    get_date_partition_path, get_version_partition_path,
    ensure_directories
)


# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DataLakeKafkaConsumer:
    def __init__(self, topics=None):
        ensure_directories()
        
        # Déterminer les topics à consommer
        if topics is None:
            self.topics = get_topics_for_destination("data_lake")
        else:
            self.topics = topics
        
        logger.info(f"Initialisation du consumer pour les topics: {self.topics}")
        
        # Créer le consumer Kafka
        self.consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"],
            group_id=KAFKA_CONFIG["group_id"],
            auto_offset_reset=KAFKA_CONFIG["auto_offset_reset"],
            enable_auto_commit=KAFKA_CONFIG["enable_auto_commit"],
            auto_commit_interval_ms=KAFKA_CONFIG["auto_commit_interval_ms"],
            session_timeout_ms=KAFKA_CONFIG["session_timeout_ms"],
            max_poll_records=KAFKA_CONFIG["max_poll_records"],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda m: m.decode('utf-8') if m else None
        )
        
        # Buffers pour le batch processing
        self.message_buffers = {topic: [] for topic in self.topics}
        self.last_flush_time = {topic: datetime.now() for topic in self.topics}
        
        logger.info("✓ Consumer Kafka initialisé")
    
    def consume(self):
        logger.info("🚀 Démarrage de la consommation des messages Kafka")
        
        try:
            for message in self.consumer:
                try:
                    self.process_message(message)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du message: {e}")
                    logger.error(f"Topic: {message.topic}, Partition: {message.partition}, Offset: {message.offset}")
        
        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
        
        except KafkaError as e:
            logger.error(f"Erreur Kafka: {e}")
        
        finally:
            self.flush_all_buffers()
            self.consumer.close()
            logger.info("Consumer Kafka fermé")
    
    def process_message(self, message):
        topic = message.topic
        value = message.value
        
        # Ajouter le message au buffer
        self.message_buffers[topic].append(value)
        
        # Vérifier si on doit flush le buffer
        should_flush = (
            len(self.message_buffers[topic]) >= BATCH_CONFIG["batch_size"] or
            (datetime.now() - self.last_flush_time[topic]).total_seconds() >= BATCH_CONFIG["batch_timeout_seconds"]
        )
        
        if should_flush:
            self.flush_buffer(topic)
    
    def flush_buffer(self, topic):
        if not self.message_buffers[topic]:
            return
        
        messages = self.message_buffers[topic]
        logger.info(f"Flush de {len(messages)} messages pour le topic {topic}")
        
        try:
            # Récupérer la configuration du topic
            topic_config = get_topic_config(topic)
            if not topic_config:
                logger.warning(f"Configuration non trouvée pour le topic {topic}")
                return
            
            # Convertir en DataFrame
            df = pd.DataFrame(messages)
            
            if df.empty:
                logger.warning(f"DataFrame vide pour le topic {topic}")
                return
            
            # Déterminer le chemin de destination
            if topic_config["feed_type"] == "stream":
                self.write_stream_data(topic, df, topic_config)
            else:
                self.write_table_data(topic, df, topic_config)
            
            # Vider le buffer
            self.message_buffers[topic] = []
            self.last_flush_time[topic] = datetime.now()
            
            logger.info(f"✓ {len(messages)} messages écrits pour {topic}")
        
        except Exception as e:
            logger.error(f"Erreur lors du flush du buffer pour {topic}: {e}")
            # En cas d'erreur, on garde les messages dans le buffer pour retry
    
    def write_stream_data(self, topic, df, config):
        # Partitionnement par date
        today = date.today()
        partition_path = get_date_partition_path(
            STREAMS_DIR / topic,
            year=today.year,
            month=today.month,
            day=today.day
        )
        
        # Créer le dossier si nécessaire
        partition_path.mkdir(parents=True, exist_ok=True)
        
        # Nom du fichier avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = partition_path / f"data_{timestamp}.parquet"
        
        # Convertir en Arrow Table et écrire
        table = pa.Table.from_pandas(df)
        pq.write_table(
            table,
            file_path,
            compression=PARQUET_COMPRESSION,
            use_dictionary=True,
            write_statistics=True
        )
        
        logger.info(f"✓ Stream {topic} écrit: {file_path}")
    
    def write_table_data(self, topic, df, config):
        # Déterminer la prochaine version
        base_path = TABLES_DIR / topic
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Trouver les versions existantes
        existing_versions = []
        for version_dir in base_path.glob("version=v*"):
            try:
                version_num = int(version_dir.name.replace("version=v", ""))
                existing_versions.append(version_num)
            except ValueError:
                continue
        
        next_version = max(existing_versions, default=0) + 1
        
        # Créer le chemin de partition
        partition_path = get_version_partition_path(base_path, version=next_version)
        partition_path.mkdir(parents=True, exist_ok=True)
        
        # Nom du fichier avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = partition_path / f"snapshot_{timestamp}.parquet"
        
        # Convertir en Arrow Table et écrire
        table = pa.Table.from_pandas(df)
        pq.write_table(
            table,
            file_path,
            compression=PARQUET_COMPRESSION,
            use_dictionary=True,
            write_statistics=True
        )
        
        logger.info(f"✓ Table {topic} écrite: {file_path} (version {next_version})")
        
        # Nettoyage des anciennes versions si nécessaire
        self.cleanup_old_versions(base_path, retention_versions=7)
    
    def cleanup_old_versions(self, base_path: Path, retention_versions=7):
        version_dirs = sorted(
            base_path.glob("version=v*"),
            key=lambda p: int(p.name.replace("version=v", ""))
        )
        
        if len(version_dirs) > retention_versions:
            for old_version in version_dirs[:-retention_versions]:
                logger.info(f"Suppression de l'ancienne version: {old_version}")
                import shutil
                shutil.rmtree(old_version)
    
    def flush_all_buffers(self):
        logger.info("Flush de tous les buffers...")
        for topic in self.topics:
            self.flush_buffer(topic)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Kafka Consumer pour le Data Lake"
    )
    parser.add_argument(
        "--topics",
        type=str,
        nargs="+",
        help="Topics Kafka à consommer (optionnel)"
    )
    
    args = parser.parse_args()
    
    try:
        consumer = DataLakeKafkaConsumer(topics=args.topics)
        consumer.consume()
    
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
