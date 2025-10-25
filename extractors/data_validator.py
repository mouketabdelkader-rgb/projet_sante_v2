"""
Validateur de données RPPS
Applique les règles métier et validations
"""
from typing import Dict, List, Optional
from dataclasses import dataclass

from utils import (
    validate_rpps_id,
    validate_telephone,
    validate_email,
    validate_code_postal,
    get_logger
)


@dataclass
class ValidationResult:
    """Résultat de validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_data: Optional[Dict] = None


class DataValidator:
    """Validateur de données avec règles métier"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le validateur
        
        Args:
            config: Configuration optionnelle (professions cibles, etc.)
        """
        self.logger = get_logger("data_validator")
        self.config = config or {}
        
        # Professions cibles par défaut
        self.professions_cibles = self.config.get('professions_cibles', [
            '10',  # Médecin
            '21',  # Pharmacien
            '50',  # Sage-Femme
            '60',  # Infirmier
            '70',  # Masseur-Kinésithérapeute
            '80',  # Pédicure-Podologue
            '91',  # Ergothérapeute
            '94',  # Orthophoniste
        ])
        
        # Modes d'exercice prioritaires
        self.modes_prioritaires = ['Lib', 'indép', 'artis']
        
        self.stats = {
            'validated': 0,
            'rejected': 0,
            'warnings': 0
        }
    
    def validate_professionnel(self, data: Dict) -> ValidationResult:
        """
        Valide un professionnel complet
        
        Args:
            data: Dictionnaire avec toutes les données
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        cleaned = {}
        
        # 1. RPPS obligatoire et valide
        rpps_id = data.get('id_professionnel', '')
        if not validate_rpps_id(rpps_id):
            errors.append(f"RPPS invalide: {rpps_id}")
        else:
            cleaned['id_professionnel'] = rpps_id.strip()
        
        # 2. Code profession valide
        code_prof = data.get('code_profession', '').strip()
        if not code_prof:
            errors.append("Code profession manquant")
        elif code_prof not in self.professions_cibles:
            warnings.append(f"Profession hors cible: {code_prof}")
        else:
            cleaned['code_profession'] = code_prof
        
        # 3. Nom/Prénom présents
        nom = data.get('nom', '').strip()
        prenom = data.get('prenom', '').strip()
        
        if not nom:
            errors.append("Nom manquant")
        else:
            cleaned['nom'] = nom
        
        if prenom:
            cleaned['prenom'] = prenom
        else:
            warnings.append("Prénom manquant")
        
        # 4. Code postal valide (si présent)
        code_postal = data.get('code_postal', '').strip()
        if code_postal:
            if not validate_code_postal(code_postal, exclude_domtom=True):
                warnings.append(f"Code postal invalide ou DOM-TOM: {code_postal}")
            else:
                cleaned['code_postal'] = code_postal
        
        # 5. Validation téléphones
        tel1 = data.get('telephone_1', '').strip()
        if tel1:
            is_valid, clean_tel = validate_telephone(tel1)
            if is_valid:
                cleaned['telephone_1'] = clean_tel
            else:
                warnings.append(f"Téléphone 1 invalide: {tel1}")
        
        tel2 = data.get('telephone_2', '').strip()
        if tel2:
            is_valid, clean_tel = validate_telephone(tel2)
            if is_valid:
                cleaned['telephone_2'] = clean_tel
            else:
                warnings.append(f"Téléphone 2 invalide: {tel2}")
        
        # 6. Validation email
        email = data.get('email', '').strip()
        if email:
            if validate_email(email):
                cleaned['email'] = email.lower()
            else:
                warnings.append(f"Email invalide: {email}")
        
        # 7. Mode exercice (prioriser libéral)
        mode_exercice = data.get('mode_exercice', '').strip()
        if mode_exercice:
            cleaned['mode_exercice'] = mode_exercice
            # Check si libéral
            is_liberal = any(keyword in mode_exercice for keyword in self.modes_prioritaires)
            cleaned['is_liberal'] = is_liberal
        
        # Déterminer validité globale
        is_valid = len(errors) == 0
        
        # Stats
        if is_valid:
            self.stats['validated'] += 1
        else:
            self.stats['rejected'] += 1
        
        if warnings:
            self.stats['warnings'] += 1
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned if is_valid else None
        )
    
    def is_priority_contact(self, data: Dict) -> bool:
        """
        Détermine si un professionnel est prioritaire
        
        Args:
            data: Données du professionnel
            
        Returns:
            True si prioritaire
        """
        # Prioritaire si :
        # 1. Libéral
        # 2. A au moins un contact (tel ou email)
        # 3. Code postal valide (France métropolitaine)
        
        mode = data.get('mode_exercice', '')
        is_liberal = any(kw in mode for kw in self.modes_prioritaires)
        
        has_contact = bool(data.get('telephone_1') or 
                          data.get('telephone_2') or 
                          data.get('email'))
        
        code_postal = data.get('code_postal', '')
        valid_location = validate_code_postal(code_postal, exclude_domtom=True)
        
        return is_liberal and has_contact and valid_location
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques de validation"""
        return self.stats.copy()
