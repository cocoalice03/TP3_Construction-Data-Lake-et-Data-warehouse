# 🔧 Configuration MySQL - Guide de Résolution

## 🎯 Problème Actuel

Vous avez MySQL installé via Anaconda, mais le serveur MySQL n'est pas démarré.

**Erreur**: `Can't connect to local MySQL server through socket '/tmp/mysql.sock'`

---

## ✅ Solutions (3 Options)

### Option 1: Utiliser MySQL via Homebrew (Recommandé)

C'est la méthode la plus simple et la plus fiable sur macOS.

```bash
# 1. Installer MySQL via Homebrew
brew install mysql

# 2. Démarrer le service MySQL
brew services start mysql

# 3. Vérifier que MySQL fonctionne
mysql -u root -e "SELECT 1;"

# 4. Si pas de mot de passe, en définir un
mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'votre_mot_de_passe';"
```

### Option 2: Démarrer MySQL Anaconda

Si vous préférez utiliser MySQL d'Anaconda:

```bash
# 1. Trouver le chemin d'installation MySQL
which mysql
# Résultat: /Users/alice/anaconda3/bin/mysql

# 2. Trouver mysqld (le serveur)
find /Users/alice/anaconda3 -name mysqld

# 3. Démarrer le serveur MySQL
# (Le chemin exact dépend de votre installation Anaconda)
/Users/alice/anaconda3/bin/mysqld --datadir=/Users/alice/anaconda3/var/mysql &

# 4. Tester la connexion
mysql -u root -p
```

### Option 3: Utiliser Docker (Alternative)

Si vous avez Docker installé:

```bash
# 1. Démarrer MySQL dans un conteneur
docker run --name mysql-dw \
  -e MYSQL_ROOT_PASSWORD=votre_mot_de_passe \
  -p 3306:3306 \
  -d mysql:8.0

# 2. Attendre que MySQL démarre (30 secondes)
sleep 30

# 3. Tester la connexion
mysql -h 127.0.0.1 -u root -p
```

---

## 🚀 Procédure Recommandée (Option 1)

### Étape 1: Installer MySQL via Homebrew

```bash
# Installer MySQL
brew install mysql

# Démarrer MySQL
brew services start mysql

# Vérifier le statut
brew services list | grep mysql
```

**Résultat attendu**:
```
mysql started alice ~/Library/LaunchAgents/homebrew.mxcl.mysql.plist
```

### Étape 2: Configurer le Mot de Passe Root

```bash
# Se connecter (première fois, pas de mot de passe)
mysql -u root

# Dans MySQL, définir un mot de passe
mysql> ALTER USER 'root'@'localhost' IDENTIFIED BY 'votre_mot_de_passe_securise';
mysql> FLUSH PRIVILEGES;
mysql> EXIT;
```

### Étape 3: Tester la Connexion

```bash
# Tester avec le nouveau mot de passe
mysql -u root -p
# Entrer le mot de passe quand demandé

# Vérifier que ça fonctionne
mysql> SELECT VERSION();
mysql> EXIT;
```

### Étape 4: Créer le Data Warehouse

```bash
# Activer l'environnement virtuel Python
cd /Users/alice/Downloads/data_lake
source venv/bin/activate

# Créer la base de données
mysql -u root -p < sql/01_create_database.sql

# Créer les tables de dimension
mysql -u root -p < sql/02_create_dimension_tables.sql

# Créer les tables de faits
mysql -u root -p < sql/03_create_fact_tables.sql

# Vérifier
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

## 🔍 Diagnostic

### Vérifier si MySQL est Installé

```bash
# Chercher MySQL
which mysql

# Vérifier la version
mysql --version
```

### Vérifier si MySQL est Démarré

```bash
# Option 1: Via Homebrew
brew services list | grep mysql

# Option 2: Via processus
ps aux | grep mysqld | grep -v grep

