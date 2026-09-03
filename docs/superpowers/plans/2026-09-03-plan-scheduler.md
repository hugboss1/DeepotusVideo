# Scheduler — programmation et publication : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> Source : `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`,
> sections `### 6. Scheduler`, `### R6. Scheduler — réponses`, `### R12` (pour la
> part backend de D1) et `## Pièges hérités`. Les bacs de R6 sont le périmètre
> EXACT. Ce plan n'implémente rien du compagnon mobile : il expose ce que le
> backend doit fournir au plan mobile, rien de plus.

**Goal :** le Scheduler publie seul sur cinq réseaux (X, Telegram, Instagram
Reels, YouTube Shorts, TikTok), mesure ce qui est parti, propose ses créneaux
et ses recyclages, et se valide par lot d'une semaine — le tout backend d'abord,
un seul patcher bundle en queue de chaîne.

**Architecture :** un registre d'adaptateurs (`publishers.py`) avec quotas
vérifiés (`quota.py`) remplace les deux `if` de `fire_post` ; trois adaptateurs
HTTP directs (httpx, déjà dans les requirements) ; une table `post_metrics`
alimentée par la passe quotidienne de `schedule_loop` et agrégée pour un
tableau de bord ; créneaux par canal dans un JSON sous `DATA_ROOT` ; aperçus
verticaux à zones sûres dessinés par Pillow comme la carte X ; validation par
lot = `validated_at` + `mode=auto` ; brief, séries et fils = trois tables et un
`thread_of`. L'écran reste celui du bundle : UN patcher `scheduler`, panneaux en
DOM pur (patron `__dzSendMenu` de libsend).

**Tech Stack :** Python 3.13 embarqué (stdlib + Pillow), FastAPI, SQLAlchemy
async + aiosqlite, httpx (présent), tweepy (présent). Aucune dépendance
nouvelle : `google-api-python-client` est écarté — l'envoi résumable YouTube
tient en deux appels HTTP (mesuré à la Tâche 3).

---

## Périmètre

