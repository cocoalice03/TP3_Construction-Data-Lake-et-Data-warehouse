import json
import logging
import sys
from datetime import datetime, date
import pandas as pd
import mysql.connector
from mysql.connector import Error
from kafka import KafkaConsumer
from kafka.errors import KafkaError

from kafka_config import (
    KAFKA_CONFIG, KAFKA_TOPICS, BATCH_CONFIG, MYSQL_CONFIG,
    LOGS_DIR, LOG_FORMAT, LOG_LEVEL,
    get_topics_for_destination, get_topic_config
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


class WarehouseKafkaConsumer:
    def __init__(self, topics=None, mysql_password=""):
        # Déterminer les topics à consommer (uniquement les tables)
        if topics is None:
            self.topics = [
                t["topic"] for t in KAFKA_TOPICS["tables"] 
                if t["enabled"] and t["destination"] in ["data_warehouse", "both"]
            ]
        else:
            self.topics = topics
        
        logger.info(f"Initialisation du consumer pour les topics: {self.topics}")
        
        # Configuration MySQL
        self.mysql_config = MYSQL_CONFIG.copy()
        self.mysql_config["password"] = mysql_password
        
        # Connexion MySQL
        self.mysql_connection = None
        self.mysql_cursor = None
        self.connect_mysql()
        
        # Créer le consumer Kafka
        self.consumer = KafkaConsumer(
            *self.topics,
            bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"],
            group_id=f"{KAFKA_CONFIG['group_id']}_warehouse",
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
        
        # Version de snapshot
        self.snapshot_date = date.today()
        self.snapshot_version = 1
        
        logger.info("✓ Consumer Kafka initialisé")
    
    def connect_mysql(self):
        try:
            self.mysql_connection = mysql.connector.connect(**self.mysql_config)
            self.mysql_cursor = self.mysql_connection.cursor(dictionary=True)
            logger.info("✓ Connexion à MySQL établie")
        except Error as e:
            logger.error(f"Erreur de connexion à MySQL: {e}")
            raise
    
    def disconnect_mysql(self):
        if self.mysql_cursor:
            self.mysql_cursor.close()
        if self.mysql_connection:
            self.mysql_connection.close()
        logger.info("Connexion à MySQL fermée")
    
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
            self.disconnect_mysql()
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
            
            # Insérer dans MySQL selon le type de table
            if topic == "user_transaction_summary":
                self.insert_user_transaction_summary(df)
            elif topic == "user_transaction_summary_eur":
                self.insert_user_transaction_summary_eur(df)
            elif topic == "payment_method_totals":
                self.insert_payment_method_totals(df)
            elif topic == "product_purchase_counts":
                self.insert_product_purchase_counts(df)
            else:
                logger.warning(f"Topic non supporté: {topic}")
                return
            
            # Vider le buffer
            self.message_buffers[topic] = []
            self.last_flush_time[topic] = datetime.now()
            
            logger.info(f"✓ {len(messages)} messages insérés dans MySQL pour {topic}")
        
        except Exception as e:
            logger.error(f"Erreur lors du flush du buffer pour {topic}: {e}")
            self.mysql_connection.rollback()
    
    def upsert_user(self, user_data):
        query = """
        INSERT INTO dim_users (user_id, user_name, user_email, user_country, user_city)
        VALUES (%(user_id)s, %(user_name)s, %(user_email)s, %(user_country)s, %(user_city)s)
        ON DUPLICATE KEY UPDATE
            user_name = VALUES(user_name),
            user_email = VALUES(user_email),
            user_country = VALUES(user_country),
            user_city = VALUES(user_city),
            updated_at = CURRENT_TIMESTAMP
        """
        
        try:
            self.mysql_cursor.execute(query, user_data)
        except Error as e:
            logger.error(f"Erreur lors de l'upsert utilisateur: {e}")
            raise
    
    def get_payment_method_id(self, payment_method_name):
        query = "SELECT payment_method_id FROM dim_payment_methods WHERE payment_method_name = %s"
        
        try:
            self.mysql_cursor.execute(query, (payment_method_name,))
            result = self.mysql_cursor.fetchone()
            return result['payment_method_id'] if result else None
        except Error as e:
            logger.error(f"Erreur lors de la récupération de la méthode de paiement: {e}")
            return None
    
    def insert_user_transaction_summary(self, df):
        query = """
        INSERT INTO fact_user_transaction_summary (
            user_id, transaction_type, total_amount, transaction_count,
            avg_amount, min_amount, max_amount, last_transaction_date,
            snapshot_date, snapshot_version
        ) VALUES (
            %(user_id)s, %(transaction_type)s, %(total_amount)s, %(transaction_count)s,
            %(avg_amount)s, %(min_amount)s, %(max_amount)s, %(last_transaction_date)s,
            %(snapshot_date)s, %(snapshot_version)s
        )
        ON DUPLICATE KEY UPDATE
            total_amount = VALUES(total_amount),
            transaction_count = VALUES(transaction_count),
            avg_amount = VALUES(avg_amount),
            min_amount = VALUES(min_amount),
            max_amount = VALUES(max_amount),
            last_transaction_date = VALUES(last_transaction_date),
            updated_at = CURRENT_TIMESTAMP
        """
        
        for _, row in df.iterrows():
            # Upsert utilisateur
            user_data = {
                "user_id": row.get("user_id"),
                "user_name": row.get("user_name", ""),
                "user_email": row.get("user_email", ""),
                "user_country": row.get("user_country", ""),
                "user_city": row.get("user_city", "")
            }
            self.upsert_user(user_data)
            
            # Insérer le résumé
            summary_data = {
                "user_id": row.get("user_id"),
                "transaction_type": row.get("transaction_type"),
                "total_amount": row.get("total_amount"),
                "transaction_count": row.get("transaction_count"),
                "avg_amount": row.get("avg_amount"),
                "min_amount": row.get("min_amount"),
                "max_amount": row.get("max_amount"),
                "last_transaction_date": row.get("last_transaction_date"),
                "snapshot_date": self.snapshot_date,
                "snapshot_version": self.snapshot_version
            }
            self.mysql_cursor.execute(query, summary_data)
        
        self.mysql_connection.commit()
    
    def insert_user_transaction_summary_eur(self, df):
        query = """
        INSERT INTO fact_user_transaction_summary_eur (
            user_id, transaction_type, total_amount_eur, transaction_count,
            avg_amount_eur, exchange_rate, snapshot_date, snapshot_version
        ) VALUES (
            %(user_id)s, %(transaction_type)s, %(total_amount_eur)s, %(transaction_count)s,
            %(avg_amount_eur)s, %(exchange_rate)s, %(snapshot_date)s, %(snapshot_version)s
        )
        ON DUPLICATE KEY UPDATE
            total_amount_eur = VALUES(total_amount_eur),
            transaction_count = VALUES(transaction_count),
            avg_amount_eur = VALUES(avg_amount_eur),
            exchange_rate = VALUES(exchange_rate),
            updated_at = CURRENT_TIMESTAMP
        """
        
        for _, row in df.iterrows():
            # Upsert utilisateur
            user_data = {
                "user_id": row.get("user_id"),
                "user_name": row.get("user_name", ""),
                "user_email": row.get("user_email", ""),
                "user_country": row.get("user_country", ""),
                "user_city": row.get("user_city", "")
            }
            self.upsert_user(user_data)
            
            # Insérer le résumé EUR
            summary_data = {
                "user_id": row.get("user_id"),
                "transaction_type": row.get("transaction_type"),
                "total_amount_eur": row.get("total_amount_eur"),
                "transaction_count": row.get("transaction_count"),
                "avg_amount_eur": row.get("avg_amount_eur"),
                "exchange_rate": row.get("exchange_rate", 1.0),
                "snapshot_date": self.snapshot_date,
                "snapshot_version": self.snapshot_version
            }
            self.mysql_cursor.execute(query, summary_data)
        
        self.mysql_connection.commit()
    
    def insert_payment_method_totals(self, df):
        query = """
        INSERT INTO fact_payment_method_totals (
            payment_method_id, payment_method_name, total_amount,
            transaction_count, avg_amount, snapshot_date, snapshot_version
        ) VALUES (
            %(payment_method_id)s, %(payment_method_name)s, %(total_amount)s,
            %(transaction_count)s, %(avg_amount)s, %(snapshot_date)s, %(snapshot_version)s
        )
        ON DUPLICATE KEY UPDATE
            total_amount = VALUES(total_amount),
            transaction_count = VALUES(transaction_count),
            avg_amount = VALUES(avg_amount),
            updated_at = CURRENT_TIMESTAMP
        """
        
        for _, row in df.iterrows():
            payment_method_name = row.get("payment_method")
            payment_method_id = self.get_payment_method_id(payment_method_name)
            
            if not payment_method_id:
                logger.warning(f"Méthode de paiement inconnue: {payment_method_name}")
                continue
            
            totals_data = {
                "payment_method_id": payment_method_id,
                "payment_method_name": payment_method_name,
                "total_amount": row.get("total_amount"),
                "transaction_count": row.get("transaction_count"),
                "avg_amount": row.get("avg_amount"),
                "snapshot_date": self.snapshot_date,
                "snapshot_version": self.snapshot_version
            }
            self.mysql_cursor.execute(query, totals_data)
        
        self.mysql_connection.commit()
    
    def insert_product_purchase_counts(self, df):
        query = """
        INSERT INTO fact_product_purchase_counts (
            product_id, product_name, product_category, purchase_count,
            total_revenue, avg_price, unique_buyers, snapshot_date, snapshot_version
        ) VALUES (
            %(product_id)s, %(product_name)s, %(product_category)s, %(purchase_count)s,
            %(total_revenue)s, %(avg_price)s, %(unique_buyers)s, %(snapshot_date)s, %(snapshot_version)s
        )
        ON DUPLICATE KEY UPDATE
            purchase_count = VALUES(purchase_count),
            total_revenue = VALUES(total_revenue),
            avg_price = VALUES(avg_price),
            unique_buyers = VALUES(unique_buyers),
            updated_at = CURRENT_TIMESTAMP
        """
        
        for _, row in df.iterrows():
            product_data = {
                "product_id": row.get("product_id"),
                "product_name": row.get("product_name"),
                "product_category": row.get("product_category"),
                "purchase_count": row.get("purchase_count"),
                "total_revenue": row.get("total_revenue"),
                "avg_price": row.get("avg_price"),
                "unique_buyers": row.get("unique_buyers"),
                "snapshot_date": self.snapshot_date,
                "snapshot_version": self.snapshot_version
            }
            self.mysql_cursor.execute(query, product_data)
        
        self.mysql_connection.commit()
    
    def flush_all_buffers(self):
        logger.info("Flush de tous les buffers...")
        for topic in self.topics:
            self.flush_buffer(topic)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Kafka Consumer pour le Data Warehouse MySQL"
    )
    parser.add_argument(
        "--topics",
        type=str,
        nargs="+",
        help="Topics Kafka à consommer (optionnel)"
    )
    parser.add_argument(
        "--mysql-password",
        type=str,
        default="",
        help="Mot de passe MySQL"
    )
    
    args = parser.parse_args()
    
    try:
        consumer = WarehouseKafkaConsumer(
            topics=args.topics,
            mysql_password=args.mysql_password
        )
        consumer.consume()
    
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
