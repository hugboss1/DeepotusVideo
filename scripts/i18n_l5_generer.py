"""Traduction L5 (t145) : sous-titres, transfert, dialogues — de la saisie (scripts/i18n_l5/*.py) à la table du maillon,
aux deux sources et aux dictionnaires.

  python scripts/i18n_l5_generer.py              écrit scripts/i18n_l5_paires.json, frontend/patches/transfert.js,
                                                  frontend/shared/dialogue.js (+ ses deux copies octet pour octet) et
                                                  frontend/shared/i18n/{subs,transfert,dialogue}.json
  python scripts/i18n_l5_generer.py --check      vérifie que ces fichiers sont à jour (code 1 sinon)
  python scripts/i18n_l5_generer.py --seul G [--restes]
                                                  valide le seul groupe G sans rien écrire (et liste ce qui reste en
                                                  français dans sa plage)

Trois cibles (CIBLE d'un fichier de saisie) :
  * « subs » : le bloc SUBS du bundle. Il n'a PLUS de source : frontend/patches/subs.js est INTOUCHABLE (des patchers
    aval écrivent dans le bloc, test_montage_bundle compte la divergence) — d'où un maillon de queue,
    patch_bundle_i18n_l5.py, qui rejoue la table (ancres minimales uniques, de la fin vers le début, uniques aussi
    dans le bundle dont les blocs TRANSFERT et DIALOGUE sont déjà rafraîchis ; remplacement unique APRÈS
    application : la table se défait exactement, backend/tests/_i18n_l1_aide.avant_i18n_l5).
  * « transfert » : frontend/patches/transfert.js, source COMPLÈTE de son bloc (au marqueur près) : réécrite ici, le
    bloc est rafraîchi par scripts/refresh_layer.py --layer transfert.
  * « dialogue » : frontend/shared/dialogue.js, idem (--layer dialogue), recopiée dans frontend/patches/dialogue.js et
    frontend/dist/shared/dialogue.js (test_dialogue_bundle : les trois octet pour octet).
Les bases sont prises au commit BASE, aux fins de ligne du POSTE (CRLF), comme les fichiers dont viennent les plages.
"""
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parent.parent
BASE = "2b155403"
BUNDLE = "frontend/dist/assets/index-BEOJX8L5.js"
SOURCES = {"transfert": "frontend/patches/transfert.js", "dialogue": "frontend/shared/dialogue.js"}
COPIES = {"dialogue": ["frontend/patches/dialogue.js", "frontend/dist/shared/dialogue.js"]}
TAGS = {"subs": "SUBS", "transfert": "TRANSFERT", "dialogue": "DIALOGUE"}
SAISIE = RACINE / "scripts" / "i18n_l5"
PAIRES = RACINE / "scripts" / "i18n_l5_paires.json"
ZONES = {z: z + ".json" for z in ("subs", "transfert", "dialogue")}
SEUL = None


def _eol(rel):
    p = RACINE / rel
    if not p.is_file():
        return b"\r\n"
    d = p.read_bytes()
    return b"\r\n" if d.count(b"\r\n") == d.count(b"\n") else b"\n"


def _show(rel):
    b = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=str(RACINE), capture_output=True, check=True).stdout
    return b.replace(b"\r\n", b"\n").replace(b"\n", _eol(rel)).decode("utf-8")


def bases():
    """{cible: (texte de base, début de la zone de recherche, fin, origine des numéros de ligne)}"""
    out = {}
    b = _show(BUNDLE)
    deb, fin = "/*__DZ_SUBS_BEGIN__*/", "/*__DZ_SUBS_END__*/"
    i, j = b.index(deb), b.index(fin)
    out["subs"] = (b, i + len(deb), j, b.rfind("\n", 0, i) + 1)
    for c, rel in SOURCES.items():
        s = _show(rel)
        out[c] = (s, 0, len(s), 0)
    return out


