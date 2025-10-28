# 🔄 Guide des Kafka Consumers

## 📋 Vue d'ensemble

Ce guide décrit les applications Kafka consumers qui peuplent automatiquement le Data Lake et le Data Warehouse en temps réel.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      KAFKA TOPICS                            │
│  • transaction_stream                                        │
│  • transaction_flattened                                     │
│  • transaction_stream_anonymized                             │
│  • user_transaction_summary                                  │
│  • payment_method_totals                                     │
│  • product_purchase_counts                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌───────────────────┐     ┌──────────────────────┐
│  CONSUMER         │     │  CONSUMER            │
│  DATA LAKE        │     │  DATA WAREHOUSE      │
│  (Parquet)        │     │  (MySQL)             │
└────────┬──────────┘     └──────────┬───────────┘
         │                           │
         ▼                           ▼
┌───────────────────┐     ┌──────────────────────┐
│  DATA LAKE        │     │  DATA WAREHOUSE      │
│  • Streams        │     │  • dim_users         │
│  • Tables         │     │  • dim_payment...    │
│  • Parquet files  │     │  • fact_user...      │
└───────────────────┘     └──────────────────────┘
```

---

## 📦 Composants

### 1. kafka_config.py
**Configuration centralisée** pour tous les consumers

- Configuration Kafka (bootstrap servers, group ID, etc.)
- Mapping des topics vers destinations
- Configuration du batch processing
- Configuration MySQL

### 2. kafka_consumer_datalake.py
**Consumer pour le Data Lake** (Parquet)

- Consomme les topics Kafka (streams et tables)
- Écrit les données au format Parquet
- Partitionnement automatique (date/version)
- Batch processing pour performance

### 3. kafka_consumer_warehouse.py
**Consumer pour le Data Warehouse** (MySQL)

- Consomme uniquement les topics tables
- Insère les données dans MySQL
- Gestion des dimensions (users, payment_methods)
- Snapshots versionnés

### 4. kafka_consumer_orchestrator.py
**Orchestrateur** pour gérer les consumers

- Lance les consumers en parallèle
- Gestion des processus
- Arrêt gracieux
- Monitoring

---

## 🚀 Installation

### 1. Installer les Dépendances

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Installer Kafka
pip install kafka-python>=2.0.2

# Ou réinstaller toutes les dépendances
pip install -r requirements.txt
```

### 2. Vérifier Kafka

```bash
# Vérifier que Kafka est accessible
nc -zv localhost 9092

# Lister les topics
kafka-topics --bootstrap-server localhost:9092 --list
```

---

## ⚙️ Configuration

### Éditer kafka_config.py

```python
# Configuration Kafka
KAFKA_CONFIG = {
    "bootstrap_servers": ["localhost:9092"],  # Votre serveur Kafka
    "group_id": "data_lake_consumers",
    "auto_offset_reset": "earliest",  # ou 'latest'
}

# Configuration MySQL
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "database": "data_warehouse",
    "user": "root",
    "password": "",  # À configurer
}
```

### Topics Configurés

**Streams** (Data Lake uniquement):
- `transaction_stream`
- `transaction_flattened`
- `transaction_stream_anonymized`
- `transaction_stream_blacklisted`

**Tables** (Data Lake + Data Warehouse):
- `user_transaction_summary`
- `user_transaction_summary_eur`
- `payment_method_totals`
- `product_purchase_counts`

---

## 🎯 Utilisation

### Option 1: Orchestrateur (Recommandé)

Lance tous les consumers en parallèle:

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Lancer tous les consumers
python kafka_consumer_orchestrator.py \
  --mode all \
  --mysql-password votre_mot_de_passe

# Lancer uniquement Data Lake
python kafka_consumer_orchestrator.py --mode datalake

# Lancer uniquement Data Warehouse
python kafka_consumer_orchestrator.py \
  --mode warehouse \
  --mysql-password votre_mot_de_passe
```

### Option 2: Consumers Individuels

#### Consumer Data Lake

```bash
# Tous les topics
python kafka_consumer_datalake.py

# Topics spécifiques
python kafka_consumer_datalake.py \
  --topics transaction_stream user_transaction_summary
