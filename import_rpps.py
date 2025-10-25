#!/usr/bin/env python3
"""
Import RPPS - VERSION CORRIGÉE ET OPTIMISÉE (v5)
Corrections:
- Fix perte de données : ID Map divisée en chunks de 900 (limite Oracle 1000)
- Fix performance : Batch optimisé, moins de commits
- Fix traçabilité : Mode DEBUG et logging détaillé
- Fix robustesse : Gestion des structures sans ID
"""
import oracledb
import os
import sys
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

# --- CONFIGURATION ---
BATCH_SIZE = 5000  # Réduit pour éviter les limites Oracle
ID_MAP_CHUNK_SIZE = 900  # Limite sûre pour les requêtes IN Oracle
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
FICHIER_RPPS = "PS_LibreAcces_Personne_activite_202509230829.txt"
# ---------------------

# Configuration logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_rpps.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialiser Oracle
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try:
        oracledb.init_oracle_client(lib_dir=oracle_home)
    except: 
        pass

# Connexion
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_dsn = os.getenv("DB_DSN")
wallet_path = os.getenv("WALLET_PATH")

if not all([db_user, db_password, db_dsn, wallet_path]):
    logger.error("Variables .env manquantes (DB_USER, DB_PASSWORD, DB_DSN, WALLET_PATH)")
    sys.exit(1)

file_path = Path(FICHIER_RPPS)
if not file_path.exists():
    logger.error(f"Fichier source non trouvé : {FICHIER_RPPS}")
    sys.exit(1)

file_size = file_path.stat().st_size / (1024*1024*1024)
logger.info(f"📄 Fichier source : {FICHIER_RPPS} ({file_size:.2f} Go)")

logger.info("🔌 Connexion à Oracle...")
try:
    conn = oracledb.connect(
        user=db_user, password=db_password, dsn=db_dsn,
        config_dir=wallet_path, wallet_location=wallet_path
    )
    logger.info("✓ Connexion réussie")
    cursor = conn.cursor()
except Exception as e:
    logger.error(f"Erreur de connexion Oracle: {e}")
    sys.exit(1)

# NETTOYAGE avec TRUNCATE
logger.info("🧹 Nettoyage des tables (TRUNCATE)...")
tables = ['contacts', 'adresses', 'activites', 'structures', 'professionnels']
for table in tables:
    try:
        cursor.execute(f"TRUNCATE TABLE {table}")
        logger.info(f"  ✓ Table '{table}' vidée")
    except Exception as e:
        logger.warning(f"  ⚠ Erreur TRUNCATE {table}: {e}")

conn.commit()

# Vérifier/Créer colonne identifiant_technique
logger.info("🔧 Vérification de l'architecture...")
try:
    cursor.execute("SELECT identifiant_technique FROM structures WHERE ROWNUM = 1")
    logger.info("  ✓ Colonne 'identifiant_technique' existe")
except:
    logger.info("  ➕ Ajout colonne 'identifiant_technique' à 'structures'...")
    try:
        cursor.execute("ALTER TABLE structures ADD (identifiant_technique VARCHAR2(50))")
        conn.commit()
        logger.info("  ✓ Colonne ajoutée")
    except Exception as e:
        logger.error(f"Erreur lors de l'ajout de la colonne: {e}")
        conn.close()
        sys.exit(1)

# Log import
logger.info("📝 Enregistrement du log d'import...")
date_import = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
cursor.execute("""
    INSERT INTO import_logs (script_execute, date_debut, date_import, statut)
    VALUES (:1, SYSDATE, TO_DATE(:2, 'YYYY-MM-DD HH24:MI:SS'), 'En cours')
""", [file_path.name, date_import])
conn.commit()
cursor.execute("SELECT MAX(id_log) FROM import_logs")
id_log = cursor.fetchone()[0]
logger.info(f"  ✓ Log ID: {id_log}")

