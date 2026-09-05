# -*- coding: utf-8 -*-
"""P4 — ETALONNAGE DE BASE : quatre curseurs sous la LUT. Banc-MIROIR : on lit
la TRAME rendue par ffmpeg et la CHAINE de filtres reellement emise, jamais le
code qui pretend les produire. En-tete recopie de test_subs_animes.py (env,
_exe, check, sh, fixture, frame, mean_rgb) — moins ffprobe et subtitle_service :
rien ici ne sonde un flux ni ne grave un ASS.
Run : & $PY tests/test_montage_etalonnage.py   (depuis backend/)

CE QUI EST FERME ICI
  [1] le CATALOGUE : `grade_basic` existe, categorie « etalonnage », quatre
      parametres exactement (exposure, contrast, saturation, temperature) et
      leurs BORNES. C'est de la que viennent les curseurs du rack et la
      vignette d'apercu — mesure faite sur la charge utile REELLE de
      GET /api/effects/catalog (effects_preview.catalog_payload), pas sur la
      table brute : c'est elle que le panneau lit.
  [1-bis] la POSITION : `grade_basic` est juste apres `grade` dans le
      catalogue, donc juste sous la LUT dans le rack. « Sous la LUT » ne dit
      rien de l'ordre dans la CHAINE : dans la pile d'un clip, l'ordre est
      celui que l'utilisateur pose. Rien n'est affirme de plus.
  [2] la CHAINE emise, au caractere pres : `colortemperature` EN TETE et
      seulement hors de 6500 K, `eq` toujours et ensuite, les HUIT bornes
      ramenees (les quatre hautes ET les quatre basses), valeur illisible
      — `NaN` compris — retombant sur le defaut.
  [3] MIROIR A L'IMAGE, huit rendus ffmpeg sur le meme aplat bleu 0x2040a0 :
      exposition (haut et bas), contraste, saturation (nulle et double),
      temperature (chaude et froide), et le NEUTRE.
  [4] la VIGNETTE d'apercu : `render_preview` rend bien trois JPEG, et trois
      JPEG DIFFERENTS selon les reglages — sans serveur ni cle.

POURQUOI `colortemperature` EST OMIS A 6500 K — la mesure, pas l'intuition.
Le filtre n'est PAS l'identite a sa propre temperature de reference.

PROTOCOLE — il change le resultat d'un ordre de grandeur, donc il se NOMME.
Source yuv420p (celle du rendu : montage_service pose `format=yuv420p` avant
`build_chain`), DECODEE une fois de chaque cote, filtre applique en memoire,
sortie PNG rgb24. Aucun SECOND encodage : la perte du codec est commune aux
deux branches et s'annule. Mesure du 04/09/2026, ffmpeg 8.1.1-essentials du
PATH (celui que le service lance) — la VERSION se nomme, un encodeur n'est pas
l'autre. Deux sources 270x480 : l'aplat 0x2040a0 et une mire testsrc2,
trame a 0,5 s :

    filtre                | pixels changes | extremum/canal | couleurs
                          |                |                | deplacees
    eq neutre     (aplat) |      0/129 600 |      (0, 0, 0) |    0/1
    eq neutre     (mire)  |      0/129 600 |      (0, 0, 0) |    0/8 714
    ct=6500       (aplat) |129 600/129 600 |      (0, 1, 4) |    1/1
    ct=6500       (mire)  |110 299/129 600 |      (0, 1, 5) | 8 637/8 714

LE CHIFFRE QUI DIT LA CHOSE est la DERNIERE colonne, pas la premiere : sur un
aplat, « 129 600 pixels sur 129 600 » compte UNE couleur 129 600 fois, et le
nombre depend de la resolution. `colortemperature` a 6500 K deplace 99,1 % des
couleurs DISTINCTES de la mire ; le temoin `eq` neutre en deplace ZERO.
L'amplitude, elle, est minuscule : (0, 1, 5) au pire — ce n'est pas elle qui
chiffre ce filtre.

DEUX CORRECTIONS, gardees visibles.
  * Un « jusqu'a (82, 89, 99) par canal » a figure ici : il sortait d'un
    DOUBLE encodage h264 (rendu de V1 a travers le filtre en mp4 yuv420p, PUIS
    trame relue a 0,5 s). Re-mesure du 04/09/2026 sous ce protocole, sur la
    mire : le temoin `eq` neutre — exact au pixel — y prend (50, 41, 69) et
    36 931 pixels changes ; `ct=6500` y prend (74, 76, 83). Le (82, 89, 99)
    lui-meme NE SE REPRODUIT PAS : c'est un chiffre de plus dont le protocole
    n'avait pas ete dit. Ce qu'il chiffrait, de toute facon, c'est la perte de
    generation du codec, pas le filtre.
  * Un « TOUT le cadre » aussi : sur la mire c'est 85,1 % des pixels, pas
    100 %. Et le meme filtre mesure sur une source RGB fait apparaitre `eq`
    neutre comme NON identite. LA SOURCE RGB SE NOMME, parce que le COMPTE en
    depend : mire testsrc2 270x480 sortie de lavfi DIRECTEMENT en PNG rgb24,
    trame a 0,5 s, jamais encodee — 103 204/129 600 pixels changes, extremum
    (1, 1, 2). Ce qui NE depend pas de la source : la sortie de `eq` neutre y
    est identique OCTET POUR OCTET a celle d'un `format=yuv444p,format=rgb24`
    SEUL (verifie sur les quatre fabrications ci-dessous). C'est l'aller-retour
    que ffmpeg insere parce que `eq` ne s'execute pas en RGB ; l'arithmetique
    de `eq` n'y est pour rien. Le COMPTE, lui, bouge a chaque fabrication :
    meme mire decodee du mp4 yuv420p a 0,5 s, 97 555 ; trame 0 de lavfi,
    104 355 ; aplat 0x2040a0, 0/129 600 — un aplat traverse le yuv444p sans
    perte. RETRACTE : un « 104 015 » a figure ici sans que sa source soit
    nommee, et aucune des HUIT fabrications re-mesurees ne le rend (les quatre
    citees, plus testsrc2 sans `r` ni `d`, testsrc, smptebars, et la trame 0
    du mp4 yuv420p : 97 606). Un chiffre dont le protocole n'est pas dit n'est
    pas verifiable — c'est ce que ce paragraphe repare, pas seulement la
    valeur.

D'ou la regle : `eq` toujours emis, `colortemperature` seulement si k != 6500.
C'est ce que verrouillent `neutre_identique` (tolerance 0.5 : le neutre mesure
0.000 d'ecart, un `colortemperature=6500` emis en mettrait 3.000) et
`k6500_n_emet_pas_colortemperature`, double de `k3200_chaine_entiere` pour que
la premiere ne puisse pas etre verte a vide.

L'ORDRE EMIS : `colortemperature` D'ABORD, `eq` ensuite — l'ordre d'etalonnage
usuel (balance des blancs, puis exposition/contraste/saturation), et le seul ou
le curseur « saturation » reste une saturation. Mesure (meme protocole,
`saturation`=0 + 3200 K), distance moyenne au gris par pixel — d =
racine((R-m)^2 + (G-m)^2 + (B-m)^2), m = (R+G+B)/3, nulle si et seulement si
R=G=B : aplat, source 94,205, `eq` puis `ct` 24,042, `ct` puis `eq` 2,160 ;
mire, source 194,872, `eq` puis `ct` 46,151, `ct` puis `eq` 2,376. Avec `eq`
en tete, `saturation`=0 grise l'image et `colortemperature` la RE-TEINTE
aussitot : un sepia franc la ou l'utilisateur a demande du gris. Epingle au
caractere pres par `k3200_chaine_entiere` et `bornes_opposees_ramenees`.

CE QUE CE BANC N'AFFIRME PAS. Il ne touche pas au bundle : le bouton
« appliquer a tous les plans » (section M13) est mesure par
test_montage_bundle.py, cœur pur execute sous node compris. Et il ne dit rien
du repli du rack quand le backend est MUET : vfxrack.js retombe alors sur son
catalogue local `VFX_STATIC`, qui compte 20 effets quand `catalog()` en rend
40 — MESURE du 04/09/2026 — et dont le commentaire annonce encore « les 21
effets du moteur ». `grade_basic` n'est que l'un des VINGT manquants, et la
derive est ANTERIEURE a P4. (Sa liste de categories de repli en compte six,
dont trois — « couleur », « optique », « cadre » — n'existent plus cote
backend, qui en sert huit : etalonnage, retro, lumiere, atmosphere,
distorsion, mouvement, cadrage, stylisation.) Ce repli vit dans une source
patchee par un maillon AMONT (patch_bundle_vfxrack.py) que cette chaine ne
peut pas rejouer seule ; c'est un reste ASSUME, hors de cette tache.

LA REGLE DES ASSERTIONS NEGATIVES, PASSEE SUR CE BANC LE 05/09/2026. Elle
vient de l'en-tete de test_montage_media.py : un TEMOIN DISTINGUABLE, ou le
repli VIDE d'une garde, SE RETOURNE CONTRE TOUTE NEGATION. `a != b`,
`not (…)`, `x not in y`, `== []`, `== ""`, `is None` sont VRAIS PAR
CONSTRUCTION entre deux temoins comme sur un `{}` ou une `[]` de repli : la
ligne verdit sans avoir rien mesure. LA REGLE : toute assertion negative doit
d'abord exiger que ses operandes SOIENT ce qu'ils pretendent etre, et
seulement ensuite les comparer.

  L'ETAT VIDE DE CE BANC : `build_chain` ne rend PLUS RIEN, donc toute
  chaine de filtres est la chaine VIDE. C'est la « fixture non ecrite » de
  ce banc-ci — un effet qui ne serait plus enregistre :
      & $PY scratchpad/vide3.py tests/test_montage_etalonnage.py
  MESURE AVANT : 9 vertes. APRES les deux reparations : 7.
  LES DEUX REPAREES — et la seconde n'est meme pas une negation, c'est une
  EGALITE ENTRE DEUX OPERANDES CALCULES, l'autre face exacte du meme piege :
    * k6500_n_emet_pas_colortemperature — « n'emet pas X » est vrai d'une
      chaine vide. On exige d'abord que `k65` SOIT une chaine de
      `grade_basic` (le `eq=brightness=` que les quatre curseurs traversent
      tous), et seulement ensuite l'absence du filtre de temperature ;
    * valeur_illisible_retombe_sur_le_defaut — `mou == neutre` : deux
      chaines VIDES sont egales. On exige que `neutre` soit le neutre, ce
      que la premiere ligne de la section mesure deja et qui est REPRIS ici.
  LES SEPT VERTES A BON DROIT, UNE A UNE : catalogue_grade_basic,
  bornes_temperature, bornes_exposition, bornes_contraste_et_saturation,
  grade_basic_juste_sous_la_LUT, route_catalogue_sert_les_quatre_curseurs et
  categorie_etalonnage_compte_le_nouvel_effet — les sept lisent le CATALOGUE,
  pas la chaine, et le catalogue n'est pas touche par ce levier.
  DEJA CONFORME, ET C'EST DIT : les onze lignes de la section [3] portent
  toutes un `x is not None` en tete, parce que `render()` rend `None` sans
  lever quand ffmpeg echoue. La regle y etait deja appliquee ; les deux
  reparations ci-dessus ne concernent que la section [2].
"""
import os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp4_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def _exe(name):
    p = shutil.which(name)
    if p:
        return p
    cand = os.path.expandvars(rf"%LOCALAPPDATA%\DeepotusVideoGen\bin\{name}.exe")
    if os.path.isfile(cand):
        os.environ["PATH"] = os.path.dirname(cand) + os.pathsep + os.environ["PATH"]
        return cand   # la commande sous test lance un "ffmpeg" NU : il faut le PATH
    print(f"SKIP: {name} introuvable — le banc-miroir ne peut rien mesurer")
    sys.exit(0)


