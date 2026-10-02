from decimal import Context, Decimal, DecimalException, ROUND_HALF_EVEN, localcontext
import re

ARITHMETIC_PROFILE = "r7-decimal34-v1"
REFERENCE_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)


def finite_decimal(value: str) -> Decimal:
    if (not isinstance(value,str) or not value or len(value)>128
            or not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',value)):
        raise ValueError("Bounded finite decimal string required")
    try:
        number=Decimal(value)
        if not number.is_finite() or len(number.as_tuple().digits)>34:
            raise ValueError("Finite decimal with at most 34 significant digits required")
        with localcontext(REFERENCE_CONTEXT) as context:
            result=context.create_decimal(number)
            if result != number:
                raise ValueError("Decimal cannot be represented without input rounding")
        return number
    except DecimalException:
        raise ValueError("Decimal outside arithmetic profile") from None


def canonical_decimal(value: str) -> str:
    number=finite_decimal(value)
    if number.is_zero(): return "0"
    with localcontext(REFERENCE_CONTEXT): normalized=number.normalize()
    if -32 <= normalized.adjusted() <= 33:
        return format(normalized,"f")
    return str(normalized)