**Lot 1 — parité (R6, dans l'ordre)** : P1 trois adaptateurs automatiques
(après la tâche de décision contre Postiz) ; P2 tableau de bord d'analytics ;
P3 créneaux par canal + horaire proposé ; P4 aperçus Reels / Shorts / TikTok à
zones sûres ; P5 validation par lot.

**Lot 2 — différenciant** : D1 réduit à sa part backend (lot validé exportable
avec vidéos, légendes, heures ; retour d'état) ; D2 brief de campagne persistant
+ séries récurrentes + fils X ; D3 recyclage proposé.

**Exclus** : E1 validation en équipe, E2 analytics concurrents, E3 TikTok
public sans audit (impossible par l'API — mesuré R6), et tout ce que R12 porte :
appairage, jeton d'appareil, LAN, publication depuis le téléphone, rappels
mobiles.

### Ce que le code fait aujourd'hui (relu le 03/09/2026, lignes réelles)

- `backend/app/services/marketing.py` (896 l.) : `generate_plan` l.230,
  `materialize_plan` l.255, `_x_client` l.535, `_publish_x_sync` l.554 (tweepy,
  vidéo chunkée), `publish_x` l.579, `_fetch_x_metrics_sync` l.600,
  `refresh_x_metrics` l.616 (10 posts, budget de lecture), `performance_context`
  l.643, `publish_telegram` l.682, `auto_channels` l.760 (telegram, x),
  `fire_post` l.770 (claim `posting`, deux `if` par canal, l.812-826),
  `schedule_loop` l.849 (tick 60 s, passe X quotidienne l.859-866).
- `backend/app/services/post_preview.py` (279 l.) : `_render_x` l.168,
  `_render_telegram` l.221, `render_preview` l.270 — tout autre canal tombe sur
  la carte X.
- `backend/app/api/routes.py` : `/health` l.3459 (`telegram_enabled`,
  `x_enabled`), `_ALLOWED_ENV_KEYS` l.3501 (contient déjà `YOUTUBE_*` et `IG_*`
  — clés stockables, jamais lues), `_require_localhost` l.3547, `/settings/keys`
  l.3555-3612, `_post_to_dict` l.3924, `GET/POST /schedule` l.3955/3974,
  `PATCH` l.4009, `DELETE` l.4050, `fire` l.4063, `preview.png` l.4101,
  `/marketing/plan` l.4273, `/channels/test` l.4361.
- `backend/app/services/storage.py` : `ScheduledPost` l.82-120 (`x_post_id`,
  `metrics`, `brief`), `SCHEDULED_POSTS_COLUMNS` l.385 (auto-ALTER),
  `_auto_migrate` l.447.
- `backend/app/config.py` : `TELEGRAM_*` l.146, `X_*` l.158, `has_x` l.225.
  **Aucune** clé YouTube/Instagram/TikTok dans `Settings`.
- `backend/app/services/plan_schema.py` : `_CHANNELS` l.38 (x, telegram,
  youtube, instagram), `BRIEF_FIELDS` l.23.
- `backend/app/personas/deepotus.json` : `default_hashtags_pool` contient
  `#1000x` — un terme que le brief (D2) doit pouvoir interdire.
- Skill `deepotus-comms` : **hors dépôt** (`~/.claude/skills/deepotus-comms`,
  seul le brief de balayage le nomme). Il crée des brouillons par
  `POST /schedule` et lit `references/account-config.md` pour ses créneaux ; D2
  lui expose un `GET /marketing/brief` — sa mise à jour est hors plan.
- Bundle `frontend/dist/assets/index-BEOJX8L5.js` : table des canaux `_t`
  (x, telegram, youtube, instagram — 1 occurrence), Settings « Connected
  accounts » avec YouTube/Instagram en `auto:!1,testable:!1`, l'aperçu itère
  `e.channels` sur `preview.png?channel=` (P4 est donc backend pur), bouton
  `Duplicate to next day` (`onClick:P,` unique), en-tête `" planned"` unique.

## Décisions tranchées avant le code

1. **Adaptateurs directs, pas Postiz** — argumenté et re-mesuré à la Tâche 0.
2. **httpx direct** pour Google, Meta, TikTok : `httpx>=0.27.2` est dans
   `backend/requirements.txt` l.11 ; la seule chose que
   `google-api-python-client` apporterait (découverte + résumable) tient en
   deux requêtes. Zéro ligne dans les requirements.
3. **Registre d'adaptateurs** : un canal = `(disponible(), publier())`,
   quota vérifié AVANT l'appel réseau, compté APRÈS succès ; `fire_post`
   itère le registre ; `remote_ids` JSON par canal (le `x_post_id` reste
   synchronisé pour `performance_context`).
4. **Bancs-miroirs** : chaque adaptateur est testé par un faux client HTTP
   (`backend/tests/fakehttp.py`) qui enregistre méthode, URL, en-têtes et corps
   LU ; on lit la base (PRAGMA, lignes) et les fichiers écrits, jamais le code.
5. **UI en DOM pur** dans un seul patcher `scheduler` : les panneaux
   (Comptes, Valider, Créneaux, Analytics, Brief, Séries, Recycler) sont des
   fonctions `__dzSched*` insérées avant `__dzSendSched` ; l'en-tête reçoit une
   rangée de boutons ; l'inspecteur un bouton « Suite (fil X) ».
6. **Telegram et métriques** : l'API Bot ne renvoie pas les vues d'un message de
   canal (de mémoire — relu à la Tâche 7, étape 1) ; le tableau de bord affiche
   « — » pour Telegram plutôt qu'un chiffre inventé.

## Coût de patch (tâche par tâche)

| Tâche | Bundle | Détail |
|---|---|---|
| T0 décision, T1 socle, T2 registre+quotas, T3 YouTube, T4 Instagram, T5 TikTok | aucun | backend + bancs |
| T6 réglages/OAuth | aucun | clés, `/health`, `/channels/test`, `/oauth/*` |
| T7 métriques, T8 créneaux, T9 aperçus, T10 validation | aucun | backend ; P4 profite de l'itération `e.channels` existante |
| **T11 patcher `scheduler` (lot 1)** | **1 patcher, 5 ancres** | comptées dans CE bundle le 03/09 (`python` + `str.count`, chacune à 1) : helpers avant `function __dzSendSched` (A1), table `_t` à `limit:2200}},Bu=Object.values(_t)` (A2), icône `channelTiktok` à la fin de la carte d'icônes (A3), liste `chans` de Settings à `connected:["IG_ACCESS_TOKEN","IG_BUSINESS_ID"].every(setk)}];` (A4), rangée de boutons de l'en-tête à `children:"New post"})]})}` (A5). Les cartes Settings restent des DONNÉES (une entrée de tableau) : les boutons de connexion vivent dans un panneau DOM, pas dans le JSX — d'où 5 ancres et non les 9 estimées avant mesure. |
| T12 lot exportable, T13 brief, T14 séries, T15 fils, T16 recyclage | aucun | backend |
| **T17 patcher `scheduler` (lot 2)** | **MÊME patcher, +1 ancre (6)** | le patcher est ÉTENDU puis relancé (il restaure depuis `.bak_scheduler` et réapplique tout) : helpers A1 grossissent, A5 gagne un bouton « Campagne », et A6 `onClick:P,children:"Duplicate to next day"})]})]})}` (1 occurrence, mesurée) porte « Suite (fil X) ». |
| T18 mutations | aucun | `backend/tests/mutations_scheduler.py` |

Chaîne : `.bak_*` sont ignorés par git (`.gitignore` l.58) — la chaîne est une
propriété de la copie de travail. Mesuré dans ce worktree le 03/09 :
`ls -t frontend/dist/assets/*.bak_*` → `seedance25` (28/08 18:14) en queue ;
les patchers `etabli` et `asset3d_h31` (T4 Établi) déclarent « POST-libsend »
et ont tourné ailleurs. **Avant T11 : `python scripts/repatch_all.py --list`**
et écrire le BASELINE du docstring d'après ce qui est imprimé ; sans aucun
`.bak`, le patcher crée `.bak_scheduler` depuis le bundle commité (déjà patché
jusqu'au dernier commit — les ancres ont été mesurées dessus). Jamais
`repatch_all.py --from` sur cette chaîne (garde `guard_downstream`).

## Références vérifiées

Vérifiées le 03/09/2026 (R6) — seules celles-ci servent d'argument :
- **X API** : palier gratuit 500 posts et 100 lectures par mois (docs.x.com,
  devcommunity.x.com). Analytics X bornée à 10 posts × ~10 rafraîchissements.
- **Instagram Graph API** : compte professionnel (Business/Creator) ; reels en
  média unique ; 50 posts / 24 h ; accès Standard pour ses propres comptes
  (developers.facebook.com).
- **YouTube Data API** : `videos.insert` dans son propre seau, 100 envois/jour ;
  10 000 unités/jour pour le reste (developers.google.com).
- **TikTok Content Posting API** : client non audité = `SELF_ONLY`, compte
  privé, 5 utilisateurs / 24 h ; ~15 posts/jour par créateur ; l'audit lève la
  restriction (developers.tiktok.com).
- **Postiz** : open source, auto-hébergeable, 30+ plateformes, API (postiz.com,
  github.com).

De mémoire, à vérifier dans la tâche qui les utilise (étape « relire la doc »,
`WebFetch` exact, date écrite dans le docstring du module) :
- Instagram : envoi **résumable** (`upload_type=resumable`, `rupload.facebook.com`,
  en-têtes `offset`/`file_size`) et noms des métriques d'insights de reels
  (`views` a remplacé `plays` en 2024) — T4.
- YouTube : OAuth « application de bureau » avec redirection loopback
  `http://127.0.0.1:<port>` ; Shorts = vertical ≤ 3 min ; `videos.list?part=statistics`
  = 1 unité — T3, T7.
- TikTok : redirect URI en HTTPS obligatoire (d'où « coller le code »), morceaux
  de 5 à 64 Mo, `video/query` avec `view_count`/`like_count`/… — T5, T7.
- Telegram Bot API : absence de champ `views` sur `Message` — T7.
- Zones d'interface Reels/Shorts/TikTok (fractions du cadre) — T9 ; les
  captures d'écran d'un vrai téléphone font foi.

## Structure de fichiers

Créés :
- `backend/app/services/quota.py` — compteurs par canal, plafonds vérifiés.
- `backend/app/services/publishers.py` — registre + `PublishResult`.
- `backend/app/services/youtube_publisher.py`, `instagram_publisher.py`,
  `tiktok_publisher.py` — un adaptateur par fichier, chacun s'enregistre.
- `backend/app/services/metrics_service.py` — instantanés, passe quotidienne,
  agrégats.
- `backend/app/services/schedule_slots.py` — créneaux par canal, proposition.
- `backend/app/services/series_service.py` — séries récurrentes.
- `backend/tests/fakehttp.py` — faux `httpx.AsyncClient` partagé.
- `backend/tests/test_scheduler_<socle|publish|youtube|instagram|tiktok|settings|metrics|slots|preview|validate|bundle|lot|brief|series|threads|recycle>.py`.
- `backend/tests/mutations_scheduler.py`.
- `scripts/patch_bundle_scheduler.py`.

Modifiés : `storage.py` (colonnes + 3 tables), `marketing.py` (registre,
threads, brief, recyclage, tick), `post_preview.py` (verticaux), `config.py`
(clés), `plan_schema.py` (tiktok), `routes.py` (routes `/schedule/*`,
`/marketing/*`, `/oauth/*`), `CHANGELOG.md`.

Conventions des bancs : scripts AUTONOMES, `sys.stdout.reconfigure(encoding="utf-8")`,
base temporaire par `DATABASE_URL` posé avant l'import de `app.config` puis
forcé sur l'objet `settings` (le `.env` du data-dir a priorité — patron
`test_plan_brief.py` l.15-25), un processus par fichier :
`cd backend ; python tests/test_<x>.py`. Jamais `pytest tests`.

Commits : sujet SANS accents, corps accentué, pied
`Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, guillemets simples
dans `-m`. **C'est l'orchestrateur qui commet** : les étapes « Commit » donnent
la commande à lui remettre.

---

## Lot 1 — parité

### Tâche 0 : décision P1 — trois adaptateurs directs contre Postiz

**Files :** aucun code ; le verdict s'écrit dans ce plan (section ci-dessous) et
dans le docstring de `publishers.py` (Tâche 2).

- [ ] **Étape 1 : mesurer Postiz** — `WebFetch https://docs.postiz.com/` puis
  `WebFetch https://github.com/gitroomhq/postiz-app` ; relever (a) les
  prérequis d'auto-hébergement (conteneurs, base, cache), (b) si Postiz
  dispense de créer une app développeur Meta / Google / TikTok (attendu : non —
  chaque fournisseur exige SON app et SA revue ; noter la page qui le dit),
  (c) l'existence d'une API publique pour pousser un post. Noter la date.
- [ ] **Étape 2 : remplir la grille** (ci-dessous, à corriger si l'étape 1
  contredit) :

| Critère | 3 adaptateurs directs | Postiz relais unique |
|---|---|---|
| Coût de dev | 3 modules ≈ 120 l. + 3 bancs (T3-T5) | 1 module + installation/maintenance d'un service (Docker, Postgres, Redis) |
| Comptes / revues | app Meta (Standard suffit pour son compte), projet Google Cloud, app TikTok + audit | **les mêmes** — le relais n'en dispense pas |
| Quotas (R6) | 50/24 h IG, 100/j YT, 15/j TikTok, 500/mois X | **les mêmes** |
| Service qui tourne | aucun : le backend publie à l'heure | un hôte permanent — refusé par R12 (réponses 4 et 6 : pas d'hôte, aucun tiers) |
| PC éteint | le téléphone publie (R12 P3, hors plan) | Postiz local s'éteint avec le PC ; hébergé = hôte permanent |

- [ ] **Étape 3 : trancher** — adaptateurs directs, sauf si l'utilisateur veut
  un hôte permanent (R12 dit non). Postiz reste une note (R12 E2). Écrire le
  verdict daté dans le docstring de `publishers.py` (Tâche 2, étape 3).

### Tâche 1 : socle de données

**Files :**
- Modify : `backend/app/services/storage.py` (ScheduledPost l.82-120, `SCHEDULED_POSTS_COLUMNS` l.385, `_auto_migrate` l.516)
- Test : `backend/tests/test_scheduler_socle.py`

- [ ] **Étape 1 : écrire le banc (rouge)**

```python
"""Socle du Scheduler (plan 2026-09-03) : colonnes neuves de scheduled_posts
posées par auto-ALTER sur une base d'AVANT, tables post_metrics /
campaign_briefs / post_series créées. Banc-miroir : on lit PRAGMA table_info,
pas le modèle.  Run (depuis backend/) : python tests/test_scheduler_socle.py"""
import asyncio, os, pathlib, sqlite3, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
_db = pathlib.Path(_tmp, "t.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from app.services.storage import init_db              # noqa: E402

LEGACY = ("CREATE TABLE scheduled_posts (id VARCHAR(36) PRIMARY KEY, title VARCHAR(200),"
          " caption TEXT, channels VARCHAR(120), run_at DATETIME, status VARCHAR(20),"
          " mode VARCHAR(12), job_id VARCHAR(36), format VARCHAR(20), hook TEXT,"
          " script_idea TEXT, image_idea TEXT, plan_id VARCHAR(36), error TEXT,"
          " created_at DATETIME, posted_at DATETIME, x_post_id VARCHAR(40), metrics TEXT,"
          " source_image VARCHAR(255), brief TEXT)")
NEW = ["remote_ids", "validated_at", "thread_of", "thread_index", "series_id",
       "recycled_from", "published_by"]


def cols(table):
    con = sqlite3.connect(_db)
    try:
        return [r[1] for r in con.execute(f"PRAGMA table_info({table})")]
    finally:
        con.close()


async def main():
    con = sqlite3.connect(_db)
    con.execute(LEGACY)
    con.execute("INSERT INTO scheduled_posts (id,title,channels,run_at,status,mode)"
                " VALUES ('old1','ancien','x','2026-09-01 10:00:00','posted','assisted')")
    con.commit(); con.close()
    await init_db()
    sp = cols("scheduled_posts")
    for c in NEW:
        assert c in sp, f"colonne absente après auto-ALTER : {c}"
    for t in ("post_metrics", "campaign_briefs", "post_series"):
        assert cols(t), f"table absente : {t}"
    assert "engagement" not in cols("post_metrics")   # calculé, jamais stocké
    con = sqlite3.connect(_db)
    assert con.execute("SELECT title FROM scheduled_posts WHERE id='old1'").fetchone()[0] == "ancien"
    con.close()
    print("SCHEDULER SOCLE: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge** — `cd backend ; python tests/test_scheduler_socle.py`
  → `AssertionError: colonne absente après auto-ALTER : remote_ids`.
- [ ] **Étape 3 : colonnes** — dans `ScheduledPost`, après `brief` (l.120) :

```python
    # plan scheduler (03/09/2026) — P1 ids distants par canal, P5 validation par
    # lot, D2 fils et séries, D3 recyclage, D1 qui a publié (pc | appareil R12).
    remote_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON {"x": "17…", "youtube": "dQw…"}
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    thread_of: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    thread_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    series_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    recycled_from: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    published_by: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
```

  et dans `SCHEDULED_POSTS_COLUMNS` après `("brief", "TEXT"),` :

```python
    # plan scheduler (03/09/2026)
    ("remote_ids", "TEXT"), ("validated_at", "DATETIME"), ("thread_of", "VARCHAR(36)"),
    ("thread_index", "INTEGER"), ("series_id", "VARCHAR(36)"),
    ("recycled_from", "VARCHAR(36)"), ("published_by", "VARCHAR(40)"),
```

- [ ] **Étape 4 : tables** — après `class ScheduledPost` :

```python
class PostMetric(Base):
    """Instantané daté des métriques d'un post sur un canal (P2). L'engagement
    est calculé (metrics_service.engagement), jamais stocké."""
    __tablename__ = "post_metrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    post_id: Mapped[str] = mapped_column(String(36), index=True)
    channel: Mapped[str] = mapped_column(String(20), index=True)
    remote_id: Mapped[str] = mapped_column(String(80), default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CampaignBrief(Base):
    """D2 — brief persistant lu par generate_plan (un seul actif)."""
    __tablename__ = "campaign_briefs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    start_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    messages: Mapped[str] = mapped_column(Text, default="")    # une ligne par message clé
    forbidden: Mapped[str] = mapped_column(Text, default="")   # une ligne par terme interdit
    rubrics: Mapped[str] = mapped_column(Text, default="")     # une ligne par rubrique fixe
    active: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PostSeries(Base):
    """D2 — série récurrente matérialisée en brouillons (series_service)."""
    __tablename__ = "post_series"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    weekdays: Mapped[str] = mapped_column(String(20), default="0")   # csv 0=lundi … 6=dimanche
    time: Mapped[str] = mapped_column(String(5), default="09:30")    # heure LOCALE
    channels: Mapped[str] = mapped_column(String(120), default="x")
    format: Mapped[str] = mapped_column(String(20), default="image")
    caption_template: Mapped[str] = mapped_column(Text, default="")  # {date} {weekday} {week}
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Étape 5 : vert** — même commande → `SCHEDULER SOCLE: PASS`. Puis
  `python tests/test_plan_brief.py` → `PLAN BRIEF TEST: PASS` (rien de cassé).
- [ ] **Étape 6 : commit** (remis à l'orchestrateur)

```bash
git add backend/app/services/storage.py backend/tests/test_scheduler_socle.py
git commit -m 'scheduler : socle de donnees - colonnes et trois tables' -m 'Colonnes remote_ids, validated_at, thread_of, thread_index, series_id, recycled_from, published_by posées par auto-ALTER ; tables post_metrics, campaign_briefs, post_series ; banc-miroir sur PRAGMA table_info et base héritée.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 2 : registre des adaptateurs, quotas vérifiés, échec parlant

**Files :**
- Create : `backend/app/services/quota.py`, `backend/app/services/publishers.py`
- Modify : `backend/app/services/marketing.py` (imports l.16-29, `publish_x` l.579, `auto_channels` l.760, `fire_post` l.796-826), `backend/app/services/plan_schema.py` l.38 et l.81, `backend/app/api/routes.py` (`_post_to_dict` l.3924)
- Test : `backend/tests/test_scheduler_publish.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Registre des adaptateurs + quotas (P1) : un canal factice « fakenet »
plafonné à 2/jour ; fire_post itère le registre, écrit remote_ids, refuse au
quota avec un message qui nomme la source, ne republie pas un canal déjà parti.
Run (depuis backend/) : python tests/test_scheduler_publish.py"""
import asyncio, json, os, pathlib, sqlite3, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
_db = pathlib.Path(_tmp, "t.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import marketing, publishers, quota  # noqa: E402
from app.services.publishers import PublishResult     # noqa: E402

quota._FILE = pathlib.Path(_tmp, "quota.json")
quota.LIMITS["fakenet"] = ("day", 2, "banc : 2 par jour")
CALLS = []


async def _fake(caption, video, image, meta):
    CALLS.append((caption, meta.get("title")))
    return PublishResult(True, f"fakenet: ok {len(CALLS)}", f"rid-{len(CALLS)}")

publishers.register("fakenet", lambda: True, _fake)


async def main():
    await init_db()
    assert "fakenet" in marketing.auto_channels()
    assert "instagram" not in marketing.auto_channels()      # aucune clé
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/schedule", json={
            "title": "T1", "caption": "salut", "channels": ["fakenet", "instagram"],
            "run_at": "2026-09-10T10:00:00Z", "status": "scheduled", "mode": "auto",
            "source_image": "nope.png"})
        pid = r.json()["id"]
        res = await marketing.fire_post(pid)
        assert res["ok"] and res["status"] == "posted", res
        assert res["sent"] == ["fakenet: ok 1"]
        assert res["pending"] == ["instagram: assisted (no auto adapter)"]
        assert CALLS[0] == ("salut", "T1")
        row = next(p for p in (await c.get("/api/schedule")).json() if p["id"] == pid)
        assert row["remote_ids"] == {"fakenet": "rid-1"}
        # rejeu : le canal déjà parti n'est PAS republié
        await c.patch(f"/api/schedule/{pid}", json={"status": "scheduled"})
        res = await marketing.fire_post(pid)
        assert res["sent"] == ["fakenet: déjà publié (rid-1)"] and len(CALLS) == 1
        # quota : 2e succès puis refus parlant au 3e
        ids = []
        for i in range(2):
            r = await c.post("/api/schedule", json={"title": f"Q{i}", "caption": "x",
                             "channels": ["fakenet"], "run_at": "2026-09-10T11:00:00Z"})
            ids.append(r.json()["id"])
        assert (await marketing.fire_post(ids[0]))["ok"]
        res = await marketing.fire_post(ids[1])
        assert not res["ok"] and res["pending"] == ["quota fakenet : 2/2 — banc : 2 par jour"], res
        assert res["status"] == "ready"
    q = json.loads(quota._FILE.read_text("utf-8"))
    assert list(q["fakenet"].values()) == [2]
    con = sqlite3.connect(_db)
    assert con.execute("SELECT x_post_id FROM scheduled_posts WHERE id=?", (pid,)).fetchone()[0] is None
    con.close()
    print("SCHEDULER PUBLISH: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge** — `python tests/test_scheduler_publish.py` →
  `ModuleNotFoundError: No module named 'app.services.publishers'`.
- [ ] **Étape 3 : `quota.py`**

```python
"""Compteurs de publication par canal, bornés par les quotas VÉRIFIÉS (R6,
03/09/2026). Fichier JSON DATA_ROOT/scheduler/quota.json :
{"x": {"2026-09": 12}, "youtube": {"2026-09-03": 2}}. Instagram compte 50 posts
par 24 h GLISSANTES ; on borne par jour UTC — plus strict d'au plus un jour,
jamais plus permissif. Telegram n'a pas de plafond publié : non compté."""
import json
from datetime import datetime
from app.config import DATA_ROOT

# canal -> (période, plafond, source datée — reprise telle quelle dans l'erreur)
LIMITS = {
    "x": ("month", 500, "palier gratuit X : 500 posts/mois (docs.x.com, 03/09/2026)"),
    "instagram": ("day", 50, "Instagram Graph API : 50 posts/24 h (developers.facebook.com, 03/09/2026)"),
    "youtube": ("day", 100, "YouTube Data API : 100 envois/jour (developers.google.com, 03/09/2026)"),
    "tiktok": ("day", 15, "TikTok Direct Post : ~15 posts/jour par créateur (developers.tiktok.com, 03/09/2026)"),
}
_FILE = DATA_ROOT / "scheduler" / "quota.json"


def _key(period: str, now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    return now.strftime("%Y-%m") if period == "month" else now.strftime("%Y-%m-%d")


def _load() -> dict:
    try:
        return json.loads(_FILE.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _save(d: dict) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1), "utf-8")
    tmp.replace(_FILE)


def used(channel: str, now: datetime | None = None) -> int:
    lim = LIMITS.get(channel)
    return int(_load().get(channel, {}).get(_key(lim[0], now), 0)) if lim else 0


def check(channel: str, now: datetime | None = None) -> tuple[bool, str]:
    """(True, 'n/plafond') ou (False, message parlant qui nomme la source)."""
    lim = LIMITS.get(channel)
    if not lim:
        return True, ""
    n = used(channel, now)
    if n >= lim[1]:
        return False, f"quota {channel} : {n}/{lim[1]} — {lim[2]}"
    return True, f"{n}/{lim[1]}"


def count(channel: str, now: datetime | None = None) -> int:
    lim = LIMITS.get(channel)
    if not lim:
        return 0
    d = _load()
    k = _key(lim[0], now)
    d.setdefault(channel, {})[k] = int(d.get(channel, {}).get(k, 0)) + 1
    _save(d)
    return d[channel][k]


def summary() -> dict:
    return {ch: {"used": used(ch), "limit": lim[1], "period": lim[0], "source": lim[2]}
            for ch, lim in LIMITS.items()}
```

- [ ] **Étape 4 : `publishers.py`** (le verdict de T0 dans le docstring)

```python
"""Registre des adaptateurs de publication (plan scheduler, P1).

Décision T0 (03/09/2026) : adaptateurs DIRECTS plutôt que Postiz en relais —
mêmes apps développeur, mêmes quotas, mais aucun service permanent à faire
tourner (R12 : pas d'hôte, aucun tiers). Postiz reste une note (R12 E2).

Un adaptateur = (canal, disponible(), publier(caption, video, image, meta)).
`publish` vérifie le quota AVANT l'appel réseau, compte APRÈS un succès, et ne
lève jamais : l'échec est une chaîne qui nomme le canal et la cause."""
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from loguru import logger

from app.services import quota


@dataclass
class PublishResult:
    ok: bool
    detail: str                      # "youtube: short abc" | "youtube init 403: …"
    remote_id: Optional[str] = None


Publisher = Callable[[str, Optional[str], Optional[str], dict], Awaitable[PublishResult]]
_REGISTRY: dict[str, tuple[Callable[[], bool], Publisher]] = {}


def register(channel: str, available: Callable[[], bool], fn: Publisher) -> None:
    _REGISTRY[channel] = (available, fn)


def available_channels() -> set[str]:
    return {ch for ch, (avail, _fn) in _REGISTRY.items() if avail()}


async def publish(channel: str, caption: str, video_path: Optional[str],
                  image_path: Optional[str], meta: dict | None = None) -> PublishResult:
    entry = _REGISTRY.get(channel)
    if not entry or not entry[0]():
        return PublishResult(False, f"{channel}: assisted (no auto adapter)")
    ok, msg = quota.check(channel)
    if not ok:
        return PublishResult(False, msg)
    try:
        res = await entry[1](caption or "", video_path, image_path, meta or {})
    except Exception as e:
        logger.warning(f"publish {channel} raised: {e}")
        return PublishResult(False, f"{channel} error: {e}")
    if res.ok:
        quota.count(channel)
    return res
```

- [ ] **Étape 5 : `marketing.py`** — imports (après l.29) :

```python
from app.services import publishers
from app.services.publishers import PublishResult
```

  `publish_x` gagne `reply_to` (D2 fils, câblé en T15) — signature l.579 :
  `async def publish_x(caption, *, video_path=None, image_path=None, retries=2, reply_to=None)`
  et `_publish_x_sync(caption, video_path, image_path, reply_to=None)` avec
  `client.create_tweet(text=(caption or "")[:280], media_ids=media_ids, in_reply_to_tweet_id=reply_to)` ;
  l'appel devient `asyncio.to_thread(_publish_x_sync, caption, video_path, image_path, reply_to)`.

  Après `publish_telegram` (l.723), les deux enregistrements et `auto_channels` :

```python
async def _pub_telegram(caption, video_path, image_path, meta) -> PublishResult:
    ok, detail = await publish_telegram(caption, video_path=video_path, image_path=image_path)
    return PublishResult(ok, f"telegram: {detail}")


async def _pub_x(caption, video_path, image_path, meta) -> PublishResult:
    ok, detail, tid = await publish_x(caption, video_path=video_path,
                                      image_path=image_path, reply_to=meta.get("reply_to"))
    return PublishResult(ok, f"x: {detail}", tid)


publishers.register("telegram", lambda: settings.has_telegram, _pub_telegram)
publishers.register("x", lambda: settings.has_x, _pub_x)


def auto_channels() -> set[str]:
    """Canaux dont l'adaptateur est enregistré ET dont les clés sont là."""
    return publishers.available_channels()
```

  Dans `fire_post`, remplacer l.804-826 (de `tg_caption = None` à la fin du
  `for ch in channels`) par :

```python
            tg_caption = None
            brief_d = {}
            if post.brief:
                try:
                    brief_d = json.loads(post.brief) or {}
                except (ValueError, TypeError):
                    brief_d = {}
                tg_caption = brief_d.get("tg_caption")
            remote: dict = {}
            if post.remote_ids:
                try:
                    remote = json.loads(post.remote_ids) or {}
                except ValueError:
                    remote = {}
            meta = {"title": post.title, "brief": brief_d}
            for ch in channels:
                if ch in remote:      # rejeu après échec partiel : jamais deux fois
                    sent.append(f"{ch}: déjà publié ({remote[ch]})")
                    continue
                cap = tg_caption if (ch == "telegram" and tg_caption) else (post.caption or post.title)
                res = await publishers.publish(ch, cap, video, image, meta)
                if res.ok:
                    sent.append(res.detail)
                    if res.remote_id:
                        remote[ch] = res.remote_id
                        if ch == "x":
                            post.x_post_id = res.remote_id
                else:
                    errors.append(res.detail)
            post.remote_ids = json.dumps(remote) if remote else None
```

  `plan_schema.py` l.38 : `_CHANNELS = ("x", "telegram", "youtube", "instagram", "tiktok")` ;
  l.81 : ajouter `|\"tiktok\"` dans la liste des canaux du prompt.
  `_post_to_dict` (routes l.3924) : ajouter la clé `"remote_ids"` — le JSON
  parsé dans un `try` qui rend `None` sur `(ValueError, TypeError)`.
- [ ] **Étape 6 : vert** — `python tests/test_scheduler_publish.py` →
  `SCHEDULER PUBLISH: PASS` ; `python tests/test_plan_brief.py` → PASS
  (Telegram reçoit toujours la `tg_caption`).
- [ ] **Étape 7 : commit**

```bash
git add backend/app/services/quota.py backend/app/services/publishers.py backend/app/services/marketing.py backend/app/services/plan_schema.py backend/app/api/routes.py backend/tests/test_scheduler_publish.py
git commit -m 'scheduler : registre des adaptateurs et quotas verifies' -m 'Un canal = (disponible, publier) ; quota vérifié avant, compté après ; fire_post itère le registre, écrit remote_ids par canal et ne rejoue jamais un canal déjà parti ; décision T0 (adaptateurs directs, pas Postiz) dans le docstring.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 3 : YouTube Shorts (OAuth loopback + envoi résumable)

**Files :**
- Create : `backend/app/services/youtube_publisher.py`, `backend/tests/fakehttp.py`
- Modify : `backend/app/config.py` (clés, après l.161), `backend/app/services/marketing.py` (import d'enregistrement)
- Test : `backend/tests/test_scheduler_youtube.py`

- [ ] **Étape 1 : relire la doc** — `WebFetch https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol`
  (init `POST …/upload/youtube/v3/videos?uploadType=resumable`, en-têtes
  `X-Upload-Content-Length/Type`, réponse `Location`, puis `PUT`),
  `WebFetch https://developers.google.com/identity/protocols/oauth2/native-app`
  (loopback `http://127.0.0.1:<port>` autorisé pour un client « Desktop »),
  `WebFetch https://developers.google.com/youtube/v3/determine_quota_cost`.
  Écrire les trois dates dans le docstring ; corriger les URL du module si la
  doc diffère.
- [ ] **Étape 2 : clés** — `config.py` après `X_ACCESS_SECRET` :

```python
    # plan scheduler (03/09/2026) — YouTube Shorts (OAuth appli de bureau, refresh
    # token écrit par /api/oauth/youtube/callback), Instagram Reels (jeton longue
    # durée + id du compte pro), TikTok Direct Post (OAuth ; TIKTOK_AUDITED lève
    # la visibilité SELF_ONLY).
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REFRESH_TOKEN: str = ""
    YOUTUBE_CHANNEL_ID: str = ""
    IG_ACCESS_TOKEN: str = ""
    IG_BUSINESS_ID: str = ""
    TIKTOK_CLIENT_KEY: str = ""
    TIKTOK_CLIENT_SECRET: str = ""
    TIKTOK_REFRESH_TOKEN: str = ""
    TIKTOK_REDIRECT_URI: str = ""
    TIKTOK_AUDITED: bool = False

    @property
    def has_youtube(self) -> bool:
        return all(v.strip() for v in (self.YOUTUBE_CLIENT_ID, self.YOUTUBE_CLIENT_SECRET,
                                       self.YOUTUBE_REFRESH_TOKEN))

    @property
    def has_instagram(self) -> bool:
        return bool(self.IG_ACCESS_TOKEN.strip() and self.IG_BUSINESS_ID.strip())

    @property
    def has_tiktok(self) -> bool:
        return all(v.strip() for v in (self.TIKTOK_CLIENT_KEY, self.TIKTOK_CLIENT_SECRET,
                                       self.TIKTOK_REFRESH_TOKEN))
```

- [ ] **Étape 3 : `tests/fakehttp.py`** (partagé par T3-T7 ; pas un test, non collecté)

```python
"""Faux httpx.AsyncClient pour les bancs du Scheduler : enregistre chaque
appel (méthode, url, kwargs, corps LU) et répond selon un script consommé
dans l'ordre. `factory` remplace `<module>._client`."""


class FakeResp:
    def __init__(self, status=200, json=None, headers=None, text=""):
        self.status_code, self._json = status, json or {}
        self.headers, self.text = headers or {}, text or str(json or "")

    def json(self):
        return self._json


class FakeClient:
    calls: list = []
    script: list = []

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def _do(self, method, url, **kw):
        content = kw.get("content")
        body = content.read() if hasattr(content, "read") else content
        FakeClient.calls.append((method, url, kw, body))
        return FakeClient.script.pop(0) if FakeClient.script else FakeResp(200, {})

    async def post(self, url, **kw):
        return await self._do("POST", url, **kw)

    async def put(self, url, **kw):
        return await self._do("PUT", url, **kw)

    async def get(self, url, **kw):
        return await self._do("GET", url, **kw)


def factory(timeout=60.0, **k):
    return FakeClient()
```

- [ ] **Étape 4 : banc (rouge)**

```python
"""YouTube Shorts (P1) : init résumable avec la taille RÉELLE, PUT du fichier,
id renvoyé ; refus parlant sur 403 ; pas de vidéo = refus sans réseau.
Run (depuis backend/) : python tests/test_scheduler_youtube.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from app.config import settings                        # noqa: E402
from app.services import youtube_publisher as yp       # noqa: E402
from fakehttp import FakeClient, FakeResp, factory     # noqa: E402

yp._client = factory
settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_CLIENT_SECRET = "cid", "sec"
settings.YOUTUBE_REFRESH_TOKEN = "rt"
vid = pathlib.Path(tempfile.mkdtemp(), "short.mp4")
vid.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"z" * 500)


async def main():
    assert settings.has_youtube
    assert yp.auth_url("s1").startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "state=s1" in yp.auth_url("s1") and "127.0.0.1" in yp.redirect_uri()
    FakeClient.calls.clear()
    FakeClient.script[:] = [FakeResp(200, {"access_token": "at"}),
                            FakeResp(200, {}, {"location": "https://up.example/sess"}),
                            FakeResp(200, {"id": "vid123"})]
    res = await yp.publish("Titre du short\nLigne 2 #Shorts", str(vid), None, {"title": "Mon Short"})
    assert res.ok and res.remote_id == "vid123", res
    tok, init, put = FakeClient.calls
    assert init[1].startswith("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable")
    assert init[2]["headers"]["X-Upload-Content-Length"] == str(vid.stat().st_size)
    assert init[2]["json"]["snippet"]["title"] == "Mon Short"
    assert put[1] == "https://up.example/sess" and put[3] == vid.read_bytes()
    FakeClient.script[:] = [FakeResp(200, {"access_token": "at"}), FakeResp(403, {}, text="quotaExceeded")]
    res = await yp.publish("x", str(vid), None, {})
    assert not res.ok and res.detail.startswith("youtube init 403"), res
    res = await yp.publish("x", None, "still.png", {})
    assert not res.ok and "exige une vidéo" in res.detail
    FakeClient.calls.clear()
    FakeClient.script[:] = [FakeResp(200, {"access_token": "at"}),
                            FakeResp(200, {"items": [{"id": "vid123", "statistics": {
                                "viewCount": "42", "likeCount": "3", "commentCount": "1"}}]})]
    st = await yp.fetch_stats(["vid123"])
    assert st == {"vid123": {"views": 42, "likes": 3, "comments": 1, "shares": 0, "saves": 0}}
    assert FakeClient.calls[1][2]["params"]["part"] == "statistics"
    print("SCHEDULER YOUTUBE: PASS")

asyncio.run(main())
```

- [ ] **Étape 5 : rouge** — `python tests/test_scheduler_youtube.py` →
  `ModuleNotFoundError: No module named 'app.services.youtube_publisher'`.
- [ ] **Étape 6 : `youtube_publisher.py`**

```python
"""YouTube Shorts — Data API v3 en HTTP direct (httpx), sans client Google.
OAuth 2.0 « application de bureau » : redirection loopback sur le backend
(http://127.0.0.1:<PORT>/api/oauth/youtube/callback), refresh token écrit dans
.env par la route. Envoi résumable : POST init → Location → PUT du fichier.
Quota : 100 envois/jour (developers.google.com, vérifié 03/09/2026 — R6).
Doc relue le <date écrite à l'étape 1 de la Tâche 3>."""
from pathlib import Path
from urllib.parse import urlencode

import httpx
from loguru import logger

from app.config import settings, SSL_VERIFY
from app.services import publishers
from app.services.publishers import PublishResult

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = ("https://www.googleapis.com/upload/youtube/v3/videos"
              "?uploadType=resumable&part=snippet,status")
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
SCOPES = ("https://www.googleapis.com/auth/youtube.upload "
          "https://www.googleapis.com/auth/youtube.readonly")


def redirect_uri() -> str:
    return f"http://127.0.0.1:{settings.PORT}/api/oauth/youtube/callback"


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def auth_url(state: str) -> str:
    return AUTH_URL + "?" + urlencode({
        "client_id": settings.YOUTUBE_CLIENT_ID, "redirect_uri": redirect_uri(),
        "response_type": "code", "scope": SCOPES, "access_type": "offline",
        "prompt": "consent", "state": state})


async def exchange_code(code: str) -> str:
    """code → refresh_token ('' si Google refuse)."""
    async with _client() as c:
        r = await c.post(TOKEN_URL, data={
            "code": code, "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "redirect_uri": redirect_uri(), "grant_type": "authorization_code"})
    if r.status_code != 200:
        logger.warning(f"youtube oauth {r.status_code}: {r.text[:200]}")
        return ""
    return str(r.json().get("refresh_token") or "")


async def access_token() -> str:
    async with _client() as c:
        r = await c.post(TOKEN_URL, data={
            "refresh_token": settings.YOUTUBE_REFRESH_TOKEN,
            "client_id": settings.YOUTUBE_CLIENT_ID,
            "client_secret": settings.YOUTUBE_CLIENT_SECRET,
            "grant_type": "refresh_token"})
    if r.status_code != 200:
        raise RuntimeError(f"youtube token {r.status_code}: {r.text[:160]}")
    return r.json()["access_token"]


async def publish(caption: str, video_path, image_path, meta: dict) -> PublishResult:
    if not video_path or not Path(video_path).is_file():
        return PublishResult(False, "youtube: un Short exige une vidéo (aucun rendu attaché)")
    size = Path(video_path).stat().st_size
    first = caption.splitlines()[0] if caption else "Short"
    title = (meta.get("title") or first)[:100]
    body = {"snippet": {"title": title, "description": caption[:5000], "categoryId": "22"},
            "status": {"privacyStatus": meta.get("privacy", "public"),
                       "selfDeclaredMadeForKids": False}}
    try:
        tok = await access_token()
        async with _client(timeout=900.0) as c:
            r = await c.post(UPLOAD_URL, json=body, headers={
                "Authorization": f"Bearer {tok}", "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(size)})
            if r.status_code != 200:
                return PublishResult(False, f"youtube init {r.status_code}: {r.text[:200]}")
            loc = r.headers.get("location", "")
            with open(video_path, "rb") as f:
                r2 = await c.put(loc, content=f, headers={
                    "Authorization": f"Bearer {tok}", "Content-Type": "video/mp4",
                    "Content-Length": str(size)})
        if r2.status_code not in (200, 201):
            return PublishResult(False, f"youtube upload {r2.status_code}: {r2.text[:200]}")
        vid = str(r2.json().get("id") or "")
        return PublishResult(True, f"youtube: short {vid}", vid or None)
    except Exception as e:
        return PublishResult(False, f"youtube error: {e}")


async def fetch_stats(video_ids: list[str]) -> dict[str, dict]:
    """statistics de ≤ 50 vidéos — 1 unité de quota par appel."""
    if not video_ids:
        return {}
    tok = await access_token()
    async with _client() as c:
        r = await c.get(VIDEOS_URL, params={"part": "statistics", "id": ",".join(video_ids[:50])},
                        headers={"Authorization": f"Bearer {tok}"})
    if r.status_code != 200:
        return {}
    out = {}
    for it in r.json().get("items", []):
        s = it.get("statistics", {})
        out[it["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                         "comments": int(s.get("commentCount", 0)), "shares": 0, "saves": 0}
    return out


publishers.register("youtube", lambda: settings.has_youtube, publish)
```

  Dans `marketing.py`, sous les imports :
  `from app.services import youtube_publisher  # noqa: F401 — enregistre l'adaptateur`.
- [ ] **Étape 7 : vert** — `python tests/test_scheduler_youtube.py` → `SCHEDULER YOUTUBE: PASS` ;
  `python tests/test_hygiene_imports.py` → vert (aucun `asyncio` sans import).
- [ ] **Étape 8 : commit**

```bash
git add backend/app/services/youtube_publisher.py backend/app/config.py backend/app/services/marketing.py backend/tests/fakehttp.py backend/tests/test_scheduler_youtube.py
git commit -m 'scheduler : adaptateur YouTube Shorts, OAuth loopback et envoi resumable' -m 'HTTP direct par httpx (aucune dépendance Google) ; init résumable avec la taille réelle, PUT du fichier, statistics pour les métriques ; faux client HTTP partagé par les bancs.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 4 : Instagram Reels (Graph API, envoi résumable)

**Files :**
- Create : `backend/app/services/instagram_publisher.py`
- Modify : `backend/app/services/marketing.py` (import d'enregistrement)
- Test : `backend/tests/test_scheduler_instagram.py`

- [ ] **Étape 1 : relire la doc** — `WebFetch https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media`
  (paramètres `media_type=REELS`, `upload_type=resumable`, `uri` de retour) et
  `WebFetch https://developers.facebook.com/docs/instagram-platform/content-publishing`
  (limite 50/24 h, statut du conteneur, `media_publish`), puis
  `WebFetch https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/insights`
  (noms des métriques de reels). Trois issues possibles, à écrire dans le
  docstring avec la date : (a) résumable documenté → `RESUMABLE_SUPPORTED = True` ;
  (b) seulement `video_url` public → `RESUMABLE_SUPPORTED = False`, l'adaptateur
  se déclare indisponible (« instagram : l'API exige une URL publique — reste au
  téléphone, R12 P3 ») ; (c) noms de métriques différents → corriger `METRICS`.
- [ ] **Étape 2 : banc (rouge)**

```python
"""Instagram Reels (P1) : conteneur résumable, envoi binaire avec offset/file_size,
sondage FINISHED, media_publish ; jeton jamais dans le détail d'erreur.
Run (depuis backend/) : python tests/test_scheduler_instagram.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from app.config import settings                        # noqa: E402
from app.services import instagram_publisher as ip     # noqa: E402
from fakehttp import FakeClient, FakeResp, factory     # noqa: E402

ip._client = factory
ip.POLL_EVERY_S = 0
settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID = "IGTOKEN-SECRET", "1789"
vid = pathlib.Path(tempfile.mkdtemp(), "reel.mp4")
vid.write_bytes(b"reel" * 100)


async def main():
    assert ip.available() == ip.RESUMABLE_SUPPORTED
    FakeClient.calls.clear()
    FakeClient.script[:] = [
        FakeResp(200, {"id": "c1", "uri": "https://rupload.facebook.com/ig-api-upload/v21.0/c1"}),
        FakeResp(200, {"success": True}),
        FakeResp(200, {"status_code": "IN_PROGRESS"}),
        FakeResp(200, {"status_code": "FINISHED"}),
        FakeResp(200, {"id": "media9"})]
    res = await ip.publish("Légende #reel", str(vid), None, {})
    assert res.ok and res.remote_id == "media9", res
    cont, up, s1, s2, pub = FakeClient.calls
    assert cont[1].endswith("/1789/media") and cont[2]["data"]["media_type"] == "REELS"
    assert cont[2]["data"]["upload_type"] == "resumable"
    assert up[2]["headers"]["file_size"] == str(vid.stat().st_size) and up[3] == vid.read_bytes()
    assert up[2]["headers"]["offset"] == "0"
    assert pub[1].endswith("/1789/media_publish") and pub[2]["data"]["creation_id"] == "c1"
    FakeClient.script[:] = [FakeResp(400, {"error": {"message": "bad IGTOKEN-SECRET"}})]
    res = await ip.publish("x", str(vid), None, {})
    assert not res.ok and "IGTOKEN-SECRET" not in res.detail and res.detail.startswith("instagram container 400")
    FakeClient.calls.clear()
    FakeClient.script[:] = [FakeResp(200, {"data": [{"name": "views", "values": [{"value": 500}]},
                                                    {"name": "likes", "values": [{"value": 20}]},
                                                    {"name": "saved", "values": [{"value": 2}]}]})]
    st = await ip.fetch_insights(["media9"])
    assert st["media9"] == {"views": 500, "likes": 20, "comments": 0, "shares": 0, "saves": 2}
    print("SCHEDULER INSTAGRAM: PASS")

asyncio.run(main())
```

- [ ] **Étape 3 : rouge** — `python tests/test_scheduler_instagram.py` → `ModuleNotFoundError`.
- [ ] **Étape 4 : `instagram_publisher.py`**

```python
"""Instagram Reels — Graph API (compte professionnel, jeton longue durée +
id du compte IG : IG_ACCESS_TOKEN / IG_BUSINESS_ID). Envoi RÉSUMABLE
(upload_type=resumable, rupload.facebook.com) : le fichier part du PC, aucun
hôte public. 50 posts/24 h (developers.facebook.com, vérifié 03/09/2026 — R6).
Doc relue le <date T4 étape 1> : RESUMABLE_SUPPORTED reflète ce qui a été lu."""
import asyncio
from pathlib import Path

import httpx

from app.config import settings, SSL_VERIFY
from app.services import publishers
from app.services.publishers import PublishResult

GRAPH = "https://graph.facebook.com/v21.0"
RESUMABLE_SUPPORTED = True          # bascule mesurée à la Tâche 4, étape 1
METRICS = "views,likes,comments,shares,saved"
POLL_EVERY_S, POLL_MAX = 5.0, 36    # 3 min


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def _scrub(text: str) -> str:
    tok = settings.IG_ACCESS_TOKEN.strip()
    return text.replace(tok, "***") if tok else text


def available() -> bool:
    return settings.has_instagram and RESUMABLE_SUPPORTED


async def publish(caption: str, video_path, image_path, meta: dict) -> PublishResult:
    if not video_path or not Path(video_path).is_file():
        return PublishResult(False, "instagram: un Reel exige une vidéo (aucun rendu attaché)")
    tok, ig = settings.IG_ACCESS_TOKEN, settings.IG_BUSINESS_ID
    size = Path(video_path).stat().st_size
    try:
        async with _client(timeout=900.0) as c:
            r = await c.post(f"{GRAPH}/{ig}/media", data={
                "media_type": "REELS", "upload_type": "resumable",
                "caption": caption[:2200], "share_to_feed": "true", "access_token": tok})
            if r.status_code != 200:
                return PublishResult(False, f"instagram container {r.status_code}: {_scrub(r.text)[:200]}")
            j = r.json()
            container, uri = str(j.get("id", "")), j.get("uri", "")
            with open(video_path, "rb") as f:
                r2 = await c.post(uri, content=f, headers={
                    "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)})
            if r2.status_code != 200 or not r2.json().get("success"):
                return PublishResult(False, f"instagram upload {r2.status_code}: {_scrub(r2.text)[:200]}")
            for _ in range(POLL_MAX):
                s = await c.get(f"{GRAPH}/{container}",
                                params={"fields": "status_code,status", "access_token": tok})
                code = s.json().get("status_code")
                if code == "FINISHED":
                    break
                if code in ("ERROR", "EXPIRED"):
                    return PublishResult(False, f"instagram container {code}: {str(s.json().get('status', ''))[:200]}")
                await asyncio.sleep(POLL_EVERY_S)
            else:
                return PublishResult(False, "instagram: conteneur jamais FINISHED après 3 min")
            r3 = await c.post(f"{GRAPH}/{ig}/media_publish",
                              data={"creation_id": container, "access_token": tok})
        if r3.status_code != 200:
            return PublishResult(False, f"instagram publish {r3.status_code}: {_scrub(r3.text)[:200]}")
        mid = str(r3.json().get("id") or "")
        return PublishResult(True, f"instagram: reel {mid}", mid or None)
    except Exception as e:
        return PublishResult(False, f"instagram error: {_scrub(str(e))}")


async def fetch_insights(media_ids: list[str]) -> dict[str, dict]:
    out = {}
    tok = settings.IG_ACCESS_TOKEN
    async with _client() as c:
        for mid in media_ids:
            r = await c.get(f"{GRAPH}/{mid}/insights", params={"metric": METRICS, "access_token": tok})
            if r.status_code != 200:
                continue
            vals = {d.get("name"): (d.get("values") or [{}])[0].get("value", 0)
                    for d in r.json().get("data", [])}
            out[mid] = {"views": int(vals.get("views", 0)), "likes": int(vals.get("likes", 0)),
                        "comments": int(vals.get("comments", 0)), "shares": int(vals.get("shares", 0)),
                        "saves": int(vals.get("saved", 0))}
    return out


publishers.register("instagram", available, publish)
```

  `marketing.py` : `from app.services import instagram_publisher  # noqa: F401`.
- [ ] **Étape 5 : vert** — `python tests/test_scheduler_instagram.py` → `SCHEDULER INSTAGRAM: PASS`.
- [ ] **Étape 6 : commit**

```bash
git add backend/app/services/instagram_publisher.py backend/app/services/marketing.py backend/tests/test_scheduler_instagram.py
git commit -m 'scheduler : adaptateur Instagram Reels par envoi resumable' -m 'Conteneur REELS résumable, envoi binaire depuis le PC (aucun hôte public), sondage FINISHED, media_publish ; le jeton est masqué dans tout détail d erreur ; insights pour les métriques.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 5 : TikTok Direct Post (FILE_UPLOAD par morceaux, privé sans audit)

**Files :**
- Create : `backend/app/services/tiktok_publisher.py`
- Modify : `backend/app/services/marketing.py` (import d'enregistrement)
- Test : `backend/tests/test_scheduler_tiktok.py`

- [ ] **Étape 1 : relire la doc** — `WebFetch https://developers.tiktok.com/doc/content-posting-api-reference-direct-post`
  (init `source: FILE_UPLOAD`, `chunk_size`, `total_chunk_count`, `upload_url`,
  `Content-Range`, bornes des morceaux), `WebFetch https://developers.tiktok.com/doc/content-posting-api-get-started`
  (client non audité → `SELF_ONLY`, compte privé), `WebFetch https://developers.tiktok.com/doc/oauth-user-access-token-management`
  (refresh token ; **redirect URI HTTPS obligatoire ?** — si oui, la voie
  « coller le code » de T6 est la seule ; si un loopback http est accepté,
  ajouter une route callback comme YouTube). Dater dans le docstring ; corriger
  `CHUNK`/`SINGLE_MAX` si les bornes lues diffèrent.
- [ ] **Étape 2 : banc (rouge)**

```python
"""TikTok Direct Post (P1) : init FILE_UPLOAD (taille/chunks réels), PUT avec
Content-Range, sondage PUBLISH_COMPLETE ; SELF_ONLY forcé tant que le client
n'est pas audité, et le détail LE DIT.
Run (depuis backend/) : python tests/test_scheduler_tiktok.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from app.config import settings                        # noqa: E402
from app.services import tiktok_publisher as tp        # noqa: E402
from fakehttp import FakeClient, FakeResp, factory     # noqa: E402

tp._client = factory
tp.POLL_EVERY_S = 0
settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET = "ck", "cs"
settings.TIKTOK_REFRESH_TOKEN, settings.TIKTOK_AUDITED = "rt", False
vid = pathlib.Path(tempfile.mkdtemp(), "tt.mp4")
vid.write_bytes(b"t" * 1000)


async def main():
    assert settings.has_tiktok and tp._chunks(1000) == (1000, 1)
    assert tp._chunks(70 * 1024 * 1024) == (tp.CHUNK, 3)
    FakeClient.calls.clear()
    FakeClient.script[:] = [FakeResp(200, {"access_token": "at"}),
                            FakeResp(200, {"data": {"publish_id": "p1", "upload_url": "https://up.tt/x"}}),
                            FakeResp(201, {}),
                            FakeResp(200, {"data": {"status": "PROCESSING_UPLOAD"}}),
                            FakeResp(200, {"data": {"status": "PUBLISH_COMPLETE",
                                                    "publicaly_available_post_id": [7350001]}})]
    res = await tp.publish("Légende tiktok", str(vid), None, {"privacy": "PUBLIC_TO_EVERYONE"})
    assert res.ok and res.remote_id == "7350001" and "PRIVÉ" in res.detail, res
    tok, init, put, s1, s2 = FakeClient.calls
    assert init[2]["json"]["post_info"]["privacy_level"] == "SELF_ONLY"
    assert init[2]["json"]["source_info"] == {"source": "FILE_UPLOAD", "video_size": 1000,
                                              "chunk_size": 1000, "total_chunk_count": 1}
    assert put[2]["headers"]["Content-Range"] == "bytes 0-999/1000" and put[3] == vid.read_bytes()
    settings.TIKTOK_AUDITED = True
    FakeClient.script[:] = [FakeResp(200, {"access_token": "at"}),
                            FakeResp(200, {"data": {}, "error": {"code": "spam_risk_too_many_posts"}})]
    res = await tp.publish("x", str(vid), None, {})
    assert not res.ok and "spam_risk_too_many_posts" in res.detail
    assert FakeClient.calls[-1][2]["json"]["post_info"]["privacy_level"] == "PUBLIC_TO_EVERYONE"
    print("SCHEDULER TIKTOK: PASS")

asyncio.run(main())
```

- [ ] **Étape 3 : rouge** — `python tests/test_scheduler_tiktok.py` → `ModuleNotFoundError`.
- [ ] **Étape 4 : `tiktok_publisher.py`**

```python
"""TikTok Direct Post — Content Posting API v2, FILE_UPLOAD par morceaux.
Client NON audité = visibilité SELF_ONLY forcée et dite, ~15 posts/jour
(developers.tiktok.com, vérifié 03/09/2026 — R6). TIKTOK_AUDITED=true (Settings)
lève la contrainte. Le refresh token vient de /api/oauth/tiktok/exchange (code
collé — redirect HTTPS). Doc relue le <date T5 étape 1>."""
import asyncio
from pathlib import Path

import httpx

from app.config import settings, SSL_VERIFY
from app.services import publishers
from app.services.publishers import PublishResult

INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
QUERY_URL = "https://open.tiktokapis.com/v2/video/query/"
CHUNK = 32 * 1024 * 1024        # 5 Mo ≤ morceau ≤ 64 Mo (de mémoire — T5 étape 1)
SINGLE_MAX = 64 * 1024 * 1024
POLL_EVERY_S, POLL_MAX = 5.0, 36


def _client(timeout: float = 60.0) -> httpx.AsyncClient:
    return httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout)


def _chunks(size: int) -> tuple[int, int]:
    if size <= SINGLE_MAX:
        return size, 1
    return CHUNK, -(-size // CHUNK)


async def _token(grant: dict) -> dict:
    async with _client() as c:
        r = await c.post(TOKEN_URL, data={"client_key": settings.TIKTOK_CLIENT_KEY,
                                          "client_secret": settings.TIKTOK_CLIENT_SECRET, **grant},
                         headers={"Content-Type": "application/x-www-form-urlencoded"})
    if r.status_code != 200 or not r.json().get("access_token"):
        raise RuntimeError(f"tiktok token {r.status_code}: {r.text[:160]}")
    return r.json()


async def access_token() -> str:
    return (await _token({"grant_type": "refresh_token",
                          "refresh_token": settings.TIKTOK_REFRESH_TOKEN}))["access_token"]


async def exchange_code(code: str) -> str:
    """code collé par l'utilisateur → refresh_token."""
    j = await _token({"grant_type": "authorization_code", "code": code,
                      "redirect_uri": settings.TIKTOK_REDIRECT_URI})
    return str(j.get("refresh_token") or "")


async def publish(caption: str, video_path, image_path, meta: dict) -> PublishResult:
    if not video_path or not Path(video_path).is_file():
        return PublishResult(False, "tiktok: une vidéo est requise (aucun rendu attaché)")
    size = Path(video_path).stat().st_size
    chunk, n = _chunks(size)
    privacy = meta.get("privacy", "PUBLIC_TO_EVERYONE") if settings.TIKTOK_AUDITED else "SELF_ONLY"
    body = {"post_info": {"title": caption[:2200], "privacy_level": privacy,
                          "disable_duet": False, "disable_comment": False,
                          "disable_stitch": False, "video_cover_timestamp_ms": 1000},
            "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                            "chunk_size": chunk, "total_chunk_count": n}}
    try:
        tok = await access_token()
        hdr = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
        async with _client(timeout=900.0) as c:
            r = await c.post(INIT_URL, json=body, headers=hdr)
            d = r.json().get("data") or {}
            if r.status_code != 200 or not d.get("upload_url"):
                return PublishResult(False, f"tiktok init {r.status_code}: {str(r.json().get('error'))[:200]}")
            pid, url = d["publish_id"], d["upload_url"]
            with open(video_path, "rb") as f:
                for i in range(n):
                    part = f.read(chunk)
                    start = i * chunk
                    r2 = await c.put(url, content=part, headers={
                        "Content-Type": "video/mp4", "Content-Length": str(len(part)),
                        "Content-Range": f"bytes {start}-{start + len(part) - 1}/{size}"})
                    if r2.status_code not in (200, 201, 206):
                        return PublishResult(False, f"tiktok upload {r2.status_code} (morceau {i + 1}/{n})")
            post_id = ""
            for _ in range(POLL_MAX):
                s = await c.post(STATUS_URL, json={"publish_id": pid}, headers=hdr)
                sd = s.json().get("data") or {}
                if sd.get("status") == "PUBLISH_COMPLETE":
                    ids = sd.get("publicaly_available_post_id") or []
                    post_id = str(ids[0]) if ids else ""
                    break
                if sd.get("status") == "FAILED":
                    return PublishResult(False, f"tiktok FAILED: {sd.get('fail_reason', '')}")
                await asyncio.sleep(POLL_EVERY_S)
            else:
                return PublishResult(False, "tiktok: statut jamais PUBLISH_COMPLETE après 3 min")
        note = "" if settings.TIKTOK_AUDITED else " — publié en PRIVÉ (client non audité, SELF_ONLY)"
        return PublishResult(True, f"tiktok: {post_id or pid}{note}", post_id or pid)
    except Exception as e:
        return PublishResult(False, f"tiktok error: {e}")


async def fetch_stats(video_ids: list[str]) -> dict[str, dict]:
    tok = await access_token()
    async with _client() as c:
        r = await c.post(QUERY_URL, params={"fields": "id,view_count,like_count,comment_count,share_count"},
                         json={"filters": {"video_ids": [v for v in video_ids if v.isdigit()][:20]}},
                         headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    if r.status_code != 200:
        return {}
    out = {}
    for v in (r.json().get("data") or {}).get("videos", []):
        out[str(v.get("id"))] = {"views": int(v.get("view_count", 0)), "likes": int(v.get("like_count", 0)),
                                 "comments": int(v.get("comment_count", 0)),
                                 "shares": int(v.get("share_count", 0)), "saves": 0}
    return out


publishers.register("tiktok", lambda: settings.has_tiktok, publish)
```

  `marketing.py` : `from app.services import tiktok_publisher  # noqa: F401`.
- [ ] **Étape 5 : vert** — `python tests/test_scheduler_tiktok.py` → `SCHEDULER TIKTOK: PASS` ;
  `python tests/test_hygiene_imports.py` → vert.
- [ ] **Étape 6 : commit**

```bash
git add backend/app/services/tiktok_publisher.py backend/app/services/marketing.py backend/tests/test_scheduler_tiktok.py
git commit -m 'scheduler : adaptateur TikTok Direct Post, prive sans audit' -m 'Init FILE_UPLOAD aux tailles réelles, PUT par morceaux avec Content-Range, sondage PUBLISH_COMPLETE ; SELF_ONLY forcé et dit tant que TIKTOK_AUDITED est faux ; video/query pour les métriques.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 6 : réglages, `/health`, `/channels/test`, routes OAuth

**Files :**
- Modify : `backend/app/api/routes.py` (`/health` l.3459, `_ALLOWED_ENV_KEYS` l.3501, `set_key` l.3568-3612, `/channels/test` l.4361), imports en tête de `routes.py`
- Test : `backend/tests/test_scheduler_settings.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Réglages des trois canaux (P1) : clés listées, drapeaux /health, OAuth
YouTube par loopback (state, refresh token ÉCRIT dans le .env du data-dir et
posé sur settings sans redémarrage), code TikTok collé, /channels/test.
Run (depuis backend/) : python tests/test_scheduler_settings.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp                # .env du banc, pas celui de l'utilisateur
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings, ENV_FILE             # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import youtube_publisher as yp, tiktok_publisher as tp  # noqa: E402

assert str(ENV_FILE).startswith(_tmp), ENV_FILE


async def _fake_yt(code):
    return "rt-yt-" + code


async def _fake_tt(code):
    return "rt-tt-" + code

yp.exchange_code, tp.exchange_code = _fake_yt, _fake_tt


async def main():
    await init_db()
    settings.YOUTUBE_CLIENT_ID, settings.YOUTUBE_CLIENT_SECRET = "cid", "sec"
    settings.YOUTUBE_REFRESH_TOKEN = ""
    settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET = "ck", "cs"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        keys = {k["key"] for k in (await c.get("/api/settings/keys")).json()["keys"]}
        assert {"TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN",
                "TIKTOK_REDIRECT_URI", "TIKTOK_AUDITED", "IG_ACCESS_TOKEN"} <= keys
        h = (await c.get("/api/health")).json()
        assert h["youtube_enabled"] is False and h["instagram_enabled"] is False and h["tiktok_enabled"] is False
        r = await c.get("/api/oauth/youtube/start", follow_redirects=False)
        assert r.status_code in (302, 307) and "accounts.google.com" in r.headers["location"]
        state = r.headers["location"].split("state=")[1].split("&")[0]
        r = await c.get("/api/oauth/youtube/callback", params={"code": "abc", "state": "faux"})
        assert r.status_code == 400
        r = await c.get("/api/oauth/youtube/callback", params={"code": "abc", "state": state})
        assert r.status_code == 200 and "connecté" in r.text.lower()
        assert "YOUTUBE_REFRESH_TOKEN=rt-yt-abc" in ENV_FILE.read_text("utf-8")
        assert settings.has_youtube and (await c.get("/api/health")).json()["youtube_enabled"] is True
        r = await c.post("/api/oauth/tiktok/exchange", json={"code": "zzz"})
        assert r.json()["ok"] and "TIKTOK_REFRESH_TOKEN=rt-tt-zzz" in ENV_FILE.read_text("utf-8")
        assert settings.has_tiktok
        r = await c.post("/api/channels/test", json={"channel": "instagram"})
        assert r.status_code == 400 and "IG_ACCESS_TOKEN" in r.json()["detail"]
    print("SCHEDULER SETTINGS: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge** — `python tests/test_scheduler_settings.py` → `AssertionError` sur les clés TikTok.
- [ ] **Étape 3 : clés et drapeaux** — `_ALLOWED_ENV_KEYS` : ajouter
  `"TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN", "TIKTOK_REDIRECT_URI", "TIKTOK_AUDITED",`.
  `/health` : après `"x_enabled"` ajouter `"youtube_enabled": settings.has_youtube,
  "instagram_enabled": settings.has_instagram, "tiktok_enabled": settings.has_tiktok,`.
- [ ] **Étape 4 : extraire l'écriture du `.env`** — dans `set_key`, remplacer
  le bloc `p = _env_path()` … `p.write_text(...)` par `_upsert_env(changes)` et
  poser au-dessus de la route :

```python
def _upsert_env(changes: dict[str, str]) -> None:
    """Upsert structuré dans le .env du data-dir (commentaires et ordre gardés)."""
    p = _env_path()
    lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
    seen: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        s = line.strip()
        if (not s) or s.startswith("#") or "=" not in s:
            new_lines.append(line)
            continue
        k, _, _v = line.partition("=")
        k = k.strip()
        if k in changes:
            new_lines.append(f"{k}={changes[k]}")
            seen.add(k)
        else:
            new_lines.append(line)
    for k, v in changes.items():
        if k not in seen:
            new_lines.append(f"{k}={v}")
    p.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info(f"Wrote {len(changes)} key(s) to {p}")
```

- [ ] **Étape 5 : routes OAuth** — après `/channels/test` ; ajouter
  `RedirectResponse, HTMLResponse` à l'import `fastapi.responses` de `routes.py`
  s'ils manquent (`grep -n "from fastapi.responses" backend/app/api/routes.py`).

```python
_OAUTH_STATES: set[str] = set()


@router.get("/oauth/youtube/start")
async def oauth_youtube_start(request: Request):
    """Ouvre le consentement Google (client « application de bureau »). Le
    refresh token revient par /oauth/youtube/callback (loopback)."""
    _require_localhost(request)
    if not (settings.YOUTUBE_CLIENT_ID.strip() and settings.YOUTUBE_CLIENT_SECRET.strip()):
        raise HTTPException(400, "Renseigne YOUTUBE_CLIENT_ID et YOUTUBE_CLIENT_SECRET (console Google, "
                                 "client OAuth de type « Application de bureau ») puis redémarre")
    from app.services import youtube_publisher as _yp
    state = uuid4().hex
    _OAUTH_STATES.add(state)
    return RedirectResponse(_yp.auth_url(state), status_code=302)


@router.get("/oauth/youtube/callback", response_class=HTMLResponse)
async def oauth_youtube_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    _require_localhost(request)
    if error or state not in _OAUTH_STATES:
        return HTMLResponse(f"<h2>YouTube : refusé ({error or 'state inconnu'})</h2>", status_code=400)
    _OAUTH_STATES.discard(state)
    from app.services import youtube_publisher as _yp
    rt = await _yp.exchange_code(code)
    if not rt:
        return HTMLResponse("<h2>YouTube : aucun refresh token reçu — révoque l'accès dans ton compte "
                            "Google et recommence (prompt=consent)</h2>", status_code=502)
    _upsert_env({"YOUTUBE_REFRESH_TOKEN": rt})
    settings.YOUTUBE_REFRESH_TOKEN = rt        # actif sans redémarrage
    return HTMLResponse("<h2>YouTube connecté — tu peux fermer cet onglet.</h2>")


@router.post("/oauth/tiktok/exchange")
async def oauth_tiktok_exchange(body: dict, request: Request):
    """TikTok exige un redirect HTTPS : l'utilisateur colle le `code` lu sur
    sa page de redirection (TIKTOK_REDIRECT_URI) ; on l'échange ici."""
    _require_localhost(request)
    code = str((body or {}).get("code") or "").strip()
    if not code:
        raise HTTPException(400, "code manquant")
    from app.services import tiktok_publisher as _tp
    try:
        rt = await _tp.exchange_code(code)
    except Exception as e:
        raise HTTPException(502, f"TikTok a refusé le code : {e}")
    if not rt:
        raise HTTPException(502, "TikTok n'a pas renvoyé de refresh token")
    _upsert_env({"TIKTOK_REFRESH_TOKEN": rt})
    settings.TIKTOK_REFRESH_TOKEN = rt
    return {"ok": True}
```

- [ ] **Étape 6 : `/channels/test`** — avant le `raise HTTPException(400, f"No test available…")` :

```python
    if ch == "youtube":
        if not settings.has_youtube:
            raise HTTPException(400, "YouTube : YOUTUBE_CLIENT_ID/SECRET + Connecter (OAuth) requis")
        from app.services import youtube_publisher as _yp
        try:
            tok = await _yp.access_token()
            async with _yp._client() as hc:
                r = await hc.get("https://www.googleapis.com/youtube/v3/channels",
                                 params={"part": "snippet", "mine": "true"},
                                 headers={"Authorization": f"Bearer {tok}"})
            items = r.json().get("items") or []
            return {"ok": bool(items), "detail": items[0]["snippet"]["title"] if items else r.text[:200]}
        except Exception as e:
            return {"ok": False, "detail": str(e)}
    if ch == "instagram":
        if not settings.has_instagram:
            raise HTTPException(400, "Instagram : IG_ACCESS_TOKEN + IG_BUSINESS_ID requis")
        from app.services import instagram_publisher as _ip
        async with _ip._client() as hc:
            r = await hc.get(f"{_ip.GRAPH}/{settings.IG_BUSINESS_ID}",
                             params={"fields": "username", "access_token": settings.IG_ACCESS_TOKEN})
        return {"ok": r.status_code == 200, "detail": _ip._scrub(str(r.json().get("username") or r.text[:200]))}
    if ch == "tiktok":
        if not settings.has_tiktok:
            raise HTTPException(400, "TikTok : TIKTOK_CLIENT_KEY/SECRET + code OAuth collé requis")
        from app.services import tiktok_publisher as _tp
        try:
            tok = await _tp.access_token()
            async with _tp._client() as hc:
                r = await hc.get("https://open.tiktokapis.com/v2/user/info/",
                                 params={"fields": "display_name"},
                                 headers={"Authorization": f"Bearer {tok}"})
            name = ((r.json().get("data") or {}).get("user") or {}).get("display_name")
            return {"ok": bool(name), "detail": name or r.text[:200]}
        except Exception as e:
            return {"ok": False, "detail": str(e)}
```

- [ ] **Étape 7 : vert** — `python tests/test_scheduler_settings.py` → `SCHEDULER SETTINGS: PASS` ;
  `python tests/test_security_guards.py` → vert (les gardes loopback tiennent).
- [ ] **Étape 8 : commit**

```bash
git add backend/app/api/routes.py backend/tests/test_scheduler_settings.py
git commit -m 'scheduler : cles des trois canaux, health, OAuth YouTube loopback et code TikTok' -m 'Clés TikTok admises, drapeaux youtube/instagram/tiktok_enabled, écriture du .env factorisée (_upsert_env), consentement Google par redirection loopback avec state, code TikTok collé et échangé, tests de canal pour les trois réseaux.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 7 : métriques par canal et tableau de bord (P2)

**Files :**
- Create : `backend/app/services/metrics_service.py`
- Modify : `backend/app/services/marketing.py` (`_fetch_x_metrics_sync` l.600, `schedule_loop` l.859-866, imports), `youtube_publisher.py`, `instagram_publisher.py`, `tiktok_publisher.py` (enregistrement des fetchers), `backend/app/api/routes.py` (3 routes)
- Test : `backend/tests/test_scheduler_metrics.py`

- [ ] **Étape 1 : relire la doc Telegram** — `WebFetch https://core.telegram.org/bots/api#message` :
  chercher un champ `views` sur `Message`. Attendu : absent → Telegram reste
  « — » (le dire dans `NOTES`). S'il existe (ou via `forwardMessage`),
  écrire un fetcher `telegram` dans `marketing.py` sur le même patron que X
  et l'enregistrer. Dater dans le docstring de `metrics_service.py`.
- [ ] **Étape 2 : banc (rouge)**

```python
"""Métriques (P2) : passe quotidienne = un fetcher par canal (faux ici), une
ligne post_metrics par (post, canal, date) — le DERNIER instantané gagne dans
l'agrégat ; analytics par canal / format / semaine ISO + top ; X borné à 10.
Run (depuis backend/) : python tests/test_scheduler_metrics.py"""
import asyncio, json, os, pathlib, sqlite3, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
_db = pathlib.Path(_tmp, "t.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db.as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db, ScheduledPost, async_session_factory  # noqa: E402
from app.services import metrics_service as ms, quota  # noqa: E402

quota._FILE = pathlib.Path(_tmp, "quota.json")
TICK = {"n": 0}


async def _yt(ids):
    TICK["n"] += 1
    return {i: {"views": 1000 * TICK["n"], "likes": 10, "comments": 2, "shares": 0, "saves": 0} for i in ids}


async def _x(ids):
    return {i: {"views": 300, "likes": 5, "comments": 1, "shares": 4, "saves": 0} for i in ids}

ms.FETCHERS.clear()
ms.FETCHERS["youtube"], ms.FETCHERS["x"] = _yt, _x


async def seed():
    now = datetime.utcnow()
    async with async_session_factory() as s:
        for i in range(12):
            s.add(ScheduledPost(id=f"p{i}", title=f"Post {i}", channels="x", run_at=now, status="posted",
                                posted_at=now - timedelta(days=i), format="image" if i % 2 else "seedance",
                                remote_ids=json.dumps({"x": f"tw{i}"})))
        s.add(ScheduledPost(id="y1", title="Short", channels="youtube", run_at=now, status="posted",
                            posted_at=now - timedelta(days=2), format="seedance",
                            remote_ids=json.dumps({"youtube": "vid1"})))
        await s.commit()


async def main():
    await init_db()
    await seed()
    counts = await ms.refresh_all(max_per_channel=10)
    assert counts == {"youtube": 1, "x": 10}, counts        # X rationné à 10
    con = sqlite3.connect(_db)
    assert con.execute("SELECT count(*) FROM post_metrics").fetchone()[0] == 11
    assert con.execute("SELECT metrics FROM scheduled_posts WHERE id='p0'").fetchone()[0]  # compat performance_context
    con.close()
    await ms.refresh_all(max_per_channel=10)                 # second instantané : views 2000
    a = await ms.analytics(days=28)
    assert a["channels"]["youtube"] == {"posts": 1, "views": 2000, "likes": 10, "comments": 2,
                                        "shares": 0, "saves": 0, "engagement": 14}
    assert a["channels"]["x"]["posts"] == 10 and a["channels"]["x"]["engagement"] == 10 * (5 + 2 + 12)
    assert set(a["formats"]) == {"image", "seedance"} and len(a["weeks"]) >= 2
    assert a["top"][0]["engagement"] == 19 and a["top"][0]["channel"] == "x"
    assert "quotas" in a and "x" in a["notes"] and "telegram" in a["notes"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/schedule/analytics", params={"days": 28})
        assert r.status_code == 200 and r.json()["channels"]["youtube"]["views"] == 2000
        assert (await c.get("/api/schedule/quotas")).json()["x"]["limit"] == 500
        r = await c.post("/api/schedule/analytics/refresh")
        assert r.json() == {"youtube": 1, "x": 10}
    print("SCHEDULER METRICS: PASS")

asyncio.run(main())
```

- [ ] **Étape 3 : rouge** — `python tests/test_scheduler_metrics.py` → `ModuleNotFoundError`.
- [ ] **Étape 4 : `metrics_service.py`**

```python
"""Métriques par post et par canal (P2) : instantanés datés dans post_metrics,
rafraîchis une fois par jour par la boucle (schedule_loop), agrégés pour le
tableau de bord. Bornes vérifiées (R6, 03/09/2026) : X = 100 lectures/mois au
palier gratuit → 10 posts par passe ; Telegram : l'API Bot n'expose pas les vues
(core.telegram.org/bots/api, relu le <date T7 étape 1>) → « — »."""
import json
from datetime import datetime, timedelta
from typing import Awaitable, Callable
from uuid import uuid4

from loguru import logger
from sqlalchemy import select

from app.services import quota
from app.services.storage import PostMetric, ScheduledPost, async_session_factory

# canal → fetcher(remote_ids) → {remote_id: {views, likes, comments, shares, saves}}
FETCHERS: dict[str, Callable[[list[str]], Awaitable[dict[str, dict]]]] = {}
NOTES = {"x": "100 lectures/mois au palier gratuit (docs.x.com, 03/09/2026) — 10 posts par passe",
         "telegram": "vues non exposées par l'API Bot — aucune métrique"}


def engagement(m: dict) -> int:
    return (int(m.get("likes", 0)) + 2 * int(m.get("comments", 0))
            + 3 * int(m.get("shares", 0)) + 2 * int(m.get("saves", 0)))


def _remote(p: ScheduledPost, ch: str) -> str | None:
    try:
        return (json.loads(p.remote_ids) or {}).get(ch) if p.remote_ids else None
    except (ValueError, TypeError):
        return None


async def refresh_all(max_per_channel: int = 10) -> dict[str, int]:
    """Une passe : pour chaque canal à fetcher, les `max_per_channel` derniers
    posts publiés portant un id distant. Retourne {canal: n mis à jour}."""
    counts: dict[str, int] = {}
    async with async_session_factory() as session:
        res = await session.execute(
            select(ScheduledPost).where(ScheduledPost.status == "posted")
            .where(ScheduledPost.remote_ids.isnot(None))
            .order_by(ScheduledPost.posted_at.desc()).limit(200))
        posts = list(res.scalars().all())
        for ch, fetch in FETCHERS.items():
            pairs = [(p, _remote(p, ch)) for p in posts if _remote(p, ch)][:max_per_channel]
            if not pairs:
                continue
            try:
                got = await fetch([rid for _p, rid in pairs])
            except Exception as e:
                logger.warning(f"metrics {ch}: {e}")
                continue
            n = 0
            for p, rid in pairs:
                m = got.get(rid)
                if not m:
                    continue
                session.add(PostMetric(id=str(uuid4()), post_id=p.id, channel=ch, remote_id=rid,
                                       views=int(m.get("views", 0)), likes=int(m.get("likes", 0)),
                                       comments=int(m.get("comments", 0)), shares=int(m.get("shares", 0)),
                                       saves=int(m.get("saves", 0)), raw=json.dumps(m)))
                if ch == "x":
                    p.metrics = json.dumps(m)      # performance_context lit encore cette colonne
                n += 1
            counts[ch] = n
        await session.commit()
    return counts


async def analytics(days: int = 28) -> dict:
    """Dernier instantané par (post, canal) sur `days` jours, agrégé par canal,
    format et semaine ISO ; `items` complet (pour les créneaux) et `top` 5."""
    since = datetime.utcnow() - timedelta(days=days)
    async with async_session_factory() as session:
        posts = {p.id: p for p in (await session.execute(
            select(ScheduledPost).where(ScheduledPost.status == "posted")
            .where(ScheduledPost.posted_at >= since))).scalars().all()}
        rows = (await session.execute(
            select(PostMetric).where(PostMetric.post_id.in_(list(posts) or ["-"]))
            .order_by(PostMetric.fetched_at.asc()))).scalars().all()
    latest: dict[tuple[str, str], PostMetric] = {}
    for r in rows:
        latest[(r.post_id, r.channel)] = r          # ordre ascendant : le dernier gagne
    by_ch: dict = {}
    by_fmt: dict = {}
    by_week: dict = {}
    items = []
    for (pid, ch), r in latest.items():
        p = posts[pid]
        m = {"views": r.views, "likes": r.likes, "comments": r.comments, "shares": r.shares, "saves": r.saves}
        e = engagement(m)
        for bucket, key in ((by_ch, ch), (by_fmt, p.format or "post"), (by_week, p.posted_at.strftime("%G-W%V"))):
            b = bucket.setdefault(key, {"posts": 0, "views": 0, "likes": 0, "comments": 0,
                                        "shares": 0, "saves": 0, "engagement": 0})
            b["posts"] += 1
            b["engagement"] += e
            for k, v in m.items():
                b[k] += v
        items.append({"id": pid, "title": p.title, "channel": ch, "format": p.format,
                      "posted_at": p.posted_at.isoformat() + "Z", **m, "engagement": e})
    items.sort(key=lambda d: d["engagement"], reverse=True)
    return {"days": days, "channels": by_ch, "formats": by_fmt,
            "weeks": [{"week": w, **v} for w, v in sorted(by_week.items())],
            "items": items, "top": items[:5], "quotas": quota.summary(), "notes": NOTES}
```

- [ ] **Étape 5 : fetchers et boucle** — dans `marketing.py`, après
  `_fetch_x_metrics_sync` :

```python
def _x_norm(m: dict) -> dict:
    return {"views": int(m.get("impression_count", 0)), "likes": int(m.get("like_count", 0)),
            "comments": int(m.get("reply_count", 0)), "shares": int(m.get("retweet_count", 0)), "saves": 0}


async def _fetch_x_metrics(ids: list[str]) -> dict[str, dict]:
    raw = await asyncio.to_thread(_fetch_x_metrics_sync, ids)
    return {k: _x_norm(v) for k, v in raw.items()}


metrics_service.FETCHERS["x"] = _fetch_x_metrics
```

  (import `from app.services import metrics_service` en tête). Dans chaque
  adaptateur, sous `publishers.register(...)` : `metrics_service.FETCHERS["youtube"] = fetch_stats`
  (resp. `["instagram"] = fetch_insights`, `["tiktok"] = fetch_stats`) avec
  `from app.services import metrics_service` en tête du module. Dans
  `schedule_loop`, remplacer l.861-866 par :

```python
                try:
                    n = await metrics_service.refresh_all(max_per_channel=10)
                    if n:
                        logger.info(f"metrics refreshed: {n}")
                except Exception as e:
                    logger.warning(f"metrics pass failed: {e}")
```

  et supprimer `refresh_x_metrics` (l.616-640, plus aucun appelant —
  `grep -rn refresh_x_metrics backend/` doit rendre 0 ligne).
- [ ] **Étape 6 : routes** — après `/schedule/{post_id}/preview.png` :

```python
@router.get("/schedule/analytics")
async def schedule_analytics(days: int = 28):
    from app.services import metrics_service as _ms
    return await _ms.analytics(max(1, min(365, days)))


@router.get("/schedule/quotas")
async def schedule_quotas():
    from app.services import quota as _q
    return _q.summary()


@router.post("/schedule/analytics/refresh")
async def schedule_analytics_refresh():
    """Passe manuelle, rationnée comme la quotidienne (X : 10 posts)."""
    from app.services import metrics_service as _ms
    return await _ms.refresh_all(max_per_channel=10)
```

  **Attention à l'ordre** : `/schedule/analytics` et `/schedule/quotas`
  doivent être déclarés AVANT `GET /schedule/{post_id}/…` ? Non : les routes
  `/schedule/{post_id}` existantes sont `PATCH`/`DELETE`/`POST …/fire`/`GET …/preview.png`
  — aucun `GET /schedule/{post_id}` nu ; l'ordre est libre. Le banc le prouve.
- [ ] **Étape 7 : vert** — `python tests/test_scheduler_metrics.py` → `SCHEDULER METRICS: PASS` ;
  `python tests/test_scheduler_youtube.py`, `…_instagram.py`, `…_tiktok.py` → PASS.
- [ ] **Étape 8 : commit**

```bash
git add backend/app/services/metrics_service.py backend/app/services/marketing.py backend/app/services/youtube_publisher.py backend/app/services/instagram_publisher.py backend/app/services/tiktok_publisher.py backend/app/api/routes.py backend/tests/test_scheduler_metrics.py
git commit -m 'scheduler : metriques par canal et tableau de bord' -m 'Table post_metrics alimentée par un fetcher par canal (X rationné à 10 posts par passe, Telegram dit sans métriques), agrégats par canal, format et semaine ISO, top et quotas ; passe quotidienne de la boucle et passe manuelle.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 8 : créneaux par canal et horaire proposé (P3)

**Files :**
- Create : `backend/app/services/schedule_slots.py`
- Modify : `backend/app/api/routes.py` (`/marketing/plan` l.4286-4295 + 3 routes)
- Test : `backend/tests/test_scheduler_slots.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Créneaux par canal (P3) : défauts, sauvegarde bornée (HH:MM, canaux connus),
affectation k-ième post du jour → k-ième créneau du PREMIER canal, proposition
d'après les métriques (≥ 5 posts par canal, sinon None).
Run (depuis backend/) : python tests/test_scheduler_slots.py"""
import json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.services import schedule_slots as SL          # noqa: E402

SL._FILE = pathlib.Path(tempfile.mkdtemp(), "slots.json")
assert SL.load()["x"] == ["08:30", "13:00", "19:30"] and SL.tz_offset() == 0
saved = SL.save({"x": ["25:00", "07:00", "07:00"], "tiktok": ["20:15"], "bidon": ["10:00"], "_tz": -120})
assert saved["x"] == ["07:00"] and saved["tiktok"] == ["20:15"] and "bidon" not in saved
assert saved["youtube"] == ["09:30", "19:00"] and SL.tz_offset() == -120
assert "bidon" not in json.loads(SL._FILE.read_text("utf-8"))
posts = [{"day_offset": 0, "channels": ["x"]}, {"day_offset": 0, "channels": ["x", "telegram"]},
         {"day_offset": 1, "channels": ["youtube"]}, {"day_offset": 0, "channels": ["x"]}]
SL.assign(posts, {"x": ["07:00", "12:00"], "youtube": ["09:30"]})
assert [p["time"] for p in posts] == ["07:00", "12:00", "09:30", "07:00"]
items = ([{"channel": "x", "posted_at": "2026-09-01T17:00:00Z", "engagement": 50}] * 3
         + [{"channel": "x", "posted_at": "2026-09-02T06:10:00Z", "engagement": 5}] * 3
         + [{"channel": "youtube", "posted_at": "2026-09-01T08:00:00Z", "engagement": 9}] * 2)
sug = SL.suggest(items, tz_offset_minutes=-120)
assert sug == {"x": "19:00", "youtube": None}, sug
print("SCHEDULER SLOTS: PASS")
```

- [ ] **Étape 2 : rouge** — `python tests/test_scheduler_slots.py` → `ModuleNotFoundError`.
- [ ] **Étape 3 : `schedule_slots.py`**

```python
"""Créneaux par canal (P3) : heures LOCALES par réseau dans
DATA_ROOT/scheduler/slots.json ({"_tz": getTimezoneOffset du navigateur, "x": [...]}).
Défauts = ceux du skill deepotus-comms (account-config.md) ; TikTok de mémoire."""
import json
import re
from datetime import datetime, timedelta

from app.config import DATA_ROOT

DEFAULTS = {"x": ["08:30", "13:00", "19:30"], "telegram": ["10:00", "18:00"],
            "instagram": ["12:30", "18:30"], "youtube": ["09:30", "19:00"], "tiktok": ["12:00", "19:00"]}
_FILE = DATA_ROOT / "scheduler" / "slots.json"
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _raw() -> dict:
    try:
        return json.loads(_FILE.read_text("utf-8")) or {}
    except (OSError, ValueError):
        return {}


def _clean(d: dict) -> dict:
    out = {}
    for ch, hs in (d or {}).items():
        if ch in DEFAULTS and isinstance(hs, list):
            hs = sorted({h for h in hs if isinstance(h, str) and _HHMM.match(h)})
            if hs:
                out[ch] = hs
    try:
        out["_tz"] = int(d.get("_tz", 0))
    except (TypeError, ValueError):
        out["_tz"] = 0
    return out


def load() -> dict[str, list[str]]:
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in _clean(_raw()).items() if k != "_tz"})
    return merged


def tz_offset() -> int:
    return _clean(_raw())["_tz"]


def save(d: dict) -> dict[str, list[str]]:
    clean = _clean(d)
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(clean, indent=1), "utf-8")
    tmp.replace(_FILE)
    return load()


def assign(posts: list[dict], slots: dict | None = None) -> list[dict]:
    """k-ième post du jour sur son PREMIER canal → k-ième créneau (modulo)."""
    slots = slots or load()
    seen: dict = {}
    for p in posts:
        ch = (p.get("channels") or ["x"])[0]
        hs = slots.get(ch) or DEFAULTS["x"]
        key = (p.get("day_offset", 0), ch)
        k = seen.get(key, 0)
        seen[key] = k + 1
        p["time"] = hs[k % len(hs)]
    return posts


def suggest(items: list[dict], tz_offset_minutes: int = 0, min_posts: int = 5) -> dict:
    """Par canal : demi-heure LOCALE au meilleur engagement MOYEN si ≥ min_posts
    posts mesurés, sinon None (les défauts restent)."""
    buckets: dict = {}
    for it in items:
        try:
            t = datetime.fromisoformat(str(it["posted_at"]).replace("Z", "")) - timedelta(minutes=tz_offset_minutes)
        except (KeyError, ValueError):
            continue
        hh = f"{t.hour:02d}:{'30' if t.minute >= 30 else '00'}"
        b = buckets.setdefault(it.get("channel", "x"), {}).setdefault(hh, [0, 0])
        b[0] += int(it.get("engagement", 0))
        b[1] += 1
    out = {}
    for ch, hs in buckets.items():
        n = sum(c for _s, c in hs.values())
        out[ch] = None if n < min_posts else max(hs.items(), key=lambda kv: kv[1][0] / kv[1][1])[0]
    return out
```

- [ ] **Étape 4 : routes et plan** — après `/schedule/analytics/refresh` :

```python
@router.get("/schedule/slots")
async def get_slots():
    from app.services import schedule_slots as _sl
    return _sl.load()


@router.put("/schedule/slots")
async def put_slots(body: dict):
    from app.services import schedule_slots as _sl
    return _sl.save(body or {})


@router.get("/schedule/slots/suggest")
async def suggest_slots(days: int = 56, tz_offset_minutes: int = 0):
    from app.services import metrics_service as _ms, schedule_slots as _sl
    a = await _ms.analytics(max(1, min(365, days)))
    return {"suggested": _sl.suggest(a["items"], tz_offset_minutes), "slots": _sl.load()}
```

  Dans `marketing_plan` (routes l.4293, après `plan = await marketing.generate_plan(...)`) :

```python
    if body.get("use_slots", True):
        from app.services import schedule_slots as _sl
        _sl.assign(plan["posts"])
```

- [ ] **Étape 5 : vert** — `python tests/test_scheduler_slots.py` → `SCHEDULER SLOTS: PASS`.
- [ ] **Étape 6 : commit**

```bash
git add backend/app/services/schedule_slots.py backend/app/api/routes.py backend/tests/test_scheduler_slots.py
git commit -m 'scheduler : creneaux par canal et horaire propose par les metriques' -m 'slots.json sous DATA_ROOT (défauts du skill deepotus-comms), affectation des heures du plan par canal, proposition d horaire quand cinq posts au moins sont mesurés.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 9 : aperçus Reels, Shorts, TikTok avec zones sûres (P4)

**Files :**
- Modify : `backend/app/services/post_preview.py` (après `_render_telegram` l.267, `render_preview` l.270)
- Test : `backend/tests/test_scheduler_preview.py`

- [ ] **Étape 1 : banc (rouge)** — miroir : on lit les PIXELS du PNG.

```python
"""Aperçus verticaux (P4) : 540×960, rail droit et bande basse ASSOMBRIS sur le
visuel (zones d'interface), légende dans la bande ; x et telegram inchangés ;
la route sert le PNG pour channel=tiktok.
Run (depuis backend/) : python tests/test_scheduler_preview.py"""
import asyncio, io, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image                                  # noqa: E402
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.IMAGES_FOLDER = os.environ["IMAGES_FOLDER"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import post_preview as PP           # noqa: E402

hero = pathlib.Path(_tmp, "images", "hero.png")
Image.new("RGB", (1080, 1920), (240, 240, 240)).save(hero)


def lum(im, x, y):
    r, g, b = im.getpixel((x, y))[:3]
    return (r + g + b) / 3


for ch in ("instagram", "youtube", "tiktok"):
    im = Image.open(io.BytesIO(PP.render_preview(channel=ch, caption="Salut 🐙 légende", hero_path=str(hero))))
    W, H = im.size
    assert (W, H) == (540, 960), (ch, im.size)
    z = PP.SAFE_ZONES[ch]
    assert lum(im, W - 8, H // 2) < lum(im, W // 2, H // 2) - 40, ch          # rail droit assombri
    assert lum(im, 8, H - 8) < lum(im, W // 2, H // 2) - 40, ch               # bande basse assombrie
    assert lum(im, W // 2, int(H * (z["top"] + z["bottom"])) ) > 200, ch       # cœur du visuel intact
assert Image.open(io.BytesIO(PP.render_preview(channel="x", caption="x", hero_path=str(hero)))).size[0] == 680


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/api/schedule", json={"title": "t", "caption": "c", "channels": ["tiktok"],
                                                "run_at": "2026-09-10T10:00:00Z", "source_image": "hero.png"})
        r = await c.get(f"/api/schedule/{r.json()['id']}/preview.png", params={"channel": "tiktok"})
        assert r.status_code == 200 and Image.open(io.BytesIO(r.content)).size == (540, 960)
    print("SCHEDULER PREVIEW: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge** — `python tests/test_scheduler_preview.py` → `AttributeError: … has no attribute 'SAFE_ZONES'`.
- [ ] **Étape 3 : rendu vertical** — dans `post_preview.py`, après `_render_telegram` :

```python
# Zones d'interface des lecteurs verticaux, en fraction du cadre 9:16 (de
# mémoire, 03/09/2026 — à corriger sur des captures d'un vrai téléphone).
SAFE_ZONES = {
    "instagram": {"top": 0.06, "bottom": 0.17, "right": 0.12, "label": "Reels"},
    "youtube": {"top": 0.07, "bottom": 0.15, "right": 0.12, "label": "Shorts"},
    "tiktok": {"top": 0.08, "bottom": 0.20, "right": 0.14, "label": "TikTok"},
}
CANVAS = (540, 960)


def _cover(im, w, h):
    iw, ih = im.size
    s = max(w / iw, h / ih)
    im = im.resize((max(1, int(iw * s)), max(1, int(ih * s))), Image.LANCZOS)
    x, y = (im.size[0] - w) // 2, (im.size[1] - h) // 2
    return im.crop((x, y, x + w, y + h))


def _render_vertical(caption, hero_path, handle, network):
    W, H = CANVAS
    z = SAFE_ZONES[network]
    hero = None
    if hero_path and Path(hero_path).is_file():
        try:
            hero = _cover(Image.open(hero_path).convert("RGBA"), W, H)
        except Exception:
            hero = None
    img = hero or _placeholder(W, H, "Aucun visuel — rendu 9:16 attendu")
    top, bot, right = int(H * z["top"]), int(H * z["bottom"]), int(W * z["right"])
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([0, 0, W, top], fill=(0, 0, 0, 130))
    d.rectangle([0, H - bot, W, H], fill=(0, 0, 0, 160))
    d.rectangle([W - right, top, W, H - bot], fill=(0, 0, 0, 130))
    for y in range(0, H, 18):                      # hachures = masqué par l'interface
        d.line([(W - right, y), (W, y + 18)], fill=(244, 33, 46, 90), width=1)
    img = Image.alpha_composite(img, ov)
    d = ImageDraw.Draw(img)
    f_name, f_cap, f_small = _bold(20), _regular(19), _regular(14)
    ef = _emoji(19)
    white = (255, 255, 255, 255)
    d.text((16, 12), f"{z['label']} · zones sûres · {len(caption or '')} car.", font=f_small, fill=white)
    d.text((16, H - bot + 12), f"@{handle}", font=f_name, fill=white)
    y = H - bot + 42
    for ln in _wrap(caption or "", f_cap, ef, 19, W - right - 32)[:3]:
        _draw_line(d, 16, y, ln, f_cap, ef, white, 19)
        y += 26
    return img
```

  Dans `render_preview`, avant le `else` final :

```python
    elif ch in SAFE_ZONES:
        img = _render_vertical(caption or "", hero_path, handle, ch)
```

- [ ] **Étape 4 : vert** — `python tests/test_scheduler_preview.py` → `SCHEDULER PREVIEW: PASS`.
- [ ] **Étape 5 : commit**

```bash
git add backend/app/services/post_preview.py backend/tests/test_scheduler_preview.py
git commit -m 'scheduler : apercus Reels, Shorts et TikTok a zones sures' -m 'Rendu vertical 540×960 par Pillow : rail droit, bande haute et bande basse assombris et hachurés, légende dans la bande ; fractions dites de mémoire, à corriger sur captures réelles ; le banc lit les pixels.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 10 : validation par lot (P5) et `tick()` de la boucle

**Files :**
- Modify : `backend/app/api/routes.py` (`_post_to_dict` l.3924, `PATCH` l.4009-4047, nouvelle route), `backend/app/services/marketing.py` (`schedule_loop` l.849-896)
- Test : `backend/tests/test_scheduler_validate.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Validation par lot (P5) : la fenêtre passe scheduled+auto+validated_at, un
post sans média est ignoré ET nommé ; un contenu modifié après validation
revient en attente (draft/assisted) ; un changement de statut seul ne casse
pas la validation ; un tick de boucle publie le lot dû sur le canal factice.
Run (depuis backend/) : python tests/test_scheduler_validate.py"""
import asyncio, os, pathlib, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import marketing, publishers, quota  # noqa: E402
from app.services.publishers import PublishResult     # noqa: E402

quota._FILE = pathlib.Path(_tmp, "quota.json")
SENT = []
publishers.register("fakenet", lambda: True,
                    lambda cap, v, i, m: _ok(cap))


async def _ok(cap):
    SENT.append(cap)
    return PublishResult(True, "fakenet: ok", "r1")


async def main():
    await init_db()
    soon = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
    past = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        mk = lambda **k: c.post("/api/schedule", json={"channels": ["fakenet"], **k})
        a = (await mk(title="A", caption="a", run_at=soon, source_image="s.png")).json()["id"]
        b = (await mk(title="B", caption="b", run_at=past, job_id="job-x")).json()["id"]
        n = (await mk(title="Nu", caption="rien", run_at=soon)).json()["id"]
        far = (await mk(title="Loin", caption="l", run_at="2030-01-01T10:00:00Z", source_image="s.png")).json()["id"]
        lo = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
        r = await c.post("/api/schedule/validate", json={"from": lo})
        assert set(r.json()["validated"]) == {a, b} and r.json()["skipped"] == [
            {"id": n, "title": "Nu", "reason": "sans média"}], r.json()
        rows = {p["id"]: p for p in (await c.get("/api/schedule")).json()}
        assert rows[a]["mode"] == "auto" and rows[a]["status"] == "scheduled" and rows[a]["validated_at"]
        assert rows[far]["validated_at"] is None and rows[n]["status"] == "draft"
        r = await c.patch(f"/api/schedule/{a}", json={"caption": "a modifiée"})
        assert r.json()["status"] == "draft" and r.json()["mode"] == "assisted" and r.json()["validated_at"] is None
        r = await c.patch(f"/api/schedule/{b}", json={"status": "scheduled"})
        assert r.json()["validated_at"] and r.json()["mode"] == "auto"
        await marketing.tick()
        rows = {p["id"]: p for p in (await c.get("/api/schedule")).json()}
        assert rows[b]["status"] == "posted" and SENT == ["b"], rows[b]
        assert rows[a]["status"] == "draft"
    print("SCHEDULER VALIDATE: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge** — `python tests/test_scheduler_validate.py` → `KeyError: 'validated'` (404 sur la route).
- [ ] **Étape 3 : route et PATCH** — après `DELETE /schedule/{post_id}` :

```python
@router.post("/schedule/validate")
async def validate_lot(body: dict):
    """P5 — valide un LOT : les posts draft/scheduled de la fenêtre [from, to]
    (UTC ISO ; défaut = maintenant → +7 j) ou du plan_id passent scheduled +
    auto + validated_at. Un post SANS média (ni job_id ni source_image) est
    ignoré et nommé : l'automatique n'envoie pas de texte nu."""
    body = body or {}
    try:
        lo = _dt.fromisoformat(str(body["from"]).replace("Z", "")) if body.get("from") else _dt.utcnow()
        hi = _dt.fromisoformat(str(body["to"]).replace("Z", "")) if body.get("to") else lo + _td(days=7)
    except ValueError:
        raise HTTPException(400, "from/to : ISO UTC attendu")
    plan_id = body.get("plan_id")
    validated, skipped = [], []
    async with async_session_factory() as session:
        q = _select(ScheduledPost).where(ScheduledPost.status.in_(("draft", "scheduled")))
        q = (q.where(ScheduledPost.plan_id == plan_id) if plan_id
             else q.where(ScheduledPost.run_at >= lo).where(ScheduledPost.run_at <= hi))
        for p in (await session.execute(q)).scalars().all():
            if not (p.job_id or p.source_image):
                skipped.append({"id": p.id, "title": p.title, "reason": "sans média"})
                continue
            p.status, p.mode, p.validated_at = "scheduled", "auto", _dt.utcnow()
            validated.append(p.id)
        await session.commit()
    return {"validated": validated, "skipped": skipped}
```

  Dans `update_scheduled_post`, juste avant `await session.commit()` :

```python
        # P5 : un contenu modifié après validation revient en attente.
        if p.validated_at and any(k in body for k in
                                  ("title", "caption", "channels", "run_at", "job_id", "source_image", "brief")):
            p.validated_at, p.mode, p.status = None, "assisted", "draft"
```

  `_post_to_dict` : ajouter `"validated_at": (p.validated_at.isoformat() + "Z") if p.validated_at else None,`
  `"thread_of": p.thread_of, "thread_index": p.thread_index, "series_id": p.series_id,`
  `"recycled_from": p.recycled_from, "published_by": p.published_by,`.
- [ ] **Étape 4 : `tick()`** — dans `marketing.py`, extraire le corps du
  `try` de `schedule_loop` (l.857-891) dans `async def tick(last_metrics_day: list[str | None]) -> None`
  (la date du dernier passage vit dans `last_metrics_day[0]`), et la boucle devient :

```python
async def schedule_loop() -> None:
    """Fire due posts every 60 s. Robust: one bad post can't kill the loop."""
    logger.info("schedule loop started (60s tick)")
    marker: list[str | None] = [None]
    while True:
        try:
            await tick(marker)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"schedule loop tick failed: {e}")
        await asyncio.sleep(60)
```

  La signature de `tick` doit accepter l'appel nu du banc
  (`await marketing.tick()`) ; son en-tête et sa première ligne s'écrivent donc :

```python
async def tick(marker: list[str | None] | None = None) -> None:
    """Un tour de boucle, appelable par un banc. `marker[0]` porte la date de
    la dernière passe de métriques (jour UTC) d'un tour à l'autre."""
    marker = marker if marker is not None else [None]
```

  et, juste après la ligne qui remplit la liste `due` des posts dus, poser
  exactement (préparation de T15 : un fil part dans l'ordre de ses index) :

```python
        due.sort(key=lambda p: (p.thread_index or 0, p.run_at))
```
- [ ] **Étape 5 : vert** — `python tests/test_scheduler_validate.py` → `SCHEDULER VALIDATE: PASS` ;
  `python tests/test_plan_brief.py` → PASS.
- [ ] **Étape 6 : commit**

```bash
git add backend/app/api/routes.py backend/app/services/marketing.py backend/tests/test_scheduler_validate.py
git commit -m 'scheduler : validation par lot et tick de boucle testable' -m 'POST /schedule/validate passe la fenêtre en scheduled/auto/validated_at et nomme les posts sans média ; un contenu modifié après validation revient en attente ; la boucle appelle tick(), que le banc appelle aussi.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 11 : patcher bundle `scheduler` (lot 1)

**Files :**
- Create : `scripts/patch_bundle_scheduler.py`, `backend/tests/test_scheduler_bundle.py`
- Modify : `frontend/dist/assets/index-BEOJX8L5.js` (par le patcher, jamais à la main)

> Les cinq ancres, les deux deltas et les comptes de sondes de cette tâche ont
> été **mesurés le 03/09/2026** par une répétition à blanc sur une COPIE du
> bundle (hors dépôt) : chaque ancre est à 1 occurrence, `node --check` sort 0
> sur le résultat, `delta = +8458 caractères / +8459 octets`. Les nombres
> ci-dessous ne sont pas des estimations.

- [ ] **Étape 1 : relever la chaîne (aucune écriture)**

Run : `python scripts/repatch_all.py --list`
Attendu : la liste des maillons détectés par mtime, le dernier nommé en queue
(mesuré le 03/09 dans ce worktree : `seedance25`, 28/08 18:14). Écrire ce nom
dans la ligne `BASELINE :` du docstring du patcher (étape 4). Si la liste est
vide, écrire `BASELINE : bundle du dépôt (aucun .bak local)`.

- [ ] **Étape 2 : écrire le banc-miroir (rouge)**

Créer `backend/tests/test_scheduler_bundle.py` :

```python
"""Miroir du bundle APRÈS le patcher `scheduler` (lot 1) : on lit le bundle
écrit, jamais le patcher qui prétend l'écrire. Les comptes sont ceux mesurés
le 03/09/2026 par la répétition à blanc.
Run (depuis backend/) : python tests/test_scheduler_bundle.py"""
import pathlib
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = pathlib.Path(__file__).resolve().parents[2]
B = R / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
s = B.read_text("utf-8")

# le marqueur : l'hôte du panneau, créé une fois, relu une fois
assert s.count("__dzSchedHost") == 2, s.count("__dzSchedHost")
# la fabrique de panneau : définie une fois, appelée par les quatre panneaux
assert s.count("__dzSchedPanel") == 5, s.count("__dzSchedPanel")
# chaque panneau : sa définition et l'appel du bouton d'en-tête
for f in ("__dzSchedComptes", "__dzSchedValider", "__dzSchedCreneaux",
          "__dzSchedAnalytics"):
    assert s.count(f) == 2, (f, s.count(f))
# les routes du lot 1, écrites telles quelles
for u in ('"/schedule/validate"', '"/schedule/slots"', '"/schedule/quotas"',
          '"/schedule/analytics?days=28"', '"/schedule/analytics/refresh"',
          '"/schedule/slots/suggest?tz_offset_minutes="',
          '"/oauth/tiktok/exchange"', '"/api/oauth/youtube/start"'):
    assert u in s, u
# TikTok entre dans la table des canaux, la carte d'icônes et Settings
assert s.count("channelTiktok") == 3, s.count("channelTiktok")
assert 'tiktok:{id:"tiktok"' in s
assert '"TIKTOK_REFRESH_TOKEN"].every(setk)' in s
# l'amont de la chaîne est intact (libsend, libprov, libpicker, spritelab)
assert s.count("__dzSendSched") == 3 and s.count("__dzSendMenu") == 3
assert s.count("__dzToast") == 10, s.count("__dzToast")   # 7 avant + 3 posés
assert s.count("__dzLibPicker") == 10 and s.count("__dzSrcChips") == 2
assert s.count("__dzToSpriteLab") == 5
# le patcher porte ses gardes
p = (R / "scripts" / "patch_bundle_scheduler.py").read_text("utf-8")
for g in ("guard_downstream", "STABLE_PROBES", "SPEC_CHAR_DELTA",
          "POST_COUNTS", "node --check"):
    assert g in p, g
print("SCHEDULER BUNDLE: PASS")
```

- [ ] **Étape 3 : rouge**

Run (depuis `backend/`) : `python tests/test_scheduler_bundle.py`
Attendu : `AssertionError: 0` (le compte de `__dzSchedHost`).

- [ ] **Étape 4 : écrire le patcher — en-tête, constantes, helpers**

Créer `scripts/patch_bundle_scheduler.py`. Première moitié, complète :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_scheduler.py
"""Patcher assert-garde : ecran Scheduler — comptes, validation par lot,
creneaux, analytics (lot 1) ; campagne, series, recyclage et fils (lot 2).

BASELINE : bundle POST-patch <nom releve a l'etape 1 de la Tache 11>.
Backup dedie : `.js.bak_scheduler`. Position : EN QUEUE.
Spec : docs/superpowers/plans/2026-09-03-plan-scheduler.md

Tout le neuf est du DOM pur greffe au module (patron `__dzSendMenu` de
libsend, qui vit dans la meme portee) : aucune dependance React, aucun
composant recompile. Le JSX n'est touche que par des DONNEES — une entree de
plus dans la table des canaux `_t`, une icone de plus dans la carte
d'icones, une carte de plus dans la liste `chans` de Settings — et par une
rangee de boutons dans l'en-tete du Scheduler. Les boutons de connexion
(OAuth YouTube, code TikTok) vivent dans le panneau DOM « Comptes », pas
dans le JSX : c'est ce qui ramene le cout de 9 ancres estimees a 5 mesurees.

Une icone inconnue rend `null` (composant X du bundle) : un `icon:` absent
de la carte n'est pas une panne, le libelle reste seul.

DANGERS : jamais `repatch_all.py --from` sur cette chaine ; lancement SEUL ;
newline='' partout (le bundle est en CRLF) ; jamais d'ancre imprimee
(cp1252 en console Windows). Validation finale : copie .mjs + `node --check`.

Run :
    python scripts/patch_bundle_scheduler.py            # depot
    python scripts/patch_bundle_scheduler.py --check    # n'ecrit rien
    python scripts/patch_bundle_scheduler.py --deltas   # affiche les deltas
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "scheduler"
MARKER = "__dzSchedHost"
MARKER_ATTENDU = 2      # l'ancien hote retire + l'hote pose

# comptes releves sur le bundle du depot le 03/09/2026
STABLE_PROBES = [
    ("libsend-sched", "__dzSendSched", 3),
    ("libsend-menu", "__dzSendMenu", 3),
    ("libsend-toast", "__dzToast", 7),
    ("libpicker", "__dzLibPicker", 10),
    ("libprov", "__dzSrcChips", 2),
    ("spritelab", "__dzToSpriteLab", 5),
]

# comptes attendus APRES application (verification post-ecriture)
POST_COUNTS = [
    ("__dzSchedPanel", 5),
    ("__dzSchedComptes", 2),
    ("__dzSchedValider", 2),
    ("__dzSchedCreneaux", 2),
    ("__dzSchedAnalytics", 2),
    ("channelTiktok", 3),
    ("__dzToast", 10),
    ("__dzSendSched", 3),
    ("__dzLibPicker", 10),
    ("__dzToSpriteLab", 5),
]

SPEC_CHAR_DELTA = 8458
SPEC_BYTE_DELTA = 8459

# ── S1 : helpers module (inseres AVANT `function __dzSendSched`) ─────────────
# Tout est en \\u.... : les helpers restent ASCII pur (7414 car = 7414 o), ce
# qui met les accents a l'abri d'une console ou d'un editeur en cp1252.
HELPERS = (
    "function __dzSchedApi(m,u,b){var o={method:m,"
    'headers:{"Content-Type":"application/json"}};'
    "if(b)o.body=JSON.stringify(b);"
    'return fetch("/api"+u,o).then(function(r){'
    "return r.json().then(function(j){"
    "if(!r.ok)throw new Error((j&&j.detail)||r.status);return j})})}"

    "function __dzSchedPanel(titre){"
    'try{var old=document.getElementById("__dzSchedHost");'
    "if(old)old.remove()}catch(e){}"
    'var h=document.createElement("div");h.id="__dzSchedHost";'
    'h.style.cssText="position:fixed;inset:0;'
    "background:rgba(4,6,10,.55);z-index:9500;display:flex;"
    'align-items:center;justify-content:center";'
    'var c=document.createElement("div");'
    'c.style.cssText="min-width:340px;max-width:min(760px,94vw);'
    "max-height:84vh;overflow:auto;background:var(--bg-panel,#13171c);"
    "border:1px solid var(--stroke,#20262d);border-radius:12px;"
    "padding:14px;box-shadow:0 18px 60px rgba(0,0,0,.55);"
    'color:var(--ink,#cfd6dd);font-size:12.5px";'
    'var t=document.createElement("div");t.textContent=titre;'
    't.style.cssText="font-size:13.5px;font-weight:600;'
    'color:var(--ink-strong,#eef2f6);padding:2px 2px 10px";'
    "c.appendChild(t);"
    'var body=document.createElement("div");c.appendChild(body);'
    'var a=document.createElement("button");a.textContent="Fermer";'
    'a.style.cssText="display:block;width:100%;text-align:center;'
    "background:transparent;border:1px solid var(--stroke,#20262d);"
    "border-radius:8px;color:var(--ink-soft,#8b959f);padding:7px 10px;"
    'margin-top:12px;font-size:12px;cursor:pointer";'
    "a.onclick=function(){h.remove()};c.appendChild(a);"
    'h.addEventListener("click",function(e){if(e.target===h)h.remove()});'
    "h.appendChild(c);document.body.appendChild(h);return body}"

    "function __dzSchedBtn(lbl,fn){"
    'var b=document.createElement("button");b.textContent=lbl;'
    'b.style.cssText="background:var(--bg-panel-2,#171c22);'
    "border:1px solid var(--stroke,#20262d);border-radius:7px;"
    "color:var(--ink,#cfd6dd);padding:6px 11px;font-size:12px;"
    'cursor:pointer;margin:0 6px 6px 0";'
    "b.onclick=fn;return b}"

    "function __dzSchedOut(){"
    'var o=document.createElement("pre");'
    'o.style.cssText="white-space:pre-wrap;font-size:11.5px;'
    'margin:10px 0 0;opacity:.9";return o}'

    "function __dzSchedComptes(){"
    'var d=__dzSchedPanel("Comptes de publication");'
    'var i=document.createElement("div");'
    'i.style.cssText="opacity:.78;padding-bottom:10px;line-height:1.5";'
    'i.textContent="YouTube passe par le consentement Google (fen\\u00eatre '
    "loopback). TikTok exige une redirection HTTPS : colle le code lu sur ta "
    "page de redirection. Sans audit TikTok, l'envoi automatique est "
    'PRIV\\u00c9 (SELF_ONLY).";d.appendChild(i);'
    "var o=__dzSchedOut();"
    'd.appendChild(__dzSchedBtn("Connecter YouTube",function(){'
    'window.open("/api/oauth/youtube/start","_blank")}));'
    'd.appendChild(__dzSchedBtn("Coller le code TikTok",function(){'
    'var code=window.prompt("Code OAuth TikTok");if(!code)return;'
    '__dzSchedApi("POST","/oauth/tiktok/exchange",{code:code})'
    '.then(function(){__dzToast("TikTok connect\\u00e9")})'
    '.catch(function(e){o.textContent="TikTok : "+e.message})}));'
    "d.appendChild(o);"
    '__dzSchedApi("GET","/schedule/quotas").then(function(j){'
    "var L=[];for(var k in j)L.push(k+' : '+j[k].used+'/'+j[k].limit+"
    "' par '+(j[k].period==='month'?'mois':'jour')+' \\u2014 '+j[k].source);"
    'o.textContent=L.join("\\n")})'
    '.catch(function(e){o.textContent="Quotas injoignables : "+e.message})}'

    "function __dzSchedValider(){"
    'var d=__dzSchedPanel("Valider le lot de la semaine");'
    'var i=document.createElement("div");'
    'i.style.cssText="opacity:.78;padding-bottom:10px;line-height:1.5";'
    'i.textContent="Les brouillons et posts programm\\u00e9s des 7 prochains '
    "jours passent en automatique. Un post SANS m\\u00e9dia est laiss\\u00e9 "
    "de c\\u00f4t\\u00e9 et nomm\\u00e9 : l'automatique n'envoie pas de texte "
    'nu.";d.appendChild(i);var o=__dzSchedOut();'
    'd.appendChild(__dzSchedBtn("Valider les 7 jours",function(){'
    "var lo=new Date(),hi=new Date(Date.now()+7*864e5);"
    '__dzSchedApi("POST","/schedule/validate",'
    "{from:lo.toISOString(),to:hi.toISOString()}).then(function(j){"
    "var L=[((j.validated||[]).length)+' post(s) valid\\u00e9s'];"
    "(j.skipped||[]).forEach(function(s){"
    "L.push('laiss\\u00e9 de c\\u00f4t\\u00e9 : '+s.title+' ('+s.reason+')')});"
    'o.textContent=L.join("\\n");'
    '__dzToast("Lot valid\\u00e9 \\u2014 rouvre la semaine pour voir les '
    '\\u00e9tats")})'
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}));'
    "d.appendChild(o)}"

    "function __dzSchedCreneaux(){"
    'var d=__dzSchedPanel("Cr\\u00e9neaux par canal");'
    "var tzo=(new Date()).getTimezoneOffset();"
    'var box=document.createElement("div");d.appendChild(box);'
    "var o=__dzSchedOut();d.appendChild(o);"
    '__dzSchedApi("GET","/schedule/slots").then(function(j){'
    "var champs={};Object.keys(j).forEach(function(ch){"
    'var r=document.createElement("div");'
    'r.style.cssText="display:flex;gap:8px;align-items:center;padding:3px 0";'
    'var l=document.createElement("span");l.textContent=ch;'
    'l.style.cssText="width:92px;opacity:.8";'
    'var f=document.createElement("input");f.value=(j[ch]||[]).join(", ");'
    'f.style.cssText="flex:1;background:var(--bg-base,#0b0e12);'
    "border:1px solid var(--stroke,#20262d);border-radius:6px;"
    'color:var(--ink,#cfd6dd);padding:5px 8px;font-size:12px";'
    "champs[ch]=f;r.appendChild(l);r.appendChild(f);box.appendChild(r)});"
    'var s=document.createElement("div");s.style.cssText="padding-top:10px";'
    "box.appendChild(s);"
    's.appendChild(__dzSchedBtn("Enregistrer",function(){'
    "var b={_tz:tzo};Object.keys(champs).forEach(function(ch){"
    'b[ch]=champs[ch].value.split(",").map(function(x){return x.trim()})'
    ".filter(Boolean)});"
    '__dzSchedApi("PUT","/schedule/slots",b).then(function(j2){'
    "Object.keys(champs).forEach(function(ch){"
    'champs[ch].value=(j2[ch]||[]).join(", ")});'
    '__dzToast("Cr\\u00e9neaux enregistr\\u00e9s")})'
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}));'
    's.appendChild(__dzSchedBtn("Proposer d\'apr\\u00e8s mes m\\u00e9triques",'
    "function(){"
    '__dzSchedApi("GET","/schedule/slots/suggest?tz_offset_minutes="+tzo)'
    ".then(function(j3){var L=[];"
    "Object.keys(j3.suggested||{}).forEach(function(ch){"
    "L.push(ch+' : '+(j3.suggested[ch]||"
    "'pas assez de posts mesur\\u00e9s (5 minimum)'))});"
    'o.textContent=L.join("\\n")||"aucune m\\u00e9trique"})'
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}))})'
    '.catch(function(e){box.textContent="Cr\\u00e9neaux injoignables : "'
    "+e.message})}"

    "function __dzSchedAnalytics(){"
    'var d=__dzSchedPanel("Analytics \\u2014 28 jours");'
    "var o=__dzSchedOut();"
    "var charger=function(){o.textContent='Lecture\\u2026';"
    '__dzSchedApi("GET","/schedule/analytics?days=28").then(function(j){'
    "var L=['Par canal :'];"
    "Object.keys(j.channels||{}).forEach(function(ch){var b=j.channels[ch];"
    "L.push('  '+ch+' \\u2014 '+b.posts+' post(s), '+b.views+' vues, '"
    "+b.likes+' likes, engagement '+b.engagement)});"
    "L.push('Par format :');"
    "Object.keys(j.formats||{}).forEach(function(f){var b=j.formats[f];"
    "L.push('  '+f+' \\u2014 '+b.posts+' post(s), engagement '+b.engagement)});"
    "L.push('Par semaine :');"
    "(j.weeks||[]).forEach(function(w){L.push('  '+w.week+' \\u2014 '"
    "+w.posts+' post(s), '+w.views+' vues, engagement '+w.engagement)});"
    "L.push('Top 5 :');"
    "(j.top||[]).forEach(function(it){L.push('  '+it.channel+' \\u00b7 '"
    "+it.title+' \\u2014 engagement '+it.engagement)});"
    "L.push('Bornes :');"
    "Object.keys(j.notes||{}).forEach(function(k){"
    "L.push('  '+k+' : '+j.notes[k])});"
    'o.textContent=L.join("\\n")})'
    '.catch(function(e){o.textContent="Analytics injoignable : "+e.message})};'
    'd.appendChild(__dzSchedBtn("Rafra\\u00eechir maintenant",function(){'
    "o.textContent='Lecture en cours\\u2026';"
    '__dzSchedApi("POST","/schedule/analytics/refresh")'
    ".then(charger).catch(function(e){"
    'o.textContent="\\u00c9chec : "+e.message})}));'
    "d.appendChild(o);charger()}"
)
```

- [ ] **Étape 5 : écrire le patcher — ancres, PATCHES, machinerie**

Suite du même fichier :

```python
# ── les cinq ancres, chacune a 1 occurrence (mesure du 03/09/2026) ───────────
_A1 = "function __dzSendSched"
_A2 = 'limit:2200}},Bu=Object.values(_t)'
_A3 = ('r.jsx("circle",{cx:"17.5",cy:"6.5",r:"1",fill:"currentColor",'
       'stroke:"none"})]})};function X(')
_A4 = 'connected:["IG_ACCESS_TOKEN","IG_BUSINESS_ID"].every(setk)}];'
_A5 = 'children:"New post"})]})}'

TIKTOK_CANAL = (
    'limit:2200},tiktok:{id:"tiktok",label:"TikTok",icon:"channelTiktok",'
    'color:"#22d3ee",bg:"#0c2a2f",limit:2200}},Bu=Object.values(_t)')

TIKTOK_ICONE = (
    'r.jsx("circle",{cx:"17.5",cy:"6.5",r:"1",fill:"currentColor",'
    'stroke:"none"})]}),channelTiktok:r.jsx("path",{fill:"currentColor",'
    'd:"M14 3h2.6c.3 1.9 1.5 3.4 3.4 3.7v2.7c-1.3 0-2.5-.4-3.5-1.1v5.6c0 '
    '3.1-2.5 5.6-5.6 5.6S5.3 17 5.3 13.9s2.5-5.6 5.6-5.6c.3 0 .6 0 .9.1v2.8'
    'c-.3-.1-.6-.2-.9-.2-1.6 0-2.8 1.3-2.8 2.9s1.3 2.9 2.8 2.9 2.9-1.3 '
    '2.9-2.9V3z"})};function X(')

TIKTOK_SETTINGS = (
    'connected:["IG_ACCESS_TOKEN","IG_BUSINESS_ID"].every(setk)},'
    '{id:"tiktok",label:"TikTok",icon:"channelTiktok",color:"#22d3ee",'
    'desc:"Direct Post ; sans audit, les envois sont prives (SELF_ONLY).",'
    'connected:["TIKTOK_CLIENT_KEY","TIKTOK_CLIENT_SECRET",'
    '"TIKTOK_REFRESH_TOKEN"].every(setk)}];')

BOUTONS = (
    'children:"New post"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"cog",'
    "onClick:function(){__dzSchedComptes()},"
    'children:"Comptes"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"check",'
    "onClick:function(){__dzSchedValider()},"
    'children:"Valider la semaine"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"clock",'
    "onClick:function(){__dzSchedCreneaux()},"
    'children:"Créneaux"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"signal",'
    "onClick:function(){__dzSchedAnalytics()},"
    'children:"Analytics"})]})}'
)

PATCHES = [
    ("S1-helpers", _A1, HELPERS + _A1),
    ("S2-canal-tiktok", _A2, TIKTOK_CANAL),
    ("S3-icone-tiktok", _A3, TIKTOK_ICONE),
    ("S4-settings-tiktok", _A4, TIKTOK_SETTINGS),
    ("S5-entete", _A5, BOUTONS),
]


def deltas():
    dc = sum(len(rp) - len(a) for _t, a, rp in PATCHES)
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, rp in PATCHES)
    return dc, db


def check_spec_parity():
    dc, db = deltas()
    if (dc, db) != (SPEC_CHAR_DELTA, SPEC_BYTE_DELTA):
        raise SystemExit(
            f"[{TAG}] parite spec rompue : delta calcule {dc} car / {db} o, "
            f"spec {SPEC_CHAR_DELTA} car / {SPEC_BYTE_DELTA} o. Aborting.")
    return dc, db
```

Puis **recopier textuellement**, depuis `scripts/patch_bundle_libsend.py`
l.280-425, les fonctions `guard_downstream`, `ensure_tail_order`, `apply`,
`read_src`, `eol_stats`, `resolve_root`, `main`, et le bloc final
`if __name__ == "__main__": main()`. Elles ne dépendent que des constantes
définies ci-dessus (`TAG`, `MARKER`, `MARKER_ATTENDU`, `REL_BUNDLE`,
`PATCHES`, `STABLE_PROBES`, `POST_COUNTS`) — aucune adaptation, **sauf** les
deux `print` de fin de `main()`, à remplacer par :

```python
    print("OK - bundle patche (Scheduler : Comptes, Valider la semaine, "
          "Creneaux, Analytics ; TikTok dans les canaux et Settings).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis DEPLOYER le bundle")
```

- [ ] **Étape 6 : vérifier les deltas et l'applicabilité, sans rien écrire**

Run : `python scripts/patch_bundle_scheduler.py --deltas`
Attendu : `[scheduler] delta +8458 car / +8459 o`.
Si un autre nombre sort, une chaîne a été retouchée : corriger la chaîne, PAS
la constante — la constante est la mesure de référence.

Run : `python scripts/patch_bundle_scheduler.py --check`
Attendu, trois lignes :
```
[scheduler] applicable sur <...>index-BEOJX8L5.js
[scheduler] 5 ancres OK, marqueur absent, 6 sondes aux comptes
[scheduler] CRLF=<n> LF-isole=0 CR-isole=0 ; delta +8458 car / +8459 o
```

- [ ] **Étape 7 : appliquer**

Run : `python scripts/patch_bundle_scheduler.py`
Attendu :
```
backup -> index-BEOJX8L5.js.bak_scheduler
OK - bundle patche (Scheduler : Comptes, Valider la semaine, Creneaux, Analytics ; TikTok dans les canaux et Settings).
   taille : <n> -> <n+8459> o (+8459)
   suite  : copie .mjs + node --check, puis DEPLOYER le bundle
```
(La ligne « mtime du backup pousse en queue de chaine » peut précéder : c'est
`ensure_tail_order` qui remet `scheduler` en queue. C'est normal.)

- [ ] **Étape 8 : `node --check` sur une copie**

Run (depuis la racine du dépôt) :
```bash
cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dz-scheduler.mjs && node --check /tmp/dz-scheduler.mjs && echo NODE-OK
```
Attendu : `NODE-OK` seul (aucune sortie de node). Mesuré le 03/09 sur la
répétition à blanc : code de retour 0.

- [ ] **Étape 9 : vert**

Run (depuis `backend/`) : `python tests/test_scheduler_bundle.py`
Attendu : `SCHEDULER BUNDLE: PASS`.

`test_library_sendto.py` est, lui, un fichier **pytest** (il date de la chaîne
libsend) : le lancer comme tel pour prouver que l'amont n'a pas bougé.
Run : `python -m pytest tests/test_library_sendto.py -q`
Attendu : `3 passed`.

- [ ] **Étape 10 : commit**

```bash
git add scripts/patch_bundle_scheduler.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_scheduler_bundle.py
git commit -m 'scheduler : patcher du bundle - comptes, validation par lot, creneaux, analytics' -m 'Cinq ancres mesurées à une occurrence, helpers DOM purs greffés avant __dzSendSched (patron libsend), TikTok dans la table des canaux, la carte d icônes et Settings, rangée de quatre boutons dans l en-tête ; delta +8458 car / +8459 o, node --check vert, banc-miroir sur le bundle écrit.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — différenciant

R6 D1 (part backend seulement : **le téléphone publie** est planifié par R12,
pas ici), D2 (brief de campagne + séries + fils), D3 (recyclage proposé).

### Tâche 12 : le lot validé, exportable (D1 — part backend)

**Ce que ce plan livre, et ce qu'il ne livre pas.** R12 porte l'appairage, le
jeton d'appareil, l'écoute LAN, la publication depuis le téléphone et les
notifications. Ici, le backend expose **deux routes et rien d'autre** : le lot
validé lisible d'un coup (vidéos, légendes, heures) et le retour d'état. Aucun
jeton ne transite : les clés voyagent par l'archive chiffrée (R11 D1 / R12 P2).

**Files :**
- Modify : `backend/app/api/routes.py` (après `POST /schedule/validate`), `backend/app/services/marketing.py` (`_job_video_path` réutilisé)
- Test : `backend/tests/test_scheduler_lot.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Lot exportable (D1, part backend) : seuls les posts VALIDÉS de la fenêtre
sortent, chacun avec son média (URL locale, taille, sha256) ; le retour d'état
du compagnon fond le résultat, compte le quota et refuse d'écraser un post que
le PC a déjà publié. Banc-miroir : on relit la base par l'API et le fichier sur
le disque. Run (depuis backend/) : python tests/test_scheduler_lot.py"""
import asyncio, hashlib, os, pathlib, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import quota                        # noqa: E402

quota._FILE = pathlib.Path(_tmp, "quota.json")
IMG = settings.images_path
IMG.mkdir(parents=True, exist_ok=True)
(IMG / "lot.png").write_bytes(b"PNG-de-banc" * 40)
SHA = hashlib.sha256((IMG / "lot.png").read_bytes()).hexdigest()


async def main():
    await init_db()
    soon = (datetime.utcnow() + timedelta(hours=3)).isoformat() + "Z"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        a = (await c.post("/api/schedule", json={
            "title": "Avec média", "caption": "légende A", "channels": ["x", "telegram"],
            "run_at": soon, "source_image": "lot.png",
            "brief": {"tg_caption": "version Telegram", "hashtags": "#Deepotus"}})).json()["id"]
        b = (await c.post("/api/schedule", json={
            "title": "Sans média", "caption": "légende B", "channels": ["x"],
            "run_at": soon})).json()["id"]
        lo = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"
        v = (await c.post("/api/schedule/validate", json={"from": lo})).json()
        assert v["validated"] == [a] and v["skipped"][0]["id"] == b, v
        lot = (await c.get("/api/schedule/lot?days=7")).json()
        assert [p["id"] for p in lot["posts"]] == [a], lot
        p = lot["posts"][0]
        assert p["caption"] == "légende A" and p["tg_caption"] == "version Telegram"
        assert p["channels"] == ["x", "telegram"] and p["run_at"].endswith("Z")
        assert p["media"] == {"kind": "image", "url": "/api/images/lot.png",
                              "filename": "lot.png", "bytes": len(b"PNG-de-banc" * 40),
                              "sha256": SHA}, p["media"]
        assert p["preview"] == f"/api/schedule/{a}/preview.png"
        assert lot["quotas"]["x"]["limit"] == 500 and "tiktok" in lot["notes"]
        # le compagnon publie, puis rapporte
        r = await c.post(f"/api/schedule/{a}/report", json={
            "status": "posted", "published_by": "iPhone d'Olivier",
            "remote_ids": {"x": "1900", "telegram": "42"}})
        assert r.json()["ok"] is True, r.json()
        row = [q for q in (await c.get("/api/schedule")).json() if q["id"] == a][0]
        assert row["status"] == "posted" and row["published_by"] == "iPhone d'Olivier"
        assert row["remote_ids"] == {"x": "1900", "telegram": "42"} and row["x_post_id"] == "1900"
        assert quota.used("x") == 1, quota.used("x")   # le plafond est partagé
        # un second rapport d'un AUTRE appareil ne réécrit rien
        r = await c.post(f"/api/schedule/{a}/report", json={
            "status": "posted", "published_by": "Pixel", "remote_ids": {"x": "9999"}})
        assert r.status_code == 409, r.status_code
        row = [q for q in (await c.get("/api/schedule")).json() if q["id"] == a][0]
        assert row["remote_ids"]["x"] == "1900" and quota.used("x") == 1
        # un échec rapporté rend le post reprenable par le PC, jamais « failed »
        r = await c.post(f"/api/schedule/{b}/report", json={
            "status": "failed", "published_by": "iPhone d'Olivier", "error": "hors réseau"})
        row = [q for q in (await c.get("/api/schedule")).json() if q["id"] == b][0]
        assert row["status"] == "ready" and "hors réseau" in row["error"]
        assert (await c.post("/api/schedule/inconnu/report", json={"status": "posted"})).status_code == 404
    print("SCHEDULER LOT: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge**

Run (depuis `backend/`) : `python tests/test_scheduler_lot.py`
Attendu : `KeyError: 'posts'` (404 sur `/schedule/lot`).

- [ ] **Étape 3 : les deux routes**

Dans `routes.py`, après `POST /schedule/validate` :

```python
def _sha256_size(p: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with open(p, "rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


@router.get("/schedule/lot")
async def export_lot(days: int = 7):
    """D1 (part backend) — le lot VALIDÉ, prêt à partir sur le compagnon :
    vidéos, légendes, heures, plafonds. Le transport (appairage, jeton,
    LAN) et la publication sont planifiés par R12, pas ici. AUCUN jeton ne
    sort par cette route : les clés voyagent par l'archive chiffrée."""
    from app.services import marketing as _mk, quota as _q
    from app.services.metrics_service import NOTES as _NOTES
    hi = _dt.utcnow() + _td(days=max(1, min(31, days)))
    posts = []
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost)
            .where(ScheduledPost.status == "scheduled")
            .where(ScheduledPost.mode == "auto")
            .where(ScheduledPost.validated_at.isnot(None))
            .where(ScheduledPost.run_at <= hi)
            .order_by(ScheduledPost.run_at.asc()))
        rows = list(res.scalars().all())
    for p in rows:
        brief = {}
        if p.brief:
            try:
                brief = json.loads(p.brief) or {}
            except (ValueError, TypeError):
                brief = {}
        media = None
        video = await _mk._job_video_path(p.job_id)
        if video and Path(video).is_file():
            sha, n = await asyncio.to_thread(_sha256_size, Path(video))
            media = {"kind": "video", "url": f"/api/jobs/{p.job_id}/video",
                     "filename": Path(video).name, "bytes": n, "sha256": sha}
        else:
            img = await _mk._resolve_post_image(p)
            if img and Path(img).is_file():
                sha, n = await asyncio.to_thread(_sha256_size, Path(img))
                media = {"kind": "image",
                         "url": f"/api/images/{Path(img).name}",
                         "filename": Path(img).name, "bytes": n, "sha256": sha}
        posts.append({
            "id": p.id, "title": p.title, "caption": p.caption,
            "tg_caption": brief.get("tg_caption"),
            "hashtags": brief.get("hashtags"), "links": brief.get("links"),
            "channels": [c for c in (p.channels or "").split(",") if c],
            "run_at": p.run_at.isoformat() + "Z", "format": p.format,
            "media": media, "preview": f"/api/schedule/{p.id}/preview.png"})
    return {"generated_at": _dt.utcnow().isoformat() + "Z",
            "posts": posts, "quotas": _q.summary(),
            "notes": {**_NOTES,
                      "tiktok": ("sans audit, l'envoi automatique est privé "
                                 "(SELF_ONLY) — le public passe par le "
                                 "partage natif du téléphone")}}


@router.post("/schedule/{post_id}/report")
async def report_post(post_id: str, body: dict):
    """Retour d'état du compagnon (R12 P3) : « j'ai publié » ou « j'ai
    échoué ». Idempotent et non destructif — un post déjà publié par un
    AUTRE porteur est un 409, jamais un écrasement ; un échec rend le post
    reprenable par le PC (`ready`), jamais définitivement `failed`."""
    from app.services import quota as _q
    body = body or {}
    status = str(body.get("status") or "").strip()
    if status not in ("posted", "failed"):
        raise HTTPException(400, "status : 'posted' ou 'failed' attendu")
    who = str(body.get("published_by") or "compagnon")[:40]
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.id == post_id))
        p = res.scalar_one_or_none()
        if p is None:
            raise HTTPException(404, "post inconnu")
        if p.status == "posted" and (p.published_by or "") != who:
            raise HTTPException(409, f"déjà publié par « {p.published_by or 'ce PC'} »")
        if status == "failed":
            p.status = "ready"
            p.error = str(body.get("error") or "échec rapporté par le compagnon")[:500]
            p.published_by = who
            await session.commit()
            return {"ok": False, "status": p.status}
        remote = {}
        if p.remote_ids:
            try:
                remote = json.loads(p.remote_ids) or {}
            except (ValueError, TypeError):
                remote = {}
        neufs = {str(k): str(v) for k, v in (body.get("remote_ids") or {}).items()
                 if k not in remote}
        remote.update(neufs)
        for ch in neufs:
            _q.count(ch)              # le plafond du réseau est partagé (R12)
        p.remote_ids = json.dumps(remote)
        if remote.get("x"):
            p.x_post_id = remote["x"]
        p.status = "posted"
        p.published_by = who
        p.posted_at = _dt.utcnow()
        p.error = None
        await session.commit()
        return {"ok": True, "status": p.status, "counted": sorted(neufs)}
```

En tête de `routes.py`, ajouter `import hashlib` s'il n'y est pas
(`grep -n '^import hashlib' backend/app/api/routes.py` — s'il rend une ligne,
ne rien ajouter).

- [ ] **Étape 4 : vert**

Run : `python tests/test_scheduler_lot.py` → `SCHEDULER LOT: PASS`
Run : `python tests/test_scheduler_validate.py` → `SCHEDULER VALIDATE: PASS`

- [ ] **Étape 5 : commit**

```bash
git add backend/app/api/routes.py backend/tests/test_scheduler_lot.py
git commit -m 'scheduler : lot valide exportable et retour d etat du compagnon' -m 'GET /schedule/lot rend les posts validés avec vidéos, légendes, heures, taille et sha256 des médias, plafonds et bornes ; POST /schedule/{id}/report fond l état rapporté, compte le quota partagé, refuse un second porteur (409) et rend un échec reprenable. Aucun jeton ne sort par ces routes.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 13 : brief de campagne persistant (D2)

**Files :**
- Modify : `backend/app/services/marketing.py` (`generate_plan` l.230-252), `backend/app/api/routes.py` (2 routes)
- Test : `backend/tests/test_scheduler_brief.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Brief de campagne (D2) : un seul actif, relu par le plan ; l'objectif et
les messages entrent dans le prompt, les INTERDITS sortent des légendes et des
hashtags produits — le pool du persona contient #1000x, que le brief interdit.
Run (depuis backend/) : python tests/test_scheduler_brief.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.ANTHROPIC_API_KEY = settings.OPENAI_API_KEY = ""
settings.GEMINI_API_KEY = settings.OLLAMA_MODEL = ""   # plan déterministe
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import marketing                    # noqa: E402


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/api/marketing/brief")).json() is None
        r = await c.put("/api/marketing/brief", json={
            "name": "Mint de septembre", "objective": "faire connaître le mint",
            "start_date": "2026-09-05", "end_date": "2026-09-30",
            "messages": "le mint ouvre le 12\nles missions donnent des places",
            "forbidden": "#1000x\ngaranti", "rubrics": "lundi : coulisses\nvendredi : démo"})
        assert r.json()["name"] == "Mint de septembre" and r.json()["active"] == 1
        b = await marketing.active_brief()
        assert b["forbidden"] == ["#1000x", "garanti"] and b["rubrics"][0] == "lundi : coulisses"
        ctx = marketing.brief_context(b)
        assert "faire connaître le mint" in ctx and "#1000x" in ctx and "2026-09-30" in ctx
        posts, retires = marketing.apply_forbidden(
            [{"caption": "gain garanti #Deepotus #1000x", "hashtags": "#1000x #SOL"},
             {"caption": "rien à retirer", "hashtags": "#SOL"}], b["forbidden"])
        assert posts[0]["caption"] == "gain #Deepotus" and posts[0]["hashtags"] == "#SOL"
        assert posts[1]["caption"] == "rien à retirer"
        assert sorted(retires) == ["#1000x", "garanti"], retires
        plan = (await c.post("/api/marketing/plan", json={
            "prompt": "semaine de lancement", "days": 2, "posts_per_day": 1,
            "channels": ["x"]})).json()
        assert plan["engine"] == "deterministic" and plan["campaign_brief"] == "Mint de septembre"
        for p in plan["posts"]:
            assert "#1000x" not in (p.get("caption") or "") + (p.get("hashtags") or "")
        # le brief remplacé reste unique : un seul actif
        await c.put("/api/marketing/brief", json={"name": "Octobre", "objective": "suite"})
        b2 = await marketing.active_brief()
        assert b2["name"] == "Octobre" and b2["forbidden"] == []
    print("SCHEDULER BRIEF: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge**

Run : `python tests/test_scheduler_brief.py`
Attendu : `AttributeError: module 'app.services.marketing' has no attribute 'active_brief'`
(précédé d'un 404 sur `GET /api/marketing/brief` — l'assertion `is None` du
banc échoue d'abord : `AssertionError`). L'un ou l'autre est le rouge attendu ;
c'est la même absence.

- [ ] **Étape 3 : les trois fonctions de `marketing.py`**

Après `performance_context` (l.669) :

```python
def _lignes(s: str | None) -> list[str]:
    return [x.strip() for x in (s or "").splitlines() if x.strip()]


async def active_brief() -> dict | None:
    """D2 — le brief de campagne actif, ou None. Un seul actif à la fois."""
    async with async_session_factory() as session:
        res = await session.execute(
            select(CampaignBrief).where(CampaignBrief.active == 1)
            .order_by(CampaignBrief.updated_at.desc()).limit(1))
        b = res.scalar_one_or_none()
    if b is None:
        return None
    return {"id": b.id, "name": b.name, "objective": b.objective,
            "start_date": b.start_date, "end_date": b.end_date,
            "messages": _lignes(b.messages), "forbidden": _lignes(b.forbidden),
            "rubrics": _lignes(b.rubrics), "active": b.active,
            "updated_at": b.updated_at.isoformat() + "Z"}


def brief_context(b: dict | None) -> str:
    """Le brief tel qu'il entre dans le prompt du planner. Les interdits sont
    DITS au modèle (il évitera souvent) ET retirés après coup
    (apply_forbidden) : dire ne suffit pas, on mesure la sortie."""
    if not b:
        return ""
    out = [f"Campaign brief « {b['name']} ».", f"Objective: {b['objective']}."]
    if b.get("start_date") or b.get("end_date"):
        out.append(f"Window: {b.get('start_date') or '?'} -> {b.get('end_date') or '?'}.")
    if b.get("messages"):
        out.append("Key messages (weave them in, one per post at most):\n"
                   + "\n".join(f"- {m}" for m in b["messages"]))
    if b.get("rubrics"):
        out.append("Fixed rubrics to honour:\n"
                   + "\n".join(f"- {r}" for r in b["rubrics"]))
    if b.get("forbidden"):
        out.append("NEVER use these words, claims or hashtags: "
                   + ", ".join(b["forbidden"]) + ".")
    return "\n".join(out)


def apply_forbidden(posts: list[dict], forbidden: list[str]) -> tuple[list[dict], list[str]]:
    """Retire les termes interdits des champs de texte du plan, et rend la
    liste de ceux qui ont dû être retirés (le tableau de bord du brief le
    montre : un modèle qui insiste est un signal, pas un détail)."""
    champs = ("caption", "tg_caption", "hook", "title", "hashtags",
              "on_image_text", "cta")
    retires: set[str] = set()
    for p in posts:
        for k in champs:
            v = p.get(k)
            if not isinstance(v, str) or not v:
                continue
            for mot in forbidden:
                if not mot:
                    continue
                pat = re.compile(re.escape(mot), re.IGNORECASE)
                if pat.search(v):
                    retires.add(mot)
                    v = pat.sub("", v)
            p[k] = re.sub(r"\s{2,}", " ", v).strip()
    return posts, sorted(retires)
```

`CampaignBrief` s'importe en tête de `marketing.py`, à la ligne d'import de
`ScheduledPost` : `from app.services.storage import CampaignBrief, ...`.

- [ ] **Étape 4 : `generate_plan` lit le brief**

Dans `generate_plan`, remplacer **tout le corps** après la ligne
`channels = channels or ["x"]` par ceci (le corps entier, sans coupure : les
quatre lignes du milieu — `pref`, `order`, le `if pref` et sa suite — sont
celles d'aujourd'hui, recopiées à l'identique pour qu'il n'y ait rien à
deviner) :

```python
    perf = await performance_context()
    brief = await active_brief()
    morceaux = [prompt, brief_context(brief), perf]
    full_prompt = "\n\n".join(m for m in morceaux if m)
    pref = settings.PLANNER_PROVIDER.strip().lower()
    order = [p for p in _PLAN_PRIORITY if _plan_available(p)]
    if pref and pref in order:
        order = [pref] + [p for p in order if p != pref]
    for engine in order:
        fn = _PLAN_PROVIDERS.get(engine)
        if fn:
            posts = await fn(full_prompt, days, posts_per_day, channels,
                             language, persona)
            if posts is not None:
                posts, retires = apply_forbidden(posts, (brief or {}).get("forbidden") or [])
                return {"posts": posts, "engine": engine,
                        "campaign_brief": (brief or {}).get("name"),
                        "removed": retires}
    posts = _deterministic_plan(prompt, days, posts_per_day, channels,
                                language, persona)
    posts, retires = apply_forbidden(posts, (brief or {}).get("forbidden") or [])
    return {"posts": posts, "engine": "deterministic",
            "campaign_brief": (brief or {}).get("name"), "removed": retires}
```

La clé s'appelle `campaign_brief` et non `brief` : `brief` est déjà le nom de
la colonne JSON d'un POST (`materialize_plan`), et la route rend `{**plan, …}`.

- [ ] **Étape 5 : les deux routes**

Dans `routes.py`, après `/marketing/plan/materialize` :

```python
@router.get("/marketing/brief")
async def get_campaign_brief():
    return await marketing.active_brief()


@router.put("/marketing/brief")
async def put_campaign_brief(body: dict):
    """D2 — remplace le brief actif (un seul à la fois : les précédents
    passent inactifs, ils restent en base pour l'historique)."""
    body = body or {}
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name est requis")
    async with async_session_factory() as session:
        res = await session.execute(
            _select(CampaignBrief).where(CampaignBrief.active == 1))
        for old in res.scalars().all():
            old.active = 0
        b = CampaignBrief(
            id=str(uuid4()), name=name[:120],
            objective=str(body.get("objective") or "")[:4000],
            start_date=(str(body.get("start_date"))[:10] if body.get("start_date") else None),
            end_date=(str(body.get("end_date"))[:10] if body.get("end_date") else None),
            messages=str(body.get("messages") or "")[:4000],
            forbidden=str(body.get("forbidden") or "")[:2000],
            rubrics=str(body.get("rubrics") or "")[:2000],
            active=1, updated_at=_dt.utcnow())
        session.add(b)
        await session.commit()
    return await marketing.active_brief()
```

`CampaignBrief` s'ajoute à la ligne d'import de `ScheduledPost` dans
`routes.py`.

- [ ] **Étape 6 : vert**

Run : `python tests/test_scheduler_brief.py` → `SCHEDULER BRIEF: PASS`
Run : `python tests/test_plan_brief.py` → `PLAN BRIEF TEST: PASS`
Run : `python tests/test_plan_doc_import.py` → PASS

- [ ] **Étape 7 : commit**

```bash
git add backend/app/services/marketing.py backend/app/api/routes.py backend/tests/test_scheduler_brief.py
git commit -m 'scheduler : brief de campagne persistant lu par le plan' -m 'Un brief actif (objectif, fenêtre, messages, rubriques, interdits) entre dans le prompt du planner et ses interdits sont RETIRÉS de la sortie, pas seulement demandés ; le plan rend campaign_brief et la liste des termes retirés.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 14 : séries récurrentes (D2)

**Files :**
- Create : `backend/app/services/series_service.py`
- Modify : `backend/app/api/routes.py` (4 routes)
- Test : `backend/tests/test_scheduler_series.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Séries récurrentes (D2) : une série produit des BROUILLONS aux jours et à
l'heure dits, jamais deux fois le même créneau (rejouer est sans effet), et
le gabarit de légende reçoit la date. Banc-miroir : on relit les posts par
l'API. Run (depuis backend/) : python tests/test_scheduler_series.py"""
import asyncio, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402


async def main():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get("/api/schedule/series")).json() == []
        r = await c.post("/api/schedule/series", json={
            "name": "Coulisses", "weekdays": "0,3", "time": "09:30",
            "channels": ["x", "telegram"], "format": "image",
            "caption_template": "Coulisses du {date} — {weekday}"})
        sid = r.json()["id"]
        assert r.json()["weekdays"] == "0,3" and r.json()["channels"] == ["x", "telegram"]
        # 2026-09-07 est un lundi : 2 semaines -> lundi 07, jeudi 10, lundi 14, jeudi 17
        body = {"weeks": 2, "start_date": "2026-09-07", "tz_offset_minutes": 0}
        r = await c.post(f"/api/schedule/series/{sid}/materialize", json=body)
        assert r.json()["created"] == 4 and r.json()["skipped"] == 0, r.json()
        posts = [p for p in (await c.get("/api/schedule")).json() if p["series_id"] == sid]
        assert len(posts) == 4
        assert sorted(p["run_at"] for p in posts) == [
            "2026-09-07T09:30:00Z", "2026-09-10T09:30:00Z",
            "2026-09-14T09:30:00Z", "2026-09-17T09:30:00Z"]
        assert all(p["status"] == "draft" and p["mode"] == "assisted" for p in posts)
        assert posts[0]["channels"] == ["x", "telegram"] and posts[0]["format"] == "image"
        assert "Coulisses du 2026-09-07 — lundi" in [p["caption"] for p in posts]
        # rejouer ne duplique rien
        r = await c.post(f"/api/schedule/series/{sid}/materialize", json=body)
        assert r.json() == {"created": 0, "skipped": 4}, r.json()
        assert len([p for p in (await c.get("/api/schedule")).json() if p["series_id"] == sid]) == 4
        # supprimer la série ne supprime pas les posts déjà posés
        assert (await c.delete(f"/api/schedule/series/{sid}")).json() == {"deleted": sid}
        assert (await c.get("/api/schedule/series")).json() == []
        assert len([p for p in (await c.get("/api/schedule")).json() if p["series_id"] == sid]) == 4
        assert (await c.post("/api/schedule/series", json={"name": "x", "weekdays": "9"})).status_code == 400
    print("SCHEDULER SERIES: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge**

Run : `python tests/test_scheduler_series.py`
Attendu : `AssertionError` — `GET /api/schedule/series` rend un 404, pas `[]`.

- [ ] **Étape 3 : `series_service.py`**

```python
"""Séries récurrentes (D2) : une série est une règle (jours de semaine, heure
LOCALE, canaux, format, gabarit de légende) qui se MATÉRIALISE en brouillons.
Rien ne part tout seul : les brouillons attendent la validation par lot (P5),
comme tout le reste. Rejouer une matérialisation est sans effet — l'unicité
est (series_id, run_at)."""
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.services.storage import PostSeries, ScheduledPost, async_session_factory

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _weekdays(raw: str) -> list[int]:
    """« 0,3 » -> [0, 3]. Lève ValueError sur un jour hors 0-6 ou vide."""
    out = []
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        n = int(part)                      # ValueError si ce n'est pas un entier
        if not 0 <= n <= 6:
            raise ValueError(f"jour de semaine hors 0-6 : {n}")
        if n not in out:
            out.append(n)
    if not out:
        raise ValueError("weekdays : au moins un jour (0=lundi … 6=dimanche)")
    return sorted(out)


def _hhmm(raw: str) -> tuple[int, int]:
    hh, _, mm = str(raw or "09:30").partition(":")
    h, m = int(hh), int(mm or 0)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"heure invalide : {raw}")
    return h, m


def to_dict(s: PostSeries) -> dict:
    return {"id": s.id, "name": s.name, "weekdays": s.weekdays, "time": s.time,
            "channels": [c for c in (s.channels or "").split(",") if c],
            "format": s.format, "caption_template": s.caption_template,
            "active": s.active,
            "created_at": s.created_at.isoformat() + "Z"}


async def list_series() -> list[dict]:
    async with async_session_factory() as session:
        res = await session.execute(
            select(PostSeries).where(PostSeries.active == 1)
            .order_by(PostSeries.created_at.asc()))
        return [to_dict(s) for s in res.scalars().all()]


async def create(body: dict) -> dict:
    """Lève ValueError sur des jours ou une heure invalides — la route la
    traduit en 400 qui NOMME le champ fautif."""
    days = _weekdays(body.get("weekdays"))
    h, m = _hhmm(body.get("time") or "09:30")
    s = PostSeries(
        id=str(uuid4()), name=str(body.get("name") or "Série")[:120],
        weekdays=",".join(str(d) for d in days), time=f"{h:02d}:{m:02d}",
        channels=",".join(body.get("channels") or ["x"])[:120],
        format=str(body.get("format") or "image")[:20],
        caption_template=str(body.get("caption_template") or "")[:4000],
        active=1, created_at=datetime.utcnow())
    async with async_session_factory() as session:
        session.add(s)
        await session.commit()
    return to_dict(s)


async def delete(series_id: str) -> bool:
    """Désactive la série. Les brouillons déjà posés RESTENT : ils sont du
    contenu, pas une dépendance de la règle."""
    async with async_session_factory() as session:
        res = await session.execute(
            select(PostSeries).where(PostSeries.id == series_id))
        s = res.scalar_one_or_none()
        if s is None:
            return False
        s.active = 0
        await session.commit()
        return True


async def materialize(series_id: str, *, weeks: int = 1, start_date: str,
                      tz_offset_minutes: int = 0) -> dict:
    """Pose les brouillons de `weeks` semaines à partir de start_date (date
    LOCALE, YYYY-MM-DD). utc = local + tz_offset_minutes (JS
    getTimezoneOffset), comme materialize_plan."""
    async with async_session_factory() as session:
        res = await session.execute(
            select(PostSeries).where(PostSeries.id == series_id))
        s = res.scalar_one_or_none()
        if s is None:
            return {"created": 0, "skipped": 0, "error": "série inconnue"}
        days = _weekdays(s.weekdays)
        h, m = _hhmm(s.time)
        base = datetime.fromisoformat(start_date)
        existants = {p.run_at for p in (await session.execute(
            select(ScheduledPost).where(ScheduledPost.series_id == series_id)
        )).scalars().all()}
        created = skipped = 0
        for w in range(max(1, min(52, weeks))):
            lundi = base - timedelta(days=base.weekday()) + timedelta(weeks=w)
            for d in days:
                local = (lundi + timedelta(days=d)).replace(hour=h, minute=m,
                                                            second=0, microsecond=0)
                if local < base.replace(hour=h, minute=m, second=0, microsecond=0):
                    continue                      # avant le départ demandé
                run_at = local + timedelta(minutes=tz_offset_minutes)
                if run_at in existants:
                    skipped += 1
                    continue
                cap = (s.caption_template or "").replace(
                    "{date}", local.strftime("%Y-%m-%d")).replace(
                    "{weekday}", JOURS[local.weekday()]).replace(
                    "{week}", local.strftime("%G-W%V"))
                session.add(ScheduledPost(
                    id=str(uuid4()), title=f"{s.name} — {local.strftime('%Y-%m-%d')}"[:200],
                    caption=cap, channels=s.channels, run_at=run_at,
                    status="draft", mode="assisted", format=s.format,
                    series_id=series_id))
                existants.add(run_at)
                created += 1
        await session.commit()
    return {"created": created, "skipped": skipped}
```

- [ ] **Étape 4 : les quatre routes**

Dans `routes.py`, après `POST /schedule/validate` :

```python
@router.get("/schedule/series")
async def list_post_series():
    from app.services import series_service as _ss
    return await _ss.list_series()


@router.post("/schedule/series")
async def create_post_series(body: dict):
    from app.services import series_service as _ss
    try:
        return await _ss.create(body or {})
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/schedule/series/{series_id}")
async def delete_post_series(series_id: str):
    from app.services import series_service as _ss
    if not await _ss.delete(series_id):
        raise HTTPException(404, "série inconnue")
    return {"deleted": series_id}


@router.post("/schedule/series/{series_id}/materialize")
async def materialize_post_series(series_id: str, body: dict):
    from app.services import series_service as _ss
    body = body or {}
    try:
        res = await _ss.materialize(
            series_id,
            weeks=int(body.get("weeks") or 1),
            start_date=body.get("start_date") or _dt.utcnow().strftime("%Y-%m-%d"),
            tz_offset_minutes=int(body.get("tz_offset_minutes") or 0))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if res.get("error"):
        raise HTTPException(404, res["error"])
    return res
```

**Ordre des routes** : `/schedule/series` doit être déclaré AVANT
`/schedule/{post_id}/…` ? Non — les routes existantes sont
`PATCH /schedule/{post_id}`, `DELETE /schedule/{post_id}`,
`POST /schedule/{post_id}/fire` et `GET /schedule/{post_id}/preview.png` :
`DELETE /schedule/series/{series_id}` a deux segments de plus, il ne peut pas
être avalé par `DELETE /schedule/{post_id}`. Le banc le prouve (la suppression
de série rend `{"deleted": …}`, pas un 404 de post).

- [ ] **Étape 5 : vert**

Run : `python tests/test_scheduler_series.py` → `SCHEDULER SERIES: PASS`
Run : `python tests/test_scheduler_validate.py` → `SCHEDULER VALIDATE: PASS`

- [ ] **Étape 6 : commit**

```bash
git add backend/app/services/series_service.py backend/app/api/routes.py backend/tests/test_scheduler_series.py
git commit -m 'scheduler : series recurrentes materialisees en brouillons' -m 'Une série (jours de semaine, heure locale, canaux, format, gabarit) pose des brouillons ; rejouer est sans effet (unicité series_id + run_at) ; supprimer la règle garde les posts ; un jour hors 0-6 est refusé en le disant.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 15 : fils X (D2)

**Files :**
- Modify : `backend/app/api/routes.py` (1 route), `backend/app/services/marketing.py` (`fire_post`)
- Test : `backend/tests/test_scheduler_threads.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Fils X (D2) : la suite d'un post est un post lié (thread_of, thread_index) ;
elle part en RÉPONSE au message distant du parent ; tant que le parent n'est pas
publié, la suite est REPORTÉE, jamais échouée.
Run (depuis backend/) : python tests/test_scheduler_threads.py"""
import asyncio, os, pathlib, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import init_db              # noqa: E402
from app.services import marketing, publishers, quota  # noqa: E402
from app.services.publishers import PublishResult     # noqa: E402

quota._FILE = pathlib.Path(_tmp, "quota.json")
VUS = []


async def _pub(caption, video, image, meta):
    VUS.append((caption, meta.get("reply_to")))
    return PublishResult(True, "x: ok", "r%d" % len(VUS))

publishers.register("x", lambda: True, _pub)


async def main():
    await init_db()
    past = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        p1 = (await c.post("/api/schedule", json={
            "title": "Tête", "caption": "1/ le début", "channels": ["x"],
            "run_at": past, "source_image": "s.png", "status": "scheduled"})).json()["id"]
        r = await c.post(f"/api/schedule/{p1}/thread", json={"caption": "2/ la suite"})
        p2 = r.json()["id"]
        assert r.json()["thread_of"] == p1 and r.json()["thread_index"] == 1
        assert r.json()["channels"] == ["x"] and r.json()["status"] == "scheduled"
        r = await c.post(f"/api/schedule/{p2}/thread", json={"caption": "3/ la fin"})
        p3 = r.json()["id"]
        assert r.json()["thread_of"] == p1 and r.json()["thread_index"] == 2
        # la suite seule, parent non publié : reportée, pas échouée
        assert (await c.post(f"/api/schedule/{p2}/fire")).json()["status"] == "scheduled"
        assert VUS == []
        rows = {q["id"]: q for q in (await c.get("/api/schedule")).json()}
        assert "attend" in (rows[p2]["error"] or "").lower(), rows[p2]["error"]
        # le fil entier, dans l'ordre
        await c.post(f"/api/schedule/{p1}/fire")
        await c.post(f"/api/schedule/{p2}/fire")
        await c.post(f"/api/schedule/{p3}/fire")
        assert VUS == [("1/ le début", None), ("2/ la suite", "r1"), ("3/ la fin", "r2")], VUS
        rows = {q["id"]: q for q in (await c.get("/api/schedule")).json()}
        assert all(rows[i]["status"] == "posted" for i in (p1, p2, p3))
        assert rows[p3]["error"] is None
        assert (await c.post("/api/schedule/inconnu/thread", json={"caption": "x"})).status_code == 404
    print("SCHEDULER THREADS: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge**

Run : `python tests/test_scheduler_threads.py`
Attendu : `KeyError: 'id'` (404 sur `/schedule/{id}/thread`).

- [ ] **Étape 3 : la route de suite**

Dans `routes.py`, après `POST /schedule/{post_id}/fire` :

```python
@router.post("/schedule/{post_id}/thread")
async def add_thread_post(post_id: str, body: dict):
    """D2 — la SUITE d'un post : un fil X. La racine du fil est le
    `thread_of` du parent s'il en a un, sinon le parent lui-même : un fil
    est plat, jamais un arbre. Le canal est `x` : le fil est un mécanisme
    de X ; les autres réseaux reçoivent des posts séparés."""
    body = body or {}
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.id == post_id))
        parent = res.scalar_one_or_none()
        if parent is None:
            raise HTTPException(404, "post inconnu")
        racine = parent.thread_of or parent.id
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.thread_of == racine))
        idx = max([p.thread_index or 0 for p in res.scalars().all()] + [0]) + 1
        p = ScheduledPost(
            id=str(uuid4()),
            title=f"{(parent.title or 'Fil')[:180]} ({idx + 1})",
            caption=str(body.get("caption") or "")[:4000],
            channels="x", run_at=parent.run_at + _td(minutes=2 * idx),
            status="scheduled", mode=parent.mode, format=parent.format,
            plan_id=parent.plan_id, thread_of=racine, thread_index=idx)
        session.add(p)
        await session.commit()
        return _post_to_dict(p)
```

- [ ] **Étape 4 : `fire_post` répond au parent**

Dans `marketing.py`, dans `fire_post`, juste avant la boucle `for ch in channels`
(après la construction de `meta`) :

```python
            if post.thread_of:
                res_p = await session.execute(
                    select(ScheduledPost)
                    .where(ScheduledPost.thread_of == post.thread_of)
                    .where(ScheduledPost.thread_index == (post.thread_index or 1) - 1))
                amont = res_p.scalar_one_or_none()
                if amont is None and (post.thread_index or 1) == 1:
                    res_p = await session.execute(
                        select(ScheduledPost).where(ScheduledPost.id == post.thread_of))
                    amont = res_p.scalar_one_or_none()
                rid = None
                if amont is not None and amont.remote_ids:
                    try:
                        rid = (json.loads(amont.remote_ids) or {}).get("x")
                    except (ValueError, TypeError):
                        rid = None
                if not rid:
                    # le parent n'est pas encore parti : on REPORTE, on n'échoue pas.
                    post.status = "scheduled"
                    post.run_at = datetime.utcnow() + timedelta(minutes=2)
                    post.error = "fil : attend la publication du message précédent"
                    await session.commit()
                    return {"ok": False, "error": post.error, "status": post.status}
                meta["reply_to"] = rid
```

`timedelta` est déjà importé en tête de `marketing.py`
(`from datetime import datetime, timedelta` — le vérifier :
`grep -n 'from datetime import' backend/app/services/marketing.py`).

- [ ] **Étape 5 : vert**

Run : `python tests/test_scheduler_threads.py` → `SCHEDULER THREADS: PASS`
Run : `python tests/test_scheduler_publish.py` → `SCHEDULER PUBLISH: PASS`
Run : `python tests/test_scheduler_validate.py` → `SCHEDULER VALIDATE: PASS`
(le tri de `tick` par `thread_index` posé en T10 fait partir le fil dans
l'ordre quand la boucle publie plusieurs posts au même tick).

- [ ] **Étape 6 : commit**

```bash
git add backend/app/api/routes.py backend/app/services/marketing.py backend/tests/test_scheduler_threads.py
git commit -m 'scheduler : fils X - une suite repond au message precedent' -m 'POST /schedule/{id}/thread pose un post lié (fil plat, racine unique, canal x) ; fire_post lit l id distant de l amont et le passe en reply_to ; tant que l amont n est pas parti, la suite est reportée de deux minutes et le dit, jamais échouée.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 16 : recyclage proposé (D3)

**Files :**
- Modify : `backend/app/services/marketing.py` (variation de légende), `backend/app/api/routes.py` (2 routes)
- Test : `backend/tests/test_scheduler_recycle.py`

- [ ] **Étape 1 : banc (rouge)**

```python
"""Recyclage proposé (D3) : les posts les mieux mesurés, assez vieux et jamais
recyclés, reviennent en PROPOSITION ; rien ne part sans un POST explicite. La
variation déterministe (sans clé LLM) change la légende et retire les termes
interdits du brief. Run (depuis backend/) : python tests/test_scheduler_recycle.py"""
import asyncio, json, os, pathlib, sys, tempfile
from datetime import datetime, timedelta
from uuid import uuid4
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp()
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import settings                       # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.ANTHROPIC_API_KEY = settings.OPENAI_API_KEY = ""
settings.GEMINI_API_KEY = settings.OLLAMA_MODEL = ""
from httpx import AsyncClient, ASGITransport          # noqa: E402
from app.main import app                              # noqa: E402
from app.services.storage import (PostMetric, ScheduledPost,   # noqa: E402
                                  async_session_factory, init_db)


async def _poser(titre, jours, engagement, image="s.png"):
    pid = str(uuid4())
    quand = datetime.utcnow() - timedelta(days=jours)
    async with async_session_factory() as s:
        s.add(ScheduledPost(id=pid, title=titre, caption=f"{titre} #1000x",
                            channels="x", run_at=quand, status="posted",
                            mode="auto", format="image", posted_at=quand,
                            source_image=image,
                            remote_ids=json.dumps({"x": "r-" + pid[:6]})))
        s.add(PostMetric(id=str(uuid4()), post_id=pid, channel="x",
                         remote_id="r-" + pid[:6], fetched_at=quand,
                         views=1000, likes=engagement, comments=0, shares=0, saves=0))
        await s.commit()
    return pid


async def main():
    await init_db()
    vieux = await _poser("Le meilleur", 40, 90)
    moyen = await _poser("Le moyen", 40, 10)
    frais = await _poser("Trop frais", 3, 500)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.put("/api/marketing/brief", json={"name": "B", "forbidden": "#1000x"})
        r = (await c.get("/api/schedule/recycle/suggest?days=90&limit=5")).json()
        ids = [x["source_id"] for x in r["suggestions"]]
        assert ids == [vieux, moyen], ids           # trop frais : écarté
        top = r["suggestions"][0]
        assert top["engagement"] == 90 and top["age_days"] >= 21
        assert "#1000x" not in top["caption"] and top["caption"] != "Le meilleur #1000x"
        assert top["source_image"] == "s.png" and top["engine"] == "deterministic"
        quand = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
        n = (await c.post("/api/schedule/recycle", json={
            "source_id": vieux, "run_at": quand, "caption": top["caption"]})).json()
        assert n["recycled_from"] == vieux and n["status"] == "draft"
        assert n["source_image"] == "s.png" and n["channels"] == ["x"]
        # une fois recyclé, il ne revient plus dans les propositions
        r2 = (await c.get("/api/schedule/recycle/suggest?days=90&limit=5")).json()
        assert [x["source_id"] for x in r2["suggestions"]] == [moyen]
        assert (await c.post("/api/schedule/recycle", json={
            "source_id": "inconnu", "run_at": quand})).status_code == 404
    print("SCHEDULER RECYCLE: PASS")

asyncio.run(main())
```

- [ ] **Étape 2 : rouge**

Run : `python tests/test_scheduler_recycle.py`
Attendu : `KeyError: 'suggestions'` (404 sur `/schedule/recycle/suggest`).

- [ ] **Étape 3 : la variation de légende**

Dans `marketing.py`, après `apply_forbidden` :

```python
_RELANCES = [
    "On y revient : ", "Rappel : ", "Toujours vrai — ", "À relire : ",
    "Ça méritait un second passage : ",
]


async def vary_caption(caption: str, *, persona: dict | None = None,
                       forbidden: list[str] | None = None) -> tuple[str, str]:
    """D3 — une AUTRE légende pour le même contenu. Avec une clé LLM, on la
    demande ; sans clé, la variation est déterministe (relance choisie par le
    hachage de la légende + une ligne de hashtags du persona, hors interdits)
    — jamais la même chaîne que l'originale. Rend (légende, moteur)."""
    base = (caption or "").strip()
    forbidden = forbidden or []
    order = [p for p in _PLAN_PRIORITY if _plan_available(p)]
    if order:
        prompt = ("Rewrite this social post so it says the same thing with a "
                  "different opening and rhythm. Same language. One or two "
                  "sentences. No hashtags. Answer with the rewrite only.\n\n"
                  + base[:1500])
        try:
            posts = await _PLAN_PROVIDERS[order[0]](prompt, 1, 1, ["x"], "FR", persona)
            neuf = ((posts or [{}])[0].get("caption") or "").strip()
            if neuf and neuf != base:
                out, _r = apply_forbidden([{"caption": neuf}], forbidden)
                return out[0]["caption"], order[0]
        except Exception as e:
            logger.warning(f"vary_caption {order[0]}: {e}")
    corps = base
    for mot in forbidden:
        corps = re.sub(re.escape(mot), "", corps, flags=re.IGNORECASE)
    corps = re.sub(r"\s{2,}", " ", corps).strip()
    relance = _RELANCES[sum(ord(ch) for ch in base) % len(_RELANCES)]
    pool = [h for h in ((persona or {}).get("default_hashtags_pool") or [])
            if not any(f.lower() == h.lower() for f in forbidden)]
    tags = " ".join(pool[:3])
    neuf = (relance + corps + (" " + tags if tags else "")).strip()
    return (neuf if neuf != base else relance + base), "deterministic"
```

- [ ] **Étape 4 : les deux routes**

Dans `routes.py`, après `POST /schedule/validate` :

```python
@router.get("/schedule/recycle/suggest")
async def suggest_recycle(days: int = 90, limit: int = 5,
                          min_age_days: int = 21):
    """D3 — propositions de recyclage : les posts les mieux mesurés (P2),
    publiés il y a au moins `min_age_days`, jamais encore recyclés. Rien
    n'est créé ici : c'est une PROPOSITION, à valider."""
    from app.services import metrics_service as _ms
    a = await _ms.analytics(max(1, min(365, days)))
    brief = await marketing.active_brief()
    interdits = (brief or {}).get("forbidden") or []
    persona = _load_persona()
    limite = _dt.utcnow() - _td(days=max(0, min_age_days))
    deja: set[str] = set()
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.recycled_from.isnot(None)))
        deja = {p.recycled_from for p in res.scalars().all()}
        res = await session.execute(_select(ScheduledPost))
        rows = {p.id: p for p in res.scalars().all()}
    out = []
    vus: set[str] = set()
    for it in a["items"]:                      # déjà trié par engagement
        pid = it["id"]
        p = rows.get(pid)
        if pid in deja or pid in vus or p is None or p.posted_at is None:
            continue
        if p.posted_at > limite:
            continue
        vus.add(pid)
        cap, moteur = await marketing.vary_caption(
            p.caption or p.title or "", persona=persona, forbidden=interdits)
        out.append({"source_id": pid, "title": p.title,
                    "channels": [c for c in (p.channels or "").split(",") if c],
                    "format": p.format, "source_image": p.source_image,
                    "job_id": p.job_id, "engagement": it["engagement"],
                    "views": it["views"],
                    "age_days": (_dt.utcnow() - p.posted_at).days,
                    "caption": cap, "engine": moteur})
        if len(out) >= max(1, min(20, limit)):
            break
    return {"days": days, "min_age_days": min_age_days, "suggestions": out}


@router.post("/schedule/recycle")
async def create_recycled_post(body: dict):
    """Matérialise UNE proposition en brouillon (jamais en `scheduled` :
    le recyclage repasse par la validation par lot, comme le reste)."""
    body = body or {}
    src_id = str(body.get("source_id") or "")
    try:
        run_at = _dt.fromisoformat(str(body.get("run_at") or "").replace("Z", ""))
    except ValueError:
        raise HTTPException(400, f"run_at invalide : {body.get('run_at')}")
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost).where(ScheduledPost.id == src_id))
        src = res.scalar_one_or_none()
        if src is None:
            raise HTTPException(404, "post source inconnu")
        p = ScheduledPost(
            id=str(uuid4()), title=f"{(src.title or 'Post')[:180]} (repost)",
            caption=str(body.get("caption") or src.caption or "")[:4000],
            channels=src.channels, run_at=run_at, status="draft",
            mode="assisted", format=src.format, hook=src.hook,
            script_idea=src.script_idea, image_idea=src.image_idea,
            source_image=src.source_image, job_id=src.job_id,
            brief=src.brief, recycled_from=src.id)
        session.add(p)
        await session.commit()
        return _post_to_dict(p)
```

`_load_persona` est la fonction déjà utilisée par les routes marketing pour
lire `backend/app/personas/deepotus.json` — la retrouver avant d'écrire :
`grep -n 'persona' backend/app/api/routes.py | grep -i 'def\|json'`. Si aucune
fonction ne l'expose, écrire à côté des routes :

```python
def _load_persona() -> dict:
    p = Path(__file__).resolve().parent.parent / "personas" / "deepotus.json"
    try:
        return json.loads(p.read_text("utf-8"))
    except (OSError, ValueError):
        return {}
```

- [ ] **Étape 5 : vert**

Run : `python tests/test_scheduler_recycle.py` → `SCHEDULER RECYCLE: PASS`
Run : `python tests/test_scheduler_metrics.py` → `SCHEDULER METRICS: PASS`
Run : `python tests/test_scheduler_brief.py` → `SCHEDULER BRIEF: PASS`

- [ ] **Étape 6 : commit**

```bash
git add backend/app/services/marketing.py backend/app/api/routes.py backend/tests/test_scheduler_recycle.py
git commit -m 'scheduler : recyclage propose d apres les metriques' -m 'Les posts les mieux mesurés, vieux d au moins trois semaines et jamais recyclés, reviennent en proposition avec une légende variée (LLM si clé, variation déterministe sinon) purgée des interdits du brief ; la matérialisation est un brouillon explicite, jamais un envoi.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

### Tâche 17 : patcher `scheduler` (lot 2) — brief, séries, recyclage, fils

Le patcher n'est **pas** un second fichier : on **étend** `patch_bundle_scheduler.py`
et on le **relance**. `main()` restaure d'abord le bundle depuis `.bak_scheduler`
puis réapplique la liste entière : le résultat est le même que si le lot 2 avait
toujours été là, et la chaîne ne gagne pas un maillon de plus.

> Mesuré le 03/09/2026 sur une COPIE hors dépôt, avec le lot 1 :
> six ancres à 1 occurrence, `node --check` rc 0,
> `delta = +14348 caractères / +14349 octets` au total.

**Files :**
- Modify : `scripts/patch_bundle_scheduler.py`, `backend/tests/test_scheduler_bundle.py`, `frontend/dist/assets/index-BEOJX8L5.js` (par le patcher)

- [ ] **Étape 1 : allonger le banc-miroir (rouge)**

Dans `backend/tests/test_scheduler_bundle.py`, avant la lecture du patcher,
ajouter :

```python
# lot 2 : les trois panneaux de campagne et le bouton de suite de fil
for f in ("__dzSchedBrief", "__dzSchedSeries", "__dzSchedRecycler",
          "__dzSchedCampagne"):
    assert s.count(f) == 2, (f, s.count(f))
for u in ('"/marketing/brief"', '"/schedule/series"',
          '"/schedule/recycle/suggest?days=90&limit=5"', '"/schedule/recycle"',
          '"/schedule/"+e.id+"/thread"'):
    assert u in s, u
assert 'children:"Suite (fil X)"' in s and 'children:"Campagne"' in s
# le menu de libsend est REUTILISE, pas recopie : 3 avant + 1 appel
assert s.count("__dzSendMenu") == 4, s.count("__dzSendMenu")
```

et **corriger** les comptes du lot 1 devenus faux par croissance :

```python
assert s.count("__dzSchedPanel") == 8, s.count("__dzSchedPanel")
assert s.count("__dzToast") == 11, s.count("__dzToast")
```
(les deux lignes remplacent les `== 5` et `== 10` du lot 1 ; le compte de
`__dzSchedHost` reste 2, celui de `channelTiktok` reste 3.)

- [ ] **Étape 2 : rouge**

Run (depuis `backend/`) : `python tests/test_scheduler_bundle.py`
Attendu : `AssertionError: ('__dzSchedBrief', 0)`.

- [ ] **Étape 3 : les quatre helpers de campagne**

Dans `scripts/patch_bundle_scheduler.py`, juste après la constante `HELPERS`,
ajouter `HELPERS2` (elle aussi en `\\u....`, ASCII pur — 5374 car = 5374 o) :

```python
# ── lot 2 : brief, series, recyclage, et le menu qui les rassemble ──────────
HELPERS2 = (
    "function __dzSchedBrief(){"
    'var d=__dzSchedPanel("Brief de campagne");'
    "var champs={};var o=__dzSchedOut();"
    "var lignes=[['name','Nom'],['objective','Objectif'],"
    "['start_date','D\\u00e9but (AAAA-MM-JJ)'],['end_date','Fin (AAAA-MM-JJ)'],"
    "['messages','Messages cl\\u00e9s (un par ligne)'],"
    "['forbidden','Interdits (un par ligne)'],"
    "['rubrics','Rubriques fixes (une par ligne)']];"
    "lignes.forEach(function(L){"
    'var r=document.createElement("div");'
    'r.style.cssText="display:flex;gap:8px;align-items:flex-start;padding:3px 0";'
    'var lab=document.createElement("span");lab.textContent=L[1];'
    'lab.style.cssText="width:190px;opacity:.8;padding-top:5px";'
    "var f=document.createElement("
    "L[0]==='messages'||L[0]==='forbidden'||L[0]==='rubrics'?"
    "'textarea':'input');"
    'f.style.cssText="flex:1;min-height:'
    "\"+(f.tagName==='TEXTAREA'?'62':'0')+\"px;"
    "background:var(--bg-base,#0b0e12);"
    "border:1px solid var(--stroke,#20262d);border-radius:6px;"
    'color:var(--ink,#cfd6dd);padding:5px 8px;font-size:12px";'
    "champs[L[0]]=f;r.appendChild(lab);r.appendChild(f);d.appendChild(r)});"
    '__dzSchedApi("GET","/marketing/brief").then(function(j){'
    "if(!j)return;Object.keys(champs).forEach(function(k){"
    "var v=j[k];if(v&&v.join)v=v.join('\\n');"
    "champs[k].value=v||''})})"
    '.catch(function(){});'
    'd.appendChild(__dzSchedBtn("Enregistrer le brief",function(){'
    "var b={};Object.keys(champs).forEach(function(k){b[k]=champs[k].value});"
    '__dzSchedApi("PUT","/marketing/brief",b).then(function(j){'
    "o.textContent='Brief \\u00ab '+j.name+' \\u00bb enregistr\\u00e9 \\u2014 '"
    "+(j.forbidden||[]).length+' interdit(s), '+(j.rubrics||[]).length"
    "+' rubrique(s). Le prochain plan le lit.'})"
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}));'
    "d.appendChild(o)}"

    "function __dzSchedSeries(){"
    'var d=__dzSchedPanel("S\\u00e9ries r\\u00e9currentes");'
    "var liste=document.createElement('div');d.appendChild(liste);"
    "var o=__dzSchedOut();"
    "var recharger=function(){liste.textContent='';"
    '__dzSchedApi("GET","/schedule/series").then(function(js){'
    "if(!js.length){liste.textContent='Aucune s\\u00e9rie.';return}"
    "js.forEach(function(s){"
    "var r=document.createElement('div');"
    'r.style.cssText="display:flex;gap:8px;align-items:center;'
    'padding:4px 0;border-bottom:1px solid var(--stroke,#20262d)";'
    "var t=document.createElement('span');t.style.cssText='flex:1';"
    "t.textContent=s.name+' \\u2014 jours '+s.weekdays+' \\u00e0 '+s.time"
    "+' sur '+(s.channels||[]).join(', ');r.appendChild(t);"
    'r.appendChild(__dzSchedBtn("Poser 4 semaines",function(){'
    "var dt=new Date();var iso=dt.getFullYear()+'-'"
    "+('0'+(dt.getMonth()+1)).slice(-2)+'-'+('0'+dt.getDate()).slice(-2);"
    '__dzSchedApi("POST","/schedule/series/"+s.id+"/materialize",'
    "{weeks:4,start_date:iso,tz_offset_minutes:dt.getTimezoneOffset()})"
    ".then(function(j){o.textContent=j.created+' brouillon(s) pos\\u00e9(s), '"
    "+j.skipped+' d\\u00e9j\\u00e0 l\\u00e0.'})"
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}));'
    'r.appendChild(__dzSchedBtn("Supprimer",function(){'
    '__dzSchedApi("DELETE","/schedule/series/"+s.id).then(recharger)'
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}));'
    "liste.appendChild(r)})}).catch(function(e){"
    "liste.textContent='S\\u00e9ries injoignables : '+e.message})};"
    'd.appendChild(__dzSchedBtn("Nouvelle s\\u00e9rie",function(){'
    "var nom=window.prompt('Nom de la s\\u00e9rie');if(!nom)return;"
    "var jours=window.prompt('Jours (0=lundi \\u2026 6=dimanche, s\\u00e9par\\u00e9s "
    "par des virgules)','0,3');if(!jours)return;"
    "var heure=window.prompt('Heure locale HH:MM','09:30');if(!heure)return;"
    "var can=window.prompt('Canaux (virgules)','x,telegram')||'x';"
    "var gab=window.prompt('Gabarit de l\\u00e9gende ({date} {weekday} {week})',"
    "'')||'';"
    '__dzSchedApi("POST","/schedule/series",{name:nom,weekdays:jours,'
    "time:heure,channels:can.split(',').map(function(x){return x.trim()})"
    ".filter(Boolean),caption_template:gab}).then(recharger)"
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}));'
    "d.appendChild(o);recharger()}"

    "function __dzSchedRecycler(){"
    'var d=__dzSchedPanel("Recyclage propos\\u00e9");'
    "var liste=document.createElement('div');d.appendChild(liste);"
    "var o=__dzSchedOut();d.appendChild(o);"
    "liste.textContent='Lecture des m\\u00e9triques\\u2026';"
    '__dzSchedApi("GET","/schedule/recycle/suggest?days=90&limit=5")'
    ".then(function(j){liste.textContent='';"
    "if(!(j.suggestions||[]).length){liste.textContent="
    "'Rien \\u00e0 recycler : il faut des posts mesur\\u00e9s de plus de '"
    "+j.min_age_days+' jours.';return}"
    "j.suggestions.forEach(function(s){"
    "var r=document.createElement('div');"
    'r.style.cssText="padding:6px 0;border-bottom:1px solid '
    'var(--stroke,#20262d)";'
    "var t=document.createElement('div');"
    "t.textContent=s.title+' \\u2014 engagement '+s.engagement+', '"
    "+s.age_days+' jours, l\\u00e9gende ('+s.engine+') : '+s.caption;"
    "r.appendChild(t);"
    'r.appendChild(__dzSchedBtn("Proposer demain",function(){'
    "var q=new Date(Date.now()+864e5);"
    '__dzSchedApi("POST","/schedule/recycle",{source_id:s.source_id,'
    "run_at:q.toISOString(),caption:s.caption}).then(function(p){"
    "o.textContent='Brouillon cr\\u00e9\\u00e9 : '+p.title"
    "+' \\u2014 il passe par la validation par lot comme les autres.'})"
    '.catch(function(e){o.textContent="\\u00c9chec : "+e.message})}));'
    "liste.appendChild(r)})})"
    ".catch(function(e){liste.textContent="
    "'Propositions injoignables : '+e.message})}"

    "function __dzSchedCampagne(){__dzSendMenu(["
    '{lbl:"\\u270e Brief de campagne",fn:__dzSchedBrief},'
    '{lbl:"\\u21bb S\\u00e9ries r\\u00e9currentes",fn:__dzSchedSeries},'
    '{lbl:"\\u267b Recyclage propos\\u00e9",fn:__dzSchedRecycler}],'
    '"Campagne\\u2026")}'
)
```

- [ ] **Étape 4 : la sixième ancre et les deux remplacements changés**

Dans le même fichier, ajouter `_A6` sous `_A5`, remplacer `BOUTONS` par la
version à cinq boutons, ajouter `SUITE`, et refaire la liste `PATCHES` :

```python
_A6 = 'onClick:P,children:"Duplicate to next day"})]})]})}'

