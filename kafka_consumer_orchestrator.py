"""
Orchestrateur de Kafka Consumers
Lance et gère les consumers pour le Data Lake et le Data Warehouse
"""
import argparse
import logging
import sys
import signal
import time
from multiprocessing import Process
from typing import List

from kafka_consumer_datalake import DataLakeKafkaConsumer
from kafka_consumer_warehouse import WarehouseKafkaConsumer
from kafka_config import LOGS_DIR, LOG_FORMAT, LOG_LEVEL
from datetime import datetime


# Configuration du logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOGS_DIR / f"kafka_orchestrator_{datetime.now().strftime('%Y%m')}.log"
        )
    ]
)
logger = logging.getLogger(__name__)


class KafkaConsumerOrchestrator:
    """Orchestrateur pour gérer plusieurs consumers Kafka"""
    
    def __init__(self, enable_datalake: bool = True, enable_warehouse: bool = True, mysql_password: str = ""):
        """
        Initialise l'orchestrateur
        
        Args:
            enable_datalake: Activer le consumer Data Lake
            enable_warehouse: Activer le consumer Data Warehouse
            mysql_password: Mot de passe MySQL
        """
        self.enable_datalake = enable_datalake
        self.enable_warehouse = enable_warehouse
        self.mysql_password = mysql_password
        
        self.processes: List[Process] = []
        self.running = False
        
        # Gestion des signaux pour arrêt gracieux
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("Orchestrateur initialisé")
    
    def signal_handler(self, signum, frame):
        """Gère les signaux d'arrêt"""
        logger.info(f"Signal {signum} reçu, arrêt des consumers...")
        self.stop()
    
    def start_datalake_consumer(self):
        """Démarre le consumer Data Lake dans un processus séparé"""
        logger.info("Démarrage du consumer Data Lake...")
        consumer = DataLakeKafkaConsumer()
        consumer.consume()
    
    def start_warehouse_consumer(self):
        """Démarre le consumer Data Warehouse dans un processus séparé"""
        logger.info("Démarrage du consumer Data Warehouse...")
        consumer = WarehouseKafkaConsumer(mysql_password=self.mysql_password)
        consumer.consume()
    
    def start(self):
        """Démarre tous les consumers activés"""
        logger.info("🚀 Démarrage de l'orchestrateur Kafka")
        self.running = True
        
        # Démarrer le consumer Data Lake
        if self.enable_datalake:
            logger.info("Lancement du consumer Data Lake")
            p_datalake = Process(
                target=self.start_datalake_consumer,
                name="DataLakeConsumer"
            )
            p_datalake.start()
            self.processes.append(p_datalake)
            logger.info(f"✓ Consumer Data Lake démarré (PID: {p_datalake.pid})")
        
        # Démarrer le consumer Data Warehouse
        if self.enable_warehouse:
            logger.info("Lancement du consumer Data Warehouse")
            p_warehouse = Process(
                target=self.start_warehouse_consumer,
                name="WarehouseConsumer"
            )
            p_warehouse.start()
            self.processes.append(p_warehouse)
            logger.info(f"✓ Consumer Data Warehouse démarré (PID: {p_warehouse.pid})")
        
        # Attendre que tous les processus se terminent
        try:
            while self.running:
                # Vérifier l'état des processus
                for process in self.processes:
                    if not process.is_alive():
                        logger.warning(f"Processus {process.name} (PID: {process.pid}) s'est arrêté")
                        self.processes.remove(process)
                
                # Si tous les processus sont arrêtés, sortir
                if not self.processes:
                    logger.info("Tous les processus sont arrêtés")
                    break
                
                time.sleep(5)
        
        except KeyboardInterrupt:
            logger.info("Interruption clavier détectée")
            self.stop()
    
    def stop(self):
        """Arrête tous les consumers"""
        logger.info("Arrêt de tous les consumers...")
        self.running = False
        
        for process in self.processes:
            if process.is_alive():
                logger.info(f"Arrêt du processus {process.name} (PID: {process.pid})")
                process.terminate()
                process.join(timeout=10)
                
                if process.is_alive():
                    logger.warning(f"Processus {process.name} ne répond pas, kill forcé")
                    process.kill()
                    process.join()
        
        logger.info("✓ Tous les consumers sont arrêtés")
    
    def status(self):
        """Affiche le statut des consumers"""
        logger.info("=== Statut des Consumers ===")
        
        if not self.processes:
            logger.info("Aucun consumer en cours d'exécution")
            return
        
        for process in self.processes:
            status = "Running" if process.is_alive() else "Stopped"
            logger.info(f"- {process.name} (PID: {process.pid}): {status}")


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Orchestrateur de Kafka Consumers"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["all", "datalake", "warehouse"],
        default="all",
        help="Mode d'exécution: all (défaut), datalake, ou warehouse"
    )
    parser.add_argument(
        "--mysql-password",
        type=str,
        default="",
        help="Mot de passe MySQL (requis si mode=warehouse ou mode=all)"
    )
    
    args = parser.parse_args()
    
    # Déterminer quels consumers activer
    enable_datalake = args.mode in ["all", "datalake"]
    enable_warehouse = args.mode in ["all", "warehouse"]
    
    # Vérifier que le mot de passe MySQL est fourni si nécessaire
    if enable_warehouse and not args.mysql_password:
        logger.warning("Mot de passe MySQL non fourni, utilisation du mot de passe vide")
    
    try:
        orchestrator = KafkaConsumerOrchestrator(
            enable_datalake=enable_datalake,
            enable_warehouse=enable_warehouse,
            mysql_password=args.mysql_password
        )
        
        orchestrator.start()
    
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
