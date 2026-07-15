# 🎫 Helpdesk - Application de Gestion de Tickets d'Incidents

[![Django](https://img.shields.io/badge/Django-6.0.6-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.0-purple.svg)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Une application web complète de gestion de tickets d'incidents (Helpdesk) développée avec Django, permettant aux employés de signaler des problèmes informatiques et à l'équipe support de les traiter efficacement.

---

## 📋 Table des matières

- [Aperçu](#aperçu)
- [Fonctionnalités](#fonctionnalités)
- [Stack Technique](#stack-technique)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Rôles et Permissions](#rôles-et-permissions)
- [Structure du Projet](#structure-du-projet)
- [API REST](#api-rest)
- [Déploiement](#déploiement)
- [Captures d'écran](#captures-décran)
- [Contribution](#contribution)
- [Licence](#licence)

---

## 🎯 Aperçu

Helpdesk est une solution interne de gestion des demandes d'assistance informatique pour les PME. Elle permet de :

- 📝 **Centraliser** toutes les demandes d'assistance
- 🎯 **Prioriser** les problèmes critiques
- 👥 **Assigner** les tickets aux bons techniciens
- 📊 **Analyser** la performance du support
- 🔗 **Intégrer** avec d'autres outils (chatbot, API)

---

## ✨ Fonctionnalités

### 🔐 Authentification
- ✅ Sélection du rôle avant la connexion (Admin, Manager, Technicien, Employé)
- ✅ Connexion sécurisée avec session persistante
- ✅ Réinitialisation du mot de passe par email
- ✅ Profil utilisateur personnalisé

### 👤 Employé
- ✅ Créer des tickets (ses propres problèmes)
- ✅ Voir ses tickets
- ✅ Commenter ses tickets
- ✅ Voir le statut de ses tickets

### 👨‍🔧 Technicien
- ✅ Voir TOUS les tickets
- ✅ Prendre un ticket (s'assigner)
- ✅ Changer le statut des tickets
- ✅ Résoudre des tickets
- ✅ Commenter sur tous les tickets
- ✅ Voir les commentaires internes
- ✅ Dashboard avec tickets disponibles
- ✅ Exporter un ticket en PDF

### 👔 Manager
- ✅ Tout ce que fait un technicien
- ✅ Assigner des tickets à d'autres techniciens
- ✅ Voir les statistiques complètes
- ✅ Voir la performance des techniciens
- ✅ Générer des rapports (PDF, CSV, HTML)
- ✅ Dashboard complet avec KPIs
- ✅ Assignation en masse de tickets
- ✅ Exporter un ticket ou tous les tickets en PDF

### 🛡️ Admin
- ✅ TOUT faire
- ✅ Créer/modifier/supprimer des utilisateurs
- ✅ Modifier les rôles
- ✅ Supprimer des tickets
- ✅ Accéder à l'admin Django
- ✅ Archiver des tickets
- ✅ Gérer les permissions

### 📧 Notifications
- ✅ Notification à la création d'un ticket
- ✅ Notification au changement de statut
- ✅ Notification à l'assignation
- ✅ Interface de notifications en temps réel
- ✅ **Notifications sonores** avec sons personnalisés (1.wav, 2.wav, 3.wav)
- ✅ Polling des notifications toutes les 10 secondes

### 📊 Dashboard
- ✅ Statistiques en temps réel
- ✅ Graphiques d'évolution
- ✅ Performance des techniciens
- ✅ Conformité SLA
- ✅ Tickets urgents et récents
- ✅ Dashboard personnalisé selon le rôle

### 📄 Export PDF
- ✅ Exporter un ticket individuel en PDF
- ✅ Exporter tous les tickets en PDF
- ✅ Impression via navigateur avec sauvegarde PDF
- ✅ Design professionnel et responsive

### 📎 Pièces jointes
- ✅ Upload multiple de fichiers
- ✅ Support des images, PDF, documents
- ✅ Validation des types et tailles (max 5Mo)

### 📊 Rapports (Manager/Admin)
- ✅ Rapport de performance des techniciens
- ✅ Rapport d'activité
- ✅ Export en HTML, PDF, CSV
- ✅ Graphiques et statistiques avancées
- ✅ Filtrage par période et technicien

### 🎯 Assignation avancée
- ✅ Assignation individuelle par Manager/Admin
- ✅ Assignation en masse de plusieurs tickets
- ✅ Auto-assignation par les techniciens
- ✅ Désassignation des tickets

---

## 🛠️ Stack Technique

### Backend
- **Framework** : Django 6.0.6
- **Langage** : Python 3.12+
- **Base de données** : SQLite (dev) / PostgreSQL (prod)
- **ORM** : Django ORM
- **API** : Django REST Framework

### Frontend
- **Framework** : Bootstrap 5.3.0
- **JavaScript** : Alpine.js 3.13.0
- **CSS** : Custom CSS + Bootstrap
- **Icônes** : Font Awesome 6.4.0
- **Graphiques** : Chart.js

### Outils
- **Email** : Django Email Backend
- **Déploiement** : Vercel / Docker
- **Notifications sonores** : Web Audio API + fichiers WAV

---

## 📦 Installation

### Prérequis

- Python 3.12+
- pip
- Git (optionnel)

### Étapes d'installation

#### 1. Cloner le projet

```bash
git clone https://github.com/votre-compte/helpdesk.git
cd helpdesk