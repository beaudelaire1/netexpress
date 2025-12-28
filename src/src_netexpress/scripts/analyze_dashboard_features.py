#!/usr/bin/env python
"""
Script d'analyse des fonctionnalités des dashboards pour la rationalisation.

Ce script analyse les différences entre /dashboard/ et /admin-dashboard/
pour identifier les fonctionnalités à migrer ou supprimer.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netexpress.settings.base')
django.setup()

from django.urls import reverse, NoReverseMatch
from django.test import Client
from django.contrib.auth.models import User
from accounts.models import Profile
from devis.models import Quote
from factures.models import Invoice
from tasks.models import Task
from messaging.models import EmailMessage


class DashboardAnalyzer:
    """Analyseur des fonctionnalités des dashboards."""
    
    def __init__(self):
        self.client = Client()
        self.setup_test_users()
    
    def setup_test_users(self):
        """Créer des utilisateurs de test pour l'analyse."""
        # Superuser
        self.superuser = User.objects.create_superuser(
            'superuser_test', 'super@test.com', 'password123'
        )
        
        # Staff user (admin business)
        self.staff_user = User.objects.create_user(
            'staff_test', 'staff@test.com', 'password123', is_staff=True
        )
        Profile.objects.create(user=self.staff_user, role='admin_business')
        
        print("✓ Utilisateurs de test créés")
    
    def analyze_dashboard_views(self):
        """Analyser les vues dashboard existantes."""
        print("\n" + "="*60)
        print("ANALYSE DES VUES DASHBOARD")
        print("="*60)
        
        # Analyser /dashboard/
        print("\n1. ANALYSE DE /dashboard/")
        print("-" * 30)
        self.analyze_technical_dashboard()
        
        # Analyser /admin-dashboard/
        print("\n2. ANALYSE DE /admin-dashboard/")
        print("-" * 30)
        self.analyze_admin_dashboard()
        
        # Comparaison
        print("\n3. COMPARAISON ET RECOMMANDATIONS")
        print("-" * 30)
        self.compare_dashboards()
    
    def analyze_technical_dashboard(self):
        """Analyser le dashboard technique (/dashboard/)."""
        self.client.force_login(self.superuser)
        
        try:
            response = self.client.get('/dashboard/')
            if response.status_code == 200:
                context = response.context
                
                print("✓ Dashboard technique accessible")
                print(f"  Template: {response.templates[0].name}")
                
                # Analyser le contexte
                if context:
                    print("  Données du contexte:")
                    for key, value in context.items():
                        if not key.startswith('_') and key not in ['request', 'user', 'perms']:
                            if hasattr(value, '__len__') and not isinstance(value, str):
                                print(f"    - {key}: {len(value)} éléments")
                            else:
                                print(f"    - {key}: {type(value).__name__}")
                
                # Analyser les statistiques
                self.analyze_dashboard_stats(context, "technique")
                
            else:
                print(f"✗ Dashboard technique inaccessible (status: {response.status_code})")
                
        except Exception as e:
            print(f"✗ Erreur lors de l'accès au dashboard technique: {e}")
    
    def analyze_admin_dashboard(self):
        """Analyser le dashboard admin business (/admin-dashboard/)."""
        self.client.force_login(self.staff_user)
        
        try:
            response = self.client.get('/admin-dashboard/')
            if response.status_code == 200:
                context = response.context
                
                print("✓ Dashboard admin business accessible")
                print(f"  Template: {response.templates[0].name}")
                
                # Analyser le contexte
                if context:
                    print("  Données du contexte:")
                    for key, value in context.items():
                        if not key.startswith('_') and key not in ['request', 'user', 'perms']:
                            if hasattr(value, '__len__') and not isinstance(value, str):
                                print(f"    - {key}: {len(value)} éléments")
                            else:
                                print(f"    - {key}: {type(value).__name__}")
                
                # Analyser les statistiques
                self.analyze_dashboard_stats(context, "admin_business")
                
            else:
                print(f"✗ Dashboard admin business inaccessible (status: {response.status_code})")
                
        except Exception as e:
            print(f"✗ Erreur lors de l'accès au dashboard admin: {e}")
    
    def analyze_dashboard_stats(self, context, dashboard_type):
        """Analyser les statistiques d'un dashboard."""
        print(f"  Statistiques {dashboard_type}:")
        
        # Statistiques communes
        stats_keys = [
            'invoice_stats', 'task_stats', 'quote_stats',
            'total_revenue', 'monthly_revenue', 'pending_revenue',
            'conversion_rate', 'task_completion_rate'
        ]
        
        for key in stats_keys:
            if key in context:
                value = context[key]
                if isinstance(value, dict):
                    print(f"    - {key}: {list(value.keys())}")
                else:
                    print(f"    - {key}: {value}")
        
        # Listes d'objets
        list_keys = [
            'tasks', 'quotes', 'invoices', 'recent_messages',
            'recent_quotes', 'recent_invoices', 'recent_tasks'
        ]
        
        for key in list_keys:
            if key in context:
                items = context[key]
                if hasattr(items, '__len__'):
                    print(f"    - {key}: {len(items)} éléments")
    
    def compare_dashboards(self):
        """Comparer les fonctionnalités des deux dashboards."""
        print("FONCTIONNALITÉS IDENTIFIÉES:")
        print()
        
        # Fonctionnalités du dashboard technique
        print("Dashboard Technique (/dashboard/):")
        tech_features = [
            "- Statistiques rapides (ERP)",
            "- Liste des tâches récentes (5 dernières)",
            "- Liste des devis récents (5 derniers)", 
            "- Liste des factures récentes (5 dernières)",
            "- Messages email récents (5 derniers)",
            "- Compteurs par statut (invoices, tasks, quotes)"
        ]
        for feature in tech_features:
            print(f"  {feature}")
        
        print()
        print("Dashboard Admin Business (/admin-dashboard/):")
        admin_features = [
            "- KPIs financiers (CA total, mensuel, en attente)",
            "- Taux de conversion des devis",
            "- Performance des tâches (taux de completion)",
            "- Performance des ouvriers (statistiques détaillées)",
            "- Répartition par statut (devis, factures, tâches)",
            "- Activité récente (devis, factures, tâches)",
            "- Actions rapides (création d'entités)",
            "- Métriques temps réel"
        ]
        for feature in admin_features:
            print(f"  {feature}")
        
        print()
        print("RECOMMANDATIONS:")
        print("✓ SUPPRIMER le dashboard technique (/dashboard/)")
        print("✓ CONSERVER le dashboard admin business (/admin-dashboard/)")
        print("✓ MIGRER les fonctionnalités uniques si nécessaires")
        print()
        
        # Analyse des doublons
        print("ANALYSE DES DOUBLONS:")
        duplicates = [
            "Listes des tâches récentes",
            "Listes des devis récents", 
            "Listes des factures récentes",
            "Statistiques par statut"
        ]
        
        for duplicate in duplicates:
            print(f"  ⚠️  {duplicate} (présent dans les deux)")
        
        print()
        print("FONCTIONNALITÉS UNIQUES À MIGRER:")
        unique_tech = [
            "Messages email récents (si pas dans admin dashboard)"
        ]
        
        for unique in unique_tech:
            print(f"  📋 {unique}")
    
    def analyze_url_patterns(self):
        """Analyser les patterns d'URLs."""
        print("\n" + "="*60)
        print("ANALYSE DES PATTERNS D'URLS")
        print("="*60)
        
        # URLs à supprimer
        urls_to_remove = [
            '/dashboard/',
        ]
        
        # URLs à conserver
        urls_to_keep = [
            '/admin-dashboard/',
            '/gestion/',
            '/client/',
            '/worker/'
        ]
        
        print("\nURLs À SUPPRIMER:")
        for url in urls_to_remove:
            print(f"  ❌ {url}")
        
        print("\nURLs À CONSERVER:")
        for url in urls_to_keep:
            print(f"  ✅ {url}")
    
    def analyze_user_access_patterns(self):
        """Analyser les patterns d'accès utilisateur."""
        print("\n" + "="*60)
        print("ANALYSE DES PATTERNS D'ACCÈS")
        print("="*60)
        
        # Simuler différents types d'utilisateurs
        access_matrix = {
            'Superuser': {
                'current': ['/dashboard/', '/admin-dashboard/', '/gestion/'],
                'target': ['/gestion/']
            },
            'Staff (Admin Business)': {
                'current': ['/dashboard/', '/admin-dashboard/', '/gestion/'],
                'target': ['/admin-dashboard/', '/gestion/ (lecture)']
            },
            'Worker': {
                'current': ['/worker/'],
                'target': ['/worker/']
            },
            'Client': {
                'current': ['/client/'],
                'target': ['/client/']
            }
        }
        
        print("\nMATRICE D'ACCÈS:")
        print("-" * 50)
        
        for user_type, access in access_matrix.items():
            print(f"\n{user_type}:")
            print(f"  Actuel: {', '.join(access['current'])}")
            print(f"  Cible:  {', '.join(access['target'])}")
            
            # Identifier les changements
            current_set = set(access['current'])
            target_set = set(access['target'])
            
            removed = current_set - target_set
            added = target_set - current_set
            
            if removed:
                print(f"  ❌ Supprimé: {', '.join(removed)}")
            if added:
                print(f"  ➕ Ajouté: {', '.join(added)}")
    
    def generate_migration_plan(self):
        """Générer un plan de migration détaillé."""
        print("\n" + "="*60)
        print("PLAN DE MIGRATION DÉTAILLÉ")
        print("="*60)
        
        migration_steps = [
            {
                'step': 1,
                'title': 'Audit et Sauvegarde',
                'actions': [
                    'Sauvegarder la base de données',
                    'Documenter les fonctionnalités actuelles',
                    'Identifier les utilisateurs affectés'
                ]
            },
            {
                'step': 2,
                'title': 'Préparation du Code',
                'actions': [
                    'Créer les nouveaux rôles admin_technical/admin_business',
                    'Migrer les données utilisateur',
                    'Mettre à jour le middleware d\'accès'
                ]
            },
            {
                'step': 3,
                'title': 'Suppression du Dashboard Technique',
                'actions': [
                    'Supprimer la vue dashboard() dans core/views.py',
                    'Supprimer l\'URL /dashboard/ dans core/urls.py',
                    'Supprimer le template dashboard.html',
                    'Migrer les fonctionnalités uniques vers admin_dashboard'
                ]
            },
            {
                'step': 4,
                'title': 'Tests et Validation',
                'actions': [
                    'Exécuter les tests de régression',
                    'Tester les accès par rôle',
                    'Valider les redirections',
                    'Vérifier les performances'
                ]
            },
            {
                'step': 5,
                'title': 'Déploiement',
                'actions': [
                    'Déployer en staging',
                    'Tests utilisateur',
                    'Déploiement production',
                    'Monitoring post-déploiement'
                ]
            }
        ]
        
        for step_info in migration_steps:
            print(f"\nÉTAPE {step_info['step']}: {step_info['title']}")
            print("-" * 40)
            for action in step_info['actions']:
                print(f"  • {action}")
    
    def cleanup_test_data(self):
        """Nettoyer les données de test."""
        try:
            self.superuser.delete()
            self.staff_user.delete()
            print("\n✓ Données de test nettoyées")
        except Exception as e:
            print(f"\n⚠️  Erreur lors du nettoyage: {e}")
    
    def run_analysis(self):
        """Exécuter l'analyse complète."""
        print("ANALYSEUR DES DASHBOARDS NETEXPRESS V2")
        print("="*60)
        
        try:
            self.analyze_dashboard_views()
            self.analyze_url_patterns()
            self.analyze_user_access_patterns()
            self.generate_migration_plan()
            
        finally:
            self.cleanup_test_data()
        
        print("\n" + "="*60)
        print("ANALYSE TERMINÉE")
        print("="*60)
        print("\nProchaines étapes:")
        print("1. Réviser le plan de migration")
        print("2. Valider avec l'équipe")
        print("3. Commencer l'implémentation")


if __name__ == '__main__':
    analyzer = DashboardAnalyzer()
    analyzer.run_analysis()