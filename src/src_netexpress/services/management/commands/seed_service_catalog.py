"""Catalogue de prestations de Nettoyage Express, rejouable sans risque.

À la différence de ``seed_demo_data``, cette commande ne crée ni client, ni devis,
ni facture : uniquement le référentiel des prestations. Elle est donc sûre en
production, où le catalogue est un prérequis — sans lui, aucun devis ne peut être
composé.

Rejouer la commande met à jour les libellés sans dupliquer : l'appariement se
fait sur le slug pour les catégories et sur le titre pour les prestations, tous
deux uniques en base. Les tâches d'une prestation sont réécrites intégralement,
faute de clé stable pour les apparier une à une.

Les durées sont des estimations de départ destinées au chiffrage ; elles se
règlent ensuite depuis l'administration. Aucun prix n'est défini ici : la
tarification appartient aux lignes de devis, pas au référentiel.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from services.models import Category, Service, ServiceTask

# Le climat équatorial guyanais dicte une partie de ce catalogue : repousse
# rapide imposant un débroussaillage régulier, humidité permanente qui fait
# proliférer mousses et moisissures sur les façades comme à l'intérieur.
CATALOGUE: list[dict] = [
    {
        "slug": "espaces-verts",
        "name": "Espaces verts",
        "services": [
            {
                "title": "Débroussaillage de terrain",
                "short_description": "Remise en état de parcelles envahies, jusqu'aux terrains laissés à l'abandon.",
                "description": (
                    "Coupe de la végétation herbacée et arbustive sur terrain nu ou bâti. "
                    "Sous climat équatorial, une parcelle non entretenue redevient impraticable "
                    "en quelques mois : l'intervention rétablit l'accès et la visibilité, puis "
                    "peut être reconduite selon un rythme convenu ensemble. "
                    "Évacuation des rémanents chiffrée à part selon le volume."
                ),
                "unit_type": "m²",
                "duration_minutes": 240,
                "tasks": [
                    "Repérage du terrain et des points sensibles",
                    "Débroussaillage mécanique",
                    "Finition manuelle autour des obstacles",
                    "Regroupement des rémanents",
                    "Contrôle final avec le client",
                ],
            },
            {
                "title": "Tonte et entretien de pelouse",
                "short_description": "Passage régulier pour garder un gazon net toute l'année.",
                "description": (
                    "Tonte, finition des bordures et ramassage de l'herbe coupée. "
                    "Prestation pensée pour un passage récurrent — la fréquence se cale sur "
                    "la saison des pluies, où la pousse s'accélère nettement."
                ),
                "unit_type": "m²",
                "duration_minutes": 120,
                "tasks": [
                    "Retrait des obstacles et débris",
                    "Tonte",
                    "Finition des bordures",
                    "Ramassage de l'herbe",
                    "Nettoyage des abords",
                ],
            },
            {
                "title": "Taille de haies et arbustes",
                "short_description": "Mise en forme des haies, massifs et arbustes d'ornement.",
                "description": (
                    "Taille de formation ou d'entretien, sur haies libres comme taillées. "
                    "Les déchets verts sont regroupés et évacués sur demande. "
                    "Chiffrage au mètre linéaire, hauteur prise en compte au devis."
                ),
                "unit_type": "ml",
                "duration_minutes": 180,
                "tasks": [
                    "Protection des massifs voisins",
                    "Taille des faces et du dessus",
                    "Reprise des reprises et gourmands",
                    "Ramassage des déchets de coupe",
                ],
            },
            {
                "title": "Élagage et abattage léger",
                "short_description": "Réduction de branches gênantes et abattage de petits sujets.",
                "description": (
                    "Suppression de branches basses, mortes ou menaçant une toiture, un câble "
                    "ou une clôture. Abattage limité aux sujets de faible hauteur accessibles "
                    "depuis le sol ou une nacelle légère. Les sujets de grande hauteur et les "
                    "interventions sur cordes ne relèvent pas de cette prestation."
                ),
                "unit_type": "forfait",
                "duration_minutes": 300,
                "tasks": [
                    "Diagnostic du sujet et de son environnement",
                    "Balisage de la zone de chute",
                    "Coupe des branches",
                    "Débitage et regroupement",
                    "Remise en état de la zone",
                ],
            },
            {
                "title": "Évacuation de déchets verts",
                "short_description": "Enlèvement et dépose en filière des rémanents de coupe.",
                "description": (
                    "Chargement et transport des déchets verts issus d'une intervention ou "
                    "déjà présents sur place, puis dépose en déchèterie. Facturé au volume "
                    "chargé ; peut compléter n'importe quelle prestation d'espaces verts."
                ),
                "unit_type": "m³",
                "duration_minutes": 120,
                "tasks": [
                    "Estimation du volume",
                    "Chargement",
                    "Transport en filière agréée",
                    "Nettoyage de la zone de stockage",
                ],
            },
            {
                "title": "Contrat d'entretien de jardin",
                "short_description": "Passages planifiés à l'année, pour ne plus y penser.",
                "description": (
                    "Formule récurrente combinant tonte, taille et désherbage selon un "
                    "calendrier arrêté au départ. Le rythme est renforcé en saison des pluies "
                    "et allégé en saison sèche. Le détail des passages figure au devis."
                ),
                "unit_type": "mois",
                "duration_minutes": 240,
                "tasks": [
                    "Visite initiale et calendrier de passages",
                    "Tonte et finitions",
                    "Taille d'entretien",
                    "Désherbage des allées et massifs",
                    "Compte rendu après chaque passage",
                ],
            },
        ],
    },
    {
        "slug": "nettoyage",
        "name": "Nettoyage",
        "services": [
            {
                "title": "Nettoyage de bureaux",
                "short_description": "Entretien régulier des locaux professionnels, hors horaires d'activité.",
                "description": (
                    "Nettoyage des postes de travail, sols, sanitaires et espaces communs. "
                    "Les passages se font avant l'ouverture ou après la fermeture afin de ne "
                    "pas gêner l'activité. Fréquence et périmètre définis au devis."
                ),
                "unit_type": "m²",
                "duration_minutes": 120,
                "tasks": [
                    "Vidage des corbeilles",
                    "Dépoussiérage des surfaces et mobilier",
                    "Nettoyage et désinfection des sanitaires",
                    "Lavage des sols",
                    "Réapprovisionnement des consommables",
                ],
            },
            {
                "title": "Nettoyage de fin de chantier",
                "short_description": "Livraison propre après travaux, prête à recevoir.",
                "description": (
                    "Élimination des poussières de chantier, résidus de peinture, colle et "
                    "adhésifs, jusqu'aux traces sur menuiseries et vitrages. Intervention "
                    "généralement en une fois, dimensionnée à la surface et à l'état du "
                    "chantier constaté lors de la visite."
                ),
                "unit_type": "m²",
                "duration_minutes": 480,
                "tasks": [
                    "Évacuation des gravats légers et emballages",
                    "Dépoussiérage complet, plafonds compris",
                    "Décollage des adhésifs et projections",
                    "Nettoyage des menuiseries et vitrages",
                    "Lavage et rinçage des sols",
                    "Réception avec le maître d'ouvrage",
                ],
            },
            {
                "title": "Remise en état de logement",
                "short_description": "Logement rendu impeccable pour un état des lieux ou une relocation.",
                "description": (
                    "Nettoyage approfondi de toutes les pièces, avec un soin particulier sur "
                    "la cuisine et la salle d'eau, où se joue le plus souvent l'état des lieux. "
                    "Traitement des traces d'humidité dans la limite d'un nettoyage — une "
                    "moisissure installée relève du traitement anti-moisissure."
                ),
                "unit_type": "m²",
                "duration_minutes": 360,
                "tasks": [
                    "Dégraissage de la cuisine et des électroménagers",
                    "Détartrage et désinfection de la salle d'eau",
                    "Nettoyage intérieur des placards",
                    "Vitres et menuiseries",
                    "Lavage des sols et plinthes",
                ],
            },
            {
                "title": "Nettoyage de vitres",
                "short_description": "Vitrages, baies et vérandas sans traces.",
                "description": (
                    "Lavage des faces intérieure et extérieure, encadrements et rails compris. "
                    "Les vitrages en hauteur sont traités à la perche télescopique ; au-delà, "
                    "un moyen d'accès spécifique est chiffré séparément."
                ),
                "unit_type": "m²",
                "duration_minutes": 90,
                "tasks": [
                    "Protection des abords",
                    "Lavage des vitres, deux faces",
                    "Nettoyage des encadrements et rails",
                    "Finition sans traces",
                ],
            },
            {
                "title": "Nettoyage haute pression",
                "short_description": "Façades, terrasses et allées débarrassées des mousses et noircissures.",
                "description": (
                    "Décapage au jet haute pression des surfaces extérieures. Sous ce climat, "
                    "mousses, algues et lichens réapparaissent vite : un traitement préventif "
                    "peut être appliqué après nettoyage pour espacer les passages. "
                    "La pression est adaptée au support pour ne pas l'abîmer."
                ),
                "unit_type": "m²",
                "duration_minutes": 240,
                "tasks": [
                    "Protection des menuiseries et plantations",
                    "Test de pression sur zone discrète",
                    "Passage haute pression",
                    "Rinçage",
                    "Application d'un traitement préventif si retenu",
                ],
            },
            {
                "title": "Entretien de parties communes",
                "short_description": "Halls, escaliers et locaux techniques d'immeubles collectifs.",
                "description": (
                    "Passage régulier sur les circulations d'un immeuble : hall, cages "
                    "d'escalier, ascenseur, local poubelles. Prestation destinée aux syndics "
                    "et bailleurs, avec un rythme et un périmètre contractualisés."
                ),
                "unit_type": "forfait",
                "duration_minutes": 180,
                "tasks": [
                    "Balayage et lavage du hall",
                    "Nettoyage des escaliers et rampes",
                    "Désinfection des points de contact",
                    "Entretien du local poubelles",
                    "Signalement des anomalies au gestionnaire",
                ],
            },
        ],
    },
    {
        "slug": "peinture",
        "name": "Peinture",
        "services": [
            {
                "title": "Peinture intérieure",
                "short_description": "Murs et plafonds repeints, préparation des supports comprise.",
                "description": (
                    "Application en deux couches après préparation du support. La qualité du "
                    "rendu tient d'abord au rebouchage et au ponçage : ils sont inclus, sauf "
                    "reprise lourde qui fait l'objet d'une ligne distincte au devis."
                ),
                "unit_type": "m²",
                "duration_minutes": 480,
                "tasks": [
                    "Protection des sols et du mobilier",
                    "Rebouchage et ponçage",
                    "Application de la sous-couche",
                    "Deux couches de finition",
                    "Retrait des protections et nettoyage",
                ],
            },
            {
                "title": "Peinture extérieure et façade",
                "short_description": "Façades protégées et remises à neuf, adaptées au climat humide.",
                "description": (
                    "Nettoyage préalable, traitement des reprises puis mise en peinture avec "
                    "un produit adapté à l'exposition. Le nettoyage haute pression de la façade "
                    "est un préalable presque systématique et se chiffre à part."
                ),
                "unit_type": "m²",
                "duration_minutes": 600,
                "tasks": [
                    "Nettoyage et séchage du support",
                    "Traitement des fissures et reprises",
                    "Application d'un fixateur",
                    "Deux couches de finition",
                    "Réception avec le client",
                ],
            },
            {
                "title": "Traitement anti-moisissure",
                "short_description": "Élimination des taches noires et protection durable des surfaces.",
                "description": (
                    "Traitement fongicide des zones atteintes, suivi d'une remise en peinture "
                    "avec un produit assainissant. L'humidité permanente rend ces désordres "
                    "fréquents en intérieur comme en extérieur. Si la cause est une infiltration "
                    "ou un défaut de ventilation, elle est signalée : la traiter relève d'une "
                    "autre intervention, sans quoi les taches reviendront."
                ),
                "unit_type": "m²",
                "duration_minutes": 240,
                "tasks": [
                    "Diagnostic de l'origine de l'humidité",
                    "Nettoyage des zones atteintes",
                    "Application du traitement fongicide",
                    "Temps de séchage",
                    "Remise en peinture assainissante",
                ],
            },
            {
                "title": "Peinture de toiture",
                "short_description": "Toitures nettoyées puis protégées contre les UV et les mousses.",
                "description": (
                    "Démoussage, réparation ponctuelle puis application d'une peinture de "
                    "protection. Intervention limitée aux toitures accessibles en sécurité ; "
                    "l'état de la charpente et de la couverture est vérifié avant tout "
                    "engagement."
                ),
                "unit_type": "m²",
                "duration_minutes": 600,
                "tasks": [
                    "Contrôle de l'accessibilité et de la sécurité",
                    "Démoussage et nettoyage",
                    "Réparation des points singuliers",
                    "Application de la peinture de protection",
                    "Contrôle des évacuations d'eau",
                ],
            },
        ],
    },
    {
        "slug": "bricolage",
        "name": "Bricolage",
        "services": [
            {
                "title": "Montage de meubles",
                "short_description": "Meubles livrés en kit assemblés et posés à leur place.",
                "description": (
                    "Assemblage de mobilier en kit, fixation murale comprise lorsqu'elle est "
                    "nécessaire à la stabilité. Les emballages sont évacués sur demande. "
                    "Facturation à l'heure, un forfait pouvant être arrêté au devis."
                ),
                "unit_type": "heure",
                "duration_minutes": 120,
                "tasks": [
                    "Vérification des pièces et de la notice",
                    "Assemblage",
                    "Fixation murale si requise",
                    "Contrôle de stabilité",
                    "Évacuation des emballages",
                ],
            },
            {
                "title": "Pose d'étagères et fixations",
                "short_description": "Tringles, tableaux, téléviseurs et étagères fixés dans les règles.",
                "description": (
                    "Perçage et fixation adaptés à la nature du support — placo, béton, bois — "
                    "avec les chevilles correspondantes. La charge admissible est vérifiée "
                    "avant pose."
                ),
                "unit_type": "heure",
                "duration_minutes": 60,
                "tasks": [
                    "Repérage des réseaux avant perçage",
                    "Traçage et mise à niveau",
                    "Perçage et chevillage adapté au support",
                    "Pose et contrôle de charge",
                ],
            },
            {
                "title": "Petites réparations de plomberie",
                "short_description": "Fuites, joints et robinetterie du quotidien.",
                "description": (
                    "Remplacement de joints, de flexibles, de mécanismes de chasse et de "
                    "robinetterie. Les interventions sur réseau encastré ou nécessitant une "
                    "reprise de maçonnerie sortent de ce cadre et font l'objet d'un devis "
                    "distinct."
                ),
                "unit_type": "heure",
                "duration_minutes": 90,
                "tasks": [
                    "Diagnostic et coupure d'eau",
                    "Dépose de l'élément défectueux",
                    "Pose de la pièce neuve",
                    "Remise en eau et contrôle d'étanchéité",
                ],
            },
            {
                "title": "Petites réparations électriques",
                "short_description": "Remplacement de prises, interrupteurs et luminaires.",
                "description": (
                    "Interventions simples sur installation existante et conforme : "
                    "appareillage, points lumineux, remplacement à l'identique. "
                    "Toute reprise de tableau ou création de circuit relève d'un électricien "
                    "et n'entre pas dans cette prestation."
                ),
                "unit_type": "heure",
                "duration_minutes": 90,
                "tasks": [
                    "Coupure au disjoncteur et consignation",
                    "Dépose de l'appareillage",
                    "Pose et raccordement",
                    "Test de fonctionnement",
                ],
            },
            {
                "title": "Pose de revêtements de sol",
                "short_description": "Sols souples et stratifiés posés sur support préparé.",
                "description": (
                    "Pose de lames stratifiées, vinyle ou moquette, avec sous-couche et "
                    "plinthes ou barres de seuil. La planéité du support est vérifiée au "
                    "préalable : un ragréage éventuel se chiffre séparément."
                ),
                "unit_type": "m²",
                "duration_minutes": 480,
                "tasks": [
                    "Contrôle de la planéité du support",
                    "Pose de la sous-couche",
                    "Pose du revêtement",
                    "Découpes et finitions",
                    "Pose des plinthes ou barres de seuil",
                ],
            },
            {
                "title": "Dépannage et travaux divers",
                "short_description": "Les petits travaux qui traînent, traités en une visite.",
                "description": (
                    "Intervention à l'heure regroupant plusieurs petites demandes : réglage "
                    "de porte, remplacement de serrure, reprise de silicone, fixation diverse. "
                    "La liste est arrêtée avec vous avant l'intervention."
                ),
                "unit_type": "heure",
                "duration_minutes": 120,
                "tasks": [
                    "Recensement des points à traiter",
                    "Réalisation des travaux",
                    "Contrôle avec le client",
                    "Nettoyage de la zone",
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Crée ou met à jour le catalogue de prestations. Rejouable sans doublon."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait écrit, sans rien enregistrer.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        simulation = options["dry_run"]
        categories_creees = services_crees = services_majs = 0

        for bloc in CATALOGUE:
            categorie, cree = Category.objects.get_or_create(
                slug=bloc["slug"], defaults={"name": bloc["name"]}
            )
            if cree:
                categories_creees += 1
            elif categorie.name != bloc["name"]:
                categorie.name = bloc["name"]
                categorie.save(update_fields=["name"])

            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{bloc['name']}"))

            for fiche in bloc["services"]:
                taches = fiche.pop("tasks")
                service, cree = Service.objects.update_or_create(
                    title=fiche["title"],
                    defaults={**fiche, "category": categorie, "is_active": True},
                )
                fiche["tasks"] = taches  # la commande doit rester rejouable en mémoire

                # Réécriture complète : les tâches n'ont pas d'identifiant stable
                # permettant de les apparier une à une entre deux exécutions.
                service.tasks.all().delete()
                ServiceTask.objects.bulk_create(
                    [
                        ServiceTask(service=service, name=nom, order=rang)
                        for rang, nom in enumerate(taches, start=1)
                    ]
                )

                if cree:
                    services_crees += 1
                    marque = self.style.SUCCESS("créé  ")
                else:
                    services_majs += 1
                    marque = self.style.WARNING("mis à jour")
                self.stdout.write(
                    f"  {marque} {service.title} "
                    f"({service.unit_type}, {len(taches)} tâches)"
                )

        resume = (
            f"\n{categories_creees} catégorie(s) créée(s), "
            f"{services_crees} prestation(s) créée(s), "
            f"{services_majs} mise(s) à jour."
        )

        if simulation:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(f"{resume}\nSimulation : rien n'a été enregistré."))
        else:
            self.stdout.write(self.style.SUCCESS(resume))
