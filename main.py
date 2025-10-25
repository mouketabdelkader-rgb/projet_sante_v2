#!/usr/bin/env python3
"""
Script principal - Chargement initial RPPS vers Oracle
Orchestration complète : extraction, validation, chargement
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import yaml
from dotenv import load_dotenv
import os

# Ajoute le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from extractors import RPPSExtractor, DataValidator
from loaders import OracleLoader
from utils import get_logger


def load_config(config_path: str = "./config/config.yaml") -> dict:
    """Charge la configuration depuis YAML"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Remplace les variables d'environnement
    config['database']['user'] = os.getenv('DB_USER', config['database']['user'])
    config['database']['password'] = os.getenv('DB_PASSWORD', config['database']['password'])
    config['database']['dsn'] = os.getenv('DB_DSN', config['database']['dsn'])
    config['database']['wallet_path'] = os.getenv('WALLET_PATH', config['database']['wallet_path'])
    
    return config


def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description='Chargement initial données RPPS vers Oracle'
    )
    parser.add_argument(
        'rpps_file',
        help='Chemin vers le fichier RPPS (PS_LibreAcces_...txt)'
    )
    parser.add_argument(
        '--config',
        default='./config/config.yaml',
        help='Fichier de configuration YAML (défaut: ./config/config.yaml)'
    )
    parser.add_argument(
        '--max-records',
        type=int,
        default=None,
        help='Nombre max d\'enregistrements à traiter (pour tests)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mode test : extraction et validation sans insertion BDD'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Niveau de log'
    )
    
    args = parser.parse_args()
    
    # Charge variables d'environnement
    load_dotenv()
    
    # Initialise le logger
    logger = get_logger("main", level=getattr(__import__('logging'), args.log_level))
    
    logger.info("="*60)
    logger.info("DÉMARRAGE - Chargement initial RPPS")
    logger.info("="*60)
    logger.info(f"Fichier RPPS: {args.rpps_file}")
    logger.info(f"Mode dry-run: {args.dry_run}")
    if args.max_records:
        logger.info(f"Limite: {args.max_records} enregistrements")
    
    start_time = datetime.now()
    
    try:
        # 1. Charge la configuration
        logger.info("\n[1/4] Chargement configuration...")
        config = load_config(args.config)
        logger.info("✓ Configuration chargée")
        
        # 2. Extraction des données RPPS
        logger.info("\n[2/4] Extraction données RPPS...")
        extractor = RPPSExtractor(
            mapping_file=config['paths']['mapping_file']
        )
        
        records_list = []
        for record in extractor.extract_records(args.rpps_file, args.max_records):
            if record.is_valid:
                # Convertit RPPSRecord en dict
                record_dict = {
                    'id_professionnel': record.id_professionnel,
                    'nom': record.nom,
                    'prenom': record.prenom,
                    'civilite': record.civilite,
                    'code_profession': record.code_profession,
                    'libelle_profession': record.libelle_profession,
                    'categorie_profession': record.categorie_profession,
                    'code_savoir_faire': record.code_savoir_faire,
                    'libelle_savoir_faire': record.libelle_savoir_faire,
                    'mode_exercice': record.mode_exercice,
                    'code_mode_exercice': record.code_mode_exercice,
                    'secteur_activite': record.secteur_activite,
                    'date_debut_activite': record.date_debut_activite,
                    'date_fin_activite': record.date_fin_activite,
                    'siret': record.siret,
                    'siren': record.siren,
                    'finess': record.finess,
                    'raison_sociale': record.raison_sociale,
                    'enseigne_commerciale': record.enseigne_commerciale,
                    'numero_voie': record.numero_voie,
                    'type_voie': record.type_voie,
                    'libelle_voie': record.libelle_voie,
                    'complement_adresse': record.complement_adresse,
                    'code_postal': record.code_postal,
                    'commune': record.commune,
                    'code_commune_insee': record.code_commune_insee,
                    'departement': record.departement,
                    'pays': record.pays,
                    'telephone_1': record.telephone_1,
                    'telephone_2': record.telephone_2,
                    'fax': record.fax,
                    'email': record.email,
                }
                records_list.append(record_dict)
        
        extract_stats = extractor.get_stats()
        logger.info(f"✓ Extraction terminée")
        logger.info(f"  - Total lignes: {extract_stats['total_lines']}")
        logger.info(f"  - Valides: {extract_stats['valid_records']}")
        logger.info(f"  - Invalides: {extract_stats['invalid_records']}")
        
        if not records_list:
            logger.error("❌ Aucun enregistrement valide extrait")
            return 1
        
        # 3. Validation des données
        logger.info(f"\n[3/4] Validation de {len(records_list)} enregistrements...")
        validator = DataValidator(config=config)
        
        validated_records = []
        for record in records_list:
            result = validator.validate_professionnel(record)
            if result.is_valid:
                # Utilise les données nettoyées
                validated_records.append({**record, **result.cleaned_data})
            elif result.warnings:
                # Log les warnings mais garde quand même
                logger.warning(f"RPPS {record['id_professionnel']}: {result.warnings}")
                validated_records.append(record)
        
        valid_stats = validator.get_stats()
        logger.info(f"✓ Validation terminée")
        logger.info(f"  - Validés: {valid_stats['validated']}")
        logger.info(f"  - Rejetés: {valid_stats['rejected']}")
        logger.info(f"  - Warnings: {valid_stats['warnings']}")
        
        # 4. Chargement en base (sauf si dry-run)
        if args.dry_run:
            logger.info("\n[4/4] Mode DRY-RUN - Pas d'insertion en base")
            logger.info(f"✓ {len(validated_records)} enregistrements prêts pour insertion")
        else:
            logger.info(f"\n[4/4] Chargement de {len(validated_records)} enregistrements en base...")
            
            db_config = {
                'user': config['database']['user'],
                'password': config['database']['password'],
                'dsn': config['database']['dsn'],
                'wallet_path': config['database']['wallet_path']
            }
            
            loader = OracleLoader(db_config)
            loader.batch_size = config['import']['batch_size']
            loader.load_data(validated_records)
            
            load_stats = loader.get_stats()
            logger.info(f"✓ Chargement terminé")
            logger.info(f"  - Professionnels: {load_stats['professionnels_inserted']}")
            logger.info(f"  - Activités: {load_stats['activites_inserted']}")
            logger.info(f"  - Adresses: {load_stats['adresses_inserted']}")
            logger.info(f"  - Contacts: {load_stats['contacts_inserted']}")
            logger.info(f"  - Erreurs: {load_stats['errors']}")
        
        # Statistiques finales
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "="*60)
        logger.info("TERMINÉ AVEC SUCCÈS")
        logger.info("="*60)
        logger.info(f"Durée totale: {duration:.1f} secondes")
        logger.info(f"Performance: {len(validated_records)/duration:.0f} enregistrements/sec")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"❌ Fichier introuvable: {e}")
        return 1
    except Exception as e:
        logger.exception(f"❌ Erreur critique: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
