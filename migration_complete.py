#!/usr/bin/env python3
"""
Migration vers codes standardisés - Exécution correcte
"""
import oracledb
import os
from dotenv import load_dotenv

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

print("="*60)
print("MIGRATION VERS CODES STANDARDISÉS")
print("="*60)

# ÉTAPE 1 : Ajouter les colonnes
print("\n[1/6] Ajout des colonnes...")
try:
    cursor.execute("""
        ALTER TABLE professionnels ADD (
            code_categorie_profession VARCHAR2(2)
        )
    """)
    print("  ✓ code_categorie_profession ajoutée")
except Exception as e:
    if "ORA-01430" in str(e):
        print("  - code_categorie_profession existe déjà")
    else:
        print(f"  ✗ {e}")

try:
    cursor.execute("""
        ALTER TABLE activites ADD (
            code_mode_exercice VARCHAR2(1)
        )
    """)
    print("  ✓ code_mode_exercice ajoutée")
except Exception as e:
    if "ORA-01430" in str(e):
        print("  - code_mode_exercice existe déjà")
    else:
        print(f"  ✗ {e}")

conn.commit()

# ÉTAPE 2 : Créer table ref_professions
print("\n[2/6] Création table ref_professions...")
try:
    cursor.execute("DROP TABLE ref_professions CASCADE CONSTRAINTS")
except:
    pass

cursor.execute("""
    CREATE TABLE ref_professions (
        code_profession VARCHAR2(10) PRIMARY KEY,
        libelle_profession VARCHAR2(200) NOT NULL,
        code_categorie VARCHAR2(2) NOT NULL,
        ordre_affichage NUMBER,
        actif CHAR(1) DEFAULT 'O'
    )
""")
print("  ✓ Table créée")

# Insérer les professions
professions = [
    # Médecins
    ('10', 'Médecin', 'C', 1),
    ('40', 'Chirurgien-Dentiste', 'C', 2),
    ('50', 'Sage-Femme', 'C', 3),
    # Pharmaciens
    ('21', 'Pharmacien', 'D', 10),
    # Paramédicaux
    ('60', 'Infirmier', 'S', 20),
    ('70', 'Masseur-Kinésithérapeute', 'S', 21),
    ('80', 'Pédicure-Podologue', 'S', 22),
    ('81', 'Ergothérapeute', 'S', 23),
    ('82', 'Psychomotricien', 'S', 24),
    ('83', 'Manipulateur ERM', 'S', 25),
    ('84', 'Technicien de Laboratoire Médical', 'S', 26),
    ('85', 'Audioprothésiste', 'S', 27),
    ('86', 'Opticien-Lunetier', 'S', 28),
    ('91', 'Orthophoniste', 'S', 29),
    ('92', 'Orthoptiste', 'S', 30),
    ('93', 'Diététicien', 'S', 31),
    ('94', 'Psychologue', 'S', 32),
    ('95', 'Ostéopathe', 'S', 33),
    ('96', 'Chiropracteur', 'S', 34),
]

cursor.executemany("""
    INSERT INTO ref_professions 
    (code_profession, libelle_profession, code_categorie, ordre_affichage)
    VALUES (:1, :2, :3, :4)
""", professions)
print(f"  ✓ {len(professions)} professions insérées")

conn.commit()

# ÉTAPE 3 : Créer table ref_categories
print("\n[3/6] Création table ref_categories...")
try:
    cursor.execute("DROP TABLE ref_categories CASCADE CONSTRAINTS")
except:
    pass

cursor.execute("""
    CREATE TABLE ref_categories (
        code_categorie VARCHAR2(2) PRIMARY KEY,
        libelle_categorie VARCHAR2(50) NOT NULL,
        description VARCHAR2(200)
    )
""")

categories = [
    ('C', 'Profession Médicale', 'Médecins, chirurgiens-dentistes, sages-femmes'),
    ('D', 'Profession Pharmaceutique', 'Pharmaciens'),
    ('S', 'Auxiliaire Médical', 'Paramédicaux : infirmiers, kinés, etc.'),
    ('M', 'Autres Professions de Santé', 'Techniciens, assistants sociaux, etc.'),
]

cursor.executemany("""
    INSERT INTO ref_categories VALUES (:1, :2, :3)
""", categories)
print(f"  ✓ {len(categories)} catégories insérées")

conn.commit()

# ÉTAPE 4 : Créer table ref_modes_exercice
print("\n[4/6] Création table ref_modes_exercice...")
try:
    cursor.execute("DROP TABLE ref_modes_exercice CASCADE CONSTRAINTS")
except:
    pass

cursor.execute("""
    CREATE TABLE ref_modes_exercice (
        code_mode VARCHAR2(1) PRIMARY KEY,
        libelle_mode VARCHAR2(50) NOT NULL,
        description VARCHAR2(200)
    )
""")

modes = [
    ('L', 'Libéral', 'Exercice en cabinet libéral, indépendant ou commercial'),
    ('S', 'Salarié', 'Exercice salarié en établissement de santé'),
    ('B', 'Bénévole', 'Exercice bénévole'),
    ('M', 'Mixte', 'Exercice mixte (libéral + salarié)'),
]

