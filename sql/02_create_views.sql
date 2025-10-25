-- =============================================
-- VUES MÉTIER ESSENTIELLES
-- =============================================

-- Vue 1 : Contacts Qualifiés (pour export campagnes)
CREATE OR REPLACE VIEW v_contacts_qualifies AS
SELECT 
    p.id_professionnel,
    p.nom,
    p.prenom,
    p.libelle_profession,
    p.categorie_profession,
    p.statut_enregistrement,
    a.mode_exercice,
    a.statut_activite,
    ad.code_postal,
    ad.commune,
    ad.departement,
    ad.region,
    -- Agrégation téléphones
    LISTAGG(DISTINCT CASE WHEN c.type_contact = 'TELEPHONE' 
        THEN c.valeur END, '; ') 
        WITHIN GROUP (ORDER BY c.priorite DESC) AS telephones,
    -- Agrégation emails
    LISTAGG(DISTINCT CASE WHEN c.type_contact = 'EMAIL' 
        THEN c.valeur END, '; ') 
        WITHIN GROUP (ORDER BY c.priorite DESC) AS emails,
    -- Score de qualification (0-100)
    (CASE WHEN EXISTS(SELECT 1 FROM contacts WHERE id_professionnel = p.id_professionnel 
        AND type_contact = 'TELEPHONE') THEN 50 ELSE 0 END +
    CASE WHEN EXISTS(SELECT 1 FROM contacts WHERE id_professionnel = p.id_professionnel 
        AND type_contact = 'EMAIL') THEN 30 ELSE 0 END +
    CASE WHEN p.date_premiere_apparition >= ADD_MONTHS(SYSDATE, -12) 
        THEN 20 ELSE 0 END) AS score_qualification
FROM professionnels p
LEFT JOIN activites a ON p.id_professionnel = a.id_professionnel 
    AND a.statut_activite = 'Actif'
LEFT JOIN adresses ad ON p.id_professionnel = ad.id_professionnel
LEFT JOIN contacts c ON p.id_professionnel = c.id_professionnel
WHERE p.statut_enregistrement = 'Actif'
GROUP BY 
    p.id_professionnel, p.nom, p.prenom, p.libelle_profession, 
    p.categorie_profession, p.statut_enregistrement, a.mode_exercice,
    a.statut_activite, ad.code_postal, ad.commune, ad.departement, 
    ad.region, p.date_premiere_apparition;

COMMENT ON VIEW v_contacts_qualifies IS 'Vue agrégée des professionnels avec leurs contacts pour campagnes marketing';

-- Vue 2 : Nouveaux Entrants Mois en cours
CREATE OR REPLACE VIEW v_nouveaux_entrants_mois AS
SELECT 
    p.id_professionnel,
    p.nom,
    p.prenom,
    p.libelle_profession,
    p.code_profession,
    p.categorie_profession,
    p.date_premiere_apparition,
    a.mode_exercice,
    a.date_debut_activite,
    ad.code_postal,
    ad.commune,
    ad.departement,
    ad.region,
    -- Contacts
    (SELECT LISTAGG(valeur, '; ') WITHIN GROUP (ORDER BY priorite DESC)
     FROM contacts 
     WHERE id_professionnel = p.id_professionnel 
       AND type_contact = 'TELEPHONE') AS telephones,
    (SELECT LISTAGG(valeur, '; ') WITHIN GROUP (ORDER BY priorite DESC)
     FROM contacts 
     WHERE id_professionnel = p.id_professionnel 
       AND type_contact = 'EMAIL') AS emails
FROM professionnels p
LEFT JOIN activites a ON p.id_professionnel = a.id_professionnel
    AND a.statut_activite = 'Actif'
LEFT JOIN adresses ad ON p.id_professionnel = ad.id_professionnel
WHERE p.date_premiere_apparition >= TRUNC(SYSDATE, 'MM')
ORDER BY p.date_premiere_apparition DESC;

COMMENT ON VIEW v_nouveaux_entrants_mois IS 'Professionnels détectés pour la première fois ce mois-ci';

-- Vue 3 : Professionnels Libéraux avec Contacts
CREATE OR REPLACE VIEW v_liberaux_avec_contacts AS
SELECT 
    p.id_professionnel,
    p.nom,
    p.prenom,
    p.libelle_profession,
    a.mode_exercice,
    ad.numero_voie || ' ' || ad.type_voie || ' ' || ad.libelle_voie AS adresse_complete,
    ad.code_postal,
    ad.commune,
    ad.departement,
    c_tel.valeur AS telephone,
    c_email.valeur AS email,
    s.siret,
    s.raison_sociale
