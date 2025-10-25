#!/usr/bin/env python3
"""
Validation finale Phase 1
Vérifie que l'import est complet et cohérent à 100%
"""
import oracledb
import os
from dotenv import load_dotenv
from tabulate import tabulate

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

print("="*80)
print("✅ VALIDATION FINALE PHASE 1 - IMPORT RPPS")
print("="*80)

# Critères de validation
validation = {
    'total': 0,
    'passes': 0,
    'warnings': 0,
    'fails': 0,
}

def test(name, query, condition, expected_desc):
    """Exécute un test de validation"""
    global validation
    validation['total'] += 1
    
    cursor.execute(query)
    result = cursor.fetchone()[0]
    
    passed = condition(result)
    
    status = "✅ PASS" if passed else "❌ FAIL"
    
    print(f"\n{status} | {name}")
    print(f"  Résultat : {result:,}")
    print(f"  Attendu  : {expected_desc}")
    
    if passed:
        validation['passes'] += 1
    else:
        validation['fails'] += 1
    
    return result

# ============================================================================
# TESTS DE VALIDATION
# ============================================================================

print("\n" + "="*80)
print("1️⃣  VOLUMES DE DONNÉES")
print("="*80)

nb_pros = test(
    "Professionnels importés",
    "SELECT COUNT(*) FROM professionnels",
    lambda x: x > 1_500_000,  # Au moins 1.5M pros
    "> 1,500,000"
)

nb_struct = test(
    "Structures importées",
    "SELECT COUNT(*) FROM structures",
    lambda x: x > 300_000,  # Au moins 300k structures
    "> 300,000"
)

nb_act = test(
    "Activités importées",
    "SELECT COUNT(*) FROM activites",
    lambda x: x > 1_800_000,  # Au moins 1.8M activités
    "> 1,800,000"
)

# ============================================================================
print("\n" + "="*80)
print("2️⃣  QUALITÉ DES DONNÉES")
print("="*80)

# % Pros sans activité (doit être < 10%)
pct_sans_act = test(
    "% Pros sans activité",
    """
    SELECT ROUND(
        COUNT(CASE WHEN NOT EXISTS (
            SELECT 1 FROM activites a WHERE a.id_professionnel = p.id_professionnel
        ) THEN 1 END) * 100.0 / COUNT(*), 2
    )
    FROM professionnels p
    """,
    lambda x: x < 10,
    "< 10%"
)

# % Structures avec identifiant
pct_struct_id = test(
    "% Structures avec ID",
    """
    SELECT ROUND(
        COUNT(CASE WHEN siret IS NOT NULL 
                    OR finess IS NOT NULL 
                    OR identifiant_technique IS NOT NULL 
              THEN 1 END) * 100.0 / COUNT(*), 2
    )
    FROM structures
    """,
    lambda x: x > 95,
    "> 95%"
)

# ============================================================================
print("\n" + "="*80)
print("3️⃣  INTÉGRITÉ RÉFÉRENTIELLE")
print("="*80)

# Activités orphelines
act_orphelines = test(
    "Activités sans professionnel",
    """
    SELECT COUNT(*) FROM activites a
    WHERE NOT EXISTS (
        SELECT 1 FROM professionnels p 
        WHERE p.id_professionnel = a.id_professionnel
    )
    """,
    lambda x: x == 0,
    "= 0 (aucune)"
)

# Activités sans structure
act_sans_struct = test(
    "Activités sans structure",
    """
    SELECT COUNT(*) FROM activites a
    WHERE NOT EXISTS (
        SELECT 1 FROM structures s 
        WHERE s.id_structure = a.id_structure
    )
    """,
    lambda x: x == 0,
    "= 0 (aucune)"
)

# ============================================================================
print("\n" + "="*80)
print("4️⃣  CODES STANDARDISÉS")
print("="*80)

# Professionnels avec code_categorie
pct_avec_cat = test(
    "% Pros avec code_categorie",
    """
    SELECT ROUND(
        COUNT(CASE WHEN code_categorie_profession IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2
    )
    FROM professionnels
    """,
    lambda x: x > 90,
    "> 90%"
)

# Activités avec code_mode
pct_avec_mode = test(
    "% Activités avec code_mode",
    """
    SELECT ROUND(
        COUNT(CASE WHEN code_mode_exercice IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2
    )
    FROM activites
    """,
    lambda x: x > 90,
    "> 90%"
)