BOUTONS = (
    'children:"New post"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"cog",'
    "onClick:function(){__dzSchedComptes()},"
    'children:"Comptes"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"check",'
    "onClick:function(){__dzSchedValider()},"
    'children:"Valider la semaine"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"clock",'
    "onClick:function(){__dzSchedCreneaux()},"
    'children:"Créneaux"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"signal",'
    "onClick:function(){__dzSchedAnalytics()},"
    'children:"Analytics"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"book",'
    "onClick:function(){__dzSchedCampagne()},"
    'children:"Campagne"})]})}'
)

SUITE = (
    'onClick:P,children:"Duplicate to next day"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"send",'
    "onClick:function(){__dzSchedApi"
    '("POST","/schedule/"+e.id+"/thread",{caption:""})'
    ".then(function(p){__dzToast"
    '("Suite ajout\\u00e9e \\u2014 \\u00e9cris-la dans l\\u2019inspecteur");'
    'window.dispatchEvent(new CustomEvent("deepotus:select-post",'
    "{detail:{id:p.id}}))})"
    '.catch(function(er){window.alert("Fil : "+String(er&&er.message||er))})},'
    'children:"Suite (fil X)"})]})]})}'
)

PATCHES = [
    ("S1-helpers", _A1, HELPERS + HELPERS2 + _A1),
    ("S2-canal-tiktok", _A2, TIKTOK_CANAL),
    ("S3-icone-tiktok", _A3, TIKTOK_ICONE),
    ("S4-settings-tiktok", _A4, TIKTOK_SETTINGS),
    ("S5-entete", _A5, BOUTONS),
    ("S6-suite-fil", _A6, SUITE),
]
```

`__dzSchedApi` préfixe déjà `/api` : l'URL du fil s'écrit `"/schedule/"+e.id+"/thread"`,
**sans** `/api` (une répétition donnerait `/api/api/schedule/…`, un 404 muet).

Et mettre à jour les constantes de garde du même fichier :

```python
SPEC_CHAR_DELTA = 14348
SPEC_BYTE_DELTA = 14349