```

#### Consumer Data Warehouse

```bash
# Tous les topics tables
python kafka_consumer_warehouse.py \
  --mysql-password votre_mot_de_passe

# Topics spécifiques
python kafka_consumer_warehouse.py \
  --topics user_transaction_summary payment_method_totals \
  --mysql-password votre_mot_de_passe
```

---

## 🔄 Fonctionnement

### Batch Processing

Les consumers utilisent le **batch processing** pour optimiser les performances:

1. **Accumulation**: Les messages sont accumulés dans un buffer
2. **Flush**: Le buffer est vidé quand:
   - Taille du batch atteinte (1000 messages par défaut)
   - Timeout atteint (30 secondes par défaut)
3. **Écriture**: Les données sont écrites en une seule opération

### Partitionnement Automatique

#### Streams (Data Lake)
```
data_lake/streams/transaction_stream/
└── year=2025/month=01/day=28/
    ├── data_20250128_140000.parquet
    ├── data_20250128_140030.parquet
    └── data_20250128_140100.parquet
```

#### Tables (Data Lake)
```
data_lake/tables/user_transaction_summary/
├── version=v1/
│   └── snapshot_20250128_140000.parquet
├── version=v2/
│   └── snapshot_20250128_150000.parquet
└── version=v3/
    └── snapshot_20250128_160000.parquet
```

### Insertion MySQL

Les tables sont insérées avec **UPSERT** (INSERT ... ON DUPLICATE KEY UPDATE):
- Évite les doublons
- Met à jour les données existantes
- Gère les snapshots versionnés

---

## 📊 Monitoring

### Logs

```bash
# Logs de l'orchestrateur
tail -f data_lake/logs/kafka_orchestrator_*.log

# Logs du consumer Data Lake
tail -f data_lake/logs/kafka_consumer_datalake_*.log

# Logs du consumer Data Warehouse
tail -f data_lake/logs/kafka_consumer_warehouse_*.log
```

### Vérifier les Données

#### Data Lake

```bash
# Lister les fichiers créés
find data_lake/streams -name "*.parquet" -mtime -1

# Lire un fichier Parquet
python -c "import pandas as pd; df = pd.read_parquet('data_lake/streams/transaction_stream/year=2025/month=01/day=28/data_*.parquet'); print(df.head())"
```

#### Data Warehouse

```bash
# Vérifier les insertions
mysql -u root -p -e "
USE data_warehouse;
SELECT 
    'fact_user_transaction_summary' as table_name,
    COUNT(*) as count,
    MAX(created_at) as last_insert
FROM fact_user_transaction_summary
UNION ALL
SELECT 
    'fact_payment_method_totals',
    COUNT(*),
    MAX(created_at)
FROM fact_payment_method_totals;
"
```

---

## 🔧 Configuration Avancée

### Ajuster le Batch Processing

Éditer `kafka_config.py`:

```python
BATCH_CONFIG = {
    "batch_size": 1000,  # Augmenter pour plus de performance
    "batch_timeout_seconds": 30,  # Réduire pour plus de réactivité
    "max_retries": 3,
    "retry_delay_seconds": 5
}
```

### Ajuster la Configuration Kafka

```python
KAFKA_CONFIG = {
    "bootstrap_servers": ["localhost:9092"],
    "group_id": "data_lake_consumers",
    "auto_offset_reset": "earliest",  # 'earliest' ou 'latest'
    "enable_auto_commit": True,
    "auto_commit_interval_ms": 5000,  # Fréquence de commit
    "session_timeout_ms": 30000,
    "max_poll_records": 500,  # Messages par poll
    "max_poll_interval_ms": 300000,
}
```

### Ajouter un Nouveau Topic

1. Éditer `kafka_config.py`:

```python
KAFKA_TOPICS = {
    "streams": [
        # ... topics existants ...
        {
            "topic": "nouveau_stream",
            "feed_type": "stream",
            "destination": "data_lake",
            "partitioning": "date",
            "storage_mode": "append",
            "enabled": True
        }
    ]
}
```

2. Redémarrer les consumers

---

## 🐛 Troubleshooting

### Erreur de Connexion Kafka

```bash
# Vérifier que Kafka est démarré
ps aux | grep kafka