FF = _exe("ffmpeg")
from PIL import Image                                              # noqa: E402
from app.services.effects_engine import build_chain, catalog       # noqa: E402
from app.services import effects_preview as PV                     # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

def sh(cmd, timeout=240):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")

def fixture(label, cmd):
    """Une source qui ne se cree pas doit mourir ICI (meme garde-fou que P0)."""
    r = sh(cmd)
    if r.returncode:
        print(f"  ECHEC fixture {label} : {r.stderr[-400:]}")
        sys.exit(1)

V1 = os.path.join(TMP, "v1.mp4")
fixture("v1", [FF, "-y", "-v", "error", "-f", "lavfi", "-i",
               "color=c=0x2040a0:s=270x480:r=30:d=4", "-pix_fmt", "yuv420p", V1])

def frame(path, t):
    png = os.path.join(TMP, f"f_{os.path.basename(path)}_{t}.png")
    sh([FF, "-y", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", png])
    return Image.open(png).convert("RGB")

def mean_rgb(im, box=None):
    if box: im = im.crop(box)
    px = list(im.getdata()); n = float(len(px))
    return tuple(round(sum(p[i] for p in px) / n, 2) for i in range(3))


CTX = {"w": 270, "h": 480, "dur": 4.0, "fps": 30}

def chain(eff):
    """La chaine que le rendu ET la vignette d'apercu emettront pour cet effet."""
    return ";".join(build_chain([eff], "0:v", "vout", "u", CTX))

def render(eff, name):
    """Rend 1 s de V1 a travers `eff`. Rend None SANS lever : un ffmpeg qui
    echoue doit faire ROUGIR le banc, jamais le faire MOURIR au milieu — les
    assertions suivantes lisent `None` et se gardent."""
    out = os.path.join(TMP, name + ".mp4")
    g = chain(eff)
    r = sh([FF, "-y", "-v", "error", "-i", V1, "-filter_complex", g,
            "-map", "[vout]", "-t", "1", "-pix_fmt", "yuv420p", out])
    if r.returncode:
        check("rendu_" + name, False, g + " :: " + (r.stderr or "")[-200:])
        return None
    return out

def ycc(path):
    """Moyenne YCbCr de la trame a 0,5 s. Y porte l'exposition et le contraste,
    Cb/Cr la saturation et la temperature : trois nombres, trois curseurs."""
    if path is None:
        return None
    im = frame(path, 0.5).convert("YCbCr")
    px = list(im.getdata()); n = float(len(px))
    return tuple(round(sum(p[i] for p in px) / n, 3) for i in range(3))

def ycc_of(eff, name):
    return ycc(render(eff, name))

def rgb_of(eff, name):
    p = render(eff, name)
    return None if p is None else mean_rgb(frame(p, 0.5))

def fmt(t):
    """Detail SUR : une mesure absente s'ecrit « n/a », elle ne leve pas. Un
    `f"{t[0]:.1f}"` sur un rendu rate tuait le banc au lieu de le rougir."""
    return "n/a" if t is None else "(" + ", ".join(f"{v:.3f}" for v in t) + ")"

def chroma_d(t):
    """Distance au gris dans le plan Cb/Cr : LA mesure de la saturation."""
    return None if t is None else ((t[1] - 128.0) ** 2 + (t[2] - 128.0) ** 2) ** 0.5


# =============================================================================
print("\n[1] le CATALOGUE — d'ou viennent les curseurs et la vignette")
# =============================================================================
cat = catalog()
spec = cat.get("grade_basic")
check("catalogue_grade_basic",
      bool(spec) and spec.get("params") == ["exposure", "contrast", "saturation",
                                            "temperature"]
      and spec.get("cat") == "etalonnage",
      str(spec))

B = (spec or {}).get("bounds") or {}
t = B.get("temperature") or {}
check("bornes_temperature",
      t.get("type") == "range" and t.get("min") == 2000 and t.get("max") == 12000
      and t.get("step") == 100 and t.get("default") == 6500 and t.get("unit") == "K",
      str(t))
e = B.get("exposure") or {}
check("bornes_exposition",
      e.get("type") == "range" and e.get("min") == -100 and e.get("max") == 100
      and e.get("default") == 0, str(e))
c_, s_ = B.get("contrast") or {}, B.get("saturation") or {}
check("bornes_contraste_et_saturation",
      c_.get("min") == 0 and c_.get("max") == 200 and c_.get("default") == 100
      and s_.get("min") == 0 and s_.get("max") == 200 and s_.get("default") == 100,
      f"contraste={c_} saturation={s_}")
# « sous la LUT » : la POSITION dans le rack, et rien d'autre.
keys = list(cat.keys())
check("grade_basic_juste_sous_la_LUT",
      "grade" in keys and "grade_basic" in keys
      and keys.index("grade_basic") == keys.index("grade") + 1,
      str(keys[:4]))
# La charge utile REELLE de GET /api/effects/catalog : c'est elle que
# vfxrack.js lit (`bounds` par effet) pour dessiner les quatre curseurs, et
# c'est elle qui nomme l'effet dans la vignette d'apercu. Sans cette ligne, le
# banc benirait un catalogue interne que la route n'expose pas.
pay = PV.catalog_payload()
peff = (pay.get("effects") or {}).get("grade_basic") or {}
check("route_catalogue_sert_les_quatre_curseurs",
      sorted((peff.get("bounds") or {}).keys())
      == ["contrast", "exposure", "saturation", "temperature"]
      and peff.get("label") == "Réglages de base",
      str(peff.get("label")) + " " + str(sorted((peff.get("bounds") or {}).keys())))
# Le compte de la categorie « Étalonnage » du rack suit le catalogue : mesure
# AVANT P4 = 5 (grade, colorize, invert, posterize + l'alias lut), donc 6.
_eta = [c for c in pay.get("categories") or [] if c.get("id") == "etalonnage"]
check("categorie_etalonnage_compte_le_nouvel_effet",
      len(_eta) == 1 and _eta[0].get("count") == 6, str(_eta))


# =============================================================================
print("\n[2] la CHAINE emise — au caractere pres")
# =============================================================================
neutre = chain({"type": "grade_basic"})
_NEUTRE = "[0:v]eq=brightness=0.000:contrast=1.000:saturation=1.000[vout]"
check("defauts_neutres_emettent_eq_seul", neutre == _NEUTRE, neutre)
k65 = chain({"type": "grade_basic", "temperature": 6500})
# « n'emet pas X » EST VRAI D'UNE CHAINE VIDE. MESURE le 05/09/2026 (banc
# relance avec `build_chain` rendant `[]`, `scratchpad/vide3.py`) : VERTE
# alors que l'effet n'emettait plus rien du tout. On exige donc d'abord que
# `k65` SOIT une chaine de `grade_basic` — le `eq` que les quatre curseurs
# traversent tous — et seulement ensuite qu'elle ne porte pas le filtre de
# temperature.
check("k6500_n_emet_pas_colortemperature",
      "eq=brightness=" in k65 and "colortemperature" not in k65, k65)
k32 = chain({"type": "grade_basic", "temperature": 3200})
# La chaine ENTIERE hors neutre, et pas un `in`. DEUX mesures y tiennent.
# (a) L'ORDRE : `colortemperature` D'ABORD. Avec `eq` en tete, `saturation`=0
#     grise l'image et `colortemperature` la RE-TEINTE aussitot — mesure du
#     04/09/2026, distance moyenne au gris par pixel (protocole dans la
#     docstring de _grade_basic) : sur l'aplat 24,042 dans l'ordre `eq` puis
#     `ct` contre 2,160 dans l'ordre inverse ; sur la mire 46,151 contre
#     2,376. RIEN ne gardait cet ordre : `defauts_neutres_emettent_eq_seul`
#     n'epingle la chaine entiere que dans le cas ou `colortemperature` n'est
#     PAS emis, et deplacer le filtre en tete y laissait le banc a 20/0.
# (b) Le FORMAT du nombre : `"…=3200"` est un PREFIXE de `"…=3200.0"`, donc
#     l'ancien `in` laissait retirer le `int()` sans rougir.
check("k3200_chaine_entiere",
      k32 == "[0:v]colortemperature=temperature=3200,"
             "eq=brightness=0.000:contrast=1.000:saturation=1.000[vout]", k32)
# Les bornes ne sont pas decoratives : une valeur venue du client ne doit pas
# atteindre la ligne de commande telle quelle.
hors = chain({"type": "grade_basic", "exposure": 999, "contrast": -50,
              "saturation": 999, "temperature": 99})
check("valeurs_hors_bornes_ramenees",
      hors == "[0:v]colortemperature=temperature=2000,"
              "eq=brightness=0.500:contrast=0.000:saturation=2.000[vout]", hors)
# Les QUATRE bornes OPPOSEES. Le cas ci-dessus n'en exerce qu'une sur deux :
# elargir `brightness` par le BAS, `contrast` ou `saturation` par le HAUT, ou
# la temperature par le HAUT laissait le banc entierement vert.
bas = chain({"type": "grade_basic", "exposure": -999, "contrast": 999,
             "saturation": -5, "temperature": 99999})
check("bornes_opposees_ramenees",
      bas == "[0:v]colortemperature=temperature=12000,"
             "eq=brightness=-0.500:contrast=2.000:saturation=0.000[vout]", bas)
# Une valeur ILLISIBLE retombe sur le defaut. Sans _num, build_chain attraperait
# la ValueError et emettrait un `null` : l'effet disparaitrait EN SILENCE.
# `NaN` est du lot, et il est ATTEIGNABLE : `json.loads("NaN")` le rend nu, et
# une comparaison `<`/`>` sur NaN est fausse dans les DEUX sens — sans la
# garde `v != v` de _num il traverserait les bornes et sortirait en
# « brightness=nan » sur la ligne de commande.
mou = chain({"type": "grade_basic", "exposure": "abc", "temperature": None,
             "contrast": float("nan")})
# EGALITE ENTRE DEUX CHAINES CALCULEES : deux chaines VIDES sont egales, et
# la ligne verdit sans rien mesurer (meme mesure que ci-dessus, meme etat).
# `neutre` doit d'abord ETRE le neutre — c'est la premiere ligne de la
# section, reprise ici plutot que supposee.
check("valeur_illisible_retombe_sur_le_defaut",
      neutre == _NEUTRE and mou == neutre, mou)


# =============================================================================
print("\n[3] MIROIR A L'IMAGE — huit rendus sur l'aplat bleu 0x2040a0")
# =============================================================================
base = ycc(V1)
base_rgb = mean_rgb(frame(V1, 0.5))
print(f"  source V1 : YCbCr {fmt(base)}  RGB {fmt(base_rgb)}")

# Le neutre ne doit pas changer UN OCTET. Mesure : ecart 0.000 sur les trois
# canaux. Tolerance a 0.5 — dix fois moins que l'ecart qu'un
# `colortemperature=6500` emis y mettrait (Y 3.000, Cb 1.992).
ref = ycc_of({"type": "grade_basic"}, "neutre")
check("neutre_identique",
      ref is not None and all(abs(a - b) < 0.5 for a, b in zip(ref, base)),
      f"{fmt(ref)} vs {fmt(base)}")

# Exposition. Mesure : +60 -> Y 152.000 (source 64.000), -60 -> Y 8.000.
# Seuil a 25, soit moins du tiers de l'ecart mesure dans les deux sens.
e60 = ycc_of({"type": "grade_basic", "exposure": 60}, "expo_p60")
check("exposition_eclaircit", e60 is not None and e60[0] > base[0] + 25,
      f"Y {fmt(e60)} vs {fmt(base)}")
em60 = ycc_of({"type": "grade_basic", "exposure": -60}, "expo_m60")
check("exposition_negative_assombrit", em60 is not None and em60[0] < base[0] - 25,
      f"Y {fmt(em60)} vs {fmt(base)}")

# Contraste. Mesure : contrast=0 -> Y 128.000 PILE (source 64.000), Cb et Cr
# inchanges (181.000 / 104.000) — eq n'ecrase que la luma. Tolerance 1.0.
c0 = ycc_of({"type": "grade_basic", "contrast": 0}, "contr0")
check("contraste_zero_aplatit_la_luma_vers_le_gris",
      c0 is not None and abs(c0[0] - 128.0) < 1.0
      and abs(c0[1] - base[1]) < 1.0 and abs(c0[2] - base[2]) < 1.0,
      f"{fmt(c0)} vs {fmt(base)}")

# Saturation. Mesure : 0 -> Cb 126.000 / Cr 127.000 (distance au gris 2.24,
# source 58.18) ; 200 -> Cb 233.000 / Cr 81.000 (distance 115.04).
s0 = ycc_of({"type": "grade_basic", "saturation": 0}, "sat0")
check("saturation_zero_gris",
      s0 is not None and abs(s0[1] - 128) < 4 and abs(s0[2] - 128) < 4, fmt(s0))
s200 = ycc_of({"type": "grade_basic", "saturation": 200}, "sat200")
check("saturation_double_eloigne_du_gris",
      s200 is not None and chroma_d(s200) > chroma_d(base) + 20,
      f"{chroma_d(s200)} vs {chroma_d(base)}")

# Temperature CHAUDE : mesure, R-B passe de -128.00 a -46.97, soit 81.03 de
# plus. Seuil a 20, un quart de la mesure.
w = rgb_of({"type": "grade_basic", "temperature": 3200}, "chaud")
check("temperature_chaude_rougit",
      w is not None and (w[0] - w[2]) > (base_rgb[0] - base_rgb[2]) + 20,
      f"{fmt(w)} vs {fmt(base_rgb)}")
# Temperature FROIDE : sur un bleu deja sature, R-B ne bouge presque pas
# (-135.97 contre -128.00, huit points) — c'est le RAPPORT bleu/rouge qui
# porte la mesure : 7.466 contre 5.129, soit 2.337 de plus. Seuil a 1.0.
cold = rgb_of({"type": "grade_basic", "temperature": 12000}, "froid")
_r0 = base_rgb[2] / max(base_rgb[0], 1e-6)
_r1 = None if cold is None else cold[2] / max(cold[0], 1e-6)
check("temperature_froide_bleuit", _r1 is not None and _r1 > _r0 + 1.0,
      f"B/R {_r1} vs {_r0} — {fmt(cold)} vs {fmt(base_rgb)}")


# =============================================================================
print("\n[4] la VIGNETTE d'apercu — trois rendus DISTINCTS, sans serveur")
# =============================================================================
# P4 declarait « ce banc ne rend AUCUNE vignette ». C'etait la seule
# affirmation qu'il refusait de faire alors qu'il importait deja `PV` : quatre
# lignes la referment, sans serveur ni cle. `render_preview` partage
# `build_chain` avec le rendu (chaine deja mesuree en [2]) ; ce qui restait
# non mesure, c'est qu'elle produise vraiment un JPEG, et un JPEG DIFFERENT
# par reglage.
# LES TAILLES NE SONT PLUS PUBLIEES ICI, et c'est le point. Elles ne sont
# assertees par RIEN — elles dependent de la version de ffmpeg et de son
# encodeur JPEG, et un banc qui les epinglerait rougirait a la premiere mise a
# jour sans qu'un seul octet de ce depot ait bouge. Mais un chiffre que rien
# ne garde PERIME EN SILENCE, et c'est arrive ici : celui du milieu, republie
# tel quel, datait d'AVANT l'inversion `colortemperature`/`eq` du meme commit.
# Des trois reglages, il est le SEUL dont la chaine porte deux filtres — les
# deux autres n'emettent que `eq` (la temperature reste a 6500 K, donc omise),
# donc aucun ordre n'existe pour eux et leurs tailles, elles, n'avaient pas
# bouge. Ce que ce banc asserte : trois fichiers, signature JPEG, deux a deux
# DIFFERENTS. Le detail de l'assertion imprime les tailles DU JOUR quand elle
# rougit — c'est la qu'il faut les lire, pas dans un commentaire.
_vg = []
for _lbl, _prm in (("neutre", {}),
                   ("chaud+expo", {"temperature": 3200, "exposure": 60}),
                   ("saturation nulle", {"saturation": 0})):
    try:
        _vg.append((_lbl, PV.render_preview("grade_basic", _prm, source="mire",
                                            t=1.0, width=160).read_bytes()))
    except Exception as _e:            # noqa: BLE001 — on ROUGIT, on ne meurt pas
        _vg.append((_lbl, b""))
        print(f"  (vignette {_lbl} : {type(_e).__name__} {_e})")
check("vignette_rend_trois_jpeg_distincts",
      len(_vg) == 3 and all(b[:2] == b"\xff\xd8" for _l, b in _vg)
      and len({b for _l, b in _vg}) == 3,
      " ".join(f"{_l}={len(b)}o" for _l, b in _vg))


shutil.rmtree(TMP, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
