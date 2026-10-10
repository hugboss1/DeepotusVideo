"""Traduction L7 (t147) : le Card Forge (frontend/cardforge/) — de la saisie (scripts/i18n_l7/*.py, format dans
scripts/i18n_l7/outils.py) aux sources des modules, au dictionnaire frontend/shared/i18n/cartes.json et à la table
réversible scripts/i18n_l7_paires.json. Repris du générateur L6 (Vectorlab).

  python scripts/i18n_l7_generer.py              écrit les modules traduits, la table, le dictionnaire, puis réassemble
  python scripts/i18n_l7_generer.py --check      code 1 si l'un de ces fichiers n'est pas à jour
  python scripts/i18n_l7_generer.py --seul G     valide le seul groupe G (rien n'est écrit) et liste ses RESTES
  python scripts/i18n_l7_generer.py --restes     les restes de TOUS les fichiers du Card Forge

Les modules du Card Forge sont des scripts CLASSIQUES (pas d'import) chargés APRÈS /shared/dz-i18n.js : un texte
affiché devient dzT("cartes.<zone>.<role>") (fonction globale du runtime). index.html n'est pas modifié : ses textes
sont traduits à l'affichage par la surcouche, d'après les entrées H. La table garde chaque édition (fichier, pos,
avant, apres) : les bancs lisent la source d'avant L7 sans git (backend/tests/_i18n_l1_aide.source_avant_i18n_l7).
"""
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BASE = "f788790b"
LAB = "frontend/cardforge/"
SAISIE = RACINE / "scripts" / "i18n_l7"
PAIRES = RACINE / "scripts" / "i18n_l7_paires.json"
ZONE = "cartes"
DICO_F = RACINE / "frontend" / "shared" / "i18n" / "cartes.json"
SEUL = None


def base(fichier: str) -> str:
    rel = LAB + fichier
    b = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=str(RACINE), capture_output=True, check=True).stdout
    return b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n").decode("utf-8")


def fichiers_lab():
    out = ["index.html"]
    r = subprocess.run(["git", "ls-tree", "--name-only", f"{BASE}", LAB + "js/"], cwd=str(RACINE),
                       capture_output=True, text=True, check=True).stdout.split()
    out += sorted(p[len(LAB):] for p in r if p.endswith(".js"))
    return out


def entrees():
    out = []
    sys.path.insert(0, str(SAISIE))
    for f in sorted(SAISIE.glob("*.py")):
        if f.name == "outils.py":
            continue
        spec = importlib.util.spec_from_file_location(f"saisie7_{f.stem}", f)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
            lst = m.ENTREES
        except Exception as x:                       # noqa: BLE001
            if SEUL and f.stem != SEUL:              # --seul : un AUTRE groupe en cours d'écriture ne bloque pas
                print(f"  (groupe {f.stem} ignoré : {type(x).__name__}: {x})")
                continue
            raise
        # PLAGES = {fichier: (première ligne, dernière ligne)} : un gros module partagé entre plusieurs groupes — chaque
        # entrée doit COMMENCER dans la plage de son groupe, et --seul ne liste que les restes de la plage
        plages = getattr(m, "PLAGES", {})
        PLAGES_GROUPES[f.stem] = plages
        for e in lst:
            e["groupe"] = f.stem
            if e["type"] != "H" and e["fichier"] in plages:
                a, z = plages[e["fichier"]]
                if not (a <= e["ligne"] <= z):
                    raise SystemExit(f"[l7] {f.stem} : {e['fichier']}:{e['ligne']} hors de la plage du groupe ({a}-{z})")
            out.append(e)
    return out


PLAGES_GROUPES = {}


def dans_plage(reste: str, plages: dict) -> bool:
    m = re.match(r"([^:]+):(\d+):", reste)
    if not m or m.group(1) not in plages:
        return True
    a, z = plages[m.group(1)]
    return a <= int(m.group(2)) <= z


def debut_ligne(s: str, ligne: int) -> tuple:
    i = 0
    for _ in range(ligne - 1):
        i = s.index("\n", i) + 1
    j = s.find("\n", i)
    return i, (len(s) if j < 0 else j)


def _ident(c):
    return c.isalnum() or c in "_$"


def _unquote(lit: str):
    """Contenu d'un littéral simple ("…", '…', `…` sans ${}) ; None si ce n'en est pas un."""
    if len(lit) < 2 or lit[0] != lit[-1] or lit[0] not in "\"'`" or (lit[0] == "`" and "${" in lit):
        return None
    body = lit[1:-1]
    try:
        return json.loads('"' + body.replace('"', '\\"').replace("\\'", "'").replace("\\`", "`")
                          .replace('\\\\"', '\\"') + '"') if "\\" in body else body
    except Exception:                               # noqa: BLE001
        return None