POST_COUNTS = [
    ("__dzSchedPanel", 8),
    ("__dzSchedComptes", 2),
    ("__dzSchedValider", 2),
    ("__dzSchedCreneaux", 2),
    ("__dzSchedAnalytics", 2),
    ("__dzSchedBrief", 2),
    ("__dzSchedSeries", 2),
    ("__dzSchedRecycler", 2),
    ("__dzSchedCampagne", 2),
    ("channelTiktok", 3),
    ("__dzToast", 11),
    ("__dzSendMenu", 4),
    ("__dzSendSched", 3),
    ("__dzLibPicker", 10),
    ("__dzToSpriteLab", 5),
]
```

`MARKER`, `MARKER_ATTENDU` (2) et `STABLE_PROBES` ne changent pas : les sondes
se lisent sur le bundle RESTAURÉ depuis `.bak_scheduler`, c'est-à-dire d'avant
le lot 1.

- [ ] **Étape 5 : mesurer, appliquer, vérifier la syntaxe**

Run : `python scripts/patch_bundle_scheduler.py --deltas`
Attendu : `[scheduler] delta +14348 car / +14349 o`

Run : `python scripts/patch_bundle_scheduler.py --check`
Attendu : `[scheduler] 6 ancres OK, marqueur absent, 6 sondes aux comptes`
(« marqueur absent » : `--check` lit `.bak_scheduler`, qui est le bundle
d'avant le lot 1 — c'est ce qui rend la relance sûre.)

Run : `python scripts/patch_bundle_scheduler.py`
Attendu : `restore <- index-BEOJX8L5.js.bak_scheduler` puis
`OK - bundle patche (…)` et `taille : <n> -> <n+14349> o (+14349)`.

Run :
```bash
cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dz-scheduler2.mjs && node --check /tmp/dz-scheduler2.mjs && echo NODE-OK
```
Attendu : `NODE-OK`. (Mesuré le 03/09 sur la répétition à blanc : rc 0.)

- [ ] **Étape 6 : vert**

Run (depuis `backend/`) : `python tests/test_scheduler_bundle.py`
Attendu : `SCHEDULER BUNDLE: PASS`
Run : `python -m pytest tests/test_library_sendto.py -q` → `3 passed`

- [ ] **Étape 7 : commit**

```bash
git add scripts/patch_bundle_scheduler.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_scheduler_bundle.py
git commit -m 'scheduler : bundle lot 2 - brief, series, recyclage et suite de fil' -m 'Le patcher scheduler est étendu et relancé (il restaure son backup et réapplique tout) : trois panneaux de campagne derrière le menu réutilisé de libsend, un bouton Campagne dans l en-tête, un bouton Suite (fil X) dans l inspecteur ; six ancres, delta +14348 car / +14349 o, node --check vert.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

