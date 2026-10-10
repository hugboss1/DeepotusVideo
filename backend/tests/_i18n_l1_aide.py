"""t141 — aides des bancs pour la traduction L1 (coque, Réglages, Bibliothèque passées par dzT).

  avant_i18n(bundle)      le bundle tel qu'il était AVANT la traduction L1 : la table du maillon patch_bundle_i18n_l1
                          défaite (paires inversées, dans l'ordre inverse) et le bloc MONTAGE ramené à la couche
                          d'avant (substitutions de la saisie défaites). Sans git : marche aussi dans l'app installée.
                          t142 : la table du maillon L2 (patch_bundle_i18n_l2) est défaite d'abord.
  avant_i18n_l2(bundle)   le bundle d'avant la seule traduction L2 (L1 toujours posée).
                          Pour les bancs qui vérifient qu'un patcher AMONT a livré sa section (« remplacement x1 ») :
                          la section est contrôlée telle que le patcher l'a posée ; test_i18n_l1 garantit que la
                          traduction posée par-dessus est exactement réversible.
  couche_avant_i18n(c)    la couche frontend/patches/montage.js d'avant la traduction L1.
  avant_i18n_l4(bundle)   t144 : le bundle dont les blocs SFXSTUDIO, VFXRACK, SONVFX sont ramenés aux couches d'avant L4
                          (avant_i18n le fait aussi, en premier).
  couche_avant_i18n_l4(texte, cible)  t144 : une des trois couches (sfxstudio, vfxrack, sonvfx) d'avant L4.
  PRELUDE_DZT             code JS à placer AVANT la couche ou le bundle exécutés sous node : window.DZ_I18N (le
                          dictionnaire assemblé) et dzT(clé, vars) en FRANÇAIS, la langue de référence — les attentes
                          en français des bancs restent vraies.
  fr(cle, **vars)         le texte français d'une clé (pour les bancs qui épinglent un libellé).
  avant_dzglyph(bundle)   icônes G1 (maillon de queue patch_bundle_dzglyph, APRÈS L1/L2/L4) : sa table défaite et les
                          blocs des quatre couches (montage, sonvfx, sfxstudio, vfxrack) ramenés à leur source d'avant G1.
                          Chaque « avant_* » ci-dessus commence par là : les icônes se défont AVANT les traductions.
  couche_avant_dzglyph(texte, cible)  une couche (« montage », « sonvfx »… ou son nom de fichier) d'avant G1 ; un texte
                          qui ne porte pas G1 (déjà défait, ou plus ancien) est rendu tel quel.
  couche_avant_i18n_l3(c) / avant_i18n_l3(bundle)  t143 : la couche montage (ou le bloc MONTAGE) d'avant L3 ; G1, posé
                          APRÈS L3 (BASE de g1_generer = la couche traduite), y est GARDÉ, recalé en positions d'avant
                          L3 : la vue est la couche de main d'avant L3, à l'octet. couche_avant_dzglyph défait G1 dans
                          les deux vues (couche traduite, ou d'avant L3).
"""
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))

_TABLE = RACINE / "scripts" / "i18n_l1_paires.json"
_TABLE2 = RACINE / "scripts" / "i18n_l2_paires.json"     # t142 : la table du maillon L2, défaite avant celle de L1
_DICO_JS = RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js"


def _dico():
    d = {}
    for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        d.update(json.loads(f.read_text("utf-8")))
    return d


DICO = _dico()


def fr(cle, **vars):
    s = DICO[cle]["fr"]
    for k, v in vars.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def _couche_defaire(couche: str, table, nom) -> str:
    """Défait les substitutions « couche » d'une table (positions dans la couche de BASE de ce lot, aux fins de ligne
    du poste) ; dans la couche actuelle, chacune est décalée de la somme des écarts de celles qui la précèdent.
    `couche` peut être en LF ou en CRLF : on rend la même forme."""
    if not table.is_file():
        return couche
    subs = json.loads(table.read_bytes().decode("utf-8")).get("couche", [])
    crlf = "\r\n" in couche
    s = couche if crlf else couche.replace("\n", "\r\n")
    decal, morceaux, k = 0, [], 0
    for e in sorted(subs, key=lambda x: x["pos"]):
        p = e["pos"] + decal
        if s[p:p + len(e["apres"])] != e["apres"]:
            raise ValueError(f"{nom} : la substitution {e['groupe']}@{e['pos']} n'est pas à sa place ({s[p:p + 40]!r})")
        morceaux.append(s[k:p] + e["avant"])
        k = p + len(e["apres"])
        decal += len(e["apres"]) - len(e["avant"])
    morceaux.append(s[k:])
    r = "".join(morceaux)
    return r if crlf else r.replace("\r\n", "\n")


