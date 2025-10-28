# 🚀 Guide de Démarrage Rapide - Data Lake

## Installation

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Créer la structure du data lake

```bash
python data_lake_config.py
```

### 3. Synchroniser les feeds

```bash
python manage_feeds.py sync
```

---

## Utilisation Basique

### Exporter toutes les données

```bash
python export_to_data_lake.py --all
```

### Exporter un stream spécifique

```bash
python export_to_data_lake.py --stream transaction_stream_anonymized
```

### Exporter une table spécifique

```bash
python export_to_data_lake.py --table user_transaction_summary
```

---

## Gestion des Feeds

### Lister les feeds actifs

```bash
python manage_feeds.py list
```

### Ajouter un nouveau feed

```bash
python manage_feeds.py add \
  --name new_stream \
  --type stream \
  --source new_stream \
  --description "Description du nouveau stream"
```

### Désactiver un feed

```bash
python manage_feeds.py disable transaction_stream
```

### Archiver un feed

```bash
python manage_feeds.py archive old_stream
```

---

## Monitoring

### Afficher les statistiques

```bash
python metadata_utils.py --stats
```

### Générer un rapport complet

```bash
python metadata_utils.py --report
```

### Exporter en CSV

```bash
python metadata_utils.py --csv report.csv
```

---

## Configuration ksqlDB

Modifier dans `data_lake_config.py`:

```python
KSQLDB_CONFIG = {
    "host": "localhost",  # Votre host ksqlDB
    "port": 8088,         # Votre port ksqlDB
    "timeout": 30
}
```

---

## Export Automatique

### Ajouter au crontab

```bash
# Export quotidien à 2h du matin
0 2 * * * cd /path/to/project && python export_to_data_lake.py --all >> logs/export.log 2>&1
```

---

## Structure du Data Lake

```
data_lake/
├── streams/           # Données des streams (mode APPEND)
│   └── transaction_stream/
│       └── year=2025/month=01/day=15/
│           └── data_*.parquet
│
├── tables/            # Données des tables (mode OVERWRITE)
│   └── user_transaction_summary/
│       └── version=v1/
│           └── snapshot_*.parquet
│
├── feeds/             # Configuration des feeds
│   ├── active/
│   └── archived/
│
└── logs/              # Logs d'export
```

---

## Lecture des Données

### Avec Pandas

```python
import pandas as pd

# Lire un stream avec filtre par date
df = pd.read_parquet(
    'data_lake/streams/transaction_stream_anonymized',
    filters=[('year', '=', 2025), ('month', '=', 1)]
)

# Lire une table (dernière version)
df = pd.read_parquet('data_lake/tables/user_transaction_summary/version=v1')
```

### Avec DuckDB

```python
import duckdb

# Requête SQL sur le data lake
result = duckdb.sql("""
    SELECT * FROM 'data_lake/streams/transaction_stream_anonymized/**/*.parquet'
    WHERE year = 2025 AND month = 1
""").df()
```

---

## Troubleshooting

### Erreur de connexion ksqlDB

Vérifier que ksqlDB est accessible:

```bash
curl http://localhost:8088/info
```

### Permissions insuffisantes

```bash
chmod -R 755 data_lake/
```

### Logs d'export

```bash
tail -f data_lake/logs/export_*.log
```

---

## Documentation Complète

- **Architecture**: `DESIGN_DOCUMENT.md`
- **Documentation utilisateur**: `data_lake/README.md`
- **Configuration**: `data_lake_config.py`
