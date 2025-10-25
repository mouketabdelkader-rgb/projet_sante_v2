-- =============================================
-- MIGRATION : Ajouter les codes standardisés
-- =============================================

-- Ajouter code_categorie_profession dans professionnels
ALTER TABLE professionnels ADD (
    code_categorie_profession VARCHAR2(2)
);

COMMENT ON COLUMN professionnels.code_categorie_profession IS 
    'Code catégorie : C=Médical, D=Pharma, S=Paramédical, M=Autre';

-- Ajouter code_mode_exercice dans activites
ALTER TABLE activites ADD (
    code_mode_exercice VARCHAR2(1)
);

COMMENT ON COLUMN activites.code_mode_exercice IS 
    'Code mode : L=Libéral, S=Salarié, B=Bénévole, M=Mixte';

COMMIT;

-- =============================================
-- TABLES DE RÉFÉRENCE (Lookup tables)
-- =============================================

-- Table de référence : PROFESSIONS
CREATE TABLE ref_professions (
    code_profession VARCHAR2(10) PRIMARY KEY,
    libelle_profession VARCHAR2(200) NOT NULL,
    code_categorie VARCHAR2(2) NOT NULL,
    ordre_affichage NUMBER,
    actif CHAR(1) DEFAULT 'O'
);

COMMENT ON TABLE ref_professions IS 'Référentiel officiel des professions de santé (RPPS)';

-- Insérer les professions principales
INSERT INTO ref_professions (code_profession, libelle_profession, code_categorie, ordre_affichage) VALUES
-- Médecins
('10', 'Médecin', 'C', 1),
('40', 'Chirurgien-Dentiste', 'C', 2),
('50', 'Sage-Femme', 'C', 3),
-- Pharmaciens
('21', 'Pharmacien', 'D', 10),
-- Paramédicaux
('60', 'Infirmier', 'S', 20),
('70', 'Masseur-Kinésithérapeute', 'S', 21),
('80', 'Pédicure-Podologue', 'S', 22),
('81', 'Ergothérapeute', 'S', 23),
('82', 'Psychomotricien', 'S', 24),
('83', 'Manipulateur ERM', 'S', 25),
('84', 'Technicien de Laboratoire Médical', 'S', 26),
('85', 'Audioprothésiste', 'S', 27),
('86', 'Opticien-Lunetier', 'S', 28),
('91', 'Orthophoniste', 'S', 29),
('92', 'Orthoptiste', 'S', 30),
('93', 'Diététicien', 'S', 31),
('94', 'Psychologue', 'S', 32),
('95', 'Ostéopathe', 'S', 33),
('96', 'Chiropracteur', 'S', 34);

-- Table de référence : CATÉGORIES
CREATE TABLE ref_categories (
    code_categorie VARCHAR2(2) PRIMARY KEY,
    libelle_categorie VARCHAR2(50) NOT NULL,
    description VARCHAR2(200)
);

INSERT INTO ref_categories VALUES
('C', 'Profession Médicale', 'Médecins, chirurgiens-dentistes, sages-femmes'),
('D', 'Profession Pharmaceutique', 'Pharmaciens'),
('S', 'Auxiliaire Médical', 'Paramédicaux : infirmiers, kinés, etc.'),
('M', 'Autres Professions de Santé', 'Techniciens, assistants sociaux, etc.');

-- Table de référence : MODES D'EXERCICE
CREATE TABLE ref_modes_exercice (
    code_mode VARCHAR2(1) PRIMARY KEY,
    libelle_mode VARCHAR2(50) NOT NULL,
    description VARCHAR2(200)
);

INSERT INTO ref_modes_exercice VALUES
('L', 'Libéral', 'Exercice en cabinet libéral, indépendant ou commercial'),
('S', 'Salarié', 'Exercice salarié en établissement de santé'),
('B', 'Bénévole', 'Exercice bénévole'),
('M', 'Mixte', 'Exercice mixte (libéral + salarié)');

COMMIT;

-- =============================================
-- MISE À JOUR DES CODES DEPUIS LES LIBELLÉS
-- =============================================

-- Mettre à jour code_categorie_profession
UPDATE professionnels p
SET code_categorie_profession = (
    SELECT code_categorie 
    FROM ref_professions r 
    WHERE r.code_profession = p.code_profession
)
WHERE EXISTS (
    SELECT 1 FROM ref_professions r 
    WHERE r.code_profession = p.code_profession
);

-- Mettre à jour code_mode_exercice
UPDATE activites
SET code_mode_exercice = CASE
    WHEN UPPER(mode_exercice) LIKE '%LIB%' 
      OR UPPER(mode_exercice) LIKE '%INDEP%' 
      OR UPPER(mode_exercice) LIKE '%ARTIS%'
      OR UPPER(mode_exercice) LIKE '%COM%' THEN 'L'
    WHEN UPPER(mode_exercice) LIKE '%SALAR%' THEN 'S'
    WHEN UPPER(mode_exercice) LIKE '%BENEV%' THEN 'B'
    WHEN UPPER(mode_exercice) LIKE '%MIXTE%' THEN 'M'
    ELSE NULL
END;

COMMIT;

-- =============================================
-- STATISTIQUES APRÈS MIGRATION
-- =============================================

PROMPT '========================================';
PROMPT 'STATISTIQUES APRÈS MIGRATION';
PROMPT '========================================';

-- Catégories avec les CODES
SELECT 
    c.libelle_categorie,
    COUNT(*) as nb,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM professionnels), 2) as pct
FROM professionnels p
JOIN ref_categories c ON p.code_categorie_profession = c.code_categorie
GROUP BY c.libelle_categorie
ORDER BY COUNT(*) DESC;

-- Top professions avec les CODES
SELECT 
    r.libelle_profession,
    COUNT(*) as nb,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM professionnels), 2) as pct
FROM professionnels p
JOIN ref_professions r ON p.code_profession = r.code_profession
GROUP BY r.libelle_profession
ORDER BY COUNT(*) DESC
FETCH FIRST 10 ROWS ONLY;

-- Modes d'exercice avec les CODES
SELECT 
    m.libelle_mode,
    COUNT(*) as nb,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM activites), 2) as pct
FROM activites a
JOIN ref_modes_exercice m ON a.code_mode_exercice = m.code_mode
GROUP BY m.libelle_mode
ORDER BY COUNT(*) DESC;

PROMPT '========================================';
PROMPT 'MIGRATION TERMINÉE';
PROMPT '========================================';
