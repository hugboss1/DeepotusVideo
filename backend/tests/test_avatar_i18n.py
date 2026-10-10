# -*- coding: utf-8 -*-
"""Avatar live G7 (t168, 10/10/2026) — l'écran Avatar live en français ET en anglais (règles de la traduction t134) :
dictionnaire frontend/shared/i18n/avatar.json (FR de référence, EN), textes fixes de la page traduits par la SURCOUCHE
(texte français exact), messages et <option> (que la surcouche ignore) passés par dzT. Le dictionnaire assemblé est
à jour et aucun texte français n'y reçoit deux traductions différentes (la surcouche n'en garderait qu'une).
Run (depuis backend/) : & $PY tests/test_avatar_i18n.py"""
import json, pathlib, re, subprocess, sys
from html.parser import HTMLParser
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


norm = lambda s: re.sub(r"\s+", " ", s).strip()
I18N = RACINE / "frontend" / "shared" / "i18n"
AV = json.loads((I18N / "avatar.json").read_text(encoding="utf-8"))
check("D1 chaque clé a son français et son anglais, non vides", all(v.get("fr") and v.get("en") for v in AV.values()))
check("D2 toutes les clés sont dans l'espace « avatar. »", all(k.startswith("avatar.") for k in AV))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True, text=True)
check("D3 le dictionnaire assemblé est à jour (i18n_assembler --check)", r.returncode == 0, r.stdout + r.stderr)
par_fr: dict = {}
for f in I18N.glob("*.json"):
    for k, v in json.loads(f.read_text(encoding="utf-8")).items():
        if not v.get("contexte"):
            par_fr.setdefault(norm(v["fr"]), set()).add(v["en"])
conflits = {fr: en for fr, en in par_fr.items() if len(en) > 1 and fr in {norm(v["fr"]) for v in AV.values()}}
check("D4 aucun texte français d'Avatar live n'a deux traductions dans l'ensemble des dictionnaires", not conflits, str(conflits))

print("\n[J] le code de l'écran")
js = "".join((RACINE / "frontend" / "avatar" / n).read_text(encoding="utf-8") for n in ("avatar.js", "direct.js"))
cles = set(re.findall(r'\bT\("(avatar\.[a-z_.]+)"', js)) | set(re.findall(r'\bT\((?:[^()]|\([^()]*\))*?"(avatar\.[a-z_.]+)"', js))
html = (RACINE / "frontend" / "avatar" / "index.html").read_text(encoding="utf-8")
cles |= set(re.findall(r'data-t="(avatar\.[a-z_.]+)"', html))
manquantes = sorted(c for c in cles if c not in AV and not c.endswith("."))
check(f"J1 les {len(cles)} clés employées (T, data-t) existent", not manquantes, str(manquantes))
check("J2 les statuts de job passent par avatar.job.<statut> (les huit sont au dictionnaire)",
      all(f"avatar.job.{s}" in AV for s in ("queued", "uploading_image", "generating_video", "downloading_video",
                                             "generating_voiceover", "merging", "done", "failed")))
reste = [m for m in re.findall(r'(?:dire|msg)\([^)]*?"([A-ZÀ-Ý][^"]{6,})"', js)]
check("J3 plus aucun message en dur dans dire()/msg()", not reste, str(reste[:5]))


class P(HTMLParser):
    def __init__(s): super().__init__(); s.out = []; s.pile = []
    def handle_starttag(s, tag, attrs):
        s.pile.append(tag)
        for k, v in attrs:
            if k in ("placeholder", "title", "aria-label") and v: s.out.append((tag, v))
    def handle_endtag(s, tag):
        if s.pile and s.pile[-1] == tag: s.pile.pop()
    def handle_data(s, d):
        d = norm(d)
        if d and not (set(s.pile) & {"script", "style", "option"}): s.out.append((s.pile[-1] if s.pile else "", d))


p = P(); p.feed(html)
fr_av = {norm(v["fr"]) for v in AV.values()}
NEUTRES = re.compile(r"^[\d\s:×.,()%-]*(min|s)?$|^…$|^—$|^dct_…$")
oublies = sorted({t for _tag, t in p.out if t not in fr_av and not NEUTRES.match(t)})
check("H1 chaque texte fixe de la page (et title/placeholder/aria-label) est au dictionnaire (la surcouche le traduit)",
      not oublies, str(oublies))
ordre = [m.group(1) for m in re.finditer(r'<script[^>]*src="([^"]+)"', html)]
check("H2 dictionnaire puis runtime AVANT tout autre script", ordre[:2] == ["/shared/dz-i18n-dico.js", "/shared/dz-i18n.js"], str(ordre))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
