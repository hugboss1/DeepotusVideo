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
    s = _avant_l2_crlf(bundle)                     # t142 : L2 se défait d'abord (maillon posé APRÈS L1)
    s = _defaire(s, _TABLE, "avant_i18n")
    return _bloc(s, lambda c: _couche_defaire(c, _TABLE, "couche"))


def _prelude():
    dico_js = _DICO_JS.read_bytes().decode("utf-8") if _DICO_JS.is_file() else "window.DZ_I18N={};"
    return ("var window = (typeof window !== 'undefined') ? window : {};\n"
            + dico_js + "\n"
            + "function dzT(k, v) { var e = (window.DZ_I18N || {})[k]; var s = e ? e.fr : k;"
              " if (v) s = s.replace(/\\{(\\w+)\\}/g, function (m, n) { return v[n] != null ? String(v[n]) : m; });"
              " return s; }\n"
            + "if (typeof globalThis !== 'undefined') globalThis.dzT = dzT;\n")


PRELUDE_DZT = _prelude()
