# Données de démonstration de l'Atelier sur le backend de PREUVE (8809) : un chapitre, deux entités, un découpage
# « par paragraphe » (gratuit, sans IA). Jamais le 8765.
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE


def api(methode, chemin, corps=None):
    req = urllib.request.Request(BASE + "/api" + chemin, method=methode,
                                 data=json.dumps(corps).encode() if corps is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


TEXTE = ("Le phare de Brume-Noire s'allume chaque soir à la même heure. Mara, la gardienne, monte les cent douze marches "
         "en comptant à voix basse.\n\n"
         "Cette nuit-là, la lanterne refuse de tourner. Mara pose la main sur le verre froid et sent, sous ses doigts, "
         "une lente pulsation.\n\n"
         "En bas, sur les rochers, une forme immense déploie ses bras. Le poulpe de la baie est revenu, et il regarde la "
         "lumière comme on regarde un vieil ami.")
ch = api("POST", "/chapters", {"title": "Le phare de Brume-Noire", "series": "Démo", "script_text": TEXTE})
cid = ch.get("id") or ch.get("chapter", {}).get("id")
for kind, nom, desc in (("character", "Mara", "Gardienne du phare, cinquante ans, ciré jaune."),
                        ("location", "Le phare de Brume-Noire", "Phare de granit sur une pointe battue par la houle.")):
    try:
        api("POST", "/bible/entities", {"kind": kind, "name": nom, "description": desc})
    except Exception as e:                                   # noqa: BLE001 — un kind différent selon la version
        print("entité", nom, e)
d = api("POST", f"/chapters/{cid}/storyboard/decoupe", {"method": "paragraph", "language": "fr"})
print("chapitre", cid, "plans", len(d.get("shots", d) if isinstance(d, dict) else d))
