"""
Oracle Loader - Insertion des données dans Oracle DB
"""
import oracledb
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

from utils import (
    get_logger,
    calculate_professionnel_hash,
    get_region_from_departement
)


class OracleLoader:
    """Chargeur de données vers Oracle"""
    
    def __init__(self, db_config: Dict):
        """
        Initialise le loader
        
        Args:
            db_config: Configuration connexion (user, password, dsn, wallet_path)
        """
        self.logger = get_logger("oracle_loader")
        self.db_config = db_config
        self.connection = None
        self.batch_size = 1000
        
        # Statistiques
        self.stats = {
            'professionnels_inserted': 0,
            'professionnels_updated': 0,
            'activites_inserted': 0,
            'structures_inserted': 0,
            'adresses_inserted': 0,
            'contacts_inserted': 0,
            'qualifications_inserted': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Buffers pour batch insert
        self.buffers = {
            'professionnels': [],
            'activites': [],
            'structures': [],
            'adresses': [],
            'contacts': [],
            'qualifications': []
        }
    
    @contextmanager
    def get_connection(self):
        """Context manager pour connexion Oracle"""
        try:
            self.logger.info("Connexion à Oracle...")
            
            conn = oracledb.connect(
                user=self.db_config['user'],
                password=self.db_config['password'],
                dsn=self.db_config['dsn'],
                config_dir=self.db_config.get('wallet_path'),
                wallet_location=self.db_config.get('wallet_path')
            )
            
            self.logger.info("Connexion établie")
            yield conn
            
        except oracledb.Error as e:
            self.logger.error(f"Erreur connexion Oracle: {e}")
            raise
        finally:
            if conn:
                conn.close()
                self.logger.info("Connexion fermée")
    
    def load_data(self, records: List[Dict]):
        """
        Charge les données dans Oracle
        
        Args:
            records: Liste de dictionnaires (données nettoyées)
        """
        self.stats['start_time'] = datetime.now()
        self.logger.info(f"Début chargement de {len(records)} enregistrements")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Log début d'import
                log_id = self._log_import_start(cursor, len(records))
                
                # Traitement par batch
                for i, record in enumerate(records, 1):
                    try:
                        self._process_record(cursor, record)
                        
                        # Commit tous les batch_size enregistrements
                        if i % self.batch_size == 0:
                            self._flush_buffers(cursor)
                            conn.commit()
                            self.logger.info(f"Progression: {i}/{len(records)} enregistrements")
                    
                    except Exception as e:
                        self.stats['errors'] += 1
                        self.logger.error(f"Erreur enregistrement {record.get('id_professionnel')}: {e}")
                        continue
                
                # Dernier commit
                self._flush_buffers(cursor)
                conn.commit()
                
                # Log fin d'import
                self._log_import_end(cursor, log_id, 'SUCCESS')
                conn.commit()
                
                self.stats['end_time'] = datetime.now()
                duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
                
                self.logger.info(f"Chargement terminé en {duration:.1f}s")
                self.logger.info(f"Stats: {self.stats}")
                
            except Exception as e:
                self.logger.error(f"Erreur critique: {e}")
                conn.rollback()
                raise
    
    def _process_record(self, cursor, record: Dict):
        """Traite un enregistrement (ajoute aux buffers)"""
        
        # 1. Professionnel
        prof_data = self._prepare_professionnel(record)
        self.buffers['professionnels'].append(prof_data)
        
        # 2. Activité
        if record.get('mode_exercice'):
            act_data = self._prepare_activite(record)
            self.buffers['activites'].append(act_data)
        
        # 3. Structure (si SIRET présent)
        if record.get('siret'):
            struct_data = self._prepare_structure(record)
            self.buffers['structures'].append(struct_data)
        
        # 4. Adresse
        if record.get('code_postal'):
            addr_data = self._prepare_adresse(record)
            self.buffers['adresses'].append(addr_data)
        
        # 5. Contacts
        contacts_data = self._prepare_contacts(record)
        self.buffers['contacts'].extend(contacts_data)
    
    def _prepare_professionnel(self, record: Dict) -> tuple:
        """Prépare les données pour table PROFESSIONNELS"""
        
        # Calcul hash
        hash_data = calculate_professionnel_hash(
            record.get('nom', ''),
            record.get('prenom', ''),
            record.get('code_profession', ''),
            'Actif'
        )
        
        return (
            record.get('id_professionnel'),
            record.get('nom'),
            record.get('prenom'),
            record.get('nom'),  # nom_exercice = nom
            record.get('civilite'),
            record.get('code_profession'),
            record.get('libelle_profession'),
            record.get('categorie_profession'),
            None,  # date_naissance
            'Actif',  # statut_enregistrement
            hash_data
        )
    
    def _prepare_activite(self, record: Dict) -> tuple:
        """Prépare les données pour table ACTIVITES"""
        
        # Détermine statut activité
        date_fin = record.get('date_fin_activite')
        statut = 'Cessé' if date_fin else 'Actif'
        
        return (
            record.get('id_professionnel'),
            record.get('code_savoir_faire'),
            record.get('libelle_savoir_faire'),
            record.get('mode_exercice'),
            record.get('secteur_activite'),
            self._parse_date(record.get('date_debut_activite')),
            self._parse_date(date_fin),
            statut,
            None  # id_structure (FK à gérer séparément)
        )
    
    def _prepare_structure(self, record: Dict) -> tuple:
        """Prépare les données pour table STRUCTURES"""
        
        siret = record.get('siret')
        siren = siret[:9] if siret and len(siret) >= 9 else record.get('siren')
        
        return (
            siret,
            record.get('finess'),
            record.get('raison_sociale'),
            record.get('enseigne_commerciale'),
            None,  # type_structure
            None,  # statut_juridique
            None,  # date_creation
            None   # date_fermeture
        )
    
    def _prepare_adresse(self, record: Dict) -> tuple:
        """Prépare les données pour table ADRESSES"""
        
        departement = record.get('departement', '')[:2]
        region = get_region_from_departement(departement)
        
        return (
            record.get('id_professionnel'),
            None,  # id_structure (FK à gérer)
            'Exercice',  # type_adresse
            record.get('numero_voie'),
            record.get('type_voie'),
            record.get('libelle_voie'),
            record.get('complement_adresse'),
            record.get('code_postal'),
            record.get('commune'),
            record.get('code_commune_insee'),
            departement,
            region,
            record.get('pays') or 'France',
            None,  # latitude
            None   # longitude
        )
    
    def _prepare_contacts(self, record: Dict) -> List[tuple]:
        """Prépare les données pour table CONTACTS"""
        contacts = []
        
        # Téléphone 1
        if record.get('telephone_1'):
            contacts.append((
                record.get('id_professionnel'),
                None,  # id_structure
                'TELEPHONE',
                record.get('telephone_1'),
                'Pro',
                80,  # priorité
                'A_Verifier',
                'RPPS'
            ))
        
        # Téléphone 2
        if record.get('telephone_2'):
            contacts.append((
                record.get('id_professionnel'),
                None,
                'TELEPHONE',
                record.get('telephone_2'),
                'Pro',
                70,
                'A_Verifier',
                'RPPS'
            ))
        
        # Email
        if record.get('email'):
            contacts.append((
                record.get('id_professionnel'),
                None,
                'EMAIL',
                record.get('email'),
                'Pro',
                90,
                'A_Verifier',
                'RPPS'
            ))
        
        # Fax
        if record.get('fax'):
            contacts.append((
                record.get('id_professionnel'),
                None,
                'FAX',
                record.get('fax'),
                'Pro',
                50,
                'A_Verifier',
                'RPPS'
            ))
        
        return contacts
    
    def _flush_buffers(self, cursor):
        """Vide les buffers vers la base"""
        
        # PROFESSIONNELS - MERGE (upsert)
        if self.buffers['professionnels']:
            sql = """
            MERGE INTO professionnels p
            USING (SELECT :1 AS id_professionnel, :2 AS nom, :3 AS prenom, :4 AS nom_exercice,
                          :5 AS civilite, :6 AS code_profession, :7 AS libelle_profession,
                          :8 AS categorie_profession, :9 AS date_naissance,
                          :10 AS statut_enregistrement, :11 AS hash_data FROM DUAL) src
            ON (p.id_professionnel = src.id_professionnel)
            WHEN MATCHED THEN
                UPDATE SET p.nom = src.nom, p.prenom = src.prenom,
                          p.code_profession = src.code_profession,
                          p.libelle_profession = src.libelle_profession,
                          p.categorie_profession = src.categorie_profession,
                          p.hash_data = src.hash_data,
                          p.date_derniere_maj = SYSDATE
            WHEN NOT MATCHED THEN
                INSERT (id_professionnel, nom, prenom, nom_exercice, civilite,
                       code_profession, libelle_profession, categorie_profession,
                       date_naissance, statut_enregistrement, hash_data)
                VALUES (src.id_professionnel, src.nom, src.prenom, src.nom_exercice,
                       src.civilite, src.code_profession, src.libelle_profession,
                       src.categorie_profession, src.date_naissance,
                       src.statut_enregistrement, src.hash_data)
            """
            cursor.executemany(sql, self.buffers['professionnels'])
            self.stats['professionnels_inserted'] += len(self.buffers['professionnels'])
            self.buffers['professionnels'] = []
        
        # ACTIVITES
        if self.buffers['activites']:
            sql = """
            INSERT INTO activites (id_professionnel, code_savoir_faire, libelle_savoir_faire,
                                  mode_exercice, secteur_activite, date_debut_activite,
                                  date_fin_activite, statut_activite, id_structure)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)
            """
            cursor.executemany(sql, self.buffers['activites'])
            self.stats['activites_inserted'] += len(self.buffers['activites'])
            self.buffers['activites'] = []
        
        # ADRESSES
        if self.buffers['adresses']:
            sql = """
            INSERT INTO adresses (id_professionnel, id_structure, type_adresse,
                                 numero_voie, type_voie, libelle_voie, complement_adresse,
                                 code_postal, commune, code_commune_insee, departement,
                                 region, pays, latitude, longitude)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15)
            """
            cursor.executemany(sql, self.buffers['adresses'])
            self.stats['adresses_inserted'] += len(self.buffers['adresses'])
            self.buffers['adresses'] = []
        
        # CONTACTS
        if self.buffers['contacts']:
            sql = """
            INSERT INTO contacts (id_professionnel, id_structure, type_contact,
                                 valeur, categorie, priorite, statut_validation,
                                 source_origine)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
            """
            cursor.executemany(sql, self.buffers['contacts'])
            self.stats['contacts_inserted'] += len(self.buffers['contacts'])
            self.buffers['contacts'] = []
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse une date string vers format Oracle"""
        if not date_str:
            return None
        
        # Format attendu : YYYYMMDD ou DD/MM/YYYY
        try:
            if len(date_str) == 8 and date_str.isdigit():
                # YYYYMMDD
                return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
            else:
                return date_str
        except:
            return None
    
    def _log_import_start(self, cursor, nb_records: int) -> int:
        """Log début d'import"""
        sql = """
        INSERT INTO import_logs (type_import, script_execute, statut,
                                nb_lignes_traitees, date_debut, message_log)
        VALUES ('RPPS_INITIAL', 'load_initial_data', 'RUNNING',
                :nb_records, SYSTIMESTAMP, 'Import RPPS démarré')
        RETURNING id_log INTO :log_id
        """
        log_id = cursor.var(int)
        cursor.execute(sql, nb_records=nb_records, log_id=log_id)
        return log_id.getvalue()[0]
    
    def _log_import_end(self, cursor, log_id: int, statut: str):
        """Log fin d'import"""
        sql = """
        UPDATE import_logs
        SET statut = :statut,
            date_fin = SYSTIMESTAMP,
            nb_lignes_inserees = :inserted,
            nb_lignes_mises_a_jour = :updated,
            nb_erreurs = :errors,
            message_log = :message
        WHERE id_log = :log_id
        """
        message = f"Import terminé - {self.stats['professionnels_inserted']} pros, {self.stats['contacts_inserted']} contacts"
        
        cursor.execute(sql,
                      statut=statut,
                      inserted=self.stats['professionnels_inserted'],
                      updated=self.stats['professionnels_updated'],
                      errors=self.stats['errors'],
                      message=message,
                      log_id=log_id)
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques"""
        return self.stats.copy()