def resoudre(E, textes):
    """-> (subs {fichier: [(pos, avant, apres, groupe)]}, dico {cle: (fr, en, ctx)}, gardes[])."""
    subs, dico, gardes = {}, {}, []
    erreurs = []
    for e in E:
        for cle, v in e.get("dico", {}).items():
            fr, en, ctx = v[0], v[1], len(v) > 2 and v[2] == "contexte"
            if not re.fullmatch(r"cartes(\.[a-z0-9_]+){2,}", cle):
                erreurs.append(f"{e['groupe']} : clé {cle!r} hors format cartes.<zone>.<role> (ascii minuscule)")
            if not fr or not en:
                erreurs.append(f"{e['groupe']} : {cle} : fr ou en vide")
            if set(re.findall(r"\{(\w+)\}", fr)) != set(re.findall(r"\{(\w+)\}", en)):
                erreurs.append(f"{e['groupe']} : {cle} : variables différentes en fr et en")
            if cle in dico and dico[cle] != (fr, en, ctx):
                erreurs.append(f"{e['groupe']} : {cle} : deux textes différents ({dico[cle]} / {(fr, en, ctx)})")
            dico[cle] = (fr, en, ctx)
        if e["type"] == "H":
            continue
        f = e["fichier"]
        if f not in textes:
            erreurs.append(f"{e['groupe']} : fichier inconnu {f!r}")
            continue
        s = textes[f]
        try:
            i, j = debut_ligne(s, e["ligne"])
        except ValueError:
            erreurs.append(f"{e['groupe']} : {f}:{e['ligne']} : ligne hors du fichier")
            continue
        av = e["avant"]
        if not av:                                   # un ancrage vide ne s'avance jamais (boucle sans fin)
            erreurs.append(f"{e['groupe']} : {f}:{e['ligne']} : « avant » vide — ancrer sur un texte de la ligne")
            continue
        pos, k = [], i
        while True:
            p = s.find(av, k)
            if p < 0 or p > j:
                break
            pos.append(p)
            k = p + len(av)
        if len(pos) != e["n"]:
            erreurs.append(f"{e['groupe']} : {f}:{e['ligne']} : {av[:70]!r} trouvé {len(pos)} fois sur la ligne "
                           f"(attendu n={e['n']}) — ligne : {s[i:j].strip()[:140]!r}")
            continue
        if e["type"] == "X":
            gardes.append({"fichier": f, "ligne": e["ligne"], "texte": av, "raison": e["raison"],
                           "groupe": e["groupe"], "pos": pos})
            continue
        if e["type"] == "L":
            u = _unquote(av)
            fr = e["dico"][e["cle"]][0]
            if u is None:
                erreurs.append(f"{e['groupe']} : {f}:{e['ligne']} : L sur {av[:60]!r} qui n'est pas un littéral simple "
                               "(gabarit à ${} ou guillemets manquants : utiliser S)")
                continue
            if u != fr:
                erreurs.append(f"{e['groupe']} : {f}:{e['ligne']} : fr de {e['cle']} ({fr!r}) ≠ littéral ({u!r})")
                continue
        for p in pos:
            apres = e["apres"]
            if p > 0 and _ident(s[p - 1]) and apres and _ident(apres[0]):
                apres = " " + apres
            subs.setdefault(f, []).append((p, av, apres, e["groupe"]))
    # chevauchements
    for f, lst in subs.items():
        lst.sort(key=lambda x: x[0])
        for a, b in zip(lst, lst[1:]):
            if a[0] + len(a[1]) > b[0]:
                erreurs.append(f"chevauchement {f} : {a[3]} {a[1][:40]!r} et {b[3]} {b[1][:40]!r}")
    # clés utilisées par un S : chaque T("clé") écrit doit être au dico
    for e in E:
        if e["type"] == "S":
            for cle in re.findall(r'\bdzT\("([^"]+)"', e["apres"]):
                if cle not in dico:
                    erreurs.append(f"{e['groupe']} : {e['fichier']}:{e['ligne']} : dzT({cle!r}) sans entrée au dico")
    # un même texte français n'a qu'UNE traduction dans tout le dictionnaire (test_i18n_l0 2.4)
    vu = {}
    for fj in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        if fj.name == DICO_F.name:
            continue
        for k, v in json.loads(fj.read_text("utf-8")).items():
            if not v.get("contexte"):
                vu.setdefault(v["fr"], (v["en"], f"{fj.name}:{k}"))
    for cle, (fr, en, ctx) in sorted(dico.items()):
        if ctx:
            continue
        if fr in vu and vu[fr][0] != en:
            erreurs.append(f"{cle} : « {fr} » est traduit « {en} », mais « {vu[fr][0]} » par {vu[fr][1]} "
                           "(prendre la même traduction, ou contexte=True)")
        vu.setdefault(fr, (en, cle))
    if erreurs:
        raise SystemExit("[l7] saisie refusée :\n  " + "\n  ".join(erreurs))
    return subs, dico, gardes


