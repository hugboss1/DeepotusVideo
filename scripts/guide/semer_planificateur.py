# Une semaine de posts de démonstration posés sur le backend de PREUVE (aucun envoi : aucune clé de réseau).
# Dates relatives à aujourd'hui (heure locale) : deux posts aujourd'hui, puis un par jour sur la semaine suivante.
import json
import sys
import urllib.request
from datetime import datetime, time, timedelta, timezone

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE


def appel(methode, chemin, corps=None):
    req = urllib.request.Request(BASE + "/api" + chemin, method=methode,
                                 data=None if corps is None else json.dumps(corps).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def utc(jour, hh, mm):
    local = datetime.combine(datetime.now().date() + timedelta(days=jour), time(hh, mm)).astimezone()
    return local.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


POSTS = [
    (0, 18, 0, "Le phare du récif", "image", ["telegram", "x"], "scheduled",
     "Ce soir, le phare du récif se rallume. Trois minutes pour comprendre pourquoi."),
    (0, 21, 0, "Coulisses du montage", "seedance", ["instagram", "youtube", "tiktok"], "draft",
     "Dans les coulisses : un plan, trois réglages, une ambiance."),
    (1, 10, 0, "Carte de la semaine", "image", ["telegram"], "draft",
     "La carte de la semaine : un poulpe, une boussole et une marée."),
    (2, 17, 30, "Tutoriel en 30 secondes", "composition", ["youtube", "tiktok"], "draft",
     "Une vidéo en 30 secondes, du texte au rendu."),
    (3, 9, 0, "Revue du matin", "news", ["x", "telegram"], "draft",
     "Revue du matin : trois sujets, trois phrases."),
    (4, 19, 0, "Le récif la nuit", "seedance", ["instagram", "tiktok"], "draft",
     "Le récif la nuit : lumière froide, eau calme."),
    (5, 11, 0, "Question de la semaine", "image", ["x"], "draft",
     "Question de la semaine : quel décor pour le prochain épisode ?"),
]

for p in appel("GET", "/schedule") or []:
    appel("DELETE", f"/schedule/{p['id']}")
for jour, hh, mm, titre, fmt, canaux, statut, legende in POSTS:
    p = appel("POST", "/schedule", {"title": titre, "caption": legende, "channels": canaux, "run_at": utc(jour, hh, mm),
                                    "status": statut, "mode": "assisted", "format": fmt,
                                    "hook": legende.split(":")[0], "source_image": "demo-affiche.png"})
    print(p["run_at"], titre)
