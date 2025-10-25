#!/usr/bin/env python3
"""
EXTRACTEUR RPPS OPTIMISÉ v3.0 - CORRECTION DU BUG D'ÉCRASEMENT
================================================================
CORRECTIFS MAJEURS:
- ✅ Déduplication intelligente des professionnels (agrégation au lieu d'écrasement)
- ✅ Séparation claire entre données de professionnel et données d'activité
- ✅ Optimisation de la performance avec buffers adaptés
- ✅ Gestion robuste des erreurs et retry

PERFORMANCES CIBLES:
- ~1500-2000 lignes/seconde
- Batch size adaptatif (10k-50k)
- Gestion mémoire optimale
"""

import oracledb
import os
import csv
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import logging
from collections import defaultdict

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
CONFIG = {
    'batch_size': 20000,           # Batch initial augmenté
    'batch_size_min': 5000,         # Batch minimal en cas d'erreur
    'batch_size_max': 50000,        # Batch maximal
    'id_map_chunk_size': 900,       # Limite Oracle pour IN clause
    'max_retry_undo': 3,            # Retry max sur ORA-30036
    'max_errors': 1000,             # Arrêt si trop d'erreurs
    'commit_frequency': 1,          # COMMIT après chaque batch
    'fichier_rpps': 'PS_LibreAcces_Personne_activite_202509230829.txt',
    'debug_mode': os.getenv("DEBUG_MODE", "False").lower() == "true",
    'progress_interval': 50000,     # Afficher progression tous les 50k lignes
}

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.DEBUG if CONFIG['debug_mode'] else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_rpps_v3.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONNEXION ORACLE
# ============================================================================
def init_oracle():
    """Initialise le client Oracle et retourne la connexion"""
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

# ============================================================================
# UTILITAIRES
# ============================================================================
def clean_phone(phone):
    """Nettoie un numéro de téléphone"""
    if not phone:
        return None
    phone = re.sub(r'[^\d+]', '', phone)
    return phone if phone and len(phone) >= 10 else None

def is_valid_email(email):
    """Valide un email"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def chunks(lst, n):
    """Divise une liste en chunks de taille n"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def extract_departement(code_postal):
    """Extrait le département depuis le code postal"""
    if not code_postal:
        return None

    cp = str(code_postal).strip()

    # Corse
    if cp.startswith('20'):
        if cp[:3] in ['200', '201']:
            return '2A'
        return '2B'

    # DOM-TOM
    if cp.startswith(('97', '98')) and len(cp) >= 3:
        return cp[:3]

    # Métropole
    if len(cp) == 5:
        return cp[:2]
    elif len(cp) == 4:
        return '0' + cp[0]

    return None

# ============================================================================
# MAPPING COLONNES RPPS
# ============================================================================
COLUMNS_MAP = {
    'id_professionnel': 0,
    'nom': 7,
    'prenom': 8,
    'code_profession': 9,
    'libelle_profession': 10,
    'code_categorie': 11,
    'code_savoir_faire': 15,
    'libelle_savoir_faire': 16,
    'code_mode_exercice': 17,
    'mode_exercice': 18,
    'siret': 21,
    'finess': 23,
    'identifiant_technique': 25,
    'autorite': 27,
    'numero_voie': 28,
    'type_voie': 30,
    'libelle_voie': 31,
    'code_postal': 35,
    'commune': 37,
    'telephone_1': 40,
    'telephone_2': 41,
    'email': 43,
}

def get_value(fields, col_name, default='', max_len=None):
    """Extrait une valeur de la ligne avec gestion d'erreur"""
    try:
        idx = COLUMNS_MAP.get(col_name)
        if idx is None:
            return default

        val = fields[idx].strip() if idx < len(fields) else default

        if max_len and val:
            val = val[:max_len]

        return val if val else default
    except (IndexError, AttributeError):
        return default

