# Plan NetExpress 2026-04-10

## Décisions d'architecture actives
- NetExpress doit rester cohérent comme mini ERP: /admin-dashboard/ est le cockpit métier admin, /gestion/ reste une interface technique secondaire.
- Les liens transverses partagés doivent passer par des helpers centraux de portail, jamais par des href codés en dur vers /gestion/ ou /messages/ legacy.
- La messagerie métier doit rester sous le préfixe du portail courant: /admin-dashboard/messages/, /worker/messages/, /client/messages/.

## Réalisé
- Correction du lien Dashboard public et des retours legacy pour éviter les sorties métier vers /gestion/.
- Introduction d'un helper central portal_home_url pour les layouts partagés et écrans historiques.
- Clarification du CTA /gestion/ dans le dashboard admin comme accès technique avancé, pas comme dashboard métier.
- Correction du template d'email facture qui pointait encore vers localhost /gestion/.
- Refonte ERP léger déjà en place côté admin: import Excel clients, création client enrichie, création de tâche gardée sous /admin-dashboard/, cockpit client approfondi.
- Renfort du portail client premium et des outils de supervision email déjà intégrés.

## Dernière itération validée
- Alignement de la messagerie sur les namespaces portail avec helper dédié et redirection de sécurité depuis les anciennes URLs /messages/.
- Nettoyage des templates critiques admin, layouts principaux et écrans de messagerie qui utilisaient encore messaging:* en dur.
- Nettoyage complet des templates client restants, y compris dashboards, listes, fiches détail et écrans de validation, pour pointer directement vers les routes portail de messagerie.
- Ajout et validation de tests ciblés de non-régression sur la cohérence ERP des liens Dashboard et Messages.
- Ajout d'un lien métier explicite entre tâche et client pour rendre le suivi d'avancement visible dans le portail client.
- Ajout d'une vue Mes Interventions côté client, d'un résumé dans le dashboard premium et du rattachement client dans les écrans admin de création, édition, détail et liste des tâches.

## Validation récente
- Les tests ciblés sur le helper de route messages, la redirection legacy admin et le Dashboard superuser passent.
- Les vues client touchées restent cohérentes via des tests ciblés, et les 17 templates client modifiés compilent correctement côté Django.
- La validation manage.py check est propre après la correction.
- La migration tasks.0005_task_client est appliquée en local et les tests ciblés du nouveau suivi de tâches client passent.
- La suite complète tests.test_client_portal_units passe après l'ajout des interventions dans le portail client.
- Point d'attention connu: une partie ancienne des tests messaging utilise encore client.login(...) et remonte une dette Axes hors du périmètre de cette correction.

## Prochaines actions
- Traiter la dette de tests messaging encore dépendants de client.login(...) pour éviter les erreurs AxesBackendRequestParameterRequired.
- Continuer la réduction de dette structurelle dans core/views.py.
- Compléter les tests d'import Excel et les chantiers RGPD/cache restants sans casser la cohérence ERP des portails.
