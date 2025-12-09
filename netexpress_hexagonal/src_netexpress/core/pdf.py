"""Utilitaires de génération de PDF simples pour les devis.

Le but de ce module est d'offrir une implémentation robuste mais légère,
sans reconstruire tout le moteur de mise en page déjà présent dans
``factures.models.Invoice.generate_pdf``.  Ici, on génère un PDF texte
à partir d'un template Django en se contentant de poser les lignes
les unes sous les autres.

Si tu veux une mise en page plus avancée plus tard (tableaux, logos,
etc.), il suffira d'enrichir ce module en gardant la même signature.
"""

from io import BytesIO
from typing import Dict, Any

from django.template.loader import render_to_string
from django.utils.html import strip_tags

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def render_pdf(template_name: str, context: Dict[str, Any]) -> bytes:
    """Rend un template Django en PDF (texte simple).

    Paramètres
    ----------
    template_name:
        Nom du template à rendre (ex: ``"devis/pdf/quote.html"``).
    context:
        Contexte passé au moteur de templates.

    Retour
    ------
    bytes:
        Contenu binaire du PDF prêt à être enregistré dans un FileField
        ou joint dans un e‑mail.

    Notes
    -----
    - On commence par rendre le template en HTML, puis on nettoie en
      texte brut avec ``strip_tags``.
    - Chaque ligne est posée dans la page avec un interligne fixe.
    - Si le texte déborde, on ajoute des pages automatiquement.
    """
    # 1) Rendu du template en HTML puis conversion en texte brut
    html = render_to_string(template_name, context)
    text = strip_tags(html)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Marges et interligne
    margin_x = 20 * mm
    margin_top = 20 * mm
    line_height = 6 * mm

    x = margin_x
    y = height - margin_top

    # Police de base
    c.setFont("Helvetica", 10)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            # Ligne vide => on saute simplement une ligne
            y -= line_height
            if y < margin_top:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - margin_top
            continue

        # Si on arrive en bas de page, on crée une nouvelle page
        if y < margin_top:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - margin_top

        c.drawString(x, y, line)
        y -= line_height

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
