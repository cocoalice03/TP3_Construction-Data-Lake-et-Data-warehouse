"""
Script de test pour valider l'installation du Data Lake
"""
import sys
from pathlib import Path
from datetime import datetime

# Couleurs pour l'affichage
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def print_success(message):
    print(f"{GREEN}✓{RESET} {message}")


def print_error(message):
    print(f"{RED}✗{RESET} {message}")


def print_warning(message):
    print(f"{YELLOW}⚠{RESET} {message}")


def test_imports():
    """Test des imports Python"""
    print("\n1. Test des imports Python...")
    
    try:
        import pandas
        print_success(f"pandas {pandas.__version__}")
    except ImportError:
        print_error("pandas non installé")
        return False
    
    try:
        import pyarrow
        print_success(f"pyarrow {pyarrow.__version__}")
    except ImportError:
        print_error("pyarrow non installé")
        return False
    
    try:
        import requests
        print_success(f"requests {requests.__version__}")
    except ImportError:
        print_error("requests non installé")
        return False
    
    return True


def test_configuration():
    """Test de la configuration"""
    print("\n2. Test de la configuration...")
    
    try:
        from data_lake_config import (
            DATA_LAKE_ROOT, STREAMS_DIR, TABLES_DIR,
            FEEDS_DIR, LOGS_DIR, STREAMS_CONFIG, TABLES_CONFIG
        )
        print_success("Configuration chargée")
        print(f"   Racine: {DATA_LAKE_ROOT}")
        print(f"   Streams: {len(STREAMS_CONFIG)}")
        print(f"   Tables: {len(TABLES_CONFIG)}")
        return True
    except Exception as e:
        print_error(f"Erreur de configuration: {e}")
        return False


def test_directory_structure():
    """Test de la structure de dossiers"""
    print("\n3. Test de la structure de dossiers...")
    
    try:
        from data_lake_config import ensure_directories, DATA_LAKE_ROOT
        
        ensure_directories()
        
        required_dirs = [
            DATA_LAKE_ROOT,
            DATA_LAKE_ROOT / "streams",
            DATA_LAKE_ROOT / "tables",
            DATA_LAKE_ROOT / "feeds",
            DATA_LAKE_ROOT / "feeds" / "active",
            DATA_LAKE_ROOT / "feeds" / "archived",
            DATA_LAKE_ROOT / "logs"
        ]
        
        all_exist = True
        for directory in required_dirs:
            if directory.exists():
                print_success(f"{directory.name}/ existe")
            else:
                print_error(f"{directory.name}/ manquant")
                all_exist = False
        
        return all_exist
    except Exception as e:
        print_error(f"Erreur lors de la création des dossiers: {e}")
        return False


def test_feed_management():
    """Test de la gestion des feeds"""
    print("\n4. Test de la gestion des feeds...")
    
    try:
        from manage_feeds import FeedManager
        
        manager = FeedManager()
        print_success("FeedManager initialisé")
        
        # Compter les feeds actifs
        active_feeds = list(manager.active_dir.glob("*.json"))
        print(f"   Feeds actifs: {len(active_feeds)}")
        
        return True
    except Exception as e:
        print_error(f"Erreur de gestion des feeds: {e}")
        return False


def test_metadata_utils():
    """Test des utilitaires de métadonnées"""
    print("\n5. Test des utilitaires de métadonnées...")
    
    try:
        from metadata_utils import MetadataReader, MetadataAnalyzer
        
        print_success("MetadataReader disponible")
        print_success("MetadataAnalyzer disponible")
        
        # Test de lecture des métadonnées
        all_metadata = MetadataReader.list_all_metadata()
        print(f"   Streams avec métadonnées: {len(all_metadata['streams'])}")
        print(f"   Tables avec métadonnées: {len(all_metadata['tables'])}")
        
        return True
    except Exception as e:
        print_error(f"Erreur des utilitaires: {e}")
        return False


def test_parquet_write():
    """Test d'écriture Parquet"""
    print("\n6. Test d'écriture Parquet...")
    
    try:
        import pandas as pd
        import pyarrow.parquet as pq
        from data_lake_config import DATA_LAKE_ROOT
        
        # Créer un DataFrame de test
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'value': ['a', 'b', 'c'],
            'timestamp': [datetime.now()] * 3
        })
        
        # Écrire en Parquet
        test_file = DATA_LAKE_ROOT / "test.parquet"
        df.to_parquet(test_file, compression='snappy')
        
        # Lire et vérifier
        df_read = pd.read_parquet(test_file)
        
        if len(df_read) == 3:
            print_success("Écriture/lecture Parquet OK")
            test_file.unlink()  # Supprimer le fichier de test
            return True
        else:
            print_error("Données Parquet incorrectes")
            return False
    except Exception as e:
        print_error(f"Erreur Parquet: {e}")
        return False


def test_ksqldb_connection():
    """Test de connexion à ksqlDB (optionnel)"""
    print("\n7. Test de connexion ksqlDB (optionnel)...")
    
    try:
        from data_lake_config import KSQLDB_CONFIG
        import requests
        
        url = f"http://{KSQLDB_CONFIG['host']}:{KSQLDB_CONFIG['port']}/info"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print_success("ksqlDB accessible")
            info = response.json()
            print(f"   Version: {info.get('KsqlServerInfo', {}).get('version', 'N/A')}")
            return True
        else:
            print_warning("ksqlDB non accessible (optionnel)")
            return True  # Non bloquant
    except Exception as e:
        print_warning(f"ksqlDB non accessible: {e} (optionnel)")
        return True  # Non bloquant


def main():
    """Exécute tous les tests"""
    print("=" * 60)
    print("🧪 TEST DE L'INSTALLATION DU DATA LAKE")
    print("=" * 60)
    
    tests = [
        ("Imports Python", test_imports),
        ("Configuration", test_configuration),
        ("Structure de dossiers", test_directory_structure),
        ("Gestion des feeds", test_feed_management),
        ("Utilitaires métadonnées", test_metadata_utils),
        ("Écriture Parquet", test_parquet_write),
        ("Connexion ksqlDB", test_ksqldb_connection)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Erreur inattendue: {e}")
            results.append((name, False))
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")
    
    print("\n" + "-" * 60)
    print(f"Résultat: {passed}/{total} tests réussis")
    
    if passed == total:
        print(f"\n{GREEN}✓ Installation validée avec succès!{RESET}")
        print("\nProchaines étapes:")
        print("  1. Configurer ksqlDB dans data_lake_config.py")
        print("  2. Synchroniser les feeds: python manage_feeds.py sync")
        print("  3. Lancer un export: python export_to_data_lake.py --all")
        return 0
    else:
        print(f"\n{RED}✗ Certains tests ont échoué{RESET}")
        print("\nVérifiez:")
        print("  1. Les dépendances sont installées: pip install -r requirements.txt")
        print("  2. Les permissions sur les dossiers")
        print("  3. La configuration dans data_lake_config.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
