# -*- coding: utf-8 -*-
# scripts/refresh_layer.py
"""Rafraîchit UNE couche injectée du bundle, en place, sans toucher à la chaîne.

POURQUOI (plan 2026-09-03-plan-son-vfx T1, relu le 06/10/2026). Les patchers sfxstudio / sonvfx / vfxrack ne se
relancent pas tels quels : chacun CRÉE ou consomme un `.bak_<tag>` (la chaîne en compte 11 aujourd'hui, `version`
en queue), et vfxrack abandonne sur ses ancres déjà consommées. Rafraîchir le code d'une couche — la seule chose
qu'une tâche Son & VFX change — n'a besoin d'aucun d'eux : cet outil ne lit et n'écrit QUE le bloc entre les
marqueurs /*__DZ_<TAG>_BEGIN__*/ … /*__DZ_<TAG>_END__*/, garde les retours de ligne de BORD du bloc tels quels, et
n'ouvre JAMAIS un `.bak` (il compare leurs octets avant/après et refuse sinon).

LA GARDE DE DÉRIVE, et c'est ce que le plan n'avait pas vu (mesuré le 06/10). D'autres patchers écrivent DANS ces
blocs : `patch_bundle_montage.py` a injecté dans le bloc SFXSTUDIO l'anti-ronflement et l'égaliseur 6 bandes (L6,
25/09 — 36 lignes) et dans le bloc SONVFX tout le Montage des lots L1→L7 (1 462 lignes) sans que les sources de
`frontend/patches/` le sachent. Un rafraîchissement depuis la source les aurait EFFACÉS en silence. Avant d'écrire,
l'outil reconstruit donc le bloc depuis la source VERSIONNÉE (`git show HEAD:`) par le même chemin : s'il ne retombe
pas exactement sur le bloc du bundle, le bundle porte du code venu d'ailleurs, et l'outil REFUSE en nommant les
lignes qui seraient perdues. `--force` passe outre ; `--adopter` est la remise à niveau (voir plus bas).

LE BUNDLE SE LIT EN OCTETS : le mode texte de Python aplatit les 17 204 CRLF en silence.

    python scripts/refresh_layer.py --layer sfxstudio|vfxrack|sonvfx|montage|transfert|dialogue [--check] [--force] [--adopter] [--root CHEMIN]

`--adopter` : la source est réécrite depuis le bloc du bundle, et seulement si le rafraîchissement depuis elle
reconstruit alors le bundle À L'OCTET.
`--root` : la racine d'un dépôt (défaut : celui de ce script) — ce qui permet au banc de travailler sur une COPIE.

PLUS DE REJEU IN-BLOC, ET C'EST UNE DÉCISION MESURÉE (06/10). Le plan rejouait, après un rafraîchissement de
sonvfx, les couples vfxrack/subs par `reapply_inblock_patches.py --no-refresh`. Or le bundle n'est cohérent avec
AUCUN état « source propre + couples » : sept de ces couples (V5, V7, S3, S8, S9, S14, S16) y ont leur ancre
INTACTE et leur remplacement ABSENT — le Montage a réécrit ces zones depuis — et le rejeu les RÉAPPLIQUERAIT
(`vfxAddTo` en double, entre autres ; son propre `--check` annonce « réappliqués : 7 »). Depuis T099, les trois
sources portent donc le bloc COMPLET tel qu'il est servi (adopté depuis le bundle), et rafraîchir = remplacer.
"""
import argparse
import difflib
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
LAYERS = {"sfxstudio": ("SFXSTUDIO", "sfxstudio.js"),
          "vfxrack": ("VFXRACK", "vfxrack.js"),
          "sonvfx": ("SONVFX", "son-vfx-montage.js"),
          # t120 (06/10/2026) : la couche du Montage (DzTracks), injectée par patch_bundle_montage M1 — le patcher ne se
          # rejoue plus (son .bak est une reconstruction gardée), et le bloc du bundle EST la source à l octet (mesuré par
          # scripts/restaurer_bak_montage.py, qui l exige) : la rafraîchir = la remplacer, comme les trois autres
          "montage": ("MONTAGE", "montage.js"),
          # t145 (traduction L5) : les couches du transfert et des dialogues. Leur source porte ses PROPRES lignes de
          # marqueurs (patch_bundle_transfert / patch_bundle_dialogue l'injectent telle quelle) : le cœur est pris
          # entre elles (_coeur). Le bloc du bundle est la source à l'octet près des marqueurs — rafraîchir = remplacer.
          # (subs n'y est PAS : des patchers aval écrivent dans son bloc et subs.js est intouchable — test_montage_bundle.)
          "transfert": ("TRANSFERT", "transfert.js"),
          "dialogue": ("DIALOGUE", "dialogue.js")}
