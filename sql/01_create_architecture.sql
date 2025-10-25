-- =============================================
-- PROJET : Système d'extraction et enrichissement automatisé de professionnels de santé
-- PHASE : Étape 1 - Fondations données
-- VERSION : 2.0 - Architecture 4 couches (12 tables)
-- DATE : 23 Octobre 2025
-- =============================================

-- ORDRE D'EXÉCUTION :
-- 1. Suppression des anciennes tables (si refonte)
-- 2. Création des tables (couches 1-3)
-- 3. Création des index
-- 4. Création des vues métier
-- 5. Création des procédures stockées
-- 6. Création des triggers

-- =============================================
-- NETTOYAGE : Suppression des anciennes tables et index
-- =============================================
BEGIN
    -- Supprimer les tables
    FOR t IN (SELECT table_name FROM user_tables 
              WHERE table_name IN (
                  'QUALIFICATIONS', 'CONTACTS', 'ADRESSES', 'STRUCTURES', 'ACTIVITES', 'PROFESSIONNELS',
                  'RESEAUX_SOCIAUX', 'SOURCES_ENTREPRISES', 'ENRICHISSEMENT_CONTACTS',
                  'IMPORT_LOGS', 'CHANGEMENTS_DETECTES', 'SNAPSHOTS_MENSUELS'
              )) LOOP
        EXECUTE IMMEDIATE 'DROP TABLE ' || t.table_name || ' CASCADE CONSTRAINTS';
    END LOOP;
    
    -- Supprimer les index restants (pas liés aux tables)
    FOR i IN (SELECT index_name FROM user_indexes 
              WHERE index_name LIKE 'IDX_%' 
              AND index_name NOT LIKE 'SYS_%') LOOP
        BEGIN
            EXECUTE IMMEDIATE 'DROP INDEX ' || i.index_name;
        EXCEPTION
            WHEN OTHERS THEN NULL;  -- Ignorer si déjà supprimé avec la table
        END;
    END LOOP;
END;
/

-- =============================================
-- COUCHE 1 : DONNÉES CORE (6 tables)
-- =============================================

-- Table 1 : PROFESSIONNELS (Master ~2.2M lignes)
CREATE TABLE professionnels (
    id_professionnel VARCHAR2(20) PRIMARY KEY,
    nom VARCHAR2(100) NOT NULL,
    prenom VARCHAR2(100),
    nom_exercice VARCHAR2(100),
    civilite VARCHAR2(10),
    code_profession VARCHAR2(10),
    libelle_profession VARCHAR2(200),
    categorie_profession VARCHAR2(50),
    date_naissance DATE,
    statut_enregistrement VARCHAR2(50) DEFAULT 'Actif',
    date_premiere_apparition DATE DEFAULT SYSDATE,
    date_derniere_maj DATE DEFAULT SYSDATE,
    date_import DATE DEFAULT SYSDATE,
    source_data VARCHAR2(50) DEFAULT 'RPPS',
    hash_data VARCHAR2(64)
);

COMMENT ON TABLE professionnels IS 'Table master contenant tous les professionnels de santé (RPPS)';
COMMENT ON COLUMN professionnels.id_professionnel IS 'Identifiant RPPS unique';
COMMENT ON COLUMN professionnels.hash_data IS 'Hash SHA256 pour détection des changements';
COMMENT ON COLUMN professionnels.categorie_profession IS 'Médecin, Paramédical, etc.';

-- Table 2 : ACTIVITES (~3M lignes)
CREATE TABLE activites (
    id_activite NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL,
    code_savoir_faire VARCHAR2(10),
    libelle_savoir_faire VARCHAR2(200),
    mode_exercice VARCHAR2(100),
    secteur_activite VARCHAR2(50),
    date_debut_activite DATE,
    date_fin_activite DATE,
    statut_activite VARCHAR2(50) DEFAULT 'Actif',
    id_structure NUMBER,
    date_import DATE DEFAULT SYSDATE,
    CONSTRAINT fk_act_prof FOREIGN KEY (id_professionnel) 
        REFERENCES professionnels(id_professionnel) ON DELETE CASCADE
);

COMMENT ON TABLE activites IS 'Activités et modes d''exercice des professionnels';
COMMENT ON COLUMN activites.mode_exercice IS 'Lib,indép,artis,com / Salarié';

