"""SQLite-backed job persistence — v1.2 with new fields + auto-migration."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, DateTime, Text, text, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from loguru import logger

from app.config import settings


class Base(DeclarativeBase):
    pass


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    image_filename: Mapped[str] = mapped_column(String(255))
    image_filename_end: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    final_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    final_video_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    caption_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caption_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    style: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    template_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    voiceover_language: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    voice_mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    composition_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    composition_layout: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    layer_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    batch_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # v1.15.6 — JSON cost inputs for /cost/usage (episodes: images + narration chars)
    cost_meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # W-a (v1.19) — which video model rendered the clip (VIDEO_MODELS id)
    video_model: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
    # D-34 (24/09/2026) — note 0..5 du rendu (« Good Take » = 5) ; NULL et 0
    # = sans note. Posée par `PUT /api/jobs/{id}/rating`, filtrée par
    # `Pipeline.list_jobs(min_rating=)` ; migrée par V1_2_NEW_COLUMNS.
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Plan Quick T2 (tâche #51, 01/10/2026) — le rendu dont ce clip est l'extension (lignée)
    parent_job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    # Bibliothèque #77 (03/10/2026) — favori du rendu, 1 = favori, NULL/0 = non. Il vivait dans le
    # navigateur (localStorage `dz_fav_renders`) ; INDÉPENDANT de `rating` (décision de l'utilisateur).
    fav: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class MeshyTaskRecord(Base):
    """v2.1 (3D Studio Meshy) — une tâche Meshy observée par le proxy.
    Spec INTEGRATION-MESHY.md §6 : les tâches créées par l'API ne remontent
    pas dans « My Assets » du web app Meshy et leurs URLs expirent — cette
    table EST la bibliothèque DeepOtus (journal + fichiers rapatriés)."""
    __tablename__ = "meshy_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # id Meshy
    kind: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # phase du graphe 3D Studio : preview|texture|remesh|rig|animate|export
    phase: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    # consumed_credits de la réponse Meshy = seule vérité comptable (0 si FAILED)
    consumed_credits: Mapped[int] = mapped_column(Integer, default=0)
    model_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # JSON
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)         # JSON envoyé
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    # rapatriement : sous-dossier de outputs/meshy3d/ + carte {clé: fichier}
    local_dir: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    local_files: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON


class ScheduledPost(Base):
    """v1.9 — one planned publication. Created by hand in the Scheduler or
    materialized from a marketing plan. The schedule loop fires due posts:
    mode='auto' publishes to capable channels (Telegram); mode='assisted'
    flips the post to 'ready' so the user posts manually with one click."""
    __tablename__ = "scheduled_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    channels: Mapped[str] = mapped_column(String(120), default="x")  # csv
    run_at: Mapped[datetime] = mapped_column(DateTime, index=True)   # UTC
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    # draft | scheduled | ready | posted | failed
    mode: Mapped[str] = mapped_column(String(12), default="assisted")  # auto | assisted
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hook: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    script_idea: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_idea: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # v1.10 — analytics loop: the tweet id when posted via the X adapter,
    # and a JSON blob of public metrics (impressions, likes, …) refreshed
    # best-effort by the daily metrics pass. Feeds the plan generator.
    x_post_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # v1.12 — resolved visual source for the post's render (a library image
    # filename used as the Seedance start frame / the post's still). Set in
    # the plan's Sources step; the Produce button uses it instead of
    # generating a fresh frame.
    source_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # v1.27 — bloc structuré du plan (style Sol) : JSON {objective, priority,
    # aspect_ratio, tg_caption, on_image_text, cta, hashtags, links,
    # avatar_script_short, avatar_script_long, scheduling_notes}. La caption
    # Telegram y prime sur `caption` à la publication (marketing.fire_post).
    brief: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # plan scheduler (03/09/2026, tâche #24 du 29/09) — P1 ids distants par canal, P5 validation par lot, D2 fils et
    # séries, D3 recyclage, D1 qui a publié (pc | appareil R12).
    remote_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON {"x": "17…", "youtube": "dQw…"}
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    thread_of: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    thread_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    series_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    recycled_from: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    published_by: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    # Plan mobile T8 (tâche #57, 01/10/2026) — DÉLÉGATION EXPLICITE (décision de l'utilisateur) : un post emporté par un
    # téléphone lui est CONFIÉ (id de l'appareil) ; le Scheduler du PC ne le publie plus tant qu'il ne lui revient pas
    # (échec rapporté, rendu, reprise à la main, appareil révoqué). Aucun doublon possible.
    delegue_a: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    delegue_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PostMetric(Base):
    """Instantané daté des métriques d'un post sur un canal (plan scheduler P2). L'engagement est calculé
    (metrics_service.engagement), jamais stocké."""
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
    """Plan scheduler D2 — brief persistant lu par generate_plan (un seul actif)."""
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
    """Plan scheduler D2 — série récurrente matérialisée en brouillons (series_service)."""
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


class AvatarPreset(Base):
    """v1.16 — a saved avatar+voice 'casting' reusable across Quick and Studio.
    Stored in deepotus.db so it migrates with the export/import kit. The *_id
    fields are the durable source of truth; the cached preview URLs
    (avatar_img/voice_prev) are HeyGen signed URLs that may expire — the UI
    tolerates a blank/stale preview and re-resolves by id from the live list."""
    __tablename__ = "avatar_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    avatar_id: Mapped[str] = mapped_column(String(120))
    avatar_type: Mapped[str] = mapped_column(String(20), default="avatar")
    avatar_img: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    voice_id: Mapped[str] = mapped_column(String(120))
    voice_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    voice_prev: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    voice_lang: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    # v1.16 — preferred HeyGen rendering engine (avatar_iii/iv/v; NULL = legacy)
    engine: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QuickPreset(Base):
    """Plan Quick T6 (tâche #53, 01/10/2026) — un preset Quick = la RECETTE de T1 (quick_recipe), nommée et rangée
    par onglet. En JSON : la recette grossit à chaque tâche (sous-titres, lip-sync, caméra) ; une colonne par champ
    imposerait une migration à chaque fois. Table neuve : créée par create_all d'init_db."""
    __tablename__ = "quick_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    tab: Mapped[str] = mapped_column(String(16), default="seedance", index=True)
    recipe: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BibleEntity(Base):
    """v1.17 (Atelier P1) — one entry of the persistent story bible, shared by
    every chapter of a series. v1.19 kinds: character | place | object | date
    (temporal markers) | ambiance (light/weather/mood) | decor (set dressing).
    The generated reference image (a Library filename) + its locked seed are
    the consistency anchor reused by storyboard/production phases."""
    __tablename__ = "bible_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    style_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inspiration_images: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    # v1.19 (agent manuscrit) — alternative names found in the text, and the
    # per-chapter verbatim evidence quotes collected during ingestion.
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # JSON list
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # JSON [{chapter,quote}]
    # v1.20 — the exact generation recipe of the current reference (full
    # prompt + seed + size): replaying it is guaranteed-identical (FLUX is
    # deterministic at equal prompt+seed), THE consistency anchor.
    prompt_recipe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    # v1.20.1 — characters: the face close-ups sheet (2nd pass, Kontext
    # chained on the turnaround so the face is guaranteed identical).
    face_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # v1.21 (B — casting voix) : la voix ElevenLabs du personnage (suggérée
    # par l'agent d'après la fiche, ou choisie manuellement).
    voice_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    voice_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    voice_prev: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # T103 (plan son-vfx D4, 06/10/2026) — tempérament de jeu du personnage, JSON
    # {"tags": ["[whispers]", …], "stability": 0.0 | 0.5 | 1.0}, TOUJOURS passé
    # par voice_direction.clamp_style avant écriture ET à la lecture. Déclarée ICI
    # (base neuve, attribut ORM) ET dans BIBLE_ENTITIES_COLUMNS (auto-ALTER des
    # bases existantes) : l'un sans l'autre casse un des deux cas.
    voice_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # v2.7 (phase D — spec Magnific §9.1 « verrouiller un produit, accessoire,
    # véhicule, élément de décor ou personnage stylisé ») : l'ancrage 3D de
    # l'entité. `model3d_job` = le dossier outputs/assets3d/<job> qui porte le
    # maillage ; `model3d_file` = la VERSION retenue (model.glb, model.v2.glb).
    # La bible verrouillait jusqu'ici en 2D seulement (ref_image + seed).
    model3d_job: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    model3d_file: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VectorDoc(Base):
    """Vectorlab (phase 0) — l'INDEX d'un document vectoriel : nom, ancrage
    (chapitre et/ou entité de la bible), rôle (decor | lumiere | personnage |
    libre) et version courante. Le CONTENU vit sur disque
    (services/vector_store.py : `<id>.json` + historique `.v<n>.json`)."""
    __tablename__ = "vector_docs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    chapter_id: Mapped[Optional[str]] = mapped_column(String(36), index=True,
                                                      nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    # le pont cartes (27/08) : un doc peut appartenir à un JEU du Cardforge —
    # miroir de chapter_id, colonne née par _auto_migrate sur les bases d'avant
    deck_id: Mapped[Optional[str]] = mapped_column(String(36), index=True,
                                                   nullable=True)
    role: Mapped[str] = mapped_column(String(12), index=True, default="libre")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)


