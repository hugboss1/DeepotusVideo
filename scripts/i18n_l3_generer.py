"""Traduction L3 (t143) : de la saisie (scripts/i18n_l3/*.py) à la couche montage.js et au dictionnaire montage.json.
Repris du générateur de L4 (scripts/i18n_l4_generer.py), pour une seule couche.

  python scripts/i18n_l3_generer.py              écrit frontend/patches/montage.js, scripts/i18n_l3_paires.json et
                                                  frontend/shared/i18n/montage.json — puis refresh_layer --layer montage
                                                  --force et i18n_assembler.py
  python scripts/i18n_l3_generer.py --check      vérifie que ces fichiers sont à jour (code 1 sinon)
  python scripts/i18n_l3_generer.py --seul G [--restes]
                                                  valide le seul groupe G sans rien écrire (et liste ce qui reste en dur
                                                  dans sa plage)

La couche est une source complète, réinjectée telle quelle par scripts/refresh_layer.py (le bloc MONTAGE du bundle EST
la source, t120). Pas de maillon : la saisie donne directement la nouvelle source. Les positions d'une saisie sont
celles de la couche de BASE be7f9e9f (L1 et L2 posées, fins de ligne du poste, CRLF). La table
scripts/i18n_l3_paires.json garde chaque substitution (pos, avant, après) : un banc reconstruit la couche d'avant L3
sans git (backend/tests/_i18n_l1_aide.couche_avant_i18n_l3), et la couche de L2 en défaisant L3 d'abord.

Format de saisie : celui de L2 (scripts/i18n_l3/outils.py : L, S, X ; FRAGMENTS pour un morceau de gabarit gardé).
"""
import importlib.util
import json
import pathlib
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
import i18n_l3_perimetre as PER                     # noqa: E402

BASE = "be7f9e9f"
CIBLES = dict(PER.CIBLES)
SAISIE = RACINE / "scripts" / "i18n_l3"
PAIRES = RACINE / "scripts" / "i18n_l3_paires.json"
SEUL = None
# zone -> fichier du dictionnaire ; la zone « montage » est PARTAGÉE avec L4 (montage_svm.json, écran DzMontage) :
# une clé de L3 ne peut pas exister dans un autre fichier (l'assembleur refuserait le doublon)
ZONES = {"montage": "montage.json"}


def _eol(rel):
    disque = (RACINE / rel).read_bytes()
    return b"\r\n" if disque.count(b"\r\n") == disque.count(b"\n") else b"\n"


def base(cible) -> str:
    rel = CIBLES[cible]
    b = subprocess.run(["git", "show", f"{BASE}:{rel}"], cwd=str(RACINE), capture_output=True, check=True).stdout
    return b.replace(b"\r\n", b"\n").replace(b"\n", _eol(rel)).decode("utf-8")


