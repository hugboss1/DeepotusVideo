"""Traduction L1 (t141) : le PÉRIMÈTRE du lot et le contrôle « plus de texte en dur ».

`restes(bundle, couche, gardes)` rend, pour les composants du lot (bundle hors couche, et couche montage.js), les
littéraux qui ressemblent encore à du texte d'interface : ni argument d'un dzT(…), ni littéral GARDÉ (saisie X), ni
bruit technique (CSS, valeurs, identifiants). Utilisé par backend/tests/test_i18n_l1.py.

Le découpage est lexical (chaînes "…" '…', morceaux de gabarits, regex et commentaires sautés) : le bundle est minifié.
"""
import re

# composants du lot dans le bundle (hors couche) — vues des autres lots exclues (Studio, Quick, Scheduler, News,
# Templates, Chapitres, Son & VFX, Game Assets, Montage), Transfert (L5), générateur de prompts (Lu, L2), recettes,
# prolongation de clip et impression 3D (autres lots)
BUNDLE = ["mo", "lg", "ng", "tg", "ig", "rg", "yd", "dzQBtn", "dzqEmpty", "Hm", "Km", "Qm", "qm", "Xm", "Zm", "Jm",
          "xm", "jm", "Cm", "_m", "Tm", "bm", "wm", "Sm", "km", "Em", "zm", "Au", "Ou", "im", "sm", "am", "lm",
          "DzImageModel", "DzVideoModelSel", "DzVoModelSel", "DzVoiceProvider", "DzTestCle", "__dzSchedConnect",
          "DzCoffre", "DzAppair", "DzDiag", "DzMaj", "DzPlafonds", "DzPricing", "DzDepenses", "DzSettingsSearch", "dzRubrique",
          "__dzCoutBlanc", "dzOct",
          "vm", "__dzSendTo", "__dzSendMenu", "__dzSendBible", "__dzSendSched", "__dzSrcChips", "__dzEtabli", "DzOptGlbBtn"]
# composants du lot dans la couche frontend/patches/montage.js
COUCHE = ["DzCorbeille", "DzFiche", "dzFicheLignes", "DzRecherche", "DzKits", "dzKitErr", "DzProjetsBar", "dzProjMenu",
          "dzProjApi", "DzNettoyage", "dzNettVue", "DzCommentaires", "DzClipBloc", "dzMo", "DzListe", "DzMetaEditor",
          "DzMetaChips", "dzCarteMeta", "DzEtatProjet", "DzLignee", "DzOutilsBiblio", "DzSemblables", "dzDuree",
          "dzOctets", "dzUsdLeg", "dzFavMigrer", "dzFavToggle", "dzSendChoisir", "dzSendRecette", "dzSendStudioRendu",
          "DzModelDefaults", "dzDefautsEcrire", "DzLangueUI"]

AVANT_REGEX = set("(,=:[!&|?{};+-*%<>~^")
MOTS_REGEX = ("return", "typeof", "case", "do", "else", "in", "of", "void", "throw", "new", "delete")


def _est_regex(s, k):
    j = k - 1
    while j >= 0 and s[j] in " \t\r\n":
        j -= 1
    mot, m = "", j
    while m >= 0 and (s[m].isalnum() or s[m] in "_$"):
        mot = s[m] + mot
        m -= 1
    return j < 0 or s[j] in AVANT_REGEX or mot in MOTS_REGEX


def _sauter_chaine(s, k, b):
    q = s[k]
    k += 1
    while k < b and s[k] != q:
        k += 2 if s[k] == "\\" else 1
    return k + 1


def _sauter_regex(s, k, b):
    k += 1
    classe = False
    while k < b:
        if s[k] == "\\":
            k += 2
            continue
        if s[k] == "[":
            classe = True
        elif s[k] == "]":
            classe = False
        elif s[k] == "/" and not classe:
            break
        k += 1
    k += 1
    while k < b and s[k].isalpha():
        k += 1
    return k


def litteraux(s, a, b):
    """[(debut, fin, texte, genre)] des chaînes et morceaux de gabarits de s[a:b]."""
    out, pile, prof, k = [], [], 0, a

    def gabarit(k):
        d = k
        while k < b:
            c = s[k]
            if c == "\\":
                k += 2
                continue
            if c == "`":
                if k > d:
                    out.append((d, k, s[d:k], "`"))
                return k + 1, False
            if c == "$" and k + 1 < b and s[k + 1] == "{":
                if k > d:
                    out.append((d, k, s[d:k], "`"))
                return k + 2, True
            k += 1
        return k, False

    while k < b:
        c = s[k]
        if c in "\"'":
            e = _sauter_chaine(s, k, b)
            out.append((k, e, s[k + 1:e - 1], c))
            k = e
            continue
        if c == "`":
            k, ouvert = gabarit(k + 1)
            if ouvert:
                pile.append(prof)
                prof += 1
            continue
        if c == "/" and k + 1 < b and s[k + 1] == "/":
            e = s.find("\n", k)
            k = b if e < 0 else e
            continue
        if c == "/" and k + 1 < b and s[k + 1] == "*":
            k = s.find("*/", k + 2) + 2
            continue
        if c == "/" and _est_regex(s, k):
            k = _sauter_regex(s, k, b)
            continue
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if pile and prof == pile[-1]:
                pile.pop()
                k, ouvert = gabarit(k + 1)
                if ouvert:
                    pile.append(prof)
                    prof += 1
                continue
        k += 1
    return out


