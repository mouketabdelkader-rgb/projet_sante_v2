#!/usr/bin/env python3
"""
EXTRACTEUR RPPS v4.0 - INSERT OPTIMISÉ (PREMIER IMPORT)
========================================================
OPTIMISATION MAJEURE:
- ✅ INSERT pur au lieu de MERGE (10-20x plus rapide pour premier import)
- ✅ Batch size optimal (5000 lignes)
- ✅ Pas de vérification d'existence (table vide après TRUNCATE)
- ✅ Performance attendue: 2000-3000 l/s

USAGE:
- Utilisez ce script pour le PREMIER import (tables vides)
- Pour les imports suivants (mise à jour), utilisez v3_fixed avec MERGE

ATTENTION:
- Ce script TRUNCATE toutes les tables au démarrage !
"""

import oracledb
import os
import csv
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import logging

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
CONFIG = {
    'batch_size': 5000,             # Batch optimisé pour INSERT pur
    'batch_size_min': 1000,         # Batch minimal
    'id_map_chunk_size': 500,       # Pour SELECT IN
    'max_retry_undo': 3,
    'max_errors': 1000,
    'fichier_rpps': 'PS_LibreAcces_Personne_activite_202509230829.txt',
    'debug_mode': os.getenv("DEBUG_MODE", "False").lower() == "true",
    'progress_interval': 25000,     # Progression tous les 25k lignes
}

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.DEBUG if CONFIG['debug_mode'] else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('import_rpps_v4.log'),
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
# UTILITAIRES (copie de v3)
# ============================================================================
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
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def extract_departement(code_postal):
    if not code_postal:
        return None
    cp = str(code_postal).strip()
    if cp.startswith('20'):
        if cp[:3] in ['200', '201']:
            return '2A'
        return '2B'
    if cp.startswith(('97', '98')) and len(cp) >= 3:
        return cp[:3]
    if len(cp) == 5:
        return cp[:2]
    elif len(cp) == 4:
        return '0' + cp[0]
    return None