def entrees():
    out = []
    sys.path.insert(0, str(SAISIE))
    for f in sorted(SAISIE.glob("*.py")):
        if f.name == "outils.py":
            continue
        spec = importlib.util.spec_from_file_location(f"saisie3_{f.stem}", f)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
            lst = m.ENTREES
            cible = m.CIBLE
        except Exception as x:                       # noqa: BLE001
            if SEUL and f.stem != SEUL:              # --seul : un AUTRE groupe en cours d'écriture ne bloque pas
                print(f"  (groupe {f.stem} ignoré : {type(x).__name__})")
                continue
            raise
        if f.stem not in PER.GROUPES or PER.GROUPES[f.stem][0] != cible:
            raise ValueError(f"{f.name} : groupe inconnu ou CIBLE {cible!r} différente du périmètre")
        for e in lst:
            e["groupe"] = f.stem
            e["cible"] = cible
            out.append(e)
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
    subs = {c: [] for c in CIBLES}
    dico, gardes = {}, []
    for e in E:
        for cle, v in e["dico"].items() if e["type"] not in "XF" else []:
            fr, en, ctx = v[0], v[1], len(v) > 2 and v[2] == "contexte"
            if cle.split(".")[0] not in ZONES or cle.count(".") < 2:
                raise ValueError(f"{cle} : zone inconnue ou clé à moins de trois segments ({', '.join(ZONES)})")
            if not fr or not en:
                raise ValueError(f"{cle} : fr ou en vide")
            if cle in dico and dico[cle] != (fr, en, ctx):
                raise ValueError(f"{cle} : deux textes différents ({dico[cle]} / {(fr, en, ctx)})")
            dico[cle] = (fr, en, ctx)
        if e["type"] == "F":
            gardes.append({"cible": e["cible"], "pos": None, "texte": "`" + e["texte"] + "`", "raison": e["raison"],
                           "groupe": e["groupe"]})
            continue
        s = textes[e["cible"]]
        g = PER.groupe_de(s, e["cible"], e["pos"])
        if g != e["groupe"]:
            raise ValueError(f"{e['groupe']} pos {e['pos']} : hors de la plage du groupe (dans {g})")
        if e["type"] == "X":
            gardes.append({"cible": e["cible"], "pos": e["pos"], "texte": litteral(s, e["pos"]), "raison": e["raison"],
                           "groupe": e["groupe"]})
            continue
        if e["type"] == "L":
            avant = litteral(s, e["pos"])
            apres = f'dzT("{e["cle"]}")'
            fr_dico = e["dico"][e["cle"]][0]
            brut = avant[1:-1]
            if "\\" not in brut and brut != fr_dico:
                raise ValueError(f"{e['groupe']} pos {e['pos']} : le français de {e['cle']} ({fr_dico!r}) n'est pas "
                                 f"le littéral de la source ({brut!r})")
        else:
            avant, apres = e["avant"], e["apres"]
            if s[e["pos"]:e["pos"] + len(avant)] != avant:
                raise ValueError(f"{e['groupe']} pos {e['pos']} : le texte ne correspond pas "
                                 f"({s[e['pos']:e['pos'] + len(avant)]!r} au lieu de {avant!r})")
        if e["pos"] > 0 and _ident(s[e["pos"] - 1]) and apres and _ident(apres[0]):
            apres = " " + apres
        subs[e["cible"]].append((e["pos"], avant, apres, e["groupe"]))
    # une clé du lot ne peut pas exister dans un AUTRE dictionnaire (la zone « montage » est partagée avec L4)
    for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        if f.name in ZONES.values():
            continue
        deja = set(json.loads(f.read_text("utf-8"))) & set(dico)
        if deja:
            raise ValueError(f"clés déjà prises dans {f.name} : {sorted(deja)[:8]}")
    # un même texte français n'a qu'UNE traduction dans tout le dictionnaire (test_i18n_l0 2.4)
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
            continue
        if fr in vu and vu[fr][0] != en:
            raise ValueError(f"{cle} : « {fr} » est traduit « {en} », mais « {vu[fr][0]} » par {vu[fr][1]}")
        vu.setdefault(fr, (en, cle))
    for c, lst in subs.items():
        lst.sort(key=lambda x: x[0])
        for a, b in zip(lst, lst[1:]):
            if a[0] + len(a[1]) > b[0]:
                raise ValueError(f"chevauchement ({c}) : {a[3]} {a[0]} et {b[3]} {b[0]}")
    return subs, dico, gardes


def construire(textes, autres=()):
    """textes = {cible: couche de BASE} -> ({cible: nouvelle couche}, table, dico, gardes)."""
    subs, dico, gardes = _dico_et_subs(entrees(), textes, autres)
    couches, table = {}, {}
    for c, s in textes.items():
        for pos, avant, apres, groupe in reversed(subs[c]):
            s = s[:pos] + apres + s[pos + len(avant):]
        couches[c] = s
        table[c] = [{"pos": p, "avant": a, "apres": r, "groupe": g} for p, a, r, g in subs[c]]
    return couches, table, dico, gardes


