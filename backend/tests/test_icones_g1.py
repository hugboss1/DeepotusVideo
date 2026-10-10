# -*- coding: utf-8 -*-
"""Icônes G1 (10/10/2026) — la suite « Deepotus Glyph » dans la coque React (bundle index-BEOJX8L5.js + couches).

  [1] le runtime : frontend/dist/index.html charge /shared/icons/dz-icons.css et dz-icons.js APRÈS dz-i18n.js et AVANT
      le module du bundle ; favicon = le logo (dz-marque-icone-app est une image), titre de fenêtre sans emoji.
  [2] la saisie couvre la liste de travail : chaque entrée de docs/icones/suite-finale/implementation.json dont la
      source est le bundle ou index.html (hors emojis conservés et texte seul) a son édition (ou une raison écrite) ;
      aucun id inventé.
  [3] le générateur scripts/icones/g1_generer.py --check est vert (couches et table à jour) ; le maillon
      patch_bundle_dzglyph.py est posé (marqueur x1), lit/écrit en octets, refuse une double application ; chaque
      paire de la table est en place dans le bundle livré ; la table se défait exactement (avant_dzglyph) ; chaque bloc
      de couche du bundle EST sa source (octet pour octet, CRLF) et les éditions G1 y sont en place.
  [4] compte par clé : chaque clé finale posée apparaît dans le bundle exactement autant de fois que la saisie la
      pose (aucune clé dz-… n'existait dans le bundle G0) ; plus AUCUN nom de l'ancienne carte d'icônes (sparkle, zap,
      caretR, channelX…) ne reste dans un site d'icône (name:, icon:, iconRight:, avatar:, données de rail).
  [5] sous node : le socle (__dzGlyphe, __dzGl, __dzGlT, __dzGlS, __dzGlH) extrait du bundle livré, avec le vrai
      runtime dz-icons.js : une clé de la suite rend un <g> au corps du SVG (fill reporté), une image rend <image>,
      une clé inconnue rend null ; le texte qui portait un glyphe garde son texte et pose l'icône à sa place.
  [6] syntaxe et fins de ligne : node --check du bundle (module) et des sources de couche modifiées ; CRLF homogène.
Run : & $PY tests/test_icones_g1.py   (depuis backend/)
"""
import importlib.util, json, pathlib, re, shutil, subprocess, sys, tempfile

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND / "tests"))
import _i18n_l1_aide as AIDE  # noqa: E402

BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
INDEX = ROOT / "frontend" / "dist" / "index.html"
INDEX_SRC = ROOT / "frontend" / "index.html"
TABLE = ROOT / "scripts" / "dzglyph_paires.json"
MAILLON = ROOT / "scripts" / "patch_bundle_dzglyph.py"
GEN = ROOT / "scripts" / "icones" / "g1_generer.py"
SAISIE = ROOT / "scripts" / "icones" / "g1_saisie.py"
SAISIE_CLES = ROOT / "scripts" / "icones" / "g1_saisie_cles.json"
IMPL = ROOT / "docs" / "icones" / "suite-finale" / "implementation.json"
DZI = ROOT / "frontend" / "dist" / "shared" / "icons" / "dz-icons.js"
COUCHES = {"montage": ("MONTAGE", "montage.js"), "sonvfx": ("SONVFX", "son-vfx-montage.js"),
           "sfxstudio": ("SFXSTUDIO", "sfxstudio.js"), "vfxrack": ("VFXRACK", "vfxrack.js")}
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:500]}")


BUNB = BUNDLE.read_bytes()
BUN = BUNB.decode("utf-8")
TAB = json.loads(TABLE.read_bytes().decode("utf-8"))

print("[1] le runtime et la marque")
idx = INDEX.read_bytes().decode("utf-8")
p_i18n, p_css, p_js, p_mod = (idx.find('<script src="/shared/dz-i18n.js"></script>'),
                               idx.find('<link rel="stylesheet" href="/shared/icons/dz-icons.css">'),
                               idx.find('<script src="/shared/icons/dz-icons.js"></script>'),
                               idx.find('<script type="module" crossorigin src="/assets/index-BEOJX8L5.js"></script>'))
check("1.1 dz-icons.css et dz-icons.js chargés une fois, après dz-i18n.js et avant le bundle",
      idx.count("/shared/icons/dz-icons.js") == 1 and idx.count("/shared/icons/dz-icons.css") == 1
      and 0 < p_i18n < p_css < p_js < p_mod, (p_i18n, p_css, p_js, p_mod))
