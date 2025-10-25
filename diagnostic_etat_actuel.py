#!/usr/bin/env python3
"""
Diagnostic rapide de l'état actuel du projet
À exécuter AVANT toute optimisation
"""
import oracledb
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Connexion
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try:
        oracledb.init_oracle_client(lib_dir=oracle_home)
    except:
        pass

try:
    conn = oracledb.connect(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        dsn=os.getenv('DB_DSN'),
        config_dir=os.getenv('WALLET_PATH'),
        wallet_location=os.getenv('WALLET_PATH')
    )
    cursor = conn.cursor()
    
    print("="*70)
    print("📊 DIAGNOSTIC ÉTAT ACTUEL DU PROJET")
    print("="*70)
    
    # 1. Volumes de données
    print("\n1️⃣  VOLUMES DE DONNÉES ACTUELS")
    print("-"*70)
    
    tables = [
        ('professionnels', 'Professionnels'),
        ('structures', 'Structures'),
        ('activites', 'Activités'),
        ('adresses', 'Adresses'),
        ('contacts', 'Contacts')
    ]
    
    for table, label in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{label:20s} : {count:>12,}")
    
    # 2. Vérifier le problème des 47%
    print("\n2️⃣  VÉRIFICATION PROBLÈME 47% ACTIVITÉS")
    print("-"*70)
    
    cursor.execute("SELECT COUNT(*) FROM professionnels")
    nb_pros = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM professionnels WHERE statut_enregistrement = 'Actif'")
    nb_pros_actifs = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT id_professionnel) 
        FROM professionnels p
        WHERE NOT EXISTS (
            SELECT 1 FROM activites a 
            WHERE a.id_professionnel = p.id_professionnel
        )
    """)
    nb_pros_sans_act = cursor.fetchone()[0]
    
    pct_sans_act = (nb_pros_sans_act / nb_pros * 100) if nb_pros > 0 else 0
    
    print(f"Professionnels total        : {nb_pros:>12,}")
    print(f"  - Actifs                  : {nb_pros_actifs:>12,}")
    print(f"  - Sans activité           : {nb_pros_sans_act:>12,} ({pct_sans_act:.1f}%)")
    
    if pct_sans_act > 10:
        print("\n⚠️  PROBLÈME DÉTECTÉ : > 10% sans activité")
        print("   → Le bug des 47% n'est PAS corrigé")
    else:
        print("\n✅ PROBLÈME RÉSOLU : < 10% sans activité (normal)")
    
    # 3. Structures avec identifiants
    print("\n3️⃣  STRUCTURES ET IDENTIFIANTS")
    print("-"*70)
    
    cursor.execute("SELECT COUNT(*) FROM structures WHERE siret IS NOT NULL")
    nb_siret = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM structures WHERE finess IS NOT NULL")
    nb_finess = cursor.fetchone()[0]
    
    try:
        cursor.execute("SELECT COUNT(*) FROM structures WHERE identifiant_technique IS NOT NULL")
        nb_id_tech = cursor.fetchone()[0]
        col_exists = True
    except:
        nb_id_tech = 0
        col_exists = False
    
    cursor.execute("SELECT COUNT(*) FROM structures")
    nb_total_struct = cursor.fetchone()[0]
    
    print(f"Structures total            : {nb_total_struct:>12,}")
    print(f"  - Avec SIRET              : {nb_siret:>12,} ({nb_siret/nb_total_struct*100:.1f}%)")
    print(f"  - Avec FINESS             : {nb_finess:>12,} ({nb_finess/nb_total_struct*100:.1f}%)")
    if col_exists:
        print(f"  - Avec ID technique       : {nb_id_tech:>12,} ({nb_id_tech/nb_total_struct*100:.1f}%)")
        print(f"\n✅ Colonne identifiant_technique existe")
    else:
        print(f"\n⚠️  Colonne identifiant_technique MANQUANTE")
    
    # 4. Dernier import
    print("\n4️⃣  DERNIER IMPORT")
    print("-"*70)
    
    cursor.execute("""
        SELECT 
            TO_CHAR(date_debut, 'DD/MM/YYYY HH24:MI'),
            statut,
            nb_lignes_traitees,
            ROUND(duree_secondes/60, 1)
        FROM import_logs
        ORDER BY date_debut DESC
        FETCH FIRST 1 ROWS ONLY
    """)
    
    row = cursor.fetchone()
    if row:
        print(f"Date                        : {row[0]}")
        print(f"Statut                      : {row[1]}")
        print(f"Lignes traitées             : {row[2]:,}")
        print(f"Durée                       : {row[3]} minutes")
    else:
        print("Aucun import enregistré")
    
    # 5. Structure de fichiers
    print("\n5️⃣  FICHIERS DU PROJET")
    print("-"*70)
    
    project_root = Path("/mnt/project")
    if project_root.exists():
        print("✅ Projet monté dans /mnt/project")
        
        important_files = [
            'import_rpps.py',
            'main.py',
            'setup_database.py',
            'explorer_donnees.py',
            'migration_complete.py'
        ]
        
        for f in important_files:
            path = project_root / f
            if path.exists():
                size_kb = path.stat().st_size / 1024
                print(f"  ✅ {f:30s} ({size_kb:.1f} KB)")
            else:
                print(f"  ❌ {f:30s} (manquant)")
    
    # 6. Codes standardisés
    print("\n6️⃣  MIGRATION CODES STANDARDISÉS")
    print("-"*70)
    
    try:
        cursor.execute("SELECT COUNT(*) FROM ref_professions")
        nb_ref_prof = cursor.fetchone()[0]
        print(f"✅ Table ref_professions    : {nb_ref_prof} professions")
    except:
        print("❌ Table ref_professions n'existe pas")
    
    try:
        cursor.execute("SELECT COUNT(*) FROM ref_categories")
        nb_ref_cat = cursor.fetchone()[0]
        print(f"✅ Table ref_categories     : {nb_ref_cat} catégories")
    except:
        print("❌ Table ref_categories n'existe pas")
    
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM professionnels 
            WHERE code_categorie_profession IS NOT NULL
        """)
        nb_avec_code = cursor.fetchone()[0]
        pct_migre = (nb_avec_code / nb_pros * 100) if nb_pros > 0 else 0
        print(f"✅ Pros avec code_categorie : {nb_avec_code:,} ({pct_migre:.1f}%)")
    except:
        print("❌ Colonne code_categorie_profession n'existe pas")
    
    print("\n" + "="*70)
    print("📋 RECOMMANDATIONS")
    print("="*70)
    
    if pct_sans_act > 10:
        print("❗ PRIORITÉ 1 : Relancer import_rpps.py (bug 47% pas corrigé)")
    elif not col_exists:
        print("❗ PRIORITÉ 1 : Ajouter colonne identifiant_technique")
    else:
        print("✅ Données OK - Prêt pour optimisation")
    
    conn.close()

except Exception as e:
    print(f"\n❌ ERREUR : {e}")
    print("\n💡 Vérifiez :")
    print("   - Connexion Oracle (variables .env)")
    print("   - Wallet Oracle (WALLET_PATH)")
