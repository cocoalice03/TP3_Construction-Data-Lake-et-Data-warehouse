# 🏞️ Data Lake - Stockage et Gestion des Données ksqlDB

> Solution complète de data lake pour stocker, partitionner et gérer les données provenant de ksqlDB

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Parquet](https://img.shields.io/badge/Format-Parquet-green)](https://parquet.apache.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📋 Vue d'ensemble

Ce data lake offre une solution robuste et extensible pour:
- ✅ **Stocker** les données ksqlDB (streams et tables) sur le système de fichiers
- ✅ **Partitionner** intelligemment par date (streams) et version (tables)
- ✅ **Gérer** facilement l'ajout de nouveaux feeds
- ✅ **Optimiser** les performances avec le format Parquet
- ✅ **Tracer** toutes les opérations avec métadonnées et logs

---

## 🚀 Démarrage Rapide

### Installation

```bash
# 1. Cloner le projet
cd /Users/alice/Downloads/data_lake

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Valider l'installation
python test_setup.py

# 4. Créer la structure du data lake
python data_lake_config.py

# 5. Synchroniser les feeds
python manage_feeds.py sync
```

### Premier Export

```bash
# Configurer ksqlDB dans data_lake_config.py
# Puis exporter toutes les données
python export_to_data_lake.py --all
```

---

## 📁 Structure du Projet

```
data_lake/
├── 📄 DESIGN_DOCUMENT.md          # Design complet avec justifications
├── 📄 ARCHITECTURE.md             # Architecture technique
├── 📄 QUICKSTART.md               # Guide de démarrage rapide
├── 📄 SUMMARY.md                  # Résumé du projet
├── 📄 README.md                   # Ce fichier
│
├── 🐍 data_lake_config.py         # Configuration centralisée
├── 🐍 export_to_data_lake.py      # Script d'export principal
├── 🐍 manage_feeds.py             # Gestion des feeds
├── 🐍 metadata_utils.py           # Utilitaires métadonnées
├── 🐍 test_setup.py               # Tests de validation
│
├── 📦 requirements.txt            # Dépendances Python
├── 🚫 .gitignore                  # Fichiers à ignorer
│
└── 📂 data_lake/                  # Dossier du data lake
    ├── streams/                   # Données des streams
    ├── tables/                    # Données des tables
    ├── feeds/                     # Configuration des feeds
    │   ├── active/
    │   └── archived/
    ├── logs/                      # Logs d'export
    └── README.md                  # Documentation détaillée
```

---

## 🎯 Fonctionnalités Principales

### 1. Export des Données

```bash
# Export complet (tous les streams et tables)
python export_to_data_lake.py --all

# Export d'un stream spécifique
python export_to_data_lake.py --stream transaction_stream_anonymized

# Export d'une table spécifique
python export_to_data_lake.py --table user_transaction_summary

# Export avec date spécifique
python export_to_data_lake.py --stream transaction_stream --date 2025-01-15
```

### 2. Gestion des Feeds

```bash
# Lister les feeds
python manage_feeds.py list

# Ajouter un nouveau feed
python manage_feeds.py add \
  --name payment_stream \
  --type stream \
  --source payment_stream \
  --description "Stream des paiements"

# Désactiver un feed
python manage_feeds.py disable transaction_stream

# Archiver un feed
python manage_feeds.py archive old_stream

# Synchroniser depuis la configuration
python manage_feeds.py sync
```

### 3. Monitoring et Métadonnées

```bash
# Afficher les statistiques
python metadata_utils.py --stats

# Générer un rapport complet
python metadata_utils.py --report

# Exporter en CSV
python metadata_utils.py --csv data_lake_report.csv
```

---

## 📊 Architecture

### Partitionnement

#### Streams (Mode APPEND)
```
streams/transaction_stream/
└── year=2025/
    └── month=01/
        └── day=15/
            ├── data_20250115_120000.parquet
            ├── data_20250115_140000.parquet
            └── data_20250115_160000.parquet
```

**Pourquoi APPEND?**
- Événements immuables (Event Sourcing)
- Historique complet pour audit
- Replay des données possible

#### Tables (Mode OVERWRITE)
```
tables/user_transaction_summary/
├── version=v1/
│   └── snapshot_20250115_120000.parquet
├── version=v2/
│   └── snapshot_20250116_120000.parquet
└── version=v3/
    └── snapshot_20250117_120000.parquet
```

**Pourquoi OVERWRITE?**
- Snapshots complets de l'état actuel
- Pas de duplication de données agrégées
- Rétention configurable (7 versions par défaut)

### Format Parquet

**Avantages:**
- 🚀 Compression 70-90% vs JSON
- 📊 Format columnaire pour l'analytique
- 🔧 Compatible Pandas, Spark, DuckDB
- 📝 Schéma intégré
- 🎯 Partitionnement natif

---

## 🔄 Ajout de Nouveaux Feeds

### Méthode 1: Via Script

```bash
python manage_feeds.py add \
  --name new_stream \
  --type stream \
  --source new_stream_ksqldb \
  --description "Description du nouveau stream" \
  --partitioning date \
  --storage-mode append \
  --retention-days 365
```

### Méthode 2: Configuration JSON

Créer `data_lake/feeds/active/new_stream.json`:

```json
{
  "feed_name": "new_stream",
  "feed_type": "stream",
  "ksqldb_source": "new_stream_ksqldb",
  "description": "Description du nouveau stream",
  "partitioning": {
    "type": "date",
    "columns": ["year", "month", "day"]
  },
  "storage_mode": "append",
  "format": "parquet",
  "retention_days": 365,
  "enabled": true,
  "created_at": "2025-01-15T10:00:00Z"
}
```

Le feed sera automatiquement détecté lors du prochain export.

---

## 📖 Lecture des Données

### Avec Pandas

```python
import pandas as pd

# Lire un stream avec filtre par date
df = pd.read_parquet(
    'data_lake/streams/transaction_stream_anonymized',
    filters=[('year', '=', 2025), ('month', '=', 1)]
)

# Lire une table (dernière version)
df = pd.read_parquet(
    'data_lake/tables/user_transaction_summary/version=v3'
)
```

### Avec DuckDB

```python
import duckdb

# Requête SQL sur le data lake
result = duckdb.sql("""
    SELECT 
        user_id,
        SUM(amount) as total_amount
    FROM 'data_lake/streams/transaction_stream_anonymized/**/*.parquet'
    WHERE year = 2025 AND month = 1
    GROUP BY user_id
""").df()
```

---

## 🔐 Sécurité et Conformité

### Niveaux de Sécurité

1. **Données brutes** - Accès restreint
   ```bash
   chmod 750 data_lake/streams/transaction_stream/
   ```

2. **Données anonymisées** - Conformité RGPD
   ```bash
   chmod 755 data_lake/streams/transaction_stream_anonymized/
   ```

3. **Agrégations** - Accès étendu
   ```bash
   chmod 755 data_lake/tables/
   ```

---

## 📈 Streams et Tables Configurés

### Streams (4)

| Stream | Description | Rétention |
|--------|-------------|-----------|
| `transaction_stream` | Données brutes | 365 jours |
| `transaction_flattened` | Schéma aplati | 365 jours |
| `transaction_stream_anonymized` | Anonymisé + EUR | 730 jours |
| `transaction_stream_blacklisted` | Villes blacklistées | 365 jours |

### Tables (4)

| Table | Description | Versions |
|-------|-------------|----------|
| `user_transaction_summary` | Montants par utilisateur | 7 |
| `user_transaction_summary_eur` | Montants en EUR | 7 |
| `payment_method_totals` | Totaux par méthode | 7 |
| `product_purchase_counts` | Compteurs par produit | 7 |

---

## 🔧 Configuration

### ksqlDB

Modifier dans `data_lake_config.py`:

```python
KSQLDB_CONFIG = {
    "host": "localhost",
    "port": 8088,
    "timeout": 30
}
```

### Parquet

```python
STORAGE_FORMAT = "parquet"
PARQUET_COMPRESSION = "snappy"
BATCH_SIZE = 10000
```

---

## 🤖 Automatisation

### Cron Job (Export Quotidien)

```bash
# Ajouter au crontab
crontab -e

# Export quotidien à 2h du matin
0 2 * * * cd /Users/alice/Downloads/data_lake && python export_to_data_lake.py --all >> data_lake/logs/cron.log 2>&1
```

---

## 📊 Métadonnées

Chaque stream/table contient `_metadata.json`:

```json
{
  "source": "transaction_stream",
  "type": "stream",
  "storage_mode": "append",
  "format": "parquet",
  "partitioning": "date",
  "last_export": "2025-01-15T14:30:00Z",
  "total_records": 150000,
  "total_size_mb": 45.2,
  "partitions": [...]
}
```

---

## 🧪 Tests

```bash
# Valider l'installation complète
python test_setup.py

# Résultat attendu:
# ✓ Installation validée avec succès!
# 7/7 tests réussis
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **DESIGN_DOCUMENT.md** | Design complet avec justifications techniques |
| **ARCHITECTURE.md** | Diagrammes et architecture détaillée |
| **QUICKSTART.md** | Guide de démarrage rapide |
| **SUMMARY.md** | Résumé exécutif du projet |
| **data_lake/README.md** | Documentation utilisateur détaillée |

---

## 🔮 Roadmap

### Phase 1: MVP ✅
- [x] Export local
- [x] Partitionnement date/version
- [x] Format Parquet
- [x] Gestion des feeds

### Phase 2: Cloud
- [ ] Export vers S3/Azure Blob
- [ ] Tiering de stockage
- [ ] Catalogue de données

### Phase 3: Advanced
- [ ] Delta Lake (ACID)
- [ ] Time travel queries
- [ ] Streaming temps réel
- [ ] Data quality checks

---

## 🐛 Troubleshooting

### Erreur de connexion ksqlDB

```bash
# Vérifier que ksqlDB est accessible
curl http://localhost:8088/info
```

### Permissions insuffisantes

```bash
# Donner les permissions
chmod -R 755 data_lake/
```

### Consulter les logs

```bash
# Logs d'export
tail -f data_lake/logs/export_*.log
```

---

## 🤝 Support

Pour toute question:
1. Consulter la documentation dans `DESIGN_DOCUMENT.md`
2. Vérifier les exemples dans `QUICKSTART.md`
3. Examiner les logs dans `data_lake/logs/`

---

## 📝 License

MIT License - Voir LICENSE pour plus de détails

---

**Version**: 1.0  
**Dernière mise à jour**: Janvier 2025  
**Statut**: ✅ Production Ready
