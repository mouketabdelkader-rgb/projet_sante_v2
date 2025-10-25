# 🎯 FEUILLE DE ROUTE PROJET CRM
## Système Complet : Extracteur → Oracle DB → Vtiger CRM + Nextcloud + FreeScout

**Date de création :** 23 Octobre 2025  
**Environnement Dev :** PC Linux (12 GB RAM)  
**Environnement Prod :** Oracle Cloud Free Tier  
**Méthodologie :** Développement modulaire distribué sur IA multiples

---

## 📐 ARCHITECTURE GLOBALE

```
┌─────────────────────────────────────────────────────────────┐
│                  PIPELINE MENSUEL AUTOMATISÉ                 │
│                        (CRON JOB)                            │
└─────────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  auto_maj.py │   │detect_       │   │enrich_       │
│              │──►│nouveaux.py   │──►│pros.py       │
│ Télécharge   │   │              │   │              │
│ RPPS mensuel │   │ Compare old  │   │ Multi-sources│
│              │   │ vs new       │   │ enrichment   │
└──────────────┘   └──────────────┘   └──────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  ORACLE DATABASE (ATP - Cloud)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📦 COUCHE DONNÉES CORE                                      │
│  ├─ professionnels (Master ~2.2M)                           │
│  ├─ activites (Exercices professionnels)                    │
│  ├─ structures (Cabinets, cliniques)                        │
│  ├─ adresses (Géolocalisation)                              │
│  ├─ contacts (Multi-sources: tél, email, web)               │
│  └─ qualifications (Diplômes, autorisations)                │
│                                                              │
│  🔍 COUCHE ENRICHISSEMENT                                    │
│  ├─ enrichissement_contacts (Données externes)              │
│  ├─ sources_entreprises (SIRENE, INPI, Pappers)             │
│  └─ reseaux_sociaux (LinkedIn, Facebook, etc.)              │
│                                                              │
│  📊 COUCHE HISTORISATION                                     │
│  ├─ snapshots_mensuels (Photos complètes)                   │
│  ├─ changements_detectes (Deltas)                           │
│  └─ import_logs (Traçabilité technique)                     │
│                                                              │
│  💼 COUCHE CRM / BUSINESS                                    │
│  ├─ interactions (Suivi commercial)                         │
│  ├─ rendez_vous (Agenda)                                    │
│  ├─ appels (Ringover)                                       │
│  ├─ campagnes (Marketing)                                   │
│  ├─ cibles_campagne (Ciblage)                               │
│  └─ statistiques_agregees (KPIs)                            │
│                                                              │
│  👁️ VUES MÉTIER                                              │
│  ├─ v_contacts_qualifies (Exports)                          │
│  ├─ v_nouveaux_entrants_mois                                │
│  └─ v_dashboard_agent                                       │
└─────────────────────────────────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   VTIGER     │   │  NEXTCLOUD   │   │  FREESCOUT   │
│     CRM      │   │   (Docs)     │   │  (Support)   │
│              │   │              │   │              │
│ • Contacts   │   │ • Calendrier │   │ • Tickets    │
│ • RDV        │   │ • Fichiers   │   │ • Emails     │
│ • Workflows  │   │              │   │              │
└──────────────┘   └──────────────┘   └──────────────┘
         │                  │                  │
         └──────────────────┼──────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │   INTERFACE AGENTS      │
              │                         │
              │ • Dashboard stats       │
              │ • Règles horaires       │
              │ • Intégration Ringover  │
              │ • Coaching IA (futur)   │
              └─────────────────────────┘
```

---

## 🗄️ ARCHITECTURE BASE DE DONNÉES DÉTAILLÉE

### **Principes de conception :**
- **Architecture en couches** : Séparation claire des responsabilités
- **Historisation complète** : Snapshots mensuels + détection changements
- **Multi-sources** : Données RPPS + enrichissements externes
- **Traçabilité** : Logs exhaustifs de tous les imports
- **Performance** : Index optimisés pour requêtes fréquentes
- **Évolutivité** : Prêt pour scaling et IA

### **📦 COUCHE DONNÉES CORE**

#### **Table 1 : PROFESSIONNELS** (Master - Source de vérité)
```sql
CREATE TABLE professionnels (
    id_professionnel VARCHAR2(20) PRIMARY KEY,  -- Identifiant PP (RPPS)
    nom VARCHAR2(100) NOT NULL,
    prenom VARCHAR2(100),
    nom_exercice VARCHAR2(100),
    civilite VARCHAR2(10),
    code_profession VARCHAR2(10),
    libelle_profession VARCHAR2(200),
    categorie_profession VARCHAR2(50),  -- Médecin, Paramédical, etc.
    date_naissance DATE,
    statut_enregistrement VARCHAR2(50),  -- Actif, Radié, etc.
    date_premiere_apparition DATE,  -- Première fois dans RPPS
    date_derniere_maj DATE,
    date_import DATE DEFAULT SYSDATE,
    source_data VARCHAR2(50) DEFAULT 'RPPS',
    hash_data VARCHAR2(64)  -- Pour détecter changements
);
```
**Volume estimé :** ~2.2M lignes  
**Croissance :** +10-15k/mois

#### **Table 2 : ACTIVITES** (Exercices professionnels)
```sql
CREATE TABLE activites (
    id_activite NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL REFERENCES professionnels,
    code_savoir_faire VARCHAR2(10),
    libelle_savoir_faire VARCHAR2(200),  -- Spécialité
    mode_exercice VARCHAR2(100),  -- Lib,indép,artis,com / Salarié
    secteur_activite VARCHAR2(50),
    date_debut_activite DATE,
    date_fin_activite DATE,
    statut_activite VARCHAR2(50),  -- Actif, Cessé
    id_structure NUMBER,
    date_import DATE DEFAULT SYSDATE
);
```
**Volume estimé :** ~3M lignes (multi-activités par pro)

#### **Table 3 : STRUCTURES** (Cabinets, cliniques, hôpitaux)
```sql
CREATE TABLE structures (
    id_structure NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    siret VARCHAR2(14),
    finess VARCHAR2(9),
    raison_sociale VARCHAR2(200),
    enseigne_commerciale VARCHAR2(200),
    type_structure VARCHAR2(100),
    statut_juridique VARCHAR2(100),
    date_creation DATE,
    date_fermeture DATE,
    date_import DATE DEFAULT SYSDATE
);
```
**Volume estimé :** ~500k lignes

#### **Table 4 : ADRESSES** (Géolocalisation)
```sql
CREATE TABLE adresses (
    id_adresse NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) REFERENCES professionnels,
    id_structure NUMBER REFERENCES structures,
    type_adresse VARCHAR2(50),  -- Exercice, Correspondance
    numero_voie VARCHAR2(10),
    type_voie VARCHAR2(50),
    libelle_voie VARCHAR2(200),
    complement_adresse VARCHAR2(200),
    code_postal VARCHAR2(5),
    commune VARCHAR2(100),
    departement VARCHAR2(3),
    region VARCHAR2(50),
    pays VARCHAR2(50) DEFAULT 'France',
    latitude NUMBER(10,8),  -- Pour futures optimisations géo
    longitude NUMBER(11,8),
    date_import DATE DEFAULT SYSDATE
);
```
**Volume estimé :** ~2.5M lignes

#### **Table 5 : CONTACTS** (Moyens de communication multi-sources)
```sql
CREATE TABLE contacts (
    id_contact NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) REFERENCES professionnels,
    id_structure NUMBER REFERENCES structures,
    type_contact VARCHAR2(20),  -- TELEPHONE, EMAIL, FAX, SITE_WEB
    valeur VARCHAR2(200) NOT NULL,
    categorie VARCHAR2(50),  -- Mobile, Fixe, Perso, Pro
    priorite NUMBER DEFAULT 50,  -- 1-100 (100 = prioritaire)
    statut_validation VARCHAR2(20),  -- Verifie, Invalide
    source_origine VARCHAR2(50),  -- RPPS, SIRENE, ENRICHISSEMENT
    date_collecte DATE DEFAULT SYSDATE,
    opt_in_marketing CHAR(1) DEFAULT 'N',  -- RGPD
    date_opt_in DATE,
    date_derniere_utilisation DATE,
    nombre_tentatives NUMBER DEFAULT 0,
    date_import DATE DEFAULT SYSDATE
);
```
**Volume estimé :** ~5M lignes (plusieurs contacts par pro)