-- Table 3 : STRUCTURES (~500k lignes)
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

COMMENT ON TABLE structures IS 'Structures d''exercice (cabinets, cliniques, hôpitaux)';

-- Table 4 : ADRESSES (~2.5M lignes)
CREATE TABLE adresses (
    id_adresse NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20),
    id_structure NUMBER,
    type_adresse VARCHAR2(50),
    numero_voie VARCHAR2(10),
    type_voie VARCHAR2(50),
    libelle_voie VARCHAR2(200),
    complement_adresse VARCHAR2(200),
    code_postal VARCHAR2(5),
    commune VARCHAR2(100),
    code_commune_insee VARCHAR2(5),
    departement VARCHAR2(3),
    region VARCHAR2(50),
    pays VARCHAR2(50) DEFAULT 'France',
    latitude NUMBER(10,8),
    longitude NUMBER(11,8),
    date_import DATE DEFAULT SYSDATE,
    CONSTRAINT fk_adr_prof FOREIGN KEY (id_professionnel) 
        REFERENCES professionnels(id_professionnel) ON DELETE CASCADE,
    CONSTRAINT fk_adr_struct FOREIGN KEY (id_structure) 
        REFERENCES structures(id_structure) ON DELETE CASCADE
);

COMMENT ON TABLE adresses IS 'Adresses postales des professionnels et structures';
COMMENT ON COLUMN adresses.type_adresse IS 'Exercice, Correspondance';

-- Table 5 : CONTACTS (~5M lignes)
CREATE TABLE contacts (
    id_contact NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20),
    id_structure NUMBER,
    type_contact VARCHAR2(20) NOT NULL,
    valeur VARCHAR2(200) NOT NULL,
    categorie VARCHAR2(50),
    priorite NUMBER DEFAULT 50,
    statut_validation VARCHAR2(20) DEFAULT 'A_Verifier',
    source_origine VARCHAR2(50),
    date_collecte DATE DEFAULT SYSDATE,
    opt_in_marketing CHAR(1) DEFAULT 'N',
    date_opt_in DATE,
    date_derniere_utilisation DATE,
    nombre_tentatives NUMBER DEFAULT 0,
    date_import DATE DEFAULT SYSDATE,
    CONSTRAINT fk_contact_prof FOREIGN KEY (id_professionnel) 
        REFERENCES professionnels(id_professionnel) ON DELETE CASCADE,
    CONSTRAINT fk_contact_struct FOREIGN KEY (id_structure) 
        REFERENCES structures(id_structure) ON DELETE CASCADE,
    CONSTRAINT chk_type_contact CHECK (type_contact IN ('TELEPHONE', 'EMAIL', 'FAX', 'SITE_WEB'))
);

COMMENT ON TABLE contacts IS 'Coordonnées de contact (téléphone, email, etc.)';
COMMENT ON COLUMN contacts.type_contact IS 'TELEPHONE, EMAIL, FAX, SITE_WEB';
COMMENT ON COLUMN contacts.priorite IS 'Score 1-100 pour priorisation';
COMMENT ON COLUMN contacts.source_origine IS 'RPPS, SIRENE, ENRICHISSEMENT';

-- Table 6 : QUALIFICATIONS (~3M lignes)
CREATE TABLE qualifications (
    id_qualification NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL,
    type_qualification VARCHAR2(50),
    code_qualification VARCHAR2(20),
    libelle_qualification VARCHAR2(200),
    date_obtention DATE,
    date_debut_validite DATE,
    date_fin_validite DATE,
    date_import DATE DEFAULT SYSDATE,
    CONSTRAINT fk_qual_prof FOREIGN KEY (id_professionnel) 
        REFERENCES professionnels(id_professionnel) ON DELETE CASCADE
);

COMMENT ON TABLE qualifications IS 'Diplômes, certifications et qualifications';

-- =============================================
-- COUCHE 2 : ENRICHISSEMENT (3 tables)
-- =============================================

