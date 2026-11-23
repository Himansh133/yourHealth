import secrets

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CHECK = ALPHABET + "*~$=U"

def new_patient_code():
    value = secrets.randbits(40)
    digits = "".join(ALPHABET[(value >> shift) & 31] for shift in range(35, -1, -5))
    return "YH-" + digits + CHECK[value % 37]

def normalize_patient_code(code):
    code = code.upper().replace("-", "").replace(" ", "")
    if not code.startswith("YH") or len(code) != 11:
        return None
    digits = code[2:10].replace("O", "0").replace("I", "1").replace("L", "1")
    if any(c not in ALPHABET for c in digits):
        return None
    value = 0
    for c in digits:
        value = value * 32 + ALPHABET.index(c)
    return "YH-" + digits + code[-1] if CHECK[value % 37] == code[-1] else None
