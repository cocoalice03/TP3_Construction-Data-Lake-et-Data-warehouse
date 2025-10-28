# 🏛️ Architecture du Data Lake

## Vue d'ensemble du Système

```
┌─────────────────────────────────────────────────────────────────────┐
│                          KSQLDB SERVER                              │
│  ┌──────────────────────┐      ┌──────────────────────┐            │
│  │   STREAMS            │      │   TABLES             │            │
│  │  - transaction_stream│      │  - user_summary      │            │
│  │  - flattened         │      │  - payment_totals    │            │
│  │  - anonymized        │      │  - product_counts    │            │
│  │  - blacklisted       │      │                      │            │
│  └──────────────────────┘      └──────────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP API
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXPORT LAYER (Python)                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  KsqlDBClient                                                 │  │
│  │  - execute_query()                                            │  │
│  │  - get_stream_data()                                          │  │
│  │  - get_table_data()                                           │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                    │                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  DataLakeExporter                                             │  │
│  │  - export_stream() → APPEND mode                              │  │
│  │  - export_table() → OVERWRITE mode                            │  │
│  │  - _write_parquet()                                           │  │
│  │  - _update_metadata()                                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Write Parquet
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAKE (File System)                        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  STREAMS (APPEND Mode)                                       │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ transaction_stream/                                     │ │  │
│  │  │   year=2025/month=01/day=15/                            │ │  │
│  │  │     ├── data_20250115_120000.parquet                    │ │  │
│  │  │     ├── data_20250115_140000.parquet                    │ │  │
│  │  │     └── data_20250115_160000.parquet                    │ │  │
│  │  │   _metadata.json                                        │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  TABLES (OVERWRITE Mode)                                    │  │
│  │  ┌────────────────────────────────────────────────────────┐ │  │
│  │  │ user_transaction_summary/                               │ │  │
│  │  │   version=v1/                                           │ │  │
│  │  │     └── snapshot_20250115_120000.parquet                │ │  │
│  │  │   version=v2/                                           │ │  │
│  │  │     └── snapshot_20250116_120000.parquet                │ │  │
│  │  │   _metadata.json                                        │ │  │
│  │  └────────────────────────────────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  FEEDS (Configuration)                                      │  │
│  │    active/                                                  │  │
│  │      ├── transaction_stream.json                            │  │
│  │      └── user_transaction_summary.json                      │  │
│  │    archived/                                                │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Read Parquet
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ANALYTICS LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Pandas     │  │   DuckDB     │  │   Spark      │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Flux de Données

### 1. Export des Streams (Mode APPEND)

```
ksqlDB Stream → KsqlDBClient.get_stream_data()
                      ↓
              DataFrame (Pandas)
                      ↓
         DataLakeExporter.export_stream()
                      ↓
         Partitionnement par date
         year=2025/month=01/day=15/
                      ↓
         Nouveau fichier Parquet
         data_20250115_120000.parquet
                      ↓
         Mise à jour _metadata.json
```

### 2. Export des Tables (Mode OVERWRITE)

```
ksqlDB Table → KsqlDBClient.get_table_data()
                      ↓
              DataFrame (Pandas)
                      ↓
         DataLakeExporter.export_table()
                      ↓
         Nouvelle version
         version=v{N+1}/
                      ↓
         Fichier Parquet
         snapshot_20250115_120000.parquet
                      ↓
         Mise à jour _metadata.json
                      ↓
         Nettoyage anciennes versions
         (rétention: 7 versions)
