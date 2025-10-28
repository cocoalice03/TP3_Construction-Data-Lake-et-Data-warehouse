# 📋 Procédure d'Ajout d'un Nouveau Feed

## 🎯 Vue d'ensemble

Ce document décrit la procédure complète pour ajouter un nouveau feed Kafka dans le Data Lake et le Data Warehouse, en réutilisant au maximum le travail existant.

---

## ⚡ Procédure Rapide (5 étapes)

```
1. Enregistrer le feed dans le registre
2. Configurer dans kafka_config.py
3. Créer le topic Kafka (si nécessaire)
4. Redémarrer les consumers
5. Vérifier l'ingestion
```

**Temps estimé**: 10-15 minutes

---

## 📝 Procédure Détaillée

### Étape 1: Enregistrer le Feed dans le Registre

#### 1.1 Ajouter dans la base de données

```sql
-- Se connecter à MySQL
mysql -u root -p data_warehouse

-- Enregistrer le nouveau feed
INSERT INTO feed_registry (
    feed_name,
    feed_type,
    source_type,
    kafka_topic,
    partitioning_strategy,
    storage_format,
    compression,
    schema_definition,
    created_by
) VALUES (
    'nouveau_feed',              -- Nom du feed
    'stream',                    -- 'stream' ou 'table'
    'kafka',                     -- Source
    'nouveau_topic_kafka',       -- Topic Kafka
    'date',                      -- 'date' ou 'version'
    'parquet',                   -- Format
    'snappy',                    -- Compression
    '{"fields": ["field1", "field2"]}',  -- Schéma JSON
    1                            -- ID utilisateur
);

-- Vérifier
SELECT * FROM feed_registry WHERE feed_name = 'nouveau_feed';
```

#### 1.2 Définir la politique de rétention

```sql
-- Ajouter une politique de rétention
INSERT INTO data_retention_policies (
    feed_name,
    feed_type,
    retention_days,
    retention_versions,
    auto_delete,
    created_by
) VALUES (
    'nouveau_feed',
    'stream',
    90,                          -- Rétention en jours
    NULL,                        -- NULL pour streams, nombre pour tables
    TRUE,
    1
);

-- Vérifier
SELECT * FROM data_retention_policies WHERE feed_name = 'nouveau_feed';
```

---

### Étape 2: Configurer dans kafka_config.py

#### 2.1 Éditer le fichier de configuration

```python
# Ouvrir kafka_config.py
vim kafka_config.py
```

#### 2.2 Ajouter le feed

**Pour un Stream** (partitionné par date):

```python
KAFKA_TOPICS = {
    "streams": [
        # ... feeds existants ...
        
        # NOUVEAU FEED
        {
            "topic": "nouveau_topic_kafka",
            "feed_type": "stream",
            "destination": "data_lake",  # ou "both" pour DL + DW
            "partitioning": "date",
            "storage_mode": "append",
            "enabled": True
        }
    ],
    # ...
}
```

**Pour une Table** (partitionnée par version):

```python
KAFKA_TOPICS = {
    # ...
    "tables": [
        # ... feeds existants ...
        
        # NOUVEAU FEED
        {
            "topic": "nouveau_topic_kafka",
            "feed_type": "table",
            "destination": "both",  # Data Lake + Data Warehouse
            "partitioning": "version",
            "storage_mode": "overwrite",
            "mysql_table": "fact_nouveau_feed",  # Table MySQL
            "enabled": True
        }
    ]
}
```

#### 2.3 Ajouter le schéma (optionnel)

```python
MESSAGE_SCHEMAS = {
    # ... schémas existants ...
    
    "nouveau_topic_kafka": {
        "fields": ["field1", "field2", "field3", "timestamp"],
        "key_field": "field1"
    }
}
```

---

### Étape 3: Créer le Topic Kafka

#### 3.1 Créer le topic

```bash
# Créer le topic Kafka
kafka-topics --bootstrap-server localhost:9092 \
  --create \
  --topic nouveau_topic_kafka \
  --partitions 3 \
  --replication-factor 1

# Vérifier
kafka-topics --bootstrap-server localhost:9092 --list | grep nouveau
```

#### 3.2 Configurer les paramètres (optionnel)

```bash
# Définir la rétention Kafka (7 jours)
kafka-configs --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name nouveau_topic_kafka \
  --alter \
  --add-config retention.ms=604800000

# Définir la compression
kafka-configs --bootstrap-server localhost:9092 \
  --entity-type topics \
  --entity-name nouveau_topic_kafka \
  --alter \
  --add-config compression.type=snappy
```

---

### Étape 4: Créer la Table MySQL (si destination = "both")

#### 4.1 Créer le script SQL

```bash
# Créer le fichier SQL
vim sql/06_create_nouveau_feed_table.sql
```

#### 4.2 Définir le schéma

