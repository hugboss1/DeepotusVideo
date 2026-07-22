# -*- coding: utf-8 -*-
"""v1.22 (W-d) — Régénère backend/app/knowledge/shotcraft_catalog.json.

Croise le catalogue du skill installé (~/.claude/skills/video-shotcraft/
gallery/api/library.json — source de vérité pour la liste des fiches et leur
énergie) avec la curation éditoriale ci-dessous :

- cat   : famille de la fiche (camera, transition, rhythm, impact, light,
          material, particle, title, outro, ui, data, brand, technique) ;
- anim  : True = grammaire transposable au découpage d'un chapitre narratif
          (l'agent interne ne propose QUE ces fiches) ; False = motion-UI
          produit (reste sélectionnable à la main dans l'Atelier) ;
- gloss : glose anglaise courte injectée dans le prompt Gemini et dans le
          prompt du croquis FLUX.

À relancer quand le skill ajoute/renomme des fiches :
    python scripts/gen_shotcraft_catalog.py [chemin/du/skill]
Le script échoue si la curation et library.json divergent (fiche ajoutée ou
retirée) — c'est voulu : chaque nouvelle fiche doit être curée à la main.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "backend" / "app" / "knowledge" / "shotcraft_catalog.json"
DEFAULT_SKILL = Path.home() / ".claude" / "skills" / "video-shotcraft"

# slug | cat | anim | gloss  (106 fiches — état du skill au 2026-07-23)
CURATION = """
ai-stream-response          | ui         | 0 | AI answer panel: summary lands first, evidence rows stream in
autolayout-gap-dial         | ui         | 0 | a spacing dial pushes the layout apart in real time
beat-cut-moves              | rhythm     | 1 | cuts as drumbeats: accelerating trailer cut-in, paparazzi flash burst
beat-step-list-theme-cycle  | ui         | 0 | list steps and theme swaps hammer on every beat
before-after-slider-scrub   | ui         | 0 | before/after slider scrub comparison
bottom-push-stack-wipe      | ui         | 0 | chapter change by bottom-push page stack
brand-frame-snap            | brand      | 0 | a brand frame wraps real footage, snapping color per mode
brand-ink-open              | material   | 1 | ink-press opening: the name stamped in ink before the story starts
bubble-swarm-takeover       | transition | 1 | a swarm of themed shapes floods the frame as a scene-change curtain
canvas-materialize-moves    | ui         | 0 | AI results materialize onto a canvas
card-flip-reveal            | ui         | 0 | feature cards flip over to reveal their results
card-flock-tumble           | ui         | 0 | a flock of cards tumbles into the brand slogan (peak energy)
cel-flash-stomp             | title      | 1 | words stomp in with cel-flash impact frames
chart-live-moves            | data       | 0 | living charts: axis rescale shock, dot-swarm regroup, oscilloscope stream
circle-match-iris           | transition | 1 | iris match-cut through a circular element into the next scene
cloner-depth-echo           | ui         | 0 | one card echoes into many clones in depth (one = many)
collab-cursor-moves         | ui         | 0 | collaborator cursors act out teamwork on the canvas
color-block-step-wipe       | transition | 1 | stepped color-block wipe, hard cuts, no easing
command-palette-summon      | ui         | 0 | a command palette summons the whole product into one input
crane-rise-reveal           | camera     | 1 | start on a detail, crane up to reveal the whole scene
crash-zoom-punch            | camera     | 1 | sudden crash zoom slamming attention onto the subject
dataviz-landscape-open      | data       | 0 | abstract data-landscape opening, slow rise
deck-deal-flyin             | ui         | 0 | cards dealt at speed into a growing wall
depth-layer-moves           | camera     | 1 | 2.5D parallax depth layers; dolly-zoom for mounting dread
document-typewriter-reveal  | title      | 1 | a document types itself, paced for reading
draw-svg-trace              | material   | 1 | the subject is drawn in as animated line strokes
edit-hook-moves             | brand      | 0 | logo sting on a button press (outro accent)
element-body-moves          | impact     | 1 | squash-and-stretch body language on fast entrances and hovers
fui-hud-moves               | ui         | 0 | sci-fi HUD: panels unfold from lines, reticle lock-on
gauge-readout-moves         | data       | 0 | gauges boot and needles sweep; one big value jump
glow-flyline-moves          | light      | 1 | glowing fly-lines arc between points in a dark scene
gradient-word-sweep         | title      | 1 | one key word supercharged by a gradient sweep
graze-face-tour             | camera     | 1 | low grazing flight across a surface, landmarks rising past the lens
hashtag-to-pill-materialize | ui         | 0 | a typed tag hardens into a UI pill and files itself
hires-rasterize-3d-text     | technique  | 0 | technique card: hi-res rasterized text for 3D zooms
icon-field-colorize         | brand      | 0 | an icon field floods with the brand color in one sweep
icon-performance-moves      | ui         | 0 | icon-level punctuation: success pop, attention bounce
impact-feedback             | impact     | 1 | anime/game-grade hit feedback the instant something lands
input-trigger-moves         | ui         | 0 | first-person input: keys and cursor trigger the product live
integration-hub-map         | ui         | 0 | integration hub: pages flip and route into one product
letterspace-materialize     | title      | 1 | quiet letter-spaced title materializes (chapter card)
light-play-moves            | light      | 1 | light as a brush: sweep reveal, halo crowning, flash on impact
line-boil                   | material   | 1 | hand-drawn line-boil wobble on held strokes
line-carry-transition       | transition | 1 | a drawn line carries the eye from one scene into the next
list-stack-press            | ui         | 0 | new items keep pressing into a living list
magician-card-flourish      | impact     | 1 | a magician's flourish materializes a single card or poster
marker-underline-title      | title      | 1 | hand-drawn marker underline emphasizes one word
montage-rhythm-moves        | rhythm     | 1 | montage breathing: build-and-burst, process quick-cuts, chain-reaction open
morph-from-primitive        | material   | 1 | the subject morphs out of a primitive shape
neon-frame-forerun          | ui         | 0 | a neon frame runs ahead, the panel lands inside it
neon-frame-orbit-drop       | ui         | 0 | a neon frame orbits, then drops the UI into place
neon-triple-marquee         | ui         | 0 | three neon marquee lines pulse the closing slogan
odometer-digit-roll         | data       | 0 | a full-screen odometer rolls up the hero number
outro-group-photo-launch    | outro      | 1 | finale group photo: every hero gathers, formation freeze, launch out
overhead-camera-moves       | camera     | 1 | top-down tabletop drop or slow tilt reveal
page-turn-transitions       | transition | 1 | physical page turn between chapters (barn door, cube rotate)
page-waterfall-wall         | ui         | 0 | a waterfall wall of product pages flows past
panel-grid-moves            | material   | 1 | comic panel grid: beat-lit panels, grid reflow, multi-angle freeze
paper-craft-moves           | material   | 1 | paper-craft world: masking-tape slap, pop-up-book rise
paper-plane-messenger       | transition | 1 | a paper plane flies the story from one scene to another
paper-title-card            | title      | 1 | paper title card as a breathing beat between louder shots
particle-celebrate-hits     | particle   | 1 | confetti / spark celebration burst, then clean stillness
particle-sand-fill          | particle   | 1 | the subject builds up from flowing sand-like particles
pill-slot-cycle             | ui         | 0 | verb pills cycle through a slot-machine slot
print-texture-transitions   | transition | 1 | ink-bleed / print texture develops the next scene
rhythm-interrupt-moves      | rhythm     | 1 | interruption as a beat: stutter push-in, strobe black frames
riso-print-hits             | impact     | 1 | risograph misregistration hit as a print-style accent
row-embed                   | ui         | 0 | structured rows grow into the page one by one
runway-ground-skim          | camera     | 1 | elements drop from above and snap upright as the camera skims the ground
sakuga-timing-shift         | rhythm     | 1 | sakuga timing: slow handcrafted build, then explosive release
scene-locked-title          | title      | 1 | the title lives inside the 3D scene, locked to its space
scroll-brake-moves          | ui         | 0 | a long list scrolls fast, then brakes hard on the big entry
segmented-thumb-hero        | ui         | 0 | a segmented toggle close-up carried as the hero shot
shot-transitions            | transition | 1 | handoff six-pack: whip pan, whip brake, mask wipe, portal wipe
skeleton-reveal             | ui         | 0 | skeleton placeholders leap into the real, living UI
slam-entrance-moves         | impact     | 1 | hero subject slams into frame with perspective snap
smear-multiples             | rhythm     | 1 | comic smear frames and multiples sell extreme speed
space-camera-moves          | camera     | 1 | big 3D showpieces: drone dive landing, exploded view, snorricam lock
spectrum-morph-ui           | ui         | 0 | an audio spectrum morphs into UI dividers, beat-synced
speed-ramp-freeze           | rhythm     | 1 | speed ramp into a freeze to hold the key instant
split-flap-title            | title      | 1 | mechanical split-flap board announces a title or date
spotlight-hero-card         | light      | 1 | a single hero object consecrated by slow light, premium and calm
spotlight-sweep-moves       | light      | 1 | spotlight sweeps wake subjects out of darkness
steep-tilt-glide            | camera     | 1 | steep-perspective glide past successive zones, fixed camera
stroke-segment-build        | title      | 1 | abstract strokes assemble; the meaning lands late (suspense reveal)
tear-streak-transitions     | transition | 1 | glitch tear-streaks rip into the next scene
tension-camera-moves        | camera     | 1 | emotional four: freeze-orbit awe, dutch-roll resolve, slow-push dread, pull-back isolation
text-as-mask                | title      | 1 | the scene lives inside the letters; text is a window
text-column-converge        | ui         | 0 | a spec list converges into the product name
theme-switch-moves          | ui         | 0 | the theme flips before your eyes and ripples across the UI
timeline-travel             | camera     | 1 | horizontal time-travel dash with a hard brake at now
title-demote-to-label       | ui         | 0 | the big title shrinks into a corner label as content takes over
trailer-grammar-moves       | rhythm     | 1 | trailer skeleton: hook open, card/footage cadence, smash-cut climax
transition-hidden-cut       | transition | 1 | invisible cut, light-leak burn, or versus slam between shots
transition-travel           | transition | 1 | travel through a shared element (letterform zoom, element morph)
type-and-filter             | ui         | 0 | type, filter, open: one interaction chain told as a shot
type-assembly-moves         | title      | 1 | letterforms assemble: drift, split-stagger, on-path, tracking reveal
type-entrance-moves         | title      | 1 | title entrances: letter-drop physics, scramble decode
type-rhythm-sync            | title      | 1 | words locked to the beat (weight pump) or to the voice (karaoke fill)
typewriter-moves            | title      | 1 | terminal / typewriter text with corrections and retypes
ui-strip-away-outro         | ui         | 0 | after the final click, all UI strips away to silence
ui-to-brand-morph           | brand      | 0 | the daily UI morphs into the brand logo
voice-waveform-live         | ui         | 0 | a live waveform listens while you speak
wall-reveal-moves           | ui         | 0 | a wall of features lights up in place
wipe-transitions            | transition | 1 | geometric wipes: clock wipe, blinds slice
word-relay-filmstrip        | ui         | 0 | one subject, many verbs: a filmstrip relay of abilities
"""


def energy_class(zh: str) -> str:
    """Classe d'énergie à partir du champ chinois de library.json."""
    s = (zh or "").strip()
    if not s or s.lower().startswith("n/a"):
        return "n/a"
    if "极高" in s or "峰值" in s:
        return "peak"
    if "/" in s:                      # fiche multi-modes (A/B/C…)
        return "varies"
    if "中高" in s:
        return "mid-high"
    if "中低" in s or "低中" in s:
        return "mid-low"
    if "高" in s:
        return "high"
    if "低" in s:
        return "low"
    if "中" in s:
        return "mid"
    return "varies"