#### **Table 6 : QUALIFICATIONS** (Diplômes, autorisations)
```sql
CREATE TABLE qualifications (
    id_qualification NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL REFERENCES professionnels,
    type_qualification VARCHAR2(50),  -- Diplome, Autorisation, DPC
    code_qualification VARCHAR2(20),
    libelle_qualification VARCHAR2(200),
    date_obtention DATE,
    date_debut_validite DATE,
    date_fin_validite DATE,
    date_import DATE DEFAULT SYSDATE
);
```
**Volume estimé :** ~3M lignes

---

### **🔍 COUCHE ENRICHISSEMENT**

#### **Table 7 : ENRICHISSEMENT_CONTACTS** (Données externes)
```sql
CREATE TABLE enrichissement_contacts (
    id_enrichissement NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL REFERENCES professionnels,
    type_donnee VARCHAR2(50),  -- TELEPHONE, EMAIL, LINKEDIN
    valeur VARCHAR2(500),
    source_enrichissement VARCHAR2(100),  -- SIRENE, PAGES_JAUNES
    url_source VARCHAR2(500),
    methode_collecte VARCHAR2(50),  -- API, SCRAPING, MANUEL
    score_confiance NUMBER(3,2),  -- 0.00 à 1.00
    statut_verification VARCHAR2(20),  -- A_VERIFIER, VERIFIE
    date_collecte DATE DEFAULT SYSDATE,
    date_verification DATE,
    metadata_json CLOB  -- Données brutes JSON
);
```
**Volume estimé :** ~10M lignes (multi-sources)

#### **Table 8 : SOURCES_ENTREPRISES** (SIRENE, INPI, Pappers)
```sql
CREATE TABLE sources_entreprises (
    id_source_entreprise NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    siret VARCHAR2(14) NOT NULL,
    siren VARCHAR2(9),
    denomination VARCHAR2(200),
    forme_juridique VARCHAR2(100),
    date_creation DATE,
    nom_dirigeant VARCHAR2(100),
    prenom_dirigeant VARCHAR2(100),
    date_naissance_dirigeant DATE,
    age_dirigeant NUMBER,
    code_ape VARCHAR2(6),
    libelle_ape VARCHAR2(200),
    effectif VARCHAR2(50),
    source_origine VARCHAR2(50),  -- SIRENE, INPI, PAPPERS
    date_collecte DATE DEFAULT SYSDATE,
    data_json CLOB
);
```
**Volume estimé :** ~1M lignes

#### **Table 9 : RESEAUX_SOCIAUX** (Présence digitale)
```sql
CREATE TABLE reseaux_sociaux (
    id_reseau_social NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL REFERENCES professionnels,
    plateforme VARCHAR2(50),  -- LINKEDIN, FACEBOOK, TWITTER
    url_profil VARCHAR2(500),
    identifiant_profil VARCHAR2(200),
    nom_affiche VARCHAR2(200),
    bio_description CLOB,
    photo_profil_url VARCHAR2(500),
    nombre_connexions NUMBER,
    date_collecte DATE DEFAULT SYSDATE,
    date_derniere_activite DATE,
    statut_profil VARCHAR2(20)  -- ACTIF, INACTIF
);
```
**Volume estimé :** ~500k lignes (présence digitale partielle)

---

### **📊 COUCHE HISTORISATION**

#### **Table 10 : SNAPSHOTS_MENSUELS** (Photo mensuelle)
```sql
CREATE TABLE snapshots_mensuels (
    id_snapshot NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    annee NUMBER(4) NOT NULL,
    mois NUMBER(2) NOT NULL,
    date_snapshot DATE NOT NULL,
    nom_fichier_rpps VARCHAR2(200),
    url_source VARCHAR2(500),
    nb_professionnels_total NUMBER,
    nb_professionnels_actifs NUMBER,
    nb_nouveaux NUMBER,
    nb_modifications NUMBER,
    nb_radiations NUMBER,
    duree_traitement_secondes NUMBER,
    statut_import VARCHAR2(20),  -- SUCCESS, PARTIAL, FAILED
    logs_import CLOB,
    UNIQUE (annee, mois)
);
```
**Volume estimé :** ~12 lignes/an (mensuel)

#### **Table 11 : CHANGEMENTS_DETECTES** (Deltas mensuels)
```sql
CREATE TABLE changements_detectes (
    id_changement NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_snapshot NUMBER NOT NULL REFERENCES snapshots_mensuels,
    id_professionnel VARCHAR2(20) NOT NULL,
    type_changement VARCHAR2(50),  -- NOUVEAU, MODIFICATION, RADIATION
    table_concernee VARCHAR2(50),
    champ_concerne VARCHAR2(100),
    valeur_ancienne VARCHAR2(500),
    valeur_nouvelle VARCHAR2(500),
    date_detection DATE DEFAULT SYSDATE
);
```
**Volume estimé :** ~200k lignes/mois

#### **Table 12 : IMPORT_LOGS** (Traçabilité technique)
```sql
CREATE TABLE import_logs (
    id_log NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date_import DATE DEFAULT SYSDATE,
    type_import VARCHAR2(50),  -- RPPS_INITIAL, RPPS_MAJ, ENRICHISSEMENT
    script_execute VARCHAR2(100),
    statut VARCHAR2(20),  -- RUNNING, SUCCESS, FAILED
    nb_lignes_traitees NUMBER,
    nb_lignes_inserees NUMBER,
    nb_lignes_mises_a_jour NUMBER,
    nb_erreurs NUMBER,
    date_debut TIMESTAMP,
    date_fin TIMESTAMP,
    duree_secondes NUMBER,
    message_log CLOB,
    erreurs_json CLOB
);
```
**Volume estimé :** ~100 lignes/mois

---

### **💼 COUCHE CRM / BUSINESS**

#### **Table 13 : INTERACTIONS** (Suivi commercial)
```sql
CREATE TABLE interactions (
    id_interaction NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL REFERENCES professionnels,
    date_interaction TIMESTAMP NOT NULL,
    type_interaction VARCHAR2(50),  -- APPEL, EMAIL, SMS
    canal VARCHAR2(50),  -- ENTRANT, SORTANT
    id_agent VARCHAR2(50),
    nom_agent VARCHAR2(100),
    sujet VARCHAR2(200),
    notes CLOB,
    resultat VARCHAR2(50),  -- CONTACT_ETABLI, RAPPEL, REFUS
    statut_avant VARCHAR2(50),
    statut_apres VARCHAR2(50),
    score_interet NUMBER(2),  -- 1-10
    duree_secondes NUMBER,
    enregistrement_url VARCHAR2(500)
);
```
**Volume estimé :** ~1M lignes/an

#### **Table 14 : RENDEZ_VOUS** (Agenda commercial)
```sql
CREATE TABLE rendez_vous (
    id_rdv NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL REFERENCES professionnels,
    date_rdv TIMESTAMP NOT NULL,
    duree_minutes NUMBER,
    type_rdv VARCHAR2(50),  -- DEMO, FORMATION, SIGNATURE
    mode_rdv VARCHAR2(50),  -- PRESENTIEL, VISIO, TELEPHONE
    lieu_rdv VARCHAR2(200),
    lien_visio VARCHAR2(500),
    statut_rdv VARCHAR2(50),  -- PLANIFIE, CONFIRME, REALISE
    date_confirmation DATE,
    id_agent VARCHAR2(50),
    notes_preparation CLOB,
    compte_rendu CLOB
);
```
**Volume estimé :** ~50k lignes/an

#### **Table 15 : APPELS** (Historique Ringover)
```sql
CREATE TABLE appels (
    id_appel NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_appel_ringover VARCHAR2(100) UNIQUE,
    id_professionnel VARCHAR2(20) REFERENCES professionnels,
    numero_telephone VARCHAR2(20) NOT NULL,
    date_heure_debut TIMESTAMP NOT NULL,
    date_heure_fin TIMESTAMP,
    duree_secondes NUMBER,
    direction VARCHAR2(20),  -- ENTRANT, SORTANT
    id_agent VARCHAR2(50),
    statut_appel VARCHAR2(50),  -- REPONDU, NON_REPONDU
    enregistrement_disponible CHAR(1) DEFAULT 'N',
    url_enregistrement VARCHAR2(500),
    id_interaction NUMBER REFERENCES interactions
);
```
**Volume estimé :** ~500k lignes/an

#### **Table 16 : CAMPAGNES** (Actions marketing)
```sql
CREATE TABLE campagnes (
    id_campagne NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nom_campagne VARCHAR2(200) NOT NULL,
    description CLOB,
    type_campagne VARCHAR2(50),  -- EMAIL, APPEL, SMS, MIXED
    date_debut DATE NOT NULL,
    date_fin DATE,
    statut_campagne VARCHAR2(50),  -- PLANIFIEE, EN_COURS, TERMINEE
    criteres_segmentation CLOB,  -- JSON des critères
    nb_cibles_initiales NUMBER,
    nb_contacts_tentes NUMBER DEFAULT 0,
    nb_contacts_reussis NUMBER DEFAULT 0,
    taux_reussite NUMBER(5,2),
    id_agent_responsable VARCHAR2(50)
);
```
**Volume estimé :** ~100 lignes/an

