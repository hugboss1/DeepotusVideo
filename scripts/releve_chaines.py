# Copie VENDUE du script du skill « traduction-deepotus » (~/.claude/skills/traduction-deepotus/scripts/releve_chaines.py),
# relevée le 08/10/2026 (t137, Photolab P2 C4) : le banc backend/tests/test_photolab_textes.py ne dépend ainsi
# d'aucun fichier hors du dépôt. Toute évolution du script du skill se recopie ici.
"""Relevé des chaînes visibles d'un ou plusieurs fichiers DeepotusVideo (JS compilé ou couche, HTML, Python).

Usage :
  python releve_chaines.py <fichier|dossier>… [--json sortie.json] [--fr-seulement] [--hors-dico dico.json…]

Sort une ligne par chaîne candidate : fichier:ligne, genre (children, title, label, placeholder, aria-label,
html, http), langue devinée (fr / en / ?) et le texte. C'est une ESTIMATION par expressions régulières :
les textes composés à l'exécution ("Plan "+i) n'apparaissent qu'en morceaux, et il reste des faux positifs
(noms propres, formats). --hors-dico ne garde que les chaînes absentes des dictionnaires donnés (champ fr),
ce qui sert de critère d'arrêt d'un lot : plus rien de français hors dictionnaire.
"""
import json, pathlib, re, sys

sys.stdout.reconfigure(encoding="utf-8")
EXT = {".js", ".mjs", ".html", ".htm", ".py"}
CHAINE = r'"((?:[^"\\\n]|\\.){2,300})"'
MOTIFS = [
    ("children", re.compile(r'children:\s*' + CHAINE)),
    ("title", re.compile(r'\btitle:\s*' + CHAINE)),
    ("label", re.compile(r'\blabel:\s*' + CHAINE)),
    ("placeholder", re.compile(r'placeholder:\s*' + CHAINE)),
    ("aria-label", re.compile(r'"aria-label":\s*' + CHAINE)),
    ("desc", re.compile(r'\bdesc:\s*' + CHAINE)),
    ("http", re.compile(r'HTTPException\(\s*\d{3}\s*,\s*f?' + CHAINE)),
    ("attr-html", re.compile(r'\b(?:title|placeholder|aria-label)="([^"<>]{2,200})"')),
    ("html", re.compile(r'>([^<>{}\n]{2,200})<')),
    # tout le reste : une chaîne qui ressemble à une phrase (une espace, une lettre) — ternaires, concaténations
    ("texte", re.compile(CHAINE)),
]
COMMENTAIRE = re.compile(r"^\s*(//|/\*|\*|#)")
MOTS_FR = re.compile(r"\b(le|la|les|des|du|une|un|et|ou|pour|avec|sans|dans|sur|est|pas|ce|cette|vos|votre|aucun|aucune|"
                     r"choisir|ajouter|enregistrer|annuler|supprimer|fermer|ouvrir|exporter|générer|voix|image|calque)\b", re.I)
MOTS_EN = re.compile(r"\b(the|and|or|for|with|without|your|you|no|not|add|save|cancel|delete|close|open|export|generate|"
                     r"select|choose|is|are|of|to)\b", re.I)


def langue(t):
    if re.search(r"[àâçéèêëîïôûùüÿœæ«»’]", t, re.I) or len(MOTS_FR.findall(t)) > len(MOTS_EN.findall(t)):
        return "fr"
    if MOTS_EN.search(t):
        return "en"
    return "?"


def visible(t):
    t = t.strip()
    if len(t) < 2 or not re.search(r"[A-Za-zÀ-ÿ]{2}", t):
        return False
    if re.fullmatch(r"[\w.\-/:#%]+", t) and not re.search(r"[A-ZÀ-Ý]", t[:1]):
        return False                      # identifiant, classe, chemin, unité
    if re.fullmatch(r"(var\(|#[0-9a-f]{3,8}|\d)", t[:4], re.I):
        return False
    return True


def fichiers(args):
    for a in args:
        p = pathlib.Path(a)
        if p.is_dir():
            for q in sorted(p.rglob("*")):
                if q.suffix in EXT and "vendor" not in q.parts and "node_modules" not in q.parts:
                    yield q
        elif p.is_file():
            yield p


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    sortie = fr_seul = None
    dicos, cibles, i = [], [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--json":
            sortie = argv[i + 1]; i += 2; continue
        if a == "--fr-seulement":
            fr_seul = True; i += 1; continue
        if a == "--hors-dico":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                dicos.append(argv[i]); i += 1
            continue
        cibles.append(a); i += 1
    connus = set()
    for d in dicos:
        for v in json.loads(pathlib.Path(d).read_text("utf-8")).values():
            if isinstance(v, dict) and v.get("fr"):
                connus.add(v["fr"].strip())
    vus, lignes = set(), []
    for f in fichiers(cibles):
        texte = f.read_bytes().decode("utf-8", "replace")
        for n, ligne in enumerate(texte.splitlines(), 1):
            if COMMENTAIRE.match(ligne):
                continue
            for genre, rx in MOTIFS:
                if genre == "html" and f.suffix not in (".html", ".htm"):
                    continue
                for m in rx.finditer(ligne):
                    t = m.group(1).strip()
                    if not visible(t) or (str(f), t) in vus or t in connus:
                        continue
                    if genre == "texte" and (" " not in t or f.suffix == ".py" and "HTTPException" not in ligne):
                        continue                  # un mot seul ou une chaîne Python ordinaire : rarement affiché
                    lg = langue(t)
                    if fr_seul and lg != "fr":
                        continue
                    vus.add((str(f), t))
                    lignes.append({"fichier": str(f), "ligne": n, "genre": genre, "langue": lg, "texte": t})
    for l in lignes:
        print(f'{l["fichier"]}:{l["ligne"]}\t{l["genre"]}\t{l["langue"]}\t{l["texte"][:120]}')
    par = {}
    for l in lignes:
        par[l["langue"]] = par.get(l["langue"], 0) + 1
    print(f"\n{len(lignes)} chaînes — " + ", ".join(f"{k}: {v}" for k, v in sorted(par.items())), file=sys.stderr)
    if sortie:
        pathlib.Path(sortie).write_text(json.dumps(lignes, ensure_ascii=False, indent=1), "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