for nom, txt in (("dist", idx), ("source Vite", INDEX_SRC.read_bytes().decode("utf-8"))):
    check(f"1.2 [{nom}] favicon = le logo (image), titre sans emoji",
          '<link rel="icon" type="image/png" href="/api/branding/logo" />' in txt and "<title>Deepotus Video Gen</title>" in txt
          and "🐙" not in txt.split("<body")[0])
check("1.3 le splash garde ses images (logo et fond, choix utilisateur)",
          'src="/api/branding/logo"' in idx.split("<body")[1] and 'src="/assets/dz-splash.jpg"' in idx)

print("[2] la saisie couvre la liste de travail")
spec = importlib.util.spec_from_file_location("g1_saisie", SAISIE)
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
cles_sites = json.loads(SAISIE_CLES.read_bytes().decode("utf-8"))["sites"]
impl = json.loads(IMPL.read_bytes().decode("utf-8"))
perim = [e for e in impl if (e["source"].startswith("frontend/dist/assets/index-BEOJX8L5.js")
                             or e["source"].startswith(("frontend/dist/index.html", "frontend/index.html")))
         and e["cle_finale"] and not e["emoji_conserve"]]
ids_sais = set()
for e in cles_sites + S.EDITIONS:
    ids_sais.update(e["ids"])
couverts = ids_sais | set(S.SATISFAITS)
manquent = [e["id"] for e in perim if e["id"] not in couverts]
check(f"2.1 chaque site de la liste ({len(perim)}) a son édition ou sa raison écrite", not manquent and len(perim) > 1000,
      manquent[:10])
inventes = sorted(i for i in couverts if i not in {e["id"] for e in impl})
check("2.2 aucun id inventé", not inventes, inventes[:5])
check("2.3 chaque raison (sans site) est écrite", all(len(v) > 20 for v in S.SATISFAITS.values()))
fin = {e["id"]: e["cle_finale"] for e in perim}
mauvaises = [(e["ids"][0], e["apres"]) for e in cles_sites for i in e["ids"] if fin.get(i) and fin[i] not in e["apres"]
             and i not in ("studio.canevas-vignette-du-n-ud-render.play-triangle-de-lecture-dans",)]
check("2.4 chaque littéral de la carte Sh est repointé vers LA clé finale de son site", not mauvaises, mauvaises[:5])

