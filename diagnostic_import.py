#!/usr/bin/env python3
"""
Diagnostic des problèmes d'import RPPS
Vérifie la cohérence des données et identifie les pertes
"""
import oracledb
import os
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

# Configuration Oracle
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try:
        oracledb.init_oracle_client(lib_dir=oracle_home)
    except:
        pass

# Connexion
print("🔌 Connexion à Oracle...")
conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)
cursor = conn.cursor()
print("✓ Connecté\n")

print("="*80)
print("🔍 DIAGNOSTIC DE L'IMPORT RPPS")
print("="*80)

# 1. STATISTIQUES GÉNÉRALES
print("\n📊 1. STATISTIQUES ACTUELLES")
print("-"*40)

cursor.execute("SELECT COUNT(*) FROM professionnels")
nb_pros = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM professionnels WHERE statut_enregistrement = 'Actif'")
nb_pros_actifs = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM professionnels WHERE statut_enregistrement = 'Inactif'")
nb_pros_inactifs = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM structures")
nb_structures = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM activites")
nb_activites = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM adresses")
nb_adresses = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM contacts")
nb_contacts = cursor.fetchone()[0]

print(f"Professionnels total    : {nb_pros:>10,}")
print(f"  - Actifs             : {nb_pros_actifs:>10,} ({nb_pros_actifs*100/nb_pros:.1f}%)")
print(f"  - Inactifs           : {nb_pros_inactifs:>10,} ({nb_pros_inactifs*100/nb_pros:.1f}%)")
print(f"Structures             : {nb_structures:>10,}")
print(f"Activités              : {nb_activites:>10,}")
print(f"Adresses               : {nb_adresses:>10,}")
print(f"Contacts               : {nb_contacts:>10,}")

# 2. ANALYSE DES RATIOS
print("\n📈 2. ANALYSE DES RATIOS")
print("-"*40)

ratio_act_pros = nb_activites / nb_pros if nb_pros > 0 else 0
ratio_adr_pros = nb_adresses / nb_pros if nb_pros > 0 else 0
ratio_struct_pros = nb_structures / nb_pros if nb_pros > 0 else 0

print(f"Activités/Professionnel : {ratio_act_pros:.2f}")
print(f"Adresses/Professionnel  : {ratio_adr_pros:.2f}")
print(f"Structures/Professionnel: {ratio_struct_pros:.2f}")

if ratio_act_pros < 0.8:
    print("⚠️  ALERTE: Ratio activités/pro trop faible! Perte de données probable.")

# 3. PROFESSIONNELS SANS ACTIVITÉ
print("\n⚠️  3. ANOMALIES DÉTECTÉES")
print("-"*40)

cursor.execute("""
    SELECT COUNT(*)
    FROM professionnels p
    WHERE statut_enregistrement = 'Actif'
    AND NOT EXISTS (SELECT 1 FROM activites WHERE id_professionnel = p.id_professionnel)
""")
pros_actifs_sans_activite = cursor.fetchone()[0]

print(f"Professionnels ACTIFS sans activité : {pros_actifs_sans_activite:>8,}")
if pros_actifs_sans_activite > 0:
    pct_sans_act = (pros_actifs_sans_activite / nb_pros_actifs) * 100
    print(f"  → {pct_sans_act:.1f}% des actifs n'ont pas d'activité!")
    if pct_sans_act > 5:
        print("  🔴 CRITIQUE: Plus de 5% des pros actifs sans activité!")

# 4. STRUCTURES ORPHELINES
cursor.execute("""
    SELECT COUNT(*)
    FROM structures s
    WHERE NOT EXISTS (SELECT 1 FROM activites WHERE id_structure = s.id_structure)
""")
structures_orphelines = cursor.fetchone()[0]

print(f"Structures sans activité : {structures_orphelines:>8,}")
if structures_orphelines > 100:
    print("  ⚠️  Beaucoup de structures orphelines")

# 5. ANALYSE DES IDENTIFIANTS STRUCTURES
print("\n🔑 4. ANALYSE DES IDENTIFIANTS STRUCTURES")
print("-"*40)

