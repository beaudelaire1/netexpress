# 🎨 Guide des couleurs Admin Nettoyage Express

## Couleur principale du thème
**#0f6b4c** - Cette couleur est maintenant utilisée dans toute l'interface d'administration

## Palette de couleurs dérivée

| Utilisation | Couleur | Code HEX |
|-------------|---------|----------|
| **Couleur principale** | ![#0f6b4c](https://via.placeholder.com/20/0f6b4c/000000?text=+) | `#0f6b4c` |
| **Hover/Focus** | ![#0d5940](https://via.placeholder.com/20/0d5940/000000?text=+) | `#0d5940` |
| **Sidebar** | ![#0a4734](https://via.placeholder.com/20/0a4734/000000?text=+) | `#0a4734` |
| **Très sombre** | ![#083528](https://via.placeholder.com/20/083528/000000?text=+) | `#083528` |
| **Arrière-plan clair** | ![#f0fdf7](https://via.placeholder.com/20/f0fdf7/000000?text=+) | `#f0fdf7` |

## Éléments stylisés

### Navigation
- **Navbar principale** : `#0f6b4c`
- **Hover navbar** : `#0d5940`

### Sidebar
- **Arrière-plan** : `#0a4734`
- **Liens actifs** : `#0f6b4c`
- **Hover** : `#0d5940`

### Boutons
- **Bouton primaire** : `#0f6b4c`
- **Hover bouton** : `#0d5940`
- **Focus** : Ombre avec `rgba(15, 107, 76, 0.25)`

### Formulaires
- **Focus input** : Bordure `#0f6b4c`
- **Checkboxes cochées** : `#0f6b4c`

### Autres éléments
- **Liens** : `#0f6b4c`
- **Badges** : `#0f6b4c`
- **Progress bars** : `#0f6b4c`
- **Pagination active** : `#0f6b4c`

## Comment vérifier

1. Accédez à `/gestion/` pour voir l'interface admin
2. Vérifiez que la navbar est bien en `#0f6b4c`
3. Vérifiez que la sidebar est en `#0a4734`
4. Testez les boutons et liens pour voir les couleurs hover
5. Ouvrez `static/css/admin_color_test.html` pour un aperçu des couleurs

## Cohérence avec le site

✅ **Parfaite harmonie** : L'admin utilise maintenant exactement la même couleur principale que le site public  
✅ **Branding unifié** : Expérience utilisateur cohérente entre toutes les interfaces  
✅ **Accessibilité** : Contraste suffisant pour une bonne lisibilité  

## Fichiers modifiés

- `static/css/jazzmin_overrides.css` - Styles personnalisés admin
- `netexpress/settings/base.py` - Configuration Jazzmin
- `static/css/admin_color_test.html` - Page de test des couleurs