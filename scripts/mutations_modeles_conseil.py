# -*- coding: utf-8 -*-
"""t492 (lot F5) — mutations de app.services.modeles_conseil : chaque mutation doit faire rougir
backend/tests/test_modeles_conseil.py. La source est copiée AVANT et comparée APRÈS (restauration sûre).

Lancement (python embarqué, depuis la racine) :  PYTHONUTF8=1 python scripts/mutations_modeles_conseil.py
"""
import os
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SRC = RACINE / "backend/app/services/modeles_conseil.py"
BANC = RACINE / "backend/tests/test_modeles_conseil.py"

M = [
    # coût
    ('        return round(usd * float(d) * n, 4)', '        return round(usd * n, 4)'),
    ('max(1, math.ceil(float(d or 60) / 60.0))', 'float(d or 60) / 60.0'),
    ('max(1, int(c.get("caracteres") or 1000)) / 1000.0', '1.0'),
    ('        return 0.0 if m.get("voie") == "local" else None', '        return 0.0'),
    # filtres
    ('    if c.get("cles_posees") and not m.get("dispo"):', '    if False:'),
    ('int(round(float(d))) not in m["durations"]', 'False'),
    ('    if c.get("image_fin") and nat & set(_NATURES_VIDEO) and not m.get("end_image"):', '    if False:'),
    ('        if m.get("refs_max") is not None and refs > int(m["refs_max"]):', '        if False:'),
    ('    if c.get("transparent") and "image" in nat and not m.get("transparent"):', '    if False:'),
    ('    if "image" in nat and bool(c.get("vecteur")) != (m.get("sortie") == "svg"):', '    if False:'),
    ('    if c.get("paroles") and "musique" in nat and not m.get("paroles"):', '    if False:'),
    ('    if c.get("garder_voix") and "sfx_video" in nat and not m.get("voix"):', '    if False:'),
    ('        if c.get("depuis_texte") and not m.get("texte"):', '        if False:'),
    ('        if c.get("pose_rig") and not m.get("tpose"):', '        if False:'),
    ('        if c.get("format_export") and c["format_export"] not in (m.get("formats") or []):', '        if False:'),
    ('    if c.get("balises") and "voix" in nat and not m.get("balises"):', '    if False:'),
    ('        if k is not None and k > float(c["budget_usd"]):', '        if False:'),
    # classement
    ('(1.0 if nomme else 0)', '0'),
    ('sum(1.0 / df.get(w, 1) for w in trouves)', 'len(trouves) * 0'),
    ('out.add(m[:6] if m.isalpha() else m)', 'out.add(m)'),
    ('        if m.isalpha() and len(m) > 4 and m[-1] in "sx":', '        if False:'),
    ('if mots & _mots(ch) and not _PAS_ENCORE.search(ch)]', 'if mots & _mots(ch)]'),
    ('next((g for g in gardes[1:] if premier and g["famille"] != premier["famille"]), None)',
     'next((g for g in gardes[1:] if premier), None)'),
    ('gardes.sort(key=lambda g: (-g["score"], not g["dispo"], g["cout_estime"] is None,',
     'gardes.sort(key=lambda g: (g["score"], not g["dispo"], g["cout_estime"] is None,'),
    ('    pub = lambda g: None if g is None else {k: v for k, v in g.items() if k != "_m"}',
     '    pub = lambda g: g'),
    ('        return {"id": p["id"], "reglage": {"texture": False},', '        return {"id": p["id"], "reglage": {},'),
    ('        bas = min(q, key=lambda k: float(q[k] or 0))', '        bas = max(q, key=lambda k: float(q[k] or 0))'),
    ('g["cout_estime"] < p["cout_estime"]]', 'g["cout_estime"] > p["cout_estime"]]'),
    # relecture
    ('        if f and (visuel or "modele3d" in nat):', '        if False:'),
    ('        if s and sonore:', '        if False:'),
    ('if not _NEGATIFS_PERMIS.match(p[x.start():]) and not _RX_SANS_SON.match(p[x.start():])]',
     'if not _RX_SANS_SON.match(p[x.start():])]'),
    ('            ou = ("le membre a un champ négatif : y mettre ces mots" if m.get("negatif")',
     '            ou = ("le membre a un champ négatif : y mettre ces mots" if True'),
    ('        if pr and visuel:', '        if False:'),
    ('        if cli:', '        if False:'),
    ('        if cr and visuel:', '        if False:'),
    ('sum(len(s.split()) <= 3 for s in segs) >= 0.7 * len(segs)', 'False'),
    ('            if IP.fond_transparent_demande(p) and not IP.accepte_transparent(m["id"]):', '            if False:'),
    ('    if lim and len(p) > lim:', '    if False:'),
    ('PROMPT_MAX_VIDEO = {"h3-max": 2000}', 'PROMPT_MAX_VIDEO = {}'),
    ('        return int(e["prompt_max"]) if e.get("prompt_max") else None', '        return None'),
    ('        tags = [x for x in VD.find_tags(p) if VD.is_known(x)]', '        tags = VD.find_tags(p)'),
    ('        if inconnues:', '        if False:'),
    # t492 : correctifs de l'épreuve d'application
    ('                raise ValueError(f"contrainte « {k} » : un nombre est attendu, pas « {v} »")', '                continue'),
    ('            if x < 0 or (k in ("n", "duree", "caracteres", "vues") and x == 0):', '            if False:'),
    ('            ignorees.append(str(k)[:40])', '            pass'),
    ('    if c.get("qualite") and isinstance(q, dict):', '    if False:'),
    ('        c["qualite"] = "bas"', '        pass'),
    ('mots = _mots(consigne) - _mots(" ".join(x.group(0) for x in _BAS_PRIX.finditer(consigne or "")))',
     'mots = _mots(consigne)'),
    ('        if "musique" in nat and not m.get("duree"):', '        if False:'),
    ('            suite = ds == list(range(ds[0], ds[-1] + 1))', '            suite = True'),
    ('+ (1.0 if nomme else 0) + adequation, 3),', '+ (1.0 if nomme else 0), 3),'),
    ('        if c.get("ratio") and nat_video and not m.get("ratios"):', '        if False:'),
    ('            "classement": [pub(g) for g in gardes], "ecartes": ecartes, "total": len(entrees)}',
     '            "classement": [pub(g) for g in gardes[:8]], "ecartes": ecartes, "total": len(entrees)}'),
    (r'|[-−]\s?\d{1,2}\s?%', ''),
    (r'\bno (?:lettering|text|words)\b', r'\bno lettering\b'),
    ('            dire("balise_hors_palette", "erreur",', '            dire("balise_hors_palette", "avertissement",'),
    ('    if requis and not p.strip():', '    if False:'),
    ('            sans_champ = bool(nat & set(_NATURES_VIDEO)) and not m.get("ratios")', '            sans_champ = False'),
    ('            "constats": out, "ok": not any(x["gravite"] == "erreur" for x in out)}',
     '            "constats": out, "ok": True}'),
    ('            dire("trop_long", "info",', '            dire("trop_long", "erreur",'),
]


def lancer() -> bool:
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run([sys.executable, str(BANC)], cwd=str(RACINE / "backend"), capture_output=True, env=env,
                       timeout=600)
    return r.returncode == 0


def main():
    avant = SRC.read_bytes()
    tues = 0
    try:
        assert lancer(), "le banc doit être VERT avant les mutations"
        for i, (a, b) in enumerate(M, 1):
            s = avant.decode("utf-8")
            a2, b2 = (a.replace("\n", "\r\n"), b.replace("\n", "\r\n")) if "\r\n" in s and a not in s else (a, b)
            assert s.count(a2) == 1, (i, a, s.count(a2))
            SRC.write_bytes(s.replace(a2, b2).encode("utf-8"))
            vert = lancer()
            SRC.write_bytes(avant)
            tues += not vert
            print(f"{'TUÉE  ' if not vert else 'SURVIT'} M{i} {a[:70]!r}")
    finally:
        SRC.write_bytes(avant)
        print("restauré, identique :", SRC.read_bytes() == avant)
    print(f"{tues}/{len(M)} mutations tuées")
    sys.exit(0 if tues == len(M) else 1)


if __name__ == "__main__":
    main()
