-- Ajouter colonnes manquantes

-- 1. identifiant_technique dans structures
BEGIN
    EXECUTE IMMEDIATE 'ALTER TABLE structures ADD (identifiant_technique VARCHAR2(50))';
    DBMS_OUTPUT.PUT_LINE('✓ identifiant_technique ajoutée');
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE = -1430 THEN
            DBMS_OUTPUT.PUT_LINE('- identifiant_technique existe déjà');
        ELSE
            RAISE;
        END IF;
END;
/

-- 2. code_savoir_faire et libelle_savoir_faire dans professionnels
BEGIN
    EXECUTE IMMEDIATE 'ALTER TABLE professionnels ADD (
        code_savoir_faire VARCHAR2(10),
        libelle_savoir_faire VARCHAR2(200)
    )';
    DBMS_OUTPUT.PUT_LINE('✓ code_savoir_faire ajouté');
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE = -1430 THEN
            DBMS_OUTPUT.PUT_LINE('- code_savoir_faire existe déjà');
        ELSE
            RAISE;
        END IF;
END;
/

-- 3. mode_exercice_principal dans professionnels
BEGIN
    EXECUTE IMMEDIATE 'ALTER TABLE professionnels ADD (
        mode_exercice_principal VARCHAR2(20)
    )';
    DBMS_OUTPUT.PUT_LINE('✓ mode_exercice_principal ajouté');
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE = -1430 THEN
            DBMS_OUTPUT.PUT_LINE('- mode_exercice_principal existe déjà');
        ELSE
            RAISE;
        END IF;
END;
/

-- 4. code_savoir_faire et libelle_savoir_faire dans activites
BEGIN
    EXECUTE IMMEDIATE 'ALTER TABLE activites ADD (
        code_savoir_faire VARCHAR2(10),
        libelle_savoir_faire VARCHAR2(200)
    )';
    DBMS_OUTPUT.PUT_LINE('✓ Colonnes savoir-faire ajoutées dans activites');
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE = -1430 THEN
            DBMS_OUTPUT.PUT_LINE('- Colonnes savoir-faire existent déjà');
        ELSE
            RAISE;
        END IF;
END;
/

COMMIT;

SELECT 'Colonnes ajoutées avec succès !' as status FROM DUAL;
