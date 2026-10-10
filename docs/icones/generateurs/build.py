"""Assemble les JSON de zone en un inventaire unique + exports.

Usage : python -I build.py <dossier_inv> <racine_depot> <dossier_sortie>
"""
import base64, csv, html, io, json, re, sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

INV, ROOT, OUT = (Path(a) for a in sys.argv[1:4])
KIT = Path(sys.argv[4]) if len(sys.argv) > 4 else None   # dossier des dz-*.svg
RES = Path(sys.argv[5]) if len(sys.argv) > 5 else None   # dossier des resN.json
REF = Path(sys.argv[6]) if len(sys.argv) > 6 else None   # dossier de la refonte (lexique, affectation, svg/)
OUT.mkdir(parents=True, exist_ok=True)

ORDRE_ZONES = ["Coque", "Marque", "Partagé", "Accueil", "Quick", "Studio", "Templates", "News", "Scheduler",
               "Épisodes", "Chapitres", "Montage", "Son & VFX", "Bibliothèque", "Réglages",
               "Game Assets", "Card Forge", "Vectorlab", "Photolab", "Spritelab", "Tilelab",
               "Établi", "Matières", "Studio 3D", "Plateau 3D", "Atelier", "Mobile"]
RENOMME = {"Chapitres (Épisodes)": "Chapitres", "Accueil (onboarding)": "Accueil", "Identité / marque": "Marque"}

entrees = []
for f in sorted(INV.glob("*.json")):
    data = json.loads(f.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("entrees") or data.get("items") or next(v for v in data.values() if isinstance(v, list))
    for e in data:
        e["_lot"] = f.stem
        entrees.append(e)

def s(e, k):
    v = e.get(k, "")
    if isinstance(v, (list, dict)):
        v = json.dumps(v, ensure_ascii=False)
    return "" if v is None else str(v)

# ---- normalisation
vus = Counter()
for e in entrees:
    for k in ("id", "zone", "ecran", "emplacement", "libelle", "fonction", "role", "type",
              "cle_visuelle", "rendu", "style", "source", "notes"):
        e[k] = s(e, k).strip()
    e["zone"] = RENOMME.get(e["zone"], e["zone"])
    e["type"] = e["type"].lower() or "aucune"
    e["role"] = e["role"].lower() or "action"
    if not e["cle_visuelle"]:
        e["cle_visuelle"] = (e["type"] + "-" + e["rendu"][:12]) if e["type"] in ("emoji", "glyphe") else e["id"]
    vus[e["id"]] += 1
    if vus[e["id"]] > 1:
        e["id"] = f'{e["id"]}~{vus[e["id"]]}'

def svg_ok(t):
    t = t.strip()
    if not t.startswith("<svg"):
        return None
    if "xmlns" not in t[:200]:
        t = t.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S | re.I)
    t = re.sub(r"\son\w+=\"[^\"]*\"", "", t)
    return t

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".ico": "image/x-icon",
        ".svg": "image/svg+xml", ".webp": "image/webp", ".gif": "image/gif"}
_cache = {}
def image_uri(chemin):
    if chemin in _cache:
        return _cache[chemin]
    p = (ROOT / chemin.split(":")[0].lstrip("/\\")).resolve()
    uri = None
    if p.is_file() and p.suffix.lower() in MIME:
        b = p.read_bytes()
        if p.suffix.lower() == ".svg":
            uri = ("svg", svg_ok(b.decode("utf-8", "replace")))
        elif len(b) < 400_000:
            uri = ("img", f"data:{MIME[p.suffix.lower()]};base64," + base64.b64encode(b).decode())
        else:
            try:
                from PIL import Image
                im = Image.open(p); im.thumbnail((256, 256)); bio = io.BytesIO(); im.convert("RGB").save(bio, "JPEG", quality=80)
                uri = ("img", "data:image/jpeg;base64," + base64.b64encode(bio.getvalue()).decode())
            except Exception:
                uri = None
    _cache[chemin] = uri
    return uri

for e in entrees:
    r = e["rendu"]
    e["_html"] = ""
    if e["type"] == "svg" or r.startswith("<svg"):
        v = svg_ok(r)
        if v:
            e["_html"] = v
        elif r.startswith("carte:"):
            e["_ref"] = r.split(":", 1)[1].strip()
    elif e["type"] == "image" or re.search(r"\.(png|jpe?g|ico|svg|webp|gif)$", r, re.I):
        u = image_uri(r)
        if u and u[0] == "svg" and u[1]:
            e["_html"] = u[1]
        elif u:
            e["_html"] = f'<img src="{u[1]}" alt="">'
    elif e["type"] in ("emoji", "glyphe", "police") and r:
        e["_html"] = f'<span class="g">{html.escape(r)}</span>'

