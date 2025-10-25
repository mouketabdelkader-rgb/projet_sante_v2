-- =============================================
-- PROCÉDURES STOCKÉES ET FONCTIONS
-- =============================================

-- Procédure 1 : Merge Contact Multi-Sources
CREATE OR REPLACE PROCEDURE sp_merge_contact(
    p_id_professionnel VARCHAR2,
    p_type_contact VARCHAR2,
    p_valeur VARCHAR2,
    p_source VARCHAR2,
    p_priorite NUMBER DEFAULT 50
) AS
    v_existing_id NUMBER;
    v_existing_priorite NUMBER;
BEGIN
    -- Vérifie si le contact existe déjà
    BEGIN
        SELECT id_contact, priorite 
        INTO v_existing_id, v_existing_priorite
        FROM contacts
        WHERE id_professionnel = p_id_professionnel
          AND type_contact = p_type_contact
          AND UPPER(valeur) = UPPER(p_valeur)
          AND ROWNUM = 1;
        
        -- Update si la nouvelle source est plus prioritaire
        IF p_priorite > v_existing_priorite THEN
            UPDATE contacts
            SET source_origine = p_source,
                priorite = p_priorite,
                date_derniere_utilisation = SYSDATE
            WHERE id_contact = v_existing_id;
        END IF;
        
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            -- Insert si nouveau contact
            INSERT INTO contacts (
                id_professionnel, type_contact, valeur, 
                source_origine, priorite, date_collecte
            ) VALUES (
                p_id_professionnel, p_type_contact, p_valeur,
                p_source, p_priorite, SYSDATE
            );
    END;
    
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE_APPLICATION_ERROR(-20001, 
            'Erreur sp_merge_contact: ' || SQLERRM);
END sp_merge_contact;
/

COMMENT ON PROCEDURE sp_merge_contact IS 'Fusionne les contacts en évitant les doublons, priorise par source';

-- Fonction 1 : Calcul Score Qualification
CREATE OR REPLACE FUNCTION fn_score_qualification(
    p_id_professionnel VARCHAR2
) RETURN NUMBER AS
    v_score NUMBER := 0;
    v_has_tel NUMBER := 0;
    v_has_email NUMBER := 0;
    v_is_recent NUMBER := 0;
BEGIN
    -- +50 si téléphone
    SELECT COUNT(*) INTO v_has_tel
    FROM contacts 
    WHERE id_professionnel = p_id_professionnel 
      AND type_contact = 'TELEPHONE'
      AND ROWNUM = 1;
    
    IF v_has_tel > 0 THEN
        v_score := v_score + 50;
    END IF;
    
    -- +30 si email
    SELECT COUNT(*) INTO v_has_email
    FROM contacts 
    WHERE id_professionnel = p_id_professionnel 
      AND type_contact = 'EMAIL'
      AND ROWNUM = 1;
    
    IF v_has_email > 0 THEN
        v_score := v_score + 30;
    END IF;
    
    -- +20 si nouveau (<1 an)
    SELECT COUNT(*) INTO v_is_recent
    FROM professionnels 
    WHERE id_professionnel = p_id_professionnel
      AND date_premiere_apparition >= ADD_MONTHS(SYSDATE, -12)
      AND ROWNUM = 1;
    
    IF v_is_recent > 0 THEN
        v_score := v_score + 20;
    END IF;
    
    RETURN v_score;
EXCEPTION
    WHEN OTHERS THEN
        RETURN 0;
END fn_score_qualification;
/

COMMENT ON FUNCTION fn_score_qualification IS 'Calcule un score 0-100 selon disponibilité contacts et ancienneté';

-- Procédure 2 : Nettoyage Logs Anciens
CREATE OR REPLACE PROCEDURE sp_clean_old_logs(
    p_retention_days NUMBER DEFAULT 365
) AS
    v_cutoff_date DATE;
    v_deleted NUMBER;
BEGIN
    v_cutoff_date := SYSDATE - p_retention_days;
    
    -- Supprime les logs anciens
    DELETE FROM import_logs 
    WHERE date_import < v_cutoff_date;
    
    v_deleted := SQL%ROWCOUNT;
    
    -- Log l'opération de nettoyage
    INSERT INTO import_logs(
        type_import, script_execute, statut, 
        nb_lignes_traitees, message_log
    ) VALUES (
        'MAINTENANCE', 'sp_clean_old_logs', 'SUCCESS',
        v_deleted, 'Supprimé ' || v_deleted || ' logs avant ' || 
        TO_CHAR(v_cutoff_date, 'DD/MM/YYYY')
    );
    
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE_APPLICATION_ERROR(-20002, 
            'Erreur sp_clean_old_logs: ' || SQLERRM);
END sp_clean_old_logs;
/

COMMENT ON PROCEDURE sp_clean_old_logs IS 'Purge les logs plus anciens que X jours (défaut 365)';

