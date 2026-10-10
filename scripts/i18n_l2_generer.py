"""Traduction L2 (t142) : de la saisie (scripts/i18n_l2/*.py) à la table du maillon, à la couche et aux dictionnaires.

  python scripts/i18n_l2_generer.py              écrit scripts/i18n_l2_paires.json, frontend/patches/montage.js et
                                                  frontend/shared/i18n/{quick,studio,templates,news,scheduler,episodes}.json
  python scripts/i18n_l2_generer.py --check      vérifie que ces fichiers sont à jour (code 1 sinon)
  python scripts/i18n_l2_generer.py --seul G [--restes]
                                                  valide le seul groupe G, sans rien écrire (et liste ce qui reste en dur
                                                  dans ses composants)

Deux cibles (attribut CIBLE d'un fichier de saisie, « bundle » par défaut), comme L1 :
  * « bundle » : positions dans le bundle de BASE 419caf63 (L1 posée). Pour chaque substitution, une ancre minimale
    UNIQUE est calculée sur le texte COURANT, de la fin vers le début (une substitution ne déplace jamais une position
    encore à traiter) ; le maillon patch_bundle_i18n_l2.py rejoue la même suite dans le même ordre. L'ancre est unique
    aussi dans le bundle de base dont la couche est déjà rafraîchie (c'est lui que le maillon reçoit), et le
    remplacement est unique APRÈS application : la table se défait exactement (backend/tests/_i18n_l1_aide).
  * « couche » : positions dans frontend/patches/montage.js de BASE 419caf63 — la couche telle que L1 l'a laissée ;
    les substitutions donnent directement la nouvelle source de la couche (réinjectée ensuite par
    scripts/refresh_layer.py --layer montage). La couche de L1 se retrouve en défaisant la liste « couche » de la
    table (i18n_l1_generer s'en sert pour son --check : la couche du poste = couche L1 + substitutions L2).
Les bases sont prises avec les fins de ligne du POSTE (CRLF ici), comme les fichiers dont viennent les positions.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
BASE = "419caf63"
CIBLES = {"bundle": "frontend/dist/assets/index-BEOJX8L5.js", "couche": "frontend/patches/montage.js"}
REL = CIBLES["bundle"]
SAISIE = RACINE / "scripts" / "i18n_l2"
PAIRES = RACINE / "scripts" / "i18n_l2_paires.json"
SEUL = None
ZONES = {z: z + ".json" for z in ("quick", "studio", "templates", "news", "scheduler", "episodes")}


def _eol(rel):
    disque = (RACINE / rel).read_bytes()
    return b"\r\n" if disque.count(b"\r\n") == disque.count(b"\n") else b"\n"


def base(cible) -> str:
    rel = CIBLES[cible]
    b = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=str(RACINE), capture_output=True, check=True).stdout
    return b.replace(b"\r\n", b"\n").replace(b"\n", _eol(rel)).decode("utf-8")


def bundle_base() -> str:
    return base("bundle")


def entrees():
    out = []
    sys.path.insert(0, str(SAISIE))
    for f in sorted(SAISIE.glob("*.py")):
        if f.name == "outils.py":
            continue
        spec = importlib.util.spec_from_file_location(f"saisie2_{f.stem}", f)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
            lst = m.ENTREES
        except Exception as x:                       # noqa: BLE001
            if SEUL and f.stem != SEUL:              # --seul : un AUTRE groupe en cours d'écriture ne bloque pas
                print(f"  (groupe {f.stem} ignoré : {type(x).__name__})")
                continue
            raise
        cible = getattr(m, "CIBLE", "bundle")
        if cible not in CIBLES:
            raise ValueError(f"{f.name} : CIBLE {cible!r} inconnue")
        for e in lst:
            e["groupe"] = f.stem
            e["cible"] = cible
            out.append(e)
        # morceaux de gabarit `…${x}…` gardés tels quels (X ne vise qu'un littéral entre guillemets)
        for t, raison in getattr(m, "FRAGMENTS", {}).items():
            out.append({"type": "F", "texte": t, "raison": raison, "groupe": f.stem, "cible": cible, "dico": {}})
    return out


def _ident(c):
    return c.isalnum() or c in "_$"


def litteral(s, pos):
    q = s[pos]
    if q not in "\"'":
        raise ValueError(f"pos {pos} : pas un littéral ({s[pos:pos + 20]!r})")
    k = pos + 1
    while s[k] != q:
        k += 2 if s[k] == "\\" else 1
    return s[pos:k + 1]


def _dico_et_subs(E, textes, autres=()):
    """autres : entrées des AUTRES groupes de la saisie (mode --seul), dont les traductions comptent pour l'unicité."""
    subs = {c: [] for c in CIBLES}
    dico, gardes = {}, []
    for e in E:
        for cle, v in e["dico"].items() if e["type"] not in "XF" else []:
            fr, en, ctx = v[0], v[1], len(v) > 2 and v[2] == "contexte"
            if cle.split(".")[0] not in ZONES or cle.count(".") < 2:
                raise ValueError(f"{cle} : zone inconnue ou clé à moins de trois segments ({', '.join(ZONES)})")
            if cle in dico and dico[cle] != (fr, en, ctx):
                raise ValueError(f"{cle} : deux textes différents ({dico[cle]} / {(fr, en, ctx)})")
            dico[cle] = (fr, en, ctx)
        if e["type"] == "F":
            gardes.append({"cible": e["cible"], "pos": None, "texte": "`" + e["texte"] + "`", "raison": e["raison"],
                           "groupe": e["groupe"]})
            continue
        s = textes[e["cible"]]
        if e["type"] == "X":
            gardes.append({"cible": e["cible"], "pos": e["pos"], "texte": litteral(s, e["pos"]), "raison": e["raison"],
                           "groupe": e["groupe"]})
            continue
        if e["type"] == "L":
            avant = litteral(s, e["pos"])
            apres = f'dzT("{e["cle"]}")'
        else:
            avant, apres = e["avant"], e["apres"]
            if s[e["pos"]:e["pos"] + len(avant)] != avant:
                raise ValueError(f"{e['groupe']} pos {e['pos']} : le texte ne correspond pas "
                                 f"({s[e['pos']:e['pos'] + len(avant)]!r} au lieu de {avant!r})")
        # `return"texte"` (minifié, sans espace) : le littéral collé à un mot-clé deviendrait `returndzT(…)`, un
        # identifiant valide que node --check laisse passer mais qui plante à l'exécution — on rend l'espace
        if e["pos"] > 0 and _ident(s[e["pos"] - 1]) and apres and _ident(apres[0]):
            apres = " " + apres
        subs[e["cible"]].append((e["pos"], avant, apres, e["groupe"]))
    # un même texte français n'a qu'UNE traduction dans tout le dictionnaire (test_i18n_l0 2.4 : sinon la surcouche
    # serait ambiguë) — contrôlé contre les autres zones et entre les clés de la saisie
    vu = {}
    for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        if f.name in ZONES.values():
            continue
        for k, v in json.loads(f.read_text("utf-8")).items():
            if not v.get("contexte"):
                vu.setdefault(v["fr"], (v["en"], f"{f.name}:{k}"))
    for e in autres:
        for k, v in e["dico"].items() if e["type"] not in "XF" else []:
            if not (len(v) > 2 and v[2] == "contexte"):
                vu.setdefault(v[0], (v[1], f"{e['groupe']}:{k}"))
    for cle, (fr, en, ctx) in sorted(dico.items()):
        if ctx:
            continue                   # entrée contextuelle : réservée à dzT(clé), ignorée par la surcouche
        if fr in vu and vu[fr][0] != en:
            raise ValueError(f"{cle} : « {fr} » est traduit « {en} », mais « {vu[fr][0]} » par {vu[fr][1]}")
        vu.setdefault(fr, (en, cle))
    for c, lst in subs.items():
        lst.sort(key=lambda x: x[0])
        for a, b in zip(lst, lst[1:]):
            if a[0] + len(a[1]) > b[0]:
                raise ValueError(f"chevauchement ({c}) : {a[3]} {a[0]} et {b[3]} {b[0]}")
    return subs, dico, gardes


