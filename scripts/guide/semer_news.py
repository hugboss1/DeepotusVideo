# Des articles FICTIFS pour l'écran News du backend de PREUVE : trois flux RSS servis le temps du semis par un petit
# serveur local, à la place des flux réels (aucun titre de presse réel dans les captures du guide).
# Une même dépêche reprise par les trois médias (fusionnée, tendance), un article écarté par la liste noire.
import json
import sys
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE
MAINTENANT = datetime.now(timezone.utc)

MEDIAS = {
    "recif": ("Gazette du Récif", [
        (1, "Le phare du récif rallumé après dix ans de silence",
         "La municipalité a rallumé le phare du récif ; les pêcheurs saluent un repère retrouvé."),
        (3, "Une nouvelle carte des courants publiée pour les plaisanciers",
         "Le service maritime publie une carte libre des courants côtiers, mise à jour chaque semaine."),
        (5, "Festival des lanternes : le programme dévoilé",
         "Trois soirées de lanternes flottantes sur le port, du jeudi au samedi."),
        (2, "Promotion spéciale : cliquez ici pour gagner",
         "Un contenu sponsorisé que la liste noire du filtre écarte."),
    ]),
    "maree": ("Le Courrier des Marées", [
        (2, "Phare du récif : rallumé après dix ans de silence",
         "Le feu du récif brille de nouveau ; la ville parle d'un symbole pour le port."),
        (4, "Les écoles de voile font le plein pour l'automne",
         "Les inscriptions aux stages d'automne dépassent celles de l'an dernier."),
        (7, "Un atelier gratuit de photo sous-marine au musée",
         "Le musée de la mer ouvre un atelier d'initiation, matériel prêté."),
    ]),
    "large": ("Radio du Large", [
        (2, "Le phare du récif rallumé après 10 ans de silence",
         "Reportage au pied du phare, rallumé hier soir devant quelques centaines d'habitants."),
        (6, "Marché du port : les producteurs locaux à l'honneur",
         "Le marché du samedi accueille vingt nouveaux producteurs de la côte."),
        (9, "Tempête annoncée en fin de semaine : les conseils de prudence",
         "Les autorités rappellent les consignes avant le coup de vent attendu."),
    ]),
}


def flux(cle):
    nom, articles = MEDIAS[cle]
    items = "".join(
        f"<item><title>{t}</title><link>https://exemple.invalid/{cle}/{k}</link><description>{d}</description>"
        f"<pubDate>{format_datetime(MAINTENANT - timedelta(hours=h))}</pubDate></item>"
        for k, (h, t, d) in enumerate(articles))
    return (f"<?xml version='1.0' encoding='utf-8'?><rss version='2.0'><channel><title>{nom}</title>"
            f"<link>https://exemple.invalid/{cle}</link><description>{nom}</description>{items}</channel></rss>")


class Flux(BaseHTTPRequestHandler):
    def do_GET(self):
        corps = flux(self.path.strip("/").removesuffix(".xml")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/rss+xml; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *a):
        pass


def appel(methode, chemin, corps=None):
    req = urllib.request.Request(BASE + "/api" + chemin, method=methode,
                                 data=None if corps is None else json.dumps(corps).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"null")


serveur = ThreadingHTTPServer(("127.0.0.1", 0), Flux)
threading.Thread(target=serveur.serve_forever, daemon=True).start()
port = serveur.server_address[1]
try:
    for s in appel("GET", "/news/sources")["sources"]:
        appel("DELETE", f"/news/sources/{s['id']}")
    for cle, (nom, _) in MEDIAS.items():
        appel("POST", "/news/sources", {"url": f"http://127.0.0.1:{port}/{cle}.xml", "name": nom, "type": "rss"})
    appel("PUT", "/news/filter", {"mots_cles": [], "sources_noires": [], "mots_noirs": ["sponsorisé", "cliquez ici"],
                                  "fraicheur_h": 48})
    r = appel("POST", "/news/refresh")
    print("articles :", r["item_count"], "fusionnés :", r["merged_count"], "erreurs :", len(r["errors"]))
finally:
    serveur.shutdown()
