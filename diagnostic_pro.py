import oracledb, os
from dotenv import load_dotenv
load_dotenv()
oracle_home = os.getenv("ORACLE_HOME")
if oracle_home:
    try: oracledb.init_oracle_client(lib_dir=oracle_home)
    except: pass
conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)
cursor = conn.cursor()

print("="*70)
print("DIAGNOSTIC PROFESSIONNELS")
print("="*70)

print("\n1. TOTAL PROFESSIONNELS :")
cursor.execute("SELECT COUNT(*), COUNT(CASE WHEN statut_enregistrement='Actif' THEN 1 END), COUNT(CASE WHEN statut_enregistrement='Inactif' THEN 1 END) FROM professionnels")
total, actifs, inactifs = cursor.fetchone()
print(f"   Total   : {total:,}")
print(f"   Actifs  : {actifs:,}")
print(f"   Inactifs: {inactifs:,}")

print("\n2. PROS AVEC ACTIVITÉS :")
cursor.execute("SELECT COUNT(DISTINCT id_professionnel) FROM activites")
print(f"   {cursor.fetchone()[0]:,}")

print("\n3. TOP 10 PROFESSIONS :")
cursor.execute("SELECT libelle_profession, COUNT(*) FROM professionnels GROUP BY libelle_profession ORDER BY COUNT(*) DESC FETCH FIRST 10 ROWS ONLY")
for prof, nb in cursor.fetchall():
    print(f"   {prof:40s} : {nb:>8,}")

conn.close()
