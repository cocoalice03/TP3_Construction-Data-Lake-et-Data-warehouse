"""
Gestionnaire de Rétention des Données
Supprime automatiquement les données historiques selon les politiques définies
"""
import logging
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import mysql.connector
from mysql.connector import Error

from data_lake_config import STREAMS_DIR, TABLES_DIR, LOGS_DIR


# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOGS_DIR / f"data_retention_{datetime.now().strftime('%Y%m')}.log"
        )
    ]
)
logger = logging.getLogger(__name__)


class DataRetentionManager:
    """Gestionnaire de rétention des données"""
    
    def __init__(self, mysql_config: dict, dry_run: bool = False):
        """
        Initialise le gestionnaire de rétention
        
        Args:
            mysql_config: Configuration MySQL
            dry_run: Si True, simule les suppressions sans les effectuer
        """
        self.mysql_config = mysql_config
        self.dry_run = dry_run
        self.mysql_connection = None
        self.mysql_cursor = None
        
        logger.info(f"DataRetentionManager initialisé (dry_run={dry_run})")
    
    def connect_mysql(self):
        """Établit la connexion à MySQL"""
        try:
            self.mysql_connection = mysql.connector.connect(**self.mysql_config)
            self.mysql_cursor = self.mysql_connection.cursor(dictionary=True)
            logger.info("✓ Connexion à MySQL établie")
        except Error as e:
            logger.error(f"Erreur de connexion à MySQL: {e}")
            raise
    
    def disconnect_mysql(self):
        """Ferme la connexion à MySQL"""
        if self.mysql_cursor:
            self.mysql_cursor.close()
        if self.mysql_connection:
            self.mysql_connection.close()
        logger.info("Connexion à MySQL fermée")
    
    def get_retention_policies(self) -> List[Dict]:
        """Récupère les politiques de rétention actives"""
        query = """
        SELECT 
            policy_id,
            feed_name,
            feed_type,
            retention_days,
            retention_versions,
            auto_delete,
            last_cleanup_at
        FROM data_retention_policies
        WHERE is_active = TRUE AND auto_delete = TRUE
        """
        
        self.mysql_cursor.execute(query)
        policies = self.mysql_cursor.fetchall()
        
        logger.info(f"Récupéré {len(policies)} politiques de rétention actives")
        return policies
    
    def cleanup_stream_data(self, feed_name: str, retention_days: int) -> Tuple[int, float]:
        """
        Supprime les données de stream plus anciennes que retention_days
        
        Returns:
            (nombre de fichiers supprimés, taille en MB)
        """
        stream_path = STREAMS_DIR / feed_name
        
        if not stream_path.exists():
            logger.warning(f"Chemin stream non trouvé: {stream_path}")
            return 0, 0.0
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        files_deleted = 0
        size_deleted = 0.0
        
        logger.info(f"Nettoyage stream {feed_name}: suppression avant {cutoff_date.date()}")
        
        # Parcourir les partitions par date
        for year_dir in stream_path.glob("year=*"):
            year = int(year_dir.name.split("=")[1])
            
            for month_dir in year_dir.glob("month=*"):
                month = int(month_dir.name.split("=")[1])
                
                for day_dir in month_dir.glob("day=*"):
                    day = int(day_dir.name.split("=")[1])
                    
                    try:
                        partition_date = datetime(year, month, day)
                        
                        if partition_date < cutoff_date:
                            # Calculer la taille
                            partition_size = sum(
                                f.stat().st_size for f in day_dir.rglob("*") if f.is_file()
                            ) / (1024 * 1024)  # MB
                            
                            # Compter les fichiers
                            file_count = len(list(day_dir.rglob("*.parquet")))
                            
                            if not self.dry_run:
                                shutil.rmtree(day_dir)
                                logger.info(f"✓ Supprimé: {day_dir} ({file_count} fichiers, {partition_size:.2f} MB)")
                            else:
                                logger.info(f"[DRY RUN] Supprimerait: {day_dir} ({file_count} fichiers, {partition_size:.2f} MB)")
                            
                            files_deleted += file_count
                            size_deleted += partition_size
                    
                    except (ValueError, OSError) as e:
                        logger.error(f"Erreur lors du traitement de {day_dir}: {e}")
        
        return files_deleted, size_deleted
    
    def cleanup_table_data(self, feed_name: str, retention_versions: int) -> Tuple[int, float]:
        """
        Supprime les anciennes versions de table au-delà de retention_versions
        
        Returns:
            (nombre de fichiers supprimés, taille en MB)
        """
        table_path = TABLES_DIR / feed_name
        
        if not table_path.exists():
            logger.warning(f"Chemin table non trouvé: {table_path}")
            return 0, 0.0
        
        # Lister toutes les versions
        version_dirs = sorted(
            table_path.glob("version=v*"),
            key=lambda p: int(p.name.replace("version=v", ""))
        )
        
        if len(version_dirs) <= retention_versions:
            logger.info(f"Table {feed_name}: {len(version_dirs)} versions (< {retention_versions}), aucune suppression")
            return 0, 0.0
        
        # Supprimer les anciennes versions
        versions_to_delete = version_dirs[:-retention_versions]
        files_deleted = 0
        size_deleted = 0.0
        
        logger.info(f"Nettoyage table {feed_name}: suppression de {len(versions_to_delete)} anciennes versions")
        
        for version_dir in versions_to_delete:
            # Calculer la taille
            version_size = sum(
                f.stat().st_size for f in version_dir.rglob("*") if f.is_file()
            ) / (1024 * 1024)  # MB
            
            # Compter les fichiers
            file_count = len(list(version_dir.rglob("*.parquet")))
            
            if not self.dry_run:
                shutil.rmtree(version_dir)
                logger.info(f"✓ Supprimé: {version_dir} ({file_count} fichiers, {version_size:.2f} MB)")
            else:
                logger.info(f"[DRY RUN] Supprimerait: {version_dir} ({file_count} fichiers, {version_size:.2f} MB)")
            
            files_deleted += file_count
            size_deleted += version_size
        
        return files_deleted, size_deleted
    
    def log_deletion(self, feed_name: str, feed_type: str, folder_path: str,
                     files_deleted: int, size_deleted: float, user_id: int = 1):
        """Enregistre la suppression dans le journal"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Enregistrerait la suppression: {feed_name}")
            return
        
        query = """
        INSERT INTO data_deletion_log (
            feed_name, feed_type, folder_path, deletion_type,
            files_deleted, size_deleted_mb, deleted_by, notes
        ) VALUES (
            %s, %s, %s, 'retention', %s, %s, %s, 'Automatic retention cleanup'
        )
        """
        
        try:
            self.mysql_cursor.execute(query, (
                feed_name, feed_type, folder_path,
                files_deleted, size_deleted, user_id
            ))
            self.mysql_connection.commit()
            logger.info(f"✓ Suppression enregistrée dans le journal")
        except Error as e:
            logger.error(f"Erreur lors de l'enregistrement de la suppression: {e}")
    
    def update_last_cleanup(self, policy_id: int):
        """Met à jour la date du dernier nettoyage"""
        if self.dry_run:
            return
        
        query = """
        UPDATE data_retention_policies
        SET last_cleanup_at = CURRENT_TIMESTAMP
        WHERE policy_id = %s
        """
        
        try:
            self.mysql_cursor.execute(query, (policy_id,))
            self.mysql_connection.commit()
        except Error as e:
            logger.error(f"Erreur lors de la mise à jour de last_cleanup_at: {e}")
    
    def run_cleanup(self):
        """Exécute le nettoyage selon les politiques de rétention"""
        logger.info("🚀 Démarrage du nettoyage des données historiques")
        
        try:
            self.connect_mysql()
            policies = self.get_retention_policies()
            
            total_files = 0
            total_size = 0.0
            
            for policy in policies:
                feed_name = policy['feed_name']
                feed_type = policy['feed_type']
                
                logger.info(f"\n--- Traitement: {feed_name} ({feed_type}) ---")
                
                if feed_type == 'stream':
                    retention_days = policy['retention_days']
                    files, size = self.cleanup_stream_data(feed_name, retention_days)
                    folder_path = str(STREAMS_DIR / feed_name)
                
                else:  # table
                    retention_versions = policy['retention_versions']
                    if retention_versions is None:
                        logger.warning(f"Pas de retention_versions défini pour {feed_name}")
                        continue
                    files, size = self.cleanup_table_data(feed_name, retention_versions)
                    folder_path = str(TABLES_DIR / feed_name)
                
                if files > 0:
                    self.log_deletion(feed_name, feed_type, folder_path, files, size)
                    self.update_last_cleanup(policy['policy_id'])
                
                total_files += files
                total_size += size
            
            logger.info(f"\n✓ Nettoyage terminé:")
            logger.info(f"  - Fichiers supprimés: {total_files}")
            logger.info(f"  - Espace libéré: {total_size:.2f} MB")
            
            if self.dry_run:
                logger.info("\n⚠️  Mode DRY RUN: Aucune suppression réelle effectuée")
        
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
            raise
        
        finally:
            self.disconnect_mysql()


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Gestionnaire de rétention des données"
    )
    parser.add_argument(
        "--mysql-password",
        type=str,
        default="",
        help="Mot de passe MySQL"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule les suppressions sans les effectuer"
    )
    
    args = parser.parse_args()
    
    mysql_config = {
        "host": "localhost",
        "port": 3306,
        "database": "data_warehouse",
        "user": "root",
        "password": args.mysql_password,
        "charset": "utf8mb4",
        "use_unicode": True
    }
    
    try:
        manager = DataRetentionManager(mysql_config, dry_run=args.dry_run)
        manager.run_cleanup()
    
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