# Tester la connexion
nc -zv localhost 9092

# Vérifier les topics
kafka-topics --bootstrap-server localhost:9092 --list
```

### Consumer Lag

```bash
# Vérifier le lag des consumers
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group data_lake_consumers \
  --describe
```

### Erreur MySQL

```bash
# Vérifier la connexion
mysql -u root -p -e "SELECT 1;"

# Vérifier les permissions
mysql -u root -p -e "SHOW GRANTS;"
```

### Messages Non Consommés

```bash
# Vérifier les offsets
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group data_lake_consumers \
  --describe

# Réinitialiser les offsets (ATTENTION: perte de données)
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group data_lake_consumers \
  --reset-offsets --to-earliest \
  --all-topics \
  --execute
```

---

## 🔄 Automatisation

### Systemd Service (Linux)

Créer `/etc/systemd/system/kafka-consumers.service`:

```ini
[Unit]
Description=Kafka Consumers for Data Lake and Data Warehouse
After=network.target kafka.service mysql.service

[Service]
Type=simple
User=alice
WorkingDirectory=/Users/alice/Downloads/data_lake
Environment="PATH=/Users/alice/Downloads/data_lake/venv/bin"
ExecStart=/Users/alice/Downloads/data_lake/venv/bin/python kafka_consumer_orchestrator.py --mode all --mysql-password PASSWORD
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Activer et démarrer
sudo systemctl enable kafka-consumers
sudo systemctl start kafka-consumers

# Vérifier le statut
sudo systemctl status kafka-consumers
```

### Launchd (macOS)

Créer `~/Library/LaunchAgents/com.datalake.kafka-consumers.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.datalake.kafka-consumers</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/alice/Downloads/data_lake/venv/bin/python</string>
        <string>/Users/alice/Downloads/data_lake/kafka_consumer_orchestrator.py</string>
        <string>--mode</string>
        <string>all</string>
        <string>--mysql-password</string>
        <string>PASSWORD</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/alice/Downloads/data_lake</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/alice/Downloads/data_lake/data_lake/logs/kafka_consumers.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/alice/Downloads/data_lake/data_lake/logs/kafka_consumers_error.log</string>
</dict>
</plist>
```

```bash
# Charger le service
launchctl load ~/Library/LaunchAgents/com.datalake.kafka-consumers.plist

# Démarrer
launchctl start com.datalake.kafka-consumers

# Vérifier
launchctl list | grep kafka-consumers
```

---

## 📈 Performance

### Métriques Typiques

| Métrique | Valeur |
|----------|--------|
| **Throughput** | 1000-5000 msg/s par consumer |
| **Latence** | < 100ms (batch processing) |
| **Batch size** | 1000 messages |
| **Batch timeout** | 30 secondes |
| **Compression Parquet** | 70-90% |

### Optimisations

1. **Augmenter le batch size** pour plus de throughput
2. **Réduire le batch timeout** pour moins de latence
3. **Paralléliser** avec plusieurs partitions Kafka
4. **Utiliser SSD** pour le Data Lake
5. **Optimiser MySQL** (index, buffer pool)

---

## ✅ Checklist de Validation

### Installation
- [ ] Kafka installé et démarré
- [ ] Topics Kafka créés
- [ ] Dépendances Python installées (`kafka-python`)
- [ ] Configuration éditée (`kafka_config.py`)

### Tests
- [ ] Consumer Data Lake démarre sans erreur
- [ ] Consumer Data Warehouse démarre sans erreur
- [ ] Fichiers Parquet créés dans `data_lake/`
- [ ] Données insérées dans MySQL
- [ ] Logs sans erreur

### Production
- [ ] Service systemd/launchd configuré
- [ ] Monitoring en place
- [ ] Alertes configurées
- [ ] Backup automatique

---

## 📚 Documentation Complète

- **kafka_config.py** - Configuration centralisée
- **kafka_consumer_datalake.py** - Consumer Data Lake
- **kafka_consumer_warehouse.py** - Consumer Data Warehouse
- **kafka_consumer_orchestrator.py** - Orchestrateur

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Statut**: ✅ Prêt pour la Production