def appliquer_subs(s: str, f: str, lst) -> tuple:
    """-> (nouvelle source, éditions en positions de BASE). Scripts classiques : dzT est global, rien à importer."""
    ed = [{"pos": p, "avant": a, "apres": r, "groupe": g} for p, a, r, g in lst]
    for e in sorted(ed, key=lambda x: -x["pos"]):
        s = s[:e["pos"]] + e["apres"] + s[e["pos"] + len(e["avant"]):]
    return s, sorted(ed, key=lambda x: x["pos"])


def appliquer(fichier: str, source_base: str) -> str:
    """La source d'avant L7 -> la source L6, d'après la table consignée (sans relire la saisie)."""
    if not PAIRES.is_file():
        return source_base
    ed = json.loads(PAIRES.read_bytes().decode("utf-8"))["fichiers"].get(fichier, [])
    crlf = "\r\n" in source_base
    s = source_base if crlf else source_base.replace("\n", "\r\n")
    for e in sorted(ed, key=lambda x: (-x["pos"], x["avant"] == "")):
        if s[e["pos"]:e["pos"] + len(e["avant"])] != e["avant"]:
            raise ValueError(f"{fichier} : l'édition L7 {e['groupe']}@{e['pos']} ne trouve pas son texte")
        s = s[:e["pos"]] + e["apres"] + s[e["pos"] + len(e["avant"]):]
    return s if crlf else s.replace("\r\n", "\n")


# ── restes : littéraux d'allure française encore en dur ─────────────────────────────────────────────────────────
_ACC = re.compile(r"[àâçéèêëîïôûùüÿœæ«»’]", re.I)
_MOTS = re.compile(r"\b(le|la|les|des|du|une|un|et|ou|pour|avec|sans|dans|sur|est|pas|ce|cette|vos|votre|aucun|"
                   r"aucune|choisir|ajouter|enregistrer|annuler|supprimer|fermer|ouvrir|exporter|calque|calques|"
                   r"outil|forme|texte|couleur|nouveau|nouvelle|image|fichier|document|taille|largeur|hauteur)\b", re.I)


def francais(t: str) -> bool:
    t = t.strip()
    if len(t) < 2 or not re.search(r"[A-Za-zÀ-ÿ]{2}", t):
        return False
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", t):          # identifiant en tirets (clé d'icône dz-*, classe CSS)
        return False
    if "[" in t and re.fullmatch(r"[\w\-#.\[\]=\"':>* ]+", t):  # sélecteur CSS (button[data-outil])
        return False
    return bool(_ACC.search(t) or _MOTS.search(t))


def litteraux_js(s: str):
    """[(pos, texte)] des littéraux d'un JS (parties fixes des gabarits comprises), hors commentaires."""
    out, i, n = [], 0, len(s)
    pile = []                                     # profondeurs d'accolades des ${…} ouverts
    prof = 0
    while i < n:
        c = s[i]
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            j = s.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "\"'":
            k = i + 1
            while k < n and s[k] != c and s[k] != "\n":
                k += 2 if s[k] == "\\" else 1
            out.append((i, s[i:k + 1]))
            i = k + 1
            continue
        if c == "`" or (c == "}" and pile and pile[-1] == prof):
            if c == "}":
                pile.pop()
            k = i + 1
            d = k
            while k < n:
                if s[k] == "\\":
                    k += 2
                    continue
                if s[k] == "`":
                    out.append((d, s[d:k]))
                    k += 1
                    break
                if s[k] == "$" and k + 1 < n and s[k + 1] == "{":
                    out.append((d, s[d:k]))
                    pile.append(prof)
                    k += 2
                    break
                k += 1
            i = k
            continue
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
        i += 1
    return out


