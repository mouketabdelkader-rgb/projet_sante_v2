#!/usr/bin/env python3
"""
Import CONTACTS - Version ULTRA-RAPIDE
Sans vérification NOT EXISTS (on gère les doublons après)
"""
import oracledb
import os
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 50000  # Gros batch pour vitesse
FICHIER_RPPS = "PS_LibreAcces_Personne_activite_202509230829.txt"

# Initialiser le client Oracle
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try:
        oracledb.init_oracle_client(lib_dir=oracle_home)
    except: pass

# Connexion
conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)

cursor = conn.cursor()

print("="*60)
print("IMPORT CONTACTS - VERSION RAPIDE")
print("="*60)

# Nettoyage
print("\n[1/3] Nettoyage table contacts...")
cursor.execute("DELETE FROM contacts WHERE source_origine = 'RPPS'")
nb_deleted = cursor.rowcount
conn.commit()
print(f"  ✓ {nb_deleted:,} anciens contacts supprimés")

# Fonction de nettoyage téléphone
def clean_phone(phone):
    if not phone:
        return None
    phone = re.sub(r'[^\d+]', '', phone)
    return phone if phone and len(phone) >= 10 else None

# Fonction de validation email
def is_valid_email(email):
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

stats = {
    'lignes': 0,
    'tels': 0,
    'emails': 0
}

buffer = []

def flush():
    global buffer
    if buffer:
        # INSERT DIRECT sans vérification
        cursor.executemany("""
            INSERT INTO contacts (
                id_professionnel, type_contact, valeur, 
                source_origine, priorite
            ) VALUES (:1, :2, :3, 'RPPS', :4)
        """, buffer)
        buffer = []
        conn.commit()

print("\n[2/3] Lecture et import...")
start = datetime.now()

with open(FICHIER_RPPS, 'r', encoding='utf-8') as f:
    header = f.readline().strip().split('|')
    
    COL_ID = header.index('Identifiant PP')
    COL_TEL1 = header.index('Téléphone (coord. structure)')
    COL_TEL2 = header.index('Téléphone 2 (coord. structure)')
    COL_EMAIL = header.index('Adresse e-mail (coord. structure)')
    
    for line in f:
        stats['lignes'] += 1
        
        try:
            fields = line.strip().split('|')
            id_prof = fields[COL_ID].strip()
            
            if not id_prof:
                continue
            
            # Téléphone 1
            tel1 = clean_phone(fields[COL_TEL1]) if COL_TEL1 < len(fields) else None
            if tel1:
                buffer.append([id_prof, 'TELEPHONE', tel1, 1])
                stats['tels'] += 1
            
            # Téléphone 2
            tel2 = clean_phone(fields[COL_TEL2]) if COL_TEL2 < len(fields) else None
            if tel2 and tel2 != tel1:
                buffer.append([id_prof, 'TELEPHONE', tel2, 2])
                stats['tels'] += 1
            
            # Email
            email = fields[COL_EMAIL].strip().lower() if COL_EMAIL < len(fields) else None
            if email and is_valid_email(email):
                buffer.append([id_prof, 'EMAIL', email, 1])
                stats['emails'] += 1
        
        except:
            pass
        
        # Flush périodique
        if len(buffer) >= BATCH_SIZE:
            flush()
            elapsed = (datetime.now() - start).total_seconds()
            vitesse = stats['lignes'] / elapsed
            print(f"  {stats['lignes']:,} lignes | {stats['tels']:,} tels | "
                  f"{stats['emails']:,} emails | {vitesse:,.0f} l/s")

flush()  # Final

duration = (datetime.now() - start).total_seconds()

print("\n[3/3] Suppression des doublons...")
cursor.execute("""
    DELETE FROM contacts c1
    WHERE c1.rowid > (
        SELECT MIN(c2.rowid) 
        FROM contacts c2 
        WHERE c1.id_professionnel = c2.id_professionnel 
        AND c1.type_contact = c2.type_contact 
        AND c1.valeur = c2.valeur
    )
""")
nb_doublons = cursor.rowcount
conn.commit()
print(f"  ✓ {nb_doublons:,} doublons supprimés")

print("\n" + "="*60)
print("✅ IMPORT TERMINÉ")
print("="*60)
print(f"⏱  Durée    : {duration/60:.1f} min")
print(f"📊 Lignes   : {stats['lignes']:,}")
print(f"📞 Tels     : {stats['tels']:,}")
print(f"📧 Emails   : {stats['emails']:,}")
print(f"🚀 Vitesse  : {stats['lignes']/duration:,.0f} l/s")

# Stats finales
cursor.execute("SELECT COUNT(*) FROM contacts WHERE type_contact = 'TELEPHONE'")
print(f"\n✓ Téléphones en base : {cursor.fetchone()[0]:,}")

cursor.execute("SELECT COUNT(*) FROM contacts WHERE type_contact = 'EMAIL'")
print(f"✓ Emails en base     : {cursor.fetchone()[0]:,}")

cursor.execute("SELECT COUNT(DISTINCT id_professionnel) FROM contacts")
nb_pros_contact = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM professionnels")
nb_pros_total = cursor.fetchone()[0]

pct = (nb_pros_contact / nb_pros_total * 100)
print(f"✓ Pros avec contact  : {nb_pros_contact:,} / {nb_pros_total:,} ({pct:.1f}%)")

print("\n🎯 Lance: python explorer_donnees.py")

conn.close()