_TABLE3 = RACINE / "scripts" / "i18n_l3_paires.json"   # t143 : la couche montage.js traduite par-dessus L2


def _subs3():
    return json.loads(_TABLE3.read_bytes().decode("utf-8"))["couches"].get("montage", []) if _TABLE3.is_file() else []


def _sans_g1_ni_l3(couche: str) -> str:
    """La couche montage d'avant G1 ET d'avant L3 (L1 et L2 posées) : G1 se défait d'abord (sa table est en positions
    de la couche traduite), puis L3."""
    couche = couche_avant_dzglyph(couche, "montage")
    if 'dzT("montage.' not in couche or not _subs3():
        return couche
    return _couche_defaire_subs(couche, _subs3(), "couche L3")


def _g1_avant_l3():
    """Les éditions G1 de la couche montage ramenées en positions de la couche d'AVANT L3 : décalées des
    substitutions L3 qui les précèdent ; une substitution L3 contenue dans une édition G1 (« + piste vidéo »
    devenu dzT(...) puis __dzGlT(…, dzT(...), "+")) y est remise en français."""
    t = _table_g()
    gsubs = (t or {}).get("couches", {}).get("montage", [])
    l3c, cum = [], 0
    for s in sorted(_subs3(), key=lambda x: x["pos"]):
        l3c.append((s["pos"] + cum, s))
        cum += len(s["apres"]) - len(s["avant"])
    out = []
    for e in gsubs:
        a, b = e["pos"], e["pos"] + len(e["avant"])
        delta, avant, apres = 0, e["avant"], e["apres"]
        for p, s in l3c:
            q = p + len(s["apres"])
            if q <= a:
                delta += len(s["apres"]) - len(s["avant"])
            elif p >= b:
                break
            else:
                if not (a <= p and q <= b):
                    raise ValueError(f"G1/L3 : édition G1 à cheval sur une substitution L3 ({e['ids'][:1]})")
                avant = avant.replace(s["apres"], s["avant"], 1)
                apres = apres.replace(s["apres"], s["avant"], 1)
        out.append({"pos": a - delta, "avant": avant, "apres": apres, "ids": e["ids"], "groupe": "dzglyph"})
    return out


def couche_avant_i18n_l3(couche: str) -> str:
    """t143 : la couche frontend/patches/montage.js d'avant la seule traduction L3 (L1 et L2 posées). Une couche
    qui ne porte pas L3 (aucun dzT("montage.") : le .bak reconstruit, une base) est rendue telle quelle.
    Icônes G1 (posées APRÈS L3) : une couche qui les porte les GARDE (recalées sur la couche d'avant L3, comme les
    bancs qui exécutent la couche et attendent « ⟦clé⟧ ») ; couche_avant_dzglyph sait les défaire dans cette vue."""
    sans = _sans_g1_ni_l3(couche)
    if couche_avant_dzglyph(couche, "montage") == couche:
        return sans                                # pas de G1 : L3 seule défaite (ou rien)
    crlf = "\r\n" in sans
    s = sans if crlf else sans.replace("\n", "\r\n")
    for e in sorted(_g1_avant_l3(), key=lambda x: -x["pos"]):
        if s[e["pos"]:e["pos"] + len(e["avant"])] != e["avant"]:
            raise ValueError(f"couche L3 : édition G1 {e['ids'][:1]} introuvable dans la couche d'avant L3")
        s = s[:e["pos"]] + e["apres"] + s[e["pos"] + len(e["avant"]):]
    return s if crlf else s.replace("\r\n", "\n")


def couche_avant_i18n_l2(couche: str) -> str:
    """t142 : la couche frontend/patches/montage.js d'avant la seule traduction L2 (L1 toujours posée).
    t143 : G1 puis L3 se défont d'abord."""
    return _couche_defaire(_sans_g1_ni_l3(couche), _TABLE2, "couche L2")


