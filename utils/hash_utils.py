"""
Utilitaires pour calcul hash et validations
"""
import hashlib
import re
from typing import Optional


def calculate_hash(data: str) -> str:
    """
    Calcule un hash SHA256 d'une chaîne
    
    Args:
        data: Chaîne à hasher
        
    Returns:
        Hash hexadécimal
    """
    if not data:
        return ""
    
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def calculate_professionnel_hash(nom: str, prenom: str, 
                                  code_profession: str, 
                                  statut: str = "Actif") -> str:
    """
    Calcule le hash d'un professionnel pour détection changements
    
    Args:
        nom: Nom du professionnel
        prenom: Prénom
        code_profession: Code profession
        statut: Statut enregistrement
        
    Returns:
        Hash SHA256
    """
    concat_string = f"{nom.strip().upper()}|{prenom.strip().upper() if prenom else ''}|{code_profession.strip()}|{statut.strip()}"
    return calculate_hash(concat_string)


def validate_rpps_id(rpps_id: str) -> bool:
    """
    Valide un identifiant RPPS (11 chiffres)
    
    Args:
        rpps_id: Identifiant à valider
        
    Returns:
        True si valide
    """
    if not rpps_id:
        return False
    
    pattern = r'^\d{11}$'
    return bool(re.match(pattern, rpps_id.strip()))


def validate_telephone(telephone: str) -> tuple[bool, Optional[str]]:
    """
    Valide et nettoie un numéro de téléphone français
    
    Args:
        telephone: Numéro à valider
        
    Returns:
        Tuple (est_valide, numero_nettoye)
    """
    if not telephone:
        return False, None
    
    # Retire espaces, points, tirets, parenthèses
    clean = re.sub(r'[^\d+]', '', telephone.strip())
    
    # Remplace 0033 par +33
    clean = re.sub(r'^0033', '+33', clean)
    
    # Remplace 33 par +33 si pas de +
    if clean.startswith('33') and not clean.startswith('+'):
        clean = '+' + clean
    
    # Valide format : 0XXXXXXXXX ou +33XXXXXXXXX
    pattern = r'^(0|\+33)\d{9}$'
    is_valid = bool(re.match(pattern, clean))
    
    return is_valid, clean if is_valid else None


