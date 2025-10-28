# 🏗️ Document de Design - Data Lake

## 📋 Vue d'ensemble

Ce document décrit l'architecture complète du Data Lake conçu pour stocker et gérer les données provenant de ksqlDB. Le data lake est implémenté sur le système de fichiers local avec un partitionnement intelligent et une gestion automatisée des feeds.

---

## 🎯 Objectifs du Design

1. **Stockage structuré** des données ksqlDB (streams et tables)
2. **Partitionnement optimisé** par date pour les streams et par version pour les tables
3. **Extensibilité** pour l'ajout de nouveaux feeds sans modification du code
4. **Traçabilité** complète avec métadonnées et logs
5. **Performance** optimale pour les requêtes analytiques

---

## 🗂️ Architecture du Data Lake

### Structure des Dossiers

```
data_lake/
├── streams/                    # Données des streams (événements immuables)
│   ├── transaction_stream/
│   │   ├── year=2025/
│   │   │   ├── month=01/
│   │   │   │   ├── day=15/
│   │   │   │   │   └── data_20250115_*.parquet
│   │   │   │   └── day=16/
│   │   └── _metadata.json
│   │
│   ├── transaction_flattened/
│   ├── transaction_stream_anonymized/
│   └── transaction_stream_blacklisted/
│
├── tables/                     # Données des tables (agrégations)
│   ├── user_transaction_summary/
│   │   ├── version=v1/
│   │   │   └── snapshot_20250115_*.parquet
│   │   ├── version=v2/
│   │   └── _metadata.json
│   │
│   ├── user_transaction_summary_eur/
│   ├── payment_method_totals/
│   └── product_purchase_counts/
│
├── feeds/                      # Configuration des feeds
│   ├── active/                 # Feeds actifs
│   │   ├── transaction_stream.json
│   │   └── transaction_stream_anonymized.json
│   └── archived/               # Feeds archivés
│
└── logs/                       # Logs d'export
    └── export_2025_01.log
```

---

## 📊 Stratégie de Partitionnement

### Partitionnement par Date (Streams)

**Utilisé pour**: Tous les streams de transactions

**Structure**: `year=YYYY/month=MM/day=DD/`

