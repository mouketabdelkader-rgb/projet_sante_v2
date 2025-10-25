# 🏥 Projet Santé - Extracteur RPPS v2.0

## 📋 Vue d'ensemble

Système professionnel d'extraction, validation et chargement automatisé des données RPPS (Répertoire Partagé des Professionnels de Santé) vers une base de données Oracle Cloud.

**Architecture :** 4 couches, 12 tables, pipeline ETL complet  
**Volume cible :** ~2.2M professionnels de santé  
**Performance :** ~15 min pour import complet  

---

## 🎯 Objectifs Étape 1

✅ **Fondations inébranlables** :
- Architecture BDD professionnelle (12 tables)
- Extracteur Python modulaire et maintenable
- Validation stricte des données
- Logs détaillés et traçabilité complète
- Performance optimisée (batch processing)

---

## 📁 Structure du Projet

```
projet_sante_v2/
├── config/
│   ├── config.yaml              # Configuration principale
│   ├── mapping_rpps.yaml        # Mapping 57 colonnes RPPS
│   └── .env.template            # Template variables d'environnement
├── sql/
│   ├── 01_create_architecture.sql   # 12 tables + index
│   ├── 02_create_views.sql          # Vues métier
│   ├── 03_create_procedures.sql     # Procédures stockées
│   └── 04_create_triggers.sql       # Triggers automatiques
├── extractors/
│   ├── __init__.py
│   ├── rpps_extractor.py        # Lecture fichier RPPS
│   └── data_validator.py        # Validation données
├── loaders/
│   ├── __init__.py
│   └── oracle_loader.py         # Insertion Oracle
├── utils/
│   ├── __init__.py
│   ├── logger.py                # Logging centralisé
│   └── hash_utils.py            # Hash + validations
├── logs/                        # Logs d'exécution
├── data/                        # Données RPPS
├── main.py                      # Script principal
├── setup_database.py            # Setup BDD
├── requirements.txt
└── README.md
```

---

## 🚀 Installation

### 1. Prérequis

- **Python 3.9+**
- **Oracle Instant Client** (21c recommandé)
- **Oracle Cloud** : Autonomous Database ATP configurée
- **Wallet Oracle** téléchargé et décompressé

### 2. Installation des dépendances

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copier le template .env
cp config/.env.template .env

# Éditer .env avec vos identifiants
nano .env
```

Compléter avec vos informations :
```env
DB_USER=ADMIN
DB_PASSWORD=VotreMotDePasseSecurise
DB_DSN=extracteursante_high
WALLET_PATH=/chemin/vers/wallet_oracle
ORACLE_HOME=/usr/lib/oracle/21/client64/lib
```

### 4. Setup de la base de données

```bash
# Exécute les scripts SQL pour créer l'architecture
python setup_database.py
```

**Sortie attendue :**
- 12 tables créées
- 35 index créés
- 5 vues métier
- 4 procédures stockées
- 2 fonctions
- 4 triggers

---

## 📊 Architecture Base de Données

### Couche 1 : Données CORE (6 tables)

1. **PROFESSIONNELS** (~2.2M lignes) - Master
2. **ACTIVITES** (~3M lignes) - Modes d'exercice
3. **STRUCTURES** (~500k lignes) - Cabinets/cliniques
4. **ADRESSES** (~2.5M lignes) - Adresses postales
5. **CONTACTS** (~5M lignes) - Téléphones/emails
6. **QUALIFICATIONS** (~3M lignes) - Diplômes/certifications

### Couche 2 : Enrichissement (3 tables)

7. **ENRICHISSEMENT_CONTACTS** - Données externes enrichies
8. **SOURCES_ENTREPRISES** - SIRENE/INPI
9. **RESEAUX_SOCIAUX** - LinkedIn, etc.

### Couche 3 : Historisation (3 tables)

10. **SNAPSHOTS_MENSUELS** - Instantanés mensuels
11. **CHANGEMENTS_DETECTES** - Suivi modifications
12. **IMPORT_LOGS** - Logs techniques

### Vues Métier

- `V_CONTACTS_QUALIFIES` - Export campagnes marketing
- `V_NOUVEAUX_ENTRANTS_MOIS` - Professionnels récents
- `V_LIBERAUX_AVEC_CONTACTS` - Libéraux contactables
- `V_STATS_PROFESSIONS` - Statistiques par profession
- `V_ENRICHISSEMENT_STATUS` - Avancement enrichissement

---

## 💻 Utilisation

### Import Initial Complet

```bash
# Import de toutes les données RPPS
python main.py /chemin/vers/PS_LibreAcces_Personne_activite_YYYYMMDDXXXX.txt

# Avec limite pour tests (1000 enregistrements)
python main.py fichier_rpps.txt --max-records 1000

# Mode dry-run (validation sans insertion)
python main.py fichier_rpps.txt --dry-run

# Avec niveau de log DEBUG
python main.py fichier_rpps.txt --log-level DEBUG
```

### Exemples de Sortie

```
===========================================================
DÉMARRAGE - Chargement initial RPPS
===========================================================
Fichier RPPS: PS_LibreAcces_Personne_activite_20251023.txt

[1/4] Chargement configuration...
✓ Configuration chargée

[2/4] Extraction données RPPS...
Progression: 10000 lignes traitées, 9856 valides
Progression: 20000 lignes traitées, 19702 valides
...
✓ Extraction terminée
  - Total lignes: 2234567
  - Valides: 2198432
  - Invalides: 36135

