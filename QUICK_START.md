# 🚀 Démarrage Rapide - Data Lake + Data Warehouse

## ✅ Installation Réussie !

Votre environnement est maintenant configuré :
- ✅ MySQL 9.5.0 installé et démarré
- ✅ Base de données `data_warehouse` créée
- ✅ 6 tables créées (2 dimensions + 4 faits)
- ✅ Environnement Python virtuel configuré
- ✅ Dépendances installées

---

## 📊 Structure du Data Warehouse

### Tables Créées

```
data_warehouse
├── dim_users (dimension)
├── dim_payment_methods (dimension)
├── fact_user_transaction_summary (fait)
├── fact_user_transaction_summary_eur (fait)
├── fact_payment_method_totals (fait)
└── fact_product_purchase_counts (fait)
```

### Vérifier les Tables

```bash
mysql -u root -e "USE data_warehouse; SHOW TABLES;"
```

---

## 🔄 Utilisation

### 1. Activer l'Environnement Python

**À faire à chaque nouvelle session terminal** :

```bash
cd /Users/alice/Downloads/data_lake
source venv/bin/activate
```

Vous devriez voir `(venv)` au début de votre prompt.

### 2. Configurer ksqlDB

Éditer `data_lake_config.py` :

```python
KSQLDB_CONFIG = {
    "host": "localhost",  # Votre host ksqlDB
    "port": 8088,         # Votre port ksqlDB
    "timeout": 30
}
```

### 3. Export Data Lake (Parquet)

```bash
# Export complet
python export_to_data_lake.py --all

# Export d'un stream spécifique
python export_to_data_lake.py --stream transaction_stream

# Export d'une table spécifique
python export_to_data_lake.py --table user_transaction_summary
```

### 4. Synchronisation Data Warehouse (MySQL)

```bash
# Synchronisation complète
python sync_to_mysql.py --mysql-password ""

# Note: Pas de mot de passe root par défaut
# Pour définir un mot de passe, voir section Sécurité ci-dessous
```

### 5. Requêtes SQL

```bash
# Se connecter à MySQL
mysql -u root data_warehouse

# Exemples de requêtes
mysql> SELECT * FROM dim_users LIMIT 10;
mysql> SELECT * FROM dim_payment_methods;
mysql> SELECT COUNT(*) FROM fact_user_transaction_summary;
mysql> EXIT;
```

---

## 🔐 Sécuriser MySQL (Recommandé)

### Définir un Mot de Passe Root

```bash
# Lancer l'assistant de sécurisation
mysql_secure_installation
```

**Réponses recommandées** :
- Set root password? **Yes** → Choisir un mot de passe sécurisé
- Remove anonymous users? **Yes**
- Disallow root login remotely? **Yes**
- Remove test database? **Yes**
- Reload privilege tables? **Yes**

### Après avoir défini un mot de passe

```bash
# Se connecter avec mot de passe
mysql -u root -p

# Synchroniser avec mot de passe
python sync_to_mysql.py --mysql-password votre_mot_de_passe
```

---

## 📊 Exemples de Requêtes SQL

### Top 10 Utilisateurs

```sql
USE data_warehouse;

SELECT 
    u.user_name,
    u.user_country,
    SUM(f.total_amount) as total_spent,
    SUM(f.transaction_count) as total_transactions
FROM dim_users u
JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
WHERE f.snapshot_date = CURDATE()
GROUP BY u.user_name, u.user_country
ORDER BY total_spent DESC
LIMIT 10;
```

### Performance des Méthodes de Paiement

```sql
SELECT 
    pm.payment_method_name,
    pm.payment_method_category,
    SUM(f.total_amount) as total_revenue,
    SUM(f.transaction_count) as total_transactions
FROM dim_payment_methods pm
JOIN fact_payment_method_totals f ON pm.payment_method_id = f.payment_method_id
WHERE f.snapshot_date = CURDATE()
GROUP BY pm.payment_method_name, pm.payment_method_category
ORDER BY total_revenue DESC;
```

### Top Produits

```sql
SELECT 
    product_name,
    product_category,
    purchase_count,
    total_revenue,
    ROUND(total_revenue / purchase_count, 2) as avg_revenue_per_purchase
FROM fact_product_purchase_counts
WHERE snapshot_date = CURDATE()
ORDER BY purchase_count DESC
LIMIT 20;
```

### Plus de requêtes

```bash
# Voir tous les exemples de requêtes
cat sql/04_sample_queries.sql
```

---

## 🔄 Workflow Quotidien

### Démarrer une Session

```bash
# 1. Naviguer vers le projet
cd /Users/alice/Downloads/data_lake

# 2. Activer l'environnement Python
source venv/bin/activate

# 3. Vérifier que MySQL est démarré
brew services list | grep mysql
```