```

---

## Composants du Système

### 1. Configuration (`data_lake_config.py`)

```
┌────────────────────────────────────┐
│  Configuration Centralisée         │
├────────────────────────────────────┤
│  • Chemins du data lake            │
│  • Configuration ksqlDB            │
│  • Mapping streams/tables          │
│  • Modes de stockage               │
│  • Paramètres Parquet              │
│  • Rétention des données           │
└────────────────────────────────────┘
```

### 2. Export (`export_to_data_lake.py`)

```
┌────────────────────────────────────┐
│  KsqlDBClient                      │
├────────────────────────────────────┤
│  • Connexion à ksqlDB              │
│  • Exécution de requêtes           │
│  • Récupération des données        │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│  DataLakeExporter                  │
├────────────────────────────────────┤
│  • export_stream()                 │
│  • export_table()                  │
│  • Partitionnement                 │
│  • Écriture Parquet                │
│  • Gestion métadonnées             │
│  • Nettoyage versions              │
└────────────────────────────────────┘
```

### 3. Gestion des Feeds (`manage_feeds.py`)

```
┌────────────────────────────────────┐
│  FeedManager                       │
├────────────────────────────────────┤
│  • add_feed()                      │
│  • update_feed()                   │
│  • enable_feed()                   │
│  • disable_feed()                  │
│  • archive_feed()                  │
│  • restore_feed()                  │
│  • delete_feed()                   │
│  • sync_from_config()              │
└────────────────────────────────────┘
```

### 4. Métadonnées (`metadata_utils.py`)

```
┌────────────────────────────────────┐
│  MetadataReader                    │
├────────────────────────────────────┤
│  • read_metadata()                 │
│  • list_all_metadata()             │
│  • get_statistics()                │
│  • get_partition_info()            │
└────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│  MetadataAnalyzer                  │
├────────────────────────────────────┤
│  • generate_report()               │
│  • export_to_csv()                 │
└────────────────────────────────────┘
```

---

## Décisions d'Architecture

### 1. Partitionnement

| Type | Stratégie | Raison |
|------|-----------|--------|
| **Streams** | Date (year/month/day) | Événements temporels, requêtes par période |
| **Tables** | Version (v1, v2, ...) | Snapshots, historique, rollback |

### 2. Modes de Stockage

| Type | Mode | Raison |
|------|------|--------|
| **Streams** | APPEND | Événements immuables, historique complet |
| **Tables** | OVERWRITE | Agrégations, état actuel, pas de duplication |

### 3. Format de Fichier

| Aspect | Choix | Raison |
|--------|-------|--------|
| **Format** | Parquet | Compression, performance, compatibilité |
| **Compression** | Snappy | Bon compromis vitesse/taille |
| **Encoding** | Dictionary | Optimisation valeurs répétées |

---

## Patterns de Conception

### 1. Factory Pattern (Feeds)

```python
def create_feed(feed_type: FeedType, config: dict):
    if feed_type == FeedType.STREAM:
        return StreamFeed(config)
    elif feed_type == FeedType.TABLE:
        return TableFeed(config)
```

### 2. Strategy Pattern (Storage Mode)

```python
class StorageStrategy:
    def write(self, data, path):
        pass

class AppendStrategy(StorageStrategy):
    def write(self, data, path):
        # Ajouter nouveau fichier
        
class OverwriteStrategy(StorageStrategy):
    def write(self, data, path):
        # Remplacer version
```

### 3. Template Method (Export)

```python
class BaseExporter:
    def export(self):
        self.fetch_data()
        self.partition_data()
        self.write_data()
        self.update_metadata()
```

---

## Scalabilité

### Scalabilité Horizontale

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Worker 1    │     │  Worker 2    │     │  Worker 3    │
│  Streams     │     │  Tables      │     │  Monitoring  │
│  1-10        │     │  1-5         │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                    │
        └────────────────────┴────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Data Lake     │
                    └─────────────────┘
```

### Scalabilité Verticale

- **Batch size**: Configurable (défaut: 10000)
- **Parallélisme**: Lecture/écriture parallèle par partition
- **Compression**: Réduction de l'espace disque

---

## Monitoring et Observabilité

### Logs

```
data_lake/logs/
├── export_2025_01.log    # Logs d'export
├── feed_2025_01.log      # Logs de gestion feeds
└── metadata_2025_01.log  # Logs de métadonnées
```

### Métadonnées

```json
{
  "source": "transaction_stream",
  "last_export": "2025-01-15T14:30:00Z",
  "total_records": 150000,
  "total_size_mb": 45.2,
  "partitions": [...]
}
```

### Métriques

- Nombre d'enregistrements exportés
- Taille des données
- Temps d'export
- Erreurs et warnings

---

## Sécurité

### Niveaux de Sécurité

```
┌─────────────────────────────────────┐
│  Niveau 1: Données Brutes           │
│  - transaction_stream               │
│  - Permissions: 750 (restreint)     │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Niveau 2: Données Anonymisées      │
│  - transaction_stream_anonymized    │
│  - Permissions: 755 (étendu)        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Niveau 3: Agrégations              │
│  - Tables d'agrégation              │
│  - Permissions: 755 (étendu)        │
└─────────────────────────────────────┘
```

---

## Performance

### Optimisations

1. **Predicate Pushdown**
   - Filtres au niveau Parquet
   - Lecture sélective des partitions

2. **Column Pruning**
   - Lecture uniquement des colonnes nécessaires
   - Format columnaire

3. **Compression**
   - Snappy: rapide et efficace
   - Réduction 70-90% de l'espace

4. **Partitionnement**
   - Parallélisme naturel
   - Skip de partitions non pertinentes

---

## Évolution

### Phase 1: MVP (Actuel)
- ✅ Export local
- ✅ Partitionnement date/version
- ✅ Format Parquet
- ✅ Gestion des feeds

### Phase 2: Cloud
- ☐ Export vers S3/Azure Blob
- ☐ Tiering de stockage
- ☐ Catalogue de données

### Phase 3: Advanced
- ☐ Delta Lake
- ☐ Time travel
- ☐ ACID transactions
- ☐ Streaming en temps réel