# résolution des renvois « carte:<nom> » vers un SVG connu de même clé
par_cle = {}
for e in entrees:
    if e["_html"].startswith("<svg"):
        par_cle.setdefault(e["cle_visuelle"], e["_html"])
for e in entrees:
    if not e["_html"] and e.get("_ref"):
        e["_html"] = par_cle.get(e["_ref"]) or par_cle.get(e["cle_visuelle"], "")

# unification des clés : même glyphe ou même SVG = même dessin, quel que soit le lot
def empreinte(e):
    if e["type"] in ("emoji", "glyphe") and 0 < len(e["rendu"]) <= 4:
        return "g:" + e["rendu"]
    if e["_html"].startswith("<svg"):
        return "s:" + re.sub(r"\s+", " ", re.sub(r'\s(aria-hidden|class|width|height)="[^"]*"', "", e["_html"])).strip()
    return None
canon = {}
for e in entrees:
    k = empreinte(e)
    if not k:
        continue
    if k.startswith("g:"):
        canon.setdefault(k, ("glyphe " if e["type"] == "glyphe" else "emoji ") + e["rendu"])
    else:
        canon.setdefault(k, e["cle_visuelle"])
    e["cle_visuelle"] = canon[k]

def rang_zone(z):
    for i, nom in enumerate(ORDRE_ZONES):
        if z.lower().startswith(nom.lower()):
            return i
    return 99
entrees.sort(key=lambda e: (rang_zone(e["zone"]), e["zone"], e["ecran"], e["id"]))

# ---- concepts visuels (dessins distincts)
concepts = OrderedDict()
for e in entrees:
    c = concepts.setdefault(e["cle_visuelle"], {"cle": e["cle_visuelle"], "type": e["type"], "html": "",
                                                "usages": 0, "zones": [], "fonctions": [], "roles": Counter(), "rendu": ""})
    c["usages"] += 1
    if e["_html"] and not c["html"]:
        c["html"], c["rendu"] = e["_html"], e["rendu"]
    if e["zone"] not in c["zones"]:
        c["zones"].append(e["zone"])
    f = e["libelle"] or e["fonction"][:60]
    if f and f not in c["fonctions"] and len(c["fonctions"]) < 6:
        c["fonctions"].append(f)
    c["roles"][e["role"]] += 1
for c in concepts.values():
    c["roles"] = [r for r, _ in c["roles"].most_common()]
    c["polysemie"] = len(set(x.lower() for x in c["fonctions"])) >= 4

# fonctions servies par plusieurs dessins
def norm(t):
    return re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿœ]+", " ", t.lower()).strip()
fonc_dessins = defaultdict(set)
for e in entrees:
    if e["type"] == "aucune":
        continue
    k = norm(e["libelle"])
    if 2 < len(k) < 40:
        fonc_dessins[k].add(e["cle_visuelle"])
synonymes = sorted(((k, sorted(v)) for k, v in fonc_dessins.items() if len(v) >= 2), key=lambda x: -len(x[1]))

stats = {
    "entrees": len(entrees),
    "concepts": len(concepts),
    "zones": len({e["zone"] for e in entrees}),
    "types": Counter(e["type"] for e in entrees),
    "roles": Counter(e["role"] for e in entrees),
    "sans_icone": sum(1 for e in entrees if e["type"] == "aucune"),
}

# ---- nouvelle suite (kit) et affectations
kit, kit_sens = OrderedDict(), {}
aff = {}
if KIT:
    doc = (KIT / "DOCUMENT-IMPLEMENTATION.md").read_text(encoding="utf-8")
    for c, sens, pl in re.findall(r"\| `(dz-[a-z0-9-]+)` \| ([^|]+) \| ([^|]+) \|", doc):
        kit_sens[c] = (sens.strip(), pl.strip())
    for c in json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))["icons"]:
        kit[c] = svg_ok((KIT / f"{c}.svg").read_text(encoding="utf-8"))
if RES:
    for f in sorted(RES.glob("res*.json")):
        aff.update(json.loads(f.read_text(encoding="utf-8")))
