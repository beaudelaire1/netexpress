# 📊 Clarification des Dashboards NetExpress

## Structure actuelle

### 🔧 `/gestion/` - Django Admin (Interface technique)
- **Usage** : Administration technique du système
- **Utilisateurs** : Développeurs, administrateurs système
- **Fonctions** : 
  - Gestion des modèles Django
  - Configuration système
  - Maintenance technique
  - Accès direct à la base de données

### 🏢 `/admin-dashboard/` - Admin Portal (Interface métier)
- **Usage** : Dashboard métier pour les administrateurs
- **Utilisateurs** : Administrateurs de Nettoyage Express
- **Fonctions** :
  - Vue d'ensemble des KPIs
  - Planning global des tâches
  - Validation des devis
  - Gestion des clients et ouvriers

### 👥 Autres portails
- **`/client/`** - Portal Client
- **`/worker/`** - Portal Ouvrier

## Recommandation

**Garder les deux** car ils ont des rôles différents :
- `/gestion/` = Technique (Django Admin)
- `/admin-dashboard/` = Métier (Interface utilisateur)