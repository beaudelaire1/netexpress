from decimal import Decimal
from typing import Iterable

from hexcore.domain.invoicing import InvoiceAggregate, InvoiceLine


class InvoiceFactory:
  """Service de construction d'agrégats de facture à partir des modèles Django."""

  def build_from_facture(self, facture) -> InvoiceAggregate:
    # On importe localement pour éviter les problèmes d'import circulaire
    from factures.models import Facture  # type: ignore

    if not isinstance(facture, Facture):
      raise TypeError("facture doit être une instance de Facture")

    client_label = getattr(facture, "client_display", str(facture.client))
    lines = []

    for item in self._iter_items(facture):
      line = InvoiceLine(
        description=str(getattr(item, "description", item)),
        quantity=Decimal(str(getattr(item, "quantity", 1))),
        unit_price_ht=Decimal(str(getattr(item, "unit_price_ht", 0))),
        vat_rate=Decimal(str(getattr(item, "vat_rate", 0))),
      )
      lines.append(line)

    return InvoiceAggregate(
      number=str(getattr(facture, "numero", facture.pk)),
      customer_label=client_label,
      lines=lines,
    )

  def _iter_items(self, facture) -> Iterable[object]:
    """Point d'extension : récupère les lignes de la facture.

    On reste volontairement défensif pour ne pas casser
    l'existant si la structure interne évolue.
    """
    items = getattr(facture, "items", None) or getattr(facture, "lignes", None)
    if items is None:
      # Fallback : on ne renvoie rien, l'appelant peut gérer une facture vide
      return []
    return items.all() if hasattr(items, "all") else items
