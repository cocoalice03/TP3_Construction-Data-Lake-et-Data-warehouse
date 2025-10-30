# Data Lake — Guide étudiant (version simplifiée)

Objectif: montrer un pipeline simple de bout-en-bout avec Kafka → Data Lake (Parquet) et, si besoin, MySQL. Cette version est pensée pour un rendu de Master, claire et rapide à exécuter.

## Prérequis
- Python 3.10+
- Kafka en local (topic créé)

## Installation rapide
```bash
pip install -r requirements.txt
python data_lake_config.py   # crée la structure minimale
```

## Démarrage rapide
1) Produire des messages vers un topic (ex: transaction_stream)
```bash
python kafka_producer.py --topic transaction_stream --messages 100 --rate 50
```
2) Consommer et écrire en Parquet (Data Lake)
```bash
python kafka_consumer_datalake.py --topics transaction_stream
```
3) Vérifier les fichiers
```bash
ls -R data_lake/streams/transaction_stream
```

Astuce: les paramètres par défaut sont modestes pour simplifier les tests.

## Annexes (contenu avancé)
- Design/Architecture: ARCHITECTURE.md, DESIGN_DOCUMENT.md
- Gouvernance/Sécurité: GOVERNANCE_SECURITY.md, GOVERNANCE_SUMMARY.md
- Guides complets: QUICK_START.md, DATA_FLOW.md, KAFKA_CONSUMERS_GUIDE.md
- Data Warehouse: DATA_WAREHOUSE_DESIGN.md, DATA_WAREHOUSE_QUICKSTART.md

## Notes
Ce dépôt conserve toutes les documentations détaillées en fichiers séparés (voir Annexes).
Le README se limite volontairement à un guide simple pour un rendu Master.