def appliquer(cible, couche_base: str) -> str:
    """La couche d'avant L3 -> la couche L3, d'après la table consignée (sans relire la saisie)."""
    if not PAIRES.is_file():
        return couche_base
    subs = json.loads(PAIRES.read_bytes().decode("utf-8"))["couches"].get(cible, [])
    crlf = "\r\n" in couche_base
    s = couche_base if crlf else couche_base.replace("\n", "\r\n")
    for e in sorted(subs, key=lambda x: -x["pos"]):
        if s[e["pos"]:e["pos"] + len(e["avant"])] != e["avant"]:
            raise ValueError(f"{cible} : la substitution L3 {e['groupe']}@{e['pos']} ne trouve pas son texte")
        s = s[:e["pos"]] + e["apres"] + s[e["pos"] + len(e["avant"]):]
    return s if crlf else s.replace("\r\n", "\n")


def _json_paires(table, gardes):
    return json.dumps({"base": BASE, "couches": table, "gardes": gardes}, ensure_ascii=False, indent=1) + "\n"


def _json_zone(dico, zone):
    z = {k: ({"fr": v[0], "en": v[1], "contexte": True} if v[2] else {"fr": v[0], "en": v[1]})
         for k, v in sorted(dico.items()) if k.startswith(zone + ".")}
    return "{\n" + ",\n".join(f'  {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}'
                              for k, v in z.items()) + "\n}\n"


def _g1(texte, cible):
    """Icônes G1 (scripts/icones/g1_generer.py, BASE = la couche traduite par L3) posées PAR-DESSUS : la source du
    poste les porte."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("g1_generer", RACINE / "scripts" / "icones" / "g1_generer.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.appliquer_couche_g1(texte, cible)


def sorties(couches, table, dico, gardes):
    """chemin -> octets attendus"""
    out = {PAIRES: _json_paires(table, gardes).encode("utf-8")}
    for c, s in couches.items():
        out[RACINE / CIBLES[c]] = _g1(s, c).encode("utf-8")
    for zone, fichier in ZONES.items():
        out[RACINE / "frontend" / "shared" / "i18n" / fichier] = _json_zone(dico, zone).encode("utf-8")
    return out


def main(args):
    global entrees, SEUL
    textes = {c: base(c) for c in CIBLES}
    if "--seul" in args:
        g = args[args.index("--seul") + 1]
        SEUL = g
        tout = entrees
        E = tout()
        entrees = lambda: [e for e in E if e["groupe"] == g]          # noqa: E731
        couches, table, dico, gardes = construire(textes, [e for e in E if e["groupe"] != g])
        n = sum(1 for e in E if e["groupe"] == g and e["type"] in "LS")
        print(f"[{g}] OK : {n} substitutions, {len(dico)} clés, {len(gardes)} littéraux gardés")
        # la couche du groupe doit rester du JavaScript valide (node --check sur un fichier temporaire)
        import shutil
        import tempfile
        if shutil.which("node"):
            with tempfile.TemporaryDirectory() as d:
                f = pathlib.Path(d) / "couche.js"
                f.write_bytes(couches[PER.GROUPES[g][0]].encode("utf-8"))
                p = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, encoding="utf-8",
                                   errors="replace")
                print(f"[{g}] node --check : " + ("OK" if p.returncode == 0 else "ÉCHEC\n" + p.stderr[-1500:]))
        if "--restes" in args:
            R = PER.restes(textes, couches, gardes, [g])
            print(f"[{g}] restes : {len(R)}")
            for r in R:
                print("  ", r)
        return 0
    couches, table, dico, gardes = construire(textes)
    attendus = sorties(couches, table, dico, gardes)
    if "--check" in args:
        perimes = [str(p.relative_to(RACINE)) for p, b in attendus.items()
                   if not p.is_file() or p.read_bytes().replace(b"\r\n", b"\n") != b.replace(b"\r\n", b"\n")]
        print("à jour" if not perimes else "PÉRIMÉ : " + ", ".join(perimes) + " — relancer python scripts/i18n_l3_generer.py")
        return 0 if not perimes else 1
    if "--restes" in args:
        R = PER.restes(textes, couches, gardes)
        print(f"restes : {len(R)}")
        for r in R:
            print("  ", r)
        return 0
    for p, b in attendus.items():
        p.write_bytes(b)
    print(f"{sum(len(v) for v in table.values())} substitutions dans les couches, {len(dico)} clés, "
          f"{len(gardes)} littéraux gardés")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
