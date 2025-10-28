# 🚀 Guide d'Installation Complet

## ⚠️ Problèmes Courants et Solutions

### Problème 1: MySQL n'est pas installé/démarré

**Symptôme**: `ERROR 2002 (HY000): Can't connect to local MySQL server through socket '/tmp/mysql.sock'`

**Solution**:

```bash
# Vérifier si MySQL est installé
which mysql

# Si MySQL n'est pas installé, l'installer avec Homebrew
brew install mysql

# Démarrer MySQL
brew services start mysql

# Vérifier que MySQL fonctionne
mysql -u root -e "SELECT 1;"
```

### Problème 2: Dépendances Python manquantes

**Symptôme**: `ModuleNotFoundError: No module named 'requests'`

**Solution**: Utiliser un environnement virtuel Python

```bash
# 1. Créer un environnement virtuel
python3 -m venv venv

# 2. Activer l'environnement virtuel
source venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

---

## 📋 Installation Complète Étape par Étape

### Étape 1: Prérequis

```bash
# Vérifier Python 3.8+
python3 --version

# Vérifier pip
pip3 --version

# Installer Homebrew (si nécessaire)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Étape 2: Installer MySQL

```bash
# Installer MySQL
brew install mysql

# Démarrer MySQL
brew services start mysql

# Sécuriser l'installation (optionnel mais recommandé)
mysql_secure_installation
```

**Configuration recommandée lors de `mysql_secure_installation`**:
- Mot de passe root: Choisir un mot de passe sécurisé
- Remove anonymous users: Yes
- Disallow root login remotely: Yes
- Remove test database: Yes
- Reload privilege tables: Yes

### Étape 3: Configurer l'Environnement Python

```bash
# Naviguer vers le projet
cd /Users/alice/Downloads/data_lake

# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Vérifier l'installation
pip list
```

### Étape 4: Créer le Data Warehouse MySQL

```bash
# S'assurer que l'environnement virtuel est activé
source venv/bin/activate

# Créer la base de données
mysql -u root -p < sql/01_create_database.sql

# Créer les tables de dimension
mysql -u root -p < sql/02_create_dimension_tables.sql

# Créer les tables de faits
mysql -u root -p < sql/03_create_fact_tables.sql

# Vérifier la création
mysql -u root -p -e "USE data_warehouse; SHOW TABLES;"
```

### Étape 5: Configurer ksqlDB

Éditer `data_lake_config.py`:

```python
KSQLDB_CONFIG = {
    "host": "localhost",  # Votre host ksqlDB
    "port": 8088,         # Votre port ksqlDB
    "timeout": 30
}
```

### Étape 6: Tester l'Installation

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Tester le Data Lake
python test_setup.py

# Tester la connexion MySQL
python -c "import mysql.connector; print('MySQL connector OK')"
```

---

## 🔄 Utilisation Quotidienne

### Démarrer une Session

```bash
# 1. Naviguer vers le projet
cd /Users/alice/Downloads/data_lake

# 2. Activer l'environnement virtuel
source venv/bin/activate

# 3. Vérifier que MySQL est démarré
brew services list | grep mysql
```

### Synchroniser les Données

```bash
# Data Lake: Export depuis ksqlDB
python export_to_data_lake.py --all

# Data Warehouse: Synchronisation vers MySQL
python sync_to_mysql.py --mysql-password VOTRE_MOT_DE_PASSE
```

### Requêtes Analytiques

```bash
# Connexion à MySQL
mysql -u root -p data_warehouse

# Exécuter des requêtes
mysql> SELECT * FROM dim_users LIMIT 10;
mysql> SELECT * FROM fact_user_transaction_summary LIMIT 10;
```

---

## 🔧 Configuration MySQL pour le Projet

### Créer un Utilisateur Dédié (Recommandé)

```sql
-- Se connecter en tant que root
mysql -u root -p

-- Créer l'utilisateur
CREATE USER 'data_warehouse_user'@'localhost' IDENTIFIED BY 'votre_mot_de_passe_securise';

-- Donner les permissions
GRANT ALL PRIVILEGES ON data_warehouse.* TO 'data_warehouse_user'@'localhost';

-- Appliquer les changements
FLUSH PRIVILEGES;

-- Quitter
EXIT;
```

### Utiliser l'Utilisateur Dédié

Éditer `sync_to_mysql.py`:

```python
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "database": "data_warehouse",
    "user": "data_warehouse_user",  # Votre utilisateur
    "password": "",  # À remplir ou passer en argument
    "charset": "utf8mb4",
    "use_unicode": True
}
```

Puis utiliser:

```bash
python sync_to_mysql.py \
  --mysql-user data_warehouse_user \
  --mysql-password votre_mot_de_passe_securise