-- Table 7 : ENRICHISSEMENT_CONTACTS (~10M lignes à terme)
CREATE TABLE enrichissement_contacts (
    id_enrichissement NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL,
    type_donnee VARCHAR2(50),
    valeur VARCHAR2(500),
    source_enrichissement VARCHAR2(100),
    url_source VARCHAR2(500),
    methode_collecte VARCHAR2(50),
    score_confiance NUMBER(3,2),
    statut_verification VARCHAR2(20),
    date_collecte DATE DEFAULT SYSDATE,
    date_verification DATE,
    metadata_json CLOB,
    CONSTRAINT fk_enr_prof FOREIGN KEY (id_professionnel) 
        REFERENCES professionnels(id_professionnel) ON DELETE CASCADE,
    CONSTRAINT chk_score CHECK (score_confiance BETWEEN 0 AND 1)
);

COMMENT ON TABLE enrichissement_contacts IS 'Données enrichies depuis sources externes';
COMMENT ON COLUMN enrichissement_contacts.source_enrichissement IS 'SIRENE, PAGES_JAUNES, DOCTOLIB, etc.';
COMMENT ON COLUMN enrichissement_contacts.score_confiance IS 'Score 0.00 à 1.00';

-- Table 8 : SOURCES_ENTREPRISES (~1M lignes)
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
    source_origine VARCHAR2(50),
    date_collecte DATE DEFAULT SYSDATE,
    data_json CLOB
);

COMMENT ON TABLE sources_entreprises IS 'Données SIRENE/INPI des structures d''exercice';

-- Table 9 : RESEAUX_SOCIAUX (~500k lignes)
CREATE TABLE reseaux_sociaux (
    id_reseau_social NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_professionnel VARCHAR2(20) NOT NULL,
    plateforme VARCHAR2(50),
    url_profil VARCHAR2(500),
    identifiant_profil VARCHAR2(200),
    nom_affiche VARCHAR2(200),
    bio_description CLOB,
    photo_profil_url VARCHAR2(500),
    nombre_connexions NUMBER,
    date_collecte DATE DEFAULT SYSDATE,
    date_derniere_activite DATE,
    statut_profil VARCHAR2(20),
    CONSTRAINT fk_rs_prof FOREIGN KEY (id_professionnel) 
        REFERENCES professionnels(id_professionnel) ON DELETE CASCADE
);

COMMENT ON TABLE reseaux_sociaux IS 'Profils LinkedIn, Facebook, Twitter, etc.';

-- =============================================
-- COUCHE 3 : HISTORISATION (3 tables)
-- =============================================

-- Table 10 : SNAPSHOTS_MENSUELS (~12/an)
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
    statut_import VARCHAR2(20),
    logs_import CLOB,
    CONSTRAINT uq_snap_periode UNIQUE (annee, mois)
);

COMMENT ON TABLE snapshots_mensuels IS 'Historique des imports mensuels RPPS';

-- Table 11 : CHANGEMENTS_DETECTES (~200k/mois)
CREATE TABLE changements_detectes (
    id_changement NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_snapshot NUMBER NOT NULL,
    id_professionnel VARCHAR2(20) NOT NULL,
    type_changement VARCHAR2(50),
    table_concernee VARCHAR2(50),
    champ_concerne VARCHAR2(100),
    valeur_ancienne VARCHAR2(500),
    valeur_nouvelle VARCHAR2(500),
    date_detection DATE DEFAULT SYSDATE,
    CONSTRAINT fk_chg_snap FOREIGN KEY (id_snapshot) 
        REFERENCES snapshots_mensuels(id_snapshot) ON DELETE CASCADE
);

COMMENT ON TABLE changements_detectes IS 'Détection des modifications entre 2 imports';
COMMENT ON COLUMN changements_detectes.type_changement IS 'NOUVEAU, MODIFICATION, RADIATION';

