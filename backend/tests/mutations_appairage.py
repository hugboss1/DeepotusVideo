# -*- coding: utf-8 -*-
"""Banc de mutations du compagnon mobile (partie PC) : casser -> rouge -> remettre.

PAS UN TEST : son nom ne commence pas par `test_`, donc pytest ne le collecte pas et run-tests.ps1 ne le liste pas.
Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_appairage.py            # toutes
    python tests/mutations_appairage.py 3 17       # celles-la (numeros de la liste, a partir de 1)

Il MUTE les sources du depot une a une et les REMET a l'octet pres (assertion sha256, meme en cas d'exception) : il ne se
lance donc pas pendant qu'un autre banc lit ces fichiers. Chaque mutation nomme le banc qu'elle doit faire rougir et
l'etiquette de l'assertion visee ; une VERTE est une assertion qui manque.

Difference avec mutations_plaque_slicer.py : les bancs de l'appairage sont AUTO-EXECUTANTS (`python tests/test_x.py`) et
impriment `  PASS  <etiquette> ...` / `  FAIL  <etiquette> ...`, la ou pytest imprime FAILED. On lit donc ces lignes, et
l'on garde le TROISIEME etat : un banc qui n'a imprime aucun bilan (import casse, syntaxe, plantage) n'est pas vert, il
est CASSE (ERREUR) -- le lire comme « aucun FAIL » en ferait une fausse verte.

Sortie : une ligne `ROUGE|VERTE|ERREUR <n> <fichier> <intention>` par mutation, puis un bilan. Code 0 si TOUTES sont ROUGES.
Les ancres ne contiennent jamais de saut de ligne (l'arbre peut etre en CRLF) : chacune est une ligne unique du fichier.
"""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
MAIN = "backend/app/main.py"
ROUTES = "backend/app/api/routes.py"
APP = "backend/app/services/appairage.py"
IDX = "backend/app/services/sync_index.py"
LOT = "backend/app/services/sync_lot.py"
EVT = "backend/app/services/sync_evenements.py"
VER = "backend/app/services/sync_verrou.py"

B_APP, B_ROU = "test_appairage.py", "test_appairage_routes.py"
B_LOT, B_MAN, B_DEP = "test_sync_lot.py", "test_sync_manifeste.py", "test_sync_depenses.py"
B_EVT, B_VER, B_P1 = "test_sync_evenements.py", "test_sync_verrou.py", "test_p1_garde_localhost.py"

_OUV = "_ECRITURES_OUVERTES: frozenset = frozenset({(\"POST\", \"/api/pair/claim\"), (\"POST\", \"/api/sync/lot/etat\"),"
_OUV_PLUS = ("_ECRITURES_OUVERTES: frozenset = frozenset({(\"POST\", \"/api/cost/pricing\"), "
             "(\"POST\", \"/api/pair/claim\"), (\"POST\", \"/api/sync/lot/etat\"),")

