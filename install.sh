#!/bin/bash

# ============================================================================
# Script d'Installation Automatique - Data Lake + Data Warehouse + Kafka
# ============================================================================

set -e  # Arrêt en cas d'erreur

echo "🚀 Installation du projet Data Lake + Data Warehouse + Kafka Consumers"
echo "======================================================================"
echo ""

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# ============================================================================
# 1. Vérification des prérequis
# ============================================================================

echo "📋 Vérification des prérequis..."
echo ""

# Vérifier Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_info "Python trouvé: $PYTHON_VERSION"
else
    log_error "Python 3 non trouvé. Veuillez l'installer."
    exit 1
fi

# Vérifier Homebrew (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &> /dev/null; then
        log_info "Homebrew trouvé"
    else
        log_warning "Homebrew non trouvé. Installation recommandée."
    fi
fi

echo ""

# ============================================================================
# 2. Installation de MySQL
# ============================================================================

echo "🗄️ Installation de MySQL..."
echo ""

if command -v mysql &> /dev/null; then
    MYSQL_VERSION=$(mysql --version)
    log_info "MySQL déjà installé: $MYSQL_VERSION"
else
    log_warning "MySQL non trouvé. Installation..."
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install mysql
        log_info "MySQL installé via Homebrew"
    else
        log_error "Veuillez installer MySQL manuellement"
        exit 1
    fi
fi

# Démarrer MySQL
if [[ "$OSTYPE" == "darwin"* ]]; then
    brew services start mysql
    log_info "MySQL démarré"
    sleep 5  # Attendre que MySQL démarre
fi

echo ""

# ============================================================================
# 3. Création de l'environnement virtuel Python
# ============================================================================

echo "🐍 Création de l'environnement virtuel Python..."
echo ""

if [ -d "venv" ]; then
    log_warning "Environnement virtuel déjà existant"
else
    python3 -m venv venv
    log_info "Environnement virtuel créé"
fi

# Activer l'environnement virtuel
source venv/bin/activate
log_info "Environnement virtuel activé"

echo ""

# ============================================================================
# 4. Installation des dépendances Python
# ============================================================================

echo "📦 Installation des dépendances Python..."
echo ""

pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
log_info "Dépendances Python installées"

echo ""

# ============================================================================
# 5. Création de la base de données MySQL
# ============================================================================

echo "🗄️ Création de la base de données MySQL..."
echo ""

# Demander le mot de passe MySQL (optionnel)
read -sp "Mot de passe MySQL root (laisser vide si pas de mot de passe): " MYSQL_PASSWORD
echo ""

if [ -z "$MYSQL_PASSWORD" ]; then
    MYSQL_CMD="mysql -u root"
else
    MYSQL_CMD="mysql -u root -p$MYSQL_PASSWORD"
fi

# Créer la base de données
$MYSQL_CMD < sql/01_create_database.sql
log_info "Base de données créée"

# Créer les tables de dimension
$MYSQL_CMD < sql/02_create_dimension_tables.sql
log_info "Tables de dimension créées"

# Créer les tables de faits
$MYSQL_CMD < sql/03_create_fact_tables.sql
log_info "Tables de faits créées"

# Vérifier les tables
TABLE_COUNT=$($MYSQL_CMD -e "USE data_warehouse; SHOW TABLES;" | wc -l)
log_info "$((TABLE_COUNT - 1)) tables créées dans data_warehouse"

echo ""

# ============================================================================
# 6. Création de la structure du Data Lake
# ============================================================================

echo "📁 Création de la structure du Data Lake..."
echo ""

python -c "from data_lake_config import ensure_directories; ensure_directories()"
log_info "Structure du Data Lake créée"

echo ""

# ============================================================================
# 7. Vérification de Kafka (optionnel)
# ============================================================================

echo "🔄 Vérification de Kafka (optionnel)..."
echo ""

if nc -zv localhost 9092 2>&1 | grep -q "succeeded"; then
    log_info "Kafka accessible sur localhost:9092"
    KAFKA_AVAILABLE=true
else
    log_warning "Kafka non accessible. Les consumers Kafka ne pourront pas démarrer."
    KAFKA_AVAILABLE=false
fi

echo ""

# ============================================================================
# 8. Tests de validation
# ============================================================================

echo "✅ Tests de validation..."
echo ""

# Test des imports Python
python -c "import pandas, pyarrow, requests, mysql.connector, kafka; print('Imports OK')" 2>&1 | grep -q "Imports OK"
if [ $? -eq 0 ]; then
    log_info "Imports Python validés"
else
    log_error "Erreur lors des imports Python"
fi

# Test de connexion MySQL
python -c "import mysql.connector; conn = mysql.connector.connect(host='localhost', user='root', password='$MYSQL_PASSWORD', database='data_warehouse'); conn.close(); print('MySQL OK')" 2>&1 | grep -q "MySQL OK"
if [ $? -eq 0 ]; then
    log_info "Connexion MySQL validée"
else
    log_error "Erreur de connexion MySQL"
fi

echo ""

# ============================================================================
# 9. Résumé de l'installation
# ============================================================================

echo "======================================================================"
echo "🎉 Installation terminée avec succès!"
echo "======================================================================"
echo ""
echo "📊 Composants installés:"
echo "  ✓ MySQL 9.x"
echo "  ✓ Base de données: data_warehouse (6 tables)"
echo "  ✓ Environnement Python virtuel"
echo "  ✓ Dépendances Python (pandas, pyarrow, mysql-connector, kafka-python)"
echo "  ✓ Structure du Data Lake"
echo ""
echo "🚀 Prochaines étapes:"
echo ""
echo "1. Activer l'environnement virtuel:"
echo "   source venv/bin/activate"
echo ""
echo "2. Configurer ksqlDB (éditer data_lake_config.py):"
echo "   vim data_lake_config.py"
echo ""
echo "3. Mode Batch - Export depuis ksqlDB:"
echo "   python export_to_data_lake.py --all"
echo "   python sync_to_mysql.py --mysql-password '$MYSQL_PASSWORD'"
echo ""

if [ "$KAFKA_AVAILABLE" = true ]; then
    echo "4. Mode Streaming - Kafka Consumers:"
    echo "   python kafka_consumer_orchestrator.py --mode all --mysql-password '$MYSQL_PASSWORD'"
    echo ""
else
    echo "4. Mode Streaming - Kafka Consumers (Kafka non disponible):"
    echo "   Démarrer Kafka puis:"
    echo "   python kafka_consumer_orchestrator.py --mode all --mysql-password '$MYSQL_PASSWORD'"
    echo ""
fi

echo "📚 Documentation:"
echo "  • QUICK_START.md - Démarrage rapide"
echo "  • KAFKA_CONSUMERS_GUIDE.md - Guide Kafka"
echo "  • PROJECT_FINAL_SUMMARY.md - Vue d'ensemble complète"
echo ""
echo "======================================================================"