-- Table 12 : IMPORT_LOGS (~100/mois)
CREATE TABLE import_logs (
    id_log NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date_import DATE DEFAULT SYSDATE,
    type_import VARCHAR2(50),
    script_execute VARCHAR2(100),
    statut VARCHAR2(20),
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

COMMENT ON TABLE import_logs IS 'Journal technique des exécutions de scripts';
COMMENT ON COLUMN import_logs.statut IS 'RUNNING, SUCCESS, FAILED';

-- =============================================
-- INDEX POUR PERFORMANCES
-- =============================================

-- =============================================
-- SECTION 3 : INDEX (Performance)
-- IMPORTANT: Autonomous Database accepte uniquement les index SIMPLES
-- Aucune option physique (TABLESPACE, STORAGE, etc.) ne doit être spécifiée
-- =============================================

-- Index PROFESSIONNELS (6 index)
CREATE INDEX idx_prof_nom ON professionnels(nom);
CREATE INDEX idx_prof_prenom ON professionnels(prenom);
CREATE INDEX idx_prof_code_profession ON professionnels(code_profession);
CREATE INDEX idx_prof_categorie ON professionnels(categorie_profession);
CREATE INDEX idx_prof_statut ON professionnels(statut_enregistrement);
CREATE INDEX idx_prof_date_maj ON professionnels(date_derniere_maj);

-- Index ACTIVITES (4 index)
CREATE INDEX idx_act_prof ON activites(id_professionnel);
CREATE INDEX idx_act_mode ON activites(mode_exercice);
CREATE INDEX idx_act_statut ON activites(statut_activite);
CREATE INDEX idx_act_structure ON activites(id_structure);

-- Index STRUCTURES (3 index)
CREATE INDEX idx_struct_siret ON structures(siret);
CREATE INDEX idx_struct_finess ON structures(finess);
CREATE INDEX idx_struct_type ON structures(type_structure);

-- Index ADRESSES (4 index)
CREATE INDEX idx_adr_prof ON adresses(id_professionnel);
CREATE INDEX idx_adr_struct ON adresses(id_structure);
CREATE INDEX idx_adr_postal ON adresses(code_postal);
CREATE INDEX idx_adr_commune ON adresses(commune);

-- Index CONTACTS (4 index)
CREATE INDEX idx_contact_prof ON contacts(id_professionnel);
CREATE INDEX idx_contact_type ON contacts(type_contact);
CREATE INDEX idx_contact_valeur ON contacts(valeur);
CREATE INDEX idx_contact_source ON contacts(source_origine);

-- Index QUALIFICATIONS (2 index)
CREATE INDEX idx_qual_prof ON qualifications(id_professionnel);
CREATE INDEX idx_qual_type ON qualifications(type_qualification);

-- Index ENRICHISSEMENT_CONTACTS (3 index)
CREATE INDEX idx_enr_prof ON enrichissement_contacts(id_professionnel);
CREATE INDEX idx_enr_type ON enrichissement_contacts(type_donnee);
CREATE INDEX idx_enr_source ON enrichissement_contacts(source_enrichissement);

-- Index SOURCES_ENTREPRISES (3 index)
CREATE INDEX idx_src_siret ON sources_entreprises(siret);
CREATE INDEX idx_src_siren ON sources_entreprises(siren);
CREATE INDEX idx_src_source ON sources_entreprises(source_origine);

-- Index RESEAUX_SOCIAUX (2 index)
CREATE INDEX idx_rs_prof ON reseaux_sociaux(id_professionnel);
CREATE INDEX idx_rs_plateforme ON reseaux_sociaux(plateforme);

-- Index SNAPSHOTS (1 index)
CREATE INDEX idx_snap_date ON snapshots_mensuels(date_snapshot);

-- Index CHANGEMENTS (3 index)
CREATE INDEX idx_chg_prof ON changements_detectes(id_professionnel);
CREATE INDEX idx_chg_type ON changements_detectes(type_changement);
CREATE INDEX idx_chg_snap ON changements_detectes(id_snapshot);

-- Index IMPORT_LOGS (2 index)
CREATE INDEX idx_log_date ON import_logs(date_import);
CREATE INDEX idx_log_statut ON import_logs(statut);

-- Index LOGS
CREATE INDEX idx_log_date ON import_logs(date_import);
CREATE INDEX idx_log_type ON import_logs(type_import);
CREATE INDEX idx_log_statut ON import_logs(statut);

-- Index pour accélérer la recherche de structures par identifiant technique
CREATE INDEX idx_structures_id_tech ON structures(identifiant_technique);

-- Index pour accélérer le MERGE sur les contacts
CREATE INDEX idx_contacts_cles ON contacts(id_professionnel, type_contact, valeur);

-- =============================================
-- Compilation finale
-- =============================================
COMMIT;

PROMPT '============================================='
PROMPT 'Architecture créée avec succès !'
PROMPT '12 tables + 37 index créés'
PROMPT '============================================='