def entrees():
    out = []
    sys.path.insert(0, str(SAISIE))
    for f in sorted(SAISIE.glob("*.py")):
        if f.name == "outils.py":
            continue
        spec = importlib.util.spec_from_file_location(f"saisie5_{f.stem}", f)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
            lst, cible, plage = m.ENTREES, m.CIBLE, m.PLAGE
        except Exception as x:                       # noqa: BLE001
            if SEUL and f.stem != SEUL:
                print(f"  (groupe {f.stem} ignoré : {type(x).__name__})")
                continue
            raise
        if cible not in TAGS:
            raise ValueError(f"{f.name} : CIBLE {cible!r} inconnue")
        for e in lst:
            e.update(groupe=f.stem, cible=cible, plage=tuple(plage))
            out.append(e)
    return out


def _ligne(s, origine, pos):
    return s.count("\n", origine, pos) + 1


def _ident(c):
    return c.isalnum() or c in "_$"


def _dico_et_subs(E, B, autres=()):
    subs = {c: [] for c in TAGS}
    dico, gardes = {}, []
    etrangers = {}
    tout = {}
    for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        for k, v in json.loads(f.read_text("utf-8")).items():
            tout[k] = (v["fr"], v["en"], bool(v.get("contexte")), f.name)
    plages = {}
    for e in list(E) + list(autres):
        plages.setdefault((e["cible"], e["groupe"]), e["plage"])
    vues = {}
    for (c, g), (a, b) in plages.items():
        for (c2, g2), (a2, b2) in plages.items():
            if c == c2 and g < g2 and a <= b2 and a2 <= b:
                raise ValueError(f"plages qui se chevauchent : {g} {a}-{b} et {g2} {a2}-{b2} ({c})")
    # S d'abord, puis L, puis X : un littéral se compte HORS des textes déjà pris (un "Fermer" ou un "en cours" pris
    # dans un S ne compte ni pour un L ni pour une garde)
    couverts = {c: set() for c in TAGS}
    for e in sorted(E, key=lambda e: "SLX".index(e["type"])):
        s, a, b, origine = B[e["cible"]]
        if "\r\n" in s:                 # une entrée sur plusieurs lignes s'écrit avec \n : la base est en CRLF
            for k in ("avant", "apres"):
                if k in e:
                    e[k] = e[k].replace("\r\n", "\n").replace("\n", "\r\n")
        for cle, v in e["dico"].items():
            fr, en, ctx = v[0], v[1], len(v) > 2 and v[2] == "contexte"
            zone = cle.split(".")[0]
            if cle.count(".") < 2:
                raise ValueError(f"{cle} : clé à moins de trois segments")
            if zone not in ZONES:
                # clé d'une autre zone (commun.action.annuler…) : elle doit exister telle quelle
                if cle not in tout or tout[cle][:2] != (fr, en):
                    raise ValueError(f"{cle} : clé d'une autre zone absente ou différente ({tout.get(cle)})")
                etrangers[cle] = (fr, en, ctx)
                continue
            if cle in dico and dico[cle] != (fr, en, ctx):
                raise ValueError(f"{cle} : deux textes différents ({dico[cle]} / {(fr, en, ctx)})")
            dico[cle] = (fr, en, ctx)
        p1, p2 = e["plage"]
        occ = []
        k = s.find(e["avant"], a)
        while 0 <= k < b:
            if p1 <= _ligne(s, origine, k) <= p2 and k not in couverts[e["cible"]]:
                occ.append(k)
            k = s.find(e["avant"], k + 1)
        if e["type"] != "X":
            for k in occ:
                couverts[e["cible"]].update(range(k, k + len(e["avant"])))
        if len(occ) != e["n"]:
            raise ValueError(f"{e['groupe']} : {e['avant'][:70]!r} trouvé {len(occ)} fois dans les lignes {p1}-{p2} "
                             f"(attendu {e['n']})")
        if e["type"] == "X":
            for k in occ:
                gardes.append({"cible": e["cible"], "ligne": _ligne(s, origine, k), "texte": e["avant"],
                               "raison": e["raison"], "groupe": e["groupe"]})
            continue
        for k in occ:
            apres = e["apres"]
            # `return"texte"` (minifié) : le littéral collé à un mot deviendrait `returndzT(…)` — on rend l'espace
            if k > 0 and _ident(s[k - 1]) and _ident(apres[0]):
                apres = " " + apres
            subs[e["cible"]].append((k, e["avant"], apres, e["groupe"]))
    # un même français n'a qu'UNE traduction (test_i18n_l0 2.4) et l'anglais d'une clé n'est le français d'aucune
    # autre (2.6) — contrôlé contre toutes les autres zones et dans la saisie
    vu = {}
    for k, (fr, en, ctx, f) in tout.items():
        if f not in ZONES.values() and not ctx:
            vu.setdefault(fr, (en, f"{f}:{k}"))
    for e in autres:
        for k, v in e["dico"].items():
            if not (len(v) > 2 and v[2] == "contexte") and k.split(".")[0] in ZONES:
                vu.setdefault(v[0], (v[1], f"{e['groupe']}:{k}"))
    for cle, (fr, en, ctx) in sorted(dico.items()):
        if ctx:
            continue
        if fr in vu and vu[fr][0] != en:
            raise ValueError(f"{cle} : « {fr} » est traduit « {en} », mais « {vu[fr][0]} » par {vu[fr][1]}")
        vu.setdefault(fr, (en, cle))
    for cle, (fr, en, ctx) in sorted(dico.items()):
        if not ctx and en != fr and en in vu and vu[en][0] != en:
            raise ValueError(f"{cle} : l'anglais « {en} » est le français d'une autre entrée ({vu[en][1]})")
    for c, lst in subs.items():
        lst.sort(key=lambda x: x[0])
        for x, y in zip(lst, lst[1:]):
            if x[0] + len(x[1]) > y[0]:
                raise ValueError(f"chevauchement ({c}) : {x[3]} {x[0]} et {y[3]} {y[0]}")
    return subs, dico, gardes