# Compteurs détaillés
stats = {
    'lignes_lues': 0,
    'professionnels': 0,
    'activites': 0,
    'activites_perdues': 0,  # Nouveau compteur
    'structures': 0,
    'structures_uniques': 0,  # Nouveau compteur
    'adresses': 0,
    'contacts': 0,
    'inactifs': 0,
    'erreurs': 0,
    'id_map_misses': 0  # Nouveau compteur pour tracer les pertes
}

# Buffers
buffer_pros = []
buffer_activites = []
buffer_structures_data = []
buffer_adresses = []
buffer_contacts = []

def clean_phone(phone):
    if not phone:
        return None
    phone = re.sub(r'[^\d+]', '', phone)
    return phone if phone and len(phone) >= 10 else None

def is_valid_email(email):
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def chunks(lst, n):
    """Divise une liste en chunks de taille n"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def build_id_map_chunked(unique_structures):
    """
    Version corrigée de l'ID Map qui gère les limites Oracle
    Divise les requêtes en chunks pour éviter ORA-01795
    """
    id_map = {}
    
    if not unique_structures:
        return id_map
    
    # Séparer les identifiants par type
    sirets = list(set(s for s, f, i in unique_structures if s))
    finess = list(set(f for s, f, i in unique_structures if f))
    id_techs = list(set(i for s, f, i in unique_structures if i))
    
    if DEBUG_MODE:
        logger.debug(f"  ID Map: {len(sirets)} SIRETs, {len(finess)} FINESS, {len(id_techs)} ID_TECH")
    
    # Traiter les SIRETs par chunks
    for siret_chunk in chunks(sirets, ID_MAP_CHUNK_SIZE):
        if siret_chunk:
            placeholders = ','.join([f":{i}" for i in range(len(siret_chunk))])
            query = f"""
                SELECT id_structure, siret 
                FROM structures 
                WHERE siret IN ({placeholders})
            """
            cursor.execute(query, siret_chunk)
            for id_struct, s in cursor.fetchall():
                id_map[s] = id_struct
    
    # Traiter les FINESS par chunks
    for finess_chunk in chunks(finess, ID_MAP_CHUNK_SIZE):
        if finess_chunk:
            placeholders = ','.join([f":{i}" for i in range(len(finess_chunk))])
            query = f"""
                SELECT id_structure, finess 
                FROM structures 
                WHERE finess IN ({placeholders})
            """
            cursor.execute(query, finess_chunk)
            for id_struct, f in cursor.fetchall():
                id_map[f] = id_struct
    
    # Traiter les ID_TECH par chunks
    for id_tech_chunk in chunks(id_techs, ID_MAP_CHUNK_SIZE):
        if id_tech_chunk:
            placeholders = ','.join([f":{i}" for i in range(len(id_tech_chunk))])
            query = f"""
                SELECT id_structure, identifiant_technique 
                FROM structures 
                WHERE identifiant_technique IN ({placeholders})
            """
            cursor.execute(query, id_tech_chunk)
            for id_struct, i in cursor.fetchall():
                id_map[i] = id_struct
    
    return id_map

def flush_buffers():
    """
    Version optimisée du flush avec meilleure gestion de l'ID Map
    """
    global buffer_pros, buffer_activites, buffer_structures_data
    global buffer_adresses, buffer_contacts
    
    # 1. PROFESSIONNELS (MERGE en batch)
    if buffer_pros:
        if DEBUG_MODE:
            logger.debug(f"  Flush {len(buffer_pros)} professionnels...")
        
        cursor.executemany("""
            MERGE INTO professionnels p
            USING (SELECT :1 AS id, :2 AS nom, :3 AS prenom, :4 AS nom_ex,
                          :5 AS code_prof, :6 AS lib_prof, :7 AS code_cat,
                          :8 AS code_sf, :9 AS lib_sf, :10 AS statut
                   FROM DUAL) src
            ON (p.id_professionnel = src.id)
            WHEN MATCHED THEN
                UPDATE SET nom = src.nom, prenom = src.prenom,
                           nom_exercice = src.nom_ex,
                           code_profession = src.code_prof,
                           libelle_profession = src.lib_prof,
                           code_categorie_profession = src.code_cat,
                           code_savoir_faire = src.code_sf,
                           libelle_savoir_faire = src.lib_sf,
                           statut_enregistrement = src.statut,
                           date_derniere_maj = SYSDATE
            WHEN NOT MATCHED THEN
                INSERT (id_professionnel, nom, prenom, nom_exercice,
                       code_profession, libelle_profession, code_categorie_profession,
                       code_savoir_faire, libelle_savoir_faire,
                       statut_enregistrement, date_import)
                VALUES (src.id, src.nom, src.prenom, src.nom_ex,
                       src.code_prof, src.lib_prof, src.code_cat,
                       src.code_sf, src.lib_sf, src.statut, SYSDATE)
        """, buffer_pros)
        stats['professionnels'] += len(buffer_pros)
        buffer_pros = []
    
    # 2. STRUCTURES (MERGE en batch)
    if buffer_structures_data:
        unique_structures = list(set(buffer_structures_data))
        stats['structures_uniques'] += len(unique_structures)
        
        if DEBUG_MODE:
            logger.debug(f"  Flush {len(unique_structures)} structures uniques...")
        
        cursor.executemany("""
            MERGE INTO structures s
            USING (SELECT :1 AS siret, :2 AS finess, :3 AS id_tech FROM DUAL) src
            ON ((s.siret = src.siret AND src.siret IS NOT NULL)
                OR (s.finess = src.finess AND src.finess IS NOT NULL)
                OR (s.identifiant_technique = src.id_tech AND src.id_tech IS NOT NULL))
            WHEN NOT MATCHED THEN
                INSERT (siret, finess, identifiant_technique, date_import)
                VALUES (src.siret, src.finess, src.id_tech, SYSDATE)
        """, unique_structures)
        
        stats['structures'] += len(unique_structures)
        
        # 3. ID MAP CORRIGÉE avec chunks
        id_map = build_id_map_chunked(unique_structures)
        
        if DEBUG_MODE:
            logger.debug(f"  ID Map contient {len(id_map)} entrées")
        
        # 4. ACTIVITÉS avec traçabilité des pertes
        if buffer_activites:
            activites_with_ids = []
            activites_total = len(buffer_activites)
            
            for id_prof, key, code_sf, lib_sf, code_mode, mode_ex in buffer_activites:
                id_struct = id_map.get(key)
                if id_struct:
                    activites_with_ids.append([
                        id_prof, id_struct, code_sf, lib_sf,
                        code_mode, mode_ex
                    ])
                else:
                    stats['id_map_misses'] += 1
                    stats['activites_perdues'] += 1
                    if DEBUG_MODE and stats['id_map_misses'] <= 10:
                        logger.debug(f"    ⚠ Structure non trouvée: key='{key}', prof={id_prof}")
            
            if activites_with_ids:
                cursor.executemany("""
                    INSERT INTO activites (
                        id_professionnel, id_structure,
                        code_savoir_faire, libelle_savoir_faire,
                        code_mode_exercice, mode_exercice,
                        statut_activite, date_import
                    ) VALUES (:1, :2, :3, :4, :5, :6, 'Actif', SYSDATE)
                """, activites_with_ids)
                stats['activites'] += len(activites_with_ids)
            
            if DEBUG_MODE:
                logger.debug(f"  Activités: {len(activites_with_ids)}/{activites_total} insérées")
            
            buffer_activites = []
        
        # 5. ADRESSES
        if buffer_adresses and id_map:
            adresses_with_ids = []
            for id_prof, key, type_adr, numero, type_voie, lib_voie, cp, commune, dept in buffer_adresses:
                id_struct = id_map.get(key)
                if id_struct:
                    adresses_with_ids.append([
                        id_prof, id_struct, type_adr, numero, type_voie,
                        lib_voie, cp, commune, dept
                    ])
            
            if adresses_with_ids:
                cursor.executemany("""
                    INSERT INTO adresses (
                        id_professionnel, id_structure, type_adresse,
                        numero_voie, type_voie, libelle_voie,
                        code_postal, commune, departement, pays, date_import
                    ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, 'France', SYSDATE)
                """, adresses_with_ids)
                stats['adresses'] += len(adresses_with_ids)
            buffer_adresses = []
        
        buffer_structures_data = []
    
    # 6. CONTACTS
    if buffer_contacts:
        cursor.executemany("""
            MERGE INTO contacts c
            USING (SELECT :1 AS id_prof, :2 AS type, :3 AS val, :4 AS prio FROM DUAL) src
            ON (c.id_professionnel = src.id_prof
                AND c.type_contact = src.type
                AND c.valeur = src.val)
            WHEN NOT MATCHED THEN
                INSERT (id_professionnel, type_contact, valeur, source_origine, priorite, date_import)
                VALUES (src.id_prof, src.type, src.val, 'RPPS', src.prio, SYSDATE)
        """, buffer_contacts)
        stats['contacts'] += len(buffer_contacts)
        buffer_contacts = []
    
    # UN SEUL COMMIT pour tout le batch
    conn.commit()


logger.info("🚀 Démarrage de l'import...")
start_time = datetime.now()

try:
    with open(FICHIER_RPPS, 'r', encoding='utf-8') as f:
        header = f.readline().strip().split('|')
        
        # Mapping des colonnes
        def get_col(name, req=True):
            try:
                return header.index(name)
            except ValueError:
                if req:
                    logger.error(f"Colonne requise '{name}' non trouvée")
                    sys.exit(1)
                return None
        
        def get_val(fields, idx, default='', max_len=None):
            if idx is None:
                return default
            try:
                val = fields[idx].strip()
                if max_len and val:
                    val = val[:max_len]
                return val if val else default
            except IndexError:
                return default
        
        # Colonnes
        COL_ID = get_col('Identifiant PP')
        COL_NOM = get_col("Nom d'exercice")
        COL_PRENOM = get_col("Prénom d'exercice", False)
        COL_CODE_PROF = get_col('Code profession')
        COL_LIB_PROF = get_col('Libellé profession')
        COL_CODE_CAT = get_col('Code catégorie professionnelle', False)
        COL_CODE_SF = get_col('Code savoir-faire', False)
        COL_LIB_SF = get_col('Libellé savoir-faire', False)
        COL_CODE_MODE = get_col('Code mode exercice', False)
        COL_MODE_EX = get_col('Libellé mode exercice', False)
        COL_SIRET = get_col('Numéro SIRET site', False)
        COL_FINESS = get_col('Numéro FINESS site', False)
        COL_ID_TECH = get_col('Identifiant technique de la structure', False)
        COL_AUTORITE = get_col('Autorité d\'enregistrement', False)
        COL_NUMERO = get_col('Numéro Voie (coord. structure)', False)
        COL_TYPE_VOIE = get_col('Libellé type de voie (coord. structure)', False)
        COL_LIB_VOIE = get_col('Libellé Voie (coord. structure)', False)
        COL_CP = get_col('Code postal (coord. structure)', False)
        COL_COMMUNE = get_col('Libellé commune (coord. structure)', False)
        COL_TEL1 = get_col('Téléphone (coord. structure)', False)
        COL_TEL2 = get_col('Téléphone 2 (coord. structure)', False)
        COL_EMAIL = get_col('Adresse e-mail (coord. structure)', False)
        
        logger.info("✓ Colonnes mappées avec succès\n")
        
        # Lecture du fichier
        for line in f:
            stats['lignes_lues'] += 1
            
            try:
                fields = line.strip().split('|')
                
                id_prof = get_val(fields, COL_ID)
                if not id_prof:
                    stats['erreurs'] += 1
                    continue
                
                # Professionnel
                nom = get_val(fields, COL_NOM, max_len=100)
                prenom = get_val(fields, COL_PRENOM, None, 100)
                code_prof = get_val(fields, COL_CODE_PROF, max_len=10)
                lib_prof = get_val(fields, COL_LIB_PROF, max_len=200)
                code_cat = get_val(fields, COL_CODE_CAT, max_len=2)
                code_sf = get_val(fields, COL_CODE_SF, max_len=10)
                lib_sf = get_val(fields, COL_LIB_SF, max_len=200)
                
                # Statut
                mode_ex = get_val(fields, COL_MODE_EX)
                autorite = get_val(fields, COL_AUTORITE)
                statut = 'Inactif' if (not mode_ex or autorite.endswith('//')) else 'Actif'
                
                if statut == 'Inactif':
                    stats['inactifs'] += 1
                
                buffer_pros.append([
                    id_prof, nom, prenom, nom, code_prof, lib_prof, code_cat,
                    code_sf, lib_sf, statut
                ])
                
                # Structure
                siret = get_val(fields, COL_SIRET, max_len=14)
                finess = get_val(fields, COL_FINESS, max_len=9)
                id_tech = get_val(fields, COL_ID_TECH, max_len=50)
                key = siret or finess or id_tech
                
                if key and statut == 'Actif':
                    buffer_structures_data.append((siret, finess, id_tech))
                    
                    # Activité
                    code_mode = get_val(fields, COL_CODE_MODE, max_len=1)
                    buffer_activites.append([
                        id_prof, key, code_sf, lib_sf, code_mode, mode_ex
                    ])
                    
                    # Adresse
                    numero = get_val(fields, COL_NUMERO, max_len=10)
                    type_voie = get_val(fields, COL_TYPE_VOIE, max_len=50)
                    lib_voie = get_val(fields, COL_LIB_VOIE, max_len=200)
                    cp = get_val(fields, COL_CP, max_len=5)
                    commune = get_val(fields, COL_COMMUNE, max_len=100)
                    
                    dept = None
                    if cp and len(cp) >= 2:
                        if cp.startswith('20'):
                            dept = '2A' if cp[:3] in ['200','201'] else '2B'
                        elif cp.startswith(('97','98')):
                            dept = cp[:3]
                        elif len(cp) == 5:
                            dept = cp[:2]
                        elif len(cp) == 4:
                            dept = '0' + cp[0]
                    
                    if cp or commune:
                        buffer_adresses.append([
                            id_prof, key, 'Professionnelle',
                            numero, type_voie, lib_voie, cp, commune, dept
                        ])
                    
                    # Contacts
                    tel1 = clean_phone(get_val(fields, COL_TEL1))
                    if tel1:
                        buffer_contacts.append([id_prof, 'TELEPHONE', tel1, 1])
                    
                    tel2 = clean_phone(get_val(fields, COL_TEL2))
                    if tel2 and tel2 != tel1:
                        buffer_contacts.append([id_prof, 'TELEPHONE', tel2, 2])
                    
                    email = get_val(fields, COL_EMAIL).lower()
                    if email and is_valid_email(email):
                        buffer_contacts.append([id_prof, 'EMAIL', email, 1])
            
            except Exception as e:
                stats['erreurs'] += 1
                if stats['erreurs'] <= 10:
                    logger.error(f"Erreur ligne {stats['lignes_lues']}: {e}")
                if stats['erreurs'] > 1000:
                    logger.error("Trop d'erreurs, arrêt.")
                    raise
            
            # FLUSH du lot
            if stats['lignes_lues'] % BATCH_SIZE == 0:
                flush_buffers()
                elapsed = (datetime.now() - start_time).total_seconds()
                vitesse = stats['lignes_lues'] / elapsed if elapsed > 0 else 0
                
                logger.info(
                    f"  {stats['lignes_lues']:,} lignes | "
                    f"{stats['activites']:,} activités | "
                    f"{stats['activites_perdues']:,} perdues | "
                    f"{vitesse:,.0f} l/s"
                )
        
        # Flush final
        logger.info("\n  Flush final...")
        flush_buffers()

except Exception as e:
    logger.error(f"ERREUR FATALE: {e}")
    import traceback
    traceback.print_exc()
    cursor.execute("""
        UPDATE import_logs SET statut='Erreur', date_fin=SYSDATE,
        message_log=:1 WHERE id_log=:2
    """, [str(e)[:500], id_log])
    conn.commit()
    conn.close()
    sys.exit(1)

# Post-traitement
logger.info("📄 Calcul du mode d'exercice principal...")
cursor.execute("""
    UPDATE professionnels p
    SET mode_exercice_principal = (
        SELECT CASE
            WHEN COUNT(DISTINCT code_mode_exercice) > 1 THEN 'Mixte'
            WHEN MAX(code_mode_exercice) = 'L' THEN 'Libéral'
            WHEN MAX(code_mode_exercice) = 'S' THEN 'Salarié'
            WHEN MAX(code_mode_exercice) = 'B' THEN 'Bénévole'
            ELSE 'Autre'
        END
        FROM activites WHERE id_professionnel = p.id_professionnel
    )
    WHERE statut_enregistrement = 'Actif'