-- Procédure 3 : Créer Snapshot Mensuel
CREATE OR REPLACE PROCEDURE sp_create_snapshot(
    p_nom_fichier VARCHAR2,
    p_url_source VARCHAR2 DEFAULT NULL
) AS
    v_id_snapshot NUMBER;
    v_annee NUMBER;
    v_mois NUMBER;
    v_nb_total NUMBER;
    v_nb_actifs NUMBER;
BEGIN
    v_annee := EXTRACT(YEAR FROM SYSDATE);
    v_mois := EXTRACT(MONTH FROM SYSDATE);
    
    -- Compte les professionnels
    SELECT COUNT(*) INTO v_nb_total FROM professionnels;
    SELECT COUNT(*) INTO v_nb_actifs 
    FROM professionnels WHERE statut_enregistrement = 'Actif';
    
    -- Insère le snapshot
    INSERT INTO snapshots_mensuels (
        annee, mois, date_snapshot, nom_fichier_rpps, url_source,
        nb_professionnels_total, nb_professionnels_actifs,
        statut_import
    ) VALUES (
        v_annee, v_mois, SYSDATE, p_nom_fichier, p_url_source,
        v_nb_total, v_nb_actifs, 'SUCCESS'
    ) RETURNING id_snapshot INTO v_id_snapshot;
    
    COMMIT;
    
    DBMS_OUTPUT.PUT_LINE('Snapshot créé - ID: ' || v_id_snapshot);
EXCEPTION
    WHEN DUP_VAL_ON_INDEX THEN
        -- Snapshot du mois déjà existant
        UPDATE snapshots_mensuels
        SET date_snapshot = SYSDATE,
            nom_fichier_rpps = p_nom_fichier,
            nb_professionnels_total = v_nb_total,
            nb_professionnels_actifs = v_nb_actifs
        WHERE annee = v_annee AND mois = v_mois;
        COMMIT;
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE_APPLICATION_ERROR(-20003, 
            'Erreur sp_create_snapshot: ' || SQLERRM);
END sp_create_snapshot;
/

COMMENT ON PROCEDURE sp_create_snapshot IS 'Crée un instantané mensuel de l''état de la base';

-- Procédure 4 : Détecter Changements (pour imports futurs)
CREATE OR REPLACE PROCEDURE sp_detect_changes(
    p_id_snapshot NUMBER,
    p_id_professionnel VARCHAR2,
    p_old_hash VARCHAR2,
    p_new_hash VARCHAR2
) AS
BEGIN
    -- Si les hash diffèrent, c'est une modification
    IF p_old_hash IS NULL THEN
        -- Nouveau professionnel
        INSERT INTO changements_detectes (
            id_snapshot, id_professionnel, type_changement,
            table_concernee, valeur_nouvelle
        ) VALUES (
            p_id_snapshot, p_id_professionnel, 'NOUVEAU',
            'PROFESSIONNELS', p_new_hash
        );
    ELSIF p_old_hash != p_new_hash THEN
        -- Modification
        INSERT INTO changements_detectes (
            id_snapshot, id_professionnel, type_changement,
            table_concernee, valeur_ancienne, valeur_nouvelle
        ) VALUES (
            p_id_snapshot, p_id_professionnel, 'MODIFICATION',
            'PROFESSIONNELS', p_old_hash, p_new_hash
        );
    END IF;
    
    COMMIT;
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK;
        RAISE_APPLICATION_ERROR(-20004, 
            'Erreur sp_detect_changes: ' || SQLERRM);
END sp_detect_changes;
/

COMMENT ON PROCEDURE sp_detect_changes IS 'Détecte et enregistre les changements entre 2 imports';

-- Fonction 2 : Calculer Hash Professionnel
CREATE OR REPLACE FUNCTION fn_calculate_hash(
    p_nom VARCHAR2,
    p_prenom VARCHAR2,
    p_code_profession VARCHAR2,
    p_statut VARCHAR2
) RETURN VARCHAR2 AS
    v_concat_string VARCHAR2(1000);
    v_hash RAW(256);
BEGIN
    v_concat_string := UPPER(TRIM(p_nom)) || '|' || 
                       UPPER(TRIM(p_prenom)) || '|' || 
                       TRIM(p_code_profession) || '|' || 
                       TRIM(p_statut);
    
    v_hash := DBMS_CRYPTO.HASH(
        UTL_RAW.CAST_TO_RAW(v_concat_string),
        DBMS_CRYPTO.HASH_SH256
    );
    
    RETURN RAWTOHEX(v_hash);
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END fn_calculate_hash;
/

COMMENT ON FUNCTION fn_calculate_hash IS 'Calcule un hash SHA256 pour détecter les modifications';

-- =============================================
-- Compilation
-- =============================================
COMMIT;

PROMPT '============================================='
PROMPT '4 procédures et 2 fonctions créées avec succès !'
PROMPT '============================================='