# Option 3: Tester la connexion
mysql -u root -p -e "SELECT 1;"
```

### Trouver le Socket MySQL

```bash
# Chercher le fichier socket
find /tmp -name "mysql.sock" 2>/dev/null
find /var -name "mysql.sock" 2>/dev/null

# Vérifier la configuration MySQL
mysql --help | grep "Default options"
```

---

## 🐛 Problèmes Courants

### Problème 1: "mysql.sock not found"

**Cause**: MySQL n'est pas démarré

**Solution**:
```bash
# Démarrer MySQL
brew services start mysql

# Ou si via Anaconda
mysqld --datadir=/path/to/datadir &
```

### Problème 2: "Access denied for user 'root'@'localhost'"

**Cause**: Mauvais mot de passe ou pas de mot de passe défini

**Solution**:
```bash
# Réinitialiser le mot de passe
brew services stop mysql
mysqld_safe --skip-grant-tables &
mysql -u root
mysql> ALTER USER 'root'@'localhost' IDENTIFIED BY 'nouveau_mot_de_passe';
mysql> FLUSH PRIVILEGES;
mysql> EXIT;
killall mysqld
brew services start mysql
```

### Problème 3: Port 3306 déjà utilisé

**Cause**: Un autre service utilise le port 3306

**Solution**:
```bash
# Vérifier quel processus utilise le port
lsof -i :3306

# Arrêter le processus
kill -9 <PID>

# Ou utiliser un autre port
mysqld --port=3307 &
```

---

## 📝 Configuration pour le Projet

### Mise à Jour de sync_to_mysql.py

Si vous utilisez un mot de passe différent ou un port différent:

```python
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,  # Changer si nécessaire
    "database": "data_warehouse",
    "user": "root",
    "password": "",  # Laisser vide, sera passé en argument
    "charset": "utf8mb4",
    "use_unicode": True
}
```

### Utilisation avec Mot de Passe

```bash
# Option 1: Passer le mot de passe en argument
python sync_to_mysql.py --mysql-password votre_mot_de_passe

# Option 2: Variable d'environnement
export MYSQL_PASSWORD=votre_mot_de_passe
python sync_to_mysql.py --mysql-password $MYSQL_PASSWORD

# Option 3: Fichier de configuration (plus sécurisé)
# Créer ~/.my.cnf
[client]
user=root
password=votre_mot_de_passe
host=localhost

# Puis utiliser sans mot de passe
mysql < sql/01_create_database.sql
```

---

## ✅ Checklist de Validation

### Installation
- [ ] MySQL installé (`which mysql`)
- [ ] MySQL démarré (`brew services list`)
- [ ] Connexion possible (`mysql -u root -p`)

### Configuration
- [ ] Mot de passe root défini
- [ ] Base de données créée
- [ ] Tables créées
- [ ] Connexion depuis Python fonctionne

### Test Final

```bash
# Test complet
cd /Users/alice/Downloads/data_lake
source venv/bin/activate

# Test 1: Connexion MySQL
mysql -u root -p -e "SELECT VERSION();"

# Test 2: Base de données existe
mysql -u root -p -e "SHOW DATABASES LIKE 'data_warehouse';"

# Test 3: Tables existent
mysql -u root -p -e "USE data_warehouse; SHOW TABLES;"

# Test 4: Python peut se connecter
python -c "import mysql.connector; conn = mysql.connector.connect(host='localhost', user='root', password='VOTRE_MOT_DE_PASSE'); print('✅ Connexion OK'); conn.close()"
```

---

## 🎯 Commandes Rapides

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

# Créer le Data Warehouse
cd /Users/alice/Downloads/data_lake
source venv/bin/activate
mysql -u root -p < sql/01_create_database.sql
mysql -u root -p < sql/02_create_dimension_tables.sql
mysql -u root -p < sql/03_create_fact_tables.sql
```

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Statut**: ✅ Guide de Résolution Complet