CRLF, LF = b"\r\n", b"\n"


def _baks(bundle: pathlib.Path) -> dict:
    return {p.name: p.read_bytes() for p in sorted(bundle.parent.glob(bundle.name + ".bak_*"))}


def _marqueurs(tag: str):
    return f"/*__DZ_{tag}_BEGIN__*/".encode(), f"/*__DZ_{tag}_END__*/".encode()


def _bloc(raw: bytes, tag: str) -> bytes:
    b, e = _marqueurs(tag)
    return raw.split(b, 1)[1].split(e, 1)[0]


def _coeur(src: bytes, tag: str) -> bytes:
    """t145 : une source qui porte ses propres lignes de marqueurs (transfert.js, dialogue.js) -> ce qui est entre
    elles ; une source sans marqueur est rendue telle quelle."""
    b, e = _marqueurs(tag)
    if b in src and e in src:
        return src.split(b, 1)[1].split(e, 1)[0]
    return src


def _remplacer(raw: bytes, tag: str, src: bytes) -> bytes:
    """Le bloc remplacé par `src`, aux fins de ligne du bundle, BORDS conservés : un rafraîchissement sans
    changement de source rend le bundle octet pour octet."""
    b, e = _marqueurs(tag)
    if src.startswith(b"\xef\xbb\xbf"):
        src = src[3:]
    src = _coeur(src, tag)
    src = src.replace(CRLF, LF)
    if CRLF in raw:
        src = src.replace(LF, CRLF)
    head, rest = raw.split(b, 1)
    ancien, tail = rest.split(e, 1)
    lead = ancien[:len(ancien) - len(ancien.lstrip(CRLF))]
    trail = ancien[len(ancien.rstrip(CRLF)):]
    return head + b + lead + src.strip(CRLF) + trail + e + tail


def _pipeline(racine: pathlib.Path, layer: str, raw: bytes, src: bytes) -> tuple:
    """Le bundle tel que le rafraîchissement le rendrait : le bloc remplacé par la source, BORDS conservés. Plus de
    rejeu in-bloc (voir l'en-tête) : la source porte le bloc COMPLET."""
    return _remplacer(raw, LAYERS[layer][0], src), 0


def adopter(racine: pathlib.Path, layer: str) -> int:
    """LE BUNDLE DEVIENT LA SOURCE : réécrit frontend/patches/<src> depuis le bloc ACTUEL, puis exige que le
    pipeline reconstruise le bundle À L'OCTET — sinon rien n'est écrit."""
    tag, src_name = LAYERS[layer]
    if layer in ("transfert", "dialogue"):
        print(f"[{layer}] --adopter refusé : la source porte ses marqueurs et a des copies (dialogue) — l'éditer elle.")
        return 7
    raw = (racine / REL_BUNDLE).read_bytes()
    bloc = _bloc(raw, tag)
    candidat = bloc.strip(CRLF)
    p_src = racine / "frontend/patches" / src_name
    ancien = p_src.read_bytes()
    candidat = candidat.replace(CRLF, LF)
    candidat = (candidat.replace(LF, CRLF) + CRLF) if CRLF in ancien else (candidat + LF)
    rejoue, rc = _pipeline(racine, layer, raw, candidat)
    if rc != 0 or rejoue != raw:
        print(f"[{layer}] ADOPTION REFUSÉE : la source candidate ne reconstruit pas le bundle à l'octet "
              f"(rc={rc}). Rien écrit.")
        return 6
    p_src.write_bytes(candidat)
    print(f"[{layer}] source adoptée depuis le bundle : {len(ancien)} -> {len(candidat)} octets ; "
          "le rafraîchissement depuis cette source rend le bundle à l'octet")
    return 0