- **E1 — Validation en équipe (rôles, approbations, à la Hootsuite)** : hors
  sujet, l'application a un utilisateur unique (R6, réponse 3 ; R12 réponse 11
  ne nomme que d'autres *appareils* du même propriétaire, jamais d'autres
  personnes).
- **E2 — Analytics de concurrents (à la Metricool)** : hors périmètre ; aucune
  des API des cinq réseaux ne le donne dans les paliers utilisés (R6), et rien
  dans ce plan ne lit un compte qui n'est pas le sien.
- **E3 — Publication automatique TikTok en public sans audit** : impossible par
  l'API — un client non audité impose `SELF_ONLY` et un compte privé
  (developers.tiktok.com, vérifié le 03/09/2026) ; le plan publie donc en privé
  et le **dit** dans le panneau Comptes et dans les notes du lot ; le public
  passe par le partage natif du téléphone, planifié en R12.
- **Postiz comme relais unique** : écarté à la Tâche 0 — mêmes apps
  développeur, mêmes quotas, mais un hôte permanent que R12 (réponses 4 et 6)
  refuse. Gardé en note si un relais permanent revenait un jour.
- **`google-api-python-client`** : écarté à la Tâche 3 — l'envoi résumable
  YouTube tient en deux requêtes `httpx`, déjà dans `backend/requirements.txt`
  l.11. Aucune dépendance nouvelle dans ce plan.

