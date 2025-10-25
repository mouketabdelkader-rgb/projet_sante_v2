"""
Extracteur de données RPPS
Lit et parse le fichier RPPS avec validation
"""
import csv
from pathlib import Path
from typing import Generator, Dict, Any, Optional
from dataclasses import dataclass
import yaml

from utils import get_logger, validate_rpps_id, safe_get_column


@dataclass
class RPPSRecord:
    """Enregistrement RPPS parsé et validé"""
    # Professionnel
    id_professionnel: str
    nom: Optional[str]
    prenom: Optional[str]
    civilite: Optional[str]
    code_profession: Optional[str]
    libelle_profession: Optional[str]
    categorie_profession: Optional[str]
    
    # Activité
    code_savoir_faire: Optional[str]
    libelle_savoir_faire: Optional[str]
    mode_exercice: Optional[str]
    code_mode_exercice: Optional[str]
    secteur_activite: Optional[str]
    date_debut_activite: Optional[str]
    date_fin_activite: Optional[str]
    
    # Structure
    siret: Optional[str]
    siren: Optional[str]
    finess: Optional[str]
    raison_sociale: Optional[str]
    enseigne_commerciale: Optional[str]
    
    # Adresse
    numero_voie: Optional[str]
    type_voie: Optional[str]
    libelle_voie: Optional[str]
    complement_adresse: Optional[str]
    code_postal: Optional[str]
    commune: Optional[str]
    code_commune_insee: Optional[str]
    departement: Optional[str]
    pays: Optional[str]
    
    # Contacts
    telephone_1: Optional[str]
    telephone_2: Optional[str]
    fax: Optional[str]
    email: Optional[str]
    
    # Métadonnées
    raw_line_number: int
    is_valid: bool = True
    validation_errors: list = None