```sql
USE data_warehouse;

-- Table pour le nouveau feed
CREATE TABLE IF NOT EXISTS fact_nouveau_feed (
    id INT AUTO_INCREMENT PRIMARY KEY,
    field1 VARCHAR(255) NOT NULL,
    field2 DECIMAL(15,2),
    field3 VARCHAR(100),
    snapshot_date DATE NOT NULL,
    snapshot_version INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_field1 (field1),
    INDEX idx_snapshot_date (snapshot_date),
    INDEX idx_snapshot_version (snapshot_version),
    
    UNIQUE KEY unique_snapshot (field1, snapshot_date, snapshot_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Nouveau feed depuis Kafka';

SELECT 'Table fact_nouveau_feed créée' AS Status;
```

#### 4.3 Exécuter le script

```bash
mysql -u root -p < sql/06_create_nouveau_feed_table.sql
```

---

### Étape 5: Adapter le Consumer Warehouse (si nécessaire)

#### 5.1 Ajouter la logique d'insertion

Si le feed va dans le Data Warehouse, ajouter la méthode d'insertion dans `kafka_consumer_warehouse.py`:

```python
def insert_nouveau_feed(self, df: pd.DataFrame):
    """Insère les données du nouveau feed"""
    query = """
    INSERT INTO fact_nouveau_feed (
        field1, field2, field3, snapshot_date, snapshot_version
    ) VALUES (
        %(field1)s, %(field2)s, %(field3)s, %(snapshot_date)s, %(snapshot_version)s
    )
    ON DUPLICATE KEY UPDATE
        field2 = VALUES(field2),
        field3 = VALUES(field3),
        updated_at = CURRENT_TIMESTAMP
    """
    
    for _, row in df.iterrows():
        data = {
            "field1": row.get("field1"),
            "field2": row.get("field2"),
            "field3": row.get("field3"),
            "snapshot_date": self.snapshot_date,
            "snapshot_version": self.snapshot_version
        }
        self.mysql_cursor.execute(query, data)
    
    self.mysql_connection.commit()
```

#### 5.2 Ajouter dans flush_buffer()

```python
def flush_buffer(self, topic: str):
    # ... code existant ...
    
    # Ajouter le nouveau feed
    elif topic == "nouveau_topic_kafka":
        self.insert_nouveau_feed(df)
    else:
        logger.warning(f"Topic non supporté: {topic}")
```

---

### Étape 6: Redémarrer les Consumers

#### 6.1 Arrêter les consumers existants

```bash
# Si les consumers tournent
ps aux | grep kafka_consumer

# Arrêter avec Ctrl+C ou
kill <PID>
```

#### 6.2 Redémarrer

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Redémarrer tous les consumers
python kafka_consumer_orchestrator.py --mode all --mysql-password ""

# Ou uniquement Data Lake
python kafka_consumer_datalake.py

# Ou uniquement Data Warehouse
python kafka_consumer_warehouse.py --mysql-password ""
```

---

### Étape 7: Vérifier l'Ingestion

#### 7.1 Vérifier les logs

```bash
# Logs du consumer Data Lake
tail -f data_lake/logs/kafka_consumer_datalake_*.log

# Logs du consumer Data Warehouse
tail -f data_lake/logs/kafka_consumer_warehouse_*.log
```

#### 7.2 Vérifier le Data Lake

```bash
# Vérifier que les fichiers sont créés
ls -lh data_lake/streams/nouveau_feed/
# ou
ls -lh data_lake/tables/nouveau_feed/

# Lire un fichier Parquet
python -c "
import pandas as pd
df = pd.read_parquet('data_lake/streams/nouveau_feed/year=2025/month=01/day=28/data_*.parquet')
print(df.head())
print(f'Lignes: {len(df)}')
"
```

#### 7.3 Vérifier le Data Warehouse

```bash
# Vérifier les données dans MySQL
mysql -u root -p -e "
USE data_warehouse;
SELECT COUNT(*) as count FROM fact_nouveau_feed;
SELECT * FROM fact_nouveau_feed LIMIT 10;
"
```

#### 7.4 Tester l'envoi de messages

```bash
# Envoyer un message de test
echo '{"field1":"test","field2":123.45,"field3":"value"}' | \
kafka-console-producer --bootstrap-server localhost:9092 \
  --topic nouveau_topic_kafka