```

---

## 🐛 Troubleshooting Détaillé

### MySQL ne démarre pas

```bash
# Vérifier les logs
tail -f /opt/homebrew/var/mysql/*.err

# Arrêter MySQL
brew services stop mysql

# Supprimer les fichiers de verrouillage
rm -f /opt/homebrew/var/mysql/*.pid

# Redémarrer
brew services start mysql
```

### Mot de passe MySQL oublié

```bash
# Arrêter MySQL
brew services stop mysql

# Démarrer en mode sans authentification
mysqld_safe --skip-grant-tables &

# Se connecter sans mot de passe
mysql -u root

# Changer le mot de passe
mysql> ALTER USER 'root'@'localhost' IDENTIFIED BY 'nouveau_mot_de_passe';
mysql> FLUSH PRIVILEGES;
mysql> EXIT;

# Redémarrer MySQL normalement
killall mysqld
brew services start mysql
```

### Erreur "Access denied for user 'root'@'localhost'"

```bash
# Option 1: Utiliser sudo
sudo mysql -u root

# Option 2: Réinitialiser le mot de passe (voir ci-dessus)

# Option 3: Vérifier les permissions
mysql -u root -p -e "SELECT user, host FROM mysql.user;"
```

### Environnement virtuel non activé

**Symptôme**: `ModuleNotFoundError` même après installation

**Solution**:

```bash
# Vérifier si l'environnement est activé
which python
# Devrait afficher: /Users/alice/Downloads/data_lake/venv/bin/python

# Si ce n'est pas le cas, activer:
source venv/bin/activate

# Vérifier à nouveau
which python
```

---

## ✅ Checklist de Validation

### Installation MySQL
- [ ] MySQL installé (`which mysql`)
- [ ] MySQL démarré (`brew services list`)
- [ ] Connexion possible (`mysql -u root -p`)
- [ ] Base de données créée (`SHOW DATABASES LIKE 'data_warehouse';`)
- [ ] Tables créées (`USE data_warehouse; SHOW TABLES;`)

### Installation Python
- [ ] Python 3.8+ installé (`python3 --version`)
- [ ] Environnement virtuel créé (`ls venv/`)
- [ ] Environnement activé (`which python`)
- [ ] Dépendances installées (`pip list | grep pandas`)

### Configuration
- [ ] ksqlDB accessible
- [ ] Configuration MySQL correcte
- [ ] Mot de passe MySQL configuré

### Tests
- [ ] `python test_setup.py` réussit
- [ ] `python -c "import mysql.connector"` réussit
- [ ] Connexion MySQL fonctionne

---

## 📝 Script d'Installation Automatique

Créer un fichier `install.sh`:

```bash
#!/bin/bash

echo "🚀 Installation du projet Data Lake + Data Warehouse"

# 1. Vérifier MySQL
echo "📦 Vérification de MySQL..."
if ! command -v mysql &> /dev/null; then
    echo "❌ MySQL non trouvé. Installation..."
    brew install mysql
    brew services start mysql
else
    echo "✅ MySQL trouvé"
fi

# 2. Créer l'environnement virtuel
echo "🐍 Création de l'environnement virtuel Python..."
python3 -m venv venv
source venv/bin/activate

# 3. Installer les dépendances
echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

# 4. Créer la base de données
echo "🗄️ Création de la base de données..."
read -sp "Mot de passe MySQL root: " MYSQL_PASSWORD
echo
mysql -u root -p"$MYSQL_PASSWORD" < sql/01_create_database.sql
mysql -u root -p"$MYSQL_PASSWORD" < sql/02_create_dimension_tables.sql
mysql -u root -p"$MYSQL_PASSWORD" < sql/03_create_fact_tables.sql

# 5. Tester
echo "✅ Test de l'installation..."
python test_setup.py

echo "🎉 Installation terminée!"
echo "Pour activer l'environnement: source venv/bin/activate"
```

Utilisation:

```bash
chmod +x install.sh
./install.sh
```

---

## 📞 Support

### Logs à Consulter

**MySQL**:
```bash
tail -f /opt/homebrew/var/mysql/*.err
```

**Python**:
```bash
tail -f data_lake/logs/*.log
```

### Commandes Utiles

```bash
# Statut MySQL
brew services list

# Redémarrer MySQL
brew services restart mysql

# Vérifier les processus MySQL
ps aux | grep mysql

# Tester la connexion
mysql -u root -p -e "SELECT 1;"
```

---

**Version**: 1.0  
**Date**: Janvier 2025  
**Statut**: ✅ Testé et Validé