# (fichier relatif au depot, ancre = UNE ligne exacte, remplacement, banc, etiquettes attendues rouges, intention)
M = [
    # -- la garde de jeton (main.py) --------------------------------------------------------------------------------
    (MAIN, "    if not await _appairage.jeton_valide(jeton):", "    if False:",
     B_ROU, ["G2", "G3", "G4"], "_device_token_guard laisse passer le reseau local sans jeton"),
    (MAIN, "_ROUTES_SANS_JETON = {\"/api/pair/claim\"}", "_ROUTES_SANS_JETON = {\"/api/pair/claim\", \"/api/jobs\"}",
     B_ROU, ["G2"], "une route de plus se passe de jeton"),
    (MAIN, "    jeton = entete[7:].strip() if entete[:7].lower() == \"bearer \" else \"\"", "    jeton = entete.strip()",
     B_ROU, ["J2"], "la garde accepte un jeton sans le mot Bearer"),
    # -- un jeton revoque -------------------------------------------------------------------------------------------
    (APP, "        res = await session.execute(_select(Device.jeton_sha256).where(Device.revoque.is_(None)))",
     "        res = await session.execute(_select(Device.jeton_sha256))",
     B_APP, ["R1", "R5"], "un jeton revoque reste accepte par la garde"),
    (APP, "    _ACTIFS_A = 0.0", "    pass",
     B_APP, ["R1"], "la revocation ne vide plus le cache : elle attend le TTL"),
    # -- les ecritures ouvertes au Wi-Fi ----------------------------------------------------------------------------
    (MAIN, _OUV, _OUV_PLUS, B_P1, ["4.5"], "_ECRITURES_OUVERTES gagne POST /api/cost/pricing (banc de la garde locale)"),
    (MAIN, _OUV, _OUV_PLUS, B_VER, ["F7"], "_ECRITURES_OUVERTES gagne POST /api/cost/pricing (banc du verrou)"),
    (MAIN, _OUV, _OUV_PLUS, B_DEP, ["A2"], "_ECRITURES_OUVERTES gagne POST /api/cost/pricing (banc des depenses)"),
    (MAIN, _OUV, _OUV_PLUS, B_MAN, ["D14"], "_ECRITURES_OUVERTES gagne POST /api/cost/pricing (banc du depot)"),
    # -- l'appareil vient du jeton, jamais du corps -----------------------------------------------------------------
    (ROUTES, "        return await _sd.fondre(appareil, (body or {}).get(\"tirs\") if isinstance(body, dict) else None)",
     "        return await _sd.fondre({\"id\": str((body or {}).get(\"appareil\") or appareil[\"id\"]), \"nom\": appareil[\"nom\"]}, "
     "(body or {}).get(\"tirs\") if isinstance(body, dict) else None)",
     B_DEP, ["F2"], "sync_depenses prend l'appareil du CORPS au lieu du jeton"),
    (IDX, "    rec.update({\"appareil\": {\"id\": appareil[\"id\"], \"nom\": appareil[\"nom\"]}, \"sha256\": vrai,",
     "    rec.update({\"appareil\": rec.get(\"appareil\") or {\"id\": appareil[\"id\"], \"nom\": appareil[\"nom\"]}, \"sha256\": vrai,",
     B_MAN, ["D4"], "le depot garde l'appareil de la recette (corps) au lieu de celui du jeton"),
    # -- le secret d'appairage --------------------------------------------------------------------------------------
    (APP, "    if fiche[\"expire_a\"] < time.time():", "    if False:",
     B_APP, ["S4"], "le secret d'appairage n'expire plus"),
    (APP, "DUREE_SECRET_S = 300          # 5 minutes (R12 réponse 11)", "DUREE_SECRET_S = 3000         # 5 minutes (R12 réponse 11)",
     B_APP, ["S1"], "le secret d'appairage vit 50 minutes au lieu de 5"),
    (APP, "    _SECRETS.pop(secret, None)                  # USAGE UNIQUE", "    pass                                        # USAGE UNIQUE",
     B_APP, ["S3"], "le secret d'appairage est reutilisable"),
    (APP, "        if len(res.all()) >= MAX_APPAREILS:", "        if False:",
     B_APP, ["R4"], "la limite de cinq appareils saute"),
    (APP, "MAX_APPAREILS = 5             # « jusqu'à cinq appareils nommés »", "MAX_APPAREILS = 50            # « jusqu'à cinq appareils nommés »",
     B_APP, ["R4"], "la limite de cinq appareils passe a cinquante"),
    (APP, "                          jeton_sha256=hashlib.sha256(jeton.encode()).hexdigest(), cree=datetime.utcnow())",
     "                          jeton_sha256=jeton, cree=datetime.utcnow())",
     B_APP, ["J1", "J2"], "le jeton est stocke en clair au lieu de son sha256"),
    # -- /api/sync/depot --------------------------------------------------------------------------------------------
    (IDX, "    if vrai != str(empreinte or \"\").strip().lower():", "    if False:",
     B_MAN, ["D6"], "/api/sync/depot accepte un sha256 qui ne correspond pas"),
    (ROUTES, "        if fmt not in _UPLOAD_IMAGE_FORMATS:", "        if False:",
     B_MAN, ["D7"], "/api/sync/depot saute la garde Pillow"),
    # -- sync_lot ---------------------------------------------------------------------------------------------------
    (LOT, "            elif p.delegue_a != moi:", "            elif False:",
     B_LOT, ["E7"], "sync_lot rend un post posted/failed/rendu sans verifier delegue_a"),
    (LOT, "            if p.delegue_a and p.delegue_a != moi:", "            if False:",
     B_LOT, ["E4"], "sync_lot laisse un autre appareil emporter un post confie"),
    (LOT, "            if p.status == \"posted\":", "            if False:",
     B_LOT, ["R3"], "sync_lot ecrase un post deja publie par le PC"),
    # -- sync_verrou ------------------------------------------------------------------------------------------------
    (ROUTES, "    await _sv.garde(chapter_id)          # tâche #59 : un chapitre emporté par le téléphone n'est pas écrasé (423)",
     "    pass                                 # tâche #59 : un chapitre emporté par le téléphone n'est pas écrasé (423)",
     B_VER, ["G1"], "sync_verrou laisse un PUT modifier un chapitre emporte"),
    (ROUTES, "            emportes = await _sv.verrouilles()      # tâche #59 : un chapitre emporté par un téléphone est laissé tel quel",
     "            emportes = set()                        # tâche #59 : un chapitre emporté par un téléphone est laissé tel quel",
     B_VER, ["G4"], "le re-import du manuscrit ecrase un chapitre emporte"),
    (VER, "        if v is None or v.device_id != appareil[\"id\"]:", "        if False:",
     B_VER, ["R1"], "rendre un chapitre sans en avoir le verrou est accepte"),
    # -- sync_evenements --------------------------------------------------------------------------------------------
    (EVT, "        q = _select(JobRecord).where(JobRecord.status.in_((\"done\", \"failed\"))).where(JobRecord.completed_at.is_not(None))",
     "        q = _select(JobRecord).where(JobRecord.status.in_((\"completed\", \"failed\"))).where(JobRecord.completed_at.is_not(None))",
     B_EVT, ["R1"], "sync_evenements filtre sur completed au lieu de done"),
]

