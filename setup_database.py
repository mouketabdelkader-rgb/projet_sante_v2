#!/usr/bin/env python3
"""
Setup COMPLET de la base de données Oracle
Exécute les 4 fichiers SQL : architecture, vues, procédures, triggers
"""
import oracledb
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Initialiser le client Oracle
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try:
        oracledb.init_oracle_client(lib_dir=oracle_home)
        print(f"Client Oracle initialisé depuis : {oracle_home}")
    except Exception as e:
        pass

# Configuration
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_dsn = os.getenv("DB_DSN")
wallet_path = os.getenv("WALLET_PATH")

if not all([db_user, db_password, db_dsn, wallet_path]):
    print("Erreur : Variables manquantes dans .env")
    sys.exit(1)

# PARSER INTELLIGENT avec gestion des quotes et commentaires
def parse_sql_commands(sql_text):
    """Parse le SQL en séparant correctement les blocs PL/SQL, gérant quotes et commentaires"""
    commands = []
    current_cmd = []
    in_plsql = False
    in_multiline_comment = False
    
    for line in sql_text.split('\n'):
        stripped = line.strip()
        
        # Gérer les commentaires multi-lignes /* */
        if '/*' in stripped:
            in_multiline_comment = True
        if in_multiline_comment:
            if '*/' in stripped:
                in_multiline_comment = False
            continue  # Ignorer cette ligne
        
        # Ignorer commentaires simples, lignes vides et commandes SQL*Plus
        if not stripped or stripped.startswith('--') or stripped.upper().startswith(('PROMPT', 'COMMIT')):
            continue
        
        # Détecter début de bloc PL/SQL
        upper_stripped = stripped.upper()
        if any(upper_stripped.startswith(kw) for kw in ['BEGIN', 'DECLARE', 'CREATE OR REPLACE PROCEDURE', 
                                                          'CREATE OR REPLACE FUNCTION', 'CREATE OR REPLACE TRIGGER']):
            in_plsql = True
        
        current_cmd.append(line)
        
        # Détecter fin de commande
        if in_plsql:
            if stripped == '/':
                cmd = '\n'.join(current_cmd[:-1])
                if cmd.strip():
                    commands.append(cmd)
                current_cmd = []
                in_plsql = False
        else:
            # Pour les commandes SQL normales, vérifier si le ; est en dehors des quotes
            if stripped.endswith(';'):
                # Compter les quotes simples dans la ligne
                quote_count = stripped.count("'")
                
                # Si nombre pair de quotes, le ; final est bien une fin de commande
                if quote_count % 2 == 0:
                    cmd = '\n'.join(current_cmd)
                    cmd = cmd.rstrip().rstrip(';').strip()
                    if cmd:
                        commands.append(cmd)
                    current_cmd = []
    
    if current_cmd:
        cmd = '\n'.join(current_cmd).strip()
        if cmd:
            commands.append(cmd)
    
    return commands

# Liste des fichiers SQL à exécuter
sql_files = [
    ("sql/01_create_architecture.sql", "Architecture (tables + index)"),
    ("sql/02_create_views.sql", "Vues métier"),
    ("sql/03_create_procedures.sql", "Procédures stockées"),
    ("sql/04_create_triggers.sql", "Triggers")
]

print("="*60)
print("SETUP COMPLET DE LA BASE DE DONNÉES ORACLE")
print("="*60)

