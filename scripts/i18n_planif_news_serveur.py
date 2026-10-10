"""Correctifs de traduction du 10/10/2026 : les textes SERVEUR du Planificateur et de News -> backend/app/i18n/messages.json.

  python scripts/i18n_planif_news_serveur.py          ajoute / met à jour les clés du lot (préfixes quota., apercu.,
                                                      news.serveur.) dans messages.json ; les autres clés restent
  python scripts/i18n_planif_news_serveur.py --check  code 1 si messages.json n'est pas à jour

Le français de chaque clé vient de la SOURCE : lu dans la table (quota.LIMITS, news_forms._CATALOGUE) ou, pour un
motif écrit dans le code, gabarit écrit ici dont chaque morceau fixe doit se retrouver dans le fichier source nommé
(un motif changé dans le service sans changer sa clé fait refuser le générateur). L'anglais est écrit ici.
Les clés du lot se placent juste AVANT les clés de i18n_l4_serveur.py (effets., transitions.…) : ce générateur-là
garde l'ordre des autres clés puis pose les siennes en fin, donc son --check reste vrai après celui-ci.
Lancé avec le python EMBARQUÉ (il importe l'application : pydantic-settings).
"""
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
MESSAGES = RACINE / "backend" / "app" / "i18n" / "messages.json"
PREFIXES = ("quota.", "apercu.", "news.serveur.")
PREFIXES_L4 = ("effets.", "transitions.", "livraison.", "titres.gabarit.")
SERVICES = RACINE / "backend" / "app" / "services"

# quota.LIMITS : la source datée de chaque plafond
EN_QUOTA = {
    "x": "X free tier: 500 posts/month (docs.x.com, 09/03/2026)",
    "instagram": "Instagram: 100 API posts per rolling 24 h, Instagram's own counter checked before each send "
                 "(developers.facebook.com, re-read 09/29/2026)",
    "youtube": "YouTube Data API: 100 uploads/day (developers.google.com, 09/03/2026)",
    "tiktok": "TikTok Direct Post: ~15 posts/day per creator (developers.tiktok.com, 09/03/2026)",
    "x_lecture": "X free tier: 100 reads/month (docs.x.com, 09/03/2026)",
}

# news_forms._CATALOGUE : nom et description par id
EN_FORMES = {
    "cartes": ("Animated cards (free)", "headlines as brand cards, rendered locally by ffmpeg; no provider"),
    "illustration_ia": ("AI illustration per headline", "one brand image generated per headline, animated as cards"),
    "plans_seedance": ("Video shots per story", "one shot generated per story, cut end to end"),
    "avatar": ("Presenter avatar", "the HeyGen avatar reads the script, composited with the cards"),
    "voix_sous_titres": ("Voice-over and subtitles",
                         "no avatar: ElevenLabs voice over the cards, subtitles aligned to the known text"),
}

# motifs et messages écrits dans le code : clé -> (fichier source, fr, en)
LITTERAUX = {
    "news.serveur.filtre.source_noire": ("news_filter.py", "source sur liste noire", "blacklisted source"),
    "news.serveur.filtre.mot_noir": ("news_filter.py", "mot sur liste noire", "blacklisted word"),
    "news.serveur.filtre.hors_mots_cles": ("news_filter.py", "hors mots-clés", "no keyword match"),
    "news.serveur.filtre.fraicheur": ("news_filter.py", "hors fenêtre de fraîcheur", "outside the freshness window"),
    "news.serveur.score.brief": ("news_rank.py", "brief : {mots}", "brief: {mots}"),
    "news.serveur.score.reprises": ("news_rank.py", "{reprises} média(s) sur le même sujet",
                                    "{reprises} outlet(s) on the same story"),
    "news.serveur.score.lisible": ("news_rank.py", "article lisible", "readable article"),
    "news.serveur.score.hors_brief": ("news_rank.py", "hors brief : moitié des points", "off-brief: half the points"),
    "news.serveur.score.socle": ("news_rank.py", "aucun signal, socle seulement", "no signal, base points only"),
    "news.serveur.score.malus": ("news_rank.py", "-{malus} source sur-représentée", "-{malus} over-represented source"),
    "news.serveur.tendances.jour": ("news_trends.py", "limite du jour atteinte : 3 lectures du signal X par jour",
                                    "daily limit reached: 3 X signal reads per day"),
    "news.serveur.tendances.cle": ("news_trends.py", "aucune clé X configurée (Réglages → Comptes connectés)",
                                   "no X key configured (Settings → Connected accounts)"),
    "news.serveur.tendances.quota": ("news_trends.py",
                                     "quota x_lecture : {deja}/{lim} ce mois, un appel peut lire {POSTS_PAR_APPEL} "
                                     "posts ({source})",
                                     "x_lecture quota: {deja}/{lim} this month, one call can read {POSTS_PAR_APPEL} "
                                     "posts ({source})"),
    "news.serveur.voix.defaut": ("news_voice.py", "aucun mot du sujet ne tranche, mode par défaut",
                                 "no topic word decides, default mode"),
    "news.serveur.voix.mots": ("news_voice.py", "mots du sujet : {mots}", "topic words: {mots}"),
    "news.serveur.voix.modele": ("news_voice.py", "choisi par le modèle", "picked by the model"),
    "news.serveur.chaine.polir_rien": ("../api/routes.py",
                                       "aucun fournisseur n'a répondu (clé absente ?) : le brouillon est gardé",
                                       "no provider answered (missing key?): the draft is kept"),
    "news.serveur.chaine.programme": ("../api/routes.py", "Post programmé ; le reel cartes se rend (file des rendus).",
                                      "Post scheduled; the cards reel is rendering (render queue)."),
    # aperçu final d'un post (post_preview.py) : gabarits posés par msg() dans le service lui-même
    "apercu.zones": ("post_preview.py", "{reseau} · zones indicatives · {n} car.",
                     "{reseau} · approximate safe zones · {n} chars"),
    "apercu.vide": ("post_preview.py", "Pas encore de visuel — Produisez-en un ou joignez-en un",
                    "No visual yet — Produce or attach one"),
    "apercu.vide_vertical": ("post_preview.py", "Aucun visuel — rendu 9:16 attendu", "No visual — 9:16 render expected"),
    "apercu.telegram": ("post_preview.py", "{n} car. · Telegram", "{n} chars · Telegram"),
}