class VectorDocLink(Base):
    """Vectorlab (phase 6) — liaison d'INSTANCIATION chapitre↔document : le
    chapitre référence un doc (bibliothèque globale ou doc d'un autre
    chapitre) SANS copie — un seul document, l'édition se voit partout ;
    « dupliquer » crée la copie indépendante et retire la liaison. PK
    composite = unicité de la paire ; table neuve : create_all suffit."""
    __tablename__ = "vector_doc_links"

    chapter_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                        index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)


class LibraryAsset(Base):
    """Bibliothèque (28/08) — l'index de PROVENANCE d'un fichier du magasin
    (images, audio) : quelle FONCTION de l'app l'a produit (`source`, slug
    de library_index.SOURCES), comment on le sait (`origin` : depot =
    enregistré à l'écriture, heuristique = déduit du nom — dit à l'UI) et
    les liens utiles. Le filename canonique reste l'identifiant de tout le
    dépôt (décision D5 du plan) ; table neuve : create_all suffit."""
    __tablename__ = "library_assets"

    filename: Mapped[str] = mapped_column(String(255), primary_key=True)
    source: Mapped[str] = mapped_column(String(24), index=True,
                                        default="inconnu")
    kind: Mapped[str] = mapped_column(String(12), default="image")
    origin: Mapped[str] = mapped_column(String(12), default="depot")
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    deck_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    doc_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime,
                                              default=datetime.utcnow)
    # ── Bibliothèque #77 (03/10/2026, plan-library T0) : le DAM. Colonnes
    # AJOUTÉES (jamais une table de remplacement), migrées par
    # LIBRARY_ASSETS_COLUMNS. Posées toutes ici : les tâches suivantes du
    # plan (lignée, droits, nettoyage, couleur) n'ont plus à retoucher la
    # migration. `fav` et `note` sont deux notions (décision 03/10).
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    fav: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parent_filename: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True)
    relation: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    licence: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    auteur: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True,
                                                  index=True)
    taille_o: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    couleur: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    teinte: Mapped[Optional[str]] = mapped_column(String(12), nullable=True,
                                                  index=True)
    # Tâche #80 (03/10/2026) : la RECETTE d'une image générée (JSON : prompt
    # d'origine, style, modèle, format, graine) — /images/generate l'écrit ;
    # la fiche la montre et « Rejouer » la renvoie. Les anciennes : NULL.
    recette: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Tâche #82 PR C (04/10/2026) : la LÉGENDE d'une image par un modèle vision (payant, prix annoncé), et ce modèle
    legende: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    legende_modele: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)