def restes(textes: dict, table: dict, fichiers, dico, gardes):
    frs = {v[0].strip() for v in dico.values()}
    couvert = {}
    for g in gardes:
        couvert.setdefault(g["fichier"], []).extend((p, p + len(g["texte"])) for p in g["pos"])
    for f, ed in table.items():
        couvert.setdefault(f, []).extend((e["pos"], e["pos"] + len(e["avant"])) for e in ed if e["avant"])
    out = []
    for f in fichiers:
        s = textes[f]                              # la source de BASE : les numéros de ligne sont ceux de la saisie
        if f.endswith(".html"):                    # index.html n'est jamais réécrit (surcouche) : son état COURANT
            s = (RACINE / (LAB + f)).read_bytes().decode("utf-8")
        if f.endswith(".html"):
            cands = [(m.start(1), m.group(1)) for m in re.finditer(r">([^<>{}]{2,300})<", s)]
            cands += [(m.start(1), m.group(1)) for m in re.finditer(r'\b(?:title|placeholder|aria-label|alt)="([^"]{2,300})"', s)]
            # les <script> et les commentaires HTML ne sont pas affichés
            masque = [(m.start(), m.end()) for m in re.finditer(r"<script\b.*?</script>|<!--.*?-->|<style\b.*?</style>", s, re.S)]
            cands = [(p, t) for p, t in cands if not any(a <= p < b for a, b in masque)]
        else:
            cands = litteraux_js(s)
        for p, t in cands:
            brut = t
            u = _unquote(t) if t[:1] in "\"'" else t
            u = u if u is not None else t
            if not francais(u):
                continue
            if re.sub(r"\s+", " ", u).strip() in frs or re.sub(r"<[^>]+>", "", u).strip() in frs:
                continue
            if any(a <= p < b for a, b in couvert.get(f, ())):
                continue
            ligne = s.count("\n", 0, p) + 1
            out.append(f"{f}:{ligne}: {u.strip()[:110]!r}")
    return out


def _json_zone(dico):
    z = {k: ({"fr": v[0], "en": v[1], "contexte": True} if v[2] else {"fr": v[0], "en": v[1]})
         for k, v in sorted(dico.items())}
    return "{\n" + ",\n".join(f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}'
                              for k, v in z.items()) + "\n}\n"


def construire(E=None):
    E = entrees() if E is None else E
    fichiers = fichiers_lab()
    textes = {f: base(f) for f in fichiers}
    subs, dico, gardes = resoudre(E, textes)
    neufs, table = {}, {}
    for f in fichiers:
        neufs[f], ed = appliquer_subs(textes[f], f, subs.get(f, []))
        if ed:
            table[f] = ed
    return textes, neufs, table, dico, gardes, fichiers


def main(argv):
    global SEUL
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if "--seul" in argv:
        SEUL = argv[argv.index("--seul") + 1]
        E = [e for e in entrees() if e["groupe"] == SEUL]
        if not E:
            raise SystemExit(f"[l7] groupe {SEUL!r} vide ou absent")
        textes, neufs, table, dico, gardes, fichiers = construire(E)
        siens = sorted({e["fichier"] for e in E if e["type"] != "H"})
        n = sum(len(v) for v in table.values())
        print(f"[l7] {SEUL} : {len(E)} entrées valides, {n} éditions, {len(dico)} clés, {len(gardes)} gardés")
        R = [r for r in restes(textes, table, siens, dico, gardes) if dans_plage(r, PLAGES_GROUPES.get(SEUL, {}))]
        print(f"[l7] restes dans {', '.join(siens)} : {len(R)}")
        for r in R:
            print("   ", r)
        return 0
    textes, neufs, table, dico, gardes, fichiers = construire()
    if "--restes" in argv:
        R = restes(textes, table, fichiers, dico, gardes)
        print(f"[l7] restes : {len(R)}")
        for r in R:
            print("   ", r)
        return 0
    sorties = {PAIRES: (json.dumps({"base": BASE, "fichiers": table, "gardes": gardes}, ensure_ascii=False, indent=1)
                        + "\n").encode("utf-8"),
               DICO_F: _json_zone(dico).encode("utf-8")}
    for f in fichiers:
        if f.endswith(".js"):
            sorties[RACINE / (LAB + f)] = neufs[f].encode("utf-8")
    ecarts = []
    for p, b in sorties.items():
        if not p.exists() or p.read_bytes().replace(b"\r\n", b"\n") != b.replace(b"\r\n", b"\n"):
            ecarts.append(str(p.relative_to(RACINE)))
            if "--check" not in argv:
                p.write_bytes(b)
    if "--check" in argv:
        print(f"[l7] --check : {'à jour' if not ecarts else 'PAS à jour : ' + ', '.join(ecarts[:8])}")
        return 1 if ecarts else 0
    n = sum(len(v) for v in table.values())
    print(f"[l7] {n} éditions dans {len(table)} fichiers, {len(dico)} clés, {len(gardes)} gardés ; écrits : {len(ecarts)}")
    subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py")], cwd=str(RACINE), check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
