#!/usr/bin/env python3
"""
Script de diagnostic pour identifier le point de blocage exact
"""
import oracledb
import os
from dotenv import load_dotenv
import time

load_dotenv()

def init_oracle():
    """Initialise la connexion Oracle"""
    oracle_home = os.getenv("ORACLE_HOME")
    if oracle_home:
        try:
            oracledb.init_oracle_client(lib_dir=oracle_home)
        except:
            pass

    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn=os.getenv("DB_DSN"),
        config_dir=os.getenv("WALLET_PATH"),
        wallet_location=os.getenv("WALLET_PATH")
    )

def test_merge_performance():
    """Test de performance du MERGE"""
    print("="*70)
    print("DIAGNOSTIC DU BLOCAGE - TEST MERGE")
    print("="*70)

    conn = init_oracle()
    cursor = conn.cursor()

    # Test 1: Vérifier les index
    print("\n1️⃣  VÉRIFICATION DES INDEX sur professionnels...")
    cursor.execute("""
        SELECT ic.index_name, ic.column_name
        FROM user_ind_columns ic
        WHERE ic.table_name = 'PROFESSIONNELS'
        ORDER BY ic.index_name, ic.column_position
    """)
    indexes = cursor.fetchall()
    if indexes:
        for idx_name, col_name in indexes:
            print(f"   ✅ Index: {idx_name} sur {col_name}")
    else:
        print("   ❌ AUCUN INDEX TROUVÉ ! C'est probablement ça le problème !")

    # Test 2: Test MERGE avec 1 seule ligne
    print("\n2️⃣  TEST MERGE avec 1 ligne...")
    start = time.time()
    try:
        cursor.execute("""
            MERGE INTO professionnels tgt
            USING (SELECT :1 AS id_prof, :2 AS nom, :3 AS prenom, :4 AS nom_ex,
                          :5 AS code_prof, :6 AS lib_prof, :7 AS code_cat, :8 AS statut
                   FROM DUAL) src
            ON (tgt.id_professionnel = src.id_prof)
            WHEN MATCHED THEN
                UPDATE SET
                    nom = src.nom,
                    prenom = src.prenom,
                    nom_exercice = src.nom_ex,
                    code_profession = src.code_prof,
                    libelle_profession = src.lib_prof,
                    code_categorie_profession = src.code_cat,
                    statut_enregistrement = src.statut,
                    date_derniere_maj = SYSDATE
            WHEN NOT MATCHED THEN
                INSERT (id_professionnel, nom, prenom, nom_exercice,
                        code_profession, libelle_profession, code_categorie_profession,
                        statut_enregistrement, date_import)
                VALUES (src.id_prof, src.nom, src.prenom, src.nom_ex,
                        src.code_prof, src.lib_prof, src.code_cat,
                        src.statut, SYSDATE)
        """, ['TEST001', 'DUPONT', 'Jean', 'DUPONT', '10', 'Médecin', 'C', 'Actif'])
        conn.commit()
        elapsed = time.time() - start
        print(f"   ✅ MERGE 1 ligne : {elapsed*1000:.0f}ms")
        if elapsed > 1.0:
            print(f"   ⚠️  WARNING : Très lent ! Devrait être < 100ms")
    except Exception as e:
        print(f"   ❌ ERREUR : {e}")

    # Test 3: Test MERGE avec 10 lignes
    print("\n3️⃣  TEST MERGE avec 10 lignes...")
    start = time.time()
    try:
        data = [[f'TEST{i:03d}', f'NOM{i}', f'PRENOM{i}', f'NOM{i}', '10', 'Médecin', 'C', 'Actif']
                for i in range(10)]
        cursor.executemany("""
            MERGE INTO professionnels tgt
            USING (SELECT :1 AS id_prof, :2 AS nom, :3 AS prenom, :4 AS nom_ex,
                          :5 AS code_prof, :6 AS lib_prof, :7 AS code_cat, :8 AS statut
                   FROM DUAL) src
            ON (tgt.id_professionnel = src.id_prof)
            WHEN MATCHED THEN
                UPDATE SET
                    nom = src.nom,
                    prenom = src.prenom,
                    nom_exercice = src.nom_ex,
                    code_profession = src.code_prof,
                    libelle_profession = src.lib_prof,
                    code_categorie_profession = src.code_cat,
                    statut_enregistrement = src.statut,
                    date_derniere_maj = SYSDATE
            WHEN NOT MATCHED THEN
                INSERT (id_professionnel, nom, prenom, nom_exercice,
                        code_profession, libelle_profession, code_categorie_profession,
                        statut_enregistrement, date_import)
                VALUES (src.id_prof, src.nom, src.prenom, src.nom_ex,
                        src.code_prof, src.lib_prof, src.code_cat,
                        src.statut, SYSDATE)
        """, data)
        conn.commit()
        elapsed = time.time() - start
        print(f"   ✅ MERGE 10 lignes : {elapsed*1000:.0f}ms ({elapsed*100:.0f}ms/ligne)")
        if elapsed > 2.0:
            print(f"   ⚠️  WARNING : Très lent ! Devrait être < 500ms")
    except Exception as e:
        print(f"   ❌ ERREUR : {e}")

    # Test 4: Test MERGE avec 100 lignes
    print("\n4️⃣  TEST MERGE avec 100 lignes (timeout 30s)...")
    start = time.time()
    try:
        cursor.execute("SAVEPOINT test_100")
        data = [[f'TEST{i:04d}', f'NOM{i}', f'PRENOM{i}', f'NOM{i}', '10', 'Médecin', 'C', 'Actif']
                for i in range(100)]
        cursor.executemany("""
            MERGE INTO professionnels tgt
            USING (SELECT :1 AS id_prof, :2 AS nom, :3 AS prenom, :4 AS nom_ex,
                          :5 AS code_prof, :6 AS lib_prof, :7 AS code_cat, :8 AS statut
                   FROM DUAL) src
            ON (tgt.id_professionnel = src.id_prof)
            WHEN MATCHED THEN
                UPDATE SET nom = src.nom, prenom = src.prenom
            WHEN NOT MATCHED THEN
                INSERT (id_professionnel, nom, prenom, nom_exercice,
                        code_profession, libelle_profession, code_categorie_profession,
                        statut_enregistrement, date_import)
                VALUES (src.id_prof, src.nom, src.prenom, src.nom_ex,
                        src.code_prof, src.lib_prof, src.code_cat,
                        src.statut, SYSDATE)
        """, data)
        cursor.execute("ROLLBACK TO SAVEPOINT test_100")
        elapsed = time.time() - start
        print(f"   ✅ MERGE 100 lignes : {elapsed*1000:.0f}ms ({elapsed*10:.0f}ms/ligne)")
        if elapsed > 5.0:
            print(f"   ⚠️  WARNING : Très lent pour 100 lignes !")
    except Exception as e:
        print(f"   ❌ ERREUR ou TIMEOUT : {e}")

    # Test 5: Vérifier statistiques table
    print("\n5️⃣  STATISTIQUES DE LA TABLE professionnels...")
    cursor.execute("""
        SELECT num_rows, blocks, avg_row_len, last_analyzed
        FROM user_tables
        WHERE table_name = 'PROFESSIONNELS'
    """)
    row = cursor.fetchone()
    if row:
        num_rows, blocks, avg_row_len, last_analyzed = row
        print(f"   Lignes       : {num_rows if num_rows else 'Non calculé'}")
        print(f"   Blocks       : {blocks if blocks else 'Non calculé'}")
        print(f"   Avg row len  : {avg_row_len if avg_row_len else 'Non calculé'}")
        print(f"   Last analyzed: {last_analyzed if last_analyzed else 'Jamais'}")

        if not last_analyzed:
            print(f"   ⚠️  WARNING : Statistiques jamais calculées ! Exécutez:")
            print(f"      EXEC DBMS_STATS.GATHER_TABLE_STATS(USER, 'PROFESSIONNELS');")

    # Test 6: Tester INSERT simple
    print("\n6️⃣  TEST INSERT simple avec 100 lignes...")
    start = time.time()
    try:
        cursor.execute("SAVEPOINT test_insert")
        data = [[f'INSERT{i:04d}', f'NOM{i}', f'PRENOM{i}', f'NOM{i}', '10', 'Médecin', 'C', None, None, 'Actif']
                for i in range(100)]
        cursor.executemany("""
            INSERT INTO professionnels (
                id_professionnel, nom, prenom, nom_exercice,
                code_profession, libelle_profession, code_categorie_profession,
                code_savoir_faire, libelle_savoir_faire,
                statut_enregistrement, date_import
            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, SYSDATE)
        """, data)
        cursor.execute("ROLLBACK TO SAVEPOINT test_insert")
        elapsed = time.time() - start
        print(f"   ✅ INSERT 100 lignes : {elapsed*1000:.0f}ms ({elapsed*10:.0f}ms/ligne)")
    except Exception as e:
        print(f"   ❌ ERREUR : {e}")

    print("\n" + "="*70)
    print("RECOMMANDATIONS:")
    print("="*70)

    if not indexes:
        print("❗ CRITIQUE : Créez un index sur id_professionnel !")
        print("   CREATE INDEX idx_pros_id ON professionnels(id_professionnel);")

    print("\n💡 Si les MERGE sont lents (>500ms pour 100 lignes):")
    print("   Option 1: Réduire batch_size à 1000-2000")
    print("   Option 2: Utiliser INSERT au lieu de MERGE (première import)")
    print("   Option 3: Diviser le MERGE en chunks de 100-200 lignes")

    conn.close()

if __name__ == '__main__':
    test_merge_performance()
