#!/bin/bash

echo "📦 Installation des dépendances..."
pip install -r requirements.txt

echo "📁 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "✅ Build terminé avec succès !"