class LibraryComment(Base):
    """Tâche #82 (04/10/2026, plan-library T14) — un COMMENTAIRE de revue sur un asset : texte, statut (a_revoir |
    valide | rejete), instant visé pour un son (`t_s`). `ref` = filename (ou job_id). Table neuve : create_all suffit."""
    __tablename__ = "library_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ref: Mapped[str] = mapped_column(String(255), index=True)
    texte: Mapped[str] = mapped_column(Text)
    statut: Mapped[str] = mapped_column(String(12), default="a_revoir")
    t_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class LibraryProject(Base):
    """Bibliothèque #78 (03/10/2026, plan-library T3) — un PROJET : campagne,
    chapitre, deck. Il contient des assets de TOUTES les catégories ; la
    catégorie devient un filtre à l'intérieur. `epingle` = il descend EN ENTIER
    sur le téléphone (décision de l'utilisateur : un seul projet, qui remplace
    le projets.json de la tâche #58). Table neuve : create_all suffit."""
    __tablename__ = "library_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nom: Mapped[str] = mapped_column(String(120))
    couleur: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    epingle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime,
                                                 default=datetime.utcnow)


class LibraryProjectItem(Base):
    """L'appartenance d'un asset à un projet : n:n, PK composite — l'unicité
    de la paire est TENUE PAR LA BASE. `ref` = filename pour un fichier, job_id
    pour un rendu / 3D / sprite : les clés que l'écran manipule déjà ; `kind`
    reprend le vocabulaire de l'écran (image, audio, render, asset3d, sprite2d)."""
    __tablename__ = "library_project_items"

    project_id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                            index=True)
    ref: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    kind: Mapped[str] = mapped_column(String(12), default="image")
    added_at: Mapped[datetime] = mapped_column(DateTime,
                                               default=datetime.utcnow)