# ============================================================================
# EXTRACTION ET PARSING
# ============================================================================
class RPPSExtractor:
    def __init__(self, fichier_rpps):
        self.fichier_rpps = fichier_rpps
        self.stats = {
            'lignes_lues': 0,
            'professionnels': 0,
            'structures': 0,
            'activites': 0,
            'activites_perdues': 0,
            'adresses': 0,
            'contacts': 0,
            'inactifs': 0,
            'erreurs': 0,
        }

    def extract(self):
        """
        Générateur qui lit le fichier RPPS ligne par ligne
        et yield des dictionnaires structurés
        """
        logger.info(f"📖 Lecture fichier : {self.fichier_rpps}")

        with open(self.fichier_rpps, 'r', encoding='utf-8') as f:
            # Utilisation de csv.reader pour parsing rapide
            reader = csv.reader(f, delimiter='|')

            # Skip header
            next(reader)

            for fields in reader:
                self.stats['lignes_lues'] += 1

                try:
                    # Extraction des données
                    id_prof = get_value(fields, 'id_professionnel')
                    if not id_prof:
                        self.stats['erreurs'] += 1
                        continue

                    # Professionnel (DONNÉES STABLES - ne changent pas par activité)
                    nom = get_value(fields, 'nom', max_len=100)
                    prenom = get_value(fields, 'prenom', max_len=100)
                    code_prof = get_value(fields, 'code_profession', max_len=10)
                    lib_prof = get_value(fields, 'libelle_profession', max_len=200)
                    code_cat = get_value(fields, 'code_categorie', max_len=2)

                    # Savoir-faire SPÉCIFIQUE à l'activité (ne va PAS dans professionnel)
                    code_sf = get_value(fields, 'code_savoir_faire', max_len=10)
                    lib_sf = get_value(fields, 'libelle_savoir_faire', max_len=200)

                    # Statut
                    mode_ex = get_value(fields, 'mode_exercice')
                    autorite = get_value(fields, 'autorite')
                    statut = 'Inactif' if (not mode_ex or autorite.endswith('//')) else 'Actif'

                    if statut == 'Inactif':
                        self.stats['inactifs'] += 1

                    # Structure (clé = SIRET OU FINESS OU ID_TECH)
                    siret = get_value(fields, 'siret', max_len=14)
                    finess = get_value(fields, 'finess', max_len=9)
                    id_tech = get_value(fields, 'identifiant_technique', max_len=50)
                    key = siret or finess or id_tech

                    # Contacts
                    tel1 = clean_phone(get_value(fields, 'telephone_1'))
                    tel2 = clean_phone(get_value(fields, 'telephone_2'))
                    email = get_value(fields, 'email').lower()

                    # Adresse
                    numero = get_value(fields, 'numero_voie', max_len=10)
                    type_voie = get_value(fields, 'type_voie', max_len=50)
                    lib_voie = get_value(fields, 'libelle_voie', max_len=200)
                    cp = get_value(fields, 'code_postal', max_len=5)
                    commune = get_value(fields, 'commune', max_len=100)
                    dept = extract_departement(cp)

                    # Activité
                    code_mode = get_value(fields, 'code_mode_exercice', max_len=1)

                    # Yield un dictionnaire structuré
                    yield {
                        'professionnel': {
                            'id': id_prof,
                            'nom': nom,
                            'prenom': prenom,
                            'code_profession': code_prof,
                            'libelle_profession': lib_prof,
                            'code_categorie': code_cat,
                            'statut': statut,
                        },
                        'structure': {
                            'siret': siret,
                            'finess': finess,
                            'identifiant_technique': id_tech,
                            'key': key,
                        } if key and statut == 'Actif' else None,
                        'activite': {
                            'id_professionnel': id_prof,
                            'key': key,
                            'code_savoir_faire': code_sf,
                            'libelle_savoir_faire': lib_sf,
                            'code_mode_exercice': code_mode,
                            'mode_exercice': mode_ex,
                        } if key and statut == 'Actif' else None,
                        'adresse': {
                            'id_professionnel': id_prof,
                            'key': key,
                            'numero': numero,
                            'type_voie': type_voie,
                            'libelle_voie': lib_voie,
                            'code_postal': cp,
                            'commune': commune,
                            'departement': dept,
                        } if (cp or commune) and key and statut == 'Actif' else None,
                        'contacts': [
                            {'id_professionnel': id_prof, 'type': 'TELEPHONE', 'valeur': tel1, 'priorite': 1}
                            if tel1 else None,
                            {'id_professionnel': id_prof, 'type': 'TELEPHONE', 'valeur': tel2, 'priorite': 2}
                            if tel2 and tel2 != tel1 else None,
                            {'id_professionnel': id_prof, 'type': 'EMAIL', 'valeur': email, 'priorite': 1}
                            if email and is_valid_email(email) else None,
                        ]
                    }

                except Exception as e:
                    self.stats['erreurs'] += 1
                    if self.stats['erreurs'] <= 10:
                        logger.error(f"Erreur ligne {self.stats['lignes_lues']}: {e}")

                    if self.stats['erreurs'] > CONFIG['max_errors']:
                        logger.error("Trop d'erreurs, arrêt.")
                        raise