#### **Table 17 : CIBLES_CAMPAGNE** (Ciblage)
```sql
CREATE TABLE cibles_campagne (
    id_cible NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_campagne NUMBER NOT NULL REFERENCES campagnes,
    id_professionnel VARCHAR2(20) NOT NULL REFERENCES professionnels,
    statut_contact VARCHAR2(50),  -- A_CONTACTER, CONTACTE, INTERESSE
    date_ajout DATE DEFAULT SYSDATE,
    date_contact DATE,
    id_interaction NUMBER REFERENCES interactions,
    notes VARCHAR2(500)
);
```
**Volume estimé :** ~500k lignes/an

#### **Table 18 : STATISTIQUES_AGREGEES** (KPIs pré-calculés)
```sql
CREATE TABLE statistiques_agregees (
    id_stat NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    type_periode VARCHAR2(20),  -- JOUR, SEMAINE, MOIS
    annee NUMBER(4),
    mois NUMBER(2),
    jour DATE,
    dimension VARCHAR2(50),  -- GLOBAL, PAR_REGION, PAR_PROFESSION
    valeur_dimension VARCHAR2(100),
    nb_professionnels_total NUMBER,
    nb_avec_telephone NUMBER,
    nb_avec_email NUMBER,
    taux_enrichissement NUMBER(5,2),
    nb_interactions NUMBER,
    nb_appels NUMBER,
    nb_rdv_realises NUMBER,
    taux_transformation NUMBER(5,2),
    date_calcul TIMESTAMP DEFAULT SYSTIMESTAMP
);
```
**Volume estimé :** ~10k lignes/an

---

### **👁️ VUES MÉTIER ESSENTIELLES**

#### **Vue 1 : Contacts Qualifiés Exploitables**
```sql
CREATE OR REPLACE VIEW v_contacts_qualifies AS
SELECT 
    p.id_professionnel,
    p.nom,
    p.prenom,
    p.libelle_profession,
    p.categorie_profession,
    a.mode_exercice,
    ad.code_postal,
    ad.commune,
    ad.departement,
    ad.region,
    LISTAGG(DISTINCT CASE WHEN c.type_contact = 'TELEPHONE' 
        THEN c.valeur END, '; ') WITHIN GROUP (ORDER BY c.priorite DESC) AS telephones,
    LISTAGG(DISTINCT CASE WHEN c.type_contact = 'EMAIL' 
        THEN c.valeur END, '; ') WITHIN GROUP (ORDER BY c.priorite DESC) AS emails,
    -- Score de qualification (0-100)
    CASE 
        WHEN EXISTS(SELECT 1 FROM contacts WHERE id_professionnel = p.id_professionnel 
            AND type_contact = 'TELEPHONE') THEN 50 ELSE 0 END +
    CASE 
        WHEN EXISTS(SELECT 1 FROM contacts WHERE id_professionnel = p.id_professionnel 
            AND type_contact = 'EMAIL') THEN 30 ELSE 0 END +
    CASE 
        WHEN p.date_premiere_apparition >= ADD_MONTHS(SYSDATE, -12) THEN 20 ELSE 0 
    END AS score_qualification
FROM professionnels p
LEFT JOIN activites a ON p.id_professionnel = a.id_professionnel 
    AND a.statut_activite = 'Actif'
LEFT JOIN adresses ad ON p.id_professionnel = ad.id_professionnel
LEFT JOIN contacts c ON p.id_professionnel = c.id_professionnel
WHERE p.statut_enregistrement = 'Actif'
GROUP BY p.id_professionnel, p.nom, p.prenom, p.libelle_profession, 
         p.categorie_profession, a.mode_exercice, ad.code_postal, 
         ad.commune, ad.departement, ad.region, p.date_premiere_apparition;
```

#### **Vue 2 : Nouveaux Entrants du Mois**
```sql
CREATE OR REPLACE VIEW v_nouveaux_entrants_mois AS
SELECT 
    p.*,
    a.date_debut_activite,
    ad.departement,
    ad.region
FROM professionnels p
JOIN activites a ON p.id_professionnel = a.id_professionnel
JOIN adresses ad ON p.id_professionnel = ad.id_professionnel
WHERE p.date_premiere_apparition >= TRUNC(SYSDATE, 'MM')
  AND a.statut_activite = 'Actif';
```

#### **Vue 3 : Dashboard Agent**
```sql
CREATE OR REPLACE VIEW v_dashboard_agent AS
SELECT 
    i.id_agent,
    i.nom_agent,
    COUNT(DISTINCT i.id_interaction) as nb_interactions_total,
    COUNT(DISTINCT CASE WHEN i.type_interaction = 'APPEL' 
        THEN i.id_interaction END) as nb_appels,
    COUNT(DISTINCT CASE WHEN i.resultat = 'CONTACT_ETABLI' 
        THEN i.id_interaction END) as nb_contacts_reussis,
    ROUND(COUNT(DISTINCT CASE WHEN i.resultat = 'CONTACT_ETABLI' 
        THEN i.id_interaction END) * 100.0 / 
        NULLIF(COUNT(DISTINCT i.id_interaction), 0), 2) as taux_reussite,
    COUNT(DISTINCT r.id_rdv) as nb_rdv_planifies,
    AVG(a.duree_secondes) as duree_moyenne_appel
FROM interactions i
LEFT JOIN rendez_vous r ON i.id_agent = r.id_agent 
    AND r.date_rdv >= TRUNC(SYSDATE, 'MM')
LEFT JOIN appels a ON i.id_agent = a.id_agent 
    AND a.date_heure_debut >= TRUNC(SYSDATE, 'MM')
WHERE i.date_interaction >= TRUNC(SYSDATE, 'MM')
GROUP BY i.id_agent, i.nom_agent;
```

---

## 📡 SOURCES D'ENRICHISSEMENT RECOMMANDÉES

### **🟢 SOURCES GRATUITES / OPEN DATA (Priorité 1)**

#### **1. API SIRENE (INSEE)** ⭐⭐⭐⭐⭐
**Données accessibles :**
- Dénomination entreprise
- Date de création
- Forme juridique
- Code APE / Activité
- Effectif
- Adresse du siège

**API :** https://api.insee.fr/catalogue/  
**Limite :** 30 requêtes/minute (gratuit)  
**Qualité :** Source officielle, données fiables  
**Use case :** Enrichir tous les SIRET de la base

#### **2. Pappers API (Freemium)** ⭐⭐⭐⭐
**Données accessibles :**
- Dirigeants (nom, prénom, date naissance)
- Bénéficiaires effectifs
- Comptes annuels
- Annonces légales

**API :** https://www.pappers.fr/api  
**Limite :** 500 requêtes/mois gratuit, puis 0.02€/requête  
**Use case :** Identification gérants, calcul âge entreprise

#### **3. Annuaire des Entreprises (data.gouv.fr)** ⭐⭐⭐⭐
**Données accessibles :**
- SIRET/SIREN enrichis
- Labels (RGE, bio, etc.)
- Certifications

**API :** https://annuaire-entreprises.data.gouv.fr/  
**Limite :** Illimité  
**Use case :** Validation données + labels qualité

#### **4. Base Adresse Nationale (BAN)** ⭐⭐⭐⭐⭐
**Données accessibles :**
- Géocodage adresses (lat/long)
- Normalisation adresses

**API :** https://adresse.data.gouv.fr/  
**Limite :** Illimité  
**Use case :** Géolocalisation pour optimisations de tournées

---

### **🟡 SOURCES SEMI-PUBLIQUES (Scraping légal - Priorité 2)**

#### **5. Pages Jaunes** ⭐⭐⭐
**Données accessibles :**
- Téléphone fixe
- Horaires d'ouverture
- Site web
- Photos

**Méthode :** Scraping respectueux (1 req/2s)  
**Use case :** Téléphones manquants dans RPPS  
**Contraintes :** Robots.txt à respecter

#### **6. Doctolib / Maiia / Keldoc** ⭐⭐⭐⭐
**Données accessibles :**
- Téléphone prise RDV
- Horaires consultation
- Spécialités détaillées
- Avis patients (optionnel)

**Méthode :** API publique ou scraping léger  
**Use case :** Téléphones + disponibilités + qualité  
**Note :** Forte valeur ajoutée pour ciblage

