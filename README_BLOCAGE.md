# 🆘 RÉSOLUTION DU BLOCAGE

## 🔍 PROBLÈME

Le script `import_rpps_v3_fixed.py` **bloque/freeze** après :
```
2025-10-26 00:36:07,783 - INFO - 🚀 Démarrage extraction...
2025-10-26 00:36:07,783 - INFO - 📖 Lecture fichier : PS_LibreAcces_Personne_activite_202509230829.txt
[FREEZE INFINI - PAS DE PROGRESSION]
```

## 🎯 CAUSE PROBABLE

Le **MERGE avec executemany** sur 10,000 lignes est TRÈS lent sur Oracle, surtout si :
- ❌ Pas d'index sur `id_professionnel`
- ❌ Statistiques de table jamais calculées
- ❌ MERGE parse et exécute 10,000 requêtes SQL distinctes

### **Pourquoi MERGE est lent :**
```sql
-- Oracle doit analyser CETTE requête 10,000 fois :
MERGE INTO professionnels tgt
USING (SELECT :1 AS id_prof, ... FROM DUAL) src
ON (tgt.id_professionnel = src.id_prof)
WHEN MATCHED THEN UPDATE ...
WHEN NOT MATCHED THEN INSERT ...
```

Chaque MERGE :
1. Parse SQL
2. Recherche dans la table (FULL TABLE SCAN si pas d'index)
3. Décide UPDATE ou INSERT
4. Exécute

**Résultat :** Avec 10,000 lignes, ça peut prendre **plusieurs minutes** ou **bloquer complètement**.

---

## ✅ SOLUTION EN 2 ÉTAPES

### **ÉTAPE 1 : DIAGNOSTIC**

Lancez le script de diagnostic pour identifier le problème exact :

```bash
cd ~/Dev/Projet_sante_v2
source venv/bin/activate
python diagnostic_blocage.py
```

**Résultats attendus :**

#### **Si vous voyez :**
```
1️⃣  VÉRIFICATION DES INDEX sur professionnels...
   ❌ AUCUN INDEX TROUVÉ ! C'est probablement ça le problème !

2️⃣  TEST MERGE avec 1 ligne...
   ⚠️  WARNING : Très lent ! (>1000ms pour 1 ligne)
```

**→ Problème = MANQUE D'INDEX**

**Solution immédiate :**
```sql
-- Se connecter à Oracle et exécuter :
CREATE INDEX idx_pros_id ON professionnels(id_professionnel);
EXEC DBMS_STATS.GATHER_TABLE_STATS(USER, 'PROFESSIONNELS');
```

Ensuite, relancez `import_rpps_v3_fixed.py`.

---

#### **Si vous voyez :**
```
2️⃣  TEST MERGE avec 1 ligne...
   ✅ MERGE 1 ligne : 50ms

3️⃣  TEST MERGE avec 10 lignes...
   ⚠️  WARNING : Très lent ! (>2000ms pour 10 lignes)
```

**→ Problème = MERGE executemany est intrinsèquement lent**

**Solution :** Utilisez la **v4 avec INSERT pur** (voir étape 2 ci-dessous)

---

### **ÉTAPE 2 : UTILISER v4 INSERT-ONLY (SOLUTION RAPIDE)**

Pour le **premier import** (tables vides après TRUNCATE), utilisez la v4 qui fait **INSERT simple** au lieu de MERGE :

```bash
cd ~/Dev/Projet_sante_v2
source venv/bin/activate
python import_rpps_v4_insert_only.py
```

**Avantages v4 :**
- ✅ **10-20x plus rapide** que MERGE pour premier import
- ✅ **Pas de blocage** : INSERT simple
- ✅ **Batch optimisé** : 5000 lignes (vs 10,000)
- ✅ **Performance attendue** : 2000-3000 lignes/seconde

**Important :**
- ⚠️ Utilisez v4 SEULEMENT pour le **premier import** (tables vides)
- ⚠️ Pour les imports suivants (mise à jour), utilisez v3 avec MERGE

---

## 📊 COMPARAISON DES VERSIONS

| Version | Méthode | Performance | Usage | Freeze ? |
|---------|---------|-------------|-------|----------|
| **v2** | UPDATE+INSERT | 1200 l/s | ❌ Bug écrasement | Oui |
| **v3** | MERGE | FREEZE | ❌ Blocage MERGE | Oui |
| **v4** | INSERT pur | **2000-3000 l/s** | ✅ Premier import | Non ✅ |

---

## 🚀 COMMANDES RECOMMANDÉES

### **Option A : Diagnostic d'abord (recommandé)**

```bash
# 1. Diagnostic
python diagnostic_blocage.py

# 2. Si index manquant, créez-le via SQL*Plus ou autre client
# CREATE INDEX idx_pros_id ON professionnels(id_professionnel);

# 3. Relancer v3 ou utiliser v4
python import_rpps_v4_insert_only.py
```

---

### **Option B : Directement v4 (plus rapide)**

```bash
# Si vous êtes pressé, utilisez directement v4
python import_rpps_v4_insert_only.py
```

**Temps estimé :**
- v4 : **10-15 minutes** pour 2.2M lignes
- v3 avec index : **15-20 minutes**
- v3 sans index : **INFINI (freeze)** ❌

---

## 🔧 APRÈS L'IMPORT

### **Vérification :**

```sql
-- Vérifier le nombre de professionnels
SELECT COUNT(*) FROM professionnels;
-- Devrait retourner ~1,800,000

-- Vérifier qu'aucun professionnel n'a toutes les activités
SELECT p.nom, p.prenom, COUNT(a.id_activite) AS nb_activites
FROM professionnels p
LEFT JOIN activites a ON p.id_professionnel = a.id_professionnel
GROUP BY p.id_professionnel, p.nom, p.prenom
ORDER BY nb_activites DESC
FETCH FIRST 10 ROWS ONLY;
-- Le max devrait être ~10-20 activités (pas 1,630,654 !)
```

### **Créer les index (si pas déjà fait) :**

```sql
-- Index essentiels
CREATE INDEX idx_pros_id ON professionnels(id_professionnel);
CREATE INDEX idx_struct_siret ON structures(siret);
CREATE INDEX idx_struct_finess ON structures(finess);
CREATE INDEX idx_struct_id_tech ON structures(identifiant_technique);
CREATE INDEX idx_act_id_prof ON activites(id_professionnel);
CREATE INDEX idx_act_id_struct ON activites(id_structure);

-- Calculer statistiques
EXEC DBMS_STATS.GATHER_TABLE_STATS(USER, 'PROFESSIONNELS');
EXEC DBMS_STATS.GATHER_TABLE_STATS(USER, 'STRUCTURES');
EXEC DBMS_STATS.GATHER_TABLE_STATS(USER, 'ACTIVITES');
```

---

## 📚 EXPLICATION TECHNIQUE

### **Pourquoi INSERT est plus rapide que MERGE ?**

**MERGE (v3) :**
```
Pour chaque ligne (×10,000):
  1. Parse SQL
  2. Recherche dans table (FULL SCAN si pas d'index)
  3. Décide UPDATE ou INSERT
  4. Exécute
  → 10,000 × (parse + scan + décision + exec) = TRÈS LENT
```

**INSERT (v4) :**
```
Pour chaque ligne (×10,000):
  1. Parse SQL UNE FOIS
  2. Prépare batch
  3. INSERT en masse
  → 1 × parse + 1 × exec = RAPIDE ✅
```

### **Quand utiliser quoi ?**

| Situation | Version à utiliser | Raison |
|-----------|-------------------|--------|
| **Premier import** (tables vides) | v4 INSERT | 10-20x plus rapide |
| **Mise à jour** (tables pleines) | v3 MERGE | Évite doublons, UPDATE intelligent |
| **Import incrémental** | v3 MERGE | Gère UPDATE + INSERT automatiquement |

---

## 🆘 SI ÇA BLOQUE ENCORE

Si même v4 bloque (peu probable), vérifiez :

1. **Espace disque disponible :**
   ```bash
   df -h
   ```

2. **Verrous Oracle actifs :**
   ```sql
   SELECT * FROM v$lock WHERE type = 'TM';
   ```

3. **Sessions bloquées :**
   ```sql
   SELECT s.sid, s.serial#, s.username, s.program, s.status
   FROM v$session s
   WHERE s.username = 'VOTRE_USER';
   ```

4. **Tablespace UNDO saturé :**
   ```sql
   SELECT tablespace_name, used_percent
   FROM dba_tablespace_usage_metrics
   WHERE tablespace_name LIKE '%UNDO%';
   ```

---

**Date :** 2025-10-26
**Auteur :** Claude (Anthropic)
**Support :** Si problème persiste, partagez les résultats de `diagnostic_blocage.py`