def validate_email(email: str) -> bool:
    """
    Valide un email
    
    Args:
        email: Email à valider
        
    Returns:
        True si valide
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip().lower()))


def validate_code_postal(code_postal: str, exclude_domtom: bool = True) -> bool:
    """
    Valide un code postal français
    
    Args:
        code_postal: Code postal à valider
        exclude_domtom: Si True, exclut DOM-TOM
        
    Returns:
        True si valide
    """
    if not code_postal:
        return False
    
    clean = code_postal.strip()
    
    # Doit être 5 chiffres
    if not re.match(r'^\d{5}$', clean):
        return False
    
    # Exclusion DOM-TOM
    if exclude_domtom and (clean.startswith('97') or clean.startswith('98')):
        return False
    
    return True


def clean_string(value: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
    """
    Nettoie une chaîne : trim, None si vide
    
    Args:
        value: Valeur à nettoyer
        max_length: Longueur max (troncature)
        
    Returns:
        Chaîne nettoyée ou None
    """
    if not value:
        return None
    
    cleaned = value.strip()
    
    if not cleaned:
        return None
    
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned


def safe_get_column(row: list, index: int, default: str = "") -> str:
    """
    Récupère une colonne d'une liste de manière sécurisée
    
    Args:
        row: Liste (ligne CSV)
        index: Index de la colonne
        default: Valeur par défaut si index invalide
        
    Returns:
        Valeur nettoyée ou défaut
    """
    try:
        if index < 0 or index >= len(row):
            return default
        
        value = row[index]
        return clean_string(value) or default
    except:
        return default


def get_region_from_departement(departement: str) -> Optional[str]:
    """
    Déduit la région à partir du département
    
    Args:
        departement: Code département (2 ou 3 caractères)
        
    Returns:
        Nom de la région ou None
    """
    mapping = {
        # Île-de-France
        "75": "Île-de-France", "77": "Île-de-France", "78": "Île-de-France",
        "91": "Île-de-France", "92": "Île-de-France", "93": "Île-de-France",
        "94": "Île-de-France", "95": "Île-de-France",
        
        # Provence-Alpes-Côte d'Azur
        "04": "Provence-Alpes-Côte d'Azur", "05": "Provence-Alpes-Côte d'Azur",
        "06": "Provence-Alpes-Côte d'Azur", "13": "Provence-Alpes-Côte d'Azur",
        "83": "Provence-Alpes-Côte d'Azur", "84": "Provence-Alpes-Côte d'Azur",
        
        # Auvergne-Rhône-Alpes
        "01": "Auvergne-Rhône-Alpes", "03": "Auvergne-Rhône-Alpes", 
        "07": "Auvergne-Rhône-Alpes", "15": "Auvergne-Rhône-Alpes",
        "26": "Auvergne-Rhône-Alpes", "38": "Auvergne-Rhône-Alpes",
        "42": "Auvergne-Rhône-Alpes", "43": "Auvergne-Rhône-Alpes",
        "63": "Auvergne-Rhône-Alpes", "69": "Auvergne-Rhône-Alpes",
        "73": "Auvergne-Rhône-Alpes", "74": "Auvergne-Rhône-Alpes",
        
        # Nouvelle-Aquitaine
        "16": "Nouvelle-Aquitaine", "17": "Nouvelle-Aquitaine",
        "19": "Nouvelle-Aquitaine", "23": "Nouvelle-Aquitaine",
        "24": "Nouvelle-Aquitaine", "33": "Nouvelle-Aquitaine",
        "40": "Nouvelle-Aquitaine", "47": "Nouvelle-Aquitaine",
        "64": "Nouvelle-Aquitaine", "79": "Nouvelle-Aquitaine",
        "86": "Nouvelle-Aquitaine", "87": "Nouvelle-Aquitaine",
        
        # Occitanie
        "09": "Occitanie", "11": "Occitanie", "12": "Occitanie",
        "30": "Occitanie", "31": "Occitanie", "32": "Occitanie",
        "34": "Occitanie", "46": "Occitanie", "48": "Occitanie",
        "65": "Occitanie", "66": "Occitanie", "81": "Occitanie",
        "82": "Occitanie",
        
        # Hauts-de-France
        "02": "Hauts-de-France", "59": "Hauts-de-France",
        "60": "Hauts-de-France", "62": "Hauts-de-France",
        "80": "Hauts-de-France",
        
        # Grand Est
        "08": "Grand Est", "10": "Grand Est", "51": "Grand Est",
        "52": "Grand Est", "54": "Grand Est", "55": "Grand Est",
        "57": "Grand Est", "67": "Grand Est", "68": "Grand Est",
        "88": "Grand Est",
        
        # Pays de la Loire
        "44": "Pays de la Loire", "49": "Pays de la Loire",
        "53": "Pays de la Loire", "72": "Pays de la Loire",
        "85": "Pays de la Loire",
        
        # Bretagne
        "22": "Bretagne", "29": "Bretagne", "35": "Bretagne",
        "56": "Bretagne",
        
        # Normandie
        "14": "Normandie", "27": "Normandie", "50": "Normandie",
        "61": "Normandie", "76": "Normandie",
        
        # Bourgogne-Franche-Comté
        "21": "Bourgogne-Franche-Comté", "25": "Bourgogne-Franche-Comté",
        "39": "Bourgogne-Franche-Comté", "58": "Bourgogne-Franche-Comté",
        "70": "Bourgogne-Franche-Comté", "71": "Bourgogne-Franche-Comté",
        "89": "Bourgogne-Franche-Comté", "90": "Bourgogne-Franche-Comté",
        
        # Centre-Val de Loire
        "18": "Centre-Val de Loire", "28": "Centre-Val de Loire",
        "36": "Centre-Val de Loire", "37": "Centre-Val de Loire",
        "41": "Centre-Val de Loire", "45": "Centre-Val de Loire",
    }
    
    if not departement:
        return None
    
    return mapping.get(departement.strip()[:2])