#### **7. Ameli (Annuaire Santé)** ⭐⭐⭐⭐⭐
**Données accessibles :**
- Coordonnées mises à jour
- Secteurs conventionnement
- Tarifs

**Méthode :** Scraping (données publiques)  
**Use case :** Validation coordonnées + secteurs  
**Note :** Source officielle complémentaire à RPPS

---

### **🔵 RÉSEAUX SOCIAUX (APIs officielles - Priorité 3)**

#### **8. LinkedIn API** ⭐⭐⭐
**Données accessibles (limitées) :**
- Profil public
- Expérience professionnelle
- Formation

**API :** LinkedIn API (très restrictive)  
**Alternative :** Scraping manuel ou outils tiers (Phantombuster)  
**Use case :** Identification profils pros, réseau  
**Contraintes :** Respecter CGU LinkedIn

#### **9. Facebook/Instagram Graph API** ⭐⭐
**Données accessibles :**
- Pages professionnelles
- Horaires
- Coordonnées si renseignées

**API :** Facebook Graph API  
**Use case :** Pages pros, présence digitale  
**Note :** Valeur ajoutée faible pour B2B santé

---

### **🔴 SOURCES PAYANTES (Si budget - Priorité 4)**

#### **10. Societe.com / Infogreffe** ⭐⭐⭐⭐⭐
**Données accessibles :**
- Historique complet entreprise
- Bilans financiers
- Procédures collectives

**Coût :** ~1-5€ par fiche  
**Use case :** Due diligence, scoring crédit  
**ROI :** Élevé si ciblage grands comptes

#### **11. Kompass / Orbis** ⭐⭐⭐⭐
**Données accessibles :**
- Contacts décideurs
- Emails directs
- Téléphones directs

**Coût :** Abonnement mensuel (~100-500€)  
**Use case :** Contacts décisionnaires  
**ROI :** Moyen, dépend du secteur cible

---

### **🚀 STRATÉGIE D'ENRICHISSEMENT RECOMMANDÉE**

#### **Phase 1 : Fondations (Mois 1-2) - GRATUIT**
✅ **SIRENE API** → Tous les SIRET (dénomination, dates, APE)  
✅ **BAN** → Géocodage toutes adresses (lat/long)  
✅ **Ameli** → Validation coordonnées secteur santé  
**Coût :** 0€ | **Impact :** Base +30% enrichie

#### **Phase 2 : Contacts (Mois 3-4) - SEMI-AUTO**
✅ **Pages Jaunes** → Téléphones fixes manquants  
✅ **Doctolib/Maiia** → Téléphones + horaires + qualité  
**Coût :** 0€ (temps dev) | **Impact :** +40% tél enrichis

#### **Phase 3 : Digital (Mois 5-6) - OPTIONNEL**
⚠️ **LinkedIn** → Profils pros (scraping léger)  
⚠️ **Facebook/Instagram** → Pages professionnelles  
**Coût :** 0-50€/mois (outils) | **Impact :** +15% présence digitale

#### **Phase 4 : Premium (Mois 7+) - SI ROI POSITIF**
💰 **Pappers** (payant après freemium) → Dirigeants + emails  
💰 **Kompass** → Contacts directs décideurs  
**Coût :** 100-500€/mois | **Impact :** +20% emails qualifiés

---

### **📊 MÉTRIQUES D'ENRICHISSEMENT CIBLES**

| Métrique | Baseline (RPPS seul) | Après Phase 1 | Après Phase 2 | Après Phase 4 |
|----------|---------------------|---------------|---------------|---------------|
| % avec téléphone | 40% | 50% | 70% | 80% |
| % avec email | 5% | 10% | 15% | 35% |
| % avec site web | 10% | 15% | 25% | 30% |
| % avec LinkedIn | 0% | 0% | 5% | 15% |
| % avec infos SIRET | 30% | 95% | 95% | 95% |

---

### **MODULE 1 : EXTRACTEUR DE DONNÉES** ⭐ PRIORITÉ ABSOLUE
**Responsabilité :** Collecte, transformation et injection dans Oracle DB  
**Technologies :** Python 3.x, cx_Oracle, pandas, logging  
**Complexité :** Moyenne-Haute  
**Durée estimée :** 8-12 heures

### **MODULE 2 : BASE DE DONNÉES ORACLE - ARCHITECTURE COMPLÈTE**
**Responsabilité :** Structure complète 4 couches + vues métier  
**Technologies :** Oracle SQL, PL/SQL  
**Complexité :** Haute  
**Durée estimée :** 8-12 heures

**Livrables :**
- Scripts DDL complets (18 tables + vues)
- Scripts DML (procédures stockées, triggers)
- Scripts de migration/évolution
- Documentation ERD complète
- Scripts de seed (données test)
- Scripts d'optimisation (index, partitioning si nécessaire)

**Architecture 4 couches :**

**Couche 1 : DONNÉES CORE (6 tables)**
- professionnels (Master ~2.2M lignes)
- activites (~3M lignes)
- structures (~500k lignes)
- adresses (~2.5M lignes)
- contacts (~5M lignes)
- qualifications (~3M lignes)

**Couche 2 : ENRICHISSEMENT (3 tables)**
- enrichissement_contacts (~10M lignes)
- sources_entreprises (~1M lignes)
- reseaux_sociaux (~500k lignes)

**Couche 3 : HISTORISATION (3 tables)**
- snapshots_mensuels (~12/an)
- changements_detectes (~200k/mois)
- import_logs (~100/mois)

**Couche 4 : CRM/BUSINESS (6 tables)**
- interactions (~1M/an)
- rendez_vous (~50k/an)
- appels (~500k/an)
- campagnes (~100/an)
- cibles_campagne (~500k/an)
- statistiques_agregees (~10k/an)

**Vues métier :**
- v_contacts_qualifies (exports)
- v_nouveaux_entrants_mois
- v_dashboard_agent

**Procédures stockées essentielles :**
```sql
-- Gestion contacts
CREATE OR REPLACE PROCEDURE sp_merge_contact(
    p_id_professionnel VARCHAR2,
    p_type_contact VARCHAR2,
    p_valeur VARCHAR2,
    p_source VARCHAR2
) AS ...

-- Détection changements
CREATE OR REPLACE PROCEDURE sp_detect_changements(
    p_id_snapshot NUMBER
) AS ...

-- Calcul statistiques
CREATE OR REPLACE PROCEDURE sp_calculate_stats(
    p_periode VARCHAR2,
    p_date_ref DATE
) AS ...

-- Scoring qualification
CREATE OR REPLACE FUNCTION fn_score_qualification(
    p_id_professionnel VARCHAR2
) RETURN NUMBER AS ...

-- Nettoyage logs anciens
CREATE OR REPLACE PROCEDURE sp_clean_old_logs(
    p_retention_days NUMBER DEFAULT 365
) AS ...
```

**Index de performance critiques :**
```sql
-- Recherches fréquentes
CREATE INDEX idx_prof_nom_prenom ON professionnels(UPPER(nom), UPPER(prenom));
CREATE INDEX idx_prof_profession ON professionnels(code_profession, categorie_profession);
CREATE INDEX idx_contact_type_valeur ON contacts(type_contact, valeur);
CREATE INDEX idx_adr_geo ON adresses(code_postal, departement, region);

-- Jointures fréquentes
CREATE INDEX idx_act_prof ON activites(id_professionnel);
CREATE INDEX idx_contact_prof ON contacts(id_professionnel);
CREATE INDEX idx_enr_prof_type ON enrichissement_contacts(id_professionnel, type_donnee);

-- Filtres temporels
CREATE INDEX idx_inter_date ON interactions(date_interaction);
CREATE INDEX idx_rdv_date_statut ON rendez_vous(date_rdv, statut_rdv);
CREATE INDEX idx_chg_snapshot ON changements_detectes(id_snapshot, type_changement);
```

**Triggers automatiques :**
```sql
-- Timestamp automatique
CREATE OR REPLACE TRIGGER trg_prof_update_timestamp
BEFORE UPDATE ON professionnels
FOR EACH ROW
BEGIN
    :NEW.date_derniere_maj := SYSDATE;
END;

-- Hash data pour détection changements
CREATE OR REPLACE TRIGGER trg_prof_calculate_hash
BEFORE INSERT OR UPDATE ON professionnels
FOR EACH ROW
BEGIN
    :NEW.hash_data := DBMS_CRYPTO.HASH(
        UTL_RAW.CAST_TO_RAW(:NEW.nom || :NEW.prenom || :NEW.code_profession),
        DBMS_CRYPTO.HASH_SH256
    );
END;

-- Log des modifications
CREATE OR REPLACE TRIGGER trg_log_contact_changes
AFTER INSERT OR UPDATE OR DELETE ON contacts
FOR EACH ROW
DECLARE
    v_action VARCHAR2(10);
BEGIN
    IF INSERTING THEN v_action := 'INSERT';
    ELSIF UPDATING THEN v_action := 'UPDATE';
    ELSE v_action := 'DELETE';
    END IF;
    
    INSERT INTO import_logs(type_import, script_execute, message_log)
    VALUES ('DATA_CHANGE', 'TRIGGER', 
            'Contact ' || v_action || ' - ID: ' || COALESCE(:NEW.id_contact, :OLD.id_contact));
END;
```

