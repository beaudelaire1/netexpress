# Checklist de Validation SEO - Nettoyage Express

## ✅ Pages Publiques Optimisées

### Pages Principales
- [x] **Accueil** (`templates/core/home.html`)
  - Titre optimisé avec les 4 villes
  - Meta description complète
  - Section "Zones d'intervention" ajoutée
  - Alt text des images optimisé
  - Hero avec mentions géographiques

- [x] **Services** (`templates/services/service_list.html`)
  - Titre avec Cayenne et Matoury
  - Meta description localisée
  - Description enrichie

- [x] **Détail Service** (`templates/services/service_detail.html`)
  - Meta tags dynamiques par service
  - Alt text optimisé
  - Mentions géographiques

- [x] **Contact** (`templates/contact/contact.html`)
  - Titre optimisé
  - Meta description avec les 4 villes
  - Open Graph configuré

- [x] **L'Excellence** (`templates/core/excellence.html`)
  - Titre enrichi
  - Contenu avec mentions des villes
  - Meta description complète

- [x] **Réalisations** (`templates/core/realisations.html`)
  - Titre optimisé
  - Meta description
  - Portfolio avec villes dans les titres

- [x] **Devis** (`templates/devis/request_quote.html`)
  - Titre orienté conversion
  - Meta description avec mention rapide

### Template de Base
- [x] **Base** (`templates/base.html`)
  - Lang="fr-GF" pour Guyane
  - Hreflang tags (fr-GF, fr)
  - Balises géo (region, placename, position)
  - Meta keywords optimisés
  - Open Graph complet (avec locale fr_GF)
  - Twitter Cards
  - Schema.org LocalBusiness enrichi
  - Schema.org BreadcrumbList
  - Footer avec zones d'intervention
  - Logo avec alt text optimisé

## 🎯 Ciblage Géographique

### Villes Ciblées
- [x] Cayenne (mentionné 15+ fois sur pages publiques)
- [x] Matoury (adresse principale, 10+ mentions)
- [x] Remire-Montjoly (8+ mentions)
- [x] Macouria (8+ mentions)

### Signaux Géographiques
- [x] Coordonnées GPS (4.8467;-52.3339)
- [x] Code région GF (Guyane Française)
- [x] Code postal 97351 (Matoury)
- [x] Téléphone local 05 94 30 23 68
- [x] Adresse complète

## 📊 Données Structurées (Schema.org)

### LocalBusiness
- [x] Nom
- [x] Description
- [x] URL
- [x] Téléphone
- [x] Adresse complète (streetAddress, postalCode, addressLocality, addressRegion, addressCountry)
- [x] Coordonnées géographiques (GeoCoordinates)
- [x] Prix range (€€)
- [x] Horaires d'ouverture (OpeningHoursSpecification)
- [x] Zones desservies (areaServed) - 4 villes
- [x] Catalogue d'offres (hasOfferCatalog)

### Autres
- [x] BreadcrumbList pour navigation
- [x] Service items dans le catalogue

## 🔍 Optimisation Mots-Clés

### Mots-clés Principaux
- [x] "nettoyage Cayenne"
- [x] "nettoyage Matoury"
- [x] "nettoyage Remire-Montjoly"
- [x] "nettoyage Macouria"
- [x] "entreprise nettoyage Guyane"
- [x] "nettoyage professionnel 973"

### Mots-clés Secondaires
- [x] "entretien espaces verts Cayenne"
- [x] "jardinage Matoury"
- [x] "peinture Cayenne"
- [x] "rénovation Guyane"
- [x] "devis nettoyage gratuit"

### Longue Traîne
- [x] "services professionnels de nettoyage à Cayenne"
- [x] "entreprise de nettoyage à Matoury"
- [x] "entretien d'espaces verts Remire-Montjoly"

## 🖼️ Images et Médias

### Alt Text Optimisé
- [x] Logo avec localisation
- [x] Images services avec villes
- [x] Portfolio avec localisations spécifiques
- [x] Images hero avec contexte

