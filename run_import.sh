#!/bin/bash
# Script de lancement de l'import RPPS v3

echo "=========================================="
echo "IMPORT RPPS v3 - MERGE OPTIMISÉ"
echo "=========================================="
echo ""

# Vérifier que venv est activé
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Activation de l'environnement virtuel..."
    source venv/bin/activate
fi

echo "🔍 Vérification de la table professionnels..."
python3 -c "
import oracledb
import os
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
cursor.execute('SELECT COUNT(*) FROM professionnels')
count = cursor.fetchone()[0]
print(f'📊 Professionnels actuellement en base : {count:,}')

if count > 0:
    print('⚠️  La table n\'est pas vide !')
    print('🧹 Nettoyage de la table...')
    cursor.execute('DELETE FROM contacts')
    cursor.execute('DELETE FROM adresses')
    cursor.execute('DELETE FROM activites')
    cursor.execute('DELETE FROM structures')
    cursor.execute('DELETE FROM professionnels')
    conn.commit()
    print('✅ Tables vidées')
else:
    print('✅ Table vide, prêt pour l\'import')

conn.close()
"

echo ""
echo "🚀 Lancement de l'import v3..."
python3 import_rpps_v3_fixed.py

echo ""
echo "=========================================="
echo "FIN DU SCRIPT"
echo "=========================================="
