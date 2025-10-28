# 🔄 Flux de Données - Data Lake

## Vue d'ensemble du Flux

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCE: KSQLDB                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTP API (port 8088)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTRACTION (KsqlDBClient)                        │
│  • execute_query("SELECT * FROM stream/table")                     │
│  • Conversion en DataFrame Pandas                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  TRANSFORMATION (DataLakeExporter)                  │
│  • Détermination du mode de stockage (APPEND/OVERWRITE)            │
│  • Calcul du partitionnement (date/version)                        │
│  • Conversion en format Parquet                                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STOCKAGE (File System)                           │
│  • Écriture des fichiers .parquet                                  │
│  • Mise à jour des métadonnées                                     │
│  • Logging des opérations                                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CONSOMMATION (Analytics)                         │
│  • Pandas, DuckDB, Spark                                           │
│  • Requêtes analytiques                                            │
│  • Visualisations                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Flux Détaillé: Export d'un Stream

### Étape 1: Requête ksqlDB

```python
# KsqlDBClient.get_stream_data()
query = "SELECT * FROM transaction_stream EMIT CHANGES"
response = requests.post(
    "http://localhost:8088/query",
    json={"ksql": query}
)
```

**Données brutes (JSON)**:
```json
{"row": {"columns": [1, "user123", 100.50, "2025-01-15T10:00:00Z"]}}
{"row": {"columns": [2, "user456", 250.00, "2025-01-15T10:05:00Z"]}}
{"row": {"columns": [3, "user789", 75.25, "2025-01-15T10:10:00Z"]}}
```

### Étape 2: Conversion en DataFrame

```python
# Conversion en Pandas DataFrame
df = pd.DataFrame(results)
```

**DataFrame**:
```
   id    user_id  amount            timestamp
0   1    user123  100.50  2025-01-15T10:00:00Z
1   2    user456  250.00  2025-01-15T10:05:00Z
2   3    user789   75.25  2025-01-15T10:10:00Z
```

### Étape 3: Partitionnement

```python
# Calcul du chemin de partition
date = datetime(2025, 1, 15)
partition_path = get_date_partition_path(
    base_path,
    year=2025,
    month=1,
    day=15
)
# → data_lake/streams/transaction_stream/year=2025/month=01/day=15/
```

### Étape 4: Écriture Parquet

```python
# Conversion en Arrow Table
table = pa.Table.from_pandas(df)

# Écriture avec compression
pq.write_table(
    table,
    file_path,
    compression='snappy',
    use_dictionary=True,
    write_statistics=True
)
```

**Fichier créé**:
```
data_lake/streams/transaction_stream/
└── year=2025/month=01/day=15/
    └── data_20250115_120000.parquet  (15.2 KB)
```

### Étape 5: Métadonnées

```python
# Mise à jour _metadata.json
metadata = {
    "source": "transaction_stream",
    "last_export": "2025-01-15T12:00:00Z",
    "total_records": 3,
    "total_size_mb": 0.015,
    "partitions": [
        {
            "path": "year=2025/month=01/day=15",
            "records": 3,
            "size_mb": 0.015
        }
    ]
}
```

---

## Flux Détaillé: Export d'une Table

### Étape 1: Requête ksqlDB

```python
# KsqlDBClient.get_table_data()
query = "SELECT * FROM user_transaction_summary"
response = requests.post(
    "http://localhost:8088/query",
    json={"ksql": query}
)
```

**Données (agrégées)**:
```json
{"row": {"columns": ["user123", 1500.50, 15]}}
{"row": {"columns": ["user456", 3200.00, 28]}}
{"row": {"columns": ["user789", 850.75, 12]}}
```

### Étape 2: Détermination de la Version

```python
# Calcul de la prochaine version
current_versions = [1, 2, 3]  # Versions existantes
next_version = max(current_versions) + 1  # → 4
```

### Étape 3: Partitionnement par Version

```python
partition_path = get_version_partition_path(
    base_path,
    version=4
)
# → data_lake/tables/user_transaction_summary/version=v4/
```

### Étape 4: Écriture (Mode OVERWRITE)

```python
# Nouvelle version complète
pq.write_table(
    table,
    partition_path / f"snapshot_{timestamp}.parquet"
)
```

**Structure créée**:
```
data_lake/tables/user_transaction_summary/
├── version=v1/  (ancienne)
├── version=v2/  (ancienne)
├── version=v3/  (ancienne)
└── version=v4/  (nouvelle)
    └── snapshot_20250115_120000.parquet
```

### Étape 5: Nettoyage

```python
# Rétention: 7 versions
# Suppression des versions > 7
if len(versions) > 7:
    for old_version in versions[7:]:
        shutil.rmtree(old_version)
```

**Après nettoyage**:
```
data_lake/tables/user_transaction_summary/
├── version=v4/  (conservée)
├── version=v3/  (conservée)
├── version=v2/  (conservée)
└── version=v1/  (conservée si < 7 versions)
```

---

## Comparaison: Stream vs Table

### Stream (APPEND)

```
Jour 1:
└── year=2025/month=01/day=15/
    ├── data_20250115_120000.parquet  (100 records)
    └── data_20250115_140000.parquet  (150 records)

Jour 2:
└── year=2025/month=01/day=16/
    ├── data_20250116_120000.parquet  (120 records)
    └── data_20250116_140000.parquet  (180 records)

Total: 550 records (tous conservés)
```

### Table (OVERWRITE)