def main() -> None:
    skill = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SKILL
    lib = skill / "gallery" / "api" / "library.json"
    data = json.loads(lib.read_text(encoding="utf-8-sig"))
    lib_cards = {c["name"]: c for c in data.get("cards", [])}

    cur = {}
    for line in CURATION.strip().splitlines():
        slug, cat, anim, gloss = (p.strip() for p in line.split("|", 3))
        cur[slug] = {"cat": cat, "anim": anim == "1", "gloss": gloss}

    missing = sorted(set(lib_cards) - set(cur))
    extra = sorted(set(cur) - set(lib_cards))
    if missing or extra:
        raise SystemExit(
            f"Curation désynchronisée du skill.\n  Fiches non curées: {missing}"
            f"\n  Fiches curées absentes du skill: {extra}")

    cards = [{"slug": slug,
              "cat": cur[slug]["cat"],
              "energy": energy_class(lib_cards[slug].get("energy", "")),
              "anim": cur[slug]["anim"],
              "gloss": cur[slug]["gloss"]}
             for slug in sorted(lib_cards)]
    out = {"skill": "video-shotcraft",
           "generated_from": f"gallery/api/library.json (revision "
                             f"{data.get('revision', '?')})",
           "cards": cards}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    n_anim = sum(1 for c in cards if c["anim"])
    print(f"OK: {len(cards)} fiches ({n_anim} anim) -> {OUT}")


if __name__ == "__main__":
    main()
