"""
Script de Synchronisation ksqlDB → MySQL Data Warehouse
"""
import argparse
import logging
import sys
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import requests
import pandas as pd
import mysql.connector
from mysql.connector import Error

from data_lake_config import (
    KSQLDB_CONFIG, TABLES_CONFIG,
    LOG_FORMAT, LOG_LEVEL, LOGS_DIR, ensure_directories
)


# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOGS_DIR / f"mysql_sync_{datetime.now().strftime('%Y%m')}.log"
        )
    ]
)
logger = logging.getLogger(__name__)


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


class KsqlDBClient:
    """Client pour interagir avec ksqlDB"""
    
    def __init__(self, host: str, port: int, timeout: int = 30):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        logger.info(f"Initialisation du client ksqlDB: {self.base_url}")
    
    def get_table_data(self, table_name: str) -> pd.DataFrame:
        """Récupère les données d'une table ksqlDB"""
        url = f"{self.base_url}/query"
        query = f"SELECT * FROM {table_name}"
        payload = {
            "ksql": query,
            "streamsProperties": {}
        }
        
        try:
            logger.debug(f"Exécution de la requête: {query}")
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            # Parser la réponse
            results = []
            for line in response.text.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    if 'row' in data:
                        results.append(data['row']['columns'])
            
            logger.info(f"Requête réussie: {len(results)} lignes récupérées")
            return pd.DataFrame(results) if results else pd.DataFrame()
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données: {e}")
            raise


class MySQLWarehouse:
    """Gestionnaire du Data Warehouse MySQL"""
    
    def __init__(self, config: dict):
        self.config = config
        self.connection = None
        self.cursor = None
        logger.info("Initialisation du gestionnaire MySQL")
    
    def connect(self):
        """Établit la connexion à MySQL"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            self.cursor = self.connection.cursor(dictionary=True)
            logger.info("✓ Connexion à MySQL établie")
        except Error as e:
            logger.error(f"Erreur de connexion à MySQL: {e}")
            raise
    
    def disconnect(self):
        """Ferme la connexion à MySQL"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Connexion à MySQL fermée")
    
    def upsert_user(self, user_data: dict):
        """Insert ou update un utilisateur dans dim_users"""
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
            self.cursor.execute(query, user_data)
            self.connection.commit()
        except Error as e:
            logger.error(f"Erreur lors de l'upsert utilisateur: {e}")
            self.connection.rollback()
            raise
    
    def get_payment_method_id(self, payment_method_name: str) -> Optional[int]:
        """Récupère l'ID d'une méthode de paiement"""
        query = "SELECT payment_method_id FROM dim_payment_methods WHERE payment_method_name = %s"
        
        try:
            self.cursor.execute(query, (payment_method_name,))
            result = self.cursor.fetchone()
            return result['payment_method_id'] if result else None
        except Error as e:
            logger.error(f"Erreur lors de la récupération de la méthode de paiement: {e}")
            return None
    
    def insert_user_transaction_summary(self, data: dict):
        """Insère un résumé de transactions utilisateur"""
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
        
        try:
            self.cursor.execute(query, data)
            self.connection.commit()
        except Error as e:
            logger.error(f"Erreur lors de l'insertion du résumé: {e}")
            self.connection.rollback()
            raise
    
    def insert_user_transaction_summary_eur(self, data: dict):
        """Insère un résumé de transactions en EUR"""
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
        
        try:
            self.cursor.execute(query, data)
            self.connection.commit()
        except Error as e:
            logger.error(f"Erreur lors de l'insertion du résumé EUR: {e}")
            self.connection.rollback()
            raise
    
    def insert_payment_method_totals(self, data: dict):
        """Insère les totaux par méthode de paiement"""
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
        
        try:
            self.cursor.execute(query, data)
            self.connection.commit()
        except Error as e:
            logger.error(f"Erreur lors de l'insertion des totaux paiement: {e}")
            self.connection.rollback()
            raise
    
    def insert_product_purchase_counts(self, data: dict):
        """Insère les compteurs d'achats par produit"""
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
        
        try:
            self.cursor.execute(query, data)
            self.connection.commit()
        except Error as e:
            logger.error(f"Erreur lors de l'insertion des compteurs produit: {e}")
            self.connection.rollback()
            raise


