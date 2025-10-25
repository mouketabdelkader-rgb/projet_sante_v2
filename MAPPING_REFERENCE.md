# 📋 RÉFÉRENCE MAPPING RPPS

## Vue d'ensemble

Le fichier RPPS contient **57 colonnes** séparées par le caractère `|`.  
Ce document liste toutes les colonnes et leur utilisation dans le projet.

---

## 🔢 Index des Colonnes (0-56)

### 🆔 IDENTITÉ (Colonnes 0-8)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 0 | Identifiant PP | PROFESSIONNELS | id_professionnel | ✅ |
| 1 | Code civilité | ❌ Non utilisé | - | - |
| 2 | Libellé civilité | ❌ Non utilisé | - | - |
| 3 | Code civilité d'exercice | PROFESSIONNELS | civilite | ⚪ |
| 4 | Libellé civilité d'exercice | ❌ Non utilisé | - | - |
| 5 | Nom de famille | ❌ Non utilisé | - | - |
| 6 | Prénom | ❌ Non utilisé | - | - |
| 7 | **Nom d'exercice** | PROFESSIONNELS | nom | ✅ |
| 8 | **Prénom d'exercice** | PROFESSIONNELS | prenom | ✅ |

**⚠️ ATTENTION :** Utiliser colonnes 7 et 8 (nom/prénom d'exercice), PAS 5 et 6 !

---

### 💼 PROFESSION (Colonnes 9-16)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 9 | **Code profession** | PROFESSIONNELS | code_profession | ✅ |
| 10 | Libellé profession | PROFESSIONNELS | libelle_profession | ✅ |
| 11 | Code catégorie professionnelle | ❌ Non utilisé | - | - |
| 12 | Libellé catégorie professionnelle | PROFESSIONNELS | categorie_profession | ⚪ |
| 13 | Code type savoir-faire | ❌ Non utilisé | - | - |
| 14 | Libellé type savoir-faire | ❌ Non utilisé | - | - |
| 15 | Code savoir-faire | ACTIVITES | code_savoir_faire | ⚪ |
| 16 | **Libellé savoir-faire** | ACTIVITES | libelle_savoir_faire | ⚪ |

**Codes profession cibles :**
- 10 : Médecin
- 21 : Pharmacien
- 50 : Sage-Femme
- 60 : Infirmier
- 70 : Masseur-Kinésithérapeute
- 80 : Pédicure-Podologue
- 91 : Ergothérapeute
- 94 : Orthophoniste

---

### 🏢 ACTIVITÉ (Colonnes 17-18)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 17 | Code mode exercice | ❌ Non utilisé directement | - | - |
| 18 | **Libellé mode exercice** | ACTIVITES | mode_exercice | ✅ |

**Valeurs fréquentes :**
- `Lib,indép,artis,com` : Libéral (⭐ Prioritaire)
- `Salarié`
- `Bénévole`

---

### 🏥 STRUCTURE (Colonnes 19-27)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 19 | **Numéro SIRET site** | STRUCTURES | siret | ⚪ |
| 20 | Numéro SIREN site | STRUCTURES | (calculé) | ⚪ |
| 21 | **Numéro FINESS site** | STRUCTURES | finess | ⚪ |
| 22 | Numéro FINESS établissement juridique | ❌ Non utilisé | - | - |
| 23 | Identifiant technique structure | ❌ Non utilisé | - | - |
| 24 | Raison sociale site | STRUCTURES | raison_sociale | ⚪ |
| 25 | Enseigne commerciale site | STRUCTURES | enseigne_commerciale | ⚪ |
| 26 | Complément destinataire | ADRESSES | complement_adresse | ⚪ |
| 27 | Complément point géographique | ❌ Non utilisé | - | - |

---

### 📍 ADRESSE (Colonnes 28-39)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 28 | **Numéro Voie** | ADRESSES | numero_voie | ⚪ |
| 29 | Indice répétition voie | ❌ Non utilisé | - | - |
| 30 | Code type de voie | ❌ Non utilisé | - | - |
| 31 | **Libellé type de voie** | ADRESSES | type_voie | ⚪ |
| 32 | **Libellé Voie** | ADRESSES | libelle_voie | ✅ |
| 33 | Mention distribution | ❌ Non utilisé | - | - |
| 34 | Bureau cedex | ❌ Non utilisé | - | - |
| 35 | **Code postal** | ADRESSES | code_postal | ✅ |
| 36 | Code commune | ADRESSES | code_commune_insee | ⚪ |
| 37 | **Libellé commune** | ADRESSES | commune | ✅ |
| 38 | Code pays | ❌ Non utilisé | - | - |
| 39 | Libellé pays | ADRESSES | pays | ⚪ |

**Validation code postal :**
- Format : 5 chiffres
- **Exclus :** 97xxx, 98xxx (DOM-TOM)

---

### 📞 CONTACTS (Colonnes 40-43)

| Index | Nom Colonne | Table Destination | Champ | Priorité |
|-------|-------------|-------------------|-------|----------|
| 40 | **Téléphone (coord. structure)** | CONTACTS | valeur | 80 ⭐ |
| 41 | Téléphone 2 (coord. structure) | CONTACTS | valeur | 70 |
| 42 | Télécopie (coord. structure) | CONTACTS | valeur | 50 |
| 43 | **Adresse e-mail (coord. structure)** | CONTACTS | valeur | 90 ⭐⭐ |

**Format téléphone :**
- Nettoyé automatiquement : `06 12 34 56 78` → `0612345678`
- Validation : `^(0|\+33)\d{9}$`

**Format email :**
- Validation : RFC 5322 basique
- Conversion : minuscules

---

### 🗺️ LOCALISATION (Colonnes 44-47)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 44 | **Code Département** | ADRESSES | departement | ✅ |
| 45 | Libellé Département | ❌ Non utilisé | - | - |
| 46 | Ancien identifiant structure | ❌ Non utilisé | - | - |
| 47 | Autorité d'enregistrement | ❌ Non utilisé | - | - |

**Régions calculées :**
Le champ `region` est calculé automatiquement à partir du département.

Exemples :
- 75, 77, 78, 91-95 → Île-de-France
- 13, 06, 83, 84 → Provence-Alpes-Côte d'Azur
- etc.

---

### 📅 DATES (Colonnes 48-51)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 48 | Date d'autorisation | ❌ Non utilisé | - | - |
| 49 | **Date de début d'activité** | ACTIVITES | date_debut_activite | ⚪ |
| 50 | Date de fin d'activité | ACTIVITES | date_fin_activite | ⚪ |
| 51 | Date de première autorisation | ❌ Non utilisé | - | - |

**Format dates :**
- Format source : `YYYYMMDD` (ex: 20200115)
- Conversion : `YYYY-MM-DD` (ex: 2020-01-15)

**Statut activité :**
- Si `date_fin_activite` est NULL ou future → `Actif`
- Si `date_fin_activite` <= aujourd'hui → `Cessé`

---

### 📊 MÉTADONNÉES (Colonnes 52-56)

| Index | Nom Colonne | Table Destination | Champ | Obligatoire |
|-------|-------------|-------------------|-------|-------------|
| 52 | Code secteur d'activité | ❌ Non utilisé | - | - |
| 53 | Libellé secteur d'activité | ACTIVITES | secteur_activite | ⚪ |
| 54 | Code section tableau pharmaciens | ❌ Non utilisé | - | - |
| 55 | Libellé section tableau pharmaciens | ❌ Non utilisé | - | - |
| 56 | Type d'identifiant PP | ❌ Non utilisé | - | - |

---

## 🎯 Colonnes Critiques (à vérifier en priorité)

### Obligatoires pour insertion
1. **Col 0** : Identifiant PP (RPPS) → 11 chiffres
2. **Col 7** : Nom d'exercice → Non vide
3. **Col 9** : Code profession → Dans liste cibles

### Très importantes pour qualité
4. **Col 8** : Prénom d'exercice
5. **Col 18** : Mode exercice (Libéral prioritaire)
6. **Col 35** : Code postal (France métropolitaine)
7. **Col 37** : Commune
8. **Col 40** : Téléphone 1
9. **Col 43** : Email

---

## ⚠️ Pièges à Éviter

### 1. Confusion Nom/Prénom
```
❌ FAUX : Col 5 (Nom de famille), Col 6 (Prénom)
✅ CORRECT : Col 7 (Nom d'exercice), Col 8 (Prénom d'exercice)
```

### 2. Mode exercice exact
```
✅ Valeur exacte : "Lib,indép,artis,com"
❌ Ne pas chercher juste "Lib" ou "Liberal"
```

### 3. Code postal DOM-TOM
```
❌ Exclure : 97xxx, 98xxx
✅ Garder : 01xxx - 96xxx (hors Corse si souhaité)
```

### 4. Téléphone format
```
Source : "01 23 45 67 89" ou "01.23.45.67.89"
✅ Nettoyé : "0123456789"
```

---

## 📚 Exemples de Lignes RPPS

### Exemple 1 : Médecin Libéral avec contacts
```
10001234567|M|Monsieur|M|Monsieur|MARTIN|Jean|MARTIN|Jean|10|Médecin|1|
Médecin|1|Activité clinique ou thérapeutique|SM26|Médecine Générale|L|
Lib,indép,artis,com|12345678901234||123456789||Cabinet Dr Martin|
Cabinet MARTIN|||15||RUE|DE LA PAIX||||75001|75056|PARIS|FR|France|
0123456789||0987654321|dr.martin@example.com|75|Paris||||
20100115||||Privé|||
```

**Extraction :**
- RPPS : 10001234567
- Nom : MARTIN
- Prénom : Jean
- Profession : Médecin (10)
- Mode : Libéral
- Adresse : 15 RUE DE LA PAIX, 75001 PARIS
- Tél : 0123456789
- Email : dr.martin@example.com

---

## 🔧 Configuration dans le Projet

Le mapping complet est défini dans :
```
config/mapping_rpps.yaml
```

Vous pouvez l'ajuster selon vos besoins spécifiques.

---

## 📞 Support

**En cas de doute sur un mapping :**
1. Consulter ce document
2. Vérifier `config/mapping_rpps.yaml`
3. Activer `--log-level DEBUG` lors de l'import
4. Consulter les logs détaillés

---

**Version :** 2.0  
**Dernière mise à jour :** 23 Octobre 2025  
**Source officielle :** [Annuaire Santé](https://annuaire.sante.fr/web/site-pro/extractions-publiques)
