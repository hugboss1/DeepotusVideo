# -*- coding: utf-8 -*-
"""Le rafraichissement News fond les doublons (plan 2026-09-03, tache 3).

Banc-miroir : il LIT le fichier `cache.json` ecrit sur le disque, pas la
valeur rendue par la methode. Le reseau est remplace : `_fetch_rss` est
monkeypatche, aucune requete ne sort.

Run (depuis backend/) : python tests/test_news_service_dedup.py
"""
import json
import os
import pathlib
import sys
import tempfile

import pytest

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp   # P1 #5 : jamais le .env ni le dossier news/ reels
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FLUX = {
    "s1": [{"id": "a1", "source_id": "s1", "source_name": "CoinDesk",
            "title": "Bitcoin tumbles below $60,000 as ETF outflows accelerate",
            "summary": "", "link": "https://c/1",
            "published": "2026-09-03T08:00:00+00:00", "image": None}],
    "s2": [{"id": "b1", "source_id": "s2", "source_name": "Decrypt",
            "title": "Bitcoin falls under $60,000 amid accelerating ETF outflows",
            "summary": "", "link": "https://d/1",
            "published": "2026-09-03T11:00:00+00:00", "image": None}],
    "s3": [{"id": "c1", "source_id": "s3", "source_name": "BBC World",
            "title": "Storm Bernard floods southern Spain",
            "summary": "", "link": "https://b/1",
            "published": "2026-09-03T10:00:00+00:00", "image": None}],
}


def _service(monkeypatch):
    from app.services.news_service import NewsService
    svc = NewsService()
    svc._save_sources([
        {"id": k, "type": "rss", "url": f"https://{k}/rss", "name": k,
         "enabled": True} for k in FLUX
    ])
    monkeypatch.setattr(svc, "_fetch_rss", lambda src: list(FLUX[src["id"]]))
    return svc


def test_le_cache_ecrit_ne_contient_plus_le_doublon(monkeypatch):
    svc = _service(monkeypatch)
    svc._refresh_blocking()
    cache = json.loads(svc.cache_path.read_text(encoding="utf-8"))
    titres = [i["title"] for i in cache["items"]]
    assert len(titres) == 2, titres
    assert "Bitcoin falls under $60,000 amid accelerating ETF outflows" in titres
    assert "Bitcoin tumbles below $60,000 as ETF outflows accelerate" \
        not in titres


def test_le_gardant_porte_le_media_fondu_dans_le_cache(monkeypatch):
    svc = _service(monkeypatch)
    svc._refresh_blocking()
    cache = json.loads(svc.cache_path.read_text(encoding="utf-8"))
    garde = [i for i in cache["items"] if i["source_name"] == "Decrypt"][0]
    assert garde["doublons"] == [{"source_name": "CoinDesk",
                                  "title": FLUX["s1"][0]["title"],
                                  "link": "https://c/1"}]


def test_le_rapport_de_rafraichissement_compte_les_fondus(monkeypatch):
    svc = _service(monkeypatch)
    rapport = svc._refresh_blocking()
    assert rapport["item_count"] == 2
    assert rapport["merged_count"] == 1


def test_le_plafond_de_300_s_applique_apres_le_dedoublonnage(monkeypatch):
    from app.services.news_service import MAX_ITEMS
    faux = [{"id": f"x{i}", "source_id": "s1", "source_name": "CoinDesk",
             "title": f"Depeche numero {i} sur un sujet parfaitement distinct",
             "summary": "", "link": f"https://c/{i}",
             "published": f"2026-09-0{1 + i % 3}T0{i % 10}:00:00+00:00",
             "image": None}
            for i in range(MAX_ITEMS + 40)]
    svc = _service(monkeypatch)
    monkeypatch.setattr(svc, "_fetch_rss",
                        lambda src: faux if src["id"] == "s1" else [])
    svc._refresh_blocking()
    cache = json.loads(svc.cache_path.read_text(encoding="utf-8"))
    assert len(cache["items"]) == MAX_ITEMS


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
