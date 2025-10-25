#!/usr/bin/env python3
"""
Exploration et validation des données RPPS importées
"""
import oracledb
import os
from dotenv import load_dotenv
from tabulate import tabulate

load_dotenv()

# Initialiser le client Oracle
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try:
        oracledb.init_oracle_client(lib_dir=oracle_home)
    except:
        pass

# Connexion
conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)

cursor = conn.cursor()

print("="*80)
print("📊 EXPLORATION DES DONNÉES RPPS IMPORTÉES")
print("="*80)

# 1. STATISTIQUES GÉNÉRALES
print("\n" + "="*80)
print("1. STATISTIQUES GÉNÉRALES")
print("="*80)

cursor.execute("SELECT COUNT(*) FROM professionnels")
nb_pros = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM structures")
nb_struct = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM activites")
nb_act = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM adresses")
nb_adr = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM contacts")
nb_contacts = cursor.fetchone()[0]

print(f"""
👤 Professionnels   : {nb_pros:>12,}
🏢 Structures       : {nb_struct:>12,}
📍 Activités        : {nb_act:>12,}
🏠 Adresses         : {nb_adr:>12,}
📞 Contacts         : {nb_contacts:>12,}
""")

# 2. TOP 10 PROFESSIONS
print("="*80)
print("2. TOP 10 PROFESSIONS LES PLUS REPRÉSENTÉES")
print("="*80)

cursor.execute("""
    SELECT 
        libelle_profession,
        COUNT(*) as nb,
        ROUND(COUNT(*) * 100.0 / :1, 2) as pct
    FROM professionnels
    GROUP BY libelle_profession
    ORDER BY COUNT(*) DESC
    FETCH FIRST 10 ROWS ONLY
""", [nb_pros])

data = cursor.fetchall()
print(tabulate(data, headers=['Profession', 'Nombre', '%'], 
               tablefmt='grid', floatfmt='.2f', intfmt=','))

# 3. RÉPARTITION PAR CATÉGORIE (AVEC CODES)
print("\n" + "="*80)
print("3. RÉPARTITION PAR CATÉGORIE PROFESSIONNELLE (CODES STANDARDISÉS)")
print("="*80)

cursor.execute("""
    SELECT 
        c.libelle_categorie,
        COUNT(*) as nb,
        ROUND(COUNT(*) * 100.0 / :1, 2) as pct
    FROM professionnels p
    JOIN ref_categories c ON p.code_categorie_profession = c.code_categorie
    GROUP BY c.libelle_categorie
    ORDER BY COUNT(*) DESC
""", [nb_pros])

data = cursor.fetchall()
print(tabulate(data, headers=['Catégorie', 'Nombre', '%'], 
               tablefmt='grid', floatfmt='.2f', intfmt=','))

# 4. TOP 10 DÉPARTEMENTS
print("\n" + "="*80)
print("4. TOP 10 DÉPARTEMENTS (par nombre de professionnels)")
print("="*80)

cursor.execute("""
    SELECT 
        departement,
        COUNT(DISTINCT a.id_professionnel) as nb_pros,
        COUNT(*) as nb_adresses
    FROM adresses a
    WHERE departement IS NOT NULL
    GROUP BY departement
    ORDER BY COUNT(DISTINCT a.id_professionnel) DESC
    FETCH FIRST 10 ROWS ONLY
""")

data = cursor.fetchall()
# Nettoyer les None
data = [[str(v) if v is not None else '' for v in row] for row in data]
print(tabulate(data, headers=['Département', 'Professionnels', 'Adresses'], 
               tablefmt='grid'))

# 5. MODE D'EXERCICE (AVEC CODES)
print("\n" + "="*80)
print("5. RÉPARTITION PAR MODE D'EXERCICE (CODES STANDARDISÉS)")
print("="*80)

cursor.execute("""
    SELECT 
        m.libelle_mode,
        COUNT(*) as nb,
        ROUND(COUNT(*) * 100.0 / :1, 2) as pct
    FROM activites a
    JOIN ref_modes_exercice m ON a.code_mode_exercice = m.code_mode
    GROUP BY m.libelle_mode
    ORDER BY COUNT(*) DESC
""", [nb_act])

data = cursor.fetchall()
print(tabulate(data, headers=['Mode Exercice', 'Nombre', '%'], 
               tablefmt='grid', floatfmt='.2f', intfmt=','))

# 6. ÉCHANTILLON DE DONNÉES
print("\n" + "="*80)
print("6. ÉCHANTILLON : 10 PROFESSIONNELS ALÉATOIRES AVEC LEURS INFOS")
print("="*80)

cursor.execute("""
    SELECT 
        p.id_professionnel,
        p.nom,
        p.prenom,
        p.libelle_profession,
        a.mode_exercice,
        ad.code_postal,
        ad.commune
    FROM professionnels p
    LEFT JOIN activites a ON p.id_professionnel = a.id_professionnel
    LEFT JOIN adresses ad ON p.id_professionnel = ad.id_professionnel
    WHERE ROWNUM <= 10
    ORDER BY DBMS_RANDOM.VALUE
""")