class RPPSExtractor:
    """Extracteur de fichiers RPPS"""
    
    def __init__(self, mapping_file: str = "./config/mapping_rpps.yaml"):
        """
        Initialise l'extracteur
        
        Args:
            mapping_file: Chemin vers le fichier de mapping YAML
        """
        self.logger = get_logger("rpps_extractor")
        self.mapping = self._load_mapping(mapping_file)
        self.stats = {
            'total_lines': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'errors': []
        }
        
    def _load_mapping(self, mapping_file: str) -> Dict:
        """Charge le mapping depuis le fichier YAML"""
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = yaml.safe_load(f)
            self.logger.info(f"Mapping RPPS chargé depuis {mapping_file}")
            return mapping
        except Exception as e:
            self.logger.error(f"Erreur chargement mapping: {e}")
            raise
    
    def extract_records(self, file_path: str, 
                       max_records: Optional[int] = None) -> Generator[RPPSRecord, None, None]:
        """
        Extrait les enregistrements du fichier RPPS
        
        Args:
            file_path: Chemin vers le fichier RPPS
            max_records: Nombre max d'enregistrements (None = tous)
            
        Yields:
            RPPSRecord parsé et validé
        """
        self.logger.info(f"Début extraction: {file_path}")
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Fichier introuvable: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='|')
            
            # Skip header
            next(reader, None)
            
            for line_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                self.stats['total_lines'] += 1
                
                # Limite si spécifiée
                if max_records and self.stats['valid_records'] >= max_records:
                    self.logger.info(f"Limite de {max_records} enregistrements atteinte")
                    break
                
                # Validation nombre de colonnes
                if len(row) != 57:
                    self.stats['invalid_records'] += 1
                    error_msg = f"Ligne {line_num}: {len(row)} colonnes au lieu de 57"
                    self.logger.warning(error_msg)
                    self.stats['errors'].append(error_msg)
                    continue
                
                # Parse l'enregistrement
                try:
                    record = self._parse_row(row, line_num)
                    
                    if record.is_valid:
                        self.stats['valid_records'] += 1
                        yield record
                    else:
                        self.stats['invalid_records'] += 1
                        
                except Exception as e:
                    self.stats['invalid_records'] += 1
                    error_msg = f"Ligne {line_num}: Erreur parsing - {str(e)}"
                    self.logger.error(error_msg)
                    self.stats['errors'].append(error_msg)
                    continue
                
                # Log progression tous les 10000 enregistrements
                if self.stats['total_lines'] % 10000 == 0:
                    self.logger.info(
                        f"Progression: {self.stats['total_lines']} lignes traitées, "
                        f"{self.stats['valid_records']} valides"
                    )
        
        # Stats finales
        self.logger.info(
            f"Extraction terminée - Total: {self.stats['total_lines']}, "
            f"Valides: {self.stats['valid_records']}, "
            f"Invalides: {self.stats['invalid_records']}"
        )
    
    def _parse_row(self, row: list, line_num: int) -> RPPSRecord:
        """
        Parse une ligne en RPPSRecord
        
        Args:
            row: Liste des colonnes
            line_num: Numéro de ligne (pour debug)
            
        Returns:
            RPPSRecord
        """
        # Mapping des indices (depuis YAML)
        mapping_prof = self.mapping['mapping_professionnels']
        mapping_act = self.mapping['mapping_activites']
        mapping_struct = self.mapping['mapping_structures']
        mapping_addr = self.mapping['mapping_adresses']
        mapping_contact = self.mapping['mapping_contacts']
        
        # Extraction des données
        id_prof = safe_get_column(row, mapping_prof['id_professionnel'])
        
        # Validation RPPS
        validation_errors = []
        is_valid = True
        
        if not validate_rpps_id(id_prof):
            validation_errors.append(f"RPPS invalide: {id_prof}")
            is_valid = False
        
        # Construction du record
        record = RPPSRecord(
            # Professionnel
            id_professionnel=id_prof,
            nom=safe_get_column(row, mapping_prof['nom']),
            prenom=safe_get_column(row, mapping_prof['prenom']),
            civilite=safe_get_column(row, mapping_prof['civilite']),
            code_profession=safe_get_column(row, mapping_prof['code_profession']),
            libelle_profession=safe_get_column(row, mapping_prof['libelle_profession']),
            categorie_profession=safe_get_column(row, mapping_prof['categorie_profession']),
            
            # Activité
            code_savoir_faire=safe_get_column(row, mapping_act['code_savoir_faire']),
            libelle_savoir_faire=safe_get_column(row, mapping_act['libelle_savoir_faire']),
            mode_exercice=safe_get_column(row, mapping_act['mode_exercice']),
            code_mode_exercice=safe_get_column(row, self.mapping['colonnes_rpps'][17]),
            secteur_activite=safe_get_column(row, mapping_act['secteur_activite']),
            date_debut_activite=safe_get_column(row, mapping_act['date_debut_activite']),
            date_fin_activite=safe_get_column(row, mapping_act['date_fin_activite']),
            
            # Structure
            siret=safe_get_column(row, mapping_struct['siret']),
            siren=safe_get_column(row, self.mapping['colonnes_rpps'][20]),
            finess=safe_get_column(row, mapping_struct['finess']),
            raison_sociale=safe_get_column(row, mapping_struct['raison_sociale']),
            enseigne_commerciale=safe_get_column(row, mapping_struct['enseigne_commerciale']),
            
            # Adresse
            numero_voie=safe_get_column(row, mapping_addr['numero_voie']),
            type_voie=safe_get_column(row, mapping_addr['type_voie']),
            libelle_voie=safe_get_column(row, mapping_addr['libelle_voie']),
            complement_adresse=safe_get_column(row, mapping_addr['complement_adresse']),
            code_postal=safe_get_column(row, mapping_addr['code_postal']),
            commune=safe_get_column(row, mapping_addr['commune']),
            code_commune_insee=safe_get_column(row, mapping_addr['code_commune_insee']),
            departement=safe_get_column(row, self.mapping['colonnes_rpps'][44]),
            pays=safe_get_column(row, mapping_addr['pays']) or 'France',
            
            # Contacts
            telephone_1=safe_get_column(row, mapping_contact['telephone_1']['valeur']),
            telephone_2=safe_get_column(row, mapping_contact['telephone_2']['valeur']),
            fax=safe_get_column(row, mapping_contact['fax']['valeur']),
            email=safe_get_column(row, mapping_contact['email']['valeur']),
            
            # Métadonnées
            raw_line_number=line_num,
            is_valid=is_valid,
            validation_errors=validation_errors if validation_errors else None
        )
        
        return record
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'extraction"""
        return self.stats.copy()