def _appliquer(s, lst):
    for pos, avant, apres, _ in reversed(lst):
        s = s[:pos] + apres + s[pos + len(avant):]
    return s


def sans_marqueurs(src: str, tag: str) -> str:
    """La source d'une couche dont le fichier porte ses propres lignes de marqueurs : le cœur, sans elles."""
    deb, fin = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    return src.split(deb, 1)[1].split(fin, 1)[0] if deb in src else src


def avec_bloc(bundle: str, tag: str, coeur: str) -> str:
    """Le bundle dont le bloc `tag` est remplacé par `coeur` (comme refresh_layer : bords du bloc conservés)."""
    b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    head, rest = bundle.split(b, 1)
    ancien, tail = rest.split(e, 1)
    lead = ancien[:len(ancien) - len(ancien.lstrip("\r\n"))]
    trail = ancien[len(ancien.rstrip("\r\n")):]
    src = coeur.lstrip("﻿").replace("\r\n", "\n")
    if "\r\n" in bundle:
        src = src.replace("\n", "\r\n")
    return head + b + lead + src.strip("\r\n") + trail + e + tail


def construire(B, autres=()):
    subs, dico, gardes = _dico_et_subs(entrees(), B, autres)
    sources = {c: _appliquer(B[c][0], subs[c]) for c in SOURCES}
    courant = B["subs"][0]
    neuf = courant
    for c in SOURCES:
        neuf = avec_bloc(neuf, TAGS[c], sans_marqueurs(sources[c], TAGS[c]))
    paires = []
    for pos, avant, apres, groupe in reversed(subs["subs"]):
        g = d = 0
        while True:
            ancre = courant[pos - g:pos + len(avant) + d]
            rempl = courant[pos - g:pos] + apres + courant[pos + len(avant):pos + len(avant) + d]
            if courant.count(ancre) == 1 and neuf.count(ancre) == 1:
                apres_c = courant[:pos - g] + rempl + courant[pos + len(avant) + d:]
                apres_n = neuf.replace(ancre, rempl, 1)
                if apres_c.count(rempl) == 1 and apres_n.count(rempl) == 1:
                    break
            g, d = g + 4, d + 4
            if g > 400:
                raise ValueError(f"subs pos {pos} ({groupe}) : aucune ancre unique")
        courant, neuf = apres_c, apres_n
        paires.append({"ancre": ancre, "remplace": rempl, "groupe": groupe})
    trace = {c: [{"pos": p, "avant": a, "apres": r, "groupe": g} for p, a, r, g in subs[c]] for c in SOURCES}
    # où commence, dans la source de BASE, le cœur que le bundle porte (après la ligne du marqueur BEGIN et les retours
    # de ligne que refresh_layer retire) : _i18n_l1_aide.avant_i18n_l5 défait les substitutions DANS le bloc du bundle
    construire.decalages = {}
    for c in SOURCES:
        src, deb = B[c][0], f"/*__DZ_{TAGS[c]}_BEGIN__*/"
        k = src.index(deb) + len(deb)
        while src[k] in "\r\n":
            k += 1
        construire.decalages[c] = k
    return paires, sources, dico, gardes, neuf, trace


