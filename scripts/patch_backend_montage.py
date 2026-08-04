#!/usr/bin/env python3
"""Branche le routeur montage (app/services/montage_service.py) dans app/main.py.

Insertion idempotente juste après l'include du routeur API principal :
    app.include_router(router, prefix="/api")
→ ajoute l'import + app.include_router(montage_router, prefix="/api/montage").

Usage :
    python scripts/patch_backend_montage.py                # dépôt
    python scripts/patch_backend_montage.py --root <dir>   # autre arbre (app)
    python scripts/patch_backend_montage.py [--root d] --strip
"""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR = 'app.include_router(router, prefix="/api")'
BEGIN = "# __DZ_MONTAGE_ROUTER_BEGIN__"
END = "# __DZ_MONTAGE_ROUTER_END__"
BLOCK = f"""{BEGIN}
from app.services.montage_service import router as montage_router
app.include_router(montage_router, prefix="/api/montage")
{END}"""


def main() -> None:
    args = sys.argv[1:]
    root = REPO
    if "--root" in args:
        root = os.path.abspath(args[args.index("--root") + 1])
    strip = "--strip" in args
    main_py = os.path.join(root, "backend", "app", "main.py")

    with open(main_py, "r", encoding="utf-8") as f:
        text = f.read()

    if strip:
        if BEGIN not in text:
            print("main.py: rien à retirer")
            return
        head, rest = text.split(BEGIN, 1)
        _, tail = rest.split(END, 1)
        text = head.rstrip() + "\n" + tail.lstrip("\n")
        with open(main_py, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"retiré de {main_py}")
        return

    if BEGIN in text:
        print("main.py: déjà branché")
        return
    if text.count(ANCHOR) != 1:
        sys.exit(f"ancre introuvable ou multiple dans {main_py} — abandon")
    text = text.replace(ANCHOR, ANCHOR + "\n" + BLOCK)
    with open(main_py, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"branché dans {main_py}")


if __name__ == "__main__":
    main()