def avec_couche(bundle: str, couche: str) -> str:
    """Le bundle dont le bloc MONTAGE est remplacé par `couche` (comme refresh_layer : bords du bloc conservés)."""
    b, e = "/*__DZ_MONTAGE_BEGIN__*/", "/*__DZ_MONTAGE_END__*/"
    head, rest = bundle.split(b, 1)
    ancien, tail = rest.split(e, 1)
    lead = ancien[:len(ancien) - len(ancien.lstrip("\r\n"))]
    trail = ancien[len(ancien.rstrip("\r\n")):]
    src = couche.lstrip("﻿").replace("\r\n", "\n")
    if "\r\n" in bundle:
        src = src.replace("\n", "\r\n")
    return head + b + lead + src.strip("\r\n") + trail + e + tail


def construire(textes, autres=()):
    """textes = {cible: texte de BASE} -> (paires du bundle, nouvelle couche, dico, gardes, bundle final)."""
    subs, dico, gardes = _dico_et_subs(entrees(), textes, autres)
    couche = textes["couche"]
    for pos, avant, apres, groupe in reversed(subs["couche"]):
        couche = couche[:pos] + apres + couche[pos + len(avant):]
    construire.couche_subs = [{"pos": p, "avant": a, "apres": r, "groupe": g} for p, a, r, g in subs["couche"]]
    courant = textes["bundle"]
    neuf = avec_couche(textes["bundle"], couche)
    paires = []
    for pos, avant, apres, groupe in reversed(subs["bundle"]):
        g, d = 0, 0                                   # contexte à gauche, à droite
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
                raise ValueError(f"pos {pos} : aucune ancre unique")
        courant, neuf = apres_c, apres_n
        paires.append({"ancre": ancre, "remplace": rempl, "groupe": groupe})
    return paires, couche, dico, gardes, neuf