cursor.execute("""
    SELECT 
        CASE 
            WHEN siret IS NOT NULL AND finess IS NULL AND identifiant_technique IS NULL THEN 'SIRET seul'
            WHEN siret IS NULL AND finess IS NOT NULL AND identifiant_technique IS NULL THEN 'FINESS seul'
            WHEN siret IS NULL AND finess IS NULL AND identifiant_technique IS NOT NULL THEN 'ID_TECH seul'
            WHEN siret IS NOT NULL AND finess IS NOT NULL AND identifiant_technique IS NULL THEN 'SIRET + FINESS'
            WHEN siret IS NOT NULL AND identifiant_technique IS NOT NULL THEN 'SIRET + ID_TECH'
            WHEN finess IS NOT NULL AND identifiant_technique IS NOT NULL THEN 'FINESS + ID_TECH'
            WHEN siret IS NOT NULL AND finess IS NOT NULL AND identifiant_technique IS NOT NULL THEN 'TOUS'
            ELSE 'AUCUN'
        END as type_identifiant,
        COUNT(*) as nombre
    FROM structures
    GROUP BY CASE 
        WHEN siret IS NOT NULL AND finess IS NULL AND identifiant_technique IS NULL THEN 'SIRET seul'
        WHEN siret IS NULL AND finess IS NOT NULL AND identifiant_technique IS NULL THEN 'FINESS seul'
        WHEN siret IS NULL AND finess IS NULL AND identifiant_technique IS NOT NULL THEN 'ID_TECH seul'
        WHEN siret IS NOT NULL AND finess IS NOT NULL AND identifiant_technique IS NULL THEN 'SIRET + FINESS'
        WHEN siret IS NOT NULL AND identifiant_technique IS NOT NULL THEN 'SIRET + ID_TECH'
        WHEN finess IS NOT NULL AND identifiant_technique IS NOT NULL THEN 'FINESS + ID_TECH'
        WHEN siret IS NOT NULL AND finess IS NOT NULL AND identifiant_technique IS NOT NULL THEN 'TOUS'
        ELSE 'AUCUN'
    END
    ORDER BY nombre DESC
""")

identifiants_data = cursor.fetchall()
print(tabulate(identifiants_data, headers=['Type Identifiant', 'Nombre'], tablefmt='grid'))

# 6. VÉRIFICATION DES ID_TECH
cursor.execute("""
    SELECT COUNT(*)
    FROM structures
    WHERE identifiant_technique IS NOT NULL
""")
nb_avec_id_tech = cursor.fetchone()[0]

print(f"\nStructures avec identifiant_technique : {nb_avec_id_tech:>8,} ({nb_avec_id_tech*100/nb_structures:.1f}%)")

# 7. ANALYSE DES BATCHES (depuis les logs)
print("\n📦 5. ANALYSE DES PERFORMANCES D'IMPORT")
print("-"*40)

cursor.execute("""
    SELECT 
        id_log,
        nb_lignes_traitees,
        nb_lignes_inserees,
        nb_erreurs,
        ROUND(duree_secondes/60, 1) as duree_min,
        ROUND(nb_lignes_traitees / NULLIF(duree_secondes, 0), 0) as lignes_par_sec,
        statut
    FROM import_logs
    WHERE nb_lignes_traitees IS NOT NULL
    ORDER BY id_log DESC
    FETCH FIRST 5 ROWS ONLY
""")

logs_data = cursor.fetchall()
if logs_data:
    print(tabulate(logs_data, 
                   headers=['ID', 'Lignes Traitées', 'Insérées', 'Erreurs', 'Durée(min)', 'L/sec', 'Statut'],
                   tablefmt='grid'))

# 8. ESTIMATION DU PROBLÈME
print("\n🎯 6. DIAGNOSTIC FINAL")
print("-"*40)

expected_activities = nb_pros_actifs * 1.15  # On s'attend à ~1.15 activités par pro actif
missing_activities = expected_activities - nb_activites

print(f"Activités attendues    : {expected_activities:>10,.0f}")
print(f"Activités réelles      : {nb_activites:>10,}")
print(f"Activités manquantes   : {missing_activities:>10,.0f}")

if missing_activities > 10000:
    print("\n🔴 DIAGNOSTIC: PERTE DE DONNÉES CONFIRMÉE")
    print(f"   Il manque environ {missing_activities:,.0f} activités")
    print("\n   Causes probables:")
    print("   1. Limite Oracle sur les paramètres bind dépassée")
    print("   2. ID Map incomplète lors du flush_buffers")
    print("   3. Structures sans identifiant_technique non mappées")
else:
    print("\n✅ Les données semblent cohérentes")

# 9. RECOMMANDATIONS
print("\n💡 7. RECOMMANDATIONS")
print("-"*40)
print("1. Diviser les batches de l'ID Map en chunks de 1000 max")
print("2. Utiliser une table temporaire pour l'ID mapping")
print("3. Logger les structures non trouvées dans l'ID Map")
print("4. Réduire le BATCH_SIZE à 5000 pour éviter les limites Oracle")
print("5. Implémenter un mode DEBUG pour tracer les pertes")

conn.close()
print("\n✅ Diagnostic terminé")