---

## Campagne de mutations

### Tâche 18 : campagne de mutations

Le banc de mutations n'est pas un test : il **casse** les lignes portantes une
à une et vérifie que le banc visé rougit. Une mutation « VERTE » est une
assertion qui manque — c'est le seul verdict qui demande du travail.

**Files :**
- Create : `backend/tests/mutations_scheduler.py`
- Modify : `CHANGELOG.md`

- [ ] **Étape 1 : écrire le lanceur**

Créer `backend/tests/mutations_scheduler.py` :

```python
"""Banc de mutations du Scheduler : casser → rouge → remettre.

PAS UN TEST : son nom ne commence pas par `test_`, ni pytest ni run-tests.ps1
ne le ramassent. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_scheduler.py            # toutes
    python tests/mutations_scheduler.py 3 17       # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près
(assertion sha256), donc il ne se lance pas pendant qu'un autre banc lit ces
fichiers. Les bancs du Scheduler sont des scripts AUTONOMES : le verdict se
lit sur le code de sortie ET sur la ligne « <NOM>: PASS », jamais sur l'un
des deux seuls — un import qui lève sort 1 sans avoir rien mesuré.

Verdicts :
  ROUGE            le banc ne passe plus : la mutation est attrapée.
  ROUGE(syntaxe)   le banc casse à l'IMPORT (SyntaxError / NameError) : rouge
                   faible, la mutation n'a pas été mesurée sur le comportement.
  VERTE            le banc passe encore : une assertion manque. À écrire.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
BACK = R / "backend"

# (fichier relatif au dépôt, ancien, nouveau, banc autonome visé)
M = [
    # ── quota.py : le plafond est une garde, pas une décoration ─────────────
    ("backend/app/services/quota.py",
     "    if n >= lim[1]:",
     "    if n > lim[1]:",
     "tests/test_scheduler_publish.py"),
    ("backend/app/services/quota.py",
     '        return False, f"quota {channel} : {n}/{lim[1]} — {lim[2]}"',
     '        return False, "plafond atteint"',
     "tests/test_scheduler_publish.py"),
    ("backend/app/services/quota.py",
     "    d.setdefault(channel, {})[k] = int(d.get(channel, {}).get(k, 0)) + 1\n    _save(d)",
     "    d.setdefault(channel, {})[k] = int(d.get(channel, {}).get(k, 0)) + 1",
     "tests/test_scheduler_lot.py"),
    # ── publishers.py : avant l'appel, après le succès ──────────────────────
    ("backend/app/services/publishers.py",
     "    ok, msg = quota.check(channel)\n    if not ok:\n        return PublishResult(False, msg)",
     "    ok, msg = quota.check(channel)",
     "tests/test_scheduler_publish.py"),
    ("backend/app/services/publishers.py",
     "    if res.ok:\n        quota.count(channel)",
     "    if not res.ok:\n        quota.count(channel)",
     "tests/test_scheduler_publish.py"),
    ("backend/app/services/publishers.py",
     "    return {ch for ch, (avail, _fn) in _REGISTRY.items() if avail()}",
     "    return set(_REGISTRY)",
     "tests/test_scheduler_publish.py"),
    # ── marketing.py : le rejeu, les ids distants, le fil ───────────────────
    ("backend/app/services/marketing.py",
     '                if ch in remote:      # rejeu après échec partiel : jamais deux fois\n'
     '                    sent.append(f"{ch}: déjà publié ({remote[ch]})")\n'
     "                    continue",
     "                if False:\n"
     '                    sent.append(f"{ch}: déjà publié ({remote[ch]})")\n'
     "                    continue",
     "tests/test_scheduler_publish.py"),
    ("backend/app/services/marketing.py",
     "            post.remote_ids = json.dumps(remote) if remote else None",
     "            pass",
     "tests/test_scheduler_publish.py"),
    ("backend/app/services/marketing.py",
     '                meta["reply_to"] = rid',
     "                pass",
     "tests/test_scheduler_threads.py"),
    ("backend/app/services/marketing.py",
     "                if not rid:",
     "                if False:",
     "tests/test_scheduler_threads.py"),
    ("backend/app/services/marketing.py",
     "        due.sort(key=lambda p: (p.thread_index or 0, p.run_at))",
     "        due.sort(key=lambda p: p.run_at)",
     "tests/test_scheduler_validate.py"),
    # ── metrics_service.py : le budget de lecture et le dernier instantané ──
    ("backend/app/services/metrics_service.py",
     "            pairs = [(p, _remote(p, ch)) for p in posts if _remote(p, ch)][:max_per_channel]",
     "            pairs = [(p, _remote(p, ch)) for p in posts if _remote(p, ch)]",
     "tests/test_scheduler_metrics.py"),
    ("backend/app/services/metrics_service.py",
     "            .order_by(PostMetric.fetched_at.asc()))).scalars().all()",
     "            .order_by(PostMetric.fetched_at.desc()))).scalars().all()",
     "tests/test_scheduler_metrics.py"),
    ("backend/app/services/metrics_service.py",
     "    return (int(m.get(\"likes\", 0)) + 2 * int(m.get(\"comments\", 0))\n"
     "            + 3 * int(m.get(\"shares\", 0)) + 2 * int(m.get(\"saves\", 0)))",
     "    return int(m.get(\"likes\", 0))",
     "tests/test_scheduler_metrics.py"),
    # ── schedule_slots.py : le format, la rotation, le seuil ────────────────
    ("backend/app/services/schedule_slots.py",
     '_HHMM = re.compile(r"^([01]\\d|2[0-3]):[0-5]\\d$")',
     '_HHMM = re.compile(r"^.*$")',
     "tests/test_scheduler_slots.py"),
    ("backend/app/services/schedule_slots.py",
     '        p["time"] = hs[k % len(hs)]',
     '        p["time"] = hs[0]',
     "tests/test_scheduler_slots.py"),
    ("backend/app/services/schedule_slots.py",
     "        out[ch] = None if n < min_posts else max(",
     "        out[ch] = None if n < 0 else max(",
     "tests/test_scheduler_slots.py"),
    # ── post_preview.py : la zone sûre est une SURFACE, pas un libellé ──────
    ("backend/app/services/post_preview.py",
     '    d.rectangle([0, H - bot, W, H], fill=(0, 0, 0, 160))',
     '    d.rectangle([0, H - 1, W, H], fill=(0, 0, 0, 160))',
     "tests/test_scheduler_preview.py"),
    ("backend/app/services/post_preview.py",
     '    d.rectangle([W - right, top, W, H - bot], fill=(0, 0, 0, 130))',
     '    pass',
     "tests/test_scheduler_preview.py"),
    # ── routes.py : validation par lot ──────────────────────────────────────
    ("backend/app/api/routes.py",
     "            if not (p.job_id or p.source_image):",
     "            if False:",
     "tests/test_scheduler_validate.py"),
    ("backend/app/api/routes.py",
     '        if p.validated_at and any(k in body for k in\n'
     '                                  ("title", "caption", "channels", "run_at", "job_id", "source_image", "brief")):\n'
     '            p.validated_at, p.mode, p.status = None, "assisted", "draft"',
     "        pass",
     "tests/test_scheduler_validate.py"),
    ("backend/app/api/routes.py",
     '        q = _select(ScheduledPost).where(ScheduledPost.status.in_(("draft", "scheduled")))',
     '        q = _select(ScheduledPost).where(ScheduledPost.status.in_(("scheduled",)))',
     "tests/test_scheduler_validate.py"),
    # ── routes.py : lot exportable et retour d'état ─────────────────────────
    ("backend/app/api/routes.py",
     '        if p.status == "posted" and (p.published_by or "") != who:',
     "        if False:",
     "tests/test_scheduler_lot.py"),
    ("backend/app/api/routes.py",
     "        for ch in neufs:\n            _q.count(ch)              # le plafond du réseau est partagé (R12)",
     "        for ch in neufs:\n            pass",
     "tests/test_scheduler_lot.py"),
    ("backend/app/api/routes.py",
     '            p.status = "ready"\n            p.error = str(body.get("error") or "échec rapporté par le compagnon")[:500]',
     '            p.status = "failed"\n            p.error = str(body.get("error") or "échec rapporté par le compagnon")[:500]',
     "tests/test_scheduler_lot.py"),
    ("backend/app/api/routes.py",
     '            .where(ScheduledPost.status == "scheduled")',
     "            .where(ScheduledPost.status.isnot(None))",
     "tests/test_scheduler_lot.py"),
    # ── brief, séries, recyclage ────────────────────────────────────────────
    ("backend/app/services/marketing.py",
     '    posts, retires = apply_forbidden(posts, (brief or {}).get("forbidden") or [])\n'
     '    return {"posts": posts, "engine": "deterministic",',
     '    retires = []\n'
     '    return {"posts": posts, "engine": "deterministic",',
     "tests/test_scheduler_brief.py"),
    ("backend/app/services/marketing.py",
     '    return [x.strip() for x in (s or "").splitlines() if x.strip()]',
     '    return [(s or "").strip()]',
     "tests/test_scheduler_brief.py"),
    ("backend/app/services/series_service.py",
     "                if run_at in existants:\n                    skipped += 1\n                    continue",
     "                if False:\n                    skipped += 1\n                    continue",
     "tests/test_scheduler_series.py"),
    ("backend/app/services/series_service.py",
     "        if not 0 <= n <= 6:\n            raise ValueError(f\"jour de semaine hors 0-6 : {n}\")",
     "        if False:\n            raise ValueError(f\"jour de semaine hors 0-6 : {n}\")",
     "tests/test_scheduler_series.py"),
    ("backend/app/api/routes.py",
     "        if p.posted_at > limite:\n            continue",
     "        if False:\n            continue",
     "tests/test_scheduler_recycle.py"),
    ("backend/app/api/routes.py",
     "        if pid in deja or pid in vus or p is None or p.posted_at is None:",
     "        if pid in vus or p is None or p.posted_at is None:",
     "tests/test_scheduler_recycle.py"),
]


def marqueur(banc: str) -> str:
    """« tests/test_scheduler_slots.py » -> « SCHEDULER SLOTS: PASS »."""
    nom = pathlib.Path(banc).stem            # test_scheduler_slots
    return "SCHEDULER " + nom.split("_", 1)[1].replace("_", " ").upper() + ": PASS"


def verdict(banc: str) -> tuple[str, str]:
    r = subprocess.run([PY, banc], capture_output=True, cwd=BACK, timeout=900)
    txt = (r.stdout + r.stderr).decode("utf-8", "replace")
    if marqueur(banc) in txt and r.returncode == 0:
        return "VERTE", txt
    if re.search(r"(SyntaxError|IndentationError|NameError|ImportError)", txt):
        return "ROUGE(syntaxe)", txt
    return "ROUGE", txt


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre peuvent être en CRLF (autocrlf) : on apparie
        # en LF et l'on réécrit avec la fin de ligne du fichier ; la remise se
        # fait à l'octet près depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:70])
        txt = txt.replace(old, new)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            v, sortie = verdict(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        if v != "ROUGE":
            print(sortie[-900:], file=sys.stderr)
        bilan.append((i, rel, v))
        print(f"[{i:2d}] {v:14s} {rel:42s} {old.strip()[:46]!r} "
              f"-> {banc}  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps(bilan, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Étape 2 : lancer la campagne**

Run (depuis `backend/`) : `python tests/mutations_scheduler.py`
Attendu : 32 lignes numérotées de `[ 0]` à `[31]`, puis une ligne JSON. Deux
choses sont **obligatoires** sur chaque ligne, quel que soit le verdict :
- l'assertion `txt.count(old) == 1` n'a pas levé — la mutation a bien été
  appliquée, la campagne n'a pas mesuré du vide ;
- le `sha …=…` montre deux empreintes **identiques** — le fichier a été remis
  à l'octet près.

Le verdict, lui, ne se promet pas : le but de la campagne est de trouver les
`VERTE`. Une au moins est attendue par construction — la mutation n° 10
(`due.sort(key=lambda p: (p.thread_index or 0, p.run_at))` → `p.run_at`) :
aucun banc ne fait passer DEUX posts d'un même fil par un seul `tick()`.
L'étape 3 dit quoi en faire ; ne pas la retirer de la liste.

- [ ] **Étape 3 : traiter les VERTES**

Pour chaque ligne `VERTE`, écrire l'assertion qui manque dans le banc nommé,
la vérifier rouge sur la mutation puis verte sans elle, et **la commiter avec
la mutation qui l'a trouvée dans le message**. Ne jamais supprimer une
mutation verte pour faire taire la campagne : la mutation est la question, la
nouvelle assertion est la réponse.

Pour la n° 10, l'assertion qui manque s'écrit dans
`backend/tests/test_scheduler_threads.py` : rendre `p2` et `p3` dus (`run_at`
dans le passé) après la publication de `p1`, appeler `await marketing.tick()`
UNE fois, et assurer `VUS == [("1/ le début", None), ("2/ la suite", "r1"),
("3/ la fin", "r2")]` — c'est l'ordre du fil dans un seul tick que le tri
garantit.

Pour chaque ligne `ROUGE(syntaxe)`, remplacer la mutation par une variante qui
laisse le module importable (par exemple `if False:` au lieu d'une suppression
de bloc) et relancer cette mutation seule : `python tests/mutations_scheduler.py <n>`.

- [ ] **Étape 4 : la suite complète, une dernière fois**

Run (depuis `backend/`), un processus par fichier :

```bash
for t in socle publish youtube instagram tiktok settings metrics slots preview validate bundle lot brief series threads recycle; do
  python tests/test_scheduler_$t.py || echo "ECHEC: $t"