# ============================================================================
# MAPPING COLONNES
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
# EXTRACTION (copie de v3)
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
        logger.info(f"📖 Lecture fichier : {self.fichier_rpps}")

        with open(self.fichier_rpps, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header

            for fields in reader:
                self.stats['lignes_lues'] += 1

                try:
                    id_prof = get_value(fields, 'id_professionnel')
                    if not id_prof:
                        self.stats['erreurs'] += 1
                        continue

                    nom = get_value(fields, 'nom', max_len=100)
                    prenom = get_value(fields, 'prenom', max_len=100)
                    code_prof = get_value(fields, 'code_profession', max_len=10)
                    lib_prof = get_value(fields, 'libelle_profession', max_len=200)
                    code_cat = get_value(fields, 'code_categorie', max_len=2)
                    code_sf = get_value(fields, 'code_savoir_faire', max_len=10)
                    lib_sf = get_value(fields, 'libelle_savoir_faire', max_len=200)

                    mode_ex = get_value(fields, 'mode_exercice')
                    autorite = get_value(fields, 'autorite')
                    statut = 'Inactif' if (not mode_ex or autorite.endswith('//')) else 'Actif'

                    if statut == 'Inactif':
                        self.stats['inactifs'] += 1

                    siret = get_value(fields, 'siret', max_len=14)
                    finess = get_value(fields, 'finess', max_len=9)
                    id_tech = get_value(fields, 'identifiant_technique', max_len=50)
                    key = siret or finess or id_tech

                    tel1 = clean_phone(get_value(fields, 'telephone_1'))
                    tel2 = clean_phone(get_value(fields, 'telephone_2'))
                    email = get_value(fields, 'email').lower()

                    numero = get_value(fields, 'numero_voie', max_len=10)
                    type_voie = get_value(fields, 'type_voie', max_len=50)
                    lib_voie = get_value(fields, 'libelle_voie', max_len=200)
                    cp = get_value(fields, 'code_postal', max_len=5)
                    commune = get_value(fields, 'commune', max_len=100)
                    dept = extract_departement(cp)

                    code_mode = get_value(fields, 'code_mode_exercice', max_len=1)

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
# LOADER OPTIMISÉ - INSERT PUR
# ============================================================================
class OracleLoaderInsertOnly:
    def __init__(self, conn):
        self.conn = conn
        self.cursor = conn.cursor()
        self.current_batch_size = CONFIG['batch_size']
        self.retry_count_undo = 0

        # Déduplication avec dict
        self.professionnels_map = {}
        self.buffer_structures = []
        self.buffer_activites = []
        self.buffer_adresses = []
        self.buffer_contacts = []

    def add_record(self, record):
        """Ajoute un enregistrement aux buffers"""
        p = record['professionnel']
        prof_id = p['id']

        if prof_id not in self.professionnels_map:
            self.professionnels_map[prof_id] = [
                prof_id, p['nom'], p['prenom'], p['nom'],
                p['code_profession'], p['libelle_profession'], p['code_categorie'],
                None, None, p['statut']
            ]

        if record['structure']:
            s = record['structure']
            self.buffer_structures.append((s['siret'], s['finess'], s['identifiant_technique']))

        if record['activite']:
            a = record['activite']
            self.buffer_activites.append([
                a['id_professionnel'], a['key'], a['code_savoir_faire'],
                a['libelle_savoir_faire'], a['code_mode_exercice'], a['mode_exercice']
            ])

        if record['adresse']:
            ad = record['adresse']
            self.buffer_adresses.append([
                ad['id_professionnel'], ad['key'], 'Professionnelle',
                ad['numero'], ad['type_voie'], ad['libelle_voie'],
                ad['code_postal'], ad['commune'], ad['departement']
            ])

        for contact in record['contacts']:
            if contact:
                self.buffer_contacts.append([
                    contact['id_professionnel'], contact['type'],
                    contact['valeur'], contact['priorite']
                ])

    def should_flush(self):
        return len(self.buffer_activites) >= self.current_batch_size

    def build_id_map_chunked(self, unique_structures):
        """Construit l'ID Map en chunks"""
        id_map = {}

        if not unique_structures:
            return id_map

        sirets = list(set(s for s, f, i in unique_structures if s))
        finess = list(set(f for s, f, i in unique_structures if f))
        id_techs = list(set(i for s, f, i in unique_structures if i))

        for chunk in chunks(sirets, CONFIG['id_map_chunk_size']):
            if chunk:
                placeholders = ','.join([f":{i}" for i in range(len(chunk))])
                query = f"SELECT id_structure, siret FROM structures WHERE siret IN ({placeholders})"
                self.cursor.execute(query, chunk)
                for id_struct, s in self.cursor.fetchall():
                    id_map[s] = id_struct

        for chunk in chunks(finess, CONFIG['id_map_chunk_size']):
            if chunk:
                placeholders = ','.join([f":{i}" for i in range(len(chunk))])
                query = f"SELECT id_structure, finess FROM structures WHERE finess IN ({placeholders})"
                self.cursor.execute(query, chunk)
                for id_struct, f in self.cursor.fetchall():
                    id_map[f] = id_struct

        for chunk in chunks(id_techs, CONFIG['id_map_chunk_size']):
            if chunk:
                placeholders = ','.join([f":{i}" for i in range(len(chunk))])
                query = f"SELECT id_structure, identifiant_technique FROM structures WHERE identifiant_technique IN ({placeholders})"
                self.cursor.execute(query, chunk)
                for id_struct, i in self.cursor.fetchall():
                    id_map[i] = id_struct

        return id_map

    def flush(self, stats):
        """Flush - INSERT PUR (pas de MERGE)"""
        try:
            # ✅ 1. PROFESSIONNELS - INSERT SIMPLE
            if self.professionnels_map:
                unique_pros = list(self.professionnels_map.values())

                if unique_pros:
                    logger.debug(f"  → Insertion de {len(unique_pros):,} professionnels...")
                    self.cursor.executemany("""
                        INSERT INTO professionnels (
                            id_professionnel, nom, prenom, nom_exercice,
                            code_profession, libelle_profession, code_categorie_profession,
                            code_savoir_faire, libelle_savoir_faire,
                            statut_enregistrement, date_import
                        ) VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, SYSDATE)
                    """, unique_pros)
                    stats['professionnels'] += len(unique_pros)
                    logger.debug(f"  ✓ {len(unique_pros):,} professionnels insérés")

            # 2. STRUCTURES
            if self.buffer_structures:
                unique_structures = list(set(self.buffer_structures))
                id_map = self.build_id_map_chunked(unique_structures)

                structures_a_inserer = []
                for siret, finess, id_tech in unique_structures:
                    key = siret or finess or id_tech
                    if key not in id_map:
                        structures_a_inserer.append((siret, finess, id_tech))

                if structures_a_inserer:
                    logger.debug(f"  → Insertion de {len(structures_a_inserer):,} structures...")
                    self.cursor.executemany("""
                        INSERT INTO structures (siret, finess, identifiant_technique, date_import)
                        VALUES (:1, :2, :3, SYSDATE)
                    """, structures_a_inserer)
                    stats['structures'] += len(structures_a_inserer)

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
                        logger.debug(f"  → Insertion de {len(activites_with_ids):,} activités...")
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

            # Vider les buffers
            self.professionnels_map = {}
            self.buffer_structures = []
            self.buffer_activites = []
            self.buffer_adresses = []
            self.buffer_contacts = []

            # COMMIT
            self.conn.commit()
            self.retry_count_undo = 0

        except oracledb.DatabaseError as e:
            error_code = e.args[0].code if hasattr(e.args[0], 'code') else 0

            if error_code == 30036:
                self.retry_count_undo += 1

                if self.retry_count_undo <= CONFIG['max_retry_undo']:
                    old_size = self.current_batch_size
                    self.current_batch_size = max(
                        CONFIG['batch_size_min'],
                        self.current_batch_size // 2
                    )

                    logger.warning(
                        f"⚠️  ORA-30036 : Réduction batch {old_size} → {self.current_batch_size} "
                        f"(tentative {self.retry_count_undo}/{CONFIG['max_retry_undo']})"
                    )

                    self.conn.rollback()
                    return
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
    logger.info("🚀 EXTRACTEUR RPPS v4.0 - INSERT OPTIMISÉ")
    logger.info("="*70)
    logger.info(f"📁 Fichier : {CONFIG['fichier_rpps']}")
    logger.info(f"📦 Batch size : {CONFIG['batch_size']:,}")

    start_time = datetime.now()

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

    conn = init_oracle()
    logger.info("✅ Connexion Oracle établie")

    logger.info("🧹 Nettoyage des tables...")
    cursor = conn.cursor()
    for table in ['contacts', 'adresses', 'activites', 'structures', 'professionnels']:
        cursor.execute(f"TRUNCATE TABLE {table}")
    conn.commit()
    logger.info("✅ Tables vidées")

    cursor.execute("""
        INSERT INTO import_logs (script_execute, date_debut, date_import, statut)
        VALUES (:1, SYSDATE, SYSDATE, 'En cours')
    """, [CONFIG['fichier_rpps']])
    conn.commit()
    cursor.execute("SELECT MAX(id_log) FROM import_logs")
    id_log = cursor.fetchone()[0]

    extractor = RPPSExtractor(CONFIG['fichier_rpps'])
    loader = OracleLoaderInsertOnly(conn)

    logger.info("🚀 Démarrage extraction...")

    try:
        for record in extractor.extract():
            loader.add_record(record)
            stats['lignes_lues'] = extractor.stats['lignes_lues']

            if loader.should_flush():
                loader.flush(stats)

                if stats['lignes_lues'] % CONFIG['progress_interval'] == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    vitesse = stats['lignes_lues'] / elapsed if elapsed > 0 else 0

                    logger.info(
                        f"  📊 {stats['lignes_lues']:>10,} lignes | "
                        f"👤 {stats['professionnels']:>10,} pros | "
                        f"📝 {stats['activites']:>10,} activités | "
                        f"🚀 {vitesse:>6,.0f} l/s"
                    )

        logger.info("🔄 Flush final...")
        loader.flush(stats)

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

        duration = (datetime.now() - start_time).total_seconds()
        cursor.execute("""
            UPDATE import_logs SET statut='Terminé', date_fin=SYSDATE,
            nb_lignes_traitees=:1, nb_lignes_inserees=:2, nb_erreurs=:3,
            duree_secondes=:4 WHERE id_log=:5
        """, [stats['lignes_lues'], stats['professionnels'], stats['erreurs'], int(duration), id_log])
        conn.commit()

        # Vérification finale
        cursor.execute("SELECT COUNT(*) FROM professionnels")
        nb_pros_final = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM activites")
        nb_act_final = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM structures")
        nb_struct_final = cursor.fetchone()[0]

        print("\n" + "="*70)
        print("✅ IMPORT TERMINÉ AVEC SUCCÈS")
        print("="*70)
        print(f"⏱️  Durée             : {duration/60:.1f} minutes")
        print(f"🚀 Vitesse moyenne    : {stats['lignes_lues']/duration:,.0f} l/s")
        print("="*70)
        print(f"📊 Lignes lues        : {stats['lignes_lues']:>12,}")
        print(f"👤 Professionnels     : {nb_pros_final:>12,}")
        print(f"🏢 Structures         : {nb_struct_final:>12,}")
        print(f"📝 Activités          : {nb_act_final:>12,}")
        print(f"🏠 Adresses           : {stats['adresses']:>12,}")
        print(f"📞 Contacts           : {stats['contacts']:>12,}")
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
