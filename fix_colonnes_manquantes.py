#!/usr/bin/env python3
"""
Ajout des colonnes de codes standardisés manquantes
À exécuter AVANT import_rpps.py
"""
import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

# Connexion
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try:
        oracledb.init_oracle_client(lib_dir=oracle_home)
    except:
        pass

conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)

cursor = conn.cursor()

print("="*60)
print("AJOUT COLONNES CODES STANDARDISÉS")
print("="*60)

# Liste des colonnes à ajouter
colonnes = [
    # Table professionnels
    ("professionnels", "code_categorie_profession", "VARCHAR2(2)"),
    ("professionnels", "code_savoir_faire", "VARCHAR2(10)"),
    ("professionnels", "libelle_savoir_faire", "VARCHAR2(200)"),
    ("professionnels", "mode_exercice_principal", "VARCHAR2(20)"),
    
    # Table activites
    ("activites", "code_savoir_faire", "VARCHAR2(10)"),
    ("activites", "libelle_savoir_faire", "VARCHAR2(200)"),
    ("activites", "code_mode_exercice", "VARCHAR2(1)"),
]

for table, colonne, type_col in colonnes:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD ({colonne} {type_col})")
        print(f"✅ {table}.{colonne} ajoutée")
    except Exception as e:
        if "ORA-01430" in str(e):
            print(f"⏭️  {table}.{colonne} existe déjà")
        else:
            print(f"❌ Erreur {table}.{colonne}: {e}")

conn.commit()

# Vérification
print("\n" + "="*60)
print("VÉRIFICATION")
print("="*60)

cursor.execute("""
    SELECT column_name 
    FROM user_tab_columns 
    WHERE table_name = 'PROFESSIONNELS'
    AND column_name LIKE '%CODE%'
    ORDER BY column_name
""")

print("\nColonnes 'code' dans professionnels :")
for row in cursor.fetchall():
    print(f"  ✓ {row[0]}")

cursor.execute("""
    SELECT column_name 
    FROM user_tab_columns 
    WHERE table_name = 'ACTIVITES'
    AND column_name LIKE '%CODE%'
    ORDER BY column_name
""")

print("\nColonnes 'code' dans activites :")
for row in cursor.fetchall():
    print(f"  ✓ {row[0]}")

conn.close()

print("\n✅ Colonnes ajoutées avec succès")
print("\n🎯 Vous pouvez maintenant lancer : python import_rpps_v2_optimized.py")