# Connexion
connection = None
try:
    print("\nConnexion à Oracle...")
    connection = oracledb.connect(
        user=db_user,
        password=db_password,
        dsn=db_dsn,
        config_dir=wallet_path,
        wallet_location=wallet_path
    )
    print("✓ Connexion réussie\n")
    
    cursor = connection.cursor()
    
    total_commands = 0
    total_success = 0
    
    # Exécuter chaque fichier SQL
    for sql_file, description in sql_files:
        print(f"\n{'='*60}")
        print(f"📄 {description}")
        print(f"   Fichier: {sql_file}")
        print('='*60)
        
        # Lire le fichier
        try:
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
        except FileNotFoundError:
            print(f"⚠ Fichier non trouvé, ignoré")
            continue
        
        # Parser les commandes
        sql_commands = parse_sql_commands(sql_content)
        print(f"  Commandes trouvées: {len(sql_commands)}")
        
        file_success = 0
        
        # Exécuter chaque commande
        for i, command in enumerate(sql_commands, 1):
            cmd_upper = command.upper().strip()
            
            # Affichage contextuel simplifié
            if cmd_upper.startswith('BEGIN'):
                display = "Bloc PL/SQL nettoyage"
            elif cmd_upper.startswith('CREATE TABLE'):
                display = f"Table {command.split()[2]}"
            elif cmd_upper.startswith('CREATE INDEX'):
                display = f"Index {command.split()[2]}"
            elif cmd_upper.startswith('CREATE OR REPLACE VIEW'):
                display = f"Vue {command.split()[4]}"
            elif cmd_upper.startswith('CREATE OR REPLACE PROCEDURE'):
                display = f"Procédure {command.split()[4]}"
            elif cmd_upper.startswith('CREATE OR REPLACE FUNCTION'):
                display = f"Fonction {command.split()[4]}"
            elif cmd_upper.startswith('CREATE OR REPLACE TRIGGER'):
                display = f"Trigger {command.split()[4]}"
            elif cmd_upper.startswith('COMMENT'):
                continue  # Ignorer silencieusement
            else:
                display = f"{cmd_upper[:30]}..."
            
            try:
                cursor.execute(command)
                print(f"  ✓ [{i:2d}] {display}")
                file_success += 1
                total_success += 1
            except oracledb.Error as e:
                error_code = e.args[0].code if hasattr(e.args[0], 'code') else 0
                
                # Ignorer erreurs acceptables
                if error_code == 942:  # Table n'existe pas
                    continue
                elif error_code == 955:  # Objet existe déjà
                    print(f"  - [{i:2d}] {display} (existe déjà)")
                    continue
                elif "ORA-00942" in str(e) and cmd_upper.startswith('BEGIN'):
                    continue
                
                # Erreur réelle
                print(f"\n✗ ERREUR sur commande {i}:")
                print(f"  {display}")
                print(f"  Erreur: {e}")
                connection.rollback()
                sys.exit(1)
        
        print(f"  ✅ {file_success} commandes exécutées")
        total_commands += len(sql_commands)
    
    connection.commit()
    
    # Statistiques finales
    print(f"\n{'='*60}")
    print("📊 RÉCAPITULATIF")
    print('='*60)
    
    cursor.execute("SELECT COUNT(*) FROM user_tables")
    nb_tables = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM user_indexes WHERE index_name NOT LIKE 'SYS_%'")
    nb_indexes = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM user_views")
    nb_views = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM user_objects 
        WHERE object_type IN ('PROCEDURE', 'FUNCTION')
    """)
    nb_procs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM user_triggers")
    nb_triggers = cursor.fetchone()[0]
    
    print(f"  Tables créées       : {nb_tables}")
    print(f"  Index créés         : {nb_indexes}")
    print(f"  Vues créées         : {nb_views}")
    print(f"  Procédures/Fonctions: {nb_procs}")
    print(f"  Triggers créés      : {nb_triggers}")
    print(f"  Total commandes     : {total_success}/{total_commands}")
    
    print(f"\n{'='*60}")
    print("✅ SETUP TERMINÉ AVEC SUCCÈS")
    print('='*60)

except oracledb.Error as e:
    print(f"\n✗ Erreur Oracle : {e}")
    if connection:
        connection.rollback()
    sys.exit(1)

finally:
    if connection:
        connection.close()
        print("\nConnexion fermée.")

print("\n🎯 Prochaine étape :")
print("   python main.py /chemin/vers/fichier_RPPS.txt")
