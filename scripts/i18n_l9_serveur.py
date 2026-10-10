"""Traduction L9 (t149) : le catalogue SERVEUR du Spritelab (« Catalogue de démarrage » : préréglages de particules de
particle_service.PRESETS et séquences animées du catalogue starter) -> backend/app/i18n/messages.json.

  python scripts/i18n_l9_serveur.py          ajoute / met à jour les clés `particules.` dans messages.json
  python scripts/i18n_l9_serveur.py --check  code 1 si messages.json n'est pas à jour

Comme i18n_l4_serveur.py : le français de chaque clé est LU dans la source au moment de la génération, l'anglais est
écrit ici ; une source sans anglais (ou un anglais sans source) fait refuser le générateur. Les clés du lot se placent
juste AVANT celles de i18n_l4_serveur.py (qui garde l'ordre des autres clés puis pose les siennes en fin) : les deux
--check restent vrais l'un après l'autre. Lancé avec le python EMBARQUÉ (il importe l'application).
"""
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
MESSAGES = RACINE / "backend" / "app" / "i18n" / "messages.json"
PREFIXE = "particules."
# les clés du lot se posent AVANT le premier bloc d'un autre générateur qui range les siennes en fin : celui des
# correctifs Planificateur/News (i18n_planif_news_serveur.py) puis celui de L4 — chacun garde ainsi son --check vrai
PREFIXES_L4 = ("quota.", "apercu.", "news.serveur.", "effets.", "transitions.", "livraison.", "titres.gabarit.")

# id -> (nom, description) ; le « type » ne change qu'un mot (boucle -> loop)
EN_PRESETS = {
    "explosion": ("Explosion", "Expanding fireball, falling embers"),
    "smoke": ("Soft smoke", "Slow column that widens and fades"),
    "goldburst": ("Golden burst", "Spray of golden stars, light gravity"),
    "sparks": ("Sparks", "Bright sparks that fall and die out"),
    "magic": ("Magic aura", "Rising wisps, cool tint"),
    "muzzle": ("Muzzle flash", "Very short muzzle flash, straight ahead"),
    "dust": ("Dust", "Ground cloud, falling debris"),
    "trail": ("Trail", "Stretched wake that reads as speed"),
    "embers": ("Floating embers", "Hot spots drifting upward — background layer"),
    "shockwave": ("Shockwave", "Single ring that opens and fades"),
    "lightning": ("Electric arcs", "Jittery discharges, abrupt on/off"),
    "ashes": ("Ash & snow", "Slow drifting fall — full-frame ambience overlay"),
}
EN_ANIMS = {
    "black-smoke": "Black smoke",
    "explosion": "Explosion",
    "low-puff": "Low puff",
    "flash": "Flash",
    "white-puff": "White puff",
}


def attendu() -> bytes:
    from app.services import particle_service as PS, starter_catalog as SC
    lot = {}
    for p in PS.PRESETS:
        if p["id"] not in EN_PRESETS:
            raise SystemExit(f"préréglage {p['id']!r} sans anglais dans EN_PRESETS")
        nom, desc = EN_PRESETS[p["id"]]
        lot[f"{PREFIXE}{p['id']}.nom"] = {"fr": p["name"], "en": nom}
        lot[f"{PREFIXE}{p['id']}.desc"] = {"fr": p["desc"], "en": desc}
        if "boucle" in p["type"]:
            lot[f"{PREFIXE}{p['id']}.type"] = {"fr": p["type"], "en": p["type"].replace("boucle", "loop")}
    for a in SC.load().get("anims", []):
        if a["id"] not in EN_ANIMS:
            raise SystemExit(f"séquence {a['id']!r} sans anglais dans EN_ANIMS")
        lot[f"{PREFIXE}anim.{a['id']}.nom"] = {"fr": a["name"], "en": EN_ANIMS[a["id"]]}
    orphelins = (set(EN_PRESETS) - {p["id"] for p in PS.PRESETS}) | (set(EN_ANIMS) - {a["id"] for a in SC.load().get("anims", [])})
    if orphelins:
        raise SystemExit(f"anglais sans source : {sorted(orphelins)}")
    actuel = json.loads(MESSAGES.read_bytes().decode("utf-8"))
    autres = [(k, v) for k, v in actuel.items() if not k.startswith(PREFIXE)]
    k4 = next((i for i, (k, _v) in enumerate(autres) if k.startswith(PREFIXES_L4)), len(autres))
    neuf = autres[:k4] + sorted(lot.items()) + autres[k4:]
    return ("{\n" + ",\n".join(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
                               for k, v in neuf) + "\n}\n").encode("utf-8")


def main(args):
    b = attendu()
    if "--check" in args:
        ok = MESSAGES.read_bytes().replace(b"\r\n", b"\n") == b
        print("à jour" if ok else "PÉRIMÉ : python scripts/i18n_l9_serveur.py (python embarqué)")
        return 0 if ok else 1
    MESSAGES.write_bytes(b)
    print("messages.json écrit")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
