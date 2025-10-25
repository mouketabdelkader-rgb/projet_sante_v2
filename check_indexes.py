import oracledb, os
from dotenv import load_dotenv
load_dotenv()

conn = oracledb.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dsn=os.getenv('DB_DSN'),
    config_dir=os.getenv('WALLET_PATH'),
    wallet_location=os.getenv('WALLET_PATH')
)
cursor = conn.cursor()

cursor.execute("""
    SELECT index_name, table_name, uniqueness 
    FROM user_indexes 
    ORDER BY table_name, index_name
""")
print("Index actuels :")
for idx, tbl, uniq in cursor.fetchall():
    print(f"  {idx} sur {tbl} ({uniq})")

conn.close()
