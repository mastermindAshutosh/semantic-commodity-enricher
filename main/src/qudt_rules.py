# src/qudt_rules.py

from .config import NAMESPACES
UNIT_NS = NAMESPACES["UNIT"]

QUDT_CANONICAL_UNITS = {
    "oil": "BBL",
    "crude": "BBL",
    "barrel": "BBL",
    "barrels": "BBL",
    "gold": "OZ_T",
    "silver": "OZ_T",
    "gas": "MMBTU",
}

QUDT_CONVERSIONS = {
    "BBL": 0.1589873,
    "OZ_T": 0.0311035,
    "MMBTU": 28.263682,
}

def infer_unit(text):
    text = (text or "").lower()
    for keyword, code in QUDT_CANONICAL_UNITS.items():
        if keyword in text:
            return code
    return None

def unit_code_to_uri(code):
    return f"{UNIT_NS}{code}"

def get_multiplier(code):
    return QUDT_CONVERSIONS.get(code)
