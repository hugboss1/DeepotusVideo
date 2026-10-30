# -*- coding: utf-8 -*-
"""Mutations t380 (30/10/2026) : les fils sociaux suivis de News (services/news_fils.py, api/news_fils_routes.py,
news_service._refresh_blocking, outil d'agent proposer_fil). Chaque mutation doit faire ÉCHOUER son banc
(backend/tests/test_news_fils.py). Les fichiers sont copiés AVANT, restaurés après chaque mutation et comparés octet à
octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_fils.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_fils_"))
F = {"nf": RACINE / "backend/app/services/news_fils.py", "rt": RACINE / "backend/app/api/news_fils_routes.py",
     "ns": RACINE / "backend/app/services/news_service.py", "ao": RACINE / "backend/app/services/agent_outils.py",
     "ab": RACINE / "backend/app/services/agent_boites.py", "sc": RACINE / "backend/app/models/schemas.py"}
for k, p in F.items(): shutil.copy2(p, SAUVE / (k + ".orig"))
SERVEUR = [sys.executable, "tests/test_news_fils.py"]
M = [
 # ── identifiants ──
 ("nf", SERVEUR, 'if not m or not (s == m.group(1) or "youtube.com" in s.lower()):', 'if not m:'),
 ("nf", SERVEUR, 'r"^[A-Za-z0-9_]{3,21}$" if sorte == "r"', 'r"^[A-Za-z0-9_]{1,21}$" if sorte == "r"'),
 ("nf", SERVEUR, 'sorte = "u" if sorte in ("u", "user") else "r"', 'sorte = "r"'),
 ("nf", SERVEUR, '"x": re.compile(r"^[A-Za-z0-9_]{1,15}$")', '"x": re.compile(r"^[A-Za-z0-9_ !]{1,16}$")'),
 ("nf", SERVEUR, '    "reddit": {"libelle": "Reddit", "lecture": "rss"},', '    "reddit": {"libelle": "Reddit", "lecture": "rss"},\n    "linkedin": {"libelle": "LinkedIn", "lecture": "rss"},'),
 ("nf", SERVEUR, 'f"https://www.youtube.com/feeds/videos.xml?channel_id={ident}"', 'f"https://www.youtube.com/channel/{ident}"'),
 # ── fils ──
 ("nf", SERVEUR, '        if any(f.get("id") == fid for f in fils):', '        if False:'),
 ("nf", SERVEUR, '    if isinstance(v, bool) or not isinstance(v, int) or v not in FREQUENCES_H:', '    if isinstance(v, bool) or not isinstance(v, int):'),
 ("nf", SERVEUR, '"origine": origine or {"type": "main"}', '"origine": {"type": "main"}'),
 ("nf", SERVEUR, '"etat": "devis_a_accepter" if apify else "jamais_lu"', '"etat": "jamais_lu"'),
 ("nf", SERVEUR, '        champs["pause"] = bool(corps["pause"])', '        champs["pause"] = False'),
 # ── éléments ──
 ("nf", SERVEUR, '        texte = _REDDIT_RESTES.sub("", _REDDIT_AUTEUR.sub("", texte or ""))', '        pass'),
 ("nf", SERVEUR, '        lien = SU._lien_sans_pseudo(str(SU._champ(it, champs["url"]) or ""))[:500]', '        lien = str(SU._champ(it, champs["url"]) or "")[:500]'),
 ("nf", SERVEUR, '        premiere = next((l.strip() for l in texte.splitlines() if l.strip()), "")', '        premiere = texte'),
 ("nf", SERVEUR, '"plateforme": f["plateforme"]})', '})'),
 ("nf", SERVEUR, '    actifs = {f["id"] for f in _fils() if not f.get("pause")}', '    actifs = {f["id"] for f in _fils()}'),
 ("nf", SERVEUR, '    _fusionner_cache(fid, [])\n', ''),
 ("nf", SERVEUR, '    _garder_items(fid, items)\n    _fusionner_cache(fid, items)\n', '    _garder_items(fid, items)\n'),
 ("ns", SERVEUR, "            items.extend(news_fils.items_actifs())", "            pass"),
 ("sc", SERVEUR, "    plateforme: Optional[str] = None            # t380", "    # t380"),
 # ── relevé payant ──
 ("nf", SERVEUR, '        return "x", {"searchTerms": [f"from:{h}"], "sort": "Latest"}', '        return "x", {"searchTerms": [h], "sort": "Latest"}'),
 ("nf", SERVEUR, '    if isinstance(plafond_usd, bool) or not isinstance(plafond_usd, (int, float)) or not 0 < plafond_usd <= maxi:', '    if isinstance(plafond_usd, bool) or not isinstance(plafond_usd, (int, float)):'),
 ("nf", SERVEUR, '    if confirme_cout is not True:', '    if False:'),
 ("nf", SERVEUR, '    if d > float(plafond_usd):', '    if False:'),
 ("nf", SERVEUR, '    if not AP.configure():\n        raise RefusFil(', '    if False:\n        raise RefusFil('),
 ("nf", SERVEUR, '        if not accord:\n', '        if not accord and False:\n'),
 ("nf", SERVEUR, '        if d > accord["plafond_usd"]:', '        if False:'),
 ("nf", SERVEUR, 'r = await AP.lancer(cle, entree, f["max"], plafond=accord["plafond_usd"])', 'r = await AP.lancer(cle, entree, f["max"])'),
 ("nf", SERVEUR, '            await plafonds.noter_reel_lignes(lignes, perdu)\n', ''),
 ("nf", SERVEUR, '        await plafonds.noter_reel_lignes(lignes, cout)\n', ''),
 ("nf", SERVEUR, '"usd": d}, "news",', '"usd": d}, "campagnes",'),
 ("nf", SERVEUR, 'cout_cumule_usd=round(float(f.get("cout_cumule_usd") or 0) + perdu, 6))', 'cout_cumule_usd=f.get("cout_cumule_usd"))'),
 # ── boucle ──
 ("nf", SERVEUR, '        if f.get("pause"):\n            continue\n', ''),
 ("nf", SERVEUR, '        if f["lecture"] == "apify" and not f.get("accord"):', '        if False:'),
 ("nf", SERVEUR, '        if not _du(f, maintenant):\n            continue\n', ''),
 ("nf", SERVEUR, 'return maintenant - datetime.fromisoformat(t) >= timedelta(hours=f["frequence_h"])', 'return maintenant - datetime.fromisoformat(t) >= timedelta(hours=24)'),
 ("nf", SERVEUR, '            _modifier(fid, etat="sans_cle")\n', ''),
 # ── suggestions ──
 ("nf", SERVEUR, '    if lire_fil(fid) is not None:\n        return {"statut": "deja_suivi"', '    if False:\n        return {"statut": "deja_suivi"'),
 ("nf", SERVEUR, '                if s.get("etat") == "ecartee":', '                if False:'),
 ("nf", SERVEUR, '                if s.get("etat") == "proposee":\n                    return', '                if False:\n                    return'),
 ("nf", SERVEUR, 'origine=s.get("origine"))', 'origine=None)'),
 ("nf", SERVEUR, '    _decider(sid, etat="acceptee", fil_id=f["id"])', '    pass'),
 ("ao", SERVEUR, '"cadre": pour, "conversation": ctx.cid,', '"cadre": pour, "conversation": None,'),
 ("ao", SERVEUR, '    if r["statut"] == "deja_suivi":', '    if False:'),
 ("ab", SERVEUR, '        "outils": ["proposer_fil"],\n        "agents": ["campagnes"],', '        "outils": ["proposer_fil"],\n        "agents": ["mcp"],'),
 # ── routes ──
 # (retirer les gardes de POST /{fid}/lire est ÉQUIVALENT : un téléphone appairé reçoit déjà 403 du garde des écritures
 # du compagnon, avant la route ; le banc 2l le vérifie quand même)
 ("rt", SERVEUR, '@router.get("", dependencies=[Depends(_local)])', '@router.get("")'),
 ("rt", SERVEUR, '        raise HTTPException(503, str(e)) from None', '        raise HTTPException(400, str(e)) from None'),
 ("rt", SERVEUR, '        raise HTTPException(502, str(e)) from None', '        raise HTTPException(500, str(e)) from None'),
]
tues = 0
try:
  for i, (k, banc, a, b) in enumerate(M, 1):
    p = F[k]; s = p.read_bytes().decode("utf-8")
    if "\r\n" in s:
        a, b = a.replace("\n", "\r\n"), b.replace("\n", "\r\n")
    assert s.count(a) == 1, (i, a, s.count(a))
    p.write_bytes(s.replace(a, b).encode("utf-8"))
    r = subprocess.run(banc, cwd=RACINE / "backend", capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    for k2, p2 in F.items(): shutil.copy2(SAUVE / (k2 + ".orig"), p2)
    ok = r.returncode != 0; tues += ok
    print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {k}: {a[:70]!r}", flush=True)
finally:
  for k, p in F.items(): shutil.copy2(SAUVE / (k + ".orig"), p)
  print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items()))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