### **MODULE 3 : SYNCHRONISATION ORACLE ↔ VTIGER**
**Responsabilité :** Middleware bidirectionnel  
**Technologies :** PHP/Python, API REST Vtiger, cx_Oracle  
**Complexité :** Haute  
**Durée estimée :** 6-8 heures

### **MODULE 4 : VTIGER CRM - CONFIGURATION**
**Responsabilité :** Installation, personnalisation, layouts  
**Technologies :** PHP, MySQL, Vtiger Studio  
**Complexité :** Faible-Moyenne  
**Durée estimée :** 3-4 heures

### **MODULE 5 : VTIGER CRM - MODULES CUSTOMS**
**Responsabilité :** Règles horaires, priorisation, workflows  
**Technologies :** PHP, JavaScript, Vtiger API  
**Complexité :** Haute  
**Durée estimée :** 6-8 heures

### **MODULE 6 : INTÉGRATION RINGOVER**
**Responsabilité :** Click-to-call, webhook, historique appels  
**Technologies :** JavaScript, PHP, API Ringover, n8n  
**Complexité :** Haute  
**Durée estimée :** 5-7 heures

### **MODULE 7 : NEXTCLOUD - INSTALLATION & CONFIG**
**Responsabilité :** Serveur fichiers, calendriers, intégration CRM  
**Technologies :** PHP, PostgreSQL/MySQL, WebDAV  
**Complexité :** Faible-Moyenne  
**Durée estimée :** 2-3 heures

### **MODULE 8 : FREESCOUT - INSTALLATION & CONFIG**
**Responsabilité :** Helpdesk, tickets, intégration CRM  
**Technologies :** PHP, Laravel, MySQL  
**Complexité :** Faible  
**Durée estimée :** 2-3 heures

### **MODULE 9 : N8N WORKFLOWS**
**Responsabilité :** Automatisations inter-services  
**Technologies :** n8n (Node.js), webhooks, API  
**Complexité :** Moyenne  
**Durée estimée :** 3-4 heures

### **MODULE 10 : MIGRATION ORACLE CLOUD**
**Responsabilité :** Déploiement production  
**Technologies :** Docker, Oracle Cloud CLI, Terraform  
**Complexité :** Moyenne  
**Durée estimée :** 4-6 heures

---

## 🚀 PLAN D'ACTION SÉQUENTIEL

### **PHASE 0 : PRÉPARATION** (1-2h)
- [ ] Installation environnement dev complet (Python, PHP, Node.js, Docker)
- [ ] Configuration Git/GitHub pour versioning
- [ ] Création structure projet
- [ ] Documentation outils et accès

### **PHASE 1 : FONDATIONS DONNÉES** ⭐ (12-18h)

#### **ÉTAPE 1.1 : Extracteur de données** (8-12h)
**🎯 Objectif :** Script Python robuste pour collecter et injecter données

**Livrables :**
- Script Python modulaire
- Configuration fichier (YAML/JSON)
- Gestion erreurs et logs
- Documentation complète
- Tests unitaires

**Spécifications détaillées :**
```yaml
Fonctionnalités:
  - Connexion sources multiples (API, CSV, bases SQL)
  - Transformation données (nettoyage, validation, mapping)
  - Injection Oracle DB avec gestion transactions
  - Logging détaillé (INFO, WARNING, ERROR)
  - Gestion déduplication
  - Mode incrémental et complet
  - Planification cron
  - Notifications erreurs (email/webhook)

Structure:
  extracteur/
    ├── config/
    │   ├── config.yaml
    │   └── sources.yaml
    ├── extractors/
    │   ├── __init__.py
    │   ├── base_extractor.py
    │   ├── api_extractor.py
    │   └── csv_extractor.py
    ├── transformers/
    │   ├── __init__.py
    │   └── data_transformer.py
    ├── loaders/
    │   ├── __init__.py
    │   └── oracle_loader.py
    ├── utils/
    │   ├── logger.py
    │   └── validators.py
    ├── main.py
    ├── requirements.txt
    └── README.md

Dépendances:
  - cx_Oracle >= 8.3
  - pandas >= 2.0
  - PyYAML >= 6.0
  - requests >= 2.31
  - python-dotenv >= 1.0
  - schedule >= 1.2 (pour cron)
```

**Persona IA recommandée :** Claude (logique complexe, architecture)

**Template prompt :**
```
Tu es un expert Python spécialisé en ETL (Extract-Transform-Load) et intégration de données.

CONTEXTE:
Je développe un extracteur de données qui doit collecter des informations depuis [SOURCES] 
et les injecter dans une base Oracle. L'extracteur doit être robuste, modulaire et maintenable.

OBJECTIF:
Créer un script Python professionnel avec:
- Architecture modulaire (extractors, transformers, loaders)
- Gestion avancée des erreurs
- Logging détaillé
- Configuration externalisée
- Tests unitaires

CONTRAINTES:
- Python 3.10+
- Oracle Database 19c
- Doit gérer [X] sources de données
- Mode incrémental et complet
- Performance: traiter [Y] lignes/minute minimum

LIVRABLES ATTENDUS:
1. Code source complet et commenté
2. Fichier requirements.txt
3. Configuration exemple (config.yaml)
4. Documentation README.md
5. Exemples d'utilisation

Commence par proposer l'architecture globale.
```

#### **ÉTAPE 1.2 : Architecture Base de Données Complète** (8-12h)
**🎯 Objectif :** Structure 4 couches complète et optimisée

**Livrables :**
- Scripts DDL complets (18 tables)
- Scripts DML (procédures stockées, triggers, fonctions)
- Documentation ERD détaillée (4 couches)
- Scripts de seed (données test représentatives)
- Scripts index et optimisation

**Architecture détaillée :**

**📦 Couche 1 : DONNÉES CORE (6 tables)**
```sql
-- 1. PROFESSIONNELS (Master - 2.2M lignes)
-- Clé : id_professionnel (RPPS)
-- Index : nom, prenom, profession, categorie
-- Hash pour détection changements

-- 2. ACTIVITES (3M lignes)
-- Lien : id_professionnel
-- Historisation : date_debut/fin_activite
-- Multi-activités par professionnel

-- 3. STRUCTURES (500k lignes)
-- Identifiants : siret, finess
-- Types : Cabinet, Clinique, Hôpital

-- 4. ADRESSES (2.5M lignes)
-- Géolocalisation : lat/long (BAN)
-- Normalisation : département, région

-- 5. CONTACTS (5M lignes)
-- Multi-sources : RPPS, SIRENE, enrichissement
-- Validation : statut_validation, score_confiance
-- RGPD : opt_in_marketing, date_opt_in

-- 6. QUALIFICATIONS (3M lignes)
-- Diplômes, autorisations, DPC
-- Dates validité
```

**🔍 Couche 2 : ENRICHISSEMENT (3 tables)**
```sql
-- 7. ENRICHISSEMENT_CONTACTS (10M lignes)
-- Sources externes multiples
-- Metadata JSON brute
-- Score confiance 0-1

-- 8. SOURCES_ENTREPRISES (1M lignes)
-- SIRENE, INPI, Pappers
-- Dirigeants, dates, APE

-- 9. RESEAUX_SOCIAUX (500k lignes)
-- LinkedIn, Facebook, Twitter
-- Métriques publiques
```

**📊 Couche 3 : HISTORISATION (3 tables)**
```sql
-- 10. SNAPSHOTS_MENSUELS (12/an)
-- Photo complète mensuelle
-- Statistiques agrégées
-- Logs import

-- 11. CHANGEMENTS_DETECTES (200k/mois)
-- Delta mensuel détaillé
-- Type : NOUVEAU, MODIF, RADIATION
-- Valeur avant/après

-- 12. IMPORT_LOGS (100/mois)
-- Traçabilité technique
-- Performance monitoring
```