# harmonisation des noms proposés par les quatre lots (même sens, même nom)
ALIAS = {"action-lier": "edit-lier", "edit-modifier": "action-modifier", "action-editer": "action-modifier",
         "edit-renommer": "action-renommer", "action-zoom-plus": "action-zoom-avant", "edit-zoom-avant": "action-zoom-avant",
         "action-zoom-moins": "action-zoom-arriere", "edit-zoom-arriere": "action-zoom-arriere", "edit-zoom": "action-zoom",
         "outil-photo-main": "edit-main", "etat-duree": "media-duree", "action-emoji": "media-emoji",
         "outil-vec-halo": "edit-halo", "cat-bible": "nav-bible", "nav-material-forge": "nav-matieres",
         "media-relief": "lab3d-relief", "action-confirmer": "action-valider", "action-lien-externe": "action-ouvrir-externe"}
for v in aff.values():
    m = (v.get("manque") or "")[3:]
    if m in ALIAS:
        v["manque"] = "dz-" + ALIAS[m]
inconnues = set()
for e in entrees:
    a = aff.get(e["id"].split("~")[0] if e["id"] not in aff else e["id"], {})
    cible = a.get("cible") or ""
    if cible and cible not in kit:
        inconnues.add(cible); a = dict(a, manque=a.get("manque") or cible); cible = ""
    e["nouvelle_cle"], e["confiance"] = cible, (a.get("confiance") or "") if cible else ""
    e["manque"] = "" if cible else (a.get("manque") or "")
    e["note_affectation"] = a.get("note") or ""
    e["_nh"] = kit.get(cible, "")
    e["statut"] = ("sure" if e["confiance"] == "sure" else "probable") if cible else ("manque" if e["manque"] else ("sans" if aff else ""))
# doublons de dessin dans le kit
par_trace = defaultdict(list)
for c, h in kit.items():
    par_trace[re.sub(r"\s+", "", h)].append(c)
kit_doublons = [v for v in par_trace.values() if len(v) > 1]
suite = []
for c, h in kit.items():
    U = [e for e in entrees if e["nouvelle_cle"] == c]
    suite.append({"cle": c, "h": h, "sens": kit_sens.get(c, ("", ""))[0], "planche": kit_sens.get(c, ("", "—"))[1],
                  "usages": len(U), "zones": sorted({e["zone"] for e in U}, key=rang_zone),
                  "libelles": list(OrderedDict.fromkeys(e["libelle"] or e["fonction"][:50] for e in U))[:8],
                  "anciens": list(OrderedDict.fromkeys(e["cle_visuelle"] for e in U))[:10]})
manques = defaultdict(lambda: {"usages": 0, "zones": [], "libelles": []})
for e in entrees:
    if e["manque"]:
        m = manques[e["manque"]]; m["usages"] += 1
        if e["zone"] not in m["zones"]: m["zones"].append(e["zone"])
        l = e["libelle"] or e["fonction"][:50]
        if l and l not in m["libelles"] and len(m["libelles"]) < 8: m["libelles"].append(l)
manques = sorted(({"cle": k} | v for k, v in manques.items()), key=lambda x: -x["usages"])
stats["kit"] = len(kit)
stats["affectees"] = sum(1 for e in entrees if e["nouvelle_cle"])
stats["manques_usages"] = sum(1 for e in entrees if e["manque"])
stats["manques_cles"] = len(manques)
stats["kit_inutilisees"] = sum(1 for x in suite if not x["usages"])