**Avantages**:
- ✅ **Requêtes rapides** filtrées par période
- ✅ **Maintenance facile** (suppression des anciennes partitions)
- ✅ **Scalabilité** (ajout sans impact sur l'existant)
- ✅ **Parallélisme** (lecture/écriture parallèle)
- ✅ **Archivage sélectif** des anciennes données

**Exemple de requête optimisée**:
```python
# Lire uniquement janvier 2025
df = pd.read_parquet(
    'data_lake/streams/transaction_stream',
    filters=[('year', '=', 2025), ('month', '=', 1)]
)
```

### Partitionnement par Version (Tables)

**Utilisé pour**: Toutes les tables d'agrégation

**Structure**: `version=vX/`

**Avantages**:
- ✅ **Snapshots complets** de l'état à un instant T
- ✅ **Historique des versions** pour audit
- ✅ **Rollback facile** en cas de problème
- ✅ **Comparaison** entre versions
- ✅ **Rétention configurable** (garder N dernières versions)

**Exemple**:
```
version=v1/  → Snapshot du 15/01/2025
version=v2/  → Snapshot du 16/01/2025
version=v3/  → Snapshot du 17/01/2025
```

---

## 💾 Modes de Stockage

### Mode APPEND (Streams)

**Principe**: Ajouter sans modifier l'existant

**Justification**:
- Les streams représentent des **événements immuables**
- Chaque transaction est **unique** et ne doit jamais être modifiée
- Permet de **conserver l'historique complet** pour audit
- Facilite le **replay** des données
- Optimise les **performances d'écriture**
- Compatible avec **Event Sourcing**

**Implémentation**:
```python
# Chaque export crée un nouveau fichier
file_path = partition_path / f"data_{timestamp}.parquet"
pq.write_table(table, file_path)
```

### Mode OVERWRITE (Tables)

**Principe**: Remplacer complètement la version

**Justification**:
- Les tables contiennent des **agrégations calculées**
- Chaque export = **snapshot complet** de l'état actuel
- Évite la **duplication** de données agrégées
- Simplifie les **requêtes analytiques**
- Réduit l'**espace disque**
- Facilite la **maintenance**

**Implémentation**:
```python
# Nouvelle version à chaque export
version = get_next_version()
partition_path = base_path / f"version=v{version}"
pq.write_table(table, partition_path / f"snapshot_{timestamp}.parquet")
```

### Mode IGNORE (Non utilisé)

**Pourquoi pas utilisé**:
- ❌ Ne convient pas aux streams (besoin d'ajouter continuellement)
- ❌ Ne convient pas aux tables (besoin de mettre à jour)
- ⚠️ Pourrait être utilisé pour des **données de référence statiques**

---

## 📁 Format de Stockage: Apache Parquet

### Choix du Format

**Format sélectionné**: Apache Parquet avec compression Snappy

### Justifications Techniques

1. **Compression efficace**
   - Réduction de 70-90% vs JSON/CSV
   - Compression Snappy: bon compromis vitesse/taille

2. **Format columnaire**
   - Lecture optimisée pour l'analytique
   - Lecture sélective des colonnes nécessaires
   - Agrégations ultra-rapides

3. **Schéma intégré**
   - Pas besoin de fichier de schéma séparé
   - Validation automatique des types
   - Évolution du schéma facilitée

4. **Compatibilité**
   - Pandas, Polars, DuckDB
   - Apache Spark, Apache Arrow
   - AWS Athena, Google BigQuery

5. **Partitionnement natif**
   - Support des partitions Hive-style
   - Predicate pushdown automatique

6. **Types complexes**
   - STRUCT, ARRAY, MAP supportés
   - Nested data structures

### Configuration Parquet

```python
pq.write_table(
    table,
    file_path,
    compression='snappy',      # Compression rapide
    use_dictionary=True,       # Compression des valeurs répétées
    write_statistics=True      # Stats pour predicate pushdown
)
```

---

## 🔄 Gestion des Nouveaux Feeds

### Processus d'Ajout

1. **Créer la configuration** du feed (JSON)
2. **Détection automatique** par les scripts
3. **Création automatique** de la structure de dossiers
4. **Export des données** selon la configuration

### Configuration d'un Feed

```json
{
  "feed_name": "payment_stream",
  "feed_type": "stream",
  "ksqldb_source": "payment_stream",
  "description": "Stream des paiements",
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

### Commandes de Gestion

```bash
# Ajouter un nouveau feed
python manage_feeds.py add \
  --name payment_stream \
  --type stream \
  --source payment_stream \
  --description "Stream des paiements"

# Lister les feeds
python manage_feeds.py list

# Désactiver un feed
python manage_feeds.py disable payment_stream

# Archiver un feed
python manage_feeds.py archive payment_stream
```

---

## 🔐 Sécurité et Conformité

### Données Anonymisées

- **Stream anonymisé**: `transaction_stream_anonymized`
- **Conformité RGPD**: Rétention de 2 ans
- **Données sensibles**: Isolées dans des streams séparés

### Permissions Recommandées

```bash
# Streams bruts: accès restreint
chmod 750 data_lake/streams/transaction_stream/

# Streams anonymisés: accès étendu
chmod 755 data_lake/streams/transaction_stream_anonymized/

# Tables: accès étendu
chmod 755 data_lake/tables/
```

### Isolation des Données

- **Blacklist**: Stream séparé `transaction_stream_blacklisted`
- **Audit trail**: Logs complets de tous les exports
- **Métadonnées**: Traçabilité complète

---

## 📈 Métadonnées et Monitoring

### Fichier _metadata.json

Chaque stream/table contient un fichier de métadonnées:

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
  "partitions": [
    {
      "path": "year=2025/month=01/day=15",
      "records": 5000,
      "size_mb": 1.5,
      "exported_at": "2025-01-15T14:30:00Z"
    }
  ],
  "schema_version": "1.0",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Utilitaires de Monitoring

```bash
# Générer un rapport complet
python metadata_utils.py --report

# Afficher les statistiques
python metadata_utils.py --stats

# Exporter en CSV
python metadata_utils.py --csv data_lake_report.csv
```

---

## 🚀 Utilisation

### Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Créer la structure du data lake
python data_lake_config.py

# Synchroniser les feeds depuis la configuration
python manage_feeds.py sync
```

### Export des Données

```bash
# Exporter tous les streams et tables
python export_to_data_lake.py --all

# Exporter un stream spécifique
python export_to_data_lake.py --stream transaction_stream_anonymized

# Exporter une table spécifique
python export_to_data_lake.py --table user_transaction_summary

# Exporter avec une date spécifique
python export_to_data_lake.py --stream transaction_stream --date 2025-01-15
```

### Export Automatique (Cron)

```bash
# Ajouter au crontab pour export quotidien à 2h du matin
0 2 * * * cd /path/to/project && python export_to_data_lake.py --all >> logs/export.log 2>&1
```

---

## 📊 Mapping Streams/Tables ksqlDB

### Streams Configurés

| Stream ksqlDB | Type | Partitionnement | Mode | Rétention |
|---------------|------|-----------------|------|-----------|
| `transaction_stream` | Stream | Date | APPEND | 365 jours |
| `transaction_flattened` | Stream | Date | APPEND | 365 jours |
| `transaction_stream_anonymized` | Stream | Date | APPEND | 730 jours |
| `transaction_stream_blacklisted` | Stream | Date | APPEND | 365 jours |

### Tables Configurées

| Table ksqlDB | Type | Partitionnement | Mode | Rétention |
|--------------|------|-----------------|------|-----------|
| `user_transaction_summary` | Table | Version | OVERWRITE | 7 versions |
| `user_transaction_summary_eur` | Table | Version | OVERWRITE | 7 versions |
| `payment_method_totals` | Table | Version | OVERWRITE | 7 versions |
| `product_purchase_counts` | Table | Version | OVERWRITE | 7 versions |

---

## 🔧 Configuration Technique

### Configuration ksqlDB

```python
KSQLDB_CONFIG = {
    "host": "localhost",
    "port": 8088,
    "timeout": 30
}
```

### Configuration Parquet

```python
STORAGE_FORMAT = "parquet"
PARQUET_COMPRESSION = "snappy"
BATCH_SIZE = 10000
```

### Configuration des Logs

```python
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
```

---

## 🎯 Évolution Future

### Extensions Possibles

1. **Compression avancée**
   - Tester ZSTD pour meilleure compression
   - Benchmark Snappy vs LZ4 vs ZSTD

2. **Tiering de stockage**
   - Déplacer anciennes données vers S3/Azure Blob
   - Implémentation d'une politique de lifecycle

3. **Indexation**
   - Créer des index pour accélérer les recherches
   - Bloom filters pour les lookups

4. **Catalogue de données**
   - Intégration avec Apache Hive Metastore
   - Support AWS Glue Data Catalog

5. **Qualité des données**
   - Validations automatiques
   - Data quality checks
   - Alertes sur anomalies

6. **Versioning avancé**
   - Implémentation Delta Lake
   - Time travel queries
   - ACID transactions

7. **Streaming en temps réel**
   - Intégration Apache Kafka
   - Micro-batching pour latence réduite

---

## 📚 Fichiers du Projet

### Scripts Principaux

- **`data_lake_config.py`** - Configuration centralisée
- **`export_to_data_lake.py`** - Script d'export principal
- **`manage_feeds.py`** - Gestion des feeds
- **`metadata_utils.py`** - Utilitaires de métadonnées

### Configuration

- **`requirements.txt`** - Dépendances Python
- **`data_lake/feeds/active/*.json`** - Configuration des feeds actifs

### Documentation

- **`data_lake/README.md`** - Documentation utilisateur
- **`DESIGN_DOCUMENT.md`** - Ce document

---

## ✅ Checklist de Validation

- [x] Structure de dossiers définie et justifiée
- [x] Partitionnement par date pour les streams
- [x] Partitionnement par version pour les tables
- [x] Modes de stockage justifiés (APPEND/OVERWRITE)
- [x] Format Parquet avec compression
- [x] Gestion extensible des nouveaux feeds
- [x] Métadonnées complètes
- [x] Scripts d'export automatisés
- [x] Gestion des feeds (add/update/archive)
- [x] Utilitaires de monitoring
- [x] Documentation complète
- [x] Sécurité et conformité RGPD

---

## 📞 Support

Pour toute question ou suggestion d'amélioration, consulter:
- Documentation complète: `data_lake/README.md`
- Exemples de feeds: `data_lake/feeds/active/`
- Logs d'export: `data_lake/logs/`

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Auteur**: Data Engineering Team
