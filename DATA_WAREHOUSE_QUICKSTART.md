# 🚀 Data Warehouse MySQL - Guide de Démarrage Rapide

## 📋 Prérequis

- MySQL 8.0+ installé et configuré
- Python 3.8+ avec pip
- ksqlDB accessible
- Accès administrateur MySQL

---

## 🔧 Installation

### 1. Installer MySQL (si nécessaire)

```bash
# macOS
brew install mysql
brew services start mysql

# Linux (Ubuntu/Debian)
sudo apt-get install mysql-server
sudo systemctl start mysql

# Sécuriser l'installation
mysql_secure_installation
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

---

## 🗄️ Création du Data Warehouse

### 1. Créer la base de données

```bash
mysql -u root -p < sql/01_create_database.sql
```

### 2. Créer les tables de dimension

```bash
mysql -u root -p < sql/02_create_dimension_tables.sql
```

### 3. Créer les tables de faits

```bash
mysql -u root -p < sql/03_create_fact_tables.sql
```

### 4. Vérifier la création

```bash
mysql -u root -p -e "USE data_warehouse; SHOW TABLES;"
```

**Résultat attendu**:
```
+----------------------------------+
| Tables_in_data_warehouse         |
+----------------------------------+
| dim_payment_methods              |
| dim_users                        |
| fact_payment_method_totals       |
| fact_product_purchase_counts     |
| fact_user_transaction_summary    |
| fact_user_transaction_summary_eur|
+----------------------------------+
```

---

## 🔄 Synchronisation des Données

### Configuration

Éditer `sync_to_mysql.py` et configurer:

```python
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "database": "data_warehouse",
    "user": "root",
    "password": "votre_mot_de_passe"
}
```

### Synchronisation Complète

```bash
python sync_to_mysql.py --mysql-password votre_mot_de_passe
```

### Synchronisation d'une Table Spécifique

```bash
# Synchroniser user_transaction_summary
python sync_to_mysql.py \
  --table user_transaction_summary \
  --mysql-password votre_mot_de_passe

# Synchroniser payment_method_totals
python sync_to_mysql.py \
  --table payment_method_totals \
  --mysql-password votre_mot_de_passe
```

---

## 📊 Requêtes Analytiques

### Connexion à MySQL

```bash
mysql -u root -p data_warehouse
```

### Exemples de Requêtes

#### Top 10 Utilisateurs

```sql
SELECT 
    u.user_name,
    u.user_country,
    SUM(f.total_amount) as total_spent
FROM dim_users u
JOIN fact_user_transaction_summary f ON u.user_id = f.user_id
WHERE f.snapshot_date = CURDATE()
GROUP BY u.user_name, u.user_country
ORDER BY total_spent DESC
LIMIT 10;
```

#### Performance des Méthodes de Paiement

```sql
SELECT 
    pm.payment_method_name,
    SUM(f.total_amount) as total_revenue,
    SUM(f.transaction_count) as total_transactions
FROM dim_payment_methods pm
JOIN fact_payment_method_totals f ON pm.payment_method_id = f.payment_method_id
WHERE f.snapshot_date = CURDATE()
GROUP BY pm.payment_method_name
ORDER BY total_revenue DESC;
```

#### Top Produits

```sql
SELECT 
    product_name,
    product_category,
    purchase_count,
    total_revenue
FROM fact_product_purchase_counts
WHERE snapshot_date = CURDATE()
ORDER BY purchase_count DESC
LIMIT 20;
```

---

## 🔄 Automatisation

### Cron Job pour Synchronisation Quotidienne

```bash
# Éditer le crontab
crontab -e

# Ajouter la ligne suivante (synchronisation à 3h du matin)
0 3 * * * cd /path/to/project && python sync_to_mysql.py --mysql-password PASSWORD >> logs/mysql_sync.log 2>&1
```

---

## 📈 Monitoring

### Vérifier les Dernières Synchronisations

```sql
SELECT 
    'fact_user_transaction_summary' as table_name,
    MAX(snapshot_date) as last_snapshot,
    COUNT(*) as total_records
FROM fact_user_transaction_summary

UNION ALL

SELECT 
    'fact_payment_method_totals',
    MAX(snapshot_date),
    COUNT(*)
FROM fact_payment_method_totals;
```

### Taille des Tables

```sql
SELECT 
    table_name,
    table_rows,
    ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb
FROM information_schema.tables
WHERE table_schema = 'data_warehouse'
ORDER BY (data_length + index_length) DESC;
```

---

## 🔐 Sécurité

### Créer un Utilisateur Dédié

```sql
-- Créer l'utilisateur
CREATE USER 'dw_sync'@'localhost' IDENTIFIED BY 'secure_password';

-- Donner les permissions
GRANT SELECT, INSERT, UPDATE ON data_warehouse.* TO 'dw_sync'@'localhost';

-- Appliquer les changements
FLUSH PRIVILEGES;
```

### Utiliser l'Utilisateur Dédié

```bash
python sync_to_mysql.py \
  --mysql-user dw_sync \
  --mysql-password secure_password
```

---

## 🐛 Troubleshooting

### Erreur de Connexion MySQL

```bash
# Vérifier que MySQL est démarré
sudo systemctl status mysql  # Linux
brew services list           # macOS

# Tester la connexion
mysql -u root -p -e "SELECT 1;"
```

### Erreur de Permissions

```sql
-- Vérifier les permissions
SHOW GRANTS FOR 'root'@'localhost';

-- Donner toutes les permissions (si nécessaire)
GRANT ALL PRIVILEGES ON data_warehouse.* TO 'root'@'localhost';
FLUSH PRIVILEGES;
```

### Tables Non Créées

```bash
# Vérifier les erreurs dans les logs
tail -f logs/mysql_sync_*.log

# Recréer les tables
mysql -u root -p < sql/01_create_database.sql
mysql -u root -p < sql/02_create_dimension_tables.sql
mysql -u root -p < sql/03_create_fact_tables.sql
```

---

## 📚 Documentation Complète

- **Design complet**: `DATA_WAREHOUSE_DESIGN.md`
- **Schéma relationnel**: Voir diagramme ERD dans `DATA_WAREHOUSE_DESIGN.md`
- **Requêtes exemples**: `sql/04_sample_queries.sql`

---

## ✅ Checklist de Validation

- [ ] MySQL installé et démarré
- [ ] Base de données créée
- [ ] Tables de dimension créées
- [ ] Tables de faits créées
- [ ] Méthodes de paiement insérées
- [ ] Première synchronisation réussie
- [ ] Requêtes de test fonctionnelles

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Statut**: ✅ Prêt à l'emploi
