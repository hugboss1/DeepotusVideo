# Studio (éditeur de nœuds) — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Un run du Studio ne repaie que ce qui a bougé, chaque nœud garde la
pile de ses résultats, un graphe JSON s'importe, la preview se parcourt image
par image ; puis une recette se lance depuis ailleurs, deux moteurs se
départagent en duel, et un rendu de la Bibliothèque ouvre un graphe neuf.

**Architecture:** Le Studio est ENTIÈREMENT dans le bundle minifié
`frontend/dist/assets/index-BEOJX8L5.js` — registre `Me` (34 types, 8
catégories), compilateur `Mh(e)` (30 828 caractères, 6 branches), écran `Lh`,
inspecteur `$h`/`Yh`/`Oh`, tiroir de résultat `Jh`. On ne réécrit pas le
compilateur : on **substitue** la valeur de slot d'un nœud dont le résultat est
épinglé par `{source_kind:"job"|"upload"}`, que `pipeline.render_template`
résout DÉJÀ sans appeler le moindre fournisseur
(`backend/app/services/pipeline.py:1069-1083`). Côté serveur : un manifeste de
parties par rendu (`outputs/_parts/<job>.json`), un registre de nœuds miroité
en JSON, une validation d'import, et une route de recette qui rejoue une
compilation figée.

**Tech Stack:** Python 3.13 EMBARQUÉ, stdlib + Pillow (**pas de numpy**),
FastAPI, SQLAlchemy/aiosqlite ; bundle JS minifié patché par
`scripts/patch_bundle_<tag>.py` chaînés par mtime ; Node 24.18.0 pour
`node --check` et pour exécuter les helpers extraits du bundle au banc ;
Windows 11, PowerShell.

**Comment lancer un banc** (rappel unique, valable pour tout le plan) : depuis
`backend/`, `python tests/test_<x>.py`. Un fichier = un processus. **Jamais**
`pytest tests`. Si `python` du PATH n'a pas les dépendances, utiliser
l'interpréteur embarqué :
`%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe`.

---

## Périmètre

Issu de `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`,
`### R2. Studio — réponses (03/09/2026)`. Rien d'autre n'entre.

**Lot 1 — parité**, dans cet ordre :

| # | Bac | Ce que ça fait |
|---|---|---|
| P1 | Épinglage du résultat d'un nœud | Un nœud de génération dont le résultat existe garde ce résultat tant que ses entrées et réglages n'ont pas bougé ; épingle manuelle ; « ce run coûte X (Y nœuds réutilisés) » avant tir. |
| P2 | Historique des rendus par nœud | La pile des résultats passés d'un nœud ; choisir lequel alimente l'aval. S'appuie sur P1. |
| P3 | Import d'un graphe JSON | L'export existe ; l'import valide contre le registre des nœuds et remonte les sources manquantes. |
| P4 | Scrub image par image | Le lecteur du tiroir de résultat lit ; il doit parcourir. |

**Lot 2 — différenciant** :

| # | Bac | Ce que ça fait |
|---|---|---|
| D1 | Recette lançable | Un graphe sauvegardé exposé comme recette dont seules les sources changent ; route « lancer la recette N avec ces assets ». |
| D2 | Duel de moteurs | Un nœud de génération marqué « duel » tire sur deux modèles ; bascule A/B avec coût et durée ; le gagnant devient le résultat épinglé (P1). |
| D3 | Départ depuis un rendu | « Envoyer vers Studio » sur un rendu pose un nœud Rendu existant dans un graphe NEUF (distinct de « Rouvrir dans Studio », qui recharge le graphe source). |

**Écarté** — voir la section « Écarté » en fin de plan : E1 sous-graphes,
E2 canevas infini, E3 nœuds de contrôle, E4 comparaison à N > 2 moteurs.
Aucune tâche.

---

## Coût de patch

Le Studio n'a pas de source : il vit dans un bundle minifié. Toute évolution
d'écran passe par un `scripts/patch_bundle_<tag>.py` — **tag NEUF, backup dédié
`.js.bak_<tag>`, position EN QUEUE de chaîne, chaque ancre trouvée exactement
une fois sinon abandon sans écrire**, et rejeu par
`python scripts/repatch_all.py --from <tag>`.

Chaîne mesurée le 03/09/2026 (`python scripts/repatch_all.py --list`) :

```
dzrailmotion     OK (bak 1391953 o)
version          OK (bak 1393303 o)
dznodecat        OK (bak 1393303 o)
seedance25       OK (bak 1394540 o)
```

La queue est `seedance25`. Les 7 tags de ce plan s'ajoutent après, dans
l'ordre : `studiopin`, `studiohist`, `studioimp`, `studioscrub`,
`studiorecette`, `studioduel`, `studiosend`.

**Prix tâche par tâche** (une greffe = un couple ancre → remplacement ; toutes
les ancres ci-dessous ont été comptées le 03/09 et valent 1) :

| Tâche | Tag | Greffes | Prix, dit franchement |
|---|---|---|---|
| T3 | `studiopin` | 9 | Cher. Le socle : helpers, 5 sites de substitution/cartographie répartis entre `Mh` (ligne 231) et `dzCompose` (ligne 46), le champ `node_slots` dans `renderLayoutTemplate` (ligne 44), la remise à zéro en tête de `Mh`. Deux blocs appartiennent à d'AUTRES patchers (`spatialports` possède `dzCompose`/`srcFor`, `keepstate` possède `var __dzG=null,__dzKeep={};`) : si l'un des deux est un jour relancé seul, ces greffes disparaissent en silence. C'est le prix, il est nommé, et `guard_downstream` l'empêche par accident. |
| T4 | `studiopin` (suite) | +5 = 14 | Moyen. Même patcher étendu : récolte après run, puce dans l'entête `Oh`, panneau dans `$h`, chiffre dans `DzStudioEst`. Un patcher restaure son `.bak` puis rejoue TOUT : étendre coûte une relance, pas une nouvelle chaîne. |
| T5 | `studiohist` | 3 | Bon marché. Un panneau ajouté à côté de celui de T4, plus l'écriture de la pile à la récolte (dans les helpers de T3 — édition in-bloc de `studiopin`, donc `studiopin` ne doit plus être relancé seul après T5). |
| T7 | `studioimp` | 2 | Très bon marché. Un bouton dans la barre du haut, à côté de `DzOpenGraph`, plus un `input file` caché. Tout le travail est backend (T6). |
| T8 | `studioscrub` | 2 | Bon marché. Le `<video>` du tiroir `Jh` (ligne 283) devient un composant `DzScrub` ; ancre unique, aucun autre patcher ne touche `Jh`. |
| T10 | `studiorecette` | 3 | Moyen. Une prise de capture dans `renderLayoutTemplate` — même fonction que la greffe S8 de T3, mais sur une ancre disjointe (l'en-tête, pas le corps de requête), donc aucune édition in-bloc — plus un bouton et un formulaire de trous. |
| T11 | `studioduel` | 1 | Très bon marché. Un panneau autonome monté par `$h` **à côté** du panneau `DzImageGenPanel` — on ne touche PAS au bloc de `patch_bundle_imagegen.py`. C'est le choix qui rend D2 pas cher. |
| T12 | `studiosend` | 1 | Très bon marché. Une entrée dans le menu « Envoyer vers… » (`__dzSendTo`, ligne 285), branche `render`. |

**Ce qui n'est PAS payé en patch** : T2, T6, T9 (backend pur), et T1 (mesure).

**Pièges de patch, hérités et mesurés le 03/09** :

- Le bundle est en **CRLF pur** (11 884 CRLF, 0 LF isolé, 0 CR isolé,
  1 395 299 octets). Une ancre qui traverse un saut de ligne s'écrit `\r\n` :
  en `\n` elle ne matche pas. Lire et écrire avec
  `open(..., encoding="utf-8", newline="")`.
- **Ne jamais imprimer une ancre accentuée** : la console Windows est en
  cp1252 et le patcher meurt sur un `UnicodeEncodeError` avant d'écrire.
  `patch_bundle_libsend.py` le dit déjà dans son en-tête.
- `patch_bundle_sonvfx.py` rafraîchit son bloc EN PLACE ; aucun tag de ce plan
  n'écrit dans ce bloc, donc `scripts/reapply_inblock_patches.py` ne concerne
  pas ce chantier. Le vérifier reste gratuit.
- Vérifier un changement de bundle **par inventaire**, jamais à l'œil
  (`README.md` §« Patching the compiled UI ») : la taille et les compteurs de
  marqueurs ne montrent pas une perte.
- Les `POST_COUNTS` de chaque patcher sont des compteurs d'identifiants
  **comptés à la main** dans le code injecté. Un échec
  `post <sonde> x<N> (want <M>)` après écriture restaure le bundle et ne veut
  pas dire que la greffe est fausse : il dit que la constante ne colle pas.
  Le remède est de vérifier laquelle des deux a raison —
  `grep -o "<sonde>" frontend/dist/assets/index-BEOJX8L5.js.bak_<tag> | wc -l`
  donne le compte AVANT le patch, et la différence doit être exactement le
  nombre d'occurrences que la greffe ajoute — puis de corriger le nombre, pas
  d'ôter la sonde.

---

## Références vérifiées

Deux seulement, relues le 03/09/2026 et déjà consignées dans `R2` :

- **ComfyUI** (docs.comfy.org, 03/09/2026) : met en cache les sorties et ne
  ré-exécute que les nœuds dont une entrée ou un réglage a changé, en remontant
  depuis les nœuds de sortie ; un nœud peut redéfinir `IS_CHANGED`.
  → **Ce qu'on en prend** : l'EFFET (un run ne repaie que ce qui a bougé) et
  l'idée d'une empreinte redéfinissable par nœud (ici : `pin.lock`).
- **n8n** (docs.n8n.io, 03/09/2026) : exécutions partielles (« Execute step »
  exécute un nœud et les nœuds amont nécessaires) ; **épinglage des données** —
  la sortie d'un nœud est figée et substituée aux runs suivants au lieu de
  rappeler le service ; rechargement des données d'une exécution passée.
  → **Ce qu'on en prend** : le MÉCANISME (substitution d'une sortie figée) et
  le rechargement d'une exécution passée (P2).

Tout le reste — Flora, Weavy, TouchDesigner, Cavalry — est **de mémoire, à
vérifier**, et n'est utilisé nulle part comme argument. La réponse 3 (« graphe
strict, pas de canevas infini ») clôt le sujet.

---

## Lot 1 — parité

### Task 1 : Mesurer, puis trancher — un job par nœud, ou une empreinte ?

**Files:**
- Create: `scripts/qa/mesure_studio.py`
- Create: `backend/tests/test_studio_pin.py`

P1 exige de savoir, avant un run, ce qui peut être réutilisé. Deux
architectures sont possibles ; la décision change tout le reste du lot, donc
**on mesure d'abord**.

**Option A — un job par nœud de génération.** Le backend orchestre le graphe
nœud par nœud : chaque nœud de génération devient un `JobRecord` avec un
`node_id`, un ordonnanceur suit les arêtes, et un cache par nœud décide de
rejouer ou non. C'est l'architecture ComfyUI.

**Option B — une empreinte des entrées stockée avec le résultat.** Le
compilateur calcule, pour chaque nœud, une empreinte du sous-graphe amont
(types + props + arêtes) ; le résultat produit est rangé dans les props du
nœud avec cette empreinte ; au run suivant, si l'empreinte n'a pas bougé, la
valeur de slot du nœud est remplacée par le résultat déjà produit. C'est le
mécanisme n8n.

**Ce que le code permet aujourd'hui** (à re-mesurer en étape 2) :

| Mesure | Valeur au 03/09/2026 | Ce qu'elle dit |
|---|---|---|
| `pipeline.render_template` résout `source_kind="job"` en lisant `final_video_path` d'un `JobRecord`, sans appeler aucun fournisseur | `pipeline.py:1069-1083` | La substitution de B est **gratuite côté serveur**. Rien à écrire. |
| `Mh` compte 6 branches `ok:!0`, 8 refus `ok:!1`, 30 828 caractères | bundle ligne 231 | A demande de réécrire les 6 branches en un plan d'exécution : c'est réécrire le compilateur entier. |
| Sites qui posent une valeur `source_kind:"seedance"` ou `"heygen"` | 3 + 1 = **4** | B ne touche que 4 endroits. |
| `srcFor(node)` dans `dzCompose` est l'entonnoir UNIQUE de la branche Composition, et renvoie déjà `{source_kind:"job",job_id}` pour Rendu existant / Animation / UGC | bundle ligne 46 | La greffe la plus lourde de B tient en une ligne. |
| Les nœuds image (`ImageGen`, `ImageEdit`, `Variations`, `RemoveBG`, `Upscale`, `CropFormat`) rangent DÉJÀ leur résultat dans `props.filename` et tirent par nœud depuis l'inspecteur | `scripts/patch_bundle_imagegen.py` | Le précédent de B existe et tourne depuis un mois. |
| Colonnes de `jobs` à ajouter pour A | `node_id`, `graph_id`, `input_sig` (3 migrations) ; pour B : **0** | A touche le modèle de données, B non. |
| Le lien nœud → sous-rendu existe-t-il ? | **Non** : le sous-job reçoit `composition_id` et `composition_layout=template_id`, jamais le nom de slot (`pipeline.py:1105-1113`) | Les DEUX options doivent le créer. C'est la seule dette commune. |

**Verdict : Option B.** A coûte le compilateur, trois colonnes et un
ordonnanceur pour un gain nul sur la question posée (« ne pas repayer ») ; B
coûte 4 substitutions et un manifeste, et s'appuie sur une résolution serveur
déjà écrite et déjà éprouvée. La dette commune (nœud → sous-rendu) est traitée
en T2 par un manifeste de parties, sans migration.

- [ ] **Step 1 : écrire le mesureur**

Créer `scripts/qa/mesure_studio.py` :

```python
# -*- coding: utf-8 -*-
# scripts/qa/mesure_studio.py
"""Les chiffres sur lesquels repose l'arbitrage P1 du plan Studio.

Ne modifie rien. A relancer avant d'executer le plan : si un chiffre a bouge,
l'arbitrage est a refaire AVANT d'ecrire une ligne de patcher.

Run : python scripts/qa/mesure_studio.py
"""
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
PIPELINE = RACINE / "backend" / "app" / "services" / "pipeline.py"

ATTENDU = {
    "types_de_noeuds": 34,
    "branches_Mh_ok": 6,
    "refus_Mh": 8,
    "sites_seedance": 3,
    "sites_heygen": 1,
    "srcFor": 1,
    "resolution_job_serveur": 1,
    "slot_name_sur_le_sous_job": 0,
}


def mesures():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    i = s.index("function Mh(e){")
    j = s.index("function Dh(e){")
    mh = s[i:j]
    k = s.index('Me={Image:{cat:"source",title:"Image"')
    reg = s[k:k + 9000]
    noms = re.findall(
        r'([A-Za-z]+):\{cat:"(source|gen|edit|compose|audio|motion|master|output)"',
        reg)
    p = PIPELINE.read_text(encoding="utf-8")
    return {
        "types_de_noeuds": len(noms),
        "branches_Mh_ok": mh.count("ok:!0"),
        "refus_Mh": mh.count("ok:!1"),
        "sites_seedance": s.count('source_kind:"seedance"'),
        "sites_heygen": s.count('source_kind:"heygen"'),
        "srcFor": s.count("  function srcFor(node){"),
        "resolution_job_serveur": p.count('elif kind == "job":'),
        "slot_name_sur_le_sous_job": p.count("jr.slot_name"),
        "_taille_Mh": len(mh),
    }


def main():
    m = mesures()
    ecarts = []
    for cle, attendu in ATTENDU.items():
        got = m[cle]
        marque = "OK " if got == attendu else "ECART"
        if got != attendu:
            ecarts.append(f"{cle}: {got} au lieu de {attendu}")
        print(f"{marque} {cle:28s} {got}")
    print(f"    taille de Mh              {m['_taille_Mh']} caracteres")
    if ecarts:
        print("\nARBITRAGE A REFAIRE — le code a bouge :")
        for e in ecarts:
            print("  " + e)
        return 1
    print("\nArbitrage du plan valide : option B (empreinte + substitution).")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
```

- [ ] **Step 2 : lancer le mesureur**

Run : `python scripts/qa/mesure_studio.py`

Attendu (exactement) :

```
OK  types_de_noeuds              34
OK  branches_Mh_ok               6
OK  refus_Mh                     8
OK  sites_seedance               3
OK  sites_heygen                 1
OK  srcFor                       1
OK  resolution_job_serveur       1
OK  slot_name_sur_le_sous_job    0
    taille de Mh              30828 caracteres

Arbitrage du plan valide : option B (empreinte + substitution).
```

Si une ligne dit `ECART`, **s'arrêter** : le plan repose sur ces chiffres.

- [ ] **Step 3 : écrire le banc qui fige la vérité serveur**

Créer `backend/tests/test_studio_pin.py` avec sa seule section A pour l'instant :