_FIN = re.compile(r"^\s*(\d+ ok, \d+ fail|\d+ PASS / \d+ FAIL)\s*$", re.M)


def lire(banc):
    """(etiquettes FAIL, sortie, erreur?) d'un banc auto-executant. ERREUR = aucun bilan imprime (3e etat)."""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY, f"tests/{banc}"], capture_output=True, cwd=R / "backend", timeout=900, env=env)
    txt = (p.stdout + p.stderr).decode("utf-8", "replace")
    echecs = set(re.findall(r"^\s*FAIL\s+(\S+)", txt, re.M))
    erreur = not _FIN.search(txt) and not echecs
    return echecs, txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus, intention) in enumerate(M, 1):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        sha_avant = hashlib.sha256(src).hexdigest()
        brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert "\n" not in old, (i, "ancre multi-ligne")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:70])
        p.write_bytes(txt.replace(old, new).replace("\n", eol).encode("utf-8"))
        try:
            echecs, sortie, erreur = lire(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        if erreur:
            verdict = "ERREUR"
            print(sortie[-1500:], file=sys.stderr)
        elif echecs:
            verdict = "ROUGE"
        else:
            verdict = "VERTE"
        manquants = [a for a in attendus if a not in echecs]
        note = f"  (rouge, mais pas sur {manquants})" if verdict == "ROUGE" and manquants else ""
        bilan.append((i, rel, banc, verdict, sorted(echecs), manquants))
        print(f"{verdict} {i} {rel} {intention} [{banc} -> {sorted(echecs)}]{note}")
        sys.stdout.flush()
    n = {v: sum(1 for b in bilan if b[3] == v) for v in ("ROUGE", "VERTE", "ERREUR")}
    print(f"\n{len(bilan)} mutation(s) : {n['ROUGE']} ROUGE, {n['VERTE']} VERTE, {n['ERREUR']} ERREUR")
    for b in bilan:
        if b[3] != "ROUGE":
            print(f"  {b[3]} [{b[0]}] {b[1]} -- banc {b[2]}, attendait {b[5] or b[4]}")
    print(json.dumps([b[:4] for b in bilan], ensure_ascii=False))
    return 0 if bilan and n["ROUGE"] == len(bilan) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