cursor.executemany("""
    INSERT INTO ref_modes_exercice VALUES (:1, :2, :3)
""", modes)
print(f"  ✓ {len(modes)} modes insérés")

conn.commit()

# ÉTAPE 5 : Mettre à jour code_categorie_profession
print("\n[5/6] Mise à jour code_categorie_profession...")
cursor.execute("""
    UPDATE professionnels p
    SET code_categorie_profession = (
        SELECT code_categorie 
        FROM ref_professions r 
        WHERE r.code_profession = p.code_profession
    )
    WHERE EXISTS (
        SELECT 1 FROM ref_professions r 
        WHERE r.code_profession = p.code_profession
    )
""")
print(f"  ✓ {cursor.rowcount:,} professionnels mis à jour")

conn.commit()

# ÉTAPE 6 : Mettre à jour code_mode_exercice
print("\n[6/6] Mise à jour code_mode_exercice...")
cursor.execute("""
    UPDATE activites
    SET code_mode_exercice = CASE
        WHEN UPPER(mode_exercice) LIKE '%LIB%' 
          OR UPPER(mode_exercice) LIKE '%INDEP%' 
          OR UPPER(mode_exercice) LIKE '%ARTIS%'
          OR UPPER(mode_exercice) LIKE '%COM%' THEN 'L'
        WHEN UPPER(mode_exercice) LIKE '%SALAR%' THEN 'S'
        WHEN UPPER(mode_exercice) LIKE '%BENEV%' THEN 'B'
        WHEN UPPER(mode_exercice) LIKE '%MIXTE%' THEN 'M'
        ELSE NULL
    END
""")
print(f"  ✓ {cursor.rowcount:,} activités mises à jour")

conn.commit()

# ÉTAPE 7 : Extraire départements depuis codes postaux
print("\n[BONUS] Extraction départements depuis codes postaux...")
cursor.execute("""
    UPDATE adresses
    SET departement = CASE
        WHEN LENGTH(code_postal) = 5 THEN SUBSTR(code_postal, 1, 2)
        WHEN LENGTH(code_postal) = 4 THEN '0' || SUBSTR(code_postal, 1, 1)
        ELSE NULL
    END
    WHERE departement IS NULL AND code_postal IS NOT NULL
""")
nb_dept = cursor.rowcount
conn.commit()  # COMMIT entre les updates

# Cas spéciaux Corse
cursor.execute("""
    UPDATE adresses
    SET departement = CASE
        WHEN SUBSTR(code_postal, 1, 3) IN ('200', '201') THEN '2A'
        WHEN SUBSTR(code_postal, 1, 3) IN ('202', '206') THEN '2B'
        ELSE departement
    END
    WHERE SUBSTR(code_postal, 1, 2) = '20'
""")
conn.commit()  # COMMIT entre les updates

# DOM-TOM
cursor.execute("""
    UPDATE adresses
    SET departement = SUBSTR(code_postal, 1, 3)
    WHERE SUBSTR(code_postal, 1, 2) IN ('97', '98')
    AND LENGTH(code_postal) >= 3
""")
conn.commit()  # COMMIT final

print(f"  ✓ {nb_dept:,} départements extraits")

# STATISTIQUES
print("\n" + "="*60)
print("STATISTIQUES APRÈS MIGRATION")
print("="*60)

print("\n📊 Catégories (avec codes) :")
cursor.execute("""
    SELECT 
        c.libelle_categorie,
        COUNT(*) as nb,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM professionnels), 2) as pct
    FROM professionnels p
    JOIN ref_categories c ON p.code_categorie_profession = c.code_categorie
    GROUP BY c.libelle_categorie
    ORDER BY COUNT(*) DESC
""")
for cat, nb, pct in cursor.fetchall():
    print(f"  {cat:30s} : {nb:>10,} ({pct:>5.2f}%)")

print("\n💼 Modes d'exercice (avec codes) :")
cursor.execute("""
    SELECT 
        m.libelle_mode,
        COUNT(*) as nb,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM activites), 2) as pct
    FROM activites a
    JOIN ref_modes_exercice m ON a.code_mode_exercice = m.code_mode
    GROUP BY m.libelle_mode
    ORDER BY COUNT(*) DESC
""")
for mode, nb, pct in cursor.fetchall():
    print(f"  {mode:30s} : {nb:>10,} ({pct:>5.2f}%)")

print("\n🏥 Top 10 Professions (avec codes) :")
cursor.execute("""
    SELECT 
        r.libelle_profession,
        COUNT(*) as nb
    FROM professionnels p
    JOIN ref_professions r ON p.code_profession = r.code_profession
    GROUP BY r.libelle_profession
    ORDER BY COUNT(*) DESC
    FETCH FIRST 10 ROWS ONLY
""")
for prof, nb in cursor.fetchall():
    print(f"  {prof:40s} : {nb:>10,}")

print("\n📍 Top 10 Départements :")
cursor.execute("""
    SELECT 
        departement,
        COUNT(*) as nb
    FROM adresses
    WHERE departement IS NOT NULL
    GROUP BY departement
    ORDER BY COUNT(*) DESC
    FETCH FIRST 10 ROWS ONLY
""")
for dept, nb in cursor.fetchall():
    print(f"  {dept:10s} : {nb:>10,}")

print("\n" + "="*60)
print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
print("="*60)

conn.close()