# Attendre quelques secondes et vérifier
```

---

## 🔄 Réutilisation du Travail Existant

### ✅ Ce qui est Automatiquement Réutilisé

#### 1. Infrastructure Kafka
- ✅ Connexion Kafka déjà configurée
- ✅ Gestion des offsets
- ✅ Batch processing (1000 messages)
- ✅ Gestion d'erreurs

#### 2. Écriture Parquet
- ✅ Conversion DataFrame → Parquet
- ✅ Compression Snappy
- ✅ Métadonnées automatiques
- ✅ Partitionnement (date/version)

#### 3. Gestion MySQL
- ✅ Connexion pool
- ✅ Transactions ACID
- ✅ UPSERT automatique
- ✅ Gestion des snapshots

#### 4. Monitoring
- ✅ Logs structurés
- ✅ Métriques de performance
- ✅ Alertes d'erreurs

#### 5. Gouvernance
- ✅ Enregistrement dans feed_registry
- ✅ Politique de rétention
- ✅ Journal d'audit
- ✅ Permissions

---

### 🚀 Avantages de la Réutilisation

| Aspect | Sans Réutilisation | Avec Réutilisation | Gain |
|--------|-------------------|-------------------|------|
| **Temps de développement** | 2-3 jours | 15 minutes | 95% |
| **Code à écrire** | ~500 lignes | ~50 lignes | 90% |
| **Tests** | Complets | Minimaux | 80% |
| **Documentation** | Complète | Mise à jour | 70% |
| **Déploiement** | Configuration complète | Redémarrage | 90% |

---

## 📊 Checklist de Validation

### Avant le Déploiement
- [ ] Feed enregistré dans `feed_registry`
- [ ] Politique de rétention définie
- [ ] Configuration ajoutée dans `kafka_config.py`
- [ ] Topic Kafka créé
- [ ] Table MySQL créée (si nécessaire)
- [ ] Logique d'insertion ajoutée (si nécessaire)
- [ ] Tests unitaires passés

### Après le Déploiement
- [ ] Consumers redémarrés sans erreur
- [ ] Messages consommés (vérifier logs)
- [ ] Fichiers Parquet créés
- [ ] Données dans MySQL (si applicable)
- [ ] Permissions configurées
- [ ] Monitoring actif
- [ ] Documentation mise à jour

---

## 🐛 Troubleshooting

### Problème 1: Topic non trouvé

```bash
# Erreur: Topic nouveau_topic_kafka is not available

# Solution: Créer le topic
kafka-topics --bootstrap-server localhost:9092 \
  --create --topic nouveau_topic_kafka \
  --partitions 3 --replication-factor 1
```

### Problème 2: Consumer ne démarre pas

```bash
# Erreur: Topic non supporté

# Solution: Vérifier kafka_config.py
grep "nouveau_topic_kafka" kafka_config.py

# Redémarrer les consumers
python kafka_consumer_orchestrator.py --mode all --mysql-password ""
```

### Problème 3: Erreur MySQL

```bash
# Erreur: Table doesn't exist

# Solution: Créer la table
mysql -u root -p < sql/06_create_nouveau_feed_table.sql
```

### Problème 4: Pas de données

```bash
# Vérifier que le producer envoie des messages
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic nouveau_topic_kafka \
  --from-beginning \
  --max-messages 10
```

---

## 📈 Exemple Complet

### Ajout d'un Feed "customer_events"

```bash
# 1. Enregistrer dans MySQL
mysql -u root -p data_warehouse << EOF
INSERT INTO feed_registry (feed_name, feed_type, source_type, kafka_topic, partitioning_strategy, created_by)
VALUES ('customer_events', 'stream', 'kafka', 'customer_events', 'date', 1);

INSERT INTO data_retention_policies (feed_name, feed_type, retention_days, created_by)
VALUES ('customer_events', 'stream', 180, 1);
EOF

# 2. Ajouter dans kafka_config.py
cat >> kafka_config.py << 'EOF'
# Dans KAFKA_TOPICS["streams"]:
{
    "topic": "customer_events",
    "feed_type": "stream",
    "destination": "data_lake",
    "partitioning": "date",
    "storage_mode": "append",
    "enabled": True
}
EOF

# 3. Créer le topic Kafka
kafka-topics --bootstrap-server localhost:9092 \
  --create --topic customer_events \
  --partitions 3 --replication-factor 1

# 4. Redémarrer les consumers
python kafka_consumer_orchestrator.py --mode all --mysql-password ""

# 5. Tester
echo '{"customer_id":"C123","event":"login","timestamp":"2025-01-28T20:00:00Z"}' | \
kafka-console-producer --bootstrap-server localhost:9092 --topic customer_events

# 6. Vérifier
ls -lh data_lake/streams/customer_events/
```

**Temps total: 10 minutes** ⚡

---

## 🎯 Résumé

### Travail Nécessaire
- ✅ Configuration: 5 minutes
- ✅ Création topic: 1 minute
- ✅ Table MySQL (optionnel): 5 minutes
- ✅ Tests: 5 minutes

### Travail Réutilisé Automatiquement
- ✅ Consumer Kafka (~300 lignes)
- ✅ Écriture Parquet (~200 lignes)
- ✅ Gestion MySQL (~300 lignes)
- ✅ Monitoring (~100 lignes)
- ✅ Gouvernance (~200 lignes)

**Total réutilisé: ~1100 lignes de code !** 🚀

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Statut**: ✅ Procédure Validée
