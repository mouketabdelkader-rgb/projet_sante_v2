#!/usr/bin/env python3
"""
Extractor modulaire pour fichier RPPS (TXT pipe-delimited).
Génère des records yieldés pour streaming (évite chargement full en RAM).
"""
import re
from pathlib import Path
from typing import Generator, Dict, Any, Tuple
from config import Config  # Externalisé

class RPPSExtractor:
    def __init__(self, file_path: str, config: Config):
        self.file_path = Path(file_path)
        self.config = config
        self.col_map = self._build_col_map()  # Mapping colonnes dynamiques via config

    def _build_col_map(self) -> Dict[str, int]:
        """Construit le mapping colonnes basé sur config.yaml (noms colonnes → index)."""
        # Exemple config : {'COL_ID': 'Identifiant PP', ...}
        col_names = self.config.get('rpps_columns', {})
        # Parser en-tête fichier pour indices réels (robustesse si format varie)
        with open(self.file_path, 'r', encoding='utf-8') as f:
            header = next(f).strip().split('|')
        return {k: header.index(v) for k, v in col_names.items() if v in header}

    def extract(self) -> Generator[Dict[str, Any], None, None]:
        """Générateur de records : yield un dict par ligne valide."""
        stats = {'lines_read': 0, 'errors': 0}
        with open(self.file_path, 'r', encoding='utf-8') as f:
            next(f)  # Skip header
            for line_num, line in enumerate(f, 2):  # 1-based pour logs
                stats['lines_read'] += 1
                try:
                    fields = line.strip().split('|')
                    if len(fields) < len(self.col_map):
                        stats['errors'] += 1
                        continue

                    record = {
                        'id_prof': fields[self.col_map['COL_ID']],
                        'nom': fields[self.col_map['COL_NOM']][:100],
                        'prenom': fields[self.col_map['COL_PRENOM']][:100] if self.col_map.get('COL_PRENOM') else None,
                        'code_prof': fields[self.col_map['COL_CODE_PROF']][:10],
                        'lib_prof': fields[self.col_map['COL_LIB_PROF']][:200],
                        'code_cat': fields[self.col_map['COL_CODE_CAT']][:2],
                        'code_sf': fields[self.col_map['COL_CODE_SF']][:10],
                        'lib_sf': fields[self.col_map['COL_LIB_SF']][:200],
                        'mode_ex': fields[self.col_map['COL_MODE_EX']],
                        'autorite': fields[self.col_map['COL_AUTORITE']],
                        'siret': fields[self.col_map['COL_SIRET']][:14],
                        'finess': fields[self.col_map['COL_FINESS']][:9],
                        'id_tech': fields[self.col_map['COL_ID_TECH']][:50],
                        'numero': fields[self.col_map['COL_NUMERO']][:10],
                        'type_voie': fields[self.col_map['COL_TYPE_VOIE']][:50],
                        'lib_voie': fields[self.col_map['COL_LIB_VOIE']][:200],
                        'cp': fields[self.col_map['COL_CP']][:5],
                        'commune': fields[self.col_map['COL_COMMUNE']][:100],
                        'tel1': fields[self.col_map['COL_TEL1']],
                        'tel2': fields[self.col_map['COL_TEL2']],
                        'email': fields[self.col_map['COL_EMAIL']].lower(),
                    }
                    if record['id_prof']:  # Skip invalides
                        yield record, stats
                except (ValueError, IndexError) as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 10:  # Log only first 10
                        from utils import logger
                        logger.warning(f"Ligne {line_num}: {e}")
                    if stats['errors'] > 1000:
                        raise ValueError("Trop d'erreurs de parsing")

    def get_stats(self) -> Dict[str, int]:
        """Retourne stats extraction (à appeler après itération)."""
        return self.stats if hasattr(self, 'stats') else {'lines_read': 0, 'errors': 0}