class DataWarehouseSyncer:
    """Synchroniseur ksqlDB → MySQL"""
    
    def __init__(self, ksqldb_client: KsqlDBClient, mysql_warehouse: MySQLWarehouse):
        self.ksqldb = ksqldb_client
        self.mysql = mysql_warehouse
        self.snapshot_date = date.today()
        self.snapshot_version = 1
        logger.info("DataWarehouseSyncer initialisé")
    
    def sync_all_tables(self):
        """Synchronise toutes les tables ksqlDB vers MySQL"""
        logger.info("Début de la synchronisation complète")
        
        try:
            self.mysql.connect()
            
            # Synchroniser chaque table
            for table_name in TABLES_CONFIG.keys():
                logger.info(f"Synchronisation de la table: {table_name}")
                self.sync_table(table_name)
            
            logger.info("✓ Synchronisation complète terminée avec succès")
        
        except Exception as e:
            logger.error(f"Erreur lors de la synchronisation: {e}")
            raise
        
        finally:
            self.mysql.disconnect()
    
    def sync_table(self, table_name: str):
        """Synchronise une table spécifique"""
        # Mapping des tables ksqlDB vers les méthodes de synchronisation
        sync_methods = {
            "user_transaction_summary": self.sync_user_transaction_summary,
            "user_transaction_summary_eur": self.sync_user_transaction_summary_eur,
            "payment_method_totals": self.sync_payment_method_totals,
            "product_purchase_counts": self.sync_product_purchase_counts
        }
        
        if table_name in sync_methods:
            sync_methods[table_name]()
        else:
            logger.warning(f"Table non supportée: {table_name}")
    
    def sync_user_transaction_summary(self):
        """Synchronise user_transaction_summary"""
        logger.info("Synchronisation de user_transaction_summary")
        
        # Récupérer les données de ksqlDB
        df = self.ksqldb.get_table_data("user_transaction_summary")
        
        if df.empty:
            logger.warning("Aucune donnée à synchroniser")
            return
        
        # Insérer chaque ligne
        for _, row in df.iterrows():
            # Upsert utilisateur dans dim_users
            user_data = {
                "user_id": row.get("user_id"),
                "user_name": row.get("user_name"),
                "user_email": row.get("user_email"),
                "user_country": row.get("user_country"),
                "user_city": row.get("user_city")
            }
            self.mysql.upsert_user(user_data)
            
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
            self.mysql.insert_user_transaction_summary(summary_data)
        
        logger.info(f"✓ {len(df)} lignes synchronisées")
    
    def sync_user_transaction_summary_eur(self):
        """Synchronise user_transaction_summary_eur"""
        logger.info("Synchronisation de user_transaction_summary_eur")
        
        df = self.ksqldb.get_table_data("user_transaction_summary_eur")
        
        if df.empty:
            logger.warning("Aucune donnée à synchroniser")
            return
        
        for _, row in df.iterrows():
            # Upsert utilisateur
            user_data = {
                "user_id": row.get("user_id"),
                "user_name": row.get("user_name"),
                "user_email": row.get("user_email"),
                "user_country": row.get("user_country"),
                "user_city": row.get("user_city")
            }
            self.mysql.upsert_user(user_data)
            
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
            self.mysql.insert_user_transaction_summary_eur(summary_data)
        
        logger.info(f"✓ {len(df)} lignes synchronisées")
    
    def sync_payment_method_totals(self):
        """Synchronise payment_method_totals"""
        logger.info("Synchronisation de payment_method_totals")
        
        df = self.ksqldb.get_table_data("payment_method_totals")
        
        if df.empty:
            logger.warning("Aucune donnée à synchroniser")
            return
        
        for _, row in df.iterrows():
            payment_method_name = row.get("payment_method")
            payment_method_id = self.mysql.get_payment_method_id(payment_method_name)
            
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
            self.mysql.insert_payment_method_totals(totals_data)
        
        logger.info(f"✓ {len(df)} lignes synchronisées")
    
    def sync_product_purchase_counts(self):
        """Synchronise product_purchase_counts"""
        logger.info("Synchronisation de product_purchase_counts")
        
        df = self.ksqldb.get_table_data("product_purchase_counts")
        
        if df.empty:
            logger.warning("Aucune donnée à synchroniser")
            return
        
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
            self.mysql.insert_product_purchase_counts(product_data)
        
        logger.info(f"✓ {len(df)} lignes synchronisées")


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Synchronisation ksqlDB → MySQL Data Warehouse"
    )
    parser.add_argument(
        "--table",
        type=str,
        help="Nom de la table à synchroniser (optionnel)"
    )
    parser.add_argument(
        "--mysql-host",
        type=str,
        default="localhost",
        help="Host MySQL"
    )
    parser.add_argument(
        "--mysql-user",
        type=str,
        default="root",
        help="Utilisateur MySQL"
    )
    parser.add_argument(
        "--mysql-password",
        type=str,
        required=True,
        help="Mot de passe MySQL"
    )
    
    args = parser.parse_args()
    
    # Mettre à jour la configuration MySQL
    MYSQL_CONFIG["host"] = args.mysql_host
    MYSQL_CONFIG["user"] = args.mysql_user
    MYSQL_CONFIG["password"] = args.mysql_password
    
    # Initialiser les clients
    try:
        ksqldb_client = KsqlDBClient(
            KSQLDB_CONFIG['host'],
            KSQLDB_CONFIG['port'],
            KSQLDB_CONFIG['timeout']
        )
        
        mysql_warehouse = MySQLWarehouse(MYSQL_CONFIG)
        
        syncer = DataWarehouseSyncer(ksqldb_client, mysql_warehouse)
        
        if args.table:
            logger.info(f"Synchronisation de la table: {args.table}")
            syncer.mysql.connect()
            syncer.sync_table(args.table)
            syncer.mysql.disconnect()
        else:
            logger.info("Synchronisation de toutes les tables")
            syncer.sync_all_tables()
        
        logger.info("✓ Synchronisation terminée avec succès")
    
    except Exception as e:
        logger.error(f"Erreur lors de la synchronisation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
