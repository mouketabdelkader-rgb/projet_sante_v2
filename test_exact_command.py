#!/usr/bin/env python3
"""
Test de la commande EXACTE qui échoue
"""
import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

# Connexion (MODE THIN)
conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)

cursor = conn.cursor()

print("="*60)
print("TEST DE LA COMMANDE EXACTE QUI ÉCHOUE")
print("="*60)

# Nettoyage
print("\n[Nettoyage]")
try:
    cursor.execute("DROP TABLE professionnels CASCADE CONSTRAINTS")
    print("  ✓ Table professionnels supprimée")
except:
    print("  - Pas de table existante")

# Créer la table professionnels (EXACTEMENT comme dans le SQL)
print("\n[Création table professionnels]")
cursor.execute("""
CREATE TABLE professionnels (
    id_professionnel VARCHAR2(20) PRIMARY KEY,
    nom VARCHAR2(100) NOT NULL,
    prenom VARCHAR2(100),
    nom_exercice VARCHAR2(100),
    civilite VARCHAR2(10),
    code_profession VARCHAR2(10),
    libelle_profession VARCHAR2(200),
    categorie_profession VARCHAR2(50),
    date_naissance DATE,
    statut_enregistrement VARCHAR2(50) DEFAULT 'Actif',
    date_premiere_apparition DATE DEFAULT SYSDATE,
    date_derniere_maj DATE DEFAULT SYSDATE,
    date_import DATE DEFAULT SYSDATE,
    source_data VARCHAR2(50) DEFAULT 'RPPS',
    hash_data VARCHAR2(64)
)
""")
print("  ✓ Table professionnels créée")

# Tester la commande EXACTE qui échoue
print("\n[Test 1] Commande EXACTE du fichier SQL...")
try:
    cursor.execute("CREATE INDEX idx_prof_prenom ON professionnels(prenom);")
    print("  ✓ Index idx_prof_prenom créé AVEC SUCCÈS !")
except Exception as e:
    print(f"  ✗ ÉCHEC: {e}")

# Tester sans le point-virgule
print("\n[Test 2] Sans point-virgule...")
try:
    cursor.execute("CREATE INDEX idx_prof_nom ON professionnels(nom)")
    print("  ✓ Index idx_prof_nom créé AVEC SUCCÈS !")
except Exception as e:
    print(f"  ✗ ÉCHEC: {e}")

# Vérifier les index créés
print("\n[Vérification]")
cursor.execute("""
    SELECT index_name, column_name 
    FROM user_ind_columns 
    WHERE table_name = 'PROFESSIONNELS'
    ORDER BY index_name
""")
indexes = cursor.fetchall()
for idx in indexes:
    print(f"  - {idx[0]}: {idx[1]}")

# Nettoyage final
print("\n[Nettoyage final]")
cursor.execute("DROP TABLE professionnels CASCADE CONSTRAINTS")
print("  ✓ Table supprimée")

conn.close()

print("\n" + "="*60)
print("TEST TERMINÉ")
print("="*60)
