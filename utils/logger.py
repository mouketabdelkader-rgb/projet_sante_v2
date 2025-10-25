"""
Module de logging centralisé pour le projet
"""
import logging
import os
from datetime import datetime
from pathlib import Path


class CustomLogger:
    """Logger personnalisé avec rotation et formatage"""
    
    def __init__(self, name: str, log_dir: str = "./logs", level=logging.INFO):
        """
        Initialise le logger
        
        Args:
            name: Nom du logger
            log_dir: Répertoire des logs
            level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Crée le répertoire logs si nécessaire
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        # Format détaillé
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler fichier avec rotation
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = Path(log_dir) / f"{name}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        
        # Handler console (simplifié)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Ajoute les handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.log_file = log_file
        
    def get_logger(self):
        """Retourne l'instance du logger"""
        return self.logger
    
    def get_log_path(self):
        """Retourne le chemin du fichier de log"""
        return self.log_file


def get_logger(name: str = "extracteur_rpps", level=logging.INFO):
    """
    Fonction helper pour obtenir un logger
    
    Args:
        name: Nom du logger
        level: Niveau de log
        
    Returns:
        Logger configuré
    """
    custom_logger = CustomLogger(name, level=level)
    return custom_logger.get_logger()
