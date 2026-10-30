"""How a stored value is shown: as printed when we kept the report's unit, rounded when we converted it.

Converting units gives false precision ("118.9056 mg/dL" for a glucose printed as 6.6 mmol/L); the report itself
never had more than 3 significant figures' worth of meaning.
"""
import math
from decimal import Decimal


def round3(d: Decimal) -> Decimal:
    """Three significant figures, for values we converted: 5.598396 -> 5.6, 151.3344 -> 151, 1234.5 -> 1235."""
    if d == 0:
        return d
    places = max(0, 2 - math.floor(math.log10(abs(d))))
    return d.quantize(Decimal(1).scaleb(-places)).normalize() if places else d.quantize(Decimal(1))


def shown(canonical: Decimal | None, printed: Decimal | None) -> Decimal | None:
    """The canonical value as it should be shown, given the number the report printed."""
    if canonical is None or canonical == printed:
        return canonical
    return round3(canonical)