def avant_i18n_l3(bundle: str) -> str:
    """t143 : le bundle dont le bloc MONTAGE est ramené à la couche d'avant L3 (L1 et L2 posées). LF ou CRLF."""
    if "/*__DZ_MONTAGE_BEGIN__*/" not in bundle:
        return bundle
    return _bloc(bundle, couche_avant_i18n_l3)    # icônes G1 gardées si le bundle les porte (couche_avant_i18n_l3)


def couche_avant_i18n(couche: str) -> str:
    """La couche d'avant toute traduction : L2 défaite (t142), puis L1."""
    return _couche_defaire(couche_avant_i18n_l2(couche), _TABLE, "couche")


def avant_i18n(bundle: str) -> str:
    """Accepte le bundle en CRLF (lu en octets) ou en LF (lu par read_text, qui aplatit les fins de ligne) et rend la
    même forme : la table porte des CRLF (une paire contient un retour de ligne littéral)."""
    if "\r\n" not in bundle:
        return _avant_crlf(bundle.replace("\n", "\r\n")).replace("\r\n", "\n")
    return _avant_crlf(bundle)


def _defaire(s, table, nom):
    for p in reversed(json.loads(table.read_bytes().decode("utf-8"))["paires"]):
        c = s.count(p["remplace"])
        if c != 1:
            raise ValueError(f"{nom} : remplacement x{c} : {p['remplace'][:80]!r}")
        s = s.replace(p["remplace"], p["ancre"], 1)
    return s


def _bloc(s, f):
    """Le bundle `s` dont le cœur du bloc MONTAGE passe par f (bords du bloc conservés)."""
    b, e = "/*__DZ_MONTAGE_BEGIN__*/", "/*__DZ_MONTAGE_END__*/"
    head, rest = s.split(b, 1)
    bloc, tail = rest.split(e, 1)
    lead = bloc[:len(bloc) - len(bloc.lstrip("\r\n"))]
    trail = bloc[len(bloc.rstrip("\r\n")):]
    return head + b + lead + f(bloc.strip("\r\n")) + trail + e + tail


def _avant_l2_crlf(bundle: str) -> str:
    bundle = avant_dzglyph(bundle)                 # icônes G1 : le maillon de queue dzglyph, posé APRÈS L4
    bundle = avant_i18n_l4(bundle)                 # t144 : les blocs des couches son, traduits APRÈS L2
    if not _TABLE2.is_file():
        return bundle
    return _bloc(_defaire(bundle, _TABLE2, "avant_i18n_l2"), couche_avant_i18n_l2)


def avant_i18n_l2(bundle: str) -> str:
    """Le bundle d'avant la seule traduction L2 (t142), L1 toujours posée : table du maillon L2 défaite et bloc MONTAGE
    ramené à la couche de L1. LF ou CRLF : on rend la même forme."""
    if "\r\n" not in bundle:
        return _avant_l2_crlf(bundle.replace("\n", "\r\n")).replace("\r\n", "\n")
    return _avant_l2_crlf(bundle)


def _avant_crlf(bundle: str) -> str:
    s = _avant_l2_crlf(bundle)                     # t142 : L2 se défait d'abord (maillon posé APRÈS L1) ; t144 : L4 avant
    s = _defaire(s, _TABLE, "avant_i18n")
    return _bloc(s, lambda c: _couche_defaire(c, _TABLE, "couche"))


# t144 — traduction L4 : les trois couches sfxstudio, vfxrack, son-vfx-montage (blocs SFXSTUDIO, VFXRACK, SONVFX du
# bundle) passent par dzT ; scripts/i18n_l4_paires.json garde, couche par couche, les substitutions de la saisie
_TABLE4 = RACINE / "scripts" / "i18n_l4_paires.json"
_BLOCS4 = {"sfxstudio": "SFXSTUDIO", "vfxrack": "VFXRACK", "sonvfx": "SONVFX"}
_FICHIERS4 = {"sfxstudio.js": "sfxstudio", "vfxrack.js": "vfxrack", "son-vfx-montage.js": "sonvfx"}


def _defaire4(texte: str, cible: str, nom: str) -> str:
    """Défait les substitutions L4 d'une couche (positions de la couche de BASE ecf945e4, CRLF)."""
    if not _TABLE4.is_file():
        return texte
    subs = json.loads(_TABLE4.read_bytes().decode("utf-8"))["couches"].get(cible, [])
    return _couche_defaire_subs(texte, subs, nom)