FROM professionnels p
JOIN activites a ON p.id_professionnel = a.id_professionnel
    AND a.statut_activite = 'Actif'
    AND a.mode_exercice LIKE '%Lib%'  -- Libéral
LEFT JOIN adresses ad ON p.id_professionnel = ad.id_professionnel
LEFT JOIN structures s ON a.id_structure = s.id_structure
LEFT JOIN (
    SELECT id_professionnel, valeur,
           ROW_NUMBER() OVER (PARTITION BY id_professionnel ORDER BY priorite DESC) AS rn
    FROM contacts WHERE type_contact = 'TELEPHONE'
) c_tel ON p.id_professionnel = c_tel.id_professionnel AND c_tel.rn = 1
LEFT JOIN (
    SELECT id_professionnel, valeur,
           ROW_NUMBER() OVER (PARTITION BY id_professionnel ORDER BY priorite DESC) AS rn
    FROM contacts WHERE type_contact = 'EMAIL'
) c_email ON p.id_professionnel = c_email.id_professionnel AND c_email.rn = 1
WHERE p.statut_enregistrement = 'Actif';

COMMENT ON VIEW v_liberaux_avec_contacts IS 'Professionnels en exercice libéral avec coordonnées';

-- Vue 4 : Statistiques par Profession
CREATE OR REPLACE VIEW v_stats_professions AS
SELECT 
    p.libelle_profession,
    p.code_profession,
    p.categorie_profession,
    COUNT(DISTINCT p.id_professionnel) AS nb_professionnels,
    COUNT(DISTINCT CASE WHEN p.statut_enregistrement = 'Actif' 
        THEN p.id_professionnel END) AS nb_actifs,
    COUNT(DISTINCT CASE WHEN c.type_contact = 'TELEPHONE' 
        THEN p.id_professionnel END) AS nb_avec_telephone,
    COUNT(DISTINCT CASE WHEN c.type_contact = 'EMAIL' 
        THEN p.id_professionnel END) AS nb_avec_email,
    COUNT(DISTINCT CASE WHEN p.date_premiere_apparition >= ADD_MONTHS(SYSDATE, -12)
        THEN p.id_professionnel END) AS nb_nouveaux_12mois,
    ROUND(AVG(CASE WHEN c.type_contact IS NOT NULL THEN 1 ELSE 0 END) * 100, 2) AS taux_contact_pct
FROM professionnels p
LEFT JOIN contacts c ON p.id_professionnel = c.id_professionnel
GROUP BY p.libelle_profession, p.code_profession, p.categorie_profession
ORDER BY nb_professionnels DESC;

COMMENT ON VIEW v_stats_professions IS 'Statistiques agrégées par type de profession';

-- Vue 5 : Enrichissement en cours
CREATE OR REPLACE VIEW v_enrichissement_status AS
SELECT 
    p.id_professionnel,
    p.nom,
    p.prenom,
    p.libelle_profession,
    -- Contacts RPPS
    COUNT(DISTINCT CASE WHEN c.source_origine = 'RPPS' THEN c.id_contact END) AS nb_contacts_rpps,
    -- Enrichissement externe
    COUNT(DISTINCT ec.id_enrichissement) AS nb_enrichissements,
    COUNT(DISTINCT CASE WHEN ec.statut_verification = 'Verifie' 
        THEN ec.id_enrichissement END) AS nb_verifies,
    -- Sources multiples
    LISTAGG(DISTINCT ec.source_enrichissement, ', ') 
        WITHIN GROUP (ORDER BY ec.source_enrichissement) AS sources_externes,
    MAX(ec.date_collecte) AS derniere_collecte
FROM professionnels p
LEFT JOIN contacts c ON p.id_professionnel = c.id_professionnel
LEFT JOIN enrichissement_contacts ec ON p.id_professionnel = ec.id_professionnel
WHERE p.statut_enregistrement = 'Actif'
GROUP BY p.id_professionnel, p.nom, p.prenom, p.libelle_profession
HAVING COUNT(DISTINCT c.id_contact) > 0 OR COUNT(DISTINCT ec.id_enrichissement) > 0
ORDER BY nb_enrichissements DESC;

COMMENT ON VIEW v_enrichissement_status IS 'Statut d''avancement de l''enrichissement par professionnel';

-- =============================================
-- Compilation
-- =============================================
COMMIT;

PROMPT '============================================='
PROMPT '5 vues métier créées avec succès !'
PROMPT '============================================='
