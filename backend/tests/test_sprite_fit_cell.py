"""_fit_into_cell ne double plus l'alpha (22/10/2026, relevé pendant t274).

`cell.paste(im2, (x, y), im2)` prenait la frame comme son propre masque : l'alpha était appliqué deux fois, un bord à
128 retombait à 64. Touchait les planches du Sprite Lab (/assets/sprite) et des séquences CC0 importées
(particle_service.import_anim) ; `_place_into_cell` (natif) l'évitait déjà.

  cd backend
  %LOCALAPPDATA%\\DeepotusVideoGen\\runtime\\python\\python.exe -m pytest tests/test_sprite_fit_cell.py -v
"""
# Amorce : le python embarque ignore PYTHONPATH (._pth)
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))

from PIL import Image

from app.services import sprite_service as S


def _frame_demi_alpha(w=16, h=16):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            im.putpixel((x, y), (200, 40, 10, 128))
    return im


def test_une_frame_de_la_taille_de_la_cellule_ressort_identique():
    im = _frame_demi_alpha()
    for align in ("center", "feet"):
        for resample in (None, Image.NEAREST):
            cell = S._fit_into_cell(im, 16, align, resample)
            assert cell.mode == "RGBA" and cell.size == (16, 16)
            assert cell.tobytes() == im.tobytes(), (align, resample)


def test_un_bord_a_128_reste_a_128_apres_agrandissement():
    # NEAREST ×2 : chaque pixel source est recopié tel quel, l'alpha doit rester 128 partout dans la frame
    cell = S._fit_into_cell(_frame_demi_alpha(8, 8), 16, "center", Image.NEAREST)
    assert set(cell.getchannel("A").tobytes()) == {128}


def test_le_vide_autour_reste_transparent_et_la_frame_garde_son_alpha():
    # frame 16×8 dans une cellule 16 : bande de 4 px vide en haut et en bas (center), 8 en haut (feet)
    im = _frame_demi_alpha(16, 8)
    centre = S._fit_into_cell(im, 16, "center", Image.NEAREST)
    assert centre.getpixel((5, 1)) == (0, 0, 0, 0) and centre.getpixel((5, 14)) == (0, 0, 0, 0)
    assert centre.getpixel((5, 7)) == (200, 40, 10, 128)
    pieds = S._fit_into_cell(im, 16, "feet", Image.NEAREST)
    assert pieds.getpixel((5, 7)) == (0, 0, 0, 0) and pieds.getpixel((5, 15)) == (200, 40, 10, 128)