done
```
Attendu : seize lignes `SCHEDULER <NOM>: PASS`, aucune ligne `ECHEC:`.

Puis les bancs voisins que ce plan a touchés :
```bash
python tests/test_plan_brief.py
python tests/test_plan_doc_import.py
python tests/test_security_guards.py
python tests/test_hygiene_imports.py
python -m pytest tests/test_library_sendto.py -q
```
Attendu : `PLAN BRIEF TEST: PASS`, le PASS de chacun des autres, et
`3 passed` pour le dernier.

- [ ] **Étape 5 : le CHANGELOG**

Dans `CHANGELOG.md`, au-dessus de l'entrée de version courante, ajouter :

```markdown
# 🐙 Deepotus Video Gen — v2.7.0 "Le Scheduler publie seul"

**Cinq réseaux partent tout seuls, la semaine se valide d'un geste, et ce qui
a marché revient de lui-même.** Instagram Reels, YouTube Shorts et TikTok
rejoignent X et Telegram derrière un registre d'adaptateurs à quotas vérifiés
(500 posts/mois sur X, 50/24 h sur Instagram, 100/jour sur YouTube, ~15/jour
sur TikTok) ; un échec nomme son canal et sa cause. Les métriques de tous les
canaux publiés alimentent un tableau de bord par canal, format et semaine,
qui propose ensuite les créneaux. Les aperçus Reels, Shorts et TikTok montrent
les zones sûres. La semaine se valide en un lot ; un contenu modifié après
validation revient en attente. Un brief de campagne persistant nourrit le
plan et en retire ses interdits ; les séries récurrentes posent leurs
brouillons ; les fils X partent en réponse les uns des autres ; les posts
performants reviennent en proposition de recyclage. Le lot validé est
exportable avec ses vidéos, ses légendes et ses heures — le compagnon mobile
le publiera quand le PC est éteint, et son retour d'état se fond sans jamais
écraser une publication du PC.