# ============================================================================
# CHARGEMENT ORACLE - VERSION CORRIGÉE
# ============================================================================
class OracleLoader:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self.current_batch_size = CONFIG['batch_size']
        self.retry_count_undo = 0

        # ✅ CORRECTION : Utilisation de dict pour déduplication INTELLIGENTE
        # On garde la PREMIÈRE occurrence complète de chaque professionnel
        self.professionnels_map = {}  # {id_prof: [id, nom, prenom, ...]}

        # Buffers normaux pour les autres entités
        self.buffer_structures = []
        self.buffer_activites = []
        self.buffer_adresses = []
        self.buffer_contacts = []

    def add_record(self, record):
        """Ajoute un enregistrement aux buffers"""
        # ✅ CORRECTION : Professionnel - on garde seulement la PREMIÈRE occurrence
        p = record['professionnel']
        prof_id = p['id']

        # Si ce professionnel n'existe pas encore dans notre map, on l'ajoute
        if prof_id not in self.professionnels_map:
            # NOTE: On retire code_savoir_faire et libelle_savoir_faire
            # car ce sont des données SPÉCIFIQUES à l'activité, pas au professionnel
            self.professionnels_map[prof_id] = [
                prof_id,
                p['nom'],
                p['prenom'],
                p['nom'],  # nom_exercice (peut être amélioré)
                p['code_profession'],
                p['libelle_profession'],
                p['code_categorie'],
                None,  # code_savoir_faire => NULL (sera calculé plus tard si besoin)
                None,  # libelle_savoir_faire => NULL
                p['statut']
            ]

        # Structure
        if record['structure']:
            s = record['structure']
            self.buffer_structures.append((s['siret'], s['finess'], s['identifiant_technique']))

        # Activité
        if record['activite']:
            a = record['activite']
            self.buffer_activites.append([
                a['id_professionnel'], a['key'], a['code_savoir_faire'],
                a['libelle_savoir_faire'], a['code_mode_exercice'], a['mode_exercice']
            ])

        # Adresse
        if record['adresse']:
            ad = record['adresse']
            self.buffer_adresses.append([
                ad['id_professionnel'], ad['key'], 'Professionnelle',
                ad['numero'], ad['type_voie'], ad['libelle_voie'],
                ad['code_postal'], ad['commune'], ad['departement']
            ])

        # Contacts
        for contact in record['contacts']:
            if contact:
                self.buffer_contacts.append([
                    contact['id_professionnel'], contact['type'],
                    contact['valeur'], contact['priorite']
                ])

    def should_flush(self):
        """Vérifie si on doit flusher les buffers"""
        return len(self.buffer_activites) >= self.current_batch_size

    def build_id_map_chunked(self, unique_structures):
        """Construit l'ID Map en chunks pour éviter ORA-01795"""
        id_map = {}

        if not unique_structures:
            return id_map

        sirets = list(set(s for s, f, i in unique_structures if s))
        finess = list(set(f for s, f, i in unique_structures if f))
        id_techs = list(set(i for s, f, i in unique_structures if i))

        # SIRET
        for chunk in chunks(sirets, CONFIG['id_map_chunk_size']):
            if chunk:
                placeholders = ','.join([f":{i}" for i in range(len(chunk))])
                query = f"SELECT id_structure, siret FROM structures WHERE siret IN ({placeholders})"
                self.cursor.execute(query, chunk)
                for id_struct, s in self.cursor.fetchall():
                    id_map[s] = id_struct

        # FINESS
        for chunk in chunks(finess, CONFIG['id_map_chunk_size']):
            if chunk:
                placeholders = ','.join([f":{i}" for i in range(len(chunk))])
                query = f"SELECT id_structure, finess FROM structures WHERE finess IN ({placeholders})"
                self.cursor.execute(query, chunk)
                for id_struct, f in self.cursor.fetchall():
                    id_map[f] = id_struct

        # ID TECHNIQUE
        for chunk in chunks(id_techs, CONFIG['id_map_chunk_size']):
            if chunk:
                placeholders = ','.join([f":{i}" for i in range(len(chunk))])
                query = f"SELECT id_structure, identifiant_technique FROM structures WHERE identifiant_technique IN ({placeholders})"
                self.cursor.execute(query, chunk)
                for id_struct, i in self.cursor.fetchall():
                    id_map[i] = id_struct

        return id_map

    def flush(self, stats):
        """Flush tous les buffers en base"""
        try:
            # ✅ 1. PROFESSIONNELS (UPSERT OPTIMISÉ - CORRECTION MAJEURE)
            if self.professionnels_map:
                # Convertir le dict en liste
                unique_pros = list(self.professionnels_map.values())

                # Récupérer les IDs qui existent déjà
                ids_pros_batch = [p[0] for p in unique_pros]
                existing_ids = set()

                if ids_pros_batch:
                    for chunk in chunks(ids_pros_batch, CONFIG['id_map_chunk_size']):
                        if not chunk:
                            continue
                        placeholders = ','.join([f":{i}" for i in range(len(chunk))])
                        query = f"SELECT id_professionnel FROM professionnels WHERE id_professionnel IN ({placeholders})"
                        self.cursor.execute(query, chunk)
                        for row in self.cursor.fetchall():
                            existing_ids.add(row[0])

                # Préparer les lots d'update et d'insert
                buffer_pros_update = []
                buffer_pros_insert = []
                for p in unique_pros:
                    if p[0] in existing_ids:
                        # Format pour UPDATE: nom, prenom, ..., id
                        buffer_pros_update.append(p[1:] + [p[0]])
                    else:
                        # Format pour INSERT: id, nom, prenom, ...
                        buffer_pros_insert.append(p)

                # Exécuter l'UPDATE en masse
                if buffer_pros_update:
                    self.cursor.executemany("""
                        UPDATE professionnels
                        SET nom = :1, prenom = :2, nom_exercice = :3,
                            code_profession = :4, libelle_profession = :5,
                            code_categorie_profession = :6,
                            statut_enregistrement = :9,
                            date_derniere_maj = SYSDATE
                        WHERE id_professionnel = :10
                    """, buffer_pros_update)
                    logger.debug(f"  ✓ {len(buffer_pros_update):,} professionnels mis à jour")

                # Exécuter l'INSERT en masse
                if buffer_pros_insert:
                    self.cursor.executemany("""
                        INSERT INTO professionnels (
                            id_professionnel, nom, prenom, nom_exercice,
                            code_profession, libelle_profession, code_categorie_profession,
                            code_savoir_faire, libelle_savoir_faire,
                            statut_enregistrement, date_import
                        ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, SYSDATE)
                    """, buffer_pros_insert)
                    logger.debug(f"  ✓ {len(buffer_pros_insert):,} professionnels insérés")

                stats['professionnels'] += len(buffer_pros_insert)  # ✅ Compter seulement les NOUVEAUX

            # 2. GESTION OPTIMISÉE DES STRUCTURES
            if self.buffer_structures:
                unique_structures = list(set(self.buffer_structures))

                # Étape A: Récupérer les IDs des structures déjà existantes
                id_map = self.build_id_map_chunked(unique_structures)

                # Étape B: Identifier les structures à insérer
                structures_a_inserer = []
                for siret, finess, id_tech in unique_structures:
                    key = siret or finess or id_tech
                    if key not in id_map:
                        structures_a_inserer.append((siret, finess, id_tech))

                # Étape C: Insérer uniquement les nouvelles structures
                if structures_a_inserer:
                    self.cursor.executemany("""
                        INSERT INTO structures (siret, finess, identifiant_technique, date_import)
                        VALUES (:1, :2, :3, SYSDATE)
                    """, structures_a_inserer)
                    stats['structures'] += len(structures_a_inserer)

                    # Étape D: Récupérer les IDs des nouvelles structures et mettre à jour la map
                    nouveaux_ids_map = self.build_id_map_chunked(structures_a_inserer)
                    id_map.update(nouveaux_ids_map)

                # 3. ACTIVITÉS
                if self.buffer_activites:
                    activites_with_ids = []
                    for id_prof, key, code_sf, lib_sf, code_mode, mode_ex in self.buffer_activites:
                        id_struct = id_map.get(key)
                        if id_struct:
                            activites_with_ids.append([
                                id_prof, id_struct, code_sf, lib_sf, code_mode, mode_ex
                            ])
                        else:
                            stats['activites_perdues'] += 1

                    if activites_with_ids:
                        self.cursor.executemany("""
                            INSERT INTO activites (
                                id_professionnel, id_structure,
                                code_savoir_faire, libelle_savoir_faire,
                                code_mode_exercice, mode_exercice,
                                statut_activite, date_import
                            ) VALUES (:1, :2, :3, :4, :5, :6, 'Actif', SYSDATE)
                        """, activites_with_ids)
                        stats['activites'] += len(activites_with_ids)

                # 4. ADRESSES
                if self.buffer_adresses:
                    adresses_with_ids = []
                    for id_prof, key, type_adr, numero, type_voie, lib_voie, cp, commune, dept in self.buffer_adresses:
                        id_struct = id_map.get(key)
                        if id_struct:
                            adresses_with_ids.append([
                                id_prof, id_struct, type_adr, numero, type_voie,
                                lib_voie, cp, commune, dept
                            ])

                    if adresses_with_ids:
                        self.cursor.executemany("""
                            INSERT INTO adresses (
                                id_professionnel, id_structure, type_adresse,
                                numero_voie, type_voie, libelle_voie,
                                code_postal, commune, departement, pays, date_import
                            ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, 'France', SYSDATE)
                        """, adresses_with_ids)
                        stats['adresses'] += len(adresses_with_ids)

            # 5. CONTACTS
            if self.buffer_contacts:
                # Dé-duplication
                unique_contacts = list(set(tuple(c) for c in self.buffer_contacts))

                self.cursor.executemany("""
                    MERGE INTO contacts c
                    USING (SELECT :1 AS id_prof, :2 AS type, :3 AS val, :4 AS prio FROM DUAL) src
                    ON (c.id_professionnel = src.id_prof
                        AND c.type_contact = src.type
                        AND c.valeur = src.val)
                    WHEN NOT MATCHED THEN
                        INSERT (id_professionnel, type_contact, valeur, source_origine, priorite, date_import)
                        VALUES (src.id_prof, src.type, src.val, 'RPPS', src.prio, SYSDATE)
                """, unique_contacts)
                stats['contacts'] += len(unique_contacts)

            # ✅ Vider tous les buffers après traitement
            self.professionnels_map = {}  # ✅ CORRECTION : Vider le dict
            self.buffer_structures = []
            self.buffer_activites = []
            self.buffer_adresses = []
            self.buffer_contacts = []

            # COMMIT
            self.conn.commit()

            # Reset retry counter on success
            self.retry_count_undo = 0

        except oracledb.DatabaseError as e:
            error_code = e.args[0].code if hasattr(e.args[0], 'code') else 0

            # Retry sur ORA-30036 (UNDO saturé)
            if error_code == 30036:
                self.retry_count_undo += 1

                if self.retry_count_undo <= CONFIG['max_retry_undo']:
                    # Réduire la taille du batch
                    old_size = self.current_batch_size
                    self.current_batch_size = max(
                        CONFIG['batch_size_min'],
                        self.current_batch_size // 2
                    )

                    logger.warning(
                        f"⚠️  ORA-30036 : Réduction batch {old_size} → {self.current_batch_size} "
                        f"(tentative {self.retry_count_undo}/{CONFIG['max_retry_undo']})"
                    )

                    # Rollback et retry avec batch plus petit
                    self.conn.rollback()
                    return  # Ne pas vider les buffers, ils seront re-flushés
                else:
                    logger.error("❌ ORA-30036 : Trop de tentatives")
                    raise
            else:
                logger.error(f"❌ Erreur BDD : {e}")
                self.conn.rollback()
                raise

