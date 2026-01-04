# Note sur le Code Pays pour la Guyane Française

## Décision: Utilisation de "GF" pour Guyane Française

### Context
Dans les templates, nous utilisons le code pays **"GF"** pour la Guyane française dans:
- Les balises `geo.region`
- Les attributs `addressCountry` dans Schema.org
- Les balises `hreflang` (fr-GF)
- L'attribut `lang` de la page (fr-GF)

### Justification

**GF** est le code ISO 3166-1 alpha-2 officiel pour la Guyane française, reconnu par:
- Schema.org
- Google Search (pour le ciblage géographique)
- ISO 3166 (standard international)
- Les moteurs de recherche pour le SEO local

### Alternative: FR

Certains services pourraient s'attendre à **"FR"** (France) car la Guyane est un département d'outre-mer français. Cependant:

1. **Pour le SEO local**, GF est préférable car il permet un ciblage géographique précis
2. **Google Search Console** reconnaît GF comme zone géographique distincte
3. **Les recherches locales** bénéficient d'un ciblage GF plutôt que FR générique
4. **Schema.org** recommande l'utilisation du code ISO pour `addressCountry`

### Impact SEO

L'utilisation de GF permet:
- ✅ Meilleur ciblage géographique pour les recherches en Guyane
- ✅ Apparition dans les résultats "près de chez moi" pour les utilisateurs en Guyane
- ✅ Distinction claire entre Guyane et France métropolitaine
- ✅ Meilleur ranking pour les recherches locales guyanaises

### Compatibilité

Si jamais un service externe nécessite FR au lieu de GF:
1. Cela peut être facilement modifié en remplaçant "GF" par "FR" dans:
   - `templates/base.html` (ligne ~59 et autres occurrences)
   - Les meta tags geo.region
   - Les attributs lang et hreflang

### Références

- [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2)
- [Google Search Central - International Targeting](https://developers.google.com/search/docs/specialty/international)
- [Schema.org - addressCountry](https://schema.org/addressCountry)

---

**Recommandation**: Conserver GF pour optimiser le référencement local en Guyane.