```
Export 1:
└── version=v1/
    └── snapshot_20250115_120000.parquet  (1000 records)

Export 2:
└── version=v2/
    └── snapshot_20250116_120000.parquet  (1050 records)

Export 3:
└── version=v3/
    └── snapshot_20250117_120000.parquet  (1100 records)

Total: 3 versions (snapshots complets)
```

---

## Flux de Lecture

### Lecture d'un Stream avec Filtre

```python
# Requête: Transactions de janvier 2025
df = pd.read_parquet(
    'data_lake/streams/transaction_stream',
    filters=[
        ('year', '=', 2025),
        ('month', '=', 1)
    ]
)
```

**Optimisation (Predicate Pushdown)**:
```
1. Scan des partitions disponibles
   ✓ year=2025/month=01/day=01/
   ✓ year=2025/month=01/day=02/
   ...
   ✓ year=2025/month=01/day=31/
   ✗ year=2025/month=02/  (skip)
   ✗ year=2024/          (skip)

2. Lecture uniquement des partitions matchées
   → Gain de performance significatif
```

### Lecture d'une Table (Dernière Version)

```python
# Requête: Dernière version de la table
df = pd.read_parquet(
    'data_lake/tables/user_transaction_summary/version=v4'
)
```

**Avantages**:
- Snapshot complet et cohérent
- Pas besoin d'agrégation
- Lecture directe

---

## Flux de Gestion des Feeds

### Ajout d'un Nouveau Feed

```
1. Création de la configuration
   ↓
   manage_feeds.py add --name new_stream ...
   ↓
2. Génération du fichier JSON
   ↓
   data_lake/feeds/active/new_stream.json
   ↓
3. Création de la structure
   ↓
   data_lake/streams/new_stream/
   ↓
4. Feed prêt pour l'export
   ↓
   export_to_data_lake.py --stream new_stream
```

### Archivage d'un Feed

```
1. Commande d'archivage
   ↓
   manage_feeds.py archive old_stream
   ↓
2. Déplacement de la configuration
   ↓
   feeds/active/old_stream.json → feeds/archived/old_stream.json
   ↓
3. Désactivation du feed
   ↓
   "enabled": false
   ↓
4. Feed archivé (données conservées)
```

---

## Flux de Monitoring

### Génération de Rapport

```
1. Lecture des métadonnées
   ↓
   MetadataReader.list_all_metadata()
   ↓
2. Agrégation des statistiques
   ↓
   • Total records
   • Total size
   • Last exports
   ↓
3. Génération du rapport
   ↓
   MetadataAnalyzer.generate_report()
   ↓
4. Affichage ou export
   ↓
   Console / CSV / JSON
```

---

## Chronologie d'un Export Complet

```
T+0s    : Démarrage export_to_data_lake.py --all
T+1s    : Connexion à ksqlDB
T+2s    : Récupération transaction_stream (1000 records)
T+3s    : Partitionnement par date
T+4s    : Écriture Parquet (compression)
T+5s    : Mise à jour métadonnées
T+6s    : Récupération transaction_flattened (1000 records)
...
T+30s   : Récupération user_transaction_summary (50 records)
T+31s   : Partitionnement par version
T+32s   : Écriture Parquet
T+33s   : Nettoyage anciennes versions
T+34s   : Mise à jour métadonnées
...
T+60s   : Export terminé
          ✓ 4 streams exportés
          ✓ 4 tables exportées
          ✓ 8 fichiers de métadonnées mis à jour
```

---

## Flux d'Erreur et Récupération

### Erreur de Connexion ksqlDB

```
1. Tentative de connexion
   ↓
   KsqlDBClient(host, port)
   ↓
2. Timeout ou erreur
   ↓
   requests.exceptions.ConnectionError
   ↓
3. Log de l'erreur
   ↓
   logger.error("Impossible de se connecter à ksqlDB")
   ↓
4. Arrêt gracieux
   ↓
   sys.exit(1)
```

### Erreur d'Écriture

```
1. Tentative d'écriture Parquet
   ↓
   pq.write_table(table, file_path)
   ↓
2. Erreur (permissions, espace disque)
   ↓
   OSError / IOError
   ↓
3. Rollback
   ↓
   • Suppression fichier partiel
   • Pas de mise à jour métadonnées
   ↓
4. Log et rapport d'erreur
   ↓
   logger.error("Erreur lors de l'écriture")
```

---

## Optimisations du Flux

### 1. Batch Processing

```python
# Traitement par lots pour grandes tables
for batch in pd.read_sql(query, chunksize=10000):
    process_batch(batch)
```

### 2. Compression Intelligente

```python
# Snappy: rapide, bon compromis
# ZSTD: meilleure compression, plus lent
compression = 'snappy' if speed_priority else 'zstd'
```

### 3. Parallélisation

```python
# Export parallèle de plusieurs streams
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(export_stream, stream)
        for stream in streams
    ]
```

---

## Métriques de Performance

### Temps d'Export Typiques

| Type | Records | Taille | Temps |
|------|---------|--------|-------|
| Stream | 10,000 | 5 MB | 2-3s |
| Stream | 100,000 | 50 MB | 15-20s |
| Table | 1,000 | 500 KB | 1-2s |
| Table | 10,000 | 5 MB | 3-5s |

### Taux de Compression

| Format | Taille Originale | Taille Parquet | Ratio |
|--------|------------------|----------------|-------|
| JSON | 100 MB | 15 MB | 85% |
| CSV | 80 MB | 12 MB | 85% |

---

**Version**: 1.0  
**Dernière mise à jour**: Janvier 2025