def appliquer_couche(couche_l1: str) -> str:
    """La couche L1 (frontend/patches/montage.js de 419caf63) -> la couche L2, d'après la table consignée (sans
    relire la saisie) : pour i18n_l1_generer --check et les bancs. Mêmes fins de ligne en sortie qu'en entrée."""
    if not PAIRES.is_file():
        return couche_l1
    subs = json.loads(PAIRES.read_bytes().decode("utf-8")).get("couche", [])
    crlf = "\r\n" in couche_l1
    s = couche_l1 if crlf else couche_l1.replace("\n", "\r\n")
    for e in sorted(subs, key=lambda x: -x["pos"]):
        if s[e["pos"]:e["pos"] + len(e["avant"])] != e["avant"]:
            raise ValueError(f"couche L1 : la substitution L2 {e['groupe']}@{e['pos']} ne trouve pas son texte")
        s = s[:e["pos"]] + e["apres"] + s[e["pos"] + len(e["avant"]):]
    s = _avec_l3(s)                         # t143 : la traduction L3 se pose sur la couche L2
    return s if crlf else s.replace("\r\n", "\n")


def _avec_l3(couche_l2: str) -> str:
    """t143 : la couche L2 -> la couche du poste (substitutions de L3 posées, table scripts/i18n_l3_paires.json)."""
    sys.path.insert(0, str(RACINE / "scripts"))      # le python embarqué n'ajoute pas le dossier du script
    import i18n_l3_generer
    return i18n_l3_generer.appliquer("montage", couche_l2)


def _json_paires(paires, gardes):
    # « couche » : les substitutions faites dans la couche (positions de la couche de BASE), pour qu'un banc puisse
    # reconstruire la couche d'avant L2 sans git (backend/tests/_i18n_l1_aide.py)
    return json.dumps({"base": BASE, "paires": paires, "gardes": gardes, "couche": getattr(construire, "couche_subs", [])},
                      ensure_ascii=False, indent=1) + "\n"


def _json_zone(dico, zone):
    z = {k: ({"fr": v[0], "en": v[1], "contexte": True} if v[2] else {"fr": v[0], "en": v[1]})
         for k, v in sorted(dico.items()) if k.startswith(zone + ".")}
    return "{\n" + ",\n".join(f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}'
                              for k, v in z.items()) + "\n}\n"


def sorties(paires, couche, dico, gardes):
    """chemin -> octets attendus"""
    out = {PAIRES: _json_paires(paires, gardes).encode("utf-8"),
           RACINE / CIBLES["couche"]: _avec_l3(couche).encode("utf-8")}   # t143 : L3 posée par-dessus
    for zone, fichier in ZONES.items():
        out[RACINE / "frontend" / "shared" / "i18n" / fichier] = _json_zone(dico, zone).encode("utf-8")
    return out


def main(args):
    textes = {c: base(c) for c in CIBLES}
    if "--seul" in args:
        g = args[args.index("--seul") + 1]
        global entrees, SEUL
        SEUL = g
        tout = entrees
        E = tout()
        entrees = lambda: [e for e in E if e["groupe"] == g]          # noqa: E731
        paires, couche, dico, gardes, final = construire(textes, [e for e in E if e["groupe"] != g])
        nc = sum(1 for e in E if e["groupe"] == g and e["cible"] == "couche" and e["type"] in "LS")
        print(f"[{g}] OK : {len(paires)} substitutions dans le bundle, {nc} dans la couche, {len(dico)} clés, "
              f"{len(gardes)} littéraux gardés")
        if "--restes" in args:
            import i18n_l2_perimetre as PER
            R = PER.restes(final, couche, gardes, [g])
            print(f"[{g}] restes : {len(R)}")
            for r in R:
                print("  ", r)
        return 0
    paires, couche, dico, gardes, _ = construire(textes)
    attendus = sorties(paires, couche, dico, gardes)
    if "--check" in args:
        perimes = [str(p.relative_to(RACINE)) for p, b in attendus.items()
                   if not p.is_file() or p.read_bytes().replace(b"\r\n", b"\n") != b.replace(b"\r\n", b"\n")]
        print("à jour" if not perimes else "PÉRIMÉ : " + ", ".join(perimes) + " — relancer python scripts/i18n_l2_generer.py")
        return 0 if not perimes else 1
    for p, b in attendus.items():
        p.write_bytes(b)
    print(f"{len(paires)} substitutions dans le bundle, {len(construire.couche_subs)} dans la couche, {len(dico)} clés, "
          f"{len(gardes)} littéraux gardés")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
