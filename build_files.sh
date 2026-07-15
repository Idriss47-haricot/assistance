#!/bin/bash
set -e

echo "📦 Installation des dépendances..."
python3 -m pip install -r requirements.txt --break-system-packages

echo "📁 Collecte des fichiers statiques..."
python3 manage.py collectstatic --noinput

echo "✅ Build terminé avec succès !"
