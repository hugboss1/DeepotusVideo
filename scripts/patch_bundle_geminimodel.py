# -*- coding: utf-8 -*-
# scripts/patch_bundle_geminimodel.py
"""Assert-guarded patcher : chantier W-c — champ « Gemini — modèle » dans
Settings → Clés.

BASELINE : bundle POST-patch version v1.20.0 (chaîne … → quickvoice →
voicenode → videomodel → voicemodel → version, cf. mémoire chantier W-b).
Backup dédié : .js.bak_geminimodel (état juste avant CE patch).
Plan : docs/superpowers/plans/2026-07-22-modeles-generation-onthefly.md (§3).

Section unique :
- G1 : le tableau déclaratif Fu des clés Settings (composant bm) gagne une
  entrée GEMINI_MODEL juste sous la clé Google Gemini. Le backend accepte
  déjà cette clé (_ALLOWED_ENV_KEYS, v1.8) : lecture masquée via GET
  /settings/keys, écriture via POST /settings/keys → .env du DATA_ROOT,
  restart requis (bandeau existant du panneau). Défaut serveur si vide :
  gemini-flash-latest (config.py, W-c).

Run : python scripts/patch_bundle_geminimodel.py
Rejouer la chaîne : python scripts/repatch_all.py --from geminimodel
"""
import pathlib
import shutil
import sys

BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
BAK = BUNDLE.parent / (BUNDLE.name + ".bak_geminimodel")

MARKER = "GEMINI_MODEL"


def guard_downstream(bak):
    """Refuse de tourner si un patcher AVAL est déjà passé — voir repatch_all.py."""
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval détecté : {other.name} (plus récent que "
                f"{bak.name}). Utiliser : python scripts/repatch_all.py --from "
                f"{bak.name.rsplit('.bak_', 1)[1]}")


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def main():
    if "--force-unchained" not in sys.argv:
        guard_downstream(BAK)
    if not BAK.exists():
        shutil.copy2(BUNDLE, BAK)
        print("backup ->", BAK)
    else:
        shutil.copy2(BAK, BUNDLE)
        print("restore <-", BAK.name)
    s = BUNDLE.read_text(encoding="utf-8")
    if MARKER in s:
        raise SystemExit(f"[sanity] marqueur {MARKER} déjà présent après restore. Aborting.")

    # G1 — entrée GEMINI_MODEL sous la clé Google Gemini dans Fu.
    a = ('{k:"GEMINI_API_KEY",label:"Google Gemini",'
         'why:"summary + plans (cloud)",health:"gemini_enabled"}')
    r = (a
         + ',{k:"GEMINI_MODEL",label:"Gemini — modèle",'
           'why:"vide = gemini-flash-latest (alias stable, suit les mises à '
           'jour) ; pin possible, ex. gemini-2.0-flash",'
           'health:"gemini_enabled"}')
    s = apply(s, a, r, "G1-fu-entry")

    BUNDLE.write_text(s, encoding="utf-8")
    print("OK — bundle patched (geminimodel W-c). Size:", BUNDLE.stat().st_size)


if __name__ == "__main__":
    main()