[3/4] Validation de 2198432 enregistrements...
✓ Validation terminée
  - Validés: 2195678
  - Rejetés: 2754
  - Warnings: 45892

[4/4] Chargement de 2195678 enregistrements en base...
Progression: 1000/2195678 enregistrements
Progression: 2000/2195678 enregistrements
...
✓ Chargement terminé
  - Professionnels: 2195678
  - Activités: 3245892
  - Adresses: 2456789
  - Contacts: 4987654
  - Erreurs: 0

===========================================================
TERMINÉ AVEC SUCCÈS
===========================================================
Durée totale: 876.3 secondes
Performance: 2506 enregistrements/sec
```

---

## 🔍 Validation et Tests

### Requêtes de Vérification

```sql
-- Compter les professionnels par catégorie
SELECT categorie_profession, COUNT(*) 
FROM professionnels 
GROUP BY categorie_profession;

-- Professionnels avec contacts
SELECT COUNT(DISTINCT p.id_professionnel)
FROM professionnels p
JOIN contacts c ON p.id_professionnel = c.id_professionnel;

-- Top 10 professions
SELECT libelle_profession, COUNT(*) as nb
FROM professionnels
GROUP BY libelle_profession
ORDER BY nb DESC
FETCH FIRST 10 ROWS ONLY;

-- Utiliser les vues métier
SELECT * FROM v_contacts_qualifies WHERE score_qualification >= 80;
SELECT * FROM v_nouveaux_entrants_mois;
```

### Export Test

```sql
-- Export 1000 contacts qualifiés pour campagne
SELECT 
    id_professionnel, nom, prenom, libelle_profession,
    telephones, emails, code_postal, commune
FROM v_contacts_qualifies
WHERE score_qualification >= 70
  AND telephones IS NOT NULL
FETCH FIRST 1000 ROWS ONLY;
```

---

## 📈 Performance

### Métriques Cibles

- **Extraction :** ~150k lignes/min
- **Validation :** ~200k lignes/min
- **Insertion BDD :** ~2000-3000 lignes/sec
- **Durée totale (2.2M) :** 15-20 minutes

### Optimisations Implémentées

✅ Lecture streaming (pas de chargement mémoire complet)  
✅ Batch insert (1000 lignes/commit)  
✅ Index Oracle optimisés  
✅ MERGE (upsert) pour professionnels  
✅ Validation parallélisable (future amélioration)

---

## 🛠️ Mapping RPPS

Le fichier `config/mapping_rpps.yaml` contient le mapping exact des 57 colonnes RPPS vers les tables Oracle.

**Colonnes critiques vérifiées :**
- Col 0 : Identifiant PP (RPPS)
- Col 7 : Nom d'exercice
- Col 8 : Prénom d'exercice
- Col 9 : Code profession
- Col 16 : Libellé savoir-faire
- Col 18 : Libellé mode exercice
- Col 28-37 : Adresse
- Col 40-43 : Contacts (tel, email)

---

## 🔒 Sécurité et RGPD

### Mesures Implémentées

- ✅ Credentials dans `.env` (jamais versionnés)
- ✅ Wallet Oracle chiffré
- ✅ Logs sans données sensibles
- ✅ Validation stricte des données
- ✅ Opt-in marketing (champ prévu)

### Conformité

- Sources : **Données publiques** (RPPS officiel)
- Base légale : **Mission d'intérêt public**
- Finalité : **Annuaire professionnel**
- Durée conservation : **Mise à jour mensuelle**

---

## 📝 Logs

Les logs sont générés dans `./logs/` avec rotation automatique :

```
logs/
├── extracteur_rpps_20251023_143522.log
├── oracle_loader_20251023_143522.log
└── main_20251023_143522.log
```

**Format :**
```
2025-10-23 14:35:22 - INFO - [rpps_extractor.py:145] - Extraction terminée
2025-10-23 14:35:22 - WARNING - [data_validator.py:78] - Téléphone invalide: 06 12
```

---

## 🐛 Troubleshooting

### Erreur : "No module named 'oracledb'"

```bash
pip install oracledb
```

### Erreur : "Wallet not found"

Vérifier que le chemin dans `.env` est correct et que le wallet contient :
- `cwallet.sso`
- `tnsnames.ora`
- `sqlnet.ora`

### Erreur : "ORA-01745: invalid host/bind variable name"

Vérifier que les bind variables n'utilisent pas de mots réservés Oracle.  
Solution : préfixer avec `p_` (ex: `:p_mode` au lieu de `:mode`)

### Performance lente

- Augmenter `batch_size` dans `config.yaml` (défaut: 1000)
- Vérifier les index Oracle : `SELECT * FROM user_indexes`
- Activer profiling : `performance.profiling_enabled: true`

---

## 🔄 Prochaines Étapes (Étapes 2-3)

### Étape 2 : Enrichissement Multi-Sources

- API SIRENE (données entreprises)
- Pages Jaunes (coordonnées)
- Doctolib (profils médicaux)
- LinkedIn (réseaux sociaux)

### Étape 3 : Automatisation Pipeline

- Cron job mensuel
- Détection nouveaux professionnels
- Notification email
- Intégration Vtiger CRM

---

## 📞 Support

**Logs :** Consulter `./logs/` pour diagnostic  
**Validation :** Utiliser `--dry-run` pour tests  
**Performance :** Activer `--log-level DEBUG`

---

## 📜 Licence

Usage interne uniquement - Conformité RGPD stricte

---

**Version :** 2.0  
**Date :** 23 Octobre 2025  
**Auteur :** Équipe Data Santé  
**Status :** ✅ Production Ready