def _json_zone(dico, zone):
    z = {k: ({"fr": v[0], "en": v[1], "contexte": True} if v[2] else {"fr": v[0], "en": v[1]})
         for k, v in sorted(dico.items()) if k.startswith(zone + ".")}
    return "{\n" + ",\n".join(f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}'
                              for k, v in z.items()) + "\n}\n"


def _g1(texte, tag):
    """Icônes G1 (scripts/icones/g1_generer.py, BASE = les blocs traduits par L5) posées PAR-DESSUS une source dont
    le bloc est édité par le maillon dzglyph (TRANSFERT : la source en est le miroir) ; DIALOGUE n'en a aucune."""
    if tag != "TRANSFERT":
        return texte
    spec = importlib.util.spec_from_file_location("g1_generer", RACINE / "scripts" / "icones" / "g1_generer.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.appliquer_bloc_g1(texte)


def sorties(paires, sources, dico, gardes, trace):
    out = {PAIRES: (json.dumps({"base": BASE, "paires": paires, "gardes": gardes, "sources": trace,
                                "decalages": getattr(construire, "decalages", {})},
                               ensure_ascii=False, indent=1) + "\n").encode("utf-8")}
    for c, rel in SOURCES.items():
        out[RACINE / rel] = _g1(sources[c], TAGS[c]).encode("utf-8")
        for copie in COPIES.get(c, []):
            out[RACINE / copie] = sources[c].encode("utf-8")
    for zone, fichier in ZONES.items():
        out[RACINE / "frontend" / "shared" / "i18n" / fichier] = _json_zone(dico, zone).encode("utf-8")
    return out


# ── restes : ce qui reste en français dans la plage d'un groupe (littéraux non couverts) ─────────────────────────────
_FR = re.compile(r"[àâäéèêëîïôöùûüçœÀÂÉÈÊÎÔÛÇ«»’]|\b(le|la|les|des|du|un|une|et|ou|pour|avec|sans|dans|sur|pas|aucun|"
                 r"aucune|est|sont|cette|ces|vos|ton|ta|tes|mots?|lignes?|pistes?|répliques?|clips?|secondes?)\b", re.I)
_TECH = re.compile(r"var\(--|\d(px|em|vh|vw|%)|rgba?\(|#[0-9a-fA-F]{3,8}\b|solid|monospace|/api/|cubic-bezier")


def litteraux(s, a, b):
    i = a
    while i < b:
        c = s[i]
        if c == "/" and s[i + 1] == "/":
            j = s.find("\n", i)
            i = b if j < 0 else j
            continue
        if c == "/" and s[i + 1] == "*":
            i = s.find("*/", i + 2) + 2
            continue
        if c in "\"'`":
            k = i + 1
            while k < b and s[k] != c:
                if c != "`" and s[k] == "\n":
                    break
                k += 2 if s[k] == "\\" else 1
            yield i, s[i:k + 1]
            i = k + 1
            continue
        if c == "/":
            j = i - 1
            while j > a and s[j] in " \t\r\n":
                j -= 1
            if s[j] in "(,=:[!&|?{};+-*%<>~^" or s[max(0, j - 5):j + 1] == "return":
                k, classe = i + 1, False
                while k < b and (s[k] != "/" or classe) and s[k] != "\n":
                    if s[k] == "\\":
                        k += 2
                        continue
                    classe = True if s[k] == "[" else False if s[k] == "]" else classe
                    k += 1
                i = k + 1
                continue
        i += 1


def restes(B, groupe, E):
    e0 = next(e for e in E if e["groupe"] == groupe)
    s, a, b, origine = B[e0["cible"]]
    p1, p2 = e0["plage"]
    couverts = set()
    for e in E:
        if e["cible"] != e0["cible"]:
            continue
        av = e["avant"].replace("\r\n", "\n").replace("\n", "\r\n") if "\r\n" in s else e["avant"]
        k = s.find(av, a)
        while 0 <= k < b:
            couverts.update(range(k, k + len(av)))
            k = s.find(av, k + 1)
    out = []
    for pos, lit in litteraux(s, a, b):
        ln = _ligne(s, origine, pos)
        if not p1 <= ln <= p2 or pos in couverts:
            continue
        corps = lit[1:-1]
        if not re.search(r"[A-Za-zÀ-ÿ]{2}", corps) or _TECH.search(corps):
            continue
        if _FR.search(corps) or (" " in corps.strip() and re.search(r"[a-zà-ÿ]{3}", corps)) or re.fullmatch(r"[A-ZÀ-Ý][a-zà-ÿ]+", corps):
            out.append(f"L{ln}\t{lit[:110]}")
    return out


def _node_check(texte, nom):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / (nom + (".mjs" if nom == "subs" else ".js"))          # le bundle est un module ES
        p.write_text(texte, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True, encoding="utf-8")
        return r.returncode == 0, (r.stderr or "")[:600]


def main(args):
    global SEUL
    B = bases()
    if "--seul" in args:
        g = args[args.index("--seul") + 1]
        SEUL = g
        E = entrees()
        global entrees_
        moi = [e for e in E if e["groupe"] == g]
        autres = [e for e in E if e["groupe"] != g]
        import builtins  # noqa: F401
        tout = entrees
        globals()["entrees"] = lambda: moi
        try:
            paires, sources, dico, gardes, final, trace = construire(B, autres)
        finally:
            globals()["entrees"] = tout
        cible = moi[0]["cible"] if moi else "?"
        n = len(paires) if cible == "subs" else len(trace.get(cible, []))
        texte = final if cible == "subs" else sources[cible]
        ok, err = _node_check(texte, cible)
        print(f"[{g}] OK : {n} substitutions ({cible}), {len(dico)} clés, {len(gardes)} littéraux gardés ; "
              f"node --check {'OK' if ok else 'ÉCHEC ' + err}")
        if "--restes" in args:
            R = restes(B, g, E)
            print(f"[{g}] restes : {len(R)}")
            for r in R:
                print("  ", r)
        return 0 if ok else 1
    paires, sources, dico, gardes, final, trace = construire(B)
    attendus = sorties(paires, sources, dico, gardes, trace)
    if "--check" in args:
        perimes = [str(p.relative_to(RACINE)) for p, b in attendus.items()
                   if not p.is_file() or p.read_bytes() != b]
        print("à jour" if not perimes else "PÉRIMÉ : " + ", ".join(perimes) + " — relancer python scripts/i18n_l5_generer.py")
        return 0 if not perimes else 1
    for c, s in [("subs", final)] + list(sources.items()):
        ok, err = _node_check(s, c)
        if not ok:
            print(f"node --check ÉCHEC ({c}) : {err}")
            return 1
    for p, b in attendus.items():
        p.write_bytes(b)
    print(f"{len(paires)} substitutions dans le bloc SUBS, " + ", ".join(f"{len(t)} dans {c}" for c, t in trace.items())
          + f", {len(dico)} clés, {len(gardes)} littéraux gardés")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