### À Faire (Recommandations)
- [ ] Compresser les images pour performance
- [ ] Ajouter des images webp pour meilleur ratio qualité/poids
- [ ] Créer des images spécifiques par ville

## 🗺️ Sitemap

- [x] Sitemap statique avec priorités différenciées
- [x] Sitemap services dynamique
- [x] Configuration dans robots.txt
- [x] Changefreq appropriés par type de page

## 🔗 Liens Internes

- [x] Menu de navigation cohérent
- [x] Liens vers devis sur toutes les pages
- [x] Footer avec liens et contact
- [x] Section zones d'intervention avec appel à l'action

## 📱 Social Media

### Open Graph
- [x] og:site_name
- [x] og:type (website)
- [x] og:url (dynamique)
- [x] og:locale (fr_GF)
- [x] og:title (personnalisé par page)
- [x] og:description (personnalisée par page)
- [x] og:image (logo)

### Twitter Cards
- [x] twitter:card (summary_large_image)
- [x] twitter:title
- [x] twitter:description

## 🌐 Internationalisation

- [x] Lang="fr-GF" sur balise html
- [x] Hreflang fr-GF
- [x] Hreflang fr (fallback)
- [x] Open Graph locale fr_GF

## 📈 Tests à Effectuer

### Validation Technique
```bash
# Google Rich Results Test
https://search.google.com/test/rich-results?url=[VOTRE_URL]

# Schema.org Validator
https://validator.schema.org/#url=[VOTRE_URL]

# Google PageSpeed Insights
https://pagespeed.web.dev/?url=[VOTRE_URL]

# Mobile-Friendly Test
https://search.google.com/test/mobile-friendly?url=[VOTRE_URL]
```

### Outils de Monitoring
- [ ] Google Search Console configuré
- [ ] Google Analytics avec tracking géographique
- [ ] Google Business Profile créé/optimisé
- [ ] Bing Webmaster Tools configuré

### Vérifications Manuelles
- [ ] Recherche Google: "nettoyage Cayenne"
- [ ] Recherche Google: "entreprise nettoyage Matoury"
- [ ] Recherche Google Maps: "Nettoyage Express Matoury"
- [ ] Test des rich snippets dans résultats de recherche

## 🎯 KPIs à Suivre

### Positions
- [ ] Position pour "nettoyage Cayenne"
- [ ] Position pour "nettoyage Matoury"
- [ ] Position pour "nettoyage Remire-Montjoly"
- [ ] Position pour "nettoyage Macouria"
- [ ] Position pour "nettoyage Guyane"

### Trafic
- [ ] Visites organiques depuis Cayenne
- [ ] Visites organiques depuis Matoury
- [ ] Visites organiques depuis Remire-Montjoly
- [ ] Visites organiques depuis Macouria
- [ ] Impressions dans Google Search

### Conversions
- [ ] Demandes de devis par ville
- [ ] Appels téléphoniques
- [ ] Soumissions de formulaire contact
- [ ] Clics vers Google Maps

## 📋 Prochaines Étapes

### Court Terme (1 mois)
1. Soumettre le sitemap à Google Search Console
2. Créer/optimiser Google Business Profile
3. Encourager premiers avis clients
4. Suivre l'indexation des nouvelles pages

### Moyen Terme (3 mois)
1. Créer contenu blog localisé
2. Obtenir des backlinks locaux
3. Créer pages dédiées par ville si pertinent
4. Optimiser les images

### Long Terme (6+ mois)
1. Développer le maillage de contenu local
2. Créer vidéos de réalisations géolocalisées
3. Développer des partenariats locaux
4. Créer une stratégie de contenu continue

## ✨ Résumé

**Pages optimisées** : 7 pages publiques principales  
**Villes ciblées** : 4 (Cayenne, Matoury, Remire-Montjoly, Macouria)  
**Mots-clés principaux** : 15+  
**Données structurées** : 2 types (LocalBusiness, BreadcrumbList)  
**Meta tags** : 17 dans base.html + spécifiques par page  
**Alt text optimisés** : 15+ images  

**Impact attendu** : Amélioration significative du référencement local en Guyane avec ciblage précis des 4 villes principales.
