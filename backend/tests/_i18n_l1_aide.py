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
  avant_i18n_l5(bundle)   t145 : le bundle d'avant la traduction L5 — table du maillon patch_bundle_i18n_l5 défaite (bloc
                          SUBS) et blocs TRANSFERT et DIALOGUE ramenés aux sources d'avant (avant_i18n le fait aussi,
                          en premier).
  source_avant_i18n_l5(texte, cible)  t145 : frontend/patches/transfert.js ou frontend/shared/dialogue.js (et ses
                          copies) d'avant L5.
  PRELUDE_DZT             code JS à placer AVANT la couche ou le bundle exécutés sous node : window.DZ_I18N (le
                          dictionnaire assemblé) et dzT(clé, vars) en FRANÇAIS, la langue de référence — les attentes
                          en français des bancs restent vraies.
  fr(cle, **vars)         le texte français d'une clé (pour les bancs qui épinglent un libellé).
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


def couche_avant_i18n_l2(couche: str) -> str:
    """t142 : la couche frontend/patches/montage.js d'avant la seule traduction L2 (L1 toujours posée)."""
    return _couche_defaire(couche, _TABLE2, "couche L2")


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
    bundle = avant_i18n_l5(bundle)                 # t145 : le maillon L5 est posé APRÈS L2
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
    s = _avant_l2_crlf(bundle)                     # t145 : L5 se défait là, en premier                     # t142 : L2 se défait d'abord (maillon posé APRÈS L1) ; t144 : L4 avant
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
    bom = texte[:1] == "﻿"
    r = _defaire4(texte[1:] if bom else texte, cible, f"couche {cible} L4")
    return ("﻿" + r) if bom else r


def avant_i18n_l4(bundle: str) -> str:
    """Le bundle dont les blocs SFXSTUDIO, VFXRACK et SONVFX sont ramenés aux couches d'avant L4 (bords conservés)."""
    s = bundle
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


def _prelude():
    dico_js = _DICO_JS.read_bytes().decode("utf-8") if _DICO_JS.is_file() else "window.DZ_I18N={};"
    return ("var window = (typeof window !== 'undefined') ? window : {};\n"
            + dico_js + "\n"
            + "function dzT(k, v) { var e = (window.DZ_I18N || {})[k]; var s = e ? e.fr : k;"
              " if (v) s = s.replace(/\\{(\\w+)\\}/g, function (m, n) { return v[n] != null ? String(v[n]) : m; });"
              " return s; }\n"
            + "if (typeof globalThis !== 'undefined') globalThis.dzT = dzT;\n")


PRELUDE_DZT = _prelude()


# t145 — traduction L5 : le bloc SUBS (maillon patch_bundle_i18n_l5, table scripts/i18n_l5_paires.json « paires ») et
# les couches TRANSFERT et DIALOGUE (sources réécrites, « sources » : positions dans la source de BASE 2b155403, CRLF ;
# « decalages » : où commence, dans cette source, le cœur que le bloc du bundle porte)
_TABLE5 = RACINE / "scripts" / "i18n_l5_paires.json"
_BLOCS5 = {"transfert": "TRANSFERT", "dialogue": "DIALOGUE"}
_FICHIERS5 = {"transfert.js": "transfert", "dialogue.js": "dialogue"}


def _table5():
    return json.loads(_TABLE5.read_bytes().decode("utf-8")) if _TABLE5.is_file() else None


def source_avant_i18n_l5(texte: str, cible: str) -> str:
    """t145 : la source `cible` (« transfert », « dialogue », ou le nom de fichier) d'avant L5 ; BOM toléré, LF ou
    CRLF : on rend la même forme."""
    cible = _FICHIERS5.get(cible, cible)
    t = _table5()
    if t is None:
        return texte
    bom = texte[:1] == "\ufeff"
    r = _couche_defaire_subs(texte[1:] if bom else texte, t["sources"].get(cible, []), f"source {cible} L5")
    return ("\ufeff" + r) if bom else r


def _avant_l5_crlf(bundle: str) -> str:
    t = _table5()
    if t is None or 'dzT("subs.' not in bundle and 'dzT("transfert.' not in bundle and "__dzT(" not in bundle:
        return bundle                          # bundle d'avant L5 (un .bak reconstruit) : rendu tel quel
    s = _defaire(bundle, _TABLE5, "avant_i18n_l5") if 'dzT("subs.' in bundle else bundle
    for cible, tag in _BLOCS5.items():
        b, e = f"/*__DZ_{tag}_BEGIN__*/", f"/*__DZ_{tag}_END__*/"
        if b not in s:
            continue
        head, rest = s.split(b, 1)
        bloc, tail = rest.split(e, 1)
        lead = bloc[:len(bloc) - len(bloc.lstrip("\r\n"))]
        trail = bloc[len(bloc.rstrip("\r\n")):]
        coeur = bloc.strip("\r\n")
        if ('dzT("transfert.' if cible == "transfert" else "__dzT(") in coeur:
            d = t["decalages"][cible]
            subs = [dict(x, pos=x["pos"] - d) for x in t["sources"].get(cible, [])]
            coeur = _couche_defaire_subs(coeur, subs, f"bloc {tag} L5")
        s = head + b + lead + coeur + trail + e + tail
    return s


def avant_i18n_l5(bundle: str) -> str:
    """Le bundle d'avant la seule traduction L5 (t145). LF ou CRLF : on rend la même forme."""
    if "\r\n" not in bundle:
        return _avant_l5_crlf(bundle.replace("\n", "\r\n")).replace("\r\n", "\n")
    return _avant_l5_crlf(bundle)