""")
logger.info(f"  ✓ {cursor.rowcount:,} professionnels mis à jour")
conn.commit()

# Fin
duration = (datetime.now() - start_time).total_seconds()
cursor.execute("""
    UPDATE import_logs SET statut='Terminé', date_fin=SYSDATE,
    nb_lignes_traitees=:1, nb_lignes_inserees=:2, nb_erreurs=:3,
    duree_secondes=:4 WHERE id_log=:5
""", [stats['lignes_lues'], stats['professionnels'], stats['erreurs'], int(duration), id_log])
conn.commit()

print("\n" + "="*60)
print("✅ IMPORT TERMINÉ AVEC SUCCÈS")
print("="*60)
print(f"⏱  Durée totale         : {duration/60:.1f} minutes")
print(f"🚀 Vitesse moyenne      : {stats['lignes_lues']/duration:,.0f} l/s")
print("="*60)
print(f"📊 Lignes lues          : {stats['lignes_lues']:,}")
print(f"👤 Professionnels       : {stats['professionnels']:,}")
print(f"   - Actifs            : {stats['professionnels']-stats['inactifs']:,}")
print(f"   - Inactifs          : {stats['inactifs']:,} ({(stats['inactifs']/stats['professionnels'])*100:.1f}%)")
print(f"🏢 Structures           : {stats['structures']:,}")
print(f"📍 Activités insérées   : {stats['activites']:,}")
if stats['activites_perdues'] > 0:
    print(f"⚠️  Activités perdues    : {stats['activites_perdues']:,} ({stats['activites_perdues']*100/(stats['activites']+stats['activites_perdues']):.1f}%)")
    print(f"   ID Map misses       : {stats['id_map_misses']:,}")
print(f"🏠 Adresses            : {stats['adresses']:,}")
print(f"📞 Contacts            : {stats['contacts']:,}")
print(f"⚠️  Erreurs            : {stats['erreurs']:,}")
print("="*60)

if stats['activites_perdues'] > 1000:
    print("\n⚠️  ATTENTION: Perte de données détectée!")
    print("   Activez DEBUG_MODE=true dans .env pour plus de détails")

conn.close()
print("\nConnexion fermée.")
print("\n🎯 Prochaines étapes:")
print("   1. python diagnostic_import.py  # Vérifier la cohérence")
print("   2. python explorer_donnees.py   # Explorer les données")