**💼 Couche 4 : CRM/BUSINESS (6 tables)**
```sql
-- 13. INTERACTIONS (1M/an)
-- Appels, emails, SMS
-- Suivi agent, résultat
-- Enregistrements Ringover

-- 14. RENDEZ_VOUS (50k/an)
-- Planification, confirmation
-- Modes : présentiel, visio, tel
-- Compte-rendu

-- 15. APPELS (500k/an)
-- Intégration Ringover
-- Direction, durée, statut
-- Lien vers interactions

-- 16. CAMPAGNES (100/an)
-- Marketing automation
-- Segmentation JSON
-- KPIs campagne

-- 17. CIBLES_CAMPAGNE (500k/an)
-- Professionnels ciblés
-- Statut contact
-- Résultats

-- 18. STATISTIQUES_AGREGEES (10k/an)
-- KPIs pré-calculés
-- Multi-dimensions
-- Performance agents
```

**Vues métier critiques :**
```sql
-- v_contacts_qualifies
-- Scoring 0-100 automatique
-- Agrégation tél/emails
-- Filtres libéraux actifs

-- v_nouveaux_entrants_mois
-- Détection nouveaux pros
-- Enrichi avec adresses

-- v_dashboard_agent
-- KPIs agents en temps réel
-- Taux réussite, nb appels
-- Performance comparative
```

**Procédures stockées essentielles :**
- `sp_merge_contact` : Fusion contacts multi-sources
- `sp_detect_changements` : Analyse delta mensuel
- `sp_calculate_stats` : Calcul KPIs agrégés
- `fn_score_qualification` : Scoring automatique
- `sp_clean_old_logs` : Rétention données

**Optimisations performance :**
- Index composites sur recherches fréquentes
- Partitioning par date (interactions, appels)
- Materialized views pour dashboards
- Compression sur tables historiques
- Statistics refresh automatique

**Spécifications RGPD :**
```sql
-- Champ opt_in sur contacts
-- Traçabilité consentement
-- Procédure anonymisation
CREATE OR REPLACE PROCEDURE sp_anonymize_data(
    p_id_professionnel VARCHAR2,
    p_raison VARCHAR2
) AS ...

-- Procédure export données (droit d'accès)
CREATE OR REPLACE PROCEDURE sp_export_gdpr_data(
    p_id_professionnel VARCHAR2,
    p_output_format VARCHAR2
) AS ...
```