def _couche_defaire_subs(couche, subs, nom):
    crlf = "\r\n" in couche
    s = couche if crlf else couche.replace("\n", "\r\n")
    decal, morceaux, k = 0, [], 0
    for e in sorted(subs, key=lambda x: x["pos"]):
        p = e["pos"] + decal
        if s[p:p + len(e["apres"])] != e["apres"]:
            raise ValueError(f"{nom} : la substitution {e['groupe']}@{e['pos']} n'est pas à sa place ({s[p:p + 40]!r})")
        morceaux.append(s[k:p] + e["avant"])
        k = p + len(e["apres"])
        decal += len(e["apres"]) - len(e["avant"])
    morceaux.append(s[k:])
    r = "".join(morceaux)
    return r if crlf else r.replace("\r\n", "\n")


def couche_avant_i18n_l4(texte: str, cible: str) -> str:
    """t144 : la couche `cible` (« sfxstudio », « vfxrack », « sonvfx », ou le nom de fichier « sfxstudio.js »…)
    d'avant la traduction L4. Accepte le texte du fichier (BOM toléré) ou le cœur du bloc du bundle ; LF ou CRLF :
    on rend la même forme."""
    cible = _FICHIERS4.get(cible, cible)
    texte = couche_avant_dzglyph(texte, cible)     # icônes G1, posées APRÈS L4
    bom = texte[:1] == "﻿"
    r = _defaire4(texte[1:] if bom else texte, cible, f"couche {cible} L4")
    return ("﻿" + r) if bom else r


def avant_i18n_l4(bundle: str) -> str:
    """Le bundle dont les blocs SFXSTUDIO, VFXRACK et SONVFX sont ramenés aux couches d'avant L4 (bords conservés)."""
    s = avant_dzglyph(bundle)
    for cible, tag in _BLOCS4.items():
        b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
        if b not in s:
            continue
        head, rest = s.split(b, 1)
        bloc, tail = rest.split(e, 1)
        lead = bloc[:len(bloc) - len(bloc.lstrip("\r\n"))]
        trail = bloc[len(bloc.rstrip("\r\n")):]
        coeur = bloc.strip("\r\n")
        # un bloc encore en français (le .bak_montage reconstruit depuis le bundle du commit d'avant L4) est rendu tel quel
        if 'dzT("' + {"sfxstudio": "sfx", "vfxrack": "vfx", "sonvfx": "son"}[cible] + "." in coeur:
            coeur = couche_avant_i18n_l4(coeur, cible)
        s = head + b + lead + coeur + trail + e + tail
    return s


# icônes G1 — le maillon de queue patch_bundle_dzglyph (table scripts/dzglyph_paires.json : ses paires, et les éditions
# faites DANS les sources des quatre couches rafraîchissables, positions dans la source de base, CRLF)
_TABLE_G = RACINE / "scripts" / "dzglyph_paires.json"
_MARQUE_G = "function __dzGlyphe("
_BLOCS_G = {"montage": "MONTAGE", "sonvfx": "SONVFX", "sfxstudio": "SFXSTUDIO", "vfxrack": "VFXRACK"}
_FICHIERS_G = {"montage.js": "montage", "son-vfx-montage.js": "sonvfx", "sfxstudio.js": "sfxstudio",
               "vfxrack.js": "vfxrack"}


def _table_g():
    return json.loads(_TABLE_G.read_bytes().decode("utf-8")) if _TABLE_G.is_file() else None


def couche_avant_dzglyph(texte: str, cible: str) -> str:
    """La couche `cible` d'avant les icônes G1. Accepte le fichier (BOM toléré) ou le cœur du bloc ; LF ou CRLF : on
    rend la même forme. Un texte qui ne porte pas G1 (sa première édition absente de sa place) est rendu tel quel."""
    t = _table_g()
    cible = _FICHIERS_G.get(cible, cible)
    subs = (t or {}).get("couches", {}).get(cible, [])
    if not subs:
        return texte
    bom = texte[:1] == "\ufeff"
    corps = texte[1:] if bom else texte
    crlf = "\r\n" in corps
    s = corps if crlf else corps.replace("\n", "\r\n")
    # t143 : la couche montage peut aussi être la vue d'avant L3 qui garde G1 (couche_avant_i18n_l3), éditions recalées
    vues = [subs] + ([_g1_avant_l3()] if cible == "montage" else [])
    r = None
    for v in vues:
        e0 = min(v, key=lambda x: x["pos"])
        if s[e0["pos"]:e0["pos"] + len(e0["apres"])] != e0["apres"]:
            continue
        try:
            r = _couche_defaire_subs(s, [dict(x, groupe="dzglyph") for x in v], f"couche {cible} G1")
            break
        except ValueError:
            if v is vues[-1]:
                raise
    if r is None:
        return texte
    r = r if crlf else r.replace("\r\n", "\n")
    return ("\ufeff" + r) if bom else r


