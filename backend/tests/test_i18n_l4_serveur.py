# -*- coding: utf-8 -*-
"""t144 (09/10/2026) — traduction L4, côté SERVEUR : les catalogues affichés par le rack VFX et le Montage (effets :
noms, aides, catégories, libellés de paramètres ; transitions xfade ; préréglages de livraison ; gabarits de titre)
sont rendus dans la langue de la requête (en-tête Accept-Language du runtime dz-i18n), le français restant la
réponse par défaut, octet pour octet celle d'avant.

  [1] scripts/i18n_l4_serveur.py --check : messages.json porte une clé par texte des tables, fr = le texte source.
  [2] sans en-tête (et en fr) : chaque route rend EXACTEMENT le catalogue source (les ~50 bancs qui lisent ces textes
      en français ne voient rien changer) ; en anglais : les textes changent, jamais les ids, valeurs ni bornes.
  [3] la traduction travaille sur une COPIE : la table source reste intacte après une réponse anglaise.
  [4] une table source modifiée sans retraduire : le texte servi est le français de la source (pas une traduction
      périmée) ; une clé absente : le texte tel quel.
Run : & $PY tests/test_i18n_l4_serveur.py   (depuis backend/, python EMBARQUÉ)
"""
import asyncio
import copy
import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
RACINE = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


def _sans_textes(x):
    """La structure sans les libellés traduisibles (label, hint) : ids, valeurs, bornes, comptes."""
    if isinstance(x, dict):
        return {k: _sans_textes(v) for k, v in x.items() if k not in ("label", "hint")}
    if isinstance(x, list):
        return [_sans_textes(v) for v in x]
    return x


async def _routes():
    import httpx
    from app.main import app
    from app.services import effects_preview as FXP, effects_engine as FX, montage_service as M
    cibles = {
        "/api/effects/catalog": lambda: FXP.catalog_payload(),
        "/api/montage/effects": lambda: {"effects": FX.catalog()},
        "/api/montage/transitions": lambda: M.transitions_catalog(),
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)),
                                 base_url="http://t") as c:
        R = {}
        for url in list(cibles) + ["/api/montage/titles", "/api/montage/deliver-presets"]:
            R[url] = {h: (await c.get(url, headers=({"Accept-Language": h} if h else {}))).json()
                      for h in ("", "fr-FR,fr;q=0.9", "en-US,en;q=0.9")}
    print("\n[2] les routes")
    for url, src in cibles.items():
        attendu = json.loads(json.dumps(src(), ensure_ascii=False))
        check(f"2a {url} sans en-tête = la table source, à l'identique", R[url][""] == attendu)
        check(f"2b {url} en français = la table source", R[url]["fr-FR,fr;q=0.9"] == attendu)
        check(f"2c {url} en anglais : mêmes ids, valeurs et bornes", _sans_textes(R[url]["en-US,en;q=0.9"]) == _sans_textes(attendu))
    for url in ("/api/montage/titles", "/api/montage/deliver-presets"):
        check(f"2d {url} : rien ne change sans en-tête ni en français, seuls les libellés changent en anglais",
              R[url][""] == R[url]["fr-FR,fr;q=0.9"] and _sans_textes(R[url]["en-US,en;q=0.9"]) == _sans_textes(R[url][""])
              and R[url]["en-US,en;q=0.9"] != R[url][""])
    en = R["/api/effects/catalog"]["en-US,en;q=0.9"]
    check("2e effets en anglais : nom, aide, catégorie et libellé de paramètre",
          en["effects"]["shake"]["label"] == "Camera shake" and en["effects"]["shake"]["hint"] == "Frame shake."
          and {c["id"]: c["label"] for c in en["categories"]}["etalonnage"] == "Grading"
          and en["effects"]["huesat"]["bounds"]["hue"]["label"] == "Hue"
          and en["effects"]["lut"]["label"] == "LUT / Grade",
          (en["effects"]["shake"], en["categories"][:2]))
    fr = R["/api/effects/catalog"][""]
    check("2f … et en français les textes d'origine", fr["effects"]["shake"]["label"] == "Secousse caméra"
          and {c["id"]: c["label"] for c in fr["categories"]}["etalonnage"] == "Étalonnage")
    tr = R["/api/montage/transitions"]["en-US,en;q=0.9"]["familles"]
    check("2g transitions en anglais (famille, libellé), id xfade inchangé",
          tr[0]["label"] == "fades" and tr[0]["items"][1] == {"id": "fadeblack", "label": "fade to black", "live": True}, tr[0])
    reste = [(f["id"], it["id"]) for f in tr for it in f["items"] if it["label"] == M._XFADE_LABELS.get(it["id"])
             and it["label"] not in ("distance",)]
    check("2h aucune transition laissée en français (hors « distance », identique)", not reste, reste[:8])
    lv = {b["id"]: b["label"] for b in R["/api/montage/deliver-presets"]["en-US,en;q=0.9"]["builtins"]}
    tt = {g["id"]: g["label"] for g in R["/api/montage/titles"]["en-US,en;q=0.9"]["gabarits"]}
    check("2i livraison et titres en anglais", lv["social_720"] == "Social 720 (light H.264)"
          and tt["tiers_inferieur"] == "lower third", (lv, tt))


def main():
    print("\n[1] le dictionnaire serveur")
    p = subprocess.run([sys.executable, "-I", str(RACINE / "scripts/i18n_l4_serveur.py"), "--check"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
    check("1a i18n_l4_serveur --check : messages.json à jour, fr = texte des tables", p.returncode == 0,
          (p.stdout + p.stderr)[-400:])
    from app.i18n import _DICO
    lot = {k: v for k, v in _DICO.items() if k.startswith(("effets.", "transitions.", "livraison.", "titres.gabarit."))}
    check("1b au moins 230 clés serveur du lot, fr et en non vides",
          len(lot) >= 230 and all(v.get("fr") and v.get("en") for v in lot.values()), len(lot))

    asyncio.run(_routes())

    print("\n[3] copie, pas mutation")
    from app.i18n import catalogues as CAT
    from app.services import effects_engine as FX, montage_service as M
    cat = FX.catalog()
    avant = copy.deepcopy(cat)
    CAT.effets(cat, "en")
    check("3a effets(…, en) laisse la table source intacte", cat == avant)
    t = M.transitions_catalog()
    t0 = copy.deepcopy(t)
    CAT.transitions(t, "en")
    check("3b transitions(…, en) laisse la table source intacte", t == t0)

    print("\n[4] source changée ou clé absente")
    faux = {"shake": dict(cat["shake"], label="Secousse NEUVE"), "inconnu": {"label": "Truc", "hint": "Aide", "bounds": {}}}
    r = CAT.effets(faux, "en")
    check("4a un texte source changé depuis la traduction est servi tel quel (jamais une traduction périmée)",
          r["shake"]["label"] == "Secousse NEUVE" and r["shake"]["hint"] == "Frame shake.", r["shake"]["label"])
    check("4b un effet sans clé garde ses textes", r["inconnu"]["label"] == "Truc" and r["inconnu"]["hint"] == "Aide")
    check("4c langue inconnue ou absente = français", CAT.effets(cat, "de") is cat and CAT.effets(cat, None) is cat)

    print(f"\n=== {ok} passed, {fail} failed ===")
    return fail


def test_i18n_l4_serveur():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