### Synchroniser les Données

```bash
# 1. Export vers Data Lake (Parquet)
python export_to_data_lake.py --all

# 2. Synchronisation vers Data Warehouse (MySQL)
python sync_to_mysql.py --mysql-password ""

# 3. Vérifier les données
mysql -u root -e "USE data_warehouse; SELECT COUNT(*) FROM fact_user_transaction_summary;"
```

### Monitoring

```bash
# Métadonnées Data Lake
python metadata_utils.py --stats

# Statistiques Data Warehouse
mysql -u root -e "
SELECT 
    table_name,
    table_rows,
    ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb
FROM information_schema.tables
WHERE table_schema = 'data_warehouse'
ORDER BY (data_length + index_length) DESC;
"
```

---

## 🛠️ Commandes Utiles

### MySQL

```bash
# Démarrer MySQL
brew services start mysql

# Arrêter MySQL
brew services stop mysql

# Redémarrer MySQL
brew services restart mysql

# Statut MySQL
brew services list | grep mysql

# Se connecter
mysql -u root -p

# Exécuter un script SQL
mysql -u root -p < fichier.sql
```

### Python

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Désactiver l'environnement virtuel
deactivate

# Lister les packages installés
pip list

# Mettre à jour un package
pip install --upgrade nom_package
```

### Data Lake

```bash
# Lister les feeds
python manage_feeds.py list

# Ajouter un feed
python manage_feeds.py add --name new_feed --type stream --source new_stream

# Synchroniser les feeds
python manage_feeds.py sync

# Statistiques
python metadata_utils.py --stats

# Rapport complet
python metadata_utils.py --report
```

---

## 📚 Documentation Complète

### Data Lake
- **README.md** - Vue d'ensemble
- **QUICKSTART.md** - Guide de démarrage
- **DESIGN_DOCUMENT.md** - Design complet
- **ARCHITECTURE.md** - Architecture technique
- **DECISION_GUIDE.md** - Guide de décision

### Data Warehouse
- **DATA_WAREHOUSE_DESIGN.md** - Design complet avec ERD
- **DATA_WAREHOUSE_QUICKSTART.md** - Guide de démarrage
- **DATA_WAREHOUSE_SUMMARY.md** - Résumé exécutif

### Installation et Troubleshooting
- **INSTALLATION_GUIDE.md** - Guide d'installation complet
- **MYSQL_SETUP.md** - Configuration MySQL détaillée
- **QUICK_START.md** - Ce fichier

### Référence Complète
- **COMPLETE_PROJECT_SUMMARY.md** - Vue d'ensemble complète
- **INDEX.md** - Index de navigation

---

## 🐛 Troubleshooting Rapide

### MySQL ne démarre pas

```bash
# Vérifier les logs
tail -f /opt/homebrew/var/mysql/*.err

# Redémarrer
brew services restart mysql
```

### Erreur "Module not found"

```bash
# Vérifier que l'environnement virtuel est activé
which python
# Devrait afficher: /Users/alice/Downloads/data_lake/venv/bin/python

# Si non activé
source venv/bin/activate
```

### Erreur de connexion ksqlDB

```bash
# Vérifier que ksqlDB est accessible
curl http://localhost:8088/info

# Modifier la configuration si nécessaire
vim data_lake_config.py
```

---

## ✅ Checklist de Validation

### Installation
- [x] MySQL installé et démarré
- [x] Base de données créée
- [x] Tables créées (6 tables)
- [x] Environnement Python activé
- [x] Dépendances installées

### Configuration
- [ ] ksqlDB configuré dans `data_lake_config.py`
- [ ] Mot de passe MySQL défini (optionnel mais recommandé)
- [ ] Premier export Data Lake réussi
- [ ] Première synchronisation Data Warehouse réussie

### Tests
```bash
# Test MySQL
mysql -u root -e "USE data_warehouse; SHOW TABLES;"

# Test Python
python -c "import pandas, pyarrow, requests, mysql.connector; print('✅ Tous les modules OK')"

# Test Data Lake
python test_setup.py
```

---

## 🎯 Prochaines Étapes

1. **Sécuriser MySQL** : `mysql_secure_installation`
2. **Configurer ksqlDB** : Éditer `data_lake_config.py`
3. **Premier export** : `python export_to_data_lake.py --all`
4. **Première synchro** : `python sync_to_mysql.py --mysql-password ""`
5. **Explorer les données** : `mysql -u root data_warehouse`

---

## 📞 Support

**Documentation** : Voir les fichiers .md dans le projet  
**Logs Data Lake** : `data_lake/logs/`  
**Logs MySQL** : `/opt/homebrew/var/mysql/*.err`

---

**Version** : 1.0  
**Date** : Janvier 2025  
**Statut** : ✅ Prêt à l'emploi
