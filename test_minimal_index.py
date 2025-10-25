#!/usr/bin/env python3
"""
Test minimal pour diagnostiquer ORA-02158
On va créer une table simple et tester différents types d'index
"""
import oracledb
import os
from dotenv import load_dotenv

load_dotenv()

# Connexion (MODE THIN - pas d'init_oracle_client)
conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)

cursor = conn.cursor()

print("="*60)
print("TEST DIAGNOSTIC - ORA-02158")
print("="*60)

# Test 1: Créer une table test simple
print("\n[Test 1] Création table test...")
try:
    cursor.execute("DROP TABLE test_index_simple CASCADE CONSTRAINTS")
    print("  ✓ Table existante supprimée")
except:
    print("  - Pas de table existante")

cursor.execute("""
    CREATE TABLE test_index_simple (
        id NUMBER PRIMARY KEY,
        nom VARCHAR2(100),
        prenom VARCHAR2(100)
    )
""")
print("  ✓ Table créée")

# Test 2: Index le plus simple possible
print("\n[Test 2] Index ultra-simple...")
try:
    cursor.execute("CREATE INDEX idx_test_id ON test_index_simple(id)")
    print("  ✓ Index sur ID créé")
except Exception as e:
    print(f"  ✗ ÉCHEC: {e}")

# Test 3: Index sur VARCHAR2
print("\n[Test 3] Index sur VARCHAR2...")
try:
    cursor.execute("CREATE INDEX idx_test_nom ON test_index_simple(nom)")
    print("  ✓ Index sur nom créé")
except Exception as e:
    print(f"  ✗ ÉCHEC: {e}")

# Test 4: Vérifier les privilèges
print("\n[Test 4] Privilèges utilisateur...")
cursor.execute("""
    SELECT privilege 
    FROM session_privs 
    WHERE privilege LIKE '%INDEX%'
    ORDER BY privilege
""")
privs = cursor.fetchall()
if privs:
    for priv in privs:
        print(f"  ✓ {priv[0]}")
else:
    print("  ✗ AUCUN privilège INDEX détecté")

# Test 5: Paramètres de session
print("\n[Test 5] Paramètres de session...")
cursor.execute("""
    SELECT name, value 
    FROM v$parameter 
    WHERE name IN ('compatible', 'db_create_file_dest')
""")
params = cursor.fetchall()
for param in params:
    print(f"  - {param[0]}: {param[1]}")

# Test 6: Lister les index existants
print("\n[Test 6] Index existants sur test_index_simple...")
cursor.execute("""
    SELECT index_name, column_name 
    FROM user_ind_columns 
    WHERE table_name = 'TEST_INDEX_SIMPLE'
""")
indexes = cursor.fetchall()
if indexes:
    for idx in indexes:
        print(f"  - {idx[0]}: {idx[1]}")
else:
    print("  - Aucun index trouvé")

# Nettoyage
print("\n[Nettoyage]")
cursor.execute("DROP TABLE test_index_simple CASCADE CONSTRAINTS")
print("  ✓ Table test supprimée")

conn.close()

print("\n" + "="*60)
print("TEST TERMINÉ")
print("="*60)