# ---- refonte : suite finale « Deepotus Glyph »
finale, retirees = [], []
if REF:
    lex = json.loads((REF / "lexique.json").read_text(encoding="utf-8"))
    aff2 = json.loads((REF / "affectation_finale.json").read_text(encoding="utf-8"))
    retirees = json.loads((REF / "retirees.json").read_text(encoding="utf-8"))
    svgs = {}
    for x in lex:
        f = REF / "svg" / f'{x["cle"]}.svg'
        svgs[x["cle"]] = svg_ok(f.read_text(encoding="utf-8")) if f.exists() else ""
    for e in entrees:
        a = aff2.get(e["id"], {})
        e["cle_finale"] = a.get("cle") or ""
        e["emoji_conserve"] = bool(a.get("emoji_conserve"))
        e["raison_finale"] = a.get("raison") or ""
        e["_fh"] = svgs.get(e["cle_finale"], "")
        e["statut_final"] = "icone" if e["cle_finale"] else ("emoji" if e["emoji_conserve"] else "texte")
    for x in lex:
        U = [e for e in entrees if e["cle_finale"] == x["cle"]]
        finale.append({"cle": x["cle"], "famille": x["famille"], "sens": x["sens"], "h": svgs.get(x["cle"], ""),
                       "origine": x.get("origine", ""), "mobile": bool(x.get("mobile")) or any(e["zone"] == "Mobile" for e in U),
                       "usages": len(U), "zones": sorted({e["zone"] for e in U}, key=rang_zone),
                       "libelles": list(OrderedDict.fromkeys(e["libelle"] or e["fonction"][:50] for e in U))[:6],
                       "anciens": list(OrderedDict.fromkeys(e["cle_visuelle"] for e in U))[:10],
                       "ncf": [[c["cle"], c.get("difference", "")] for c in x.get("ne_pas_confondre_avec", [])][:4],
                       "dessin": x.get("dessin", {}), "source_logo": x.get("source_logo", "")})
    # options proposées par fonction : icônes du kit qui portent ce sens (renommage + retraits fusionnés)
    ren = json.loads((REF / "renommage.json").read_text(encoding="utf-8"))
    for r in retirees:
        if r.get("remplacee_par"): ren.setdefault(r["cle"], r["remplacee_par"])
    kit_pour = defaultdict(list)
    for ancien, final in ren.items():
        if final and ancien in kit and ancien not in kit_pour[final]:
            kit_pour[final].append(ancien)
    for x in finale:
        x["kit"] = kit_pour.get(x["cle"], [])
    stats["finale"] = len(finale)
    stats["finale_dessinees"] = sum(1 for x in finale if x["h"])
    stats["finale_mobile"] = sum(1 for x in finale if x["mobile"])
    stats["emojis_conserves"] = sum(1 for e in entrees if e["emoji_conserve"])
    stats["texte_seul"] = sum(1 for e in entrees if e["statut_final"] == "texte")
else:
    for e in entrees:
        e["cle_finale"], e["emoji_conserve"], e["raison_finale"], e["_fh"], e["statut_final"] = "", False, "", "", ""
if inconnues: print("cibles hors kit converties en manque:", sorted(inconnues))

# ---- exports machine
champs = ["id", "zone", "ecran", "emplacement", "libelle", "fonction", "role", "type",
          "cle_visuelle", "cle_finale", "emoji_conserve", "raison_finale", "nouvelle_cle", "confiance", "manque", "note_affectation", "style", "source", "notes", "rendu"]