Sans audit TikTok, l'envoi automatique reste **privé** (`SELF_ONLY`) : c'est
la règle de l'API, dite dans l'écran et dans les notes du lot.
```

- [ ] **Étape 6 : commit**

```bash
git add backend/tests/mutations_scheduler.py CHANGELOG.md
git commit -m 'scheduler : campagne de mutations et entree de CHANGELOG' -m 'Trente-deux mutations des lignes portantes (plafonds, registre, rejeu, budget de lecture X, créneaux, zones sûres, validation par lot, retour d état du compagnon, brief, séries, fils, recyclage), chacune remise à l octet près et adossée à un banc autonome ; le verdict lit le marqueur PASS et le code de sortie, jamais l un des deux seul.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Relecture (faite le 03/09/2026)

**Couverture du périmètre.** P1 → T0 (décision) + T2 (registre) + T3/T4/T5
(les trois adaptateurs) + T6 (clés, OAuth, tests de canal) ; P2 → T7 ; P3 →
T8 ; P4 → T9 ; P5 → T10 ; l'écran de tout cela → T11. D1 part backend → T12 ;
D2 → T13 (brief) + T14 (séries) + T15 (fils) ; D3 → T16 ; l'écran du lot 2 →
T17. E1, E2, E3 et les deux refus mesurés (Postiz, `google-api-python-client`)
→ section « Écarté ». Rien de R6 ne reste sans tâche.

**Noms tenus d'un bout à l'autre** (une divergence ici serait un bogue) :
`publishers.register(channel, available, fn)` / `publishers.publish(...)` /
`PublishResult(ok, detail, remote_id)` ; `quota.check/count/used/summary` et
`quota.LIMITS` ; `metrics_service.FETCHERS`, `refresh_all(max_per_channel)`,
`analytics(days)`, `engagement(m)`, `NOTES` ; `schedule_slots.load/save/
tz_offset/assign/suggest` et `DEFAULTS` ; `series_service.list_series/create/
delete/materialize/to_dict` ; `marketing.active_brief/brief_context/
apply_forbidden/vary_caption/tick` ; colonnes `remote_ids, validated_at,
thread_of, thread_index, series_id, recycled_from, published_by` ; tables
`post_metrics, campaign_briefs, post_series`. Les helpers du bundle sont tous
en `__dzSched*`, l'hôte du panneau est `__dzSchedHost` (le marqueur du
patcher).

**Ce qui reste à mesurer par celui qui exécute** (chaque tâche l'ouvre par la
lecture de sa doc, `WebFetch` exact, date écrite dans le docstring du module) :
l'envoi résumable et les noms d'insights d'Instagram (T4), les détails OAuth
et Shorts de YouTube (T3, T7), la taille des morceaux et les champs de
`video/query` de TikTok (T5, T7), l'absence de `views` sur `Message` dans
l'API Bot de Telegram (T7), et les fractions des zones sûres, qui ne valent
que ce que valent des captures d'un vrai téléphone (T9). Le reste des chiffres
de ce plan — les cinq puis six ancres, les deux paires de deltas, les comptes
de sondes, le jour de la semaine du 07/09/2026, la présence de `httpx` et de
`tweepy` dans `backend/requirements.txt` — a été mesuré le 03/09/2026 et est
reproductible par les commandes écrites dans les tâches.