def _source_versionnee(racine: pathlib.Path, src_name: str):
    r = subprocess.run(["git", "-C", str(racine), "show", f"HEAD:frontend/patches/{src_name}"],
                       capture_output=True)
    return r.stdout if r.returncode == 0 else None


def derive(racine: pathlib.Path, layer: str, raw: bytes) -> list:
    """Les lignes du bloc du bundle que la source VERSIONNÉE, passée par le même pipeline, ne reproduit pas."""
    tag, src_name = LAYERS[layer]
    versionnee = _source_versionnee(racine, src_name)
    if versionnee is None:
        return []
    rejoue, rc = _pipeline(racine, layer, raw, versionnee)
    if rc != 0 or _bloc(rejoue, tag) == _bloc(raw, tag):
        return []
    ref = _bloc(raw, tag).decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    neuf = _bloc(rejoue, tag).decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    return [l for l in difflib.unified_diff(neuf, ref, "source HEAD", "bundle", n=0, lineterm="")
            if l.startswith("+") and not l.startswith("+++")]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", required=True, choices=sorted(LAYERS))
    ap.add_argument("--check", action="store_true", help="compte les marqueurs et mesure la dérive, n'écrit rien")
    ap.add_argument("--force", action="store_true", help="écrire malgré une dérive (lignes reportées à la main)")
    ap.add_argument("--adopter", action="store_true",
                    help="réécrire la SOURCE depuis le bloc du bundle (après un patcher qui a écrit dans le bloc)")
    ap.add_argument("--root", default=str(REPO))
    a = ap.parse_args()
    racine = pathlib.Path(a.root)
    bundle = racine / REL_BUNDLE
    tag, src_name = LAYERS[a.layer]
    b, e = _marqueurs(tag)

    raw = bundle.read_bytes()
    n_b, n_e = raw.count(b), raw.count(e)
    if n_b != 1 or n_e != 1:
        print(f"[{a.layer}] marqueurs : begin={n_b} end={n_e} (attendu 1/1). Rien écrit.")
        return 2
    if a.adopter:
        return adopter(racine, a.layer)

    lignes = derive(racine, a.layer, raw)
    etat = f"dérive : {len(lignes)} ligne(s) du bundle absente(s) de la source" if lignes else "dérive : 0"
    if a.check:
        print(f"[{a.layer}] bloc: 1 · crlf={CRLF in raw} · {etat} · rien écrit")
        return 0
    if lignes and not a.force:
        print(f"[{a.layer}] REFUS — le bundle porte du code que la source versionnée n'a pas ; un rafraîchissement "
              f"l'effacerait. Lance --adopter (ou reporte ces lignes dans frontend/patches/{src_name}) :")
        for l in lignes[:25]:
            print("   " + l[:160])
        return 5

    avant = _baks(bundle)
    src = (racine / "frontend/patches" / src_name).read_bytes()
    neuf, rc = _pipeline(racine, a.layer, raw, src)
    if rc != 0:
        print(f"[{a.layer}] rejeu des couples in-bloc échoué (rc={rc}). Rien écrit.")
        return 4
    bundle.write_bytes(neuf)
    if _baks(bundle) != avant:
        print(f"[{a.layer}] un .bak a bougé — INTERDIT")
        return 3
    print(f"[{a.layer}] bloc rafraîchi ({len(src)} octets) · .bak : {len(avant)}, aucun touché"
          + (" · identique (source inchangée)" if neuf == raw else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