# les gabarits d'aperçu ne sont PAS recopiés dans le service (il appelle msg(clé)) : on vérifie la clé, pas le texte
_PAR_CLE = {"post_preview.py"}


def _source_contient(fichier: str, fr: str, cle: str) -> bool:
    texte = (SERVICES / fichier).read_text("utf-8")
    if fichier in _PAR_CLE:
        return f'"{cle}"' in texte
    texte = re.sub(r'"\s*\n\s*(f?)"', "", texte)          # chaînes Python coupées sur deux lignes
    return all(m in texte for m in re.split(r"\{\w+\}", fr) if m.strip())


def attendu() -> bytes:
    from app.services import news_forms, quota
    lot = {}
    for ch, (_p, _n, src) in quota.LIMITS.items():
        if ch not in EN_QUOTA:
            raise SystemExit(f"quota.LIMITS[{ch!r}] sans anglais dans EN_QUOTA")
        lot[f"quota.source.{ch}"] = {"fr": src, "en": EN_QUOTA[ch]}
    for f in news_forms.catalogue():
        if f["id"] not in EN_FORMES:
            raise SystemExit(f"forme {f['id']!r} sans anglais dans EN_FORMES")
        nom, desc = EN_FORMES[f["id"]]
        lot[f"news.serveur.forme.{f['id']}.nom"] = {"fr": f["label"], "en": nom}
        lot[f"news.serveur.forme.{f['id']}.description"] = {"fr": f["description"], "en": desc}
    for cle, (fichier, fr, en) in LITTERAUX.items():
        if not _source_contient(fichier, fr, cle):
            raise SystemExit(f"{cle} : « {fr} » introuvable dans {fichier} — le service a changé, mettre la clé à jour")
        if set(re.findall(r"\{\w+\}", fr)) != set(re.findall(r"\{\w+\}", en)):
            raise SystemExit(f"{cle} : variables différentes entre fr et en")
        lot[cle] = {"fr": fr, "en": en}
    actuel = json.loads(MESSAGES.read_bytes().decode("utf-8"))
    autres = [(k, v) for k, v in actuel.items() if not k.startswith(PREFIXES)]
    k4 = next((i for i, (k, _v) in enumerate(autres) if k.startswith(PREFIXES_L4)), len(autres))
    neuf = autres[:k4] + sorted(lot.items()) + autres[k4:]
    return ("{\n" + ",\n".join(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
                               for k, v in neuf) + "\n}\n").encode("utf-8")


def main(args):
    b = attendu()
    if "--check" in args:
        ok = MESSAGES.read_bytes().replace(b"\r\n", b"\n") == b
        print("à jour" if ok else "PÉRIMÉ : python scripts/i18n_planif_news_serveur.py (python embarqué)")
        return 0 if ok else 1
    MESSAGES.write_bytes(b)
    print(f"messages.json écrit ({b.count(b'\n') - 1} clés)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