data = cursor.fetchall()
print(tabulate(data, 
               headers=['ID', 'Nom', 'Prénom', 'Profession', 'Mode Ex', 'CP', 'Commune'],
               tablefmt='grid', maxcolwidths=[11, 15, 15, 25, 20, 5, 20]))

# 7. QUALITÉ DES DONNÉES
print("\n" + "="*80)
print("7. QUALITÉ DES DONNÉES")
print("="*80)

# Professionnels sans activité
cursor.execute("""
    SELECT COUNT(*) 
    FROM professionnels p
    WHERE NOT EXISTS (SELECT 1 FROM activites WHERE id_professionnel = p.id_professionnel)
""")
nb_sans_act = cursor.fetchone()[0]

# Professionnels sans adresse
cursor.execute("""
    SELECT COUNT(*) 
    FROM professionnels p
    WHERE NOT EXISTS (SELECT 1 FROM adresses WHERE id_professionnel = p.id_professionnel)
""")
nb_sans_adr = cursor.fetchone()[0]

# Structures sans SIRET ni FINESS
cursor.execute("""
    SELECT COUNT(*) 
    FROM structures
    WHERE siret IS NULL AND finess IS NULL
""")
nb_struct_sans_id = cursor.fetchone()[0]

# Adresses sans code postal
cursor.execute("""
    SELECT COUNT(*) 
    FROM adresses
    WHERE code_postal IS NULL
""")
nb_adr_sans_cp = cursor.fetchone()[0]

print(f"""
⚠️  Professionnels sans activité        : {nb_sans_act:>12,} ({nb_sans_act*100/nb_pros:>5.2f}%)
⚠️  Professionnels sans adresse         : {nb_sans_adr:>12,} ({nb_sans_adr*100/nb_pros:>5.2f}%)
⚠️  Structures sans identifiant         : {nb_struct_sans_id:>12,} ({nb_struct_sans_id*100/nb_struct:>5.2f}%)
⚠️  Adresses sans code postal           : {nb_adr_sans_cp:>12,} ({nb_adr_sans_cp*100/nb_adr:>5.2f}%)
""")

# 8. LOGS D'IMPORT
print("="*80)
print("8. HISTORIQUE DES IMPORTS")
print("="*80)

cursor.execute("""
    SELECT 
        id_log,
        script_execute,
        TO_CHAR(date_debut, 'DD/MM/YYYY HH24:MI') as date_debut,
        statut,
        nb_lignes_traitees,
        nb_lignes_inserees,
        ROUND(duree_secondes/60, 1) as duree_min
    FROM import_logs
    ORDER BY date_debut DESC
    FETCH FIRST 5 ROWS ONLY
""")

data = cursor.fetchall()
print(tabulate(data, 
               headers=['ID', 'Fichier', 'Date', 'Statut', 'Traitées', 'Insérées', 'Durée (min)'],
               tablefmt='grid', intfmt=','))

# 9. REQUÊTES MÉTIER UTILES
print("\n" + "="*80)
print("9. EXEMPLES DE REQUÊTES MÉTIER")
print("="*80)

print("\n📍 Médecins généralistes en Île-de-France (75, 92, 93, 94, 95) :")
cursor.execute("""
    SELECT COUNT(DISTINCT p.id_professionnel)
    FROM professionnels p
    JOIN activites a ON p.id_professionnel = a.id_professionnel
    JOIN adresses ad ON p.id_professionnel = ad.id_professionnel
    WHERE UPPER(p.libelle_profession) LIKE '%MEDECIN GENERALISTE%'
    AND ad.departement IN ('75', '92', '93', '94', '95')
""")
print(f"   → {cursor.fetchone()[0]:,} médecins généralistes")

print("\n🏢 Professionnels en exercice libéral :")
cursor.execute("""
    SELECT COUNT(DISTINCT id_professionnel)
    FROM activites
    WHERE UPPER(mode_exercice) LIKE '%LIB%'
    OR UPPER(mode_exercice) LIKE '%INDEP%'
""")
print(f"   → {cursor.fetchone()[0]:,} professionnels")

print("\n💊 Pharmaciens d'officine :")
cursor.execute("""
    SELECT COUNT(*)
    FROM professionnels
    WHERE UPPER(libelle_profession) LIKE '%PHARMACIEN%'
    AND categorie_profession = 'Pharmacien'
""")
print(f"   → {cursor.fetchone()[0]:,} pharmaciens")

print("\n" + "="*80)
print("✅ EXPLORATION TERMINÉE")
print("="*80)

conn.close()

print("\n💡 Conseils :")
print("   - Les données semblent cohérentes si < 5% de pros sans activité/adresse")
print("   - Vérifie les départements : Paris (75) devrait être dans le top 3")
print("   - La catégorie 'Médecin' devrait être ~30-40% du total")
print("\n🎯 Prochaine étape : Enrichissement des données (API, géocodage, contacts)")