**Tests de validation :**
- Contraintes intégrité référentielle
- Triggers fonctionnels
- Performance requêtes (<100ms avg)
- Volumétrie (charge 1M lignes <10min)
- Procédures stockées (tous cas d'usage)

**Persona IA recommandée :** Gemini (excellent en SQL/DB design)

**Template prompt :**
```
Tu es un architecte de bases de données Oracle avec 15 ans d'expérience.

CONTEXTE:
Je conçois une base Oracle pour un CRM médical qui gère:
- Contacts professionnels santé (médecins, kinés, etc.)
- Rendez-vous avec règles horaires spécifiques
- Historique d'appels téléphoniques
- Qualifications et priorisations

OBJECTIF:
Créer un schéma de base de données:
- Normalisé (3NF minimum)
- Optimisé pour performances lecture/écriture
- Avec intégrité référentielle stricte
- Extensible pour évolutions futures

CONTRAINTES:
- Oracle 19c (Autonomous Database)
- ~100k contacts
- ~500 RDV/jour
- ~1000 appels/jour
- Rétention logs: 1 an

LIVRABLES:
1. Scripts DDL complets
2. Procédures stockées essentielles
3. Index de performance
4. ERD (format Mermaid ou PlantUML)
5. Documentation des choix techniques

Commence par proposer le modèle conceptuel (entités et relations).
```

---

### **PHASE 2 : INFRASTRUCTURE CRM** (10-14h)

#### **ÉTAPE 2.1 : Installation Stack LAMP/LEMP** (2h)
**🎯 Objectif :** Environnement serveur prêt

**Checklist :**
- [ ] Apache/Nginx installé et configuré
- [ ] PHP 8.1+ avec extensions (mysqli, gd, curl, xml, mbstring, zip, intl)
- [ ] MySQL/MariaDB installé
- [ ] Composer installé
- [ ] Node.js + npm installés
- [ ] SSL auto-signé pour dev

**Persona IA recommandée :** Grok (rapide pour tâches sysadmin)

#### **ÉTAPE 2.2 : Vtiger Installation** (2-3h)
**🎯 Objectif :** CRM opérationnel base

**Checklist :**
- [ ] Téléchargement Vtiger Open Source latest
- [ ] Installation via wizard web
- [ ] Configuration base de données
- [ ] Configuration cron jobs
- [ ] Premiers tests login/navigation

**Persona IA recommandée :** Claude (documentation précise)

#### **ÉTAPE 2.3 : Vtiger Personnalisation** (4-6h)
**🎯 Objectif :** CRM adapté aux besoins métier

**Tâches :**
- Création modules custom (Professionnels, Règles horaires)
- Personnalisation champs (spécialité, horaires, priorité)
- Configuration layouts par rôle (agent/admin)
- Création dashboards statistiques
- Configuration picklists

**Persona IA recommandée :** Claude (logique métier complexe)

**Template prompt :**
```
Tu es un consultant Vtiger CRM avec expertise en personnalisation avancée.

CONTEXTE:
Je configure Vtiger pour gérer des contacts professionnels santé avec:
- Règles horaires spécifiques par spécialité
- Priorisation RDV automatique
- Qualification multi-niveaux
- Dashboards statistiques temps réel

OBJECTIF:
Guider la personnalisation complète:
1. Modules custom nécessaires
2. Champs personnalisés par module
3. Workflows automatisés
4. Dashboards et rapports

CONTRAINTES:
- Vtiger Open Source 7.x ou 8.x
- Pas de modules payants
- Performance: <2s chargement pages
- Mobile-friendly

LIVRABLES:
1. Liste exhaustive personnalisations
2. Code PHP pour modules custom si nécessaire
3. Configuration workflows (export XML)
4. Requêtes SQL pour rapports custom

Commence par lister les modules custom nécessaires.
```

---

### **PHASE 3 : SYNCHRONISATION** (8-10h)

#### **ÉTAPE 3.1 : Middleware Oracle → Vtiger** (4-5h)
**🎯 Objectif :** Flux données Oracle vers CRM

**Spécifications :**
```python
Fonctionnalités:
  - Lecture incrémentale Oracle (timestamp-based)
  - Mapping Oracle → Vtiger (contacts, RDV, etc.)
  - API REST Vtiger (webservices)
  - Gestion conflits (Oracle = source de vérité)
  - Logs détaillés
  - Mode dry-run pour tests
  - Planification cron (ex: toutes les 5 min)

Structure:
  sync_oracle_vtiger/
    ├── config.yaml
    ├── sync.py
    ├── mappers/
    │   ├── contact_mapper.py
    │   └── rdv_mapper.py
    ├── vtiger_api.py
    ├── oracle_reader.py
    └── README.md
```

**Persona IA recommandée :** Claude (intégrations complexes)

#### **ÉTAPE 3.2 : Middleware Vtiger → Oracle** (4-5h)
**🎯 Objectif :** Retour infos qualifications, notes agents

**Spécifications :**
```python
Fonctionnalités:
  - Webhook Vtiger ou polling API
  - Détection changements (qualifications, notes, statuts)
  - Injection Oracle (UPDATE)
  - Gestion transactions
  - Rollback en cas d'erreur
  - Notifications admins si échec
```

**Persona IA recommandée :** Claude

---

### **PHASE 4 : MODULES AVANCÉS** (14-18h)

#### **ÉTAPE 4.1 : Module Règles Horaires** (5-6h)
**🎯 Objectif :** Routage intelligent appels/RDV

**Spécifications :**
```php
Fonctionnalités:
  - Interface admin config règles (par spécialité)
  - Stockage JSON ou table dédiée
  - Fonction: get_next_available_slot(specialite, date)
  - Vérification disponibilités temps réel
  - Gestion exceptions (jours fériés, congés)
  - Notification agents si conflit

Interface admin (Vtiger custom module):
  - Liste règles
  - CRUD règles horaires
  - Vue calendrier disponibilités
  - Import/export CSV règles
```

**Persona IA recommandée :** Claude (logique métier)

#### **ÉTAPE 4.2 : Workflows Automatisés** (3-4h)
**🎯 Objectif :** Emails, alertes, priorisations auto

**Workflows à créer :**
1. Email qualification selon statut contact
2. Notification RDV J-1, H-2
3. Escalade si RDV non confirmé
4. Attribution automatique agent selon charge
5. Alerte si contact prioritaire entrant

**Persona IA recommandée :** Grok (rapidité tâches répétitives)

#### **ÉTAPE 4.3 : Intégration Ringover via n8n** (6-8h)
**🎯 Objectif :** Click-to-call, webhooks, historique

**Architecture :**
```
Ringover → Webhook → n8n → Vtiger API
                            ↓
                      Oracle DB (logs)
```

**Workflows n8n :**
1. Appel entrant → Recherche contact Vtiger → Popup fiche
2. Appel sortant → Log durée/notes → Sync Oracle
3. Appel manqué → Création tâche rappel
4. Click-to-call depuis Vtiger

**Persona IA recommandée :** Gemini (excellent avec APIs et webhooks)

**Template prompt :**
```
Tu es un expert n8n et intégration d'APIs télécoms.

CONTEXTE:
J'intègre Ringover (téléphonie cloud) avec Vtiger CRM via n8n.

OBJECTIF:
Créer workflows n8n pour:
1. Gérer appels entrants/sortants
2. Logger historique dans Vtiger + Oracle
3. Click-to-call depuis CRM
4. Notifications temps réel agents

CONTRAINTES:
- API Ringover v2
- API REST Vtiger
- n8n self-hosted
- Latence <500ms pour popup

LIVRABLES:
1. Workflows n8n (export JSON)
2. Documentation configuration
3. Schéma architecture
4. Guide troubleshooting

Commence par expliquer l'architecture globale des flux.
```

---

### **PHASE 5 : APPLICATIONS COMPLÉMENTAIRES** (5-7h)

#### **ÉTAPE 5.1 : Nextcloud** (2-3h)
**Tâches :**
- Installation (Docker ou standard)
- Configuration stockage
- Intégration CalDAV avec Vtiger
- Setup utilisateurs et droits

**Persona IA recommandée :** Grok

#### **ÉTAPE 5.2 : FreeScout** (2-3h)
**Tâches :**
- Installation
- Configuration SMTP/IMAP
- Création départements
- Intégration basique avec Vtiger (webhooks)

**Persona IA recommandée :** Grok

#### **ÉTAPE 5.3 : Intégration inter-apps** (1-2h)
**Tâches :**
- SSO si possible (LDAP/SAML)
- Menu unifié (iframe ou liens)
- Sync contacts Nextcloud ↔ Vtiger

**Persona IA recommandée :** Claude

---

### **PHASE 6 : TESTS & OPTIMISATION** (6-8h)

#### **ÉTAPE 6.1 : Tests unitaires & intégration** (3-4h)
**Checklist :**
- [ ] Tests extracteur (données valides/invalides)
- [ ] Tests sync bidirectionnelle
- [ ] Tests workflows Vtiger
- [ ] Tests webhooks n8n
- [ ] Tests charge (500 contacts simultanés)

**Persona IA recommandée :** Claude (tests exhaustifs)

#### **ÉTAPE 6.2 : Optimisation performances** (2-3h)
**Tâches :**
- Analyse requêtes lentes (MySQL slow query log)
- Optimisation index Oracle
- Cache Vtiger (Redis/Memcached)
- Compression assets frontend

**Persona IA recommandée :** Gemini (optimisation DB)

#### **ÉTAPE 6.3 : Sécurité** (1-2h)
**Checklist :**
- [ ] Firewall configuré (UFW)
- [ ] SSL/TLS activé partout
- [ ] Passwords forts + 2FA si possible
- [ ] Audit permissions fichiers
- [ ] Backup automatisé configuré

**Persona IA recommandée :** Grok

---

### **PHASE 7 : DOCUMENTATION & FORMATION** (4-5h)

#### **ÉTAPE 7.1 : Documentation technique** (2-3h)
**Livrables :**
- README général projet
- Documentation API (Swagger/OpenAPI si applicable)
- Schémas architecture (draw.io, Mermaid)
- Guide installation depuis zéro
- Guide troubleshooting

**Persona IA recommandée :** Claude (documentation précise)

#### **ÉTAPE 7.2 : Guides utilisateurs** (2h)
**Livrables :**
- Manuel agent (utilisation CRM)
- Manuel admin (configuration règles)
- Vidéos courtes (screencast) si possible
- FAQ

**Persona IA recommandée :** Grok (rédaction rapide)

---

### **PHASE 8 : MIGRATION PRODUCTION** (6-8h)

#### **ÉTAPE 8.1 : Setup Oracle Cloud** (2-3h)
**Tâches :**
- Création compte Oracle Cloud
- Provisioning VM Arm (4 cores, 24GB RAM)
- Configuration réseau (firewall, IP publique)
- Installation Docker + Docker Compose

**Persona IA recommandée :** Gemini (cloud infra)

**Template prompt :**
```
Tu es un expert Oracle Cloud Infrastructure (OCI).

CONTEXTE:
Je déploie une stack complète (Vtiger, Nextcloud, FreeScout, n8n) 
sur Oracle Cloud Free Tier (VM Arm).

OBJECTIF:
Guide complet deployment:
1. Provisioning VM optimale
2. Configuration réseau/sécurité
3. Installation Docker
4. Setup domaines et SSL (Let's Encrypt)

CONTRAINTES:
- Free Tier uniquement
- VM Arm Ampere (4 cores, 24GB)
- 200GB storage
- Haute disponibilité souhaitée

LIVRABLES:
1. Commandes CLI OCI (Terraform idéalement)
2. Configuration Docker Compose
3. Configuration nginx reverse proxy
4. Scripts backup automatisés

Commence par expliquer le sizing optimal des ressources.
```

#### **ÉTAPE 8.2 : Dockerisation** (2-3h)
**Tâches :**
- Dockerfile pour chaque app
- Docker Compose orchestration
- Volumes persistants
- Networks isolés

**Persona IA recommandée :** Claude (Docker expert)

#### **ÉTAPE 8.3 : Déploiement & Tests** (2h)
**Tâches :**
- Push images Docker
- Deploy sur Oracle Cloud
- Migration données (dump/restore Oracle)
- Tests E2E production
- Monitoring setup (Prometheus/Grafana ou simple)

**Persona IA recommandée :** Grok

---

## 📊 MATRICE RESPONSABILITÉS IA

| Module | Claude | Grok | Gemini | Justification |
|--------|--------|------|--------|---------------|
| Extracteur Python | ⭐⭐⭐ | ⭐ | ⭐⭐ | Claude excelle en architecture complexe |
| Schéma Oracle | ⭐⭐ | ⭐ | ⭐⭐⭐ | Gemini fort en SQL/DB design |
| Sync Oracle↔Vtiger | ⭐⭐⭐ | ⭐ | ⭐⭐ | Claude meilleur intégrations API |
| Config Vtiger | ⭐⭐⭐ | ⭐⭐ | ⭐ | Claude doc précise |
| Modules custom Vtiger | ⭐⭐⭐ | ⭐ | ⭐⭐ | Claude logique métier complexe |
| Intégration Ringover | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | Gemini excellent webhooks/APIs |
| n8n Workflows | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | Gemini visuel/automation |
| Nextcloud setup | ⭐⭐ | ⭐⭐⭐ | ⭐ | Grok rapide tâches standard |
| FreeScout setup | ⭐⭐ | ⭐⭐⭐ | ⭐ | Grok efficace install classique |
| Tests unitaires | ⭐⭐⭐ | ⭐ | ⭐⭐ | Claude exhaustif tests |
| Optimisation perf | ⭐⭐ | ⭐ | ⭐⭐⭐ | Gemini fort optimisation DB |
| Sécurité | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | Grok pragmatique sécurité |
| Documentation | ⭐⭐⭐ | ⭐⭐ | ⭐ | Claude précision rédaction |
| Oracle Cloud deploy | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ | Gemini fort cloud infra |
| Dockerisation | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | Claude containerisation expert |

**Légende :** ⭐⭐⭐ = Recommandé | ⭐⭐ = Bon | ⭐ = Acceptable

---

## 🔄 DÉPENDANCES & ORDRE D'EXÉCUTION

### **Séquence critique (bloquante) :**
```
1. Extracteur Python ──► 2. Schéma Oracle ──► 3. Tests données
                                │
                                ▼
                    4. Installation Vtiger ──► 5. Config base Vtiger
                                                      │
                                                      ▼
                                        6. Sync Oracle↔Vtiger
```

### **Tâches parallélisables :**
```
Après étape 5, en parallèle:
├─ Modules custom Vtiger
├─ Installation Nextcloud
├─ Installation FreeScout
└─ Setup n8n
```

### **Finalisation séquentielle :**
```
Tous modules prêts ──► Intégration Ringover ──► Tests E2E ──► Documentation ──► Migration prod
```

---

## ✅ CHECKLIST VALIDATION PAR PHASE

### **Phase 1 : Fondations Données**
- [ ] Extracteur extrait données de toutes sources configurées
- [ ] Données insérées dans Oracle sans erreurs
- [ ] Logs clairs et complets générés
- [ ] Mode incrémental fonctionne correctement
- [ ] Schéma Oracle validé (ERD conforme)
- [ ] Procédures stockées testées
- [ ] Performance acceptable (<5s pour 1000 inserts)

### **Phase 2 : Infrastructure CRM**
- [ ] Vtiger accessible via navigateur
- [ ] Login admin fonctionne
- [ ] Modules standard opérationnels
- [ ] Champs custom créés et visibles
- [ ] Premier dashboard affiché correctement

### **Phase 3 : Synchronisation**
- [ ] Sync Oracle → Vtiger : contacts créés automatiquement
- [ ] Sync bidirectionnelle : modifications reflétées des 2 côtés
- [ ] Gestion conflits testée et validée
- [ ] Aucune perte de données sur 100 tests
- [ ] Logs sync accessibles et clairs

### **Phase 4 : Modules Avancés**
- [ ] Règles horaires configurables via interface
- [ ] Fonction get_next_slot retourne créneaux corrects
- [ ] Workflows emails envoyés automatiquement
- [ ] Notifications RDV reçues J-1
- [ ] Ringover: click-to-call fonctionne
- [ ] Ringover: appels entrants loggés dans Vtiger
- [ ] Popup fiche contact <1s après appel entrant

### **Phase 5 : Apps Complémentaires**
- [ ] Nextcloud accessible et stockage fonctionne
- [ ] Calendriers Nextcloud synchro avec Vtiger
- [ ] FreeScout reçoit emails et crée tickets
- [ ] Lien tickets FreeScout ↔ contacts Vtiger

### **Phase 6 : Tests & Optimisation**
- [ ] Tests charge: 500 contacts simultanés sans crash
- [ ] Pages CRM chargent en <2s
- [ ] Requêtes Oracle optimisées (<100ms avg)
- [ ] Aucune faille sécurité détectée (scan basique)
- [ ] Backups automatiques configurés et testés

### **Phase 7 : Documentation**
- [ ] README principal complet et à jour
- [ ] Guides utilisateurs rédigés
- [ ] Schémas architecture exportés
- [ ] FAQ complétée avec problèmes courants

### **Phase 8 : Migration Prod**
- [ ] VM Oracle Cloud provisionnée
- [ ] Docker Compose déployé avec succès
- [ ] SSL Let's Encrypt actif
- [ ] Toutes apps accessibles en HTTPS
- [ ] Données migrées sans perte
- [ ] Tests E2E prod validés
- [ ] Monitoring basique opérationnel

---

## 🎯 TEMPLATES PROMPTS GÉNÉRIQUES

### **Pour architecture/design :**
```
Tu es [RÔLE EXPERT] avec [X] années d'expérience en [DOMAINE].

CONTEXTE:
[Description projet et contraintes]

OBJECTIF:
[Ce qui doit être accompli précisément]

CONTRAINTES:
- [Technique 1]
- [Technique 2]
- [Performance/Budget]

LIVRABLES ATTENDUS:
1. [Livrable 1]
2. [Livrable 2]
3. [Documentation/tests]

Commence par [action initiale - ex: proposer architecture].
```

### **Pour implémentation code :**
```
Tu es un développeur senior [LANGAGE/FRAMEWORK].

CONTEXTE:
[Description fonctionnalité à implémenter]

SPÉCIFICATIONS:
- [Spec 1]
- [Spec 2]
- [Spec 3]

CONTRAINTES TECHNIQUES:
- Langage: [X]
- Version: [Y]
- Dépendances autorisées: [liste]
- Performance cible: [métrique]

LIVRABLES:
1. Code source complet et commenté
2. Tests unitaires
3. Documentation inline
4. Exemple d'utilisation

IMPORTANT: [Instructions spécifiques - ex: pas de bibliothèques externes]

Commence par proposer la structure du code.
```

### **Pour debugging :**
```
Tu es un expert debugging [TECHNOLOGIE].

PROBLÈME:
[Description erreur observée]

CONTEXTE:
- Environnement: [OS, versions]
- Code concerné: [extrait si dispo]
- Logs d'erreur: [copier-coller]
- Comportement attendu vs réel

OBJECTIF:
Identifier la cause et proposer solution(s).

Commence par analyser les logs.
```

---

## 📈 INDICATEURS SUCCÈS PROJET

### **Métriques techniques :**
- ✅ Uptime >99% sur 1 mois
- ✅ Temps réponse pages <2s (95e percentile)
- ✅ Sync Oracle↔Vtiger: <5 min latence
- ✅ Zéro perte données sur tests charge
- ✅ Click-to-call Ringover: <1s latence

### **Métriques métier :**
- ✅ 100% contacts Oracle dans Vtiger
- ✅ Règles horaires respectées (0 erreur routage)
- ✅ Emails qualifications envoyés à 100%
- ✅ RDV confirmés passent de [X]% à [Y]%
- ✅ Temps traitement contact réduit de 40%

### **Métriques adoption :**
- ✅ 100% agents formés et autonomes
- ✅ Satisfaction agents >8/10
- ✅ Zéro escalade technique semaine 2

---

## 🚨 RISQUES & MITIGATION

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Bug extracteur perte données | Moyenne | Critique | Mode dry-run obligatoire, backup avant chaque sync |
| Oracle Cloud quota dépassé | Faible | Élevé | Monitoring usage, alertes 80% quota |
| Ringover API rate limit | Moyenne | Moyen | Cache appels, throttling requests |
| Vtiger perf dégradées | Moyenne | Moyen | Cache Redis, optimisation requêtes |
| Complexité migration prod | Élevée | Moyen | Tests exhaustifs en staging, rollback plan |
| Intégration n8n instable | Moyenne | Moyen | Retry logic, monitoring workflows |

---

## 📚 RESSOURCES & DOCUMENTATION

### **APIs officielles :**
- Vtiger API: https://code.vtiger.com/vtiger/vtigercrm/-/wikis/Webservices-API
- Ringover API: https://developers.ringover.com/
- Oracle cx_Oracle: https://oracle.github.io/python-cx_Oracle/

### **Documentation produits :**
- Vtiger Docs: https://www.vtiger.com/docs/
- Nextcloud Admin: https://docs.nextcloud.com/
- FreeScout: https://docs.freescout.net/
- n8n: https://docs.n8n.io/

### **Outils dev :**
- Oracle Cloud CLI: https://docs.oracle.com/en-us/iaas/Content/API/Concepts/cliconcepts.htm
- Docker Docs: https://docs.docker.com/
- Python best practices: https://docs.python-guide.org/

---

## 🎓 FORMATION CONTINUE

### **Pendant le projet :**
- [ ] Veille quotidienne changelog Vtiger
- [ ] Tests réguliers nouvelles features n8n
- [ ] Monitoring discussions Oracle Cloud forums

### **Après déploiement :**
- [ ] Formation agents (2 sessions)
- [ ] Formation admins (1 session approfondie)
- [ ] Documentation interne wiki/confluence

---

## 🔄 MAINTENANCE POST-DÉPLOIEMENT

### **Quotidien :**
- Monitoring logs erreurs
- Vérification sync Oracle↔Vtiger
- Backup automatique

### **Hebdomadaire :**
- Revue tickets support
- Optimisation requêtes lentes
- Nettoyage logs anciens

### **Mensuel :**
- Updates sécurité (OS, apps)
- Revue performances
- Feedback utilisateurs

### **Trimestriel :**
- Évaluation ajout features
- Audit sécurité complet
- Revue architecture scaling

---

## 📞 CONTACT & SUPPORT

**Pendant développement :**
- Claude: Architecture, code complexe, intégrations
- Grok: Setup rapide, sysadmin, sécurité
- Gemini: SQL, APIs, cloud infra

**Post-déploiement :**
- Documentation interne: [lien wiki]
- Support technique: [email/slack]
- Escalade urgente: [téléphone]

---

## ✨ CONCLUSION

Ce projet est ambitieux mais totalement réalisable avec:
- ✅ Découpage modulaire intelligent
- ✅ Distribution tâches sur IA multiples
- ✅ Fondations solides (extracteur + Oracle)
- ✅ Tests exhaustifs
- ✅ Documentation continue

**Prochaine action:** Démarrer PHASE 1 - Extracteur Python

**Durée totale estimée :** 60-80 heures réparties sur 3-6 semaines

---

**Date dernière mise à jour :** 23 Octobre 2025  
**Version document :** 1.0  
**Auteur :** Claude (Anthropic) + Équipe projet