propre = [{k: (e["_html"] if k == "rendu" and e["_html"].startswith("<svg") else e[k]) for k in champs} for e in entrees]
(OUT / "inventaire-icones.json").write_text(json.dumps(propre, ensure_ascii=False, indent=1), encoding="utf-8")
with open(OUT / "inventaire-icones.csv", "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=champs, delimiter=";")
    w.writeheader(); w.writerows(propre)
liste_concepts = [{"cle": c["cle"], "type": c["type"], "usages": c["usages"], "zones": c["zones"],
                   "roles": c["roles"], "exemples_fonction": c["fonctions"], "rendu_actuel": c["rendu"]}
                  for c in concepts.values()]
(OUT / "concepts-a-dessiner.json").write_text(json.dumps(liste_concepts, ensure_ascii=False, indent=1), encoding="utf-8")
svgdir = OUT / "svg-actuels"; svgdir.mkdir(exist_ok=True)
for c in concepts.values():
    if c["html"].startswith("<svg"):
        nom = re.sub(r"[^A-Za-z0-9_.-]+", "_", c["cle"])[:80] or "sans_nom"
        (svgdir / f"{nom}.svg").write_text(c["html"], encoding="utf-8")

if kit:
    (OUT / "affectation-nouvelle-suite.json").write_text(json.dumps(
        {"suite": [{k: v for k, v in x.items() if k != "h"} for x in suite], "a_ajouter": manques,
         "doublons_dans_le_kit": kit_doublons,
         "usages": [{k: e[k] for k in ("id", "zone", "ecran", "libelle", "source", "cle_visuelle", "nouvelle_cle", "confiance", "manque")} for e in entrees]},
        ensure_ascii=False, indent=1), encoding="utf-8")
if finale:
    fin = OUT / "suite-finale"; (fin / "svg").mkdir(parents=True, exist_ok=True)
    for x in finale:
        if x["h"]:
            (fin / "svg" / f'{x["cle"]}.svg').write_text(x["h"], encoding="utf-8")
    def corps(h):
        return re.sub(r"^<svg[^>]*>|</svg>$", "", h)
    def attrs_svg(h):
        m = re.match(r"<svg([^>]*)>", h); return m.group(1) if m else ""
    sym = "".join(f'<symbol id="{x["cle"]}" viewBox="0 0 24 24" fill="currentColor">{corps(x["h"])}</symbol>' for x in finale if x["h"])
    (fin / "dz-icons.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" style="display:none">{sym}</svg>', encoding="utf-8")
    carte = {x["cle"]: x["h"] for x in finale if x["h"]}
    (fin / "dz-icons.js").write_text("/* Deepotus Glyph : clé -> SVG autonome (currentColor). Généré par docs/icones/generateurs/build.py */\n"
        "window.DZ_ICONS = " + json.dumps(carte, ensure_ascii=False) + ";\n", encoding="utf-8")
    mob = {x["cle"]: x["h"] for x in finale if x["h"] and x["mobile"]}
    (fin / "dz-icons.mobile.ts").write_text("// Deepotus Glyph pour le compagnon mobile (react-native-svg : <SvgXml xml={DZ_ICONS[cle]} color={couleur} width={24} height={24} />)\n"
        "export const DZ_ICONS: Record<string, string> = " + json.dumps(mob, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    (fin / "LOGOS-TIERS.md").write_text("""# Logos tiers de la suite (famille `reseau`)

Tracés repris tels quels de **simple-icons 16.34.0** (paquet npm `simple-icons`, licence CC0-1.0), ramenés de 24 à 20 unités (`matrix(.8333 0 0 .8333 2 2)`) pour tenir dans la zone utile, couleur `currentColor`. Le dessin n'est pas modifié.

La licence CC0 couvre le fichier, pas la marque : chaque logo reste la marque de son propriétaire. L'emploi dans l'application (désigner le réseau de destination d'un post) doit suivre la charte de la marque.

| Clé | Marque | Charte |
|---|---|---|
| dz-reseau-youtube | YouTube | https://www.youtube.com/howyoutubeworks/resources/brand-resources/#logos-icons-and-colors |
| dz-reseau-instagram | Instagram | https://about.meta.com/brand/resources/instagram |
| dz-reseau-tiktok | TikTok | (pas de charte référencée par simple-icons) |
| dz-reseau-x | X | https://about.x.com/en/who-we-are/brand-toolkit |
| dz-reseau-telegram | Telegram | (pas de charte référencée par simple-icons) |
| dz-reseau-figma | Figma | https://www.figma.com/using-the-figma-brand/ |
""", encoding="utf-8")
    (fin / "lexique.json").write_text(json.dumps([{k: v for k, v in x.items() if k != "h"} for x in finale], ensure_ascii=False, indent=1), encoding="utf-8")
    (fin / "implementation.json").write_text(json.dumps([{k: e[k] for k in ("id", "zone", "ecran", "emplacement", "libelle", "source", "cle_visuelle", "cle_finale", "emoji_conserve", "raison_finale")} for e in entrees], ensure_ascii=False, indent=1), encoding="utf-8")
json.dump({"stats": {k: (dict(v) if isinstance(v, Counter) else v) for k, v in stats.items()},
           "synonymes": synonymes[:80]}, open(OUT / "_stats.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- page HTML
payload = {
    "entrees": [{k: e[k] for k in champs if k != "rendu"} | {"h": e["_html"], "nh": e["_nh"], "statut": e["statut"], "fh": e["_fh"], "sf": e["statut_final"]} for e in entrees],
    "suite": suite, "manques": manques, "kit_doublons": kit_doublons,
    "finale": finale, "retirees": retirees,
    "concepts": [{"cle": c["cle"], "type": c["type"], "usages": c["usages"], "zones": c["zones"],
                  "roles": c["roles"], "fonctions": c["fonctions"], "h": c["html"], "poly": c["polysemie"]}
                 for c in concepts.values()],
    "synonymes": synonymes[:60],
    "stats": {k: (dict(v) if isinstance(v, Counter) else v) for k, v in stats.items()},
}
tpl = (INV / "page.html").read_text(encoding="utf-8")
cahier = INV / "cahier.html"
txt_cahier = cahier.read_text(encoding="utf-8") if cahier.exists() else ""
if REF and (INV / "cahier_refonte.html").exists():
    txt_cahier = ((INV / "cahier_refonte.html").read_text(encoding="utf-8")
                  + '<h2 style="color:var(--low)">Historique : relevé initial et kit reçu</h2><p>Les sections suivantes datent des étapes précédentes. Elles restent pour mémoire ; la refonte ci-dessus les remplace.</p>'
                  + txt_cahier)
tpl = tpl.replace("__CAHIER__", txt_cahier)
data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
(OUT / "inventaire-icones.html").write_text(tpl.replace("/*__DATA__*/null", data), encoding="utf-8")
print(json.dumps(payload["stats"], ensure_ascii=False))
print("synonymes:", len(synonymes), "concepts:", len(concepts))