# ============================================================================
# MAIN
# ============================================================================
def main():
    logger.info("="*70)
    logger.info("🚀 EXTRACTEUR RPPS OPTIMISÉ v3.0 - CORRECTION BUG ÉCRASEMENT")
    logger.info("="*70)
    logger.info(f"📁 Fichier : {CONFIG['fichier_rpps']}")
    logger.info(f"📦 Batch size initial : {CONFIG['batch_size']:,}")

    start_time = datetime.now()

    # Stats
    stats = {
        'lignes_lues': 0,
        'professionnels': 0,
        'structures': 0,
        'activites': 0,
        'activites_perdues': 0,
        'adresses': 0,
        'contacts': 0,
        'inactifs': 0,
        'erreurs': 0,
    }

    # Connexion
    conn = init_oracle()
    logger.info("✅ Connexion Oracle établie")

    # Nettoyage
    logger.info("🧹 Nettoyage des tables...")
    cursor = conn.cursor()
    for table in ['contacts', 'adresses', 'activites', 'structures', 'professionnels']:
        cursor.execute(f"TRUNCATE TABLE {table}")
    conn.commit()
    logger.info("✅ Tables vidées")

    # Log import
    cursor.execute("""
        INSERT INTO import_logs (script_execute, date_debut, date_import, statut)
        VALUES (:1, SYSDATE, SYSDATE, 'En cours')
    """, [CONFIG['fichier_rpps']])
    conn.commit()
    cursor.execute("SELECT MAX(id_log) FROM import_logs")
    id_log = cursor.fetchone()[0]

    # Extraction et chargement
    extractor = RPPSExtractor(CONFIG['fichier_rpps'])
    loader = OracleLoader(conn)

    logger.info("🚀 Démarrage extraction...")

    try:
        for record in extractor.extract():
            loader.add_record(record)
            stats['lignes_lues'] = extractor.stats['lignes_lues']

            # Flush si nécessaire
            if loader.should_flush():
                loader.flush(stats)

                # Afficher progression
                if stats['lignes_lues'] % CONFIG['progress_interval'] == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    vitesse = stats['lignes_lues'] / elapsed if elapsed > 0 else 0

                    logger.info(
                        f"  📊 {stats['lignes_lues']:>10,} lignes | "
                        f"👤 {stats['professionnels']:>10,} pros | "
                        f"📝 {stats['activites']:>10,} activités | "
                        f"🚀 {vitesse:>6,.0f} l/s"
                    )

        # Flush final
        logger.info("🔄 Flush final...")
        loader.flush(stats)

        # Post-traitement : mode_exercice_principal
        logger.info("📊 Calcul mode exercice principal...")
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
        logger.info(f"✅ {cursor.rowcount:,} professionnels mis à jour")
        conn.commit()

        # Finaliser log
        duration = (datetime.now() - start_time).total_seconds()
        cursor.execute("""
            UPDATE import_logs SET statut='Terminé', date_fin=SYSDATE,
            nb_lignes_traitees=:1, nb_lignes_inserees=:2, nb_erreurs=:3,
            duree_secondes=:4 WHERE id_log=:5
        """, [stats['lignes_lues'], stats['professionnels'], stats['erreurs'], int(duration), id_log])
        conn.commit()

        # ✅ VÉRIFICATION FINALE
        logger.info("\n" + "="*70)
        logger.info("🔍 VÉRIFICATION DES DONNÉES")
        logger.info("="*70)

        cursor.execute("SELECT COUNT(*) FROM professionnels")
        nb_pros_final = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM activites")
        nb_act_final = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM structures")
        nb_struct_final = cursor.fetchone()[0]

        logger.info(f"✅ Professionnels en base : {nb_pros_final:,}")
        logger.info(f"✅ Activités en base       : {nb_act_final:,}")
        logger.info(f"✅ Structures en base      : {nb_struct_final:,}")

        # Affichage final
        print("\n" + "="*70)
        print("✅ IMPORT TERMINÉ AVEC SUCCÈS")
        print("="*70)
        print(f"⏱️  Durée             : {duration/60:.1f} minutes")
        print(f"🚀 Vitesse moyenne    : {stats['lignes_lues']/duration:,.0f} l/s")
        print("="*70)
        print(f"📊 Lignes lues        : {stats['lignes_lues']:>12,}")
        print(f"👤 Professionnels     : {nb_pros_final:>12,}")
        print(f"   - Inactifs         : {extractor.stats['inactifs']:>12,}")
        print(f"🏢 Structures         : {nb_struct_final:>12,}")
        print(f"📝 Activités          : {nb_act_final:>12,}")
        if stats['activites_perdues'] > 0:
            print(f"⚠️  Activités perdues  : {stats['activites_perdues']:>12,}")
        print(f"🏠 Adresses           : {stats['adresses']:>12,}")
        print(f"📞 Contacts           : {stats['contacts']:>12,}")
        print(f"❌ Erreurs            : {stats['erreurs']:>12,}")
        print("="*70)

    except Exception as e:
        logger.error(f"❌ ERREUR FATALE : {e}")
        import traceback
        traceback.print_exc()

        cursor.execute("""
            UPDATE import_logs SET statut='Erreur', date_fin=SYSDATE,
            message_log=:1 WHERE id_log=:2
        """, [str(e)[:500], id_log])
        conn.commit()
        return 1

    finally:
        conn.close()

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