def fin_fonction(s, i):
    """i = index du '{' du corps -> index juste après l'accolade fermante (chaînes, gabarits, regex sautés)."""
    prof, k, n = 0, i, len(s)
    pile = []
    while k < n:
        c = s[k]
        if c in "\"'":
            k = _sauter_chaine(s, k, n)
            continue
        if c == "`":
            k += 1
            while k < n:
                if s[k] == "\\":
                    k += 2
                    continue
                if s[k] == "`":
                    k += 1
                    break
                if s[k] == "$" and k + 1 < n and s[k + 1] == "{":
                    pile.append(prof)
                    prof += 1
                    k += 2
                    break
                k += 1
            continue
        if c == "/" and k + 1 < n and s[k + 1] == "/":
            k = s.find("\n", k)
            k = n if k < 0 else k
            continue
        if c == "/" and k + 1 < n and s[k + 1] == "*":
            k = s.find("*/", k + 2) + 2
            continue
        if c == "/" and _est_regex(s, k):
            k = _sauter_regex(s, k, n)
            continue
        if c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if pile and prof == pile[-1]:
                pile.pop()
                k += 1
                while k < n:
                    if s[k] == "\\":
                        k += 2
                        continue
                    if s[k] == "`":
                        k += 1
                        break
                    if s[k] == "$" and k + 1 < n and s[k + 1] == "{":
                        pile.append(prof)
                        prof += 1
                        k += 2
                        break
                    k += 1
                continue
            if prof == 0:
                return k + 1
        k += 1
    return -1


def segment(s, nom):
    t = f"function {nom}("
    i = s.find(t)
    if i < 0:
        return None
    p, prof = i + len(t) - 1, 0
    while p < len(s):
        if s[p] == "(":
            prof += 1
        elif s[p] == ")":
            prof -= 1
            if prof == 0:
                break
        p += 1
    return i, fin_fonction(s, s.find("{", p))


BRUIT = re.compile(
    r"^\s*$|^[\d\s.,:%+\-×x/()#·—–]*$"                                        # nombres, ponctuation seule
    r"|var\(--|cubic-bezier|\b\d+(px|ms|s|deg|%|fr|em|vh|vw)\b|^(rgba?|hsla?|translate[XY]?|rotate|scale)\(|-gradient\("
    r"|@keyframes|^[a-z-]+ [a-z0-9 -]*(ease|linear|infinite)"                # animations
    r"|^(application|image|video|audio|text)/|^/api|^https?:|^data:|^\.?/"  # types, chemins
    r"|^[A-Za-z0-9_$.\-/:#@]+$"                                             # un seul jeton sans espace : identifiant, clé
    r"|^([a-z-]+:[^;]*;)+"                                                  # style en ligne (cssText)
)


# littéraux techniques du périmètre qui ressemblent à du texte : classes CSS composées, noms de touches, police,
# fragments d'URL, préfixe de message d'erreur HTTP (relevés au premier passage du banc, 08/10/2026)
TECHNIQUES = {" dzNavFold", " on", "mono strong", "scroll mono", " dzq-pulse", "[data-missing]", "Escape", "Enter",
              "JetBrains Mono", "&moteur=", "HTTP ", "dzsvm dz-libsons",
              "Mixkit",            # nom propre (banque de sons)
              "Image"}             # __dzSendTo : type de nœud du Studio (type:"Image"), un identifiant


def texte_visible(t):
    """Un littéral qui ressemble à du texte d'interface (au moins un mot de 2 lettres et une espace, ou une lettre
    accentuée, ou un mot capitalisé)."""
    if BRUIT.search(t):
        # un mot seul capitalisé (« Copier », « Settings ») reste du texte : le jeton seul n'est du bruit que s'il est
        # tout en minuscules, en camelCase, ou technique
        mot = t.strip()
        if re.fullmatch(r"[A-ZÀ-Ý][a-zà-ÿ’']{2,}[.…!?:]?", mot) or re.fullmatch(r".*[à-ÿÀ-Ý].*", mot) and " " not in mot and len(mot) > 2:
            return True
        return False
    return bool(re.search(r"[A-Za-zÀ-ÿ]{2,}", t))


def _restes(s, noms, gardes_txt):
    out = []
    for nom in noms:
        r = segment(s, nom)
        if not r or r[1] < 0:
            out.append(f"{nom} : composant introuvable")
            continue
        a, b = r
        for d, e, t, g in litteraux(s, a, b):
            if s[max(0, d - 4):d] == "dzT(":
                continue                                   # la clé d'un dzT
            if t in gardes_txt or t in TECHNIQUES or not texte_visible(t):
                continue
            out.append(f"{nom}@{d} {t[:90]!r}")
    return out


def restes(bundle, couche, gardes):
    gb = {g["texte"][1:-1] for g in gardes if g.get("cible", "bundle") == "bundle"}
    gc = {g["texte"][1:-1] for g in gardes if g.get("cible") == "couche"}
    return {"bundle": _restes(bundle, BUNDLE, gb), "couche": _restes(couche, COUCHE, gc)}