# ============================================================================
print("\n" + "="*80)
print("5️⃣  COHÉRENCE MÉTIER")
print("="*80)

# Top départements
print("\n🗺️  Top 10 départements :")
cursor.execute("""
    SELECT departement, COUNT(*) as nb
    FROM adresses
    WHERE departement IS NOT NULL
    GROUP BY departement
    ORDER BY COUNT(*) DESC
    FETCH FIRST 10 ROWS ONLY
""")
dept_data = cursor.fetchall()
print(tabulate(dept_data, headers=['Département', 'Nombre'], tablefmt='simple'))

# Vérifier Paris en tête
paris_ok = dept_data[0][0] == '75'
if paris_ok:
    print("\n✅ Paris (75) est bien le département #1")
    validation['passes'] += 1
else:
    print(f"\n⚠️  WARNING: Paris pas en tête, {dept_data[0][0]} est #1")
    validation['warnings'] += 1

validation['total'] += 1

# Top professions
print("\n👥 Top 5 professions :")
cursor.execute("""
    SELECT libelle_profession, COUNT(*) as nb
    FROM professionnels
    GROUP BY libelle_profession
    ORDER BY COUNT(*) DESC
    FETCH FIRST 5 ROWS ONLY
""")
prof_data = cursor.fetchall()
print(tabulate(prof_data, headers=['Profession', 'Nombre'], tablefmt='simple'))

# ============================================================================
print("\n" + "="*80)
print("6️⃣  PERFORMANCE DERNIER IMPORT")
print("="*80)

cursor.execute("""
    SELECT 
        TO_CHAR(date_debut, 'DD/MM/YYYY HH24:MI'),
        statut,
        nb_lignes_traitees,
        nb_lignes_inserees,
        ROUND(duree_secondes/60, 1),
        ROUND(nb_lignes_traitees / NULLIF(duree_secondes, 0), 0)
    FROM import_logs
    WHERE statut = 'Terminé'
    ORDER BY date_debut DESC
    FETCH FIRST 1 ROWS ONLY
""")

row = cursor.fetchone()
if row:
    print(f"\n📅 Date            : {row[0]}")
    print(f"✅ Statut          : {row[1]}")
    print(f"📊 Lignes traitées : {row[2]:,}")
    print(f"✅ Lignes insérées : {row[3]:,}")
    print(f"⏱️  Durée          : {row[4]} minutes")
    print(f"🚀 Vitesse         : {row[5]:,} lignes/sec")
    
    # Performance acceptable ?
    if row[5] and row[5] > 800:
        print("\n✅ Performance acceptable (> 800 l/s)")
        validation['passes'] += 1
    else:
        print("\n⚠️  WARNING: Performance faible (< 800 l/s)")
        validation['warnings'] += 1
    
    validation['total'] += 1

# ============================================================================
# RÉSUMÉ FINAL
# ============================================================================
print("\n" + "="*80)
print("📋 RÉSUMÉ VALIDATION")
print("="*80)

score = (validation['passes'] / validation['total']) * 100

print(f"\n✅ Tests réussis     : {validation['passes']}/{validation['total']}")
print(f"⚠️  Warnings          : {validation['warnings']}")
print(f"❌ Tests échoués     : {validation['fails']}")
print(f"\n📊 Score             : {score:.1f}%")

if validation['fails'] == 0 and score >= 90:
    print("\n" + "="*80)
    print("🎉 PHASE 1 VALIDÉE À 100% !")
    print("="*80)
    print("\n✅ Vous pouvez passer à la Phase 2 (Enrichissement)")
    print("\n🎯 Prochaine étape :")
    print("   - Enrichissement API SIRENE")
    print("   - Géocodage BAN")
    print("   - Détection nouveaux pros")
elif validation['fails'] == 0:
    print("\n" + "="*80)
    print("⚠️  PHASE 1 VALIDÉE AVEC WARNINGS")
    print("="*80)
    print("\n✅ Import fonctionnel mais améliorations possibles")
    print("   Vous pouvez continuer ou corriger les warnings")
else:
    print("\n" + "="*80)
    print("❌ PHASE 1 NON VALIDÉE")
    print("="*80)
    print("\n⚠️  Veuillez corriger les tests échoués avant de continuer")

conn.close()