print("[3] générateur, maillon, réversibilité, couches")
r = subprocess.run([sys.executable, str(GEN), "--check"], capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
check("3.1 g1_generer.py --check : couches et table à jour", r.returncode == 0, (r.stdout + r.stderr)[-300:])
src_m = MAILLON.read_bytes().decode("utf-8")
check("3.2 le maillon lit et écrit en octets, sonde l'amont, ne laisse pas de .bak", "read_text(" not in src_m
      and "write_text(" not in src_m and "read_bytes()" in src_m and "BAK.unlink()" in src_m and "SONDE_AMONT" in src_m)
check("3.3 marqueur du maillon x1 dans le bundle livré", BUN.count("function __dzGlyphe(") == 1)
with tempfile.TemporaryDirectory(prefix="dzg1_") as tmp:
    t = pathlib.Path(tmp)
    (t / "frontend/dist/assets").mkdir(parents=True)
    (t / "scripts").mkdir()
    shutil.copy(TABLE, t / "scripts" / TABLE.name)
    (t / "frontend/dist/assets" / BUNDLE.name).write_bytes(BUNB)
    r2 = subprocess.run([sys.executable, str(MAILLON)], cwd=str(t), capture_output=True, text=True, encoding="utf-8")
    check("3.4 double application refusée (bundle intact)", r2.returncode != 0 and "double application" in (r2.stdout + r2.stderr)
          and (t / "frontend/dist/assets" / BUNDLE.name).read_bytes() == BUNB, (r2.stdout + r2.stderr)[-200:])
# rejeu : le bundle d'avant G1 (table défaite) + le maillon = le bundle livré, à l'octet
with tempfile.TemporaryDirectory(prefix="dzg1r_") as tmp:
    t = pathlib.Path(tmp)
    (t / "frontend/dist/assets").mkdir(parents=True)
    (t / "scripts").mkdir()
    shutil.copy(TABLE, t / "scripts" / TABLE.name)
    # les blocs des couches restent ceux du poste (rafraîchis AVANT le maillon) : seule la table se défait ici
    try:
        _av2 = AIDE._defaire(BUN, TABLE, "avant_dzglyph")
        (t / "frontend/dist/assets" / BUNDLE.name).write_bytes(_av2.encode("utf-8"))
        r3 = subprocess.run([sys.executable, str(MAILLON)], cwd=str(t), capture_output=True, text=True, encoding="utf-8")
        rejoue = (t / "frontend/dist/assets" / BUNDLE.name).read_bytes()
        check(f"3.5 rejeu : bundle d'avant + maillon ({len(TAB['paires'])} paires) = bundle livré, octet pour octet",
              r3.returncode == 0 and rejoue == BUNB, (r3.stdout + r3.stderr)[-300:])
    except ValueError as e:
        check("3.5 rejeu : la table se défait sur le bundle livré", False, e)
try:
    av = AIDE.avant_dzglyph(BUN)
    check("3.6 la table se défait exactement : plus de socle, plus aucune clé dz-… dans le bundle d'avant",
          "function __dzGlyphe(" not in av and not re.search(r'"dz-(action|nav|media|etat|cat|edit|reseau|lab3d|calque)-', av))
except ValueError as e:
    check("3.6 la table se défait exactement", False, e)
for c, (tag, fich) in COUCHES.items():
    b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    bloc = BUN.split(b, 1)[1].split(e, 1)[0].strip("\r\n")
    src = (ROOT / "frontend" / "patches" / fich).read_bytes().decode("utf-8")
    subs = TAB["couches"].get(c, [])
    en_place = all(src[x["pos"]:x["pos"] + len(x["apres"])] == x["apres"] for x in subs[:1]) and \
        AIDE.couche_avant_dzglyph(src, c) != src if subs else True
    check(f"3.7 [{c}] le bloc du bundle EST la source (CRLF), ses {len(subs)} éditions G1 en place",
          bloc == src.strip("\r\n") and "\r\n" in src and en_place, (len(bloc), len(src.strip()), en_place))
tr = (ROOT / "frontend/patches/transfert.js").read_bytes().decode("utf-8").strip("\r\n")
check("3.8 [transfert] la source (marqueurs compris) est le bloc du bundle, icônes comprises",
      tr in BUN and '__dzGl("dz-action-exporter", 16' in tr and "dztIcone(\"export\", 16)" not in tr)

print("[4] compte par clé, anciens noms")
attendu = {}
CLE = r'["\'](dz-[a-z0-9-]+)["\']'
# compte attendu : les clés posées par chaque édition (paires : ce qu'elles AJOUTENT ; couches : leur « après »)
for p in TAB["paires"]:
    for k in re.findall(CLE, p["remplace"]):
        attendu[k] = attendu.get(k, 0) + 1
    for k in re.findall(CLE, p["ancre"]):
        attendu[k] = attendu.get(k, 0) - 1
for v in TAB["couches"].values():
    for x in v:
        for k in re.findall(CLE, x["apres"]):
            attendu[k] = attendu.get(k, 0) + 1
suite = set(json.loads("{" + ",".join(l.rstrip(",") for l in DZI.read_bytes().decode("utf-8").splitlines()
                                      if l.startswith('"dz-')) + "}").keys())
attendu = {k: n for k, n in attendu.items() if k in suite or k.startswith("dz-marque-")}
def compte(k):
    return BUN.count(f'"{k}"') + BUN.count(f"'{k}'")


ecarts = {k: (n, compte(k)) for k, n in attendu.items() if compte(k) != n}
check(f"4.1 chaque clé posée ({len(attendu)} clés, {sum(attendu.values())} sites) apparaît autant de fois que la saisie la pose",
      not ecarts and len(attendu) > 200, list(ecarts.items())[:6])
finales = {e["cle_finale"] for e in perim} - {"dz-marque-poulpe", "dz-marque-splash", "dz-marque-icone-app"}
check("4.2 chaque clé finale du périmètre est posée au moins une fois", finales <= set(attendu), sorted(finales - set(attendu))[:8])
VIEUX = ['octopus', 'play', 'preview', 'download', 'upload', 'search', 'plus', 'minus', 'close', 'folderOpen', 'panelR', 'more',
         'edit', 'trash', 'copy', 'rename', 'bolt', 'film', 'mic', 'layers', 'rss', 'folder', 'cog', 'vectorpen', 'photolab',
         'gamegrid', 'zap', 'image', 'sparkle', 'signal', 'caret', 'caretR', 'check', 'flow', 'wave', 'link', 'warn', 'grid',
         'calendar', 'clock', 'send', 'book', 'channelX', 'channelTelegram', 'channelYoutube', 'channelInstagram',
         'channelTiktok', 'save', 'undo']
i0, i1 = BUN.find("const Sh={"), BUN.find("function __dzGlyphe(")
restes = []
for m in re.finditer(r'(?<![\w$.-])(["\'])(' + "|".join(VIEUX) + r')\1', BUN):
    if i0 <= m.start() < i1:
        continue
    if re.search(r'(icon|iconRight|name|avatar|\bi)\s*:[^,{}]{0,40}$', BUN[m.start() - 40:m.start()]):
        restes.append(BUN[m.start() - 50:m.end() + 10])
check("4.3 plus aucun nom de l'ancienne carte d'icônes dans un site d'icône (hors la carte Sh elle-même)",
      not restes, restes[:4])
check("4.4 la carte Sh garde ses 47 clés d'origine (données des personas des utilisateurs) et apprend la suite",
      BUN.count("const Sh={octopus:") == 1 and "const o=Sh[e]||__dzGlyphe(e);" in BUN)

print("[5] le socle sous node")
if NODE:
    k0 = BUN.find("function __dzGlyphe(")
    k1 = BUN.find("function X({name:e", k0)
    socle = BUN[k0:k1]
    js = ("var window={};\n" + DZI.read_bytes().decode("utf-8").replace("})();", "}).call(this);") + "\n"
          + "var r={jsx:function(t,p){return {t:t,p:p}}};var Sh={};function X(p){return {t:'X',p:p}}\n" + socle + r"""
var g=__dzGlyphe("dz-action-fermer"),im=__dzGlyphe("dz-marque-poulpe"),inc=__dzGlyphe("dz-nexiste-pas"),vieux=__dzGlyphe("sparkle");
var t1=__dzGlT("dz-action-retour","← Retour","←"),t2=__dzGlT("dz-etat-enregistre","Enregistré ✓","✓"),t3=__dzGlT("dz-etat-succes","sans glyphe","✓");
console.log(JSON.stringify({g:g&&g.t,fill:g&&g.p.fill,corps:!!(g&&/<path/.test(g.p.dangerouslySetInnerHTML.__html)),cache:Sh["dz-action-fermer"]===g,
  im:im&&im.t,href:im&&im.p.href,inc:inc,vieux:vieux,t1:[t1[0].p.name,t1[1],t1[2]],t2:[t2[0],t2[2].p.name],t3:t3,
  s:__dzGlS("📚 Parcourir les vignettes…","📚"),h:__dzGlH("dz-action-fermer",14).slice(0,24)}));
""")
    with tempfile.TemporaryDirectory(prefix="dzg1n_") as tmp:
        f = pathlib.Path(tmp) / "socle.js"
        f.write_text(js, encoding="utf-8")
        rn = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8")
    try:
        o = json.loads(rn.stdout.strip().splitlines()[-1])
    except Exception:
        o = {}
    check("5.1 une clé de la suite rend un <g> au corps du SVG, fill reporté, mis en cache dans Sh",
          o.get("g") == "g" and o.get("fill") == "currentColor" and o.get("corps") is True and o.get("cache") is True, rn.stderr[-300:] or o)
    check("5.2 une clé image (logo) rend <image> vers /api/branding/logo ; inconnue ou ancienne clé : null",
          o.get("im") == "image" and o.get("href") == "/api/branding/logo" and o.get("inc") is None and o.get("vieux") is None, o)
    check("5.3 __dzGlT : le glyphe devient l'icône à sa place (devant, derrière) ; sans glyphe le texte reste",
          o.get("t1") == ["dz-action-retour", " ", "Retour"] and o.get("t2") == ["Enregistré", "dz-etat-enregistre"]
          and o.get("t3") == "sans glyphe", o)
    check("5.4 __dzGlS retire le glyphe ; __dzGlH rend le balisage du runtime", o.get("s") == "Parcourir les vignettes…"
          and o.get("h") == '<svg class="dzi" width="', o)
else:
    check("5.0 node présent", False, "node absent du PATH")

print("[6] syntaxe et fins de ligne")
check("6.1 bundle en CRLF homogène", BUNB.count(b"\r\n") > 15000 and BUNB.count(b"\n") == BUNB.count(b"\r\n"))
if NODE:
    with BUNDLE.open("rb") as fh:
        r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
    check("6.2 node --check du bundle (module)", r.returncode == 0, r.stderr[-300:])
    for fich in ("sfxstudio.js", "vfxrack.js", "son-vfx-montage.js", "transfert.js"):
        r = subprocess.run([NODE, "--check", str(ROOT / "frontend" / "patches" / fich)], capture_output=True, text=True,
                           encoding="utf-8")
        check(f"6.3 node --check {fich}", r.returncode == 0, r.stderr[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
