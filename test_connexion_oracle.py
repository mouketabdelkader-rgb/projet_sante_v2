#!/usr/bin/env python3
"""
Script de diagnostic complet pour vérifier la connexion Oracle
et l'environnement avant le setup de la base de données.

Usage: python test_connexion_oracle.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Couleurs pour l'affichage
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text):
    """Affiche un en-tête coloré"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text):
    """Affiche un message de succès"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    """Affiche un message d'erreur"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    """Affiche un avertissement"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    """Affiche une information"""
    print(f"  {text}")


def test_1_environment_variables():
    """Test 1: Vérification des variables d'environnement"""
    print_header("TEST 1 : Variables d'environnement")
    
    # Charger le fichier .env
    env_file = Path('.env')
    if not env_file.exists():
        print_error("Fichier .env introuvable !")
        print_info("Créez le fichier .env à partir de config/.env.template")
        return False
    
    print_success("Fichier .env trouvé")
    load_dotenv()
    
    # Variables requises
    required_vars = {
        'DB_USER': 'Utilisateur Oracle',
        'DB_PASSWORD': 'Mot de passe Oracle',
        'DB_DSN': 'DSN de connexion',
        'WALLET_PATH': 'Chemin du wallet',
        'ORACLE_HOME': 'Chemin Oracle Instant Client'
    }
    
    all_ok = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Masquer le mot de passe
            if var == 'DB_PASSWORD':
                display_value = '*' * len(value)
            else:
                display_value = value
            print_success(f"{description}: {display_value}")
        else:
            print_error(f"{description} (${var}) non défini")
            all_ok = False
    
    return all_ok


def test_2_wallet_files():
    """Test 2: Vérification des fichiers du wallet Oracle"""
    print_header("TEST 2 : Fichiers du Wallet Oracle")
    
    wallet_path = os.getenv('WALLET_PATH')
    if not wallet_path:
        print_error("WALLET_PATH non défini dans .env")
        return False
    
    wallet_dir = Path(wallet_path)
    if not wallet_dir.exists():
        print_error(f"Le dossier wallet n'existe pas : {wallet_path}")
        return False
    
    print_success(f"Dossier wallet trouvé : {wallet_path}")
    
    # Fichiers requis dans le wallet
    required_files = [
        'cwallet.sso',
        'tnsnames.ora',
        'sqlnet.ora'
    ]
    
    all_ok = True
    for filename in required_files:
        file_path = wallet_dir / filename
        if file_path.exists():
            size = file_path.stat().st_size
            print_success(f"{filename} ({size} bytes)")
        else:
            print_error(f"{filename} manquant !")
            all_ok = False
    
    # Lister tous les fichiers du wallet
    print_info("\nContenu complet du wallet :")
    for file in wallet_dir.iterdir():
        if file.is_file():
            print_info(f"  - {file.name}")
    
    return all_ok


def test_3_oracle_client():
    """Test 3: Vérification d'Oracle Instant Client"""
    print_header("TEST 3 : Oracle Instant Client")
    
    oracle_home = os.getenv('ORACLE_HOME')
    if not oracle_home:
        print_error("ORACLE_HOME non défini dans .env")
        return False
    
    oracle_dir = Path(oracle_home)
    if not oracle_dir.exists():
        print_error(f"Le dossier Oracle Client n'existe pas : {oracle_home}")
        return False
    
    print_success(f"Dossier Oracle Client trouvé : {oracle_home}")
    
    # Rechercher les bibliothèques essentielles
    essential_libs = ['libclntsh.so', 'libnnz']
    
    found_libs = []
    for lib in oracle_dir.glob('*.so*'):
        found_libs.append(lib.name)
    
    if found_libs:
        print_info(f"\nBibliothèques trouvées ({len(found_libs)}) :")
        for lib in sorted(found_libs)[:10]:  # Afficher les 10 premières
            print_info(f"  - {lib}")
        if len(found_libs) > 10:
            print_info(f"  ... et {len(found_libs) - 10} autres")
        return True
    else:
        print_error("Aucune bibliothèque .so trouvée !")
        return False


def test_4_python_packages():
    """Test 4: Vérification des packages Python requis"""
    print_header("TEST 4 : Packages Python")
    
    # Mapping: nom du package pip -> nom du module à importer
    required_packages = {
        'oracledb': ('Driver Oracle', 'oracledb'),
        'python-dotenv': ('Gestion variables d\'environnement', 'dotenv'),
        'pyyaml': ('Lecture fichiers YAML', 'yaml')
    }
    
    all_ok = True
    for package, (description, import_name) in required_packages.items():
        try:
            __import__(import_name)
            print_success(f"{description} ({package})")
        except ImportError:
            print_error(f"{description} ({package}) non installé")
            print_info(f"  → pip install {package}")
            all_ok = False
    
    return all_ok


