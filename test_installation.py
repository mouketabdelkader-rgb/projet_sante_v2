#!/usr/bin/env python3
"""
Script de test et validation de l'installation
Vérifie que tous les composants sont opérationnels
"""
import sys
from pathlib import Path
import os

sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test des imports Python"""
    print("\n[1/6] Test des imports Python...")
    
    try:
        import oracledb
        print("  ✓ oracledb")
    except ImportError:
        print("  ❌ oracledb - Installer avec: pip install oracledb")
        return False
    
    try:
        import yaml
        print("  ✓ PyYAML")
    except ImportError:
        print("  ❌ PyYAML - Installer avec: pip install PyYAML")
        return False
    
    try:
        from dotenv import load_dotenv
        print("  ✓ python-dotenv")
    except ImportError:
        print("  ❌ python-dotenv - Installer avec: pip install python-dotenv")
        return False
    
    try:
        from utils import get_logger
        print("  ✓ utils.logger")
    except ImportError as e:
        print(f"  ❌ utils.logger - {e}")
        return False
    
    try:
        from extractors import RPPSExtractor
        print("  ✓ extractors.rpps_extractor")
    except ImportError as e:
        print(f"  ❌ extractors.rpps_extractor - {e}")
        return False
    
    try:
        from loaders import OracleLoader
        print("  ✓ loaders.oracle_loader")
    except ImportError as e:
        print(f"  ❌ loaders.oracle_loader - {e}")
        return False
    
    return True


def test_config_files():
    """Test de la présence des fichiers de configuration"""
    print("\n[2/6] Test des fichiers de configuration...")
    
    files = {
        'config/config.yaml': 'Configuration principale',
        'config/mapping_rpps.yaml': 'Mapping RPPS',
        '.env': 'Variables d\'environnement (copier depuis .env.template)',
    }
    
    all_ok = True
    for file_path, description in files.items():
        if Path(file_path).exists():
            print(f"  ✓ {file_path} - {description}")
        else:
            print(f"  ❌ {file_path} manquant - {description}")
            all_ok = False
    
    return all_ok


def test_sql_scripts():
    """Test de la présence des scripts SQL"""
    print("\n[3/6] Test des scripts SQL...")
    
    scripts = [
        '01_create_architecture.sql',
        '02_create_views.sql',
        '03_create_procedures.sql',
        '04_create_triggers.sql'
    ]
    
    all_ok = True
    for script in scripts:
        script_path = Path('sql') / script
        if script_path.exists():
            print(f"  ✓ {script}")
        else:
            print(f"  ❌ {script} manquant")
            all_ok = False
    
    return all_ok


def test_env_variables():
    """Test des variables d'environnement"""
    print("\n[4/6] Test des variables d'environnement...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        'DB_USER': 'Utilisateur Oracle',
        'DB_PASSWORD': 'Mot de passe Oracle',
        'DB_DSN': 'DSN Oracle',
        'WALLET_PATH': 'Chemin vers le wallet Oracle'
    }
    
    all_ok = True
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value:
            masked_value = value[:4] + '***' if len(value) > 4 else '***'
            print(f"  ✓ {var_name} = {masked_value} - {description}")
        else:
            print(f"  ❌ {var_name} non défini - {description}")
            all_ok = False
    
    return all_ok


def test_oracle_connection():
    """Test de connexion Oracle"""
    print("\n[5/6] Test de connexion Oracle...")
    
    try:
        import oracledb
        from dotenv import load_dotenv
        load_dotenv()
        
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_dsn = os.getenv('DB_DSN')
        wallet_path = os.getenv('WALLET_PATH')
        
        if not all([db_user, db_password, db_dsn, wallet_path]):
            print("  ⚠️  Variables d'environnement manquantes - test ignoré")
            return None
        
        # Initialise le client Oracle si nécessaire
        oracle_home = os.getenv('ORACLE_HOME')
        if oracle_home:
            try:
                oracledb.init_oracle_client(lib_dir=oracle_home)
            except:
                pass  # Peut être déjà initialisé
        
        print(f"  Connexion à {db_dsn}...")
        conn = oracledb.connect(
            user=db_user,
            password=db_password,
            dsn=db_dsn,
            config_dir=wallet_path,
            wallet_location=wallet_path
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_tables")
        nb_tables = cursor.fetchone()[0]
        
        print(f"  ✓ Connexion réussie")
        print(f"  ℹ️  {nb_tables} tables trouvées dans la base")
        
        if nb_tables == 0:
            print("  ⚠️  Aucune table - Exécuter setup_database.py")
        elif nb_tables < 12:
            print(f"  ⚠️  Seulement {nb_tables}/12 tables - Architecture incomplète")
        else:
            print(f"  ✓ Architecture complète ({nb_tables} tables)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur de connexion: {e}")
        return False


def test_utils_functions():
    """Test des fonctions utilitaires"""
    print("\n[6/6] Test des fonctions utilitaires...")
    
    try:
        from utils import (
            validate_rpps_id,
            validate_telephone,
            validate_email,
            calculate_professionnel_hash
        )
        
        # Test RPPS
        assert validate_rpps_id('12345678901') == True
        assert validate_rpps_id('123') == False
        print("  ✓ validate_rpps_id")
        
        # Test téléphone
        is_valid, clean = validate_telephone('06 12 34 56 78')
        assert is_valid == True
        assert clean == '0612345678'
        print("  ✓ validate_telephone")
        
        # Test email
        assert validate_email('test@example.com') == True
        assert validate_email('invalid') == False
        print("  ✓ validate_email")
        
        # Test hash
        hash1 = calculate_professionnel_hash('Dupont', 'Jean', '10', 'Actif')
        assert len(hash1) == 64  # SHA256
        print("  ✓ calculate_professionnel_hash")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return False


def main():
    """Fonction principale"""
    print("="*60)
    print("TEST ET VALIDATION DE L'INSTALLATION")
    print("="*60)
    
    results = {
        'Imports Python': test_imports(),
        'Fichiers config': test_config_files(),
        'Scripts SQL': test_sql_scripts(),
        'Variables env': test_env_variables(),
        'Connexion Oracle': test_oracle_connection(),
        'Fonctions utils': test_utils_functions()
    }
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ OK"
        elif result is False:
            status = "❌ ERREUR"
        else:
            status = "⚠️  IGNORÉ"
        
        print(f"{test_name:<25} {status}")
    
    # Conclusion
    errors = [name for name, result in results.items() if result is False]
    
    if not errors:
        print("\n✅ TOUS LES TESTS SONT PASSÉS")
        print("\n📝 Prochaines étapes:")
        print("  1. Exécuter: python setup_database.py")
        print("  2. Obtenir un fichier RPPS")
        print("  3. Exécuter: python main.py fichier_rpps.txt")
        return 0
    else:
        print(f"\n❌ {len(errors)} TEST(S) EN ERREUR:")
        for error in errors:
            print(f"  - {error}")
        print("\n📝 Corriger les erreurs ci-dessus avant de continuer")
        return 1


if __name__ == '__main__':
    sys.exit(main())