class Device(Base):
    """Plan mobile T2 (tâche #56, P1, 01/10/2026) — un appareil appairé. Le jeton n'est JAMAIS stocké : seul son
    sha256 l'est, comme un mot de passe. `revoque` non nul = l'appareil ne passe plus la garde, immédiatement (le cache
    de la garde est invalidé par la révocation, pas par son TTL). Table neuve : `create_all` suffit (comme LibraryAsset)."""
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nom: Mapped[str] = mapped_column(String(60), default="")
    jeton_sha256: Mapped[str] = mapped_column(String(64), index=True)
    cree: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoque: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    vu_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ChapterLock(Base):
    """Plan mobile T14/T21 (tâche #59, 02/10/2026) — un chapitre EMPORTÉ par un téléphone pour être écrit hors ligne.
    Tant qu'il existe, le PC ne modifie, ne supprime ni ne ré-importe ce chapitre (423). `base_sha256` = empreinte du
    texte remis au téléphone : un retour sur une autre base est un conflit. Tables neuves : `create_all` suffit."""
    __tablename__ = "chapter_locks"

    chapter_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), index=True)
    device_nom: Mapped[str] = mapped_column(String(60), default="")
    base_sha256: Mapped[str] = mapped_column(String(64), default="")
    pris_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SyncConflit(Base):
    """Le journal des conflits de chapitres : rien n'est écrasé en silence, aucun texte n'est perdu (celui du téléphone
    refusé, celui du manuscrit ré-importé sur un chapitre emporté, une reprise forcée)."""
    __tablename__ = "sync_conflits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quand: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    chapter_id: Mapped[str] = mapped_column(String(36), index=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    device_nom: Mapped[str] = mapped_column(String(60), default="")
    motif: Mapped[str] = mapped_column(String(24))      # verrou_perdu | base_differente | reimport | repris_pc | revoque
    texte: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Chapter(Base):
    """v1.17 (Atelier P1) — a story chapter: raw script text + the annotated
    spans linking text zones to bible entities ([{start,end,text,entity_id}]
    JSON, offsets over script_text)."""
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    script_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spans: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    series: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Shot(Base):
    """v1.18 (Atelier P2) — one storyboard shot of a chapter: the visual beat
    (action), which bible entities are in frame, framing + camera + duration,
    and a cheap sketch (image + locked seed) used to validate composition and
    rhythm BEFORE any paid production render."""
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(String(36), index=True)
    idx: Mapped[int] = mapped_column(Integer, default=0)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON ids
    shot_type: Mapped[str] = mapped_column(String(30), default="medium")
    camera_move: Mapped[str] = mapped_column(String(40), default="static, locked-off")
    duration_s: Mapped[float] = mapped_column(Float, default=4.0)
    sketch_image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sketch_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # tâche #62 (plan chapitres T8) — l'image de PRODUCTION du plan, générée avec les vues des entités en référence
    # (le croquis reste le jet FLUX bon marché) ; `image_refs` = le nombre de références réellement envoyées.
    image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_refs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # v1.22 (W-d) — video-shotcraft bridge: motion recipe card slug (validated
    # against the installed skill's catalog) + 1-5 energy level of the beat.
    motion_recipe: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    energy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Scene(Base):
    """v1.20 (Atelier Adaptation) — one screenplay scene of a chapter, produced
    by the adaptation pass WITHOUT touching the original manuscript. Carries
    the film grammar (slugline INT/EXT + bible location + time of day,
    lighting, camera notes, mood), the Fountain-format scene text, the bible
    entities in frame (incl. decor — reusable across chapters), and later the
    timed voice-over (phase C) that drives the storyboard."""
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chapter_id: Mapped[str] = mapped_column(String(36), index=True)
    idx: Mapped[int] = mapped_column(Integer, default=0)
    slugline: Mapped[str] = mapped_column(String(200), default="")
    int_ext: Mapped[str] = mapped_column(String(10), default="INT")
    location_entity_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    time_of_day: Mapped[str] = mapped_column(String(20), default="JOUR")
    fountain_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lighting: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    camera_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    entities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON ids
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_s: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vo_audio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TextVersion(Base):
    """Tâche #61 (plan chapitres P2, 02/10/2026) — un instantané de l'ANCIEN texte, pris avant une écriture qui l'aurait
    perdu. `kind` = chapter (script_text) | scene (fountain_text) | scenario (le scénario ENTIER d'un chapitre, gardé
    avant que l'adaptation ou la remise à zéro ne supprime ses scènes ; `target_id` = le chapitre). `n` numérote les
    instantanés d'une cible ; l'historique est élagué aux 10 derniers. Table neuve : `create_all` suffit."""
    __tablename__ = "text_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    n: Mapped[int] = mapped_column(Integer, default=1)
    passe: Mapped[str] = mapped_column(String(16), default="manuelle")
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AtelierSetting(Base):
    """v1.20.4 — réglages globaux de l'Atelier (clé/valeur). Ex:
    global_style = le style de réalisation du PROJET, injecté dans toutes
    les générations (planches bible, et la production en P3) sauf quand une
    entité définit son propre style (override ponctuel)."""
    __tablename__ = "atelier_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Depense(Base):
    """Une dépense prévue par la garde des plafonds (plan Settings T4, tâche #16 du suivi, 29/09/2026).

    `estime_usd` vient de `pricing.estimate` AVANT le tir ; `reel_usd` / `reel_unites` sont remplis APRÈS coup
    quand le fournisseur donne un chiffre (crédits Meshy consommés, delta de quota HeyGen) — sinon ils restent vides
    et l'écran dit « estimé » sur cette ligne. Table neuve : create_all suffit, aucune migration."""
    __tablename__ = "depenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    quand: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    mois: Mapped[str] = mapped_column(String(7), index=True)        # "2026-09", heure locale
    moteur: Mapped[str] = mapped_column(String(24), index=True)     # fal|heygen|elevenlabs|meshy|anthropic|…
    categorie: Mapped[str] = mapped_column(String(24), index=True)  # écran du rail
    op: Mapped[str] = mapped_column(String(32), default="")         # `kind` de pricing.estimate
    estime_usd: Mapped[float] = mapped_column(Float, default=0.0)
    reel_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reel_unites: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)


_engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
async_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


@event.listens_for(_engine.sync_engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """WAL + a real busy timeout on every connection.

    A render holds its session open for the whole generation (minutes), so
    with the default rollback journal a concurrent batch or a UI request hits
    'database is locked' instead of waiting. WAL lets readers run during a
    write; busy_timeout replaces the instant failure with a 5s wait.
    """
    cur = dbapi_conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA synchronous=NORMAL")
    finally:
        cur.close()


# Columns added in v1.2 — for SQLite auto-migration from v1.1 DBs
# Columns added in v1.3 — added to same list for forward-compat
V1_2_NEW_COLUMNS = [
    ("image_filename_end", "VARCHAR(255)"),
    ("seed", "INTEGER"),
    ("duration_s", "INTEGER"),
    ("aspect_ratio", "VARCHAR(10)"),
    ("style", "VARCHAR(20)"),
    ("template_id", "VARCHAR(60)"),
    ("voiceover_language", "VARCHAR(4)"),
    ("current_step", "VARCHAR(80)"),
    # v1.3 additions
    ("batch_id", "VARCHAR(36)"),
    ("batch_index", "INTEGER"),
    ("batch_size", "INTEGER"),
    # v1.3.1 additions
    ("voice_mode", "VARCHAR(20)"),
    # v1.4 additions
    ("provider", "VARCHAR(20)"),
    ("composition_id", "VARCHAR(36)"),
    ("composition_layout", "VARCHAR(30)"),
    ("layer_index", "INTEGER"),
    # v1.7.2 additions
    ("title", "VARCHAR(200)"),
    # v1.15.6 — episode/voiceover cost inputs (JSON: images + narration chars)
    ("cost_meta", "TEXT"),
    # W-a (v1.19) — selected video model id
    ("video_model", "VARCHAR(48)"),
    # D-34 (24/09/2026) — note étoile du rendu (0..5, NULL = sans note)
    ("rating", "INTEGER"),
    # Plan Quick T2 (tâche #51) — lignée d'extension
    ("parent_job_id", "VARCHAR(36)"),
    # Bibliothèque #77 (03/10/2026) — favori du rendu, repris du navigateur
    ("fav", "INTEGER"),
]


# v1.9 — full expected shape of scheduled_posts, for auto-ALTER when an
# older/stub table already exists (create_all never alters existing tables).
SCHEDULED_POSTS_COLUMNS = [
    ("title", "VARCHAR(200)"),
    ("caption", "TEXT"),
    ("channels", "VARCHAR(120)"),
    ("run_at", "DATETIME"),
    ("status", "VARCHAR(20)"),
    ("mode", "VARCHAR(12)"),
    ("job_id", "VARCHAR(36)"),
    ("format", "VARCHAR(20)"),
    ("hook", "TEXT"),
    ("script_idea", "TEXT"),
    ("image_idea", "TEXT"),
    ("plan_id", "VARCHAR(36)"),
    ("error", "TEXT"),
    ("created_at", "DATETIME"),
    ("posted_at", "DATETIME"),
    # v1.10 additions
    ("x_post_id", "VARCHAR(40)"),
    ("metrics", "TEXT"),
    # v1.12 additions
    ("source_image", "VARCHAR(255)"),
    # v1.27 additions
    ("brief", "TEXT"),
    # plan scheduler (03/09/2026, tâche #24)
    ("remote_ids", "TEXT"), ("validated_at", "DATETIME"), ("thread_of", "VARCHAR(36)"),
    ("thread_index", "INTEGER"), ("series_id", "VARCHAR(36)"),
    ("recycled_from", "VARCHAR(36)"), ("published_by", "VARCHAR(40)"),
    # plan mobile T8 (tâche #57) : la délégation à un appareil
    ("delegue_a", "VARCHAR(36)"), ("delegue_le", "DATETIME"),
]


# v1.16 — columns added to avatar_presets after its initial ship (create_all
# never alters an existing table, so pre-existing DBs get them via auto-ALTER).
AVATAR_PRESETS_COLUMNS = [
    ("engine", "VARCHAR(20)"),
]


# v1.19 — columns added to bible_entities after its initial ship (manuscript
# ingestion agent: aliases + per-chapter evidence quotes).
BIBLE_ENTITIES_COLUMNS = [
    ("aliases", "TEXT"),
    ("evidence", "TEXT"),
    ("prompt_recipe", "TEXT"),
    ("face_image", "VARCHAR(255)"),
    ("voice_id", "VARCHAR(80)"),
    ("voice_name", "VARCHAR(200)"),
    ("voice_prev", "TEXT"),
    ("voice_style", "TEXT"),          # T103 — tempérament de jeu (JSON clampé)
    # v2.7 (phase D) — ancrage 3D de l'entité
    ("model3d_job", "VARCHAR(36)"),
    ("model3d_file", "VARCHAR(64)"),
]


# v1.22 (W-d) — columns added to shots after its initial ship (video-shotcraft
# bridge: motion recipe card + energy level).
SHOTS_COLUMNS = [
    ("motion_recipe", "VARCHAR(60)"),
    ("energy", "INTEGER"),
    # tâche #62 : image de production + nombre de références
    ("image", "VARCHAR(255)"),
    ("image_refs", "INTEGER"),
]

# Vectorlab — pont cartes (27/08) : l'ancre deck_id sur les bases d'avant
VECTOR_DOCS_COLUMNS = [
    ("deck_id", "VARCHAR(36)"),
]

# Bibliothèque #77 (03/10/2026) — colonnes ajoutées à library_assets APRÈS sa
# livraison du 28/08. `create_all` n'ALTER jamais une table existante : sans
# cette liste, la base d'un utilisateur qui a déjà ses lignes n'aurait aucune
# de ces colonnes et toute lecture partirait en OperationalError.
LIBRARY_ASSETS_COLUMNS = [
    ("tags", "TEXT"), ("fav", "INTEGER"), ("note", "INTEGER"),
    ("parent_filename", "VARCHAR(255)"), ("relation", "VARCHAR(24)"),
    ("licence", "VARCHAR(40)"), ("auteur", "VARCHAR(120)"),
    ("source_url", "TEXT"), ("sha256", "VARCHAR(64)"), ("taille_o", "INTEGER"),
    ("couleur", "VARCHAR(7)"), ("teinte", "VARCHAR(12)"),
    ("recette", "TEXT"),   # tâche #80
    ("legende", "TEXT"), ("legende_modele", "VARCHAR(60)"),   # tâche #82 PR C
]


async def _auto_migrate():
    """Add new columns to existing tables without losing data."""
    async with _engine.begin() as conn:
        # v1.9 — the Reef design pack shipped a scheduled_posts stub with an
        # incompatible NOT NULL `scheduled_at` column. Rebuild: rename the
        # old table (kept as backup), recreate the real shape, copy rows.
        result = await conn.execute(text("PRAGMA table_info(scheduled_posts)"))
        sp_cols = {row[1] for row in result.fetchall()}
        if "scheduled_at" in sp_cols:
            logger.info("Auto-migrating: rebuilding legacy scheduled_posts "
                        "(design-pack stub shape)")
            await conn.execute(text(
                "ALTER TABLE scheduled_posts RENAME TO scheduled_posts_legacy"))
            # SQLite index names are database-global and survive the rename;
            # drop the legacy ones so the fresh table can recreate them.
            for idx in ("ix_scheduled_posts_status",
                        "ix_scheduled_posts_run_at",
                        "ix_scheduled_posts_plan_id",
                        "ix_scheduled_posts_scheduled_at"):
                await conn.execute(text(f"DROP INDEX IF EXISTS {idx}"))
            await conn.run_sync(
                lambda sc: Base.metadata.tables["scheduled_posts"].create(sc))
            await conn.execute(text("""
                INSERT INTO scheduled_posts
                    (id, title, caption, channels, run_at, status, mode,
                     job_id, format, hook, script_idea, image_idea, plan_id,
                     error, created_at, posted_at)
                SELECT id,
                       COALESCE(title, ''),
                       caption,
                       COALESCE(channels, 'x'),
                       COALESCE(run_at, scheduled_at),
                       COALESCE(status, 'draft'),
                       COALESCE(mode, 'assisted'),
                       COALESCE(job_id, render_job_id),
                       format, hook, script_idea, image_idea, plan_id,
                       error,
                       COALESCE(created_at, scheduled_at),
                       posted_at
                FROM scheduled_posts_legacy
            """))
            logger.info("scheduled_posts rebuilt; old data kept in "
                        "scheduled_posts_legacy")
        else:
            # Recovery path: a previous rebuild attempt renamed the stub but
            # crashed before copying (SQLite auto-commits DDL). If a legacy
            # table still holds rows that never made it over, copy them once.
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='scheduled_posts_legacy'"))
            if result.fetchone() and "run_at" in sp_cols:
                await conn.execute(text("""
                    INSERT INTO scheduled_posts
                        (id, title, caption, channels, run_at, status, mode,
                         job_id, format, hook, script_idea, image_idea,
                         plan_id, error, created_at, posted_at)
                    SELECT id, COALESCE(title, ''), caption,
                           COALESCE(channels, 'x'),
                           COALESCE(run_at, scheduled_at),
                           COALESCE(status, 'draft'),
                           COALESCE(mode, 'assisted'),
                           COALESCE(job_id, render_job_id),
                           format, hook, script_idea, image_idea, plan_id,
                           error, COALESCE(created_at, scheduled_at), posted_at
                    FROM scheduled_posts_legacy
                    WHERE id NOT IN (SELECT id FROM scheduled_posts)
                """))

        for table, columns in (("jobs", V1_2_NEW_COLUMNS),
                               ("scheduled_posts", SCHEDULED_POSTS_COLUMNS),
                               ("avatar_presets", AVATAR_PRESETS_COLUMNS),
                               ("bible_entities", BIBLE_ENTITIES_COLUMNS),
                               ("shots", SHOTS_COLUMNS),
                               ("vector_docs", VECTOR_DOCS_COLUMNS),
                               ("library_assets", LIBRARY_ASSETS_COLUMNS)):
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            existing_cols = {row[1] for row in result.fetchall()}
            if not existing_cols:
                continue  # Table doesn't exist yet, create_all handles it
            for col_name, col_type in columns:
                if col_name not in existing_cols:
                    logger.info(f"Auto-migrating: ALTER TABLE {table} "
                                f"ADD COLUMN {col_name} {col_type}")
                    await conn.execute(text(
                        f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}"))


async def init_db():
    # Create tables (no-op if already exist)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Then auto-migrate any v1.1 DB that's missing v1.2 columns
    await _auto_migrate()


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