def test_5_database_connection():
    """Test 5: Connexion à la base de données Oracle"""
    print_header("TEST 5 : Connexion à la base Oracle")
    
    try:
        import oracledb
    except ImportError:
        print_error("Module oracledb non installé")
        print_info("Exécutez: pip install oracledb")
        return False
    
    # Configuration de la connexion
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_dsn = os.getenv('DB_DSN')
    wallet_path = os.getenv('WALLET_PATH')
    
    if not all([db_user, db_password, db_dsn, wallet_path]):
        print_error("Variables de connexion incomplètes")
        return False
    
    print_info(f"Tentative de connexion à : {db_dsn}")
    print_info(f"Utilisateur : {db_user}")
    print_info(f"Wallet : {wallet_path}")
    
    try:
        # Initialiser le client Oracle en mode Thick (utilise Instant Client)
        print_info("\nInitialisation du client Oracle en mode Thick...")
        
        oracle_home = os.getenv('ORACLE_HOME')
        try:
            oracledb.init_oracle_client(lib_dir=oracle_home)
            print_success("Mode Thick activé avec Instant Client")
        except Exception as e:
            # Déjà initialisé ou mode Thick déjà actif
            print_info(f"Client déjà initialisé ou mode Thick actif")
        
        # Connexion avec le wallet
        connection = oracledb.connect(
            user=db_user,
            password=db_password,
            dsn=db_dsn,
            config_dir=wallet_path,
            wallet_location=wallet_path,
            wallet_password=""
        )
        
        print_success("Connexion établie avec succès !")
        
        # Test d'une requête simple
        cursor = connection.cursor()
        cursor.execute("SELECT 'Hello from Oracle!' as message FROM DUAL")
        result = cursor.fetchone()
        print_success(f"Test requête : {result[0]}")
        
        # Informations sur la base
        cursor.execute("""
            SELECT 
                instance_name, 
                version,
                status
            FROM v$instance
        """)
        instance_info = cursor.fetchone()
        print_info(f"\nInformations base de données :")
        print_info(f"  - Instance : {instance_info[0]}")
        print_info(f"  - Version : {instance_info[1]}")
        print_info(f"  - Statut : {instance_info[2]}")
        
        # Vérifier les privilèges
        cursor.execute("""
            SELECT privilege 
            FROM session_privs 
            WHERE privilege IN ('CREATE TABLE', 'CREATE VIEW', 'CREATE PROCEDURE')
            ORDER BY privilege
        """)
        privileges = cursor.fetchall()
        
        if privileges:
            print_info(f"\nPrivilèges détectés :")
            for priv in privileges:
                print_success(f"  - {priv[0]}")
        else:
            print_warning("Privilèges limités détectés")
        
        cursor.close()
        connection.close()
        
        return True
        
    except oracledb.DatabaseError as e:
        error_obj, = e.args
        print_error(f"Erreur de connexion Oracle")
        print_info(f"  Code erreur : {error_obj.code}")
        print_info(f"  Message : {error_obj.message}")
        
        # Suggestions selon l'erreur
        if "ORA-01017" in str(error_obj.message):
            print_warning("\n💡 Suggestions :")
            print_info("  - Vérifiez DB_USER et DB_PASSWORD dans .env")
            print_info("  - Testez la connexion avec SQL Developer")
        elif "ORA-12154" in str(error_obj.message):
            print_warning("\n💡 Suggestions :")
            print_info("  - Vérifiez DB_DSN dans .env")
            print_info("  - Vérifiez tnsnames.ora dans le wallet")
        elif "wallet" in str(error_obj.message).lower():
            print_warning("\n💡 Suggestions :")
            print_info("  - Vérifiez WALLET_PATH dans .env")
            print_info("  - Vérifiez que cwallet.sso existe")
        
        return False
    
    except Exception as e:
        print_error(f"Erreur inattendue : {str(e)}")
        return False


def test_6_file_structure():
    """Test 6: Vérification de la structure du projet"""
    print_header("TEST 6 : Structure du projet")
    
    required_dirs = [
        'config',
        'sql',
        'extractors',
        'loaders',
        'utils',
        'data',
        'logs'
    ]
    
    required_files = [
        'main.py',
        'setup_database.py',
        'requirements.txt',
        'config/config.yaml',
        'config/mapping_rpps.yaml',
        'sql/01_create_architecture.sql'
    ]
    
    all_ok = True
    
    # Vérifier les dossiers
    print_info("Dossiers requis :")
    for dirname in required_dirs:
        dir_path = Path(dirname)
        if dir_path.exists():
            print_success(f"{dirname}/")
        else:
            print_error(f"{dirname}/ manquant")
            all_ok = False
    
    # Vérifier les fichiers
    print_info("\nFichiers essentiels :")
    for filename in required_files:
        file_path = Path(filename)
        if file_path.exists():
            size = file_path.stat().st_size
            print_success(f"{filename} ({size} bytes)")
        else:
            print_error(f"{filename} manquant")
            all_ok = False
    
    return all_ok


def main():
    """Fonction principale - exécute tous les tests"""
    
    print_header("DIAGNOSTIC COMPLET - Projet Santé v2.0")
    print_info("Ce script vérifie que votre environnement est correctement configuré")
    print_info("pour le setup de la base de données Oracle.\n")
    
    # Liste des tests
    tests = [
        ("Variables d'environnement", test_1_environment_variables),
        ("Fichiers du Wallet", test_2_wallet_files),
        ("Oracle Instant Client", test_3_oracle_client),
        ("Packages Python", test_4_python_packages),
        ("Structure du projet", test_6_file_structure),
        ("Connexion Base de Données", test_5_database_connection),  # En dernier
    ]
    
    results = {}
    
    # Exécuter chaque test
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print_error(f"Erreur lors du test : {str(e)}")
            results[test_name] = False
    
    # Résumé final
    print_header("RÉSUMÉ DES TESTS")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")
    
    print(f"\n{Colors.BOLD}Score : {passed}/{total} tests réussis{Colors.RESET}\n")
    
    if passed == total:
        print_header("✅ TOUS LES TESTS SONT PASSÉS !")
        print_info("Vous pouvez maintenant exécuter :")
        print(f"\n{Colors.GREEN}{Colors.BOLD}  python setup_database.py{Colors.RESET}\n")
        return 0
    else:
        print_header("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print_info("Corrigez les erreurs ci-dessus avant de continuer.")
        print_info("Consultez le guide d'installation pour plus de détails.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