```python
# -*- coding: utf-8 -*-
"""Studio P1 — l'epinglage d'un resultat de noeud.

Section A : la verite SERVEUR sur laquelle repose l'arbitrage — un slot
`source_kind="job"` est resolu en lisant le fichier d'un rendu fini, sans
appeler le moindre fournisseur. C'est ce qui rend la substitution gratuite.
Les sections suivantes arrivent en T2 (manifeste), T3 et T4 (bundle).

Run : python tests/test_studio_pin.py  (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent


# ── A. la resolution serveur d'un slot deja rendu ───────────────────────────

def test_un_slot_job_se_resout_sans_fournisseur():
    """Le corps de `render_template` qui traite `source_kind == "job"` lit un
    JobRecord et prend son fichier — il n'y a NI `self.run(` NI
    `self.run_heygen(` dans cette branche. C'est la mesure qui autorise la
    substitution : epingler ne coute rien au serveur."""
    src = (RACINE / "backend" / "app" / "services"
           / "pipeline.py").read_text(encoding="utf-8")
    deb = src.index('elif kind == "job":')
    fin = src.index('elif kind == "text":', deb)
    branche = src[deb:fin]
    assert "session.get(JobRecord, sv.job_id)" in branche
    assert "final_video_path or jr.video_path" in branche
    assert "self.run(" not in branche and "self.run_heygen(" not in branche
    # et le refus est PARLANT quand le rendu epingle a disparu
    assert "has no video" in branche and "job video missing" in branche


def test_le_schema_accepte_bien_le_genre_job():
    from app.models.schemas import TemplateSlotValue
    v = TemplateSlotValue(source_kind="job", job_id="abc")
    assert v.job_id == "abc"
    with pytest.raises(Exception):
        TemplateSlotValue(source_kind="inconnu")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] **Step 4 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_pin.py`

Attendu : `2 passed`.

- [ ] **Step 5 : commit**

```
git add scripts/qa/mesure_studio.py backend/tests/test_studio_pin.py
git commit -m 'studio : mesurer et trancher larchitecture de lepinglage' -m 'Deux architectures pour P1 : un job par noeud (ComfyUI) ou une empreinte des entrees rangee avec le resultat (n8n). Le mesureur donne les huit chiffres qui tranchent : le serveur resout deja un slot source_kind=job sans appeler de fournisseur, Mh a 6 branches et 30 828 caracteres, et il ny a que 4 sites qui posent une valeur seedance ou heygen. Option B, donc : 4 substitutions contre un compilateur reecrit et trois colonnes.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 2 : Le manifeste des parties — quel nœud a produit quel sous-rendu

**Files:**
- Modify: `backend/app/models/schemas.py:492-509` (`TemplateRenderRequest`)
- Modify: `backend/app/services/pipeline.py:66-77` (à côté de `_save_source_graph`)
- Modify: `backend/app/services/pipeline.py:955-975` (signature de `render_template`)
- Modify: `backend/app/services/pipeline.py:1098-1124` (phase 2, après la boucle des sous-jobs)
- Modify: `backend/app/api/routes.py:157-224` (route de rendu : passer `node_slots`)
- Modify: `backend/app/api/routes.py:227-241` (poser `/jobs/{job_id}/parts` après `/graph`)
- Test: `backend/tests/test_studio_pin.py` (section B)

C'est la dette commune aux deux options mesurée en T1 : un sous-rendu porte
`composition_id` mais **pas** le nom de slot, donc rien ne relie un rendu au
nœud qui l'a demandé. Le client connaît cette carte (c'est lui qui compile) :
il l'envoie, le serveur la range à côté des sous-rendus. Aucune migration.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_studio_pin.py`, avant le `if __name__` :

```python
# ── B. le manifeste des parties ─────────────────────────────────────────────

class _FauxJob:
    def __init__(self, jid, prov, dur):
        self.id, self.provider, self.duration_s = jid, prov, dur


def test_le_manifeste_relie_le_slot_au_noeud_et_au_sous_rendu():
    from app.services.pipeline import _parts_manifest
    m = _parts_manifest(
        {"anim": "n_seed", "ugc": "n_up"},
        {"anim": _FauxJob("j-anim", "seedance", 10)},
        {"ugc": "C:/x/ugc.mp4"})
    assert [p["slot"] for p in m] == ["anim", "ugc"], "trie par slot"
    a, u = m
    assert a == {"slot": "anim", "node_id": "n_seed", "job_id": "j-anim",
                 "provider": "seedance", "duration_s": 10, "kind": "generated"}
    assert u == {"slot": "ugc", "node_id": "n_up", "job_id": None,
                 "provider": None, "duration_s": None, "kind": "static"}


def test_le_manifeste_survit_a_une_carte_absente():
    """Un rendu lance hors Studio n'envoie pas de carte : le manifeste existe
    quand meme, node_id a None. Sans quoi la route repondrait 404 sur des
    rendus parfaitement valides."""
    from app.services.pipeline import _parts_manifest
    m = _parts_manifest(None, {"main": _FauxJob("j1", "heygen", 7)}, {})
    assert m == [{"slot": "main", "node_id": None, "job_id": "j1",
                  "provider": "heygen", "duration_s": 7, "kind": "generated"}]


def test_la_route_des_parties():
    import asyncio
    import json as _json
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from app.config import settings
        from app.main import app
        from app.services.pipeline import _save_parts
        from app.services.storage import init_db
        await init_db()
        _save_parts("job-x", [{"slot": "anim", "node_id": "n1",
                               "job_id": "j-anim", "provider": "seedance",
                               "duration_s": 10, "kind": "generated"}])
        ecrit = settings.outputs_path / "_parts" / "job-x.json"
        assert ecrit.is_file(), ecrit
        assert _json.loads(ecrit.read_text(encoding="utf-8"))[0]["slot"] == "anim"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.get("/api/jobs/job-x/parts")
            assert r.status_code == 200, r.text
            assert r.json()["parts"][0]["node_id"] == "n1"
            # un rendu sans parties : 404 qui le DIT
            r = await c.get("/api/jobs/inconnu/parts")
            assert r.status_code == 404 and "parts" in r.json()["detail"].lower()
            # traversee de chemin refusee : le nom est reduit a son basename
            r = await c.get("/api/jobs/..%2F..%2Fetc/parts")
            assert r.status_code in (404, 400), r.text

    asyncio.run(scenario())


def test_la_requete_de_rendu_porte_la_carte():
    from app.models.schemas import TemplateRenderRequest
    q = TemplateRenderRequest(template_id="t", slot_values={},
                              node_slots={"anim": "n1"})
    assert q.node_slots == {"anim": "n1"}
    assert TemplateRenderRequest(template_id="t", slot_values={}).node_slots is None
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_studio_pin.py`

Attendu : `4 failed, 2 passed` — les quatre échecs disent
`ImportError: cannot import name '_parts_manifest'`, `... '_save_parts'`,
`404` sur `/api/jobs/job-x/parts`, et
`ValidationError ... node_slots ... extra_forbidden` ou `AttributeError`.

- [ ] **Step 3 : le champ dans le schéma**

Dans `backend/app/models/schemas.py`, classe `TemplateRenderRequest`
(ligne 492), ajouter après la ligne `source_graph: Optional[dict] = None` :

```python
    # P1 (v1.20) — carte {slot: node_id} du graphe qui a compile ce rendu.
    # Le serveur ne s'en sert que pour ecrire le manifeste des parties : c'est
    # ce qui permet au Studio d'epingler le resultat d'UN noeud.
    node_slots: Optional[dict[str, str]] = None
```

- [ ] **Step 4 : les deux fonctions du pipeline**

Dans `backend/app/services/pipeline.py`, juste après `_save_source_graph`
(qui finit ligne 77), ajouter :

```python
def _parts_manifest(node_slots, generated: dict, static: dict) -> list[dict]:
    """Une ligne par slot rempli : le noeud qui l'a demande, le sous-rendu
    produit (s'il y en a eu un), son fournisseur et sa duree.

    `generated` : {slot: JobRecord} — les slots qui ont coute de l'argent.
    `static`    : {slot: chemin}    — televerses, rendus reutilises, epingles.
    Une carte absente (rendu lance hors Studio) donne node_id=None, jamais
    une absence de ligne : le manifeste doit exister pour tout rendu template.
    """
    ns = node_slots or {}
    lignes = []
    for slot in sorted(set(generated) | set(static)):
        j = generated.get(slot)
        lignes.append({
            "slot": slot,
            "node_id": ns.get(slot) or None,
            "job_id": getattr(j, "id", None) if j is not None else None,
            "provider": getattr(j, "provider", None) if j is not None else None,
            "duration_s": getattr(j, "duration_s", None) if j is not None else None,
            "kind": "generated" if j is not None else "static",
        })
    return lignes


def _save_parts(job_id: str, parts: list) -> None:
    """Range le manifeste a cote du graphe source, meme dossier de donnees."""
    if not parts:
        return
    try:
        import json
        d = settings.outputs_path / "_parts"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{Path(job_id).name}.json").write_text(
            json.dumps(parts, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"parts save failed for {job_id}: {e}")
```

- [ ] **Step 5 : brancher le manifeste dans `render_template`**

Dans `backend/app/services/pipeline.py`, signature de `render_template`
(ligne ~964), ajouter le paramètre après `source_graph`:

```python
        source_graph: dict | None = None,
        node_slots: dict | None = None,
```

Puis, dans la phase 2, retenir les enregistrements des sous-rendus au passage.
La boucle existante commence par (ligne ~1099) :

```python
            resolved: dict[str, dict] = {}
            caption: str | None = None
            for sname, task in tasks.items():
```

La remplacer par (une ligne ajoutée) :

```python
            resolved: dict[str, dict] = {}
            caption: str | None = None
            _sous_rendus: dict = {}          # P1 — slot -> JobRecord paye
            for sname, task in tasks.items():
```

Dans le corps de cette même boucle, la ligne
`jr.composition_layout = template_id` devient deux lignes :

```python
                    jr.composition_layout = template_id
                    _sous_rendus[sname] = jr
```

Enfin, juste après la boucle
`for sname, tv in text_values.items(): resolved[sname] = {"text": tv}`
(ligne ~1123), insérer :

```python
            # P1 — qui a produit quoi. Ecrit AVANT le compositing : un ffmpeg
            # qui echoue ensuite laisse les sous-rendus PAYES epinglables.
            _save_parts(job_id, _parts_manifest(
                node_slots, _sous_rendus,
                {k: str(v) for k, v in static_paths.items()}))
```

- [ ] **Step 6 : la route de rendu passe la carte**

Dans `backend/app/api/routes.py`, dans `_run()` de `render_layout_template`
(ligne ~204), ajouter après `source_graph=request.source_graph,` :

```python
                node_slots=request.node_slots,
```

- [ ] **Step 7 : la route de lecture**

Dans `backend/app/api/routes.py`, juste après la route
`@router.get("/jobs/{job_id}/graph")` (qui finit ligne 240), ajouter :

```python
@router.get("/jobs/{job_id}/parts")
async def get_job_parts(job_id: str):
    """Les sous-rendus produits par un rendu Studio, avec le noeud du graphe
    qui les a demandes. C'est ce qui permet d'epingler le resultat d'UN noeud
    (P1) et d'en garder la pile (P2). 404 si le rendu n'a pas de parties :
    rendu non-template, ou anterieur a cette version."""
    import json as _json
    safe = Path(job_id).name
    p = settings.outputs_path / "_parts" / f"{safe}.json"
    if not p.is_file():
        raise HTTPException(404, "No parts for this render")
    try:
        return {"job_id": safe, "parts": _json.loads(p.read_text(encoding="utf-8"))}
    except Exception:
        raise HTTPException(500, "Parts unreadable")
```

- [ ] **Step 8 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_pin.py`

Attendu : `6 passed`.

- [ ] **Step 9 : commit**

```
git add backend/app/models/schemas.py backend/app/services/pipeline.py backend/app/api/routes.py backend/tests/test_studio_pin.py
git commit -m 'studio : le manifeste des parties, quel noeud a produit quel sous-rendu' -m 'Un sous-rendu portait composition_id mais jamais le nom de son slot : rien ne reliait un rendu au noeud qui lavait demande. Le client, qui compile, envoie la carte {slot: node_id} ; le serveur la range en outputs/_parts/<job>.json a cote du graphe source, et GET /api/jobs/{id}/parts la relit. Aucune colonne, aucune migration. Ecrit avant le compositing : un ffmpeg qui echoue laisse les sous-rendus payes epinglables.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 3 : Le patcher `studiopin` (a) — les cinq points de substitution

**Files:**
- Create: `scripts/_patch_studio.py` (harnais commun aux 7 patchers du plan)
- Create: `scripts/patch_bundle_studiopin.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (lignes 44, 46, 231)
- Test: `backend/tests/test_studio_pin.py` (section C)

Sept patchers vont suivre le même squelette (garde de chaîne, backup en queue,
parité des deltas, sondes stables, comptes après écriture). On l'écrit **une
fois**, dans `scripts/_patch_studio.py` ; chaque patcher n'est plus que ses
constantes et sa liste de couples. Prix de ce choix : le harnais devient un
fichier partagé — s'il casse, les 7 cassent. Bénéfice : 7 × 170 lignes de
copier-coller en moins, et une seule place où corriger une garde.

- [ ] **Step 1 : écrire le harnais**

Créer `scripts/_patch_studio.py` :

```python
# -*- coding: utf-8 -*-
# scripts/_patch_studio.py
"""Harnais commun aux patchers bundle du chantier Studio (plan 2026-09-03).

Un patcher = TAG, MARQUEURS, couples (tag, ancre, remplacement), sondes.
Tout le reste — garde de chaine, backup en queue, parite des deltas, comptes
apres ecriture, homogeneite des fins de ligne — vit ici.

Regles non negociables, apprises sur cette chaine :
  * le bundle est en CRLF PUR : on lit et on ecrit avec newline="" ;
  * une ancre absente ou trouvee deux fois = abandon SANS ecrire ;
  * le backup .bak_<TAG> doit rester le DERNIER maillon (mtime en queue) ;
  * on n'IMPRIME jamais une ancre : la console Windows est en cp1252.
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")


def deltas(patches):
    dc = sum(len(r) - len(a) for _t, a, r in patches)
    db = sum(len(r.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, r in patches)
    return dc, db


def eol_stats(data):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def read_src(p):
    return p.read_text(encoding="utf-8", newline="")


def resolve_root(args):
    if "--root" in args:
        return pathlib.Path(args[args.index("--root") + 1]).resolve()
    here = pathlib.Path(".").resolve()
    if (here / REL_BUNDLE).is_file():
        return here
    return pathlib.Path(__file__).resolve().parent.parent


def guard_downstream(tag, bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                f"{tag} n'est plus le dernier maillon ; relance la chaine "
                f"avec repatch_all.py --from {tag}, pas ce script seul.")


def ensure_tail_order(bak):
    stem = bak.name.rsplit(".bak_", 1)[0]
    autres = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not autres:
        return False
    haut = max(autres)
    if bak.stat().st_mtime > haut:
        return False
    t = max(time.time(), haut + 1.0)
    os.utime(bak, (t, t))
    return True


def poser(tag, marker, marker_attendu, patches, stable_probes, post_counts,
          spec_char, spec_byte, resume):
    """Applique `patches` au bundle. Rend 0, ou sort en erreur parlante."""
    args = sys.argv[1:]
    dc, db = deltas(patches)
    if "--deltas" in args:
        print(f"[{tag}] delta +{dc} car / +{db} o")
        return 0
    if spec_char is None or spec_byte is None:
        raise SystemExit(
            f"[{tag}] parite spec non figee. Lance --deltas, puis ecris en "
            f"tete du fichier : SPEC_CHAR_DELTA = {dc} et "
            f"SPEC_BYTE_DELTA = {db}.")
    if (dc, db) != (spec_char, spec_byte):
        raise SystemExit(
            f"[{tag}] parite spec rompue : calcule {dc} car / {db} o, "
            f"spec {spec_char} car / {spec_byte} o. Le patcher a ete edite "
            "sans mettre a jour son empreinte. Aborting.")

    root = resolve_root(args)
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{tag}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + tag)
    if "--force-unchained" not in args:
        guard_downstream(tag, bak)

    if "--check" in args:
        src = bak if bak.exists() else bundle
        s = read_src(src)
        if marker in s:
            raise SystemExit(
                f"[{tag}] marqueur deja present x{s.count(marker)} dans "
                f"{src.name} — double application refusee.")
        for t, ancre, _r in patches:
            n = s.count(ancre)
            if n != 1:
                raise SystemExit(f"[{t}] anchor count={n} (want 1). Aborting.")
        for nom, sonde, veut in stable_probes:
            if s.count(sonde) != veut:
                raise SystemExit(f"[sonde {nom}] count={s.count(sonde)} "
                                 f"(want {veut}). Aborting.")
        crlf, lf, cr = eol_stats(src.read_bytes())
        print(f"[{tag}] applicable sur {src}")
        print(f"[{tag}] {len(patches)} ancres OK, marqueur absent, "
              f"{len(stable_probes)} sondes aux comptes")
        print(f"[{tag}] CRLF={crlf} LF-isole={lf} CR-isole={cr} ; "
              f"delta +{dc} car / +{db} o")
        return 0

    if not bak.exists():
        if marker in read_src(bundle):
            raise SystemExit(
                f"[{tag}] marqueur present sans {bak.name} : etat ambigu, "
                "abandon sans rien ecrire.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    avant = bundle.read_bytes()
    crlf0, lf0, cr0 = eol_stats(avant)
    if lf0 or cr0:
        raise SystemExit(f"[{tag}] fins de ligne non homogenes. Aborting.")
    s = read_src(bundle)
    car0 = len(s)
    if marker in s:
        raise SystemExit(f"[{tag}] backup empoisonne (marqueur present apres "
                         "restore). Aborting.")
    for t, ancre, repl in patches:
        n = s.count(ancre)
        if n != 1:
            shutil.copy2(bak, bundle)
            raise SystemExit(f"[{t}] anchor count={n} (want 1). Bundle "
                             "restaure, rien d'ecrit.")
        s = s.replace(ancre, repl, 1)
    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)

    apres = bundle.read_bytes()
    crlf1, lf1, cr1 = eol_stats(apres)
    ennuis = []
    if (crlf1, lf1, cr1) != (crlf0, 0, 0):
        ennuis.append("fins de ligne changees")
    if len(apres) != len(avant) + db:
        ennuis.append(f"taille {len(apres)} o, attendu {len(avant) + db}")
    if len(s) != car0 + dc:
        ennuis.append(f"caracteres {len(s)}, attendu {car0 + dc}")
    if s.count(marker) != marker_attendu:
        ennuis.append(f"marqueur x{s.count(marker)} (want {marker_attendu})")
    for sonde, veut in post_counts:
        if s.count(sonde) != veut:
            ennuis.append(f"post {sonde} x{s.count(sonde)} (want {veut})")
    if ennuis:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{tag}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(ennuis))
    print(f"OK - bundle patche ({resume}).")
    print(f"   taille : {len(avant)} -> {len(apres)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis le banc miroir")
    return 0
```

- [ ] **Step 2 : écrire le patcher `studiopin`**

Créer `scripts/patch_bundle_studiopin.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_studiopin.py
"""P1 — un run du Studio ne repaie que ce qui a bouge.

BASELINE : bundle POST-patch seedance25 (queue de chaine au 03/09/2026).
Backup dedie : .js.bak_studiopin. Position : EN QUEUE.
Plan : docs/superpowers/plans/2026-09-03-plan-studio.md

Mecanisme (n8n : epinglage des donnees ; effet ComfyUI : ne rejouer que ce qui
a change). Chaque noeud de generation porte dans ses props :

    pin = {jobId | file, sig, at, provider, dur, lock}

`sig` est l'empreinte de son sous-graphe amont. Au run suivant, si sig n'a pas
bouge (ou si lock vaut vrai), la valeur de slot du noeud est remplacee par
{source_kind:"job"} ou {source_kind:"upload"} — que le serveur resout SANS
appeler de fournisseur (pipeline.py, branche `elif kind == "job"`).

Les cinq points de substitution, mesures le 03/09 (1 occurrence chacun) :
  S2  srcFor de dzCompose    — l'entonnoir de la branche Composition
  S3  le meme, cote appelant — la carte slot -> noeud
  S4  N.anim de la branche UGC
  S5  z[I] de la branche Montage
  S6  slots[hgSlot.name] de l'avatar HeyGen

DANGERS : dzCompose appartient a patch_bundle_spatialports.py et la
declaration `var __dzG=null,__dzKeep={};` a patch_bundle_keepstate.py — les
relancer SEULS effacerait ces greffes en silence. La garde de chaine du
harnais l'interdit par accident ; le banc test_studio_pin.py l'attrape sinon.

Run :
    python scripts/patch_bundle_studiopin.py            # depot
    python scripts/patch_bundle_studiopin.py --check    # n'ecrit rien
    python scripts/patch_bundle_studiopin.py --deltas   # empreinte
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_studio import poser  # noqa: E402

TAG = "studiopin"
MARKER = "__DZ_STUDIOPIN"
MARKER_ATTENDU = 2          # le BEGIN et le END du bloc de helpers

SPEC_CHAR_DELTA = None      # fige en etape 4 (voir le plan)
SPEC_BYTE_DELTA = None

STABLE_PROBES = [
    ("libpicker", "__dzLibPicker", 10),
    ("libsend", "__dzSendTo", 2),
    ("imagegen", "dzIsImgNode", 11),
    ("spatialports", "dzSpatialSlots", 3),
    ("keepstate", "__dzKeep", 7),
    ("compilateur", "function Mh(e){", 1),
]

# ── S1 : le bloc de helpers, pose juste avant dzIsImgNode ───────────────────
HELPERS = (
    "/*__DZ_STUDIOPIN__*/"
    # les props qui ne comptent PAS dans l'empreinte : le resultat lui-meme
    "function __dzPinNet(p){var o={},k;for(k in(p||{})){"
    'if(k==="pin"||k==="hist"||k==="duel")continue;o[k]=p[k]}return o}'
    # empreinte du sous-graphe AMONT : types, props, aretes entrantes
    "function __dzSig(g,id){var vus={},ord=[],fr=[id],h=0;"
    "while(fr.length&&h++<400){var cur=fr.shift();if(vus[cur])continue;"
    "vus[cur]=1;ord.push(cur);((g&&g.edges)||[]).forEach(function(e){"
    "if(e.to===cur&&!vus[e.from])fr.push(e.from)})}ord.sort();"
    "var txt=ord.map(function(nid){var n=((g&&g.nodes)||[]).find("
    'function(z){return z.id===nid});if(!n)return nid+":?";'
    "var c=__dzPinNet(n.props),ks=Object.keys(c).sort();"
    'var pr=ks.map(function(k){return k+"="+JSON.stringify(c[k])}).join(",");'
    "var ins=((g&&g.edges)||[]).filter(function(e){return e.to===nid})"
    '.map(function(e){return e.toPort+"<"+e.from+":"+e.fromPort}).sort()'
    '.join("|");'
    'return nid+"#"+n.type+"{"+pr+"}["+ins+"]"}).join(";");'
    "var x=5381,i;for(i=0;i<txt.length;i++){x=((x<<5)+x+txt.charCodeAt(i))|0}"
    'return(x>>>0).toString(36)}'
    # la valeur de slot d'un noeud epingle, ou null
    "function __dzPV(g,n){var p=n&&n.props&&n.props.pin;if(!p)return null;"
    "if(!(p.lock||p.sig===__dzSig(g,n.id)))return null;"
    'if(p.jobId)return{source_kind:"job",job_id:p.jobId};'
    'if(p.file)return{source_kind:"upload",upload_filename:p.file};'
    "return null}"
    # etat de l'epingle, pour l'IU : aucun / vif / perime / tenu
    "function __dzPinEtat(g,n){var p=n&&n.props&&n.props.pin;"
    'if(!p||!(p.jobId||p.file))return"aucun";'
    'if(p.lock)return"tenu";return p.sig===__dzSig(g,n.id)?"vif":"perime"}'
    # la carte slot -> noeud du run en cours, lue par renderLayoutTemplate
    "function __dzNSet(k,v){try{(window.__dzNS=window.__dzNS||{})[k]=v}"
    "catch(e){}return v||1}"
    "function __dzNRaz(){try{window.__dzNS={}}catch(e){}}"
    "/*__DZ_STUDIOPIN_END__*/"
)
_A1 = "function dzIsImgNode(n){"

# ── S2 : srcFor — l'entonnoir de la branche Composition ─────────────────────
_A2 = "    var g=thru(node);if(!g)return null;\r\n"
_R2 = ("    var g=thru(node);if(!g)return null;__dzLastSrc=g;\r\n"
       "    var __pv=__dzPV(e,g);if(__pv)return __pv;\r\n")

# ── S3 : cote appelant — la carte slot -> noeud ─────────────────────────────
_A3 = 'else if(sp){slots[r.slot_name]=sp;if(r.type==="video_slot")__filled++}'
_R3 = ('else if(sp){slots[r.slot_name]=sp;__dzNSet(r.slot_name,'
       '(__dzLastSrc&&__dzLastSrc.id)||(nd&&nd.id)||"");'
       'if(r.type==="video_slot")__filled++}')

# ── S4 : branche UGC ────────────────────────────────────────────────────────
_A4 = 'N.anim={source_kind:"seedance"'
_R4 = 'N.anim=__dzNSet("anim",j.id)&&__dzPV(e,j)||{source_kind:"seedance"'

# ── S5 : branche Montage ────────────────────────────────────────────────────
_A5 = 'z[I]={source_kind:"seedance"'
_R5 = 'z[I]=__dzNSet(I,j.id)&&__dzPV(e,j)||{source_kind:"seedance"'

# ── S6 : avatar HeyGen de la branche Composition ────────────────────────────
_A6 = 'else slots[hgSlot.name]={source_kind:"heygen"'
_R6 = ('else slots[hgSlot.name]=__dzNSet(hgSlot.name,hg.id)&&__dzPV(e,hg)'
       '||{source_kind:"heygen"')

# ── S7 : remise a zero de la carte en tete de compilation ───────────────────
_A7 = ('function Mh(e){var u,f,m,y,w,v,g,k,c,p;'
       'const t=e.nodes.find(h=>h.type==="Render");')
_R7 = ('function Mh(e){var u,f,m,y,w,v,g,k,c,p;__dzNRaz();'
       'const t=e.nodes.find(h=>h.type==="Render");')

# ── S8 : la carte part avec la requete de rendu ─────────────────────────────
_A8 = 'source_graph:g||null,voiceover:dzGraphVoiceover(g)||null,preview:_pv})'
_R8 = ('source_graph:g||null,node_slots:(window.__dzNS||null),'
       'voiceover:dzGraphVoiceover(g)||null,preview:_pv})')

# ── S9 : le magasin, declare a cote de ceux de keepstate ────────────────────
_A9 = "var __dzG=null,__dzKeep={};"
_R9 = "var __dzG=null,__dzKeep={},__dzLastSrc=null;"

PATCHES = [
    ("S1-helpers", _A1, HELPERS + _A1),
    ("S2-srcFor", _A2, _R2),
    ("S3-carte-compose", _A3, _R3),
    ("S4-ugc", _A4, _R4),
    ("S5-montage", _A5, _R5),
    ("S6-heygen", _A6, _R6),
    ("S7-raz", _A7, _R7),
    ("S8-corps-de-requete", _A8, _R8),
    ("S9-magasin", _A9, _R9),
]

POST_COUNTS = [
    ("__dzPV", 5),
    ("__dzSig", 3),
    ("__dzNSet", 5),
    ("__dzLastSrc", 4),
    ("node_slots", 1),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(poser(TAG, MARKER, MARKER_ATTENDU, PATCHES, STABLE_PROBES,
                   POST_COUNTS, SPEC_CHAR_DELTA, SPEC_BYTE_DELTA,
                   "P1 : 5 points de substitution + carte slot->noeud"))
```

Note sur `__dzNSet` : il rend `v||1`, jamais une valeur fausse, pour que le
`&&` des sites S4/S5/S6 (`__dzNSet(...)&&__dzPV(...)||{…}`) enregistre
TOUJOURS la carte avant d'évaluer l'épingle, même quand l'identifiant de nœud
serait vide.

- [ ] **Step 3 : vérifier les ancres sans rien écrire**

Run : `python scripts/patch_bundle_studiopin.py --check`

Attendu : la commande s'arrête sur
`[studiopin] parite spec non figee. Lance --deltas, puis ecris en tete du fichier : SPEC_CHAR_DELTA = <C> et SPEC_BYTE_DELTA = <O>.`
— normal, l'empreinte n'est pas encore figée.

- [ ] **Step 4 : figer l'empreinte, puis re-vérifier**

Run : `python scripts/patch_bundle_studiopin.py --deltas`

Attendu : une seule ligne `[studiopin] delta +<C> car / +<O> o`. Recopier ces
deux nombres dans `SPEC_CHAR_DELTA` et `SPEC_BYTE_DELTA` (remplacer les deux
`None`), puis relancer :

Run : `python scripts/patch_bundle_studiopin.py --check`

Attendu, mot pour mot sauf les nombres `<C>` / `<O>` (qui doivent être les
mêmes que ceux affichés par `--deltas`) :

```
[studiopin] applicable sur ...\frontend\dist\assets\index-BEOJX8L5.js
[studiopin] 9 ancres OK, marqueur absent, 6 sondes aux comptes
[studiopin] CRLF=11884 LF-isole=0 CR-isole=0 ; delta +<C> car / +<O> o
```

Si une ligne dit `anchor count=0` ou `count=2`, **ne rien écrire** : le bundle
a bougé depuis la mesure du 03/09, il faut relire l'ancre nommée.

- [ ] **Step 5 : appliquer**

Run : `python scripts/patch_bundle_studiopin.py`

Attendu :

```
backup -> index-BEOJX8L5.js.bak_studiopin
mtime du backup pousse en queue de chaine
OK - bundle patche (P1 : 5 points de substitution + carte slot->noeud).
   taille : 1395299 -> <1395299+O> o (+<O>)
   suite  : copie .mjs + node --check, puis le banc miroir
```

- [ ] **Step 6 : valider la syntaxe du bundle**

Run (depuis la racine du dépôt) :

```
cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK
```

Attendu : `SYNTAXE_OK`, rien d'autre. Une `SyntaxError` veut dire qu'un
remplacement a cassé une expression : restaurer avec
`copy frontend\dist\assets\index-BEOJX8L5.js.bak_studiopin frontend\dist\assets\index-BEOJX8L5.js`
et relire l'ancre fautive.

- [ ] **Step 7 : le banc miroir, qui EXÉCUTE les helpers**

Ajouter à `backend/tests/test_studio_pin.py`, avant le `if __name__` :

```python
# ── C. le bundle : les helpers d'epinglage, LUS ET EXECUTES ────────────────

BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def _bloc_studiopin():
    """Le bloc injecte par patch_bundle_studiopin.py, decoupe sur ses bornes.

    On lit la SURFACE REELLE — le bundle livre — et non la source du patcher :
    un patcher juste mais jamais applique doit rougir ici."""
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    d = s.index("/*__DZ_STUDIOPIN__*/") + len("/*__DZ_STUDIOPIN__*/")
    f = s.index("/*__DZ_STUDIOPIN_END__*/")
    return s[d:f]


def _node(js: str) -> str:
    import shutil
    import subprocess
    exe = shutil.which("node")
    assert exe, ("node est requis par ce banc : il execute les helpers "
                 "extraits du bundle. Installe Node (v24 au 03/09/2026) ou "
                 "lance ce fichier sur la machine de developpement.")
    r = subprocess.run([exe, "-e", js], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    return r.stdout.decode("utf-8", "replace").strip()


def test_les_cinq_points_de_substitution_sont_dans_le_bundle():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert s.count("__dzPV") == 5, s.count("__dzPV")
    assert s.count("__dzNSet") == 5, s.count("__dzNSet")
    assert "var __pv=__dzPV(e,g);if(__pv)return __pv;" in s            # srcFor
    assert 'N.anim=__dzNSet("anim",j.id)&&__dzPV(e,j)||' in s          # UGC
    assert "z[I]=__dzNSet(I,j.id)&&__dzPV(e,j)||" in s                 # montage
    assert ("slots[hgSlot.name]=__dzNSet(hgSlot.name,hg.id)"
            "&&__dzPV(e,hg)||") in s                                   # heygen
    assert "node_slots:(window.__dzNS||null)," in s
    assert "__dzNRaz();const t=e.nodes.find" in s


def test_l_empreinte_bouge_avec_un_reglage_et_pas_avec_la_position():
    js = _bloc_studiopin() + """
var g={nodes:[{id:"im",type:"Image",x:0,y:0,props:{filename:"a.png"}},
              {id:"sd",type:"Seedance",x:1,y:1,props:{durationS:10,model:"pro"}}],
       edges:[{id:"e1",from:"im",fromPort:"out",to:"sd",toPort:"image"}]};
var base=__dzSig(g,"sd");
g.nodes[1].x=999; g.nodes[0].y=42;
var bouge=__dzSig(g,"sd");
g.nodes[1].props.durationS=5;
var reglage=__dzSig(g,"sd");
g.nodes[1].props.durationS=10; g.nodes[0].props.filename="b.png";
var amont=__dzSig(g,"sd");
g.nodes[0].props.filename="a.png"; g.edges=[];
var debranche=__dzSig(g,"sd");
console.log([base===bouge,base!==reglage,base!==amont,base!==debranche].join(","));
"""
    assert _node(js) == "true,true,true,true"


def test_l_epingle_est_ignoree_quand_les_entrees_ont_change():
    js = _bloc_studiopin() + """
var g={nodes:[{id:"im",type:"Image",x:0,y:0,props:{filename:"a.png"}},
              {id:"sd",type:"Seedance",x:1,y:1,props:{durationS:10}}],
       edges:[{id:"e1",from:"im",fromPort:"out",to:"sd",toPort:"image"}]};
var sd=g.nodes[1];
sd.props.pin={jobId:"j-1",sig:__dzSig(g,"sd")};
var vif=JSON.stringify(__dzPV(g,sd)), etat1=__dzPinEtat(g,sd);
g.nodes[0].props.filename="b.png";
var perime=__dzPV(g,sd), etat2=__dzPinEtat(g,sd);
sd.props.pin.lock=true;
var tenu=JSON.stringify(__dzPV(g,sd)), etat3=__dzPinEtat(g,sd);
sd.props.pin={file:"vue.png",sig:__dzSig(g,"sd")};
var fichier=JSON.stringify(__dzPV(g,sd));
console.log([vif,etat1,perime,etat2,tenu,etat3,fichier].join(" | "));
"""
    attendu = " | ".join([
        '{"source_kind":"job","job_id":"j-1"}', "vif",
        "null", "perime",
        '{"source_kind":"job","job_id":"j-1"}', "tenu",
        '{"source_kind":"upload","upload_filename":"vue.png"}'])
    assert _node(js) == attendu


def test_l_epingle_ne_compte_pas_dans_sa_propre_empreinte():
    """Sans quoi poser l'epingle perimerait l'epingle : boucle morte."""
    js = _bloc_studiopin() + """
var g={nodes:[{id:"sd",type:"Seedance",x:0,y:0,props:{durationS:10}}],edges:[]};
var avant=__dzSig(g,"sd");
g.nodes[0].props.pin={jobId:"j",sig:avant};
g.nodes[0].props.hist=[{jobId:"j0"}];
g.nodes[0].props.duel={modelB:"x"};
console.log(avant===__dzSig(g,"sd"));
"""
    assert _node(js) == "true"


def test_le_patcher_garde_sa_place_dans_la_chaine():
    p = (RACINE / "scripts"
         / "patch_bundle_studiopin.py").read_text(encoding="utf-8")
    assert "from _patch_studio import poser" in p
    h = (RACINE / "scripts" / "_patch_studio.py").read_text(encoding="utf-8")
    assert "guard_downstream" in h and "ensure_tail_order" in h
    assert 'newline=""' in h, "le bundle est en CRLF pur"
    assert (RACINE / "frontend" / "dist" / "assets"
            / "index-BEOJX8L5.js.bak_studiopin").is_file()
```

- [ ] **Step 8 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_pin.py`

Attendu : `11 passed`.

- [ ] **Step 9 : commit**

```
git add scripts/_patch_studio.py scripts/patch_bundle_studiopin.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_pin.py
git commit -m 'studio : lepinglage, les cinq points de substitution' -m 'Le compilateur nest pas reecrit : chaque noeud de generation porte lempreinte de son sous-graphe amont et, si elle na pas bouge, sa valeur de slot devient source_kind job ou upload — que le serveur resout sans appeler de fournisseur. Cinq sites mesures : srcFor de dzCompose et son appelant, la branche UGC, la branche Montage, lavatar HeyGen. La carte slot vers noeud part avec la requete. Le harnais commun aux sept patchers du chantier vit dans _patch_studio.py. Le banc extrait les helpers du bundle LIVRE et les execute sous node : lempreinte ignore la position, suit les reglages et lamont, et ne se compte pas elle-meme.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 4 : Le patcher `studiopin` (b) — récolte, puce, panneau, chiffre du coût

**Files:**
- Modify: `scripts/patch_bundle_studiopin.py` (HELPERS étendu, S10–S14 ajoutés)
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (lignes 231, 283, 286)
- Test: `backend/tests/test_studio_pin.py` (section D)

Le mécanisme de T3 est aveugle tant que personne n'écrit les épingles ni ne les
montre. Ici : la récolte après un run (via `/jobs/{id}/parts` de T2), la puce
d'état dans l'entête du nœud, le panneau qui tient/relâche l'épingle, et le
chiffre « Y nœuds réutilisés » à côté du coût, avant le tir. Même patcher : il
restaure son `.bak` puis rejoue tout, donc étendre = relancer.

- [ ] **Step 1 : étendre les helpers**

Dans `scripts/patch_bundle_studiopin.py`, insérer dans `HELPERS`, juste avant
la ligne `"/*__DZ_STUDIOPIN_END__*/"` :

```python
    # recolte : apres un run, chaque noeud genere recoit son epingle
    "function __dzHarvest(jid,setG){try{"
    'fetch("/api/jobs/"+encodeURIComponent(jid)+"/parts")'
    ".then(function(r){return r.ok?r.json():null}).then(function(d){"
    "var ps=(d&&d.parts)||[];if(!ps.length)return;"
    "setG(function(G){var N=Object.assign({},G),"
    "now=new Date().toISOString();"
    "N.nodes=(G.nodes||[]).map(function(n){var p=null,i;"
    "for(i=0;i<ps.length;i++)if(ps[i].node_id===n.id)p=ps[i];"
    'if(!p||!p.job_id||p.kind!=="generated")return n;'
    "var pin={jobId:p.job_id,sig:__dzSig(G,n.id),at:now,"
    'provider:p.provider||"",dur:p.duration_s||0};'
    "if(n.props&&n.props.pin&&n.props.pin.lock)pin.lock=!0;"
    "return Object.assign({},n,{props:Object.assign({},n.props,"
    "{pin:pin})})});return N})}).catch(function(){})}catch(e){}}"
    # les types dont l'epingle a un sens
    'var __dzGEN=["Seedance","HeyGenAvatar","NewsIllustration","ImageGen",'
    '"ImageEdit","Variations"];'
    "function __dzEstGen(n){return!!n&&__dzGEN.indexOf(n.type)>=0}"
    # combien de noeuds ce run va reutiliser
    "function __dzReuse(g){var k=0;((g&&g.nodes)||[]).forEach(function(n){"
    "if(__dzEstGen(n)&&__dzPV(g,n))k++});return k}"
    # le panneau de l'inspecteur
    "function DzPinPanel({node,graph,onUpdate}){"
    "if(!__dzEstGen(node))return null;"
    "var p=(node.props&&node.props.pin)||null,et=__dzPinEtat(graph,node);"
    'var mot={aucun:"Rien d\'épinglé",vif:"Épingle à jour",'
    'perime:"Réglages changés depuis",'
    'tenu:"Tenu à la main"}[et];'
    'var ton={aucun:"neutral",vif:"green",perime:"amber",tenu:"cyan"}[et];'
    'return r.jsxs(ie,{label:"Épingle",children:['
    'r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:8,'
    'padding:"2px 0 8px"},children:[r.jsx(te,{tone:ton,dot:!0,children:mot}),'
    'p&&p.dur?r.jsx("span",{className:"mono",style:{fontSize:10.5,'
    'color:"var(--ink-muted)"},children:p.dur+"s"}):null]}),'
    'r.jsx(O,{hint:et==="perime"?"Ce résultat ne sera PAS réutilisé : '
    "une entrée ou un réglage amont a changé. Tiens-le à la main "
    'pour le garder quand même.":"Un résultat épinglé n’est pas '
    'repayé au run suivant.",children:r.jsx(Ze,{checked:!!(p&&p.lock),'
    "onChange:function(v){if(!p)return;"
    "onUpdate({pin:Object.assign({},p,{lock:!!v})})},"
    'label:"Tenir ce résultat à la main"})}),'
    'p?r.jsx(K,{variant:"outline",size:"sm",icon:"close",'
    'style:{width:"100%"},onClick:function(){onUpdate({pin:null})},'
    'children:"Relâcher l’épingle"}):null]})}'
```

Les libellés ci-dessus portent leurs accents en clair : le fichier déclare
`# -*- coding: utf-8 -*-`, et la règle du dépôt ne vise que l'**impression**
(console cp1252), jamais le contenu. Les apostrophes typographiques `’` sont
préférées à `'` pour ne pas avoir à échapper au milieu d'une chaîne JS
entre quotes simples. Les patchers de T12, eux, échappent en `\uXXXX` parce
que leurs ancres contiennent des emoji.

- [ ] **Step 2 : ajouter les cinq greffes**

Dans le même fichier, après le bloc `_R9`, ajouter :

```python
# ── S10 : la recolte, juste avant que le rendu fini soit affiche ────────────
_A10 = "Ee?(k({id:Ee.job_id,title:Ee.title||R.summary}),"
_R10 = "Ee?(__dzHarvest(Ee.job_id,i),k({id:Ee.job_id,title:Ee.title||R.summary}),"

# ── S11 : l'entete du noeud recoit le graphe ───────────────────────────────
_A11 = "function Oh({node:e}){const t=Me[e.type],n=Qr[t.cat];"
_R11 = ("function Oh({node:e,graph:gg}){const t=Me[e.type],n=Qr[t.cat];"
        "const __et=gg?__dzPinEtat(gg,e):\"aucun\";")

# ── S12 : la puce d'etat, a droite du titre ────────────────────────────────
_A12 = 'r.jsx(se,{name:"more"})]})})}function Fh({graph:e,onRename:t}){'
_R12 = ('__dzEstGen(e)&&__et!=="aucun"?r.jsx(te,{'
        'tone:__et==="perime"?"amber":__et==="tenu"?"cyan":"green",dot:!0,'
        'children:__et==="perime"?"périmé":'
        '__et==="tenu"?"tenu":"épinglé"}):null,'
        'r.jsx(se,{name:"more"})]})})}function Fh({graph:e,onRename:t}){')

# ── S13 : l'inspecteur passe le graphe et monte le panneau ─────────────────
_A13 = ("r.jsx(Oh,{node:e}),r.jsxs(\"div\",{className:\"scroll\","
        "style:{flex:1,overflowY:\"auto\"},children:["
        "r.jsx(Yh,{node:e,onUpdate:o,graph:t,onUpdateNode:U,onSpawnNodes:sp}),")
_R13 = ("r.jsx(Oh,{node:e,graph:t}),r.jsxs(\"div\",{className:\"scroll\","
        "style:{flex:1,overflowY:\"auto\"},children:["
        "r.jsx(Yh,{node:e,onUpdate:o,graph:t,onUpdateNode:U,onSpawnNodes:sp}),"
        "r.jsx(DzPinPanel,{node:e,graph:t,onUpdate:o}),")

# ── S14 : l'estimation saute les noeuds epingles et dit combien ────────────
_A14 = ('const sig=nodes.map(n=>n.type+":"+((n.props&&n.props.durationS)||"")'
        '+":"+((n.props&&n.props.model)||"")).join(",");')
_R14 = ('const sig=nodes.map(n=>n.type+":"+((n.props&&n.props.durationS)||"")'
        '+":"+((n.props&&n.props.model)||"")+":"'
        '+((n.props&&n.props.pin&&(n.props.pin.jobId||n.props.pin.file)'
        '+":"+(n.props.pin.lock?1:0))||"")).join(",");'
        "const __reuse=__dzReuse(graph);")

# ── S15 : les operations epinglees ne sont plus comptees ───────────────────
_A15 = ('nodes.forEach(n=>{const T=n.type;'
        'if(T==="Image"||T==="NewsIllustration")ops.push({kind:"image"});')
_R15 = ('nodes.forEach(n=>{const T=n.type;if(__dzEstGen(n)&&__dzPV(graph,n))'
        'return;'
        'if(T==="Image"||T==="NewsIllustration")ops.push({kind:"image"});')

# ── S16 : et le chiffre s'affiche a cote du montant ────────────────────────
_A16 = ('children:["≈ $",e.total_usd!=null?e.total_usd.toFixed(2):"0.00"]'
        '});}')
_R16 = ('children:["≈ $",e.total_usd!=null?e.total_usd.toFixed(2):"0.00",'
        '__reuse?" · "+__reuse+" réutilisé"+(__reuse>1?"s":""):""]'
        '});}')
```

Puis remplacer la liste `PATCHES` et `POST_COUNTS` par :

```python
PATCHES = [
    ("S1-helpers", _A1, HELPERS + _A1),
    ("S2-srcFor", _A2, _R2),
    ("S3-carte-compose", _A3, _R3),
    ("S4-ugc", _A4, _R4),
    ("S5-montage", _A5, _R5),
    ("S6-heygen", _A6, _R6),
    ("S7-raz", _A7, _R7),
    ("S8-corps-de-requete", _A8, _R8),
    ("S9-magasin", _A9, _R9),
    ("S10-recolte", _A10, _R10),
    ("S11-entete-graphe", _A11, _R11),
    ("S12-puce", _A12, _R12),
    ("S13-panneau", _A13, _R13),
    ("S14-signature-estimation", _A14, _R14),
    ("S15-estimation-saute", _A15, _R15),
    ("S16-chiffre-reutilises", _A16, _R16),
]

POST_COUNTS = [
    ("__dzPV", 7),
    ("__dzSig", 4),
    ("__dzNSet", 5),
    ("__dzLastSrc", 4),
    ("node_slots", 1),
    ("__dzPinEtat", 2),
    ("__dzEstGen", 5),
    ("DzPinPanel", 2),
    ("__dzHarvest", 2),
    ("__reuse", 4),
]
```

Mettre enfin `SPEC_CHAR_DELTA = None` et `SPEC_BYTE_DELTA = None` (l'empreinte
de T3 ne vaut plus).

- [ ] **Step 3 : refiger l'empreinte et vérifier**

Run : `python scripts/patch_bundle_studiopin.py --deltas`

Attendu : `[studiopin] delta +<C> car / +<O> o` — deux nombres plus grands que
ceux de T3. Les recopier dans les deux constantes, puis :

Run : `python scripts/patch_bundle_studiopin.py --check`

Attendu :

```
[studiopin] applicable sur ...\index-BEOJX8L5.js.bak_studiopin
[studiopin] 16 ancres OK, marqueur absent, 6 sondes aux comptes
[studiopin] CRLF=11884 LF-isole=0 CR-isole=0 ; delta +<C> car / +<O> o
```

Le `--check` lit désormais le **backup** (l'état d'avant T3), pas le bundle
courant : c'est voulu, c'est là que les ancres doivent exister.

- [ ] **Step 4 : réappliquer et valider la syntaxe**

Run : `python scripts/patch_bundle_studiopin.py`

Attendu :

```
restore <- index-BEOJX8L5.js.bak_studiopin
OK - bundle patche (P1 : 5 points de substitution + carte slot->noeud).
   taille : 1395299 -> <1395299+O> o (+<O>)
   suite  : copie .mjs + node --check, puis le banc miroir
```

Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK`

Attendu : `SYNTAXE_OK`.

- [ ] **Step 5 : le banc**

Ajouter à `backend/tests/test_studio_pin.py`, avant le `if __name__` :

```python
# ── D. l'IU de l'epingle : ce que l'utilisateur LIT ────────────────────────

def test_la_recolte_ecrit_une_epingle_par_noeud_genere():
    js = _bloc_studiopin() + """
var G={nodes:[{id:"im",type:"Image",x:0,y:0,props:{filename:"a.png"}},
               {id:"sd",type:"Seedance",x:1,y:1,props:{durationS:10}},
               {id:"up",type:"Upload",x:2,y:2,props:{jobId:"deja"}}],
        edges:[{id:"e1",from:"im",fromPort:"out",to:"sd",toPort:"image"}]};
var ps=[{slot:"anim",node_id:"sd",job_id:"j-anim",provider:"seedance",
         duration_s:10,kind:"generated"},
        {slot:"ugc",node_id:"up",job_id:null,provider:null,
         duration_s:null,kind:"static"}];
global.fetch=function(){return Promise.resolve({ok:true,
  json:function(){return Promise.resolve({parts:ps})}})};
__dzHarvest("parent",function(fn){var N=fn(G);
  var sd=N.nodes[1],up=N.nodes[2];
  console.log([sd.props.pin.jobId,sd.props.pin.provider,sd.props.pin.dur,
               __dzPV(N,sd)!==null,up.props.pin===undefined,
               N.nodes[0].props.pin===undefined].join(","))});
"""
    assert _node(js) == "j-anim,seedance,10,true,true,true"


def test_la_recolte_ne_defait_pas_une_epingle_tenue_a_la_main():
    js = _bloc_studiopin() + """
var G={nodes:[{id:"sd",type:"Seedance",x:0,y:0,
               props:{durationS:10,pin:{jobId:"vieux",sig:"x",lock:true}}}],
        edges:[]};
global.fetch=function(){return Promise.resolve({ok:true,json:function(){
  return Promise.resolve({parts:[{slot:"a",node_id:"sd",job_id:"neuf",
    provider:"seedance",duration_s:5,kind:"generated"}]})}})};
__dzHarvest("p",function(fn){var n=fn(G).nodes[0];
  console.log([n.props.pin.jobId,n.props.pin.lock].join(","))});
"""
    assert _node(js) == "neuf,true"


def test_le_compte_des_reutilises():
    js = _bloc_studiopin() + """
var g={nodes:[{id:"a",type:"Seedance",x:0,y:0,props:{durationS:10}},
              {id:"b",type:"Seedance",x:0,y:0,props:{durationS:5}},
              {id:"c",type:"Image",x:0,y:0,props:{filename:"z.png"}}],
       edges:[]};
var z=__dzReuse(g);
g.nodes[0].props.pin={jobId:"j",sig:__dzSig(g,"a")};
var un=__dzReuse(g);
g.nodes[1].props.pin={jobId:"k",sig:"perime"};
var toujours=__dzReuse(g);
g.nodes[1].props.pin.lock=true;
var deux=__dzReuse(g);
console.log([z,un,toujours,deux].join(","));
"""
    assert _node(js) == "0,1,1,2"


def test_l_ecran_dit_l_etat_de_l_epingle_et_le_nombre_reutilise():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    # la puce de l'entete, ses trois mots
    for mot in ("périmé", "tenu", "épinglé"):
        assert mot in s, mot
    # le panneau, son remede ECRIT (pas seulement un refus)
    assert "Réglages changés depuis" in s
    assert "Tiens-le à la main" in s
    assert "Tenir ce résultat à la main" in s
    assert "Relâcher l’épingle" in s
    # le chiffre AVANT le tir, a cote du montant
    assert 'réutilisé"+(__reuse>1?"s":"")' in s
    # l'estimation saute vraiment les noeuds epingles
    assert "if(__dzEstGen(n)&&__dzPV(graph,n))return;" in s
    # et la recolte est branchee sur le rendu fini
    assert "Ee?(__dzHarvest(Ee.job_id,i)," in s
```

- [ ] **Step 6 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_pin.py`

Attendu : `15 passed`.

- [ ] **Step 7 : commit**

```
git add scripts/patch_bundle_studiopin.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_pin.py
git commit -m 'studio : la recolte, la puce, le panneau et le chiffre des reutilises' -m 'Le mecanisme de la tache precedente etait aveugle. Apres un run, les parties du manifeste ecrivent une epingle sur chaque noeud genere, en respectant une epingle tenue a la main. Lentete du noeud porte une puce epingle/perime/tenu, linspecteur donne un interrupteur et un bouton relacher, et lestimation de cout saute les noeuds reutilises en affichant leur nombre AVANT le tir — cetait la reponse a la perte de credits.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 5 : `studiohist` — la pile des rendus d'un nœud (P2)

**Files:**
- Create: `scripts/patch_bundle_studiohist.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (ligne 231)
- Test: `backend/tests/test_studio_lecture.py`

P2 s'appuie sur P1 : la récolte pose déjà `pin` ; il suffit de la faire
empiler dans `props.hist` (8 au plus, le plus récent devant) et d'offrir de
choisir lequel alimente l'aval. Choisir = réécrire `pin` avec l'entrée
choisie et `lock:true` — sans quoi la prochaine récolte l'écraserait.

- [ ] **Step 1 : écrire le patcher**

Créer `scripts/patch_bundle_studiohist.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_studiohist.py
"""P2 — la pile des rendus passes d'un noeud, et le choix de celui qui alimente
l'aval.

BASELINE : bundle POST-patch studiopin. Backup dedie : .js.bak_studiohist.
Position : EN QUEUE, apres studiopin.
Plan : docs/superpowers/plans/2026-09-03-plan-studio.md

S1 modifie le helper __dzHarvest POSE PAR studiopin (edition in-bloc) : a
partir d'ici, patch_bundle_studiopin.py ne doit plus etre relance SEUL, sous
peine d'effacer la pile en silence. Passer par repatch_all.py --from studiopin.

Run : python scripts/patch_bundle_studiohist.py [--check] [--deltas]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_studio import poser  # noqa: E402

TAG = "studiohist"
MARKER = "__DZ_STUDIOHIST"
MARKER_ATTENDU = 2

SPEC_CHAR_DELTA = None
SPEC_BYTE_DELTA = None

STABLE_PROBES = [
    ("studiopin", "__DZ_STUDIOPIN", 2),
    ("studiopin-panneau", "DzPinPanel", 2),
    ("studiopin-recolte", "__dzHarvest", 2),
    ("libpicker", "__dzLibPicker", 10),
    ("imagegen", "dzIsImgNode", 11),
]

# ── S1 : la recolte empile, au lieu de seulement remplacer ─────────────────
_A1 = ("if(n.props&&n.props.pin&&n.props.pin.lock)pin.lock=!0;"
       "return Object.assign({},n,{props:Object.assign({},n.props,"
       "{pin:pin})})});return N})}).catch(function(){})}catch(e){}}")
_R1 = ("if(n.props&&n.props.pin&&n.props.pin.lock)pin.lock=!0;"
       "return Object.assign({},n,{props:Object.assign({},n.props,"
       "{pin:pin,hist:__dzHistPush((n.props||{}).hist,pin)})})});"
       "return N})}).catch(function(){})}catch(e){}}")

# ── S2 : la pile et son panneau ────────────────────────────────────────────
BLOC = (
    "/*__DZ_STUDIOHIST__*/"
    # empile en tete, sans doublon d'identifiant, 8 au plus
    "function __dzHistPush(h,e){var l=(h||[]).filter(function(x){"
    "return x&&(x.jobId||x.file)!==(e.jobId||e.file)});"
    "l.unshift({jobId:e.jobId||null,file:e.file||null,at:e.at||null,"
    'provider:e.provider||"",dur:e.dur||0,sig:e.sig||null});'
    "return l.slice(0,8)}"
    # le panneau : lire la pile, choisir, oublier
    "function DzHistPanel({node,graph,onUpdate}){"
    "if(!__dzEstGen(node))return null;"
    "var h=((node.props||{}).hist)||[];"
    "var cur=(node.props&&node.props.pin)||{};"
    "if(!h.length)return r.jsx(ie,{label:\"Historique\",children:"
    'r.jsx("div",{style:{fontSize:11,color:"var(--ink-muted)",'
    'padding:"2px 0 6px"},children:"Aucun résultat encore. Lance le '
    'graphe : chaque rendu de ce nœud viendra s’empiler ici."})});'
    'return r.jsx(ie,{label:"Historique ("+h.length+")",children:'
    'r.jsx("div",{style:{display:"flex",flexDirection:"column",gap:6},'
    "children:h.map(function(x,ix){"
    "var actif=(x.jobId||x.file)===(cur.jobId||cur.file);"
    'return r.jsxs("div",{style:{display:"flex",gap:8,alignItems:"center",'
    'padding:6,borderRadius:"var(--r-sm)",background:"var(--bg-base)",'
    'border:"1px solid var(--"+(actif?"cyan":"stroke")+")"},children:['
    'x.jobId?r.jsx("video",{src:D.jobVideoUrl(x.jobId),muted:!0,'
    'preload:"metadata",style:{width:44,height:78,objectFit:"cover",'
    'borderRadius:4,background:"#000"}}):'
    'r.jsx("img",{src:D.imageUrl(x.file||""),alt:"",'
    'style:{width:44,height:78,objectFit:"cover",borderRadius:4}}),'
    'r.jsxs("div",{style:{flex:1,minWidth:0,fontSize:10.5,'
    'color:"var(--ink-soft)"},children:['
    'r.jsx("div",{className:"mono",style:{color:"var(--ink-strong)",'
    'overflow:"hidden",textOverflow:"ellipsis"},'
    'children:(x.jobId||x.file||"?")}),'
    'r.jsx("div",{children:(x.provider||"local")'
    '+(x.dur?" · "+x.dur+"s":"")'
    '+(x.at?" · "+String(x.at).slice(0,16).replace("T"," "):"")})]}),'
    'actif?r.jsx(te,{tone:"cyan",children:"en aval"}):'
    'r.jsx(K,{variant:"outline",size:"sm",onClick:function(){'
    "onUpdate({pin:{jobId:x.jobId||null,file:x.file||null,"
    'sig:x.sig||null,at:x.at||null,provider:x.provider||"",'
    "dur:x.dur||0,lock:!0}})},"
    'children:"Utiliser"})]},String(ix))})})})}'
    "/*__DZ_STUDIOHIST_END__*/"
)
_A2 = "function DzPinPanel({node,graph,onUpdate}){"

# ── S3 : monte le panneau sous celui de l'epingle ──────────────────────────
_A3 = "r.jsx(DzPinPanel,{node:e,graph:t,onUpdate:o}),"
_R3 = ("r.jsx(DzPinPanel,{node:e,graph:t,onUpdate:o}),"
       "r.jsx(DzHistPanel,{node:e,graph:t,onUpdate:o}),")

PATCHES = [
    ("S1-recolte-empile", _A1, _R1),
    ("S2-bloc", _A2, BLOC + _A2),
    ("S3-montage-panneau", _A3, _R3),
]

POST_COUNTS = [
    ("__dzHistPush", 2),
    ("DzHistPanel", 2),
    ("DzPinPanel", 2),
    ("__DZ_STUDIOPIN", 2),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(poser(TAG, MARKER, MARKER_ATTENDU, PATCHES, STABLE_PROBES,
                   POST_COUNTS, SPEC_CHAR_DELTA, SPEC_BYTE_DELTA,
                   "P2 : pile des rendus par noeud"))
```

- [ ] **Step 2 : figer l'empreinte, vérifier, appliquer**

Run : `python scripts/patch_bundle_studiohist.py --deltas`
→ recopier les deux nombres dans les constantes.

Run : `python scripts/patch_bundle_studiohist.py --check`
Attendu : `[studiohist] 3 ancres OK, marqueur absent, 5 sondes aux comptes`.

Run : `python scripts/patch_bundle_studiohist.py`
Attendu : `backup -> index-BEOJX8L5.js.bak_studiohist`,
`mtime du backup pousse en queue de chaine`, puis
`OK - bundle patche (P2 : pile des rendus par noeud).`

Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK`
Attendu : `SYNTAXE_OK`.

- [ ] **Step 3 : le banc**

Créer `backend/tests/test_studio_lecture.py` :

```python
# -*- coding: utf-8 -*-
"""Studio — ce que l'utilisateur LIT du resultat : la pile d'un noeud (P2) et
le defilement image par image (P4).

Bancs MIROIRS : ils lisent le bundle LIVRE, et executent sous node les helpers
qu'on y decoupe. Patron de test_library_picker.py, section D.

Run : python tests/test_studio_lecture.py  (depuis backend/)
"""
import pathlib
import shutil
import subprocess
import sys

import pytest

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def _bloc(debut: str, fin: str) -> str:
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    d = s.index(debut) + len(debut)
    return s[d:s.index(fin)]


def _node(js: str) -> str:
    exe = shutil.which("node")
    assert exe, "node est requis par ce banc (il execute les helpers du bundle)."
    r = subprocess.run([exe, "-e", js], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    return r.stdout.decode("utf-8", "replace").strip()


# ── P2 : la pile ───────────────────────────────────────────────────────────

def test_la_pile_empile_en_tete_sans_doublon_et_plafonne_a_huit():
    js = _bloc("/*__DZ_STUDIOHIST__*/", "/*__DZ_STUDIOHIST_END__*/") + """
var h=null,i;
for(i=1;i<=10;i++)h=__dzHistPush(h,{jobId:"j"+i,provider:"seedance",dur:i});
var apres10=[h.length,h[0].jobId,h[7].jobId].join(",");
h=__dzHistPush(h,{jobId:"j10",provider:"heygen",dur:99});
var redoublon=[h.length,h[0].provider,h.filter(function(x){
  return x.jobId==="j10"}).length].join(",");
console.log(apres10+" | "+redoublon);
"""
    assert _node(js) == "8,j10,j3 | 8,heygen,1"


def test_la_pile_garde_un_resultat_fichier_comme_un_resultat_rendu():
    js = _bloc("/*__DZ_STUDIOHIST__*/", "/*__DZ_STUDIOHIST_END__*/") + """
var h=__dzHistPush(null,{file:"a.png",provider:"flux"});
h=__dzHistPush(h,{jobId:"j1",provider:"seedance",dur:4});
console.log([h.length,h[0].jobId,h[1].file,h[1].jobId].join(","));
"""
    assert _node(js) == "2,j1,a.png,null"


def test_l_ecran_dit_la_pile_et_le_choix():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert "DzHistPanel" in s and s.count("DzHistPanel") == 2
    # l'empty state EXPLIQUE, il ne se contente pas d'etre vide
    assert "chaque rendu de ce nœud viendra s’empiler ici" in s
    # on voit lequel alimente l'aval, et on peut en choisir un autre
    assert '"en aval"' in s and '"Utiliser"' in s
    # choisir TIENT l'epingle, sinon la recolte suivante l'ecraserait
    assert "dur:x.dur||0,lock:!0}})}," in s
    # la recolte empile
    assert "hist:__dzHistPush((n.props||{}).hist,pin)" in s
    # et le patcher dit le danger de relancer studiopin seul
    p = (RACINE / "scripts"
         / "patch_bundle_studiohist.py").read_text(encoding="utf-8")
    assert "ne doit plus etre relance SEUL" in p


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] **Step 4 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_lecture.py`

Attendu : `3 passed`.

- [ ] **Step 5 : commit**

```
git add scripts/patch_bundle_studiohist.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_lecture.py
git commit -m 'studio : la pile des rendus dun noeud' -m 'La recolte de lepinglage empile desormais dans props.hist — huit au plus, le plus recent devant, sans doublon didentifiant. Le panneau montre lequel alimente laval, et en choisir un autre TIENT lepingle a la main : sans ce verrou la recolte suivante lecraserait. Ledition touche le helper pose par studiopin, donc ce dernier ne se relance plus seul mais par repatch_all --from studiopin ; le patcher le dit et le banc lattrape.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 6 : Le registre miroité et la validation d'import (P3)

**Files:**
- Create: `scripts/qa/dump_studio_registry.py`
- Create: `backend/app/assets/studio_nodes.json` (produit par le script)
- Create: `backend/app/services/studio_graph.py`
- Modify: `backend/app/api/routes.py:1790-1807` (après `save_studio_graph`)
- Test: `backend/tests/test_studio_graph_io.py`

Le registre des nœuds vit dans le bundle. Pour valider un import côté serveur
sans y dupliquer 34 définitions à la main, on **l'extrait** vers un JSON, et un
banc surveille la dérive entre les deux. L'extraction est pure stdlib : les 34
entrées suivent toutes la forme
`Nom:{cat:"…",title:"…",desc:"…",inPorts:[…],outPorts:[…]` (vérifié le 03/09).

- [ ] **Step 1 : le script d'extraction**

Créer `scripts/qa/dump_studio_registry.py` :

```python
# -*- coding: utf-8 -*-
# scripts/qa/dump_studio_registry.py
"""Extrait le registre des noeuds du Studio (l'objet `Me` du bundle) vers
backend/app/assets/studio_nodes.json, que la validation d'import lit.

Le bundle reste la SOURCE : ce JSON en est un miroir. test_studio_graph_io.py
surveille la derive entre les deux.

Run : python scripts/qa/dump_studio_registry.py [--check]
"""
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
CIBLE = RACINE / "backend" / "app" / "assets" / "studio_nodes.json"

ENTREE = re.compile(
    r'([A-Za-z]+):\{cat:"(source|gen|edit|compose|audio|motion|master|output)",'
    r'title:"([^"]*)",desc:"([^"]*)",inPorts:\[([^\]]*)\],outPorts:\[([^\]]*)\]')
PORT = re.compile(r'\{id:"([A-Za-z0-9_]+)",type:"([a-z]+)"\}')


def extraire() -> dict:
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    k = s.index('Me={Image:{cat:"source",title:"Image"')
    seg = s[k:k + 12000]
    types = {}
    for nom, cat, titre, _desc, ip, op in ENTREE.findall(seg):
        types[nom] = {
            "cat": cat,
            "title": titre,
            "in": [p[0] for p in PORT.findall(ip)],
            "out": [p[0] for p in PORT.findall(op)],
            "in_types": {p[0]: p[1] for p in PORT.findall(ip)},
            "out_types": {p[0]: p[1] for p in PORT.findall(op)},
        }
    if len(types) < 30:
        raise SystemExit(
            f"[registre] {len(types)} types extraits (attendu 34 au 03/09) — "
            "la forme du registre a change, relire l'expression ENTREE avant "
            "d'ecrire quoi que ce soit.")
    return {"source": BUNDLE.name, "count": len(types), "types": types}


def main():
    doc = extraire()
    texte = json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True)
    if "--check" in sys.argv:
        actuel = CIBLE.read_text(encoding="utf-8") if CIBLE.is_file() else ""
        if actuel.replace("\r\n", "\n") != texte:
            print(f"[registre] DERIVE : {CIBLE.name} ne correspond plus au "
                  "bundle. Relance sans --check.")
            return 1
        print(f"[registre] a jour ({doc['count']} types)")
        return 0
    CIBLE.parent.mkdir(parents=True, exist_ok=True)
    CIBLE.write_text(texte, encoding="utf-8")
    print(f"[registre] ecrit {CIBLE} ({doc['count']} types)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
```

- [ ] **Step 2 : produire le JSON**

Run : `python scripts/qa/dump_studio_registry.py`

Attendu : `[registre] ecrit ...\backend\app\assets\studio_nodes.json (34 types)`

Puis Run : `python scripts/qa/dump_studio_registry.py --check`

Attendu : `[registre] a jour (34 types)`

- [ ] **Step 3 : écrire le banc de la validation**

Créer `backend/tests/test_studio_graph_io.py` :

```python
# -*- coding: utf-8 -*-
"""Studio P3 — importer un graphe JSON : valide contre le registre des noeuds,
et DIT ce qui manque.

Run : python tests/test_studio_graph_io.py  (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def _graphe_sain():
    return {"name": "essai",
            "nodes": [{"id": "im", "type": "Image", "x": 0, "y": 0,
                       "props": {"filename": "octopus_throne.png"}},
                      {"id": "sd", "type": "Seedance", "x": 300, "y": 0,
                       "props": {"durationS": 10}},
                      {"id": "rn", "type": "Render", "x": 600, "y": 0,
                       "props": {}}],
            "edges": [{"id": "e1", "from": "im", "fromPort": "out",
                       "to": "sd", "toPort": "image"},
                      {"id": "e2", "from": "sd", "fromPort": "out",
                       "to": "rn", "toPort": "in"}]}


# ── A. le registre miroite ─────────────────────────────────────────────────

def test_le_registre_json_suit_le_bundle():
    import json
    p = RACINE / "backend" / "app" / "assets" / "studio_nodes.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc["count"] == 34, doc["count"]
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    for nom, d in doc["types"].items():
        assert f'{nom}:{{cat:"{d["cat"]}"' in s, nom
    assert doc["types"]["Seedance"]["in"] == ["image", "end", "prompt"]
    assert doc["types"]["Render"]["in"] == ["in", "overlay", "audio", "fx"]
    assert doc["types"]["Image"]["in"] == []


# ── B. la validation, refus par refus ──────────────────────────────────────

def test_un_graphe_sain_passe_et_ressort_normalise():
    from app.services.studio_graph import valider
    g, avert, manques = valider(_graphe_sain())
    assert [n["id"] for n in g["nodes"]] == ["im", "sd", "rn"]
    assert g["nodes"][0]["props"]["filename"] == "octopus_throne.png"
    assert avert == [] and manques == []


def test_un_type_inconnu_est_refuse_en_le_NOMMANT():
    from app.services.studio_graph import valider
    g = _graphe_sain()
    g["nodes"][1]["type"] = "SoraDeluxe"
    with pytest.raises(ValueError) as e:
        valider(g)
    assert "SoraDeluxe" in str(e.value) and "34" in str(e.value)


def test_les_identifiants_en_double_sont_refuses():
    from app.services.studio_graph import valider
    g = _graphe_sain()
    g["nodes"][2]["id"] = "im"
    with pytest.raises(ValueError, match="im"):
        valider(g)


def test_un_cycle_est_refuse_en_nommant_les_noeuds():
    from app.services.studio_graph import valider
    g = _graphe_sain()
    g["edges"].append({"id": "e3", "from": "rn", "fromPort": "out",
                       "to": "im", "toPort": "in"})
    with pytest.raises(ValueError) as e:
        valider(g)
    assert "cycle" in str(e.value).lower()


def test_deux_noeuds_render_sont_refuses():
    from app.services.studio_graph import valider
    g = _graphe_sain()
    g["nodes"].append({"id": "rn2", "type": "Render", "x": 9, "y": 9})
    with pytest.raises(ValueError, match="Render"):
        valider(g)


def test_une_arete_sur_un_port_inexistant_est_JETEE_et_dite():
    from app.services.studio_graph import valider
    g = _graphe_sain()
    g["edges"][0]["toPort"] = "fantome"
    gg, avert, _m = valider(g)
    assert len(gg["edges"]) == 1, "l'arete fautive est jetee, pas gardee"
    assert any("fantome" in a and "Seedance" in a for a in avert), avert


def test_les_sources_manquantes_remontent_avec_le_noeud():
    from app.services.studio_graph import valider
    g = _graphe_sain()
    g["nodes"].append({"id": "er", "type": "ExistingRender", "x": 0, "y": 400,
                       "props": {"jobId": "job_disparu"}})
    _gg, _a, manques = valider(g, images=set(), jobs=set())
    par_noeud = {m["node_id"]: m for m in manques}
    assert par_noeud["im"]["champ"] == "filename"
    assert par_noeud["im"]["valeur"] == "octopus_throne.png"
    assert par_noeud["er"]["champ"] == "jobId"
    assert par_noeud["er"]["valeur"] == "job_disparu"
    # une source PRESENTE ne remonte pas
    _gg, _a, m2 = valider(g, images={"octopus_throne.png"},
                          jobs={"job_disparu"})
    assert m2 == []


def test_un_graphe_qui_nest_pas_un_graphe_est_refuse_parlant():
    from app.services.studio_graph import valider
    for mauvais in (None, [], {"nodes": []}, {"nodes": "x", "edges": []},
                    {"nodes": [{"type": "Image"}], "edges": []}):
        with pytest.raises(ValueError):
            valider(mauvais)


# ── C. la route ────────────────────────────────────────────────────────────

def test_la_route_d_import():
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            r = await c.post("/api/studio-graphs/import",
                             json={"graph": _graphe_sain()})
            assert r.status_code == 200, r.text
            d = r.json()
            assert len(d["graph"]["nodes"]) == 3
            assert [m["node_id"] for m in d["missing"]] == ["im"]
            mauvais = _graphe_sain()
            mauvais["nodes"][0]["type"] = "Inconnu"
            r = await c.post("/api/studio-graphs/import",
                             json={"graph": mauvais})
            assert r.status_code == 400 and "Inconnu" in r.json()["detail"]
            r = await c.post("/api/studio-graphs/import", json={})
            assert r.status_code == 400

    asyncio.run(scenario())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] **Step 4 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_studio_graph_io.py`

Attendu : `9 failed, 1 passed` — les neuf échecs disent
`ModuleNotFoundError: No module named 'app.services.studio_graph'` (et un 404
pour la route). Seul `test_le_registre_json_suit_le_bundle` passe.

- [ ] **Step 5 : écrire le validateur**

Créer `backend/app/services/studio_graph.py` :

```python
# -*- coding: utf-8 -*-
"""P3 — validation d'un graphe Studio importe, contre le registre des noeuds.

Le registre (backend/app/assets/studio_nodes.json) est extrait du bundle par
scripts/qa/dump_studio_registry.py : le bundle reste la source, ce JSON en est
le miroir cote serveur.

`valider` ne devine jamais : un type inconnu, un identifiant en double, un
cycle ou deux noeuds Render sont des REFUS qui nomment le fautif. Une arete
branchee sur un port inexistant est jetee et dite en avertissement — le graphe
reste ouvrable. Les sources absentes du disque remontent a part, pour que
l'ecran propose de les rebrancher au lieu de rendre un graphe muet.
"""
import json
from functools import lru_cache
from pathlib import Path

REGISTRE = Path(__file__).resolve().parent.parent / "assets" / "studio_nodes.json"
MAX_NOEUDS = 200
MAX_ARETES = 500
CHAMPS_SOURCE = (("filename", "images"), ("jobId", "jobs"))


@lru_cache(maxsize=1)
def registre() -> dict:
    return json.loads(REGISTRE.read_text(encoding="utf-8"))["types"]


def _nombre(v, defaut=0.0) -> float:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) \
        else defaut


def valider(graphe, images: set | None = None, jobs: set | None = None):
    """Rend (graphe_normalise, avertissements, sources_manquantes).

    `images` / `jobs` : les noms disponibles. None = on ne verifie pas (utile
    aux bancs purs). Un ensemble VIDE veut dire « rien n'est disponible ».
    """
    reg = registre()
    if not isinstance(graphe, dict):
        raise ValueError("Le fichier ne contient pas un graphe (objet JSON).")
    noeuds = graphe.get("nodes")
    aretes = graphe.get("edges") or []
    if not isinstance(noeuds, list) or not noeuds:
        raise ValueError("Le graphe n'a aucun noeud (champ 'nodes').")
    if not isinstance(aretes, list):
        raise ValueError("Le champ 'edges' n'est pas une liste.")
    if len(noeuds) > MAX_NOEUDS:
        raise ValueError(f"{len(noeuds)} noeuds : au-dela de {MAX_NOEUDS}, "
                         "ce n'est plus un graphe Studio.")
    if len(aretes) > MAX_ARETES:
        raise ValueError(f"{len(aretes)} aretes : au-dela de {MAX_ARETES}.")

    vus, propres, avert = set(), [], []
    for n in noeuds:
        if not isinstance(n, dict):
            raise ValueError("Un noeud n'est pas un objet JSON.")
        nid = str(n.get("id") or "").strip()
        typ = str(n.get("type") or "").strip()
        if not nid:
            raise ValueError("Un noeud n'a pas d'identifiant ('id').")
        if nid in vus:
            raise ValueError(f"Identifiant de noeud en double : {nid}.")
        if typ not in reg:
            raise ValueError(
                f"Type de noeud inconnu : {typ or '(vide)'}. Le registre de "
                f"cette version en compte {len(reg)}.")
        vus.add(nid)
        props = n.get("props")
        # les props inconnues sont GARDEES telles quelles : ts(), cote bundle,
        # fusionne les defauts du registre par-dessus, donc un graphe ecrit par
        # une version voisine reste ouvrable.
        props = dict(props) if isinstance(props, dict) else {}
        propres.append({"id": nid, "type": typ, "x": _nombre(n.get("x")),
                        "y": _nombre(n.get("y")), "props": props})
    rendus = [n for n in propres if n["type"] == "Render"]
    if len(rendus) > 1:
        raise ValueError(
            f"{len(rendus)} noeuds Render ({', '.join(r['id'] for r in rendus)})"
            " : le compilateur n'en accepte qu'un.")

    gardees = []
    for e in aretes:
        if not isinstance(e, dict):
            avert.append("Une arete n'est pas un objet JSON : jetee.")
            continue
        a, b = str(e.get("from") or ""), str(e.get("to") or "")
        pa, pb = str(e.get("fromPort") or ""), str(e.get("toPort") or "")
        if a not in vus or b not in vus:
            avert.append(f"Arete vers un noeud absent ({a} -> {b}) : jetee.")
            continue
        ta = next(n["type"] for n in propres if n["id"] == a)
        tb = next(n["type"] for n in propres if n["id"] == b)
        if pa not in reg[ta]["out"]:
            avert.append(f"Port de sortie '{pa}' inconnu sur {ta} ({a}) : "
                         "arete jetee.")
            continue
        if pb not in reg[tb]["in"]:
            avert.append(f"Port d'entree '{pb}' inconnu sur {tb} ({b}) : "
                         "arete jetee.")
            continue
        gardees.append({"id": str(e.get("id") or f"e_{a}_{b}_{pb}"),
                        "from": a, "fromPort": pa, "to": b, "toPort": pb})

    degre = {n["id"]: 0 for n in propres}
    for e in gardees:
        degre[e["to"]] += 1
    file = [i for i, d in degre.items() if not d]
    ordre = []
    while file:
        cur = file.pop(0)
        ordre.append(cur)
        for e in gardees:
            if e["from"] == cur:
                degre[e["to"]] -= 1
                if degre[e["to"]] == 0:
                    file.append(e["to"])
    if len(ordre) != len(propres):
        bloques = sorted(set(degre) - set(ordre))
        raise ValueError(
            "Le graphe contient un cycle : " + ", ".join(bloques) +
            ". Le Studio n'execute que des graphes orientes sans cycle.")

    manques = []
    for n in propres:
        for champ, magasin in CHAMPS_SOURCE:
            v = n["props"].get(champ)
            if not isinstance(v, str) or not v:
                continue
            dispo = images if magasin == "images" else jobs
            if dispo is not None and v not in dispo:
                manques.append({"node_id": n["id"], "type": n["type"],
                                "champ": champ, "valeur": v,
                                "magasin": magasin})

    nom = str(graphe.get("name") or "graphe importe")[:120]
    return ({"name": nom, "nodes": propres, "edges": gardees},
            avert, manques)
```

- [ ] **Step 6 : la route**

Dans `backend/app/api/routes.py`, juste après `save_studio_graph` (qui finit
ligne ~1807, avant `delete_studio_graph`), ajouter :

```python
@router.post("/studio-graphs/import")
async def import_studio_graph(body: dict, request: Request):
    """P3 — valide un graphe JSON exporte (ou ecrit a la main) contre le
    registre des noeuds, et rend ce qui manque. N'ENREGISTRE rien : l'ecran
    ouvre le graphe rendu, l'utilisateur decide de le garder."""
    _require_localhost(request)
    from app.services import studio_graph as SG
    graphe = body.get("graph")
    try:
        dispo_img = {p.name for p in settings.images_path.glob("*")
                     if p.is_file()}
    except OSError:
        dispo_img = set()
    async with async_session_factory() as session:
        res = await session.execute(select(JobRecord.id))
        dispo_jobs = {r[0] for r in res.all()}
    try:
        g, avert, manques = SG.valider(graphe, images=dispo_img,
                                       jobs=dispo_jobs)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"graph": g, "warnings": avert, "missing": manques}
```

Vérifier que `select`, `JobRecord` et `async_session_factory` sont déjà
importés dans `routes.py` ; si `select` ne l'est pas, ajouter
`from sqlalchemy import select` en tête du fichier.

- [ ] **Step 7 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_graph_io.py`

Attendu : `10 passed`.

- [ ] **Step 8 : commit**

```
git add scripts/qa/dump_studio_registry.py backend/app/assets/studio_nodes.json backend/app/services/studio_graph.py backend/app/api/routes.py backend/tests/test_studio_graph_io.py
git commit -m 'studio : le registre miroite et la validation dun graphe importe' -m 'Lexport existait, pas limport. Le registre des 34 noeuds vit dans le bundle : on lextrait vers un JSON que le serveur lit, et un banc surveille la derive. La validation refuse en NOMMANT le fautif — type inconnu avec le nombre de types connus, identifiant en double, cycle avec les noeuds bloques, deux noeuds Render — jette les aretes branchees sur un port inexistant en le disant, garde les props inconnues, et remonte a part les images et les rendus absents du disque pour que lecran propose de les rebrancher.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 7 : `studioimp` — le bouton Importer (P3)

**Files:**
- Create: `scripts/patch_bundle_studioimp.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (ligne 231)
- Test: `backend/tests/test_studio_graph_io.py` (section D)

- [ ] **Step 1 : écrire le patcher**

Créer `scripts/patch_bundle_studioimp.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_studioimp.py
"""P3 (IU) — le bouton Importer, a cote du selecteur de graphes.

BASELINE : bundle POST-patch studiohist. Backup dedie : .js.bak_studioimp.
Position : EN QUEUE. Plan : docs/superpowers/plans/2026-09-03-plan-studio.md

Tout le travail est cote serveur (POST /api/studio-graphs/import) : ici, un
bouton, un input file cache, et l'affichage des avertissements et des sources
manquantes AVANT que le graphe ne s'ouvre.

Run : python scripts/patch_bundle_studioimp.py [--check] [--deltas]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_studio import poser  # noqa: E402

TAG = "studioimp"
MARKER = "__DZ_STUDIOIMP"
MARKER_ATTENDU = 2
SPEC_CHAR_DELTA = None
SPEC_BYTE_DELTA = None

STABLE_PROBES = [
    ("studiopin", "__DZ_STUDIOPIN", 2),
    ("studiohist", "__DZ_STUDIOHIST", 2),
    ("selecteur-de-graphes", "function DzOpenGraph({onPick}){", 1),
    ("libpicker", "__dzLibPicker", 10),
]

BLOC = (
    "/*__DZ_STUDIOIMP__*/"
    "function DzImportGraph({onOpen}){"
    "var rf=x.useRef(null),ms=x.useState(null),msg=ms[0],setMsg=ms[1];"
    "function lire(f){if(!f)return;var fr=new FileReader();"
    "fr.onload=function(){var g;try{g=JSON.parse(String(fr.result))}"
    'catch(e){setMsg({err:"Ce fichier n\\u2019est pas du JSON valide."});'
    "return}"
    'fetch("/api/studio-graphs/import",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({graph:g&&g.graph?g.graph:g})})"
    ".then(function(R){return R.json().then(function(d){"
    "return{ok:R.ok,d:d}})})"
    ".then(function(o){if(!o.ok){"
    'setMsg({err:String((o.d&&o.d.detail)||"Import refuse")});return}'
    "setMsg({ok:!0,warn:o.d.warnings||[],miss:o.d.missing||[]});"
    "onOpen(o.d.graph)})"
    '.catch(function(e){setMsg({err:String(e&&e.message||e)})})};'
    "fr.readAsText(f)}"
    'return r.jsxs(r.Fragment,{children:[r.jsx("input",{ref:rf,'
    'type:"file",accept:"application/json,.json",'
    'style:{display:"none"},onChange:function(ev){'
    "lire(ev.target.files&&ev.target.files[0]);ev.target.value=\"\"}}),"
    'r.jsx(K,{variant:"outline",size:"sm",icon:"upload",'
    'title:"Ouvrir un graphe export\\u00e9 (.json)",'
    "onClick:function(){rf.current&&rf.current.click()},"
    'children:"Importer"}),'
    "msg?r.jsx(\"span\",{style:{fontSize:10.5,maxWidth:280,"
    'color:msg.err?"var(--red)":"var(--ink-soft)"},'
    "children:msg.err?msg.err:"
    "((msg.miss.length?msg.miss.length"
    '+" source(s) \\u00e0 rebrancher : "'
    '+msg.miss.map(function(m){return m.valeur}).join(", "):'
    '"Graphe import\\u00e9.")'
    '+(msg.warn.length?" \\u00b7 "+msg.warn.length'
    '+" avertissement(s) : "+msg.warn[0]:""))}):null]})}'
    "/*__DZ_STUDIOIMP_END__*/"
)
_A1 = "function DzOpenGraph({onPick}){"

_A2 = "r.jsx(DzOpenGraph,{onPick:async id=>{"
_R2 = ("r.jsx(DzImportGraph,{onOpen:function(G){i(ts(G));d({});f({});"
       "a(null);k(null)}}),r.jsx(DzOpenGraph,{onPick:async id=>{")

PATCHES = [
    ("S1-bloc", _A1, BLOC + _A1),
    ("S2-barre-du-haut", _A2, _R2),
]

POST_COUNTS = [
    ("DzImportGraph", 2),
    ("/api/studio-graphs/import", 1),
    ("DzOpenGraph", 2),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(poser(TAG, MARKER, MARKER_ATTENDU, PATCHES, STABLE_PROBES,
                   POST_COUNTS, SPEC_CHAR_DELTA, SPEC_BYTE_DELTA,
                   "P3 : bouton Importer"))
```

- [ ] **Step 2 : figer, vérifier, appliquer**

Run : `python scripts/patch_bundle_studioimp.py --deltas` → recopier les deux
nombres dans les constantes.

Run : `python scripts/patch_bundle_studioimp.py --check`
Attendu : `[studioimp] 2 ancres OK, marqueur absent, 4 sondes aux comptes`.

Run : `python scripts/patch_bundle_studioimp.py`
Attendu : `backup -> index-BEOJX8L5.js.bak_studioimp` puis
`OK - bundle patche (P3 : bouton Importer).`

Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK`
Attendu : `SYNTAXE_OK`.

- [ ] **Step 3 : le banc miroir**

Ajouter à `backend/tests/test_studio_graph_io.py`, avant le `if __name__` :

```python
# ── D. le bouton, dans le bundle livre ─────────────────────────────────────

def test_le_bouton_importer_est_dans_la_barre_du_haut():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert s.count("DzImportGraph") == 2
    assert s.count("/api/studio-graphs/import") == 1
    # il est POSE a cote du selecteur de graphes, pas ailleurs
    assert ("r.jsx(DzImportGraph,{onOpen:function(G){i(ts(G));"
            "d({});f({});a(null);k(null)}}),"
            "r.jsx(DzOpenGraph,{onPick:async id=>{") in s
    # un JSON illisible est dit AVANT tout appel reseau
    assert "n’est pas du JSON valide" in s
    # les sources manquantes et les avertissements sont ECRITS, pas comptes
    assert "source(s) à rebrancher : " in s
    assert 'avertissement(s) : "+msg.warn[0]' in s
    # le graphe importe passe par ts() : les props par defaut sont fusionnees
    assert "onOpen:function(G){i(ts(G));" in s


def test_le_patcher_dimport_tient_la_queue_de_chaine():
    p = (RACINE / "scripts"
         / "patch_bundle_studioimp.py").read_text(encoding="utf-8")
    assert 'TAG = "studioimp"' in p and "from _patch_studio import poser" in p
    assert (RACINE / "frontend" / "dist" / "assets"
            / "index-BEOJX8L5.js.bak_studioimp").is_file()
```

- [ ] **Step 4 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_graph_io.py`

Attendu : `12 passed`.

- [ ] **Step 5 : commit**

```
git add scripts/patch_bundle_studioimp.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_graph_io.py
git commit -m 'studio : le bouton Importer un graphe' -m 'Un input file cache, un POST vers la route de validation, et le resultat ECRIT a cote du bouton : le nombre de sources a rebrancher avec leurs noms, et le premier avertissement. Le graphe accepte passe par ts() avant douvrir, donc les props par defaut du registre sont fusionnees et un graphe dune version voisine reste utilisable.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 8 : `studioscrub` — le défilement image par image (P4)

**Files:**
- Create: `scripts/patch_bundle_studioscrub.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (ligne 283)
- Test: `backend/tests/test_studio_lecture.py` (section P4)

Le tiroir de résultat `Jh` affiche un `<video controls autoPlay>` : il lit, il
ne parcourt pas. On le remplace par un lecteur avec réglette en images,
compteur `f 128 / 450`, boutons `‹` `›` et les touches `,` et `.` (les touches
de Resolve, que l'utilisateur connaît). `requestVideoFrameCallback` affine la
position quand le navigateur l'a ; sinon `currentTime` suffit.

- [ ] **Step 1 : écrire le patcher**

Créer `scripts/patch_bundle_studioscrub.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_studioscrub.py
"""P4 — le tiroir de resultat se parcourt image par image.

BASELINE : bundle POST-patch studioimp. Backup dedie : .js.bak_studioscrub.
Position : EN QUEUE. Plan : docs/superpowers/plans/2026-09-03-plan-studio.md

Jh est possede par le bundle d'origine ; aucun autre patcher n'y ecrit
(verifie le 03/09 : une seule occurrence de la balise video du resultat).

Run : python scripts/patch_bundle_studioscrub.py [--check] [--deltas]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_studio import poser  # noqa: E402

TAG = "studioscrub"
MARKER = "__DZ_STUDIOSCRUB"
MARKER_ATTENDU = 2
SPEC_CHAR_DELTA = None
SPEC_BYTE_DELTA = None

STABLE_PROBES = [
    ("studiopin", "__DZ_STUDIOPIN", 2),
    ("studiohist", "__DZ_STUDIOHIST", 2),
    ("studioimp", "__DZ_STUDIOIMP", 2),
    ("tiroir-resultat", "function Jh({onClose:e,graph:t,lastJob:n}){", 1),
]

BLOC = (
    "/*__DZ_STUDIOSCRUB__*/"
    "function __dzFps(g){var n=((g&&g.nodes)||[]).find(function(z){"
    'return z.type==="Render"});'
    "var f=n&&n.props&&Number(n.props.fps);return f>0?f:30}"
    "function DzScrub({jobId,fps}){"
    "var vr=x.useRef(null),st=x.useState({d:0,t:0}),s=st[0],set=st[1];"
    "var F=Math.max(1,Number(fps)||30);"
    "function pose(t){var v=vr.current;if(!v)return;v.pause();"
    "var d=v.duration||0,n=Math.max(0,Math.min(d,t));v.currentTime=n;"
    "set({d:d,t:n});"
    "if(v.requestVideoFrameCallback)v.requestVideoFrameCallback("
    "function(_n,md){set({d:v.duration||0,"
    "t:(md&&md.mediaTime)||v.currentTime})})}"
    "function pas(k){var v=vr.current;if(v)pose((v.currentTime||0)+k/F)}"
    "x.useEffect(function(){function onk(ev){"
    "if(ev.target&&/^(INPUT|TEXTAREA)$/.test(ev.target.tagName))return;"
    'if(ev.key===","){ev.preventDefault();pas(-1)}'
    'else if(ev.key==="."){ev.preventDefault();pas(1)}}'
    'window.addEventListener("keydown",onk);'
    'return function(){window.removeEventListener("keydown",onk)}},[]);'
    'return r.jsxs("div",{children:['
    'r.jsx("video",{ref:vr,src:D.jobVideoUrl(jobId),controls:!0,'
    'preload:"metadata",'
    "onLoadedMetadata:function(ev){set({d:ev.target.duration||0,t:0})},"
    "onTimeUpdate:function(ev){set({d:ev.target.duration||0,"
    "t:ev.target.currentTime||0})},"
    'style:{width:"100%",borderRadius:8,background:"#000",'
    'border:"1px solid var(--stroke-strong)"}}),'
    'r.jsxs("div",{style:{display:"flex",alignItems:"center",gap:6,'
    'marginTop:8},children:['
    'r.jsx(K,{variant:"outline",size:"sm",title:"Image pr\\u00e9c\\u00e9dente '
    '(,)",onClick:function(){pas(-1)},children:"\\u2039"}),'
    'r.jsx("input",{type:"range",min:0,'
    "max:Math.max(1,Math.round(s.d*F)),step:1,"
    "value:Math.round(s.t*F),"
    "onChange:function(ev){pose(Number(ev.target.value)/F)},"
    'style:{flex:1,accentColor:"var(--cyan)"}}),'
    'r.jsx(K,{variant:"outline",size:"sm",title:"Image suivante (.)",'
    'onClick:function(){pas(1)},children:"\\u203a"}),'
    'r.jsx("span",{className:"mono",style:{fontSize:10.5,'
    'color:"var(--ink-soft)",minWidth:78,textAlign:"right"},'
    'children:"f "+Math.round(s.t*F)+" / "+Math.round(s.d*F)})]}),'
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-muted)",'
    'marginTop:4},children:"\\u00ab , \\u00bb et \\u00ab . \\u00bb reculent '
    'et avancent d\\u2019une image \\u00b7 "+F+" ips"})]})}'
    "/*__DZ_STUDIOSCRUB_END__*/"
)
_A1 = "function Jh({onClose:e,graph:t,lastJob:n}){"

_A2 = ('r.jsx("video",{src:D.jobVideoUrl(n.id),controls:!0,autoPlay:!0,'
       'style:{width:"100%",borderRadius:8,background:"#000",'
       'border:"1px solid var(--stroke-strong)"}})')
_R2 = "r.jsx(DzScrub,{jobId:n.id,fps:__dzFps(t)})"

PATCHES = [
    ("S1-bloc", _A1, BLOC + _A1),
    ("S2-lecteur", _A2, _R2),
]

POST_COUNTS = [
    ("DzScrub", 2),
    ("__dzFps", 2),
    ("requestVideoFrameCallback", 2),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(poser(TAG, MARKER, MARKER_ATTENDU, PATCHES, STABLE_PROBES,
                   POST_COUNTS, SPEC_CHAR_DELTA, SPEC_BYTE_DELTA,
                   "P4 : defilement image par image"))
```

- [ ] **Step 2 : figer, vérifier, appliquer**

Run : `python scripts/patch_bundle_studioscrub.py --deltas` → recopier.

Run : `python scripts/patch_bundle_studioscrub.py --check`
Attendu : `[studioscrub] 2 ancres OK, marqueur absent, 4 sondes aux comptes`.

Run : `python scripts/patch_bundle_studioscrub.py`
Attendu : `OK - bundle patche (P4 : defilement image par image).`

Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK`
Attendu : `SYNTAXE_OK`.

- [ ] **Step 3 : le banc**

Ajouter à `backend/tests/test_studio_lecture.py`, avant le `if __name__` :

```python
# ── P4 : le defilement ─────────────────────────────────────────────────────

def test_les_images_par_seconde_viennent_du_noeud_render():
    js = _bloc("/*__DZ_STUDIOSCRUB__*/", "/*__DZ_STUDIOSCRUB_END__*/") + """
var defaut=__dzFps({nodes:[{id:"a",type:"Image",props:{}}],edges:[]});
var lu=__dzFps({nodes:[{id:"r",type:"Render",props:{fps:24}}],edges:[]});
var zero=__dzFps({nodes:[{id:"r",type:"Render",props:{fps:0}}],edges:[]});
var vide=__dzFps(null);
console.log([defaut,lu,zero,vide].join(","));
"""
    assert _node(js) == "30,24,30,30"


def test_le_lecteur_parcourt_au_lieu_de_seulement_lire():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert s.count("DzScrub") == 2
    # le lecteur d'origine est REMPLACE, pas double
    assert "autoPlay:!0" not in s
    assert "r.jsx(DzScrub,{jobId:n.id,fps:__dzFps(t)})" in s
    # une reglette en IMAGES, pas en secondes
    assert "max:Math.max(1,Math.round(s.d*F))" in s
    assert 'children:"f "+Math.round(s.t*F)+" / "+Math.round(s.d*F)' in s
    # les touches de Resolve, et elles ne volent pas la frappe d'un champ
    assert "/^(INPUT|TEXTAREA)$/.test(ev.target.tagName)" in s
    # la precision quand le navigateur la donne, sans en dependre
    assert "if(v.requestVideoFrameCallback)v.requestVideoFrameCallback(" in s
    # et l'ecran DIT les touches
    assert "reculent et avancent d’une image" in s
```

- [ ] **Step 4 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_lecture.py`

Attendu : `5 passed`.

- [ ] **Step 5 : commit**

```
git add scripts/patch_bundle_studioscrub.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_lecture.py
git commit -m 'studio : le tiroir de resultat se parcourt image par image' -m 'Le lecteur lisait ; il parcourt. Reglette graduee en IMAGES et non en secondes, compteur f 128 sur 450, boutons et touches virgule et point — celles de Resolve, que lutilisateur connait — et une garde pour quelles ne volent pas la frappe dun champ. Les images par seconde viennent du noeud Render, 30 a defaut. requestVideoFrameCallback affine la position quand le navigateur la donne, sans que le lecteur en depende.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — différenciant

### Task 9 : La recette lançable, côté serveur (D1)

**Files:**
- Modify: `backend/app/api/routes.py:157-224` (extraire le démarreur de rendu)
- Modify: `backend/app/api/routes.py:1790-1807` (`save_studio_graph` : champ `recipe`)
- Create: `backend/app/services/studio_recette.py`
- Test: `backend/tests/test_studio_recette.py`

Le compilateur `Mh` vit dans le bundle : le serveur ne peut pas compiler un
graphe. Une recette est donc une **compilation figée** — le corps de requête
exact que le Studio aurait envoyé — plus la liste de ses **trous** : les
chemins, dans `slot_values`, où une source se remplace. Lancer la recette N
avec d'autres assets = recopier la compilation, poser les valeurs aux chemins
déclarés, et repartir dans la route de rendu existante. Aucun compilateur
dupliqué.

- [ ] **Step 1 : le banc**

Créer `backend/tests/test_studio_recette.py` :

```python
# -*- coding: utf-8 -*-
"""Studio D1 — une recette lancable : compilation figee + trous declares.

Run : python tests/test_studio_recette.py  (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def _recette():
    return {
        "template_id": "tpl_studio_montage",
        "template": {"id": "tpl_studio_montage", "regions": []},
        "title": "reel du matin",
        "slot_values": {
            "clip0": {"source_kind": "seedance",
                      "seedance": {"image_filename": "vieux.png",
                                   "duration_s": 5}},
            "clip1": {"source_kind": "upload", "upload_filename": "b.png"},
            "clip2": {"source_kind": "job", "job_id": "j-vieux"},
        },
        "holes": [
            {"key": "clip0", "path": ["clip0", "seedance", "image_filename"],
             "kind": "image", "label": "Seedance — image de depart"},
            {"key": "clip1", "path": ["clip1", "upload_filename"],
             "kind": "image", "label": "Image"},
            {"key": "clip2", "path": ["clip2", "job_id"],
             "kind": "job", "label": "Rendu existant"},
        ],
    }


# ── A. poser les valeurs aux chemins declares ──────────────────────────────

def test_remplir_ne_touche_que_les_chemins_declares():
    from app.services.studio_recette import remplir
    sv = remplir(_recette(), {"clip0": "neuve.png", "clip2": "j-neuf"})
    assert sv["clip0"]["seedance"]["image_filename"] == "neuve.png"
    assert sv["clip0"]["seedance"]["duration_s"] == 5, "le reglage est garde"
    assert sv["clip2"]["job_id"] == "j-neuf"
    assert sv["clip1"]["upload_filename"] == "b.png", "trou non rempli intact"


def test_remplir_ne_modifie_pas_la_recette_enregistree():
    from app.services.studio_recette import remplir
    rec = _recette()
    remplir(rec, {"clip1": "autre.png"})
    assert rec["slot_values"]["clip1"]["upload_filename"] == "b.png"


def test_une_cle_inconnue_est_refusee_en_listant_les_connues():
    from app.services.studio_recette import remplir
    with pytest.raises(ValueError) as e:
        remplir(_recette(), {"clipZ": "x.png"})
    assert "clipZ" in str(e.value)
    for k in ("clip0", "clip1", "clip2"):
        assert k in str(e.value)


def test_un_nom_de_fichier_traversant_est_refuse():
    from app.services.studio_recette import remplir
    for mauvais in ("../secret.png", "a/b.png", "", 42):
        with pytest.raises(ValueError):
            remplir(_recette(), {"clip1": mauvais})


def test_une_recette_sans_trous_ou_sans_compilation_est_refusee():
    from app.services.studio_recette import remplir
    with pytest.raises(ValueError, match="recette"):
        remplir({"slot_values": {}}, {})
    with pytest.raises(ValueError, match="recette"):
        remplir({"holes": []}, {})


# ── B. la route ────────────────────────────────────────────────────────────

def test_enregistrer_puis_lancer_une_recette():
    import asyncio
    from httpx import ASGITransport, AsyncClient

    async def scenario():
        from app.config import settings
        from app.main import app
        from app.services.storage import init_db
        await init_db()
        (settings.images_path / "neuve.png").write_bytes(b"\x89PNG\r\n\x1a\nx")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            g = {"nodes": [{"id": "n1", "type": "Render", "props": {}}],
                 "edges": []}
            r = await c.post("/api/studio-graphs",
                             json={"name": "Reel matin", "graph": g,
                                   "recipe": _recette()})
            assert r.status_code == 200, r.text
            gid = r.json()["id"]
            # la liste dit QUI est une recette
            r = await c.get("/api/studio-graphs")
            ligne = [x for x in r.json()["graphs"] if x["id"] == gid][0]
            assert ligne["recipe"] is True
            # les trous se lisent sans lancer
            r = await c.get(f"/api/studio-graphs/{gid}/recipe")
            assert r.status_code == 200
            assert [h["key"] for h in r.json()["holes"]] == \
                ["clip0", "clip1", "clip2"]
            # un fichier absent du disque est refuse EN LE NOMMANT
            r = await c.post(f"/api/studio-graphs/{gid}/run",
                             json={"fill": {"clip1": "absente.png"}})
            assert r.status_code == 400 and "absente.png" in r.json()["detail"]
            # une cle inconnue aussi
            r = await c.post(f"/api/studio-graphs/{gid}/run",
                             json={"fill": {"clipZ": "neuve.png"}})
            assert r.status_code == 400 and "clipZ" in r.json()["detail"]
            # un graphe qui n'est PAS une recette : 404 qui le dit
            r = await c.post("/api/studio-graphs",
                             json={"name": "simple", "graph": g})
            autre = r.json()["id"]
            r = await c.post(f"/api/studio-graphs/{autre}/run", json={})
            assert r.status_code == 404 and "recette" in r.json()["detail"]

    asyncio.run(scenario())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] **Step 2 : lancer, constater le rouge**

Run (depuis `backend/`) : `python tests/test_studio_recette.py`

Attendu : `6 failed` — `ModuleNotFoundError: No module named
'app.services.studio_recette'`, et la route rend 404 sur `/recipe`.

- [ ] **Step 3 : le service**

Créer `backend/app/services/studio_recette.py` :

```python
# -*- coding: utf-8 -*-
"""D1 — une recette : la compilation FIGEE d'un graphe, plus ses trous.

Le compilateur du Studio vit dans le bundle ; le serveur ne compile pas. Une
recette est donc le corps de requete exact que le Studio aurait envoye, et la
liste des chemins, dans slot_values, ou une source se remplace. Lancer une
recette = recopier, poser les valeurs aux chemins declares, repartir dans la
route de rendu existante.

`remplir` ne pose QUE sur les chemins declares : aucune cle libre, aucun
chemin devine. C'est ce qui rend la route sure a exposer a un autre ecran ou
au telephone.
"""
import copy

KINDS = ("image", "job", "text")


def _nom_sain(v) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError("Une valeur de recette doit etre un texte non vide.")
    v = v.strip()
    if "/" in v or "\\" in v or v.startswith("."):
        raise ValueError(f"Nom de fichier refuse : {v}")
    return v


def trous(recette: dict) -> list:
    h = (recette or {}).get("holes")
    sv = (recette or {}).get("slot_values")
    if not isinstance(h, list) or not isinstance(sv, dict):
        raise ValueError(
            "Ce graphe n'est pas une recette : il lui manque sa compilation "
            "figee (slot_values) ou ses trous (holes). Ouvre-le dans le "
            "Studio et enregistre-le comme recette.")
    return h


def remplir(recette: dict, fill: dict | None) -> dict:
    """Rend une COPIE de slot_values avec les valeurs posees aux chemins."""
    h = trous(recette)
    sv = copy.deepcopy(recette["slot_values"])
    par_cle = {t["key"]: t for t in h if isinstance(t, dict) and t.get("key")}
    for cle, val in (fill or {}).items():
        t = par_cle.get(cle)
        if t is None:
            raise ValueError(
                f"Trou inconnu : {cle}. Cette recette accepte "
                + ", ".join(sorted(par_cle)) + ".")
        kind = t.get("kind")
        if kind not in KINDS:
            raise ValueError(f"Trou {cle} : genre inconnu {kind}.")
        if kind == "image":
            val = _nom_sain(val)
        elif kind == "job":
            val = _nom_sain(val)
        else:
            if not isinstance(val, str):
                raise ValueError(f"Trou {cle} : un texte est attendu.")
            val = val[:4000]
        chemin = t.get("path") or []
        if not chemin or not all(isinstance(p, str) for p in chemin):
            raise ValueError(f"Trou {cle} : chemin absent ou mal forme.")
        cur = sv
        for p in chemin[:-1]:
            if not isinstance(cur, dict) or p not in cur:
                raise ValueError(
                    f"Trou {cle} : le chemin {'/'.join(chemin)} n'existe plus "
                    "dans la compilation. Reenregistre la recette.")
            cur = cur[p]
        if not isinstance(cur, dict):
            raise ValueError(f"Trou {cle} : chemin invalide.")
        cur[chemin[-1]] = val
    return sv
```

- [ ] **Step 4 : le champ `recipe` au stockage**

Dans `backend/app/api/routes.py`, `save_studio_graph` (ligne ~1791) : après
la ligne `rec = {"id": gid, "name": name, "graph": graph, ...}`, remplacer ce
dictionnaire par :

```python
    rec = {"id": gid, "name": name, "graph": graph,
           "updated_at": _dtnow.utcnow().isoformat()}
    # D1 — la compilation figee et ses trous, quand l'ecran enregistre une
    # recette. Absente = graphe ordinaire.
    if isinstance(body.get("recipe"), dict):
        rec["recipe"] = body["recipe"]
```

Et dans `list_studio_graphs` (ligne ~1766), l'entrée ajoutée devient :

```python
            out.append({"id": d.get("id", f.stem),
                        "name": d.get("name", f.stem),
                        "recipe": isinstance(d.get("recipe"), dict),
                        "updated_at": d.get("updated_at")})
```

- [ ] **Step 5 : extraire le démarreur de rendu**

Dans `backend/app/api/routes.py`, la route `render_layout_template`
(ligne 157) se termine par `return TemplateRenderResponse(...)`. Remplacer
tout le bloc qui suit la validation — c'est-à-dire depuis
`job_id = str(uuid4())` (ligne 190) jusqu'au `return` inclus — par un appel,
et poser la fonction extraite juste avant la route :

```python
def _demarrer_rendu_template(template_id: str, request: TemplateRenderRequest,
                             background_tasks: BackgroundTasks) -> str:
    """Range le graphe source, met le rendu en tache de fond, rend le job_id.
    Partage par la route de rendu et par le lancement d'une recette (D1)."""
    job_id = str(uuid4())
    if request.source_graph:
        try:
            import json as _json
            gdir = settings.outputs_path / "_graphs"
            gdir.mkdir(parents=True, exist_ok=True)
            (gdir / f"{job_id}.json").write_text(
                _json.dumps(request.source_graph, ensure_ascii=False),
                encoding="utf-8")
        except Exception as e:
            logger.warning(f"source_graph save failed for {job_id}: {e}")

    async def _run():
        try:
            await pipeline.render_template(
                template_id=template_id,
                slot_values=request.slot_values,
                voice_mode=request.voice_mode,
                job_id=job_id,
                template=request.template,
                title=request.title,
                source_graph=request.source_graph,
                node_slots=request.node_slots,
                preview=request.preview,
                voiceover=request.voiceover,
            )
        except Exception as e:
            logger.exception(f"Template render {job_id} failed: {e}")

    background_tasks.add_task(_run)
    return job_id
```

Le corps de la route devient, après le bloc de validation des clés :

```python
    job_id = _demarrer_rendu_template(template_id, request, background_tasks)
    return TemplateRenderResponse(
        template_id=template_id,
        job_id=job_id,
        message=f"Template render queued. Poll GET /api/jobs/{job_id}.",
    )
```

- [ ] **Step 6 : les deux routes de recette**

Dans `backend/app/api/routes.py`, après `import_studio_graph` (T6), ajouter :

```python
def _lire_graphe_enregistre(graph_id: str) -> dict:
    import json as _json
    p = _studio_graphs_dir() / f"{Path(graph_id).name}.json"
    if not p.is_file():
        raise HTTPException(404, "Graph not found")
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(500, "Graph unreadable")


@router.get("/studio-graphs/{graph_id}/recipe")
async def get_studio_recipe(graph_id: str):
    """Les trous d'une recette : de quoi construire le formulaire ailleurs
    (Bibliotheque, Quick, telephone) sans ouvrir le Studio."""
    from app.services import studio_recette as SR
    rec = _lire_graphe_enregistre(graph_id).get("recipe")
    try:
        h = SR.trous(rec)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"id": Path(graph_id).name, "holes": h,
            "title": (rec or {}).get("title") or ""}


@router.post("/studio-graphs/{graph_id}/run")
async def run_studio_recipe(graph_id: str, body: dict,
                            background_tasks: BackgroundTasks,
                            request: Request):
    """D1 — lancer la recette N avec ces sources. Body : {fill:{cle: valeur},
    title?}. Rien n'est compile ici : on repose les valeurs aux chemins
    declares et l'on repart dans le rendu de template existant."""
    _require_localhost(request)
    from app.services import studio_recette as SR
    doc = _lire_graphe_enregistre(graph_id)
    rec = doc.get("recipe")
    try:
        SR.trous(rec)
        slot_values = SR.remplir(rec, body.get("fill") or {})
    except ValueError as e:
        code = 404 if "n'est pas une recette" in str(e) else 400
        raise HTTPException(code, str(e))
    # les sources nommees doivent exister : un refus vaut mieux qu'un rendu
    # noir decouvert dix minutes plus tard.
    for cle, val in (body.get("fill") or {}).items():
        trou = next(t for t in rec["holes"] if t.get("key") == cle)
        if trou.get("kind") == "image" and \
                not (settings.images_path / val).is_file():
            raise HTTPException(400, f"Image introuvable : {val}")
        if trou.get("kind") == "job":
            async with async_session_factory() as session:
                jr = await session.get(JobRecord, val)
            if jr is None or not (jr.final_video_path or jr.video_path):
                raise HTTPException(400, f"Rendu introuvable : {val}")
    req = TemplateRenderRequest(
        template_id=rec["template_id"],
        slot_values=slot_values,
        template=rec.get("template"),
        title=(body.get("title") or rec.get("title")
               or doc.get("name") or "recette")[:200],
        source_graph=doc.get("graph"),
        node_slots=rec.get("node_slots"),
    )
    job_id = _demarrer_rendu_template(rec["template_id"], req,
                                      background_tasks)
    return {"job_id": job_id, "graph_id": Path(graph_id).name,
            "message": f"Recipe queued. Poll GET /api/jobs/{job_id}."}
```

- [ ] **Step 7 : lancer les bancs**

Run (depuis `backend/`) : `python tests/test_studio_recette.py`
Attendu : `6 passed`.

Run : `python tests/test_studio_pin.py`
Attendu : `15 passed` — le démarreur extrait ne casse pas la route de rendu.

- [ ] **Step 8 : commit**

```
git add backend/app/services/studio_recette.py backend/app/api/routes.py backend/tests/test_studio_recette.py
git commit -m 'studio : la recette lancable, compilation figee et trous declares' -m 'Le compilateur vit dans le bundle : le serveur ne compile pas. Une recette est donc le corps de requete exact que le Studio aurait envoye, plus la liste des chemins ou une source se remplace. Lancer = recopier, poser aux chemins DECLARES seulement, repartir dans le demarreur de rendu — extrait ici pour etre partage par les deux routes. Une cle inconnue est refusee en listant les connues, un nom traversant est refuse, et une image ou un rendu absent du disque est refuse AVANT le tir plutot que decouvert dix minutes plus tard.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 10 : `studiorecette` — capturer la compilation et enregistrer (D1)

**Files:**
- Create: `scripts/patch_bundle_studiorecette.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (lignes 44, 231)
- Test: `backend/tests/test_studio_recette.py` (section C)

La capture réutilise le tour déjà employé par la preview
(`window.__dzfxPreview`) : un drapeau fait rendre à `renderLayoutTemplate` le
corps qu'elle allait envoyer, au lieu de l'envoyer. Les branches Seedance
seul, avatar seul et Animation ne passent pas par cette fonction — elles
tirent directement chez le fournisseur — donc la capture les **refuse en le
disant** plutôt que de payer un rendu pour fabriquer une recette.

- [ ] **Step 1 : écrire le patcher**

Créer `scripts/patch_bundle_studiorecette.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_studiorecette.py
"""D1 (IU) — enregistrer un graphe comme recette.

BASELINE : bundle POST-patch studioscrub. Backup dedie : .js.bak_studiorecette.
Position : EN QUEUE. Plan : docs/superpowers/plans/2026-09-03-plan-studio.md

La capture reprend le drapeau de la preview : renderLayoutTemplate rend le
corps au lieu de l'envoyer. Les branches qui NE passent pas par elle (Seedance
seul, avatar seul, Animation) sont refusees en le disant.

Run : python scripts/patch_bundle_studiorecette.py [--check] [--deltas]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_studio import poser  # noqa: E402

TAG = "studiorecette"
MARKER = "__DZ_STUDIORECETTE"
MARKER_ATTENDU = 2
SPEC_CHAR_DELTA = None
SPEC_BYTE_DELTA = None

STABLE_PROBES = [
    ("studiopin", "__DZ_STUDIOPIN", 2),
    ("studiohist", "__DZ_STUDIOHIST", 2),
    ("studioimp", "__DZ_STUDIOIMP", 2),
    ("studioscrub", "__DZ_STUDIOSCRUB", 2),
    ("preview", "__dzfxPreview", 4),
]

# ── S1 : la prise de capture, en tete de renderLayoutTemplate ──────────────
_A1 = ("renderLayoutTemplate:async(e,t,n,o,i,g)=>{try{"
       "var _pv=!!window.__dzfxPreview;window.__dzfxPreview=!1;")
_R1 = ("renderLayoutTemplate:async(e,t,n,o,i,g)=>{try{"
       "var _pv=!!window.__dzfxPreview;window.__dzfxPreview=!1;"
       "if(window.__dzCapture){window.__dzCapture=!1;return{ok:!0,captured:{"
       "template_id:e,slot_values:t||{},template:o||null,title:i||null,"
       "node_slots:Object.assign({},window.__dzNS||{})}}}")

# ── S2 : le bloc — trous, capture, bouton ──────────────────────────────────
BLOC = (
    "/*__DZ_STUDIORECETTE__*/"
    # une recette n'a de sens que sur les branches qui passent par un template
    "function __dzRecetteOk(g){var n=(g&&g.nodes)||[];"
    "function a(t){return n.some(function(z){return z.type===t})}"
    'return a("SpatialCompose")||a("Concatenate")||'
    'n.some(function(z){return z.type==="Upload"&&z.props&&z.props.jobId})}'
    # les trous : un par source remplacable de la compilation
    "function __dzTrous(cap,g){var t=[],sv=(cap&&cap.slot_values)||{},"
    "ns=(cap&&cap.node_slots)||{};"
    "Object.keys(sv).sort().forEach(function(k){var v=sv[k]||{},"
    'nid=ns[k]||"",n=((g&&g.nodes)||[]).find(function(z){'
    "return z.id===nid});"
    "var lbl=(n&&Me[n.type]&&Me[n.type].title)||k;"
    'if(v.source_kind==="upload"&&v.upload_filename)'
    't.push({key:k,path:[k,"upload_filename"],kind:"image",'
    'label:lbl+" \\u2014 image",value:v.upload_filename});'
    'else if(v.source_kind==="job"&&v.job_id)'
    't.push({key:k,path:[k,"job_id"],kind:"job",'
    'label:lbl+" \\u2014 rendu",value:v.job_id});'
    'else if(v.source_kind==="seedance"&&v.seedance&&'
    "v.seedance.image_filename)"
    't.push({key:k,path:[k,"seedance","image_filename"],kind:"image",'
    'label:lbl+" \\u2014 image de d\\u00e9part",'
    "value:v.seedance.image_filename});"
    'else if(v.source_kind==="heygen"&&v.heygen)'
    't.push({key:k,path:[k,"heygen","script"],kind:"text",'
    'label:lbl+" \\u2014 script",value:v.heygen.script||""});'
    'else if(v.source_kind==="text")'
    't.push({key:k,path:[k,"text"],kind:"text",'
    'label:lbl+" \\u2014 texte",value:v.text||""})});'
    "return t}"
    # capture : Mh compile, run() rend le corps au lieu de l'envoyer
    "async function __dzCapturer(g){if(!__dzRecetteOk(g))"
    'throw new Error("Une recette se fait d\\u2019un graphe qui passe par '
    "Spatial compose, Concatenate ou une vid\\u00e9o UGC. Un Seedance seul "
    "ou un avatar seul tire directement chez le fournisseur : il n\\u2019y a "
    'rien \\u00e0 figer.");'
    "var R=Mh(g);if(!R.ok)throw new Error(R.error);"
    "window.__dzCapture=!0;var out;"
    "try{out=await R.run()}finally{window.__dzCapture=!1}"
    "if(!out||!out.captured)"
    'throw new Error("La compilation n\\u2019a pas pu \\u00eatre fig\\u00e9e '
    '(branche non g\\u00e9r\\u00e9e).");'
    "var cap=out.captured;cap.holes=__dzTrous(cap,g);return cap}"
    "function DzRecetteBtn({graph,setGraph,dire}){"
    "var bs=x.useState(!1),busy=bs[0],setB=bs[1];"
    'return r.jsx(K,{variant:"outline",size:"sm",icon:"check",disabled:busy,'
    'title:"Figer ce graphe en recette : seules ses sources changeront",'
    "onClick:async function(){if(busy)return;setB(!0);"
    "try{var cap=await __dzCapturer(graph);"
    'var nm=window.prompt("Nom de la recette :",'
    '(graph.name||"Ma recette"));'
    "if(nm==null){setB(!1);return}"
    'var R=await fetch("/api/studio-graphs",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({id:graph.id||void 0,"
    'name:(nm||"Ma recette").trim(),graph:graph,recipe:cap})});'
    'if(!R.ok){dire("Recette refus\\u00e9e : "+await R.text());'
    "setB(!1);return}"
    "var j=await R.json();"
    "setGraph(function(G){return Object.assign({},G,"
    "{id:j.id,name:j.name})});"
    'window.dispatchEvent(new Event("dz-graphs-changed"));'
    'dire("Recette \\u00ab "+j.name+" \\u00bb : "+cap.holes.length+'
    '" source(s) rempla\\u00e7able(s) \\u2014 lan\\u00e7able depuis la '
    'Biblioth\\u00e8que.")}'
    'catch(E){dire("Recette : "+String(E&&E.message||E))}'
    'setB(!1)},children:busy?"Capture\\u2026":"Recette"})}'
    "/*__DZ_STUDIORECETTE_END__*/"
)
_A2 = "function DzOpenGraph({onPick}){"

# ── S3 : le bouton, dans la barre du haut ──────────────────────────────────
_A3 = "r.jsx(DzImportGraph,{onOpen:function(G){i(ts(G));"
_R3 = ("r.jsx(DzRecetteBtn,{graph:o,setGraph:i,dire:p}),"
       "r.jsx(DzImportGraph,{onOpen:function(G){i(ts(G));")

PATCHES = [
    ("S1-capture", _A1, _R1),
    ("S2-bloc", _A2, BLOC + _A2),
    ("S3-bouton", _A3, _R3),
]

POST_COUNTS = [
    ("__dzCapture", 4),
    ("__dzTrous", 2),
    ("__dzRecetteOk", 2),
    ("DzRecetteBtn", 2),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(poser(TAG, MARKER, MARKER_ATTENDU, PATCHES, STABLE_PROBES,
                   POST_COUNTS, SPEC_CHAR_DELTA, SPEC_BYTE_DELTA,
                   "D1 : capture et enregistrement d'une recette"))
```

- [ ] **Step 2 : figer, vérifier, appliquer**

Run : `python scripts/patch_bundle_studiorecette.py --deltas` → recopier.

Run : `python scripts/patch_bundle_studiorecette.py --check`
Attendu : `[studiorecette] 3 ancres OK, marqueur absent, 5 sondes aux comptes`.

Run : `python scripts/patch_bundle_studiorecette.py`
Attendu : `OK - bundle patche (D1 : capture et enregistrement d'une recette).`

Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK`
Attendu : `SYNTAXE_OK`.

- [ ] **Step 3 : le banc**

Ajouter à `backend/tests/test_studio_recette.py`, avant le `if __name__` :

```python
# ── C. la capture et les trous, dans le bundle livre ───────────────────────

def _bloc_recette():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    d = s.index("/*__DZ_STUDIORECETTE__*/") + len("/*__DZ_STUDIORECETTE__*/")
    return s[d:s.index("/*__DZ_STUDIORECETTE_END__*/")]


def _node(js: str) -> str:
    import shutil
    import subprocess
    exe = shutil.which("node")
    assert exe, "node est requis par ce banc (il execute les helpers du bundle)."
    r = subprocess.run([exe, "-e", js], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    return r.stdout.decode("utf-8", "replace").strip()


def test_les_trous_couvrent_les_cinq_formes_de_source():
    js = "var Me={Seedance:{title:'Seedance'},Upload:{title:'UGC video'}," \
         "ExistingRender:{title:'Existing render'}," \
         "HeyGenAvatar:{title:'HeyGen avatar'},Text:{title:'Text'}};" \
         + _bloc_recette() + """
var cap={slot_values:{
  a:{source_kind:"seedance",seedance:{image_filename:"i.png",duration_s:5}},
  b:{source_kind:"upload",upload_filename:"u.png"},
  c:{source_kind:"job",job_id:"j1"},
  d:{source_kind:"heygen",heygen:{script:"salut"}},
  e:{source_kind:"text",text:"titre"}},
  node_slots:{a:"n1",b:"n2",c:"n3",d:"n4",e:"n5"}};
var g={nodes:[{id:"n1",type:"Seedance"},{id:"n2",type:"Upload"},
              {id:"n3",type:"ExistingRender"},{id:"n4",type:"HeyGenAvatar"},
              {id:"n5",type:"Text"}],edges:[]};
var t=__dzTrous(cap,g);
console.log(t.map(function(x){
  return x.key+":"+x.kind+":"+x.path.join("/")}).join(" "));
"""
    assert _node(js) == (
        "a:image:a/seedance/image_filename b:image:b/upload_filename "
        "c:job:c/job_id d:text:d/heygen/script e:text:e/text")


def test_une_branche_sans_template_refuse_la_capture():
    js = _bloc_recette() + """
var seul={nodes:[{id:"s",type:"Seedance",props:{}},
                 {id:"r",type:"Render",props:{}}],edges:[]};
var compose={nodes:[{id:"c",type:"SpatialCompose",props:{}}],edges:[]};
var ugc={nodes:[{id:"u",type:"Upload",props:{jobId:"j"}}],edges:[]};
var ugcVide={nodes:[{id:"u",type:"Upload",props:{}}],edges:[]};
console.log([__dzRecetteOk(seul),__dzRecetteOk(compose),
             __dzRecetteOk(ugc),__dzRecetteOk(ugcVide)].join(","));
"""
    assert _node(js) == "false,true,true,false"


def test_l_ecran_dit_la_recette_et_son_refus():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert s.count("DzRecetteBtn") == 2
    # la capture rend le corps au lieu de l'envoyer
    assert "if(window.__dzCapture){window.__dzCapture=!1;return{ok:!0," in s
    # le refus NOMME les trois branches acceptees et pourquoi
    assert "Spatial compose, Concatenate ou une vidéo UGC" in s
    assert "tire directement chez le fournisseur" in s
    # le succes DIT combien de sources sont remplaçables et d'ou la lancer
    assert "source(s) remplaçable(s)" in s
    assert "lançable depuis la Bibliothèque" in s
    # le drapeau est toujours rabaisse, meme si run() leve
    assert "try{out=await R.run()}finally{window.__dzCapture=!1}" in s
```

- [ ] **Step 4 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_recette.py`

Attendu : `9 passed`.

- [ ] **Step 5 : commit**

```
git add scripts/patch_bundle_studiorecette.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_recette.py
git commit -m 'studio : capturer la compilation et lenregistrer comme recette' -m 'La capture reprend le tour de la preview : un drapeau fait rendre a renderLayoutTemplate le corps quelle allait envoyer. Les trous sont deduits des cinq formes de source de la compilation — image de depart Seedance, televerse, rendu, script davatar, texte — et portent le titre du noeud qui les a produits. Les branches qui ne passent pas par un template sont refusees en NOMMANT les trois qui conviennent, plutot que de payer un rendu pour fabriquer une recette. Le drapeau se rabaisse dans un finally.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 11 : `studioduel` — le duel de moteurs (D2)

**Files:**
- Create: `scripts/patch_bundle_studioduel.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (ligne 231)
- Test: `backend/tests/test_studio_recette.py` (section D)

**Où le duel est possible, mesuré.** Un run de graphe est UN job : Seedance et
HeyGen ne se tirent pas nœud par nœud. Les nœuds image, eux, tirent déjà par
nœud depuis l'inspecteur et rangent leur résultat dans `props.filename`
(`patch_bundle_imagegen.py`). Le duel se pose donc sur `Image gen` — deux
modèles, deux tirs parallèles, coût et durée de chacun, le gagnant devient
l'épingle de P1. Étendre le duel à Seedance demanderait l'option A écartée en
T1 (un job par nœud) : c'est dit, ce n'est pas fait.

**Ce que « coût réel » veut dire ici** : le fournisseur ne renvoie pas de
facture ; le coût est l'estimation de `/api/cost/estimate` avec les tarifs des
Réglages, et la durée est mesurée au client. L'écran l'écrit.

Le panneau est monté **à côté** de `DzImageGenPanel`, jamais dedans : le bloc
de `patch_bundle_imagegen.py` n'est pas touché.

- [ ] **Step 1 : écrire le patcher**

Créer `scripts/patch_bundle_studioduel.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_studioduel.py
"""D2 — duel de moteurs sur le noeud Image gen.

BASELINE : bundle POST-patch studiorecette. Backup dedie : .js.bak_studioduel.
Position : EN QUEUE. Plan : docs/superpowers/plans/2026-09-03-plan-studio.md

Le panneau est MONTE A COTE de DzImageGenPanel, jamais dedans : le bloc de
patch_bundle_imagegen.py reste intact. Le gagnant ecrit props.filename ET
props.pin (P1) ; le perdant tombe dans props.hist (P2).

Run : python scripts/patch_bundle_studioduel.py [--check] [--deltas]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_studio import poser  # noqa: E402

TAG = "studioduel"
MARKER = "__DZ_STUDIODUEL"
MARKER_ATTENDU = 2
SPEC_CHAR_DELTA = None
SPEC_BYTE_DELTA = None

STABLE_PROBES = [
    ("studiopin", "__DZ_STUDIOPIN", 2),
    ("studiohist", "__DZ_STUDIOHIST", 2),
    ("studiorecette", "__DZ_STUDIORECETTE", 2),
    ("imagegen", "DzImageGenPanel", 2),
    ("selecteur-de-modeles", "function DzImgModelSel({value,onChange}){", 1),
]

BLOC = (
    "/*__DZ_STUDIODUEL__*/"
    "function __dzCout(model){return fetch(\"/api/cost/estimate\","
    '{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify({kind:"image",n:1,model:model||"flux"})})'
    ".then(function(R){return R.ok?R.json():null})"
    ".then(function(d){return d&&d.total_usd!=null?d.total_usd:null})"
    ".catch(function(){return null})}"
    "function DzDuelPanel({node,graph,onUpdate}){"
    'if(!node||node.type!=="ImageGen")return null;'
    "var p=node.props||{},d=p.duel||{};"
    "var bs=x.useState(!1),busy=bs[0],setB=bs[1],"
    "rs=x.useState(null),res=rs[0],setR=rs[1],"
    'es=x.useState(""),msg=es[0],setMsg=es[1];'
    "function set(k,v){var o={};o[k]=v;onUpdate({duel:Object.assign({},d,o)})}"
    "async function tirer(){if(busy)return;"
    "var pn=Wt(graph,node.id,\"prompt\"),"
    'txt=((pn&&pn.props&&pn.props.value)||p.prompt||"").trim();'
    'if(!txt){setMsg("\\u00c9cris un prompt, ou branche un n\\u0153ud '
    'Prompt sur l\\u2019entr\\u00e9e.");return}'
    'if(!d.modelB){setMsg("Choisis le second moteur du duel.");return}'
    'setB(!0);setMsg("Duel en cours\\u2026");setR(null);'
    "function tir(m){var t0=(window.performance||Date).now();"
    'return D.generateImage(txt,1,p.size||"portrait_16_9",m||"")'
    ".then(function(o){var f=o&&o.images&&o.images[0];"
    "return{model:m,file:f||null,"
    "ms:Math.round((window.performance||Date).now()-t0),"
    'err:f?null:String((o&&o.error)||"g\\u00e9n\\u00e9ration '
    '\\u00e9chou\\u00e9e")}})'
    ".catch(function(e){return{model:m,file:null,ms:0,"
    "err:String(e&&e.message||e)}})}"
    'var out=await Promise.all([tir(p.model||""),tir(d.modelB),'
    '__dzCout(p.model||""),__dzCout(d.modelB)]);'
    "setB(!1);"
    "var A=out[0],B=out[1];A.usd=out[2];B.usd=out[3];"
    "setR({A:A,B:B});"
    'setMsg(A.file&&B.file?"Compare, puis garde le gagnant."'
    ':"Un c\\u00f4t\\u00e9 a \\u00e9chou\\u00e9 : "'
    '+String(A.err||B.err))}'
    "function garder(x,perdant){if(!x||!x.file)return;"
    "var maj={filename:x.file,"
    "pin:{file:x.file,sig:__dzSig(graph,node.id),"
    "at:new Date().toISOString(),"
    'provider:x.model||"flux",dur:Math.round(x.ms/1000),lock:!0}};'
    "if(perdant&&perdant.file)maj.hist=__dzHistPush(p.hist,"
    "{file:perdant.file,at:new Date().toISOString(),"
    'provider:perdant.model||"flux",'
    "dur:Math.round(perdant.ms/1000)});"
    "maj.hist=__dzHistPush(maj.hist||p.hist,maj.pin);"
    'onUpdate(maj);setMsg("Gagnant \\u00e9pingl\\u00e9 : "+x.file)}'
    "function cote(x,titre,autre){"
    'if(!x)return null;'
    'return r.jsxs("div",{style:{flex:1,minWidth:0},children:['
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",'
    'marginBottom:4},children:titre+" \\u00b7 "+(x.model||"d\\u00e9faut")}),'
    'x.file?r.jsx("img",{src:D.imageUrl(x.file),alt:x.file,'
    'style:{width:"100%",aspectRatio:"9 / 16",objectFit:"cover",'
    'borderRadius:6,border:"1px solid var(--stroke)"}}):'
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--red)"},'
    'children:x.err}),'
    'r.jsx("div",{className:"mono",style:{fontSize:10,'
    'color:"var(--ink-muted)",margin:"4px 0"},'
    'children:(x.usd!=null?"$"+x.usd.toFixed(3):"$?")'
    '+" \\u00b7 "+(x.ms/1000).toFixed(1)+"s"}),'
    'r.jsx(K,{variant:"outline",size:"sm",disabled:!x.file,'
    'style:{width:"100%"},onClick:function(){garder(x,autre)},'
    'children:"Garder "+titre})]})}'
    'return r.jsxs(ie,{label:"Duel de moteurs",children:['
    'r.jsx(O,{label:"Challenger",hint:"Le champion est le g\\u00e9n\\u00e9'
    'rateur choisi plus haut. Le duel tire UNE image de chaque c\\u00f4t\\u00e9 '
    ': tu paies les deux.",children:r.jsx(DzImgModelSel,{value:d.modelB,'
    'onChange:function(v){set("modelB",v)}})}),'
    'r.jsx(K,{variant:"primary",size:"sm",icon:"sparkle",disabled:busy,'
    'style:{width:"100%"},onClick:tirer,'
    'children:busy?"Duel\\u2026":"Tirer le duel"}),'
    'msg?r.jsx("div",{style:{fontSize:10.5,marginTop:6,'
    'color:"var(--ink-soft)"},children:msg}):null,'
    'res?r.jsxs("div",{style:{display:"flex",gap:8,marginTop:8},'
    'children:[cote(res.A,"A",res.B),cote(res.B,"B",res.A)]}):null,'
    'r.jsx("div",{style:{fontSize:10,color:"var(--ink-muted)",'
    'marginTop:6},children:"Co\\u00fbt estim\\u00e9 d\\u2019apr\\u00e8s tes '
    "tarifs des R\\u00e9glages \\u2014 le fournisseur ne renvoie pas de "
    'facture. Dur\\u00e9e mesur\\u00e9e ici."})]})}'
    "/*__DZ_STUDIODUEL_END__*/"
)
_A1 = "function DzPinPanel({node,graph,onUpdate}){"

_A2 = "r.jsx(DzHistPanel,{node:e,graph:t,onUpdate:o}),"
_R2 = ("r.jsx(DzDuelPanel,{node:e,graph:t,onUpdate:o}),"
       "r.jsx(DzHistPanel,{node:e,graph:t,onUpdate:o}),")

PATCHES = [
    ("S1-bloc", _A1, BLOC + _A1),
    ("S2-montage-panneau", _A2, _R2),
]

POST_COUNTS = [
    ("DzDuelPanel", 2),
    ("__dzCout", 3),
    ("DzImageGenPanel", 2),
    ("DzImgModelSel", 5),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(poser(TAG, MARKER, MARKER_ATTENDU, PATCHES, STABLE_PROBES,
                   POST_COUNTS, SPEC_CHAR_DELTA, SPEC_BYTE_DELTA,
                   "D2 : duel de moteurs sur Image gen"))
```

- [ ] **Step 2 : figer, vérifier, appliquer**

Run : `python scripts/patch_bundle_studioduel.py --deltas` → recopier.

Run : `python scripts/patch_bundle_studioduel.py --check`
Attendu : `[studioduel] 2 ancres OK, marqueur absent, 5 sondes aux comptes`.

Run : `python scripts/patch_bundle_studioduel.py`
Attendu : `OK - bundle patche (D2 : duel de moteurs sur Image gen).`

Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK`
Attendu : `SYNTAXE_OK`.

- [ ] **Step 3 : le banc**

Ajouter à `backend/tests/test_studio_recette.py`, avant le `if __name__` :

```python
# ── D. le duel ─────────────────────────────────────────────────────────────

def test_le_duel_dit_le_cout_la_duree_et_dou_vient_le_chiffre():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert s.count("DzDuelPanel") == 2
    # deux tirs EN PARALLELE, plus les deux estimations
    assert ('var out=await Promise.all([tir(p.model||""),tir(d.modelB),'
            '__dzCout(p.model||""),__dzCout(d.modelB)]);') in s
    # la duree est mesuree ici, le cout vient des tarifs : l'ecran le DIT
    assert "le fournisseur ne renvoie pas de facture" in s
    assert "Durée mesurée ici." in s
    # et il previent qu'un duel se paie deux fois
    assert "tu paies les deux" in s
    # le gagnant devient l'epingle TENUE (P1) et entre dans la pile (P2)
    assert "pin:{file:x.file,sig:__dzSig(graph,node.id)," in s
    assert "maj.hist=__dzHistPush(maj.hist||p.hist,maj.pin);" in s
    # le bloc imagegen n'a pas ete touche
    assert s.count("DzImageGenPanel") == 2
    assert "function DzImageGenPanel({node,p,set,graph,spawn}){" in s


def test_le_duel_ne_sort_que_sur_le_noeud_image_gen():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert 'if(!node||node.type!=="ImageGen")return null;' in s
    # et le plan dit pourquoi Seedance en est exclu
    plan = (RACINE / "docs" / "superpowers" / "plans"
            / "2026-09-03-plan-studio.md").read_text(encoding="utf-8")
    assert "un job par nœud" in plan and "Image gen" in plan
```

- [ ] **Step 4 : lancer le banc**

Run (depuis `backend/`) : `python tests/test_studio_recette.py`

Attendu : `11 passed`.

- [ ] **Step 5 : commit**

```
git add scripts/patch_bundle_studioduel.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_recette.py
git commit -m 'studio : le duel de moteurs sur le noeud Image gen' -m 'Un run de graphe est UN job : Seedance et HeyGen ne se tirent pas noeud par noeud. Les noeuds image, si — ils le font depuis un mois. Le duel se pose donc la : deux modeles, deux tirs paralleles, cout estime dapres les tarifs des Reglages et duree mesuree au client, tous deux ECRITS avec la mention que le fournisseur ne facture pas en retour. Le gagnant devient lepingle tenue et entre dans la pile, le perdant aussi. Le panneau est monte A COTE de celui dimagegen, jamais dedans.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Task 12 : `studiosend` — départ depuis un rendu, et lancer une recette (D3)

**Files:**
- Create: `scripts/patch_bundle_studiosend.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (ligne 285)
- Test: `backend/tests/test_studio_recette.py` (section E)

Deux entrées dans le menu « Envoyer vers… » de la Bibliothèque :

- branche **rendu** → « Studio — nouveau graphe » : pose un nœud Rendu
  existant dans un graphe NEUF. Distinct de « Rouvrir dans Studio », qui
  recharge le graphe source. Le mécanisme existe déjà (`window.__dzRender`,
  consommé par l'initialiseur de l'écran) : l'entrée manquait ;
- branche **image** → « Lancer une recette… » : liste les recettes, puis les
  trous image de celle choisie, puis `POST /studio-graphs/{id}/run`. C'est
  D1 vu depuis un autre écran.

- [ ] **Step 1 : écrire le patcher**

Créer `scripts/patch_bundle_studiosend.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_studiosend.py
"""D3 + D1 (declenchement) — deux entrees dans le menu Envoyer vers.

BASELINE : bundle POST-patch studioduel. Backup dedie : .js.bak_studiosend.
Position : EN QUEUE. Plan : docs/superpowers/plans/2026-09-03-plan-studio.md

Edition IN-BLOC du menu pose par patch_bundle_libsend.py : ce dernier ne doit
plus etre relance seul apres cette tache. Les helpers reutilises (__dzSendMenu,
__dzSendNav, __dzToast) sont les siens.

Run : python scripts/patch_bundle_studiosend.py [--check] [--deltas]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _patch_studio import poser  # noqa: E402

TAG = "studiosend"
MARKER = "__DZ_STUDIOSEND"
MARKER_ATTENDU = 2
SPEC_CHAR_DELTA = None
SPEC_BYTE_DELTA = None

STABLE_PROBES = [
    ("libsend", "__dzSendTo", 2),
    ("libsend-menu", "function __dzSendMenu(items,titre){", 1),
    ("studiopin", "__DZ_STUDIOPIN", 2),
    ("studiorecette", "__DZ_STUDIORECETTE", 2),
    ("studioduel", "__DZ_STUDIODUEL", 2),
]

BLOC = (
    "/*__DZ_STUDIOSEND__*/"
    # D3 : un graphe NEUF a partir d'un rendu (pas son graphe source)
    "function __dzStudioNeuf(jobId){try{window.__dzRenderGraph=null;"
    "window.__dzRender=jobId}catch(e){}"
    '__dzSendNav("studio")}'
    # D1 vu d'ailleurs : choisir une recette, puis le trou a remplir
    "function __dzLancerRecette(nomImage){"
    'fetch("/api/studio-graphs").then(function(R){return R.json()})'
    ".then(function(d){"
    "var rs=((d&&d.graphs)||[]).filter(function(g){return g.recipe});"
    'if(!rs.length){__dzToast("Aucune recette enregistr\\u00e9e. Ouvre un '
    "graphe dans le Studio et clique Recette.\");return}"
    "__dzSendMenu(rs.map(function(g){return{lbl:g.name,fn:function(){"
    'fetch("/api/studio-graphs/"+encodeURIComponent(g.id)+"/recipe")'
    ".then(function(R){return R.ok?R.json():null}).then(function(rc){"
    "var trous=((rc&&rc.holes)||[]).filter(function(t){"
    'return t.kind==="image"});'
    'if(!trous.length){__dzToast("La recette \\u00ab "+g.name+" \\u00bb '
    "n\\u2019a aucune source image \\u00e0 remplacer.\");return}"
    "__dzSendMenu(trous.map(function(t){return{lbl:t.label,fn:function(){"
    "var f={};f[t.key]=nomImage;"
    'fetch("/api/studio-graphs/"+encodeURIComponent(g.id)+"/run",'
    '{method:"POST",headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({fill:f})})"
    ".then(function(R){return R.json().then(function(j){"
    "return{ok:R.ok,j:j}})})"
    ".then(function(o){__dzToast(o.ok?"
    '"Recette \\u00ab "+g.name+" \\u00bb lanc\\u00e9e \\u2014 suis-la dans '
    'la file de rendus.":'
    '"Recette refus\\u00e9e : "+String(o.j&&o.j.detail||""))})'
    '.catch(function(e){__dzToast("Recette : "+String(e&&e.message||e))})}}}),'
    '"Quelle source remplacer par \\u00ab "+nomImage+" \\u00bb ?")})'
    '.catch(function(){__dzToast("Recette illisible.")})}}}),'
    '"Lancer quelle recette ?")})'
    '.catch(function(){__dzToast("Liste des recettes indisponible.")})}'
    "/*__DZ_STUDIOSEND_END__*/"
)
_A1 = "function __dzSendTo(m,onClose){"

# ── S2 : branche rendu — D3 ────────────────────────────────────────────────
_A2 = 'if(m.kind==="render"&&m.jobId){items.push('
_R2 = ('if(m.kind==="render"&&m.jobId){items.push({'
       'lbl:"\\ud83c\\udfac Studio \\u2014 nouveau graphe",'
       "fn:function(){onClose&&onClose();__dzStudioNeuf(m.jobId)}});"
       "items.push(")

# ── S3 : branche image — D1 declenche d'ailleurs ───────────────────────────
_A3 = ('items.push({lbl:"\\u26a1 Quick \\u2014 image de d\\u00e9part",'
       "fn:function(){onClose&&onClose();window.__dzQuickStart=nom;"
       '__dzSendNav("quick")}});')
_R3 = ('items.push({lbl:"\\u26a1 Quick \\u2014 image de d\\u00e9part",'
       "fn:function(){onClose&&onClose();window.__dzQuickStart=nom;"
       '__dzSendNav("quick")}});'
       'items.push({lbl:"\\ud83d\\udcdc Lancer une recette\\u2026",'
       "fn:function(){onClose&&onClose();__dzLancerRecette(nom)}});")

PATCHES = [
    ("S1-bloc", _A1, BLOC + _A1),
    ("S2-rendu-vers-studio", _A2, _R2),
    ("S3-image-vers-recette", _A3, _R3),
]

POST_COUNTS = [
    ("__dzStudioNeuf", 2),
    ("__dzLancerRecette", 2),
    ("__dzSendTo", 2),
    ("__dzSendMenu", 5),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    sys.exit(poser(TAG, MARKER, MARKER_ATTENDU, PATCHES, STABLE_PROBES,
                   POST_COUNTS, SPEC_CHAR_DELTA, SPEC_BYTE_DELTA,
                   "D3 : rendu vers un graphe neuf + lancement de recette"))
```

Les ancres S2 et S3 sont écrites en séquences `\uXXXX` parce qu'elles
contiennent des emoji et des accents ; c'est la même chaîne que dans le
bundle, mais le fichier reste ASCII et le `--check` ne peut pas mourir sur un
encodage de console.

- [ ] **Step 2 : figer, vérifier, appliquer**

Run : `python scripts/patch_bundle_studiosend.py --deltas` → recopier.

Run : `python scripts/patch_bundle_studiosend.py --check`
Attendu : `[studiosend] 3 ancres OK, marqueur absent, 5 sondes aux comptes`.
Si S2 ou S3 dit `anchor count=0`, l'emoji ou l'espace insécable de l'entrée
voisine a changé : relire la chaîne exacte dans le bundle avant de corriger.

Run : `python scripts/patch_bundle_studiosend.py`
Attendu : `OK - bundle patche (D3 : rendu vers un graphe neuf + lancement de recette).`

Run : `cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK`
Attendu : `SYNTAXE_OK`.

- [ ] **Step 3 : le banc**

Ajouter à `backend/tests/test_studio_recette.py`, avant le `if __name__` :

```python
# ── E. les deux entrees du menu Envoyer vers ───────────────────────────────

def test_un_rendu_ouvre_un_graphe_NEUF_distinct_de_rouvrir():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert s.count("__dzStudioNeuf") == 2
    assert "🎬 Studio — nouveau graphe" in s
    # il EFFACE le graphe source avant de poser le rendu : sans quoi
    # l'initialiseur de l'ecran rechargerait l'ancien graphe.
    assert ("function __dzStudioNeuf(jobId){try{window.__dzRenderGraph=null;"
            "window.__dzRender=jobId}") in s
    # et « Rouvrir dans Studio » existe toujours, inchange
    assert "function __dzReopenStudio(id){" in s


def test_une_image_peut_lancer_une_recette_depuis_la_bibliotheque():
    s = BUNDLE.read_text(encoding="utf-8", newline="")
    assert s.count("__dzLancerRecette") == 2
    assert "📜 Lancer une recette…" in s
    # deux menus enchaines : la recette, puis LA SOURCE a remplacer
    assert "Lancer quelle recette ?" in s
    assert "Quelle source remplacer par « " in s
    # les vides sont EXPLIQUES, pas muets
    assert "Aucune recette enregistrée. Ouvre un graphe dans le Studio" in s
    assert "n’a aucune source image à remplacer." in s
    # le refus du serveur est repris TEL QUEL
    assert 'Recette refusée : "+String(o.j&&o.j.detail||"")' in s


def test_le_patcher_dit_leffet_sur_libsend():
    p = (RACINE / "scripts"
         / "patch_bundle_studiosend.py").read_text(encoding="utf-8")
    assert "Edition IN-BLOC du menu pose par patch_bundle_libsend.py" in p
    assert "ne doit plus etre relance seul" in p
```

- [ ] **Step 4 : lancer tous les bancs du chantier**

Run (depuis `backend/`), un par un :

```
python tests/test_studio_pin.py
python tests/test_studio_lecture.py
python tests/test_studio_graph_io.py
python tests/test_studio_recette.py
```

Attendu : `15 passed`, `5 passed`, `12 passed`, `14 passed`.

- [ ] **Step 5 : commit**

```
git add scripts/patch_bundle_studiosend.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_studio_recette.py
git commit -m 'studio : depart depuis un rendu, et lancer une recette depuis la Bibliotheque' -m 'Envoyer un rendu vers le Studio posait deja son graphe source ; il manquait le depart NEUF — un noeud Rendu existant dans un graphe vide, ce que le mecanisme __dzRender savait faire sans que rien ne lappelle. Il fallait effacer le graphe source avant, sinon linitialiseur rechargeait lancien. Une image de la Bibliotheque peut aussi lancer une recette : deux menus enchaines, la recette puis la source a remplacer, et le refus du serveur repris tel quel. Edition in-bloc du menu de libsend, dite dans len-tete du patcher.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

Les quatre bacs écartés de `R2`, une ligne chacun. Aucune tâche, aucune ligne
de code : ils sont ici pour qu'on ne les reprenne pas par distraction.

- **E1 — Sous-graphes et groupes** : les graphes font moins de 10 nœuds et
  aucun motif ne s'y répète (réponse 1) ; un mécanisme d'encapsulation coûterait
  plus que ce qu'il rangerait.
- **E2 — Canevas infini façon Flora / Weavy** : préférence explicite pour le
  graphe strict plus un panneau de comparaison (réponse 3) ; les deux
  références sont de mémoire, non vérifiées, donc sans valeur d'argument.
- **E3 — Nœuds de contrôle (boucle, condition, variables)** : Variations et le
  lot Quick couvrent le besoin (réponse 4) ; un langage de contrôle dans un
  graphe de 10 nœuds est un piège à complexité.
- **E4 — Comparaison à N > 2 moteurs** : le duel suffit (réponse 7) ; les
  variations d'un même moteur restent l'affaire du lot Quick.

---

## Campagne de mutations

### Task 13 : `mutations_studio.py` — casser, voir rouge, remettre

**Files:**
- Create: `backend/tests/mutations_studio.py`

Ce n'est pas un test : `pytest` ne le collecte pas (son nom ne commence pas
par `test_`) et `run-tests.ps1` ne le liste pas. Il se lance à la main et
mesure la valeur des quatre bancs du chantier : chaque mutation nomme le test
qui doit rougir, et une mutation **VERTE** est une assertion qui manque.

Le patron est celui de `backend/tests/mutations_plaque_slicer.py`, avec une
différence : chaque mutation porte **son** banc, parce que le chantier en a
quatre. Le bundle est muté comme n'importe quel fichier — c'est un fichier
texte, et la remise se fait à l'octet près sous assertion `sha256`.

- [ ] **Step 1 : écrire la campagne**

Créer `backend/tests/mutations_studio.py` :

```python
# -*- coding: utf-8 -*-
"""Banc de mutations du chantier Studio : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas, run-tests.ps1 ne le liste pas. Il se
lance A LA MAIN, depuis backend/ :

    python tests/mutations_studio.py           # toutes
    python tests/mutations_studio.py 3 17      # celles-la

Il MUTE les sources du depot une a une et les REMET a l'octet pres (assertion
sha256), donc il ne se lance pas pendant qu'un autre banc lit ces fichiers.
Chaque mutation : (fichier, ancien, nouveau, tests attendus rouges, banc).
Une mutation VERTE est une assertion qui manque — c'est l'argument de la revue.

Le bundle minifie est mute comme les autres : une seule ligne, mais un fichier
texte. Ses mutations visent les blocs injectes par les patchers du chantier.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
BUNDLE = "frontend/dist/assets/index-BEOJX8L5.js"
PIPE = "backend/app/services/pipeline.py"
ROUTES = "backend/app/api/routes.py"
SGRAPH = "backend/app/services/studio_graph.py"
SREC = "backend/app/services/studio_recette.py"

PIN = "tests/test_studio_pin.py"
LEC = "tests/test_studio_lecture.py"
IO = "tests/test_studio_graph_io.py"
REC = "tests/test_studio_recette.py"

M = [
    # ── P1 : le manifeste des parties ───────────────────────────────────────
    (PIPE,
     'for slot in sorted(set(generated) | set(static)):',
     'for slot in sorted(set(generated)):',
     ["manifeste_relie_le_slot"], PIN),
    (PIPE,
     '"node_id": ns.get(slot) or None,',
     '"node_id": slot,',
     ["manifeste_relie_le_slot"], PIN),
    (PIPE,
     '"kind": "generated" if j is not None else "static",',
     '"kind": "generated",',
     ["manifeste_relie_le_slot"], PIN),
    (PIPE,
     '    ns = node_slots or {}',
     '    ns = node_slots',
     ["manifeste_survit_a_une_carte_absente"], PIN),
    (PIPE,
     '        (d / f"{Path(job_id).name}.json").write_text(',
     '        (d / f"{job_id}.json").write_text(',
     ["la_route_des_parties"], PIN),
    (ROUTES,
     '    p = settings.outputs_path / "_parts" / f"{safe}.json"',
     '    p = settings.outputs_path / "_graphs" / f"{safe}.json"',
     ["la_route_des_parties"], PIN),
    (ROUTES,
     '                node_slots=request.node_slots,\n',
     '',
     ["requete_de_rendu_porte_la_carte"], PIN),

    # ── P1 : les substitutions dans le bundle ───────────────────────────────
    (BUNDLE,
     "var __pv=__dzPV(e,g);if(__pv)return __pv;",
     "var __pv=null;if(__pv)return __pv;",
     ["cinq_points_de_substitution"], PIN),
    (BUNDLE,
     'if(!(p.lock||p.sig===__dzSig(g,n.id)))return null;',
     'if(!(p.lock||p.sig!==__dzSig(g,n.id)))return null;',
     ["epingle_est_ignoree_quand_les_entrees"], PIN),
    (BUNDLE,
     'if(k==="pin"||k==="hist"||k==="duel")continue;',
     'if(k==="hist"||k==="duel")continue;',
     ["epingle_ne_compte_pas_dans_sa_propre_empreinte"], PIN),
    (BUNDLE,
     'var ins=((g&&g.edges)||[]).filter(function(e){return e.to===nid})',
     'var ins=[].filter(function(e){return e.to===nid})',
     ["empreinte_bouge_avec_un_reglage"], PIN),
    (BUNDLE,
     "if(e.to===cur&&!vus[e.from])fr.push(e.from)})}ord.sort();",
     "if(e.to===cur&&!vus[e.from])fr.push(e.from)})}",
     ["empreinte_bouge_avec_un_reglage"], PIN),
    (BUNDLE,
     "if(n.props&&n.props.pin&&n.props.pin.lock)pin.lock=!0;",
     "",
     ["recolte_ne_defait_pas_une_epingle_tenue"], PIN),
    (BUNDLE,
     "if(__dzEstGen(n)&&__dzPV(graph,n))return;",
     "",
     ["ecran_dit_l_etat_de_l_epingle"], PIN),

    # ── P2 : la pile ────────────────────────────────────────────────────────
    (BUNDLE,
     "return l.slice(0,8)}",
     "return l}",
     ["pile_empile_en_tete_sans_doublon"], LEC),
    (BUNDLE,
     'var l=(h||[]).filter(function(x){'
     'return x&&(x.jobId||x.file)!==(e.jobId||e.file)});',
     'var l=(h||[]).slice();',
     ["pile_empile_en_tete_sans_doublon"], LEC),
    (BUNDLE,
     "hist:__dzHistPush((n.props||{}).hist,pin)",
     "hist:(n.props||{}).hist",
     ["ecran_dit_la_pile_et_le_choix"], LEC),

    # ── P3 : la validation d'import ─────────────────────────────────────────
    (SGRAPH,
     '        if nid in vus:',
     '        if False:',
     ["identifiants_en_double"], IO),
    (SGRAPH,
     '        if typ not in reg:',
     '        if typ not in reg and False:',
     ["type_inconnu_est_refuse"], IO),
    (SGRAPH,
     '    if len(ordre) != len(propres):',
     '    if False:',
     ["cycle_est_refuse"], IO),
    (SGRAPH,
     '    if len(rendus) > 1:',
     '    if len(rendus) > 2:',
     ["deux_noeuds_render"], IO),
    (SGRAPH,
     '        if pb not in reg[tb]["in"]:',
     '        if pb not in reg[tb]["in"] and False:',
     ["arete_sur_un_port_inexistant"], IO),
    (SGRAPH,
     '            if dispo is not None and v not in dispo:',
     '            if dispo and v not in dispo:',
     ["sources_manquantes_remontent"], IO),

    # ── D1 : la recette ─────────────────────────────────────────────────────
    (SREC,
     '    sv = copy.deepcopy(recette["slot_values"])',
     '    sv = dict(recette["slot_values"])',
     ["remplir_ne_modifie_pas_la_recette"], REC),
    (SREC,
     '        if t is None:',
     '        if False:',
     ["cle_inconnue_est_refusee"], REC),
    (SREC,
     '    if "/" in v or "\\\\" in v or v.startswith("."):',
     '    if "/" in v:',
     ["nom_de_fichier_traversant"], REC),
    (SREC,
     '    if not isinstance(h, list) or not isinstance(sv, dict):',
     '    if not isinstance(h, list):',
     ["recette_sans_trous_ou_sans_compilation"], REC),
    (ROUTES,
     '        if trou.get("kind") == "image" and \\\n'
     '                not (settings.images_path / val).is_file():',
     '        if False:',
     ["enregistrer_puis_lancer_une_recette"], REC),

    # ── D1/D2/D3 : le bundle ────────────────────────────────────────────────
    (BUNDLE,
     "try{out=await R.run()}finally{window.__dzCapture=!1}",
     "out=await R.run();window.__dzCapture=!1;",
     ["ecran_dit_la_recette_et_son_refus"], REC),
    (BUNDLE,
     'n.some(function(z){return z.type==="Upload"&&z.props&&z.props.jobId})}',
     'n.some(function(z){return z.type==="Upload"})}',
     ["branche_sans_template_refuse_la_capture"], REC),
    (BUNDLE,
     't.push({key:k,path:[k,"seedance","image_filename"],kind:"image",',
     't.push({key:k,path:[k,"image_filename"],kind:"image",',
     ["trous_couvrent_les_cinq_formes"], REC),
    (BUNDLE,
     "function __dzStudioNeuf(jobId){try{window.__dzRenderGraph=null;",
     "function __dzStudioNeuf(jobId){try{",
     ["rendu_ouvre_un_graphe_NEUF"], REC),
    (BUNDLE,
     "maj.hist=__dzHistPush(maj.hist||p.hist,maj.pin);",
     "",
     ["duel_dit_le_cout_la_duree"], REC),
    (BUNDLE,
     'var trous=((rc&&rc.holes)||[]).filter(function(t){'
     'return t.kind==="image"});',
     "var trous=((rc&&rc.holes)||[]);",
     ["image_peut_lancer_une_recette"], REC),
]


def rouges(banc, k):
    """Les tests rouges du banc cible — et si RIEN n'a tourne, on le dit.

    pytest sort 0 (tout vert) ou 1 (des rouges) quand il a tourne ; 2 a 5
    quand la COLLECTE a casse (une erreur de syntaxe, un import qui leve) ou
    qu'aucun test ne correspond. Lue comme aucun FAILED, une collecte cassee
    passerait pour une mutation VERTE alors que rien n'a ete mesure.
    """
    r = subprocess.run([PY, "-m", "pytest", banc, "-q", "--no-header",
                        "-p", "no:warnings", "-k", k],
                       capture_output=True, cwd=R / "backend", timeout=900)
    txt = r.stdout.decode("utf-8", "replace")
    erreur = (r.returncode not in (0, 1)
              or bool(re.search(r"^ERROR ", txt, re.M)))
    return set(re.findall(r"^FAILED [^:]+::(\w+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, attendus, banc) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF
        # et l'on reecrit avec la fin de ligne du fichier ; la remise se fait
        # a l'octet pres depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:60])
        txt = txt.replace(old, new)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc, " or ".join(attendus))
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1200:], file=sys.stderr)
        else:
            verdict = "ROUGE" if not manquants else \
                ("VERTE" if not rg else "ROUGE(autres)")
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        apercu = old.strip()[:46]
        print(f"[{i:2d}] {verdict:16s} {rel.split('/')[-1]:24s} "
              f"{apercu!r} -> {sorted(rg)}  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    main()
```

- [ ] **Step 2 : lancer la campagne**

Run (depuis `backend/`) : `python tests/mutations_studio.py`

Attendu : 34 lignes, toutes en `ROUGE`, chacune nommant le test qu'elle a fait
rougir, avec deux empreintes `sha` identiques en fin de ligne. Par exemple :

```
[ 0] ROUGE            pipeline.py              'for slot in sorted(set(generated) | set(sta' -> ['test_le_manifeste_relie_le_slot_au_noeud_et_au_sous_rendu']  sha 3f2a1b8c04=3f2a1b8c04
```

Puis une dernière ligne JSON avec le bilan.

- [ ] **Step 3 : traiter les VERTES**

Toute ligne `VERTE` est une assertion manquante : la mutation casse le
comportement et aucun banc ne s'en aperçoit. Pour chacune, **ajouter
l'assertion** au banc nommé dans la cinquième colonne de `M`, relancer cette
mutation seule (`python tests/mutations_studio.py <n>`), et vérifier qu'elle
passe au `ROUGE`. Ne jamais retirer la mutation pour faire disparaître la
ligne verte.

Une ligne `ERREUR(collecte)` n'est pas un verdict : elle dit que le banc n'a
pas tourné (erreur de syntaxe introduite, import cassé). Lire les 1200
derniers caractères imprimés sur `stderr` et corriger la mutation.

- [ ] **Step 4 : vérifier que rien n'a bougé sur le disque**

Run (depuis la racine) : `git status --porcelain`

Attendu : seule la ligne du fichier neuf `backend/tests/mutations_studio.py`
(et rien sur `pipeline.py`, `routes.py`, `studio_graph.py`,
`studio_recette.py`, ni le bundle). La campagne remet chaque fichier à
l'octet près ; une divergence ici veut dire qu'elle a été interrompue au
milieu — restaurer avec `git checkout -- <fichier>`.

- [ ] **Step 5 : commit**

```
git add backend/tests/mutations_studio.py
git commit -m 'studio : la campagne de mutations des quatre bancs' -m 'Trente-quatre mutations qui cassent une regle a la fois — le manifeste des parties, les cinq substitutions du bundle, la pile, la validation dimport, les trous de recette, le duel et les deux entrees du menu — et nomment chacune le test qui doit rougir. Chaque mutation porte SON banc, le chantier en ayant quatre, et le fichier mute est remis a loctet pres sous assertion sha256. Une ligne VERTE est une assertion qui manque, pas une mutation a supprimer ; une ERREUR de collecte nest pas un verdict.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Ordre d'exécution et remise en état

Les 13 tâches se suivent : T1 mesure et tranche, T2 pose la dette commune,
T3–T4 le socle de P1, T5–T8 le reste du lot 1, T9–T12 le lot 2, T13 mesure la
valeur des bancs. Les sept patchers doivent être appliqués **dans l'ordre des
tags** — `studiopin`, `studiohist`, `studioimp`, `studioscrub`,
`studiorecette`, `studioduel`, `studiosend` — parce que chacun prend le
précédent pour base et que sa garde de chaîne refuse de tourner autrement.

Si un patcher doit être repris après coup, **ne pas le relancer seul** :

```
python scripts/repatch_all.py --list
python scripts/repatch_all.py --from <tag>
```

puis revalider la syntaxe et relancer les quatre bancs :

```
cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzcheck.mjs && node --check /tmp/dzcheck.mjs && echo SYNTAXE_OK
```

```
python tests/test_studio_pin.py
python tests/test_studio_lecture.py
python tests/test_studio_graph_io.py
python tests/test_studio_recette.py
```

Attendu : `SYNTAXE_OK`, puis `15 passed`, `5 passed`, `12 passed`,
`14 passed`.
