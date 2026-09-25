"""Einmalig ausführen: erzeugt keys/keys.json mit je einem RSA-Schlüssel pro Münzwert."""

import json
import os

from cryptography.hazmat.primitives.asymmetric import rsa

KEYS_PATH = "keys/keys.json"
COIN_VALUES = (1,)

if os.path.exists(KEYS_PATH):
    raise SystemExit(
        f"{KEYS_PATH} existiert schon – nicht überschreiben, sonst werden alle Münzen ungültig"
    )

os.makedirs("keys", exist_ok=True)
signing_keys = {}
for coin_value in COIN_VALUES:
    private_numbers = rsa.generate_private_key(
        public_exponent=65537, key_size=1024
    ).private_numbers()
    signing_keys[coin_value] = {
        "modulus": format(private_numbers.public_numbers.n, "x"),
        "private_exponent": format(private_numbers.d, "x"),
    }
with open(KEYS_PATH, "w") as keys_file:
    json.dump(signing_keys, keys_file, indent=2)
print(f"{KEYS_PATH} geschrieben")
