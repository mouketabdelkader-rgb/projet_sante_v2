-- =============================================
-- TRIGGERS AUTOMATIQUES
-- =============================================

-- Trigger 1 : Mise à jour automatique du timestamp
CREATE OR REPLACE TRIGGER trg_prof_update_timestamp
BEFORE UPDATE ON professionnels
FOR EACH ROW
BEGIN
    :NEW.date_derniere_maj := SYSDATE;
END;
/

COMMENT ON TRIGGER trg_prof_update_timestamp IS 'Met à jour automatiquement date_derniere_maj lors d''un UPDATE';

-- Trigger 2 : Calcul automatique du hash
CREATE OR REPLACE TRIGGER trg_prof_calculate_hash
BEFORE INSERT OR UPDATE ON professionnels
FOR EACH ROW
DECLARE
    v_concat_string VARCHAR2(1000);
BEGIN
    -- Calcule le hash uniquement si les données ont changé
    IF INSERTING OR 
       (:OLD.nom != :NEW.nom OR 
        :OLD.prenom != :NEW.prenom OR 
        :OLD.code_profession != :NEW.code_profession OR
        :OLD.statut_enregistrement != :NEW.statut_enregistrement) THEN
        
        v_concat_string := UPPER(TRIM(:NEW.nom)) || '|' || 
                          UPPER(TRIM(NVL(:NEW.prenom, ''))) || '|' || 
                          TRIM(:NEW.code_profession) || '|' || 
                          TRIM(:NEW.statut_enregistrement);
        
        :NEW.hash_data := RAWTOHEX(
            DBMS_CRYPTO.HASH(
                UTL_RAW.CAST_TO_RAW(v_concat_string),
                DBMS_CRYPTO.HASH_SH256
            )
        );
    END IF;
END;
/

COMMENT ON TRIGGER trg_prof_calculate_hash IS 'Calcule automatiquement le hash SHA256 à l''insertion/modification';

-- Trigger 3 : Validation format téléphone
CREATE OR REPLACE TRIGGER trg_contact_validate_phone
BEFORE INSERT OR UPDATE ON contacts
FOR EACH ROW
DECLARE
    v_clean_phone VARCHAR2(200);
BEGIN
    IF :NEW.type_contact = 'TELEPHONE' THEN
        -- Nettoie le téléphone (retire espaces, points, tirets)
        v_clean_phone := REGEXP_REPLACE(:NEW.valeur, '[^0-9+]', '');
        
        -- Validation basique : doit commencer par 0 ou +33 et avoir 10+ chiffres
        IF NOT (REGEXP_LIKE(v_clean_phone, '^(0|\+33)[0-9]{9,}$')) THEN
            -- Si invalide, marque comme à vérifier
            :NEW.statut_validation := 'Invalide';
        ELSE
            :NEW.valeur := v_clean_phone;
            IF :NEW.statut_validation IS NULL THEN
                :NEW.statut_validation := 'A_Verifier';
            END IF;
        END IF;
    END IF;
    
    IF :NEW.type_contact = 'EMAIL' THEN
        -- Validation basique email
        IF NOT REGEXP_LIKE(:NEW.valeur, '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$') THEN
            :NEW.statut_validation := 'Invalide';
        ELSE
            IF :NEW.statut_validation IS NULL THEN
                :NEW.statut_validation := 'A_Verifier';
            END IF;
        END IF;
    END IF;
END;
/

COMMENT ON TRIGGER trg_contact_validate_phone IS 'Valide et nettoie automatiquement téléphones et emails';

-- Trigger 4 : Log automatique des imports
CREATE OR REPLACE TRIGGER trg_log_import_duration
BEFORE UPDATE ON import_logs
FOR EACH ROW
WHEN (NEW.date_fin IS NOT NULL AND OLD.date_fin IS NULL)
BEGIN
    -- Calcule automatiquement la durée en secondes
    :NEW.duree_secondes := 
        ROUND((CAST(:NEW.date_fin AS DATE) - CAST(:NEW.date_debut AS DATE)) * 86400);
END;
/

COMMENT ON TRIGGER trg_log_import_duration IS 'Calcule automatiquement la durée d''exécution des imports';

-- Trigger 5 : Cascade soft delete (optionnel, désactivé par défaut)
-- Ce trigger permet de marquer comme inactif plutôt que de supprimer
/*
CREATE OR REPLACE TRIGGER trg_prof_soft_delete
BEFORE DELETE ON professionnels
FOR EACH ROW
BEGIN
    -- Au lieu de supprimer, on marque comme radié
    INSERT INTO professionnels (
        id_professionnel, nom, prenom, code_profession,
        libelle_profession, statut_enregistrement, 
        date_derniere_maj
    ) VALUES (
        :OLD.id_professionnel, :OLD.nom, :OLD.prenom, :OLD.code_profession,
        :OLD.libelle_profession, 'Radié', SYSDATE
    );
    
    -- Empêche la suppression réelle
    RAISE_APPLICATION_ERROR(-20005, 
        'Suppression interdite. Le professionnel a été marqué comme Radié.');
END;
/
*/

-- =============================================
-- Compilation
-- =============================================
COMMIT;

PROMPT '============================================='
PROMPT '4 triggers créés avec succès !'
PROMPT '============================================='