def _bloc_tag(s, tag, f):
    b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
    if b not in s:
        return s
    head, rest = s.split(b, 1)
    bloc, tail = rest.split(e, 1)
    lead = bloc[:len(bloc) - len(bloc.lstrip("\r\n"))]
    trail = bloc[len(bloc.rstrip("\r\n")):]
    return head + b + lead + f(bloc.strip("\r\n")) + trail + e + tail


def avant_dzglyph(bundle: str) -> str:
    """Le bundle d'avant les icônes G1 : la table du maillon dzglyph défaite (si son marqueur est là) et les blocs des
    quatre couches ramenés à leur source d'avant G1. LF ou CRLF : on rend la même forme."""
    if "\r\n" not in bundle:
        return avant_dzglyph(bundle.replace("\n", "\r\n")).replace("\r\n", "\n")
    s = bundle
    if _TABLE_G.is_file() and _MARQUE_G in s:
        s = _defaire(s, _TABLE_G, "avant_dzglyph")
    for cible, tag in _BLOCS_G.items():
        s = _bloc_tag(s, tag, lambda c, cible=cible: couche_avant_dzglyph(c, cible))
    return s


# icônes G1 sous node : les outils que le maillon dzglyph pose dans le bundle, rendus sans React et en TEXTE —
# __dzGl(clé) rend « ⟦clé⟧ », __dzGlT(clé, texte, glyphe) le texte où le glyphe est devenu « ⟦clé⟧ » (mêmes espaces
# que dans l'app), __dzGlS / __dzGlD comme dans l'app ; __dzGlH rend un <svg data-dzi="clé"> vide. Un banc qui
# cherchait un bouton par son glyphe (« × ») le cherche donc par sa clé (« ⟦dz-action-fermer⟧ »). Inclus dans
# PRELUDE_DZT.
PRELUDE_DZGLYPH = r"""
function __dzGl(e,t,n){return "⟦"+e+"⟧"}
function __dzGlT(e,s,g,t){var i=__dzGl(e,t);if(typeof s!=="string")return s;var k=g?s.indexOf(g):-1;if(k<0)return s;var a=s.slice(0,k).replace(/\s+$/,""),b=s.slice(k+g.length).replace(/^\s+/,"");return a&&b?a+" "+i+" "+b:a?a+" "+i:b?i+" "+b:i}
function __dzGlS(s,g){if(typeof s!=="string"||!g)return s;var k=s.indexOf(g);return k<0?s:(s.slice(0,k)+s.slice(k+g.length)).replace(/^\s+|\s+$/g,"").replace(/\s{2,}/g," ")}
function __dzGlH(e,t){return '<svg class="dzi" data-dzi="'+e+'"></svg>'}
function __dzGlD(el,e,s,g,t){var k=typeof s==="string"&&g?s.indexOf(g):0,f=k>0&&k>=s.length-g.length,x=__dzGlS(s,g)||"";el.textContent=f?x+" ⟦"+e+"⟧":"⟦"+e+"⟧ "+x;return el}
if (typeof globalThis !== 'undefined') { globalThis.__dzGl = __dzGl; globalThis.__dzGlT = __dzGlT; globalThis.__dzGlS = __dzGlS; globalThis.__dzGlH = __dzGlH; globalThis.__dzGlD = __dzGlD; }
"""


def _prelude():
    dico_js = _DICO_JS.read_bytes().decode("utf-8") if _DICO_JS.is_file() else "window.DZ_I18N={};"
    return ("var window = (typeof window !== 'undefined') ? window : {};\n"
            + dico_js + "\n"
            + "function dzT(k, v) { var e = (window.DZ_I18N || {})[k]; var s = e ? e.fr : k;"
              " if (v) s = s.replace(/\\{(\\w+)\\}/g, function (m, n) { return v[n] != null ? String(v[n]) : m; });"
              " return s; }\n"
            + "if (typeof globalThis !== 'undefined') globalThis.dzT = dzT;\n"
            + PRELUDE_DZGLYPH)


PRELUDE_DZT = _prelude()
