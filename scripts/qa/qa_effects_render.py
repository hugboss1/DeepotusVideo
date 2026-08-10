"""QA « application au rendu » du rack VFX — effet par effet, mesuré.

Ce harnais ne lit pas le filtergraph : il RE N D des clips par les vrais
chemins de rendu de l'app, extrait des images et les compare au pixel.

Pour CHAQUE effet du catalogue (effects_engine.EFFECTS) et pour CHACUN des
trois chemins de rendu :

  M — Montage, effets par clip      : montage_service._build_montage_command
  G — Studio, effets globaux        : graph_effects.inject_effects -> post_effects
                                      -> template_service.build_ffmpeg_command
  L — Studio, effets par calque     : graph_effects.inject_effects -> region.effects
                                      -> template_service.build_ffmpeg_command

on rend deux vidéos avec la MÊME commande à un détail près : la référence n'a
aucun effet, la vidéo de test porte l'effet borné à [t0, t1] sans rampe. On
compare ensuite, image par image (même index d'image, donc même contenu
source) :

  * au MILIEU de l'intervalle : si l'image de test est identique à la
    référence, l'effet n'a PAS été appliqué -> ECHEC ;
  * AVANT t0 et APRES t1 : si l'image de test diffère de la référence,
    les bornes fuient -> ECHEC.

La « source » de la comparaison est donc le même rendu sans effet : c'est le
seul repère honnête, la source brute étant redimensionnée, recadrée et
ré-encodée par la chaîne avant que l'effet n'intervienne.

Bruit de codec : les deux rendus ne diffèrent que dans l'intervalle, mais le
contrôle de débit de x264 propage un peu cette différence en dehors. Le seuil
de fuite tient compte de ce plancher et le rapport hors/dans est reporté :
une vraie fuite donne un rapport proche de 1, le bruit de codec reste sous
quelques pourcents.

Usage (interpréteur embarqué de l'app) :
    python scripts/qa/qa_effects_render.py [--src <clip.mp4>] [--only nom,nom]
                                           [--paths MGL] [--keep] [--json <f>]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))

# app.config fige ses dossiers à l'import : on l'isole dans un dossier jetable
# pour que le harnais n'écrive jamais dans les données de l'utilisateur.
_SANDBOX = Path(tempfile.mkdtemp(prefix="dzfxqa_data_"))
os.environ.setdefault("DEEPOTUS_DATA_DIR", str(_SANDBOX))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

APP = Path(os.path.expandvars(r"%LOCALAPPDATA%")) / "DeepotusVideoGen"
APPDATA = Path(os.path.expandvars(r"%LOCALAPPDATA%")) / "DeepotusVideoGenData"


def _ffmpeg_bin() -> tuple[str, str]:
    """(ffmpeg, ffprobe). Les services appellent « ffmpeg » nu : on met le
    dossier bin de l'app en tête du PATH pour que la commande RÉELLE marche
    telle quelle, sans la réécrire."""
    binp = APP / "bin"
    if (binp / "ffmpeg.exe").is_file():
        os.environ["PATH"] = str(binp) + os.pathsep + os.environ.get("PATH", "")
        return str(binp / "ffmpeg.exe"), str(binp / "ffprobe.exe")
    ff = shutil.which("ffmpeg")
    if not ff:
        print("ABANDON: ffmpeg introuvable (ni dans l'app, ni dans le PATH).")
        sys.exit(2)
    return ff, shutil.which("ffprobe") or "ffprobe"


FF, FP = _ffmpeg_bin()

from PIL import Image, ImageChops, ImageStat          # noqa: E402
from app.services.effects_engine import EFFECTS, catalog  # noqa: E402
from app.services.montage_service import _build_montage_command  # noqa: E402
from app.services.template_service import build_ffmpeg_command  # noqa: E402
from app.services.graph_effects import inject_effects  # noqa: E402

# ------------------------------------------------------------------ réglages
W, H, FPS = 270, 480, 30      # petit canevas 9:16 : même code, rendu rapide
DUR = 5.0                     # durée du clip de test
T0, T1 = 2.5, 4.0             # intervalle de l'effet
T_IN = 3.25                   # milieu de l'intervalle
T_BEFORE = 0.5                # hors intervalle, avant t0
T_AFTER = 4.7                 # hors intervalle, après t1

#: en dessous, l'image de test est considérée identique à la référence.
SEUIL_APPLIQUE = 1.0
#: au dessus (et si le rapport hors/dans dépasse RAPPORT_FUITE), les bornes fuient.
#: 3.0 = au dessus du plancher de bruit mesuré (~2.1) : les deux rendus ne
#: diffèrent que DANS l'intervalle, mais le contrôle de débit de x264 propage
#: un peu cette différence sur le reste du GOP.
SEUIL_FUITE = 3.0
RAPPORT_FUITE = 0.15


def _params(name: str) -> dict:
    """Paramètres représentatifs pour un effet donné (mêmes valeurs que le
    test d'enveloppe temporelle, pour que les deux se recoupent)."""
    cat = catalog()
    spec = cat.get(name) or cat["grade"]     # « lut » est un alias de grade
    eff = {"type": name, "intensity": 70}
    if "preset" in (spec.get("params") or []) and spec.get("presets"):
        eff["preset"] = spec["presets"][0]
    if name == "letterbox":
        eff["ratio"] = 2.39
    if name == "gradient":
        eff.update({"c0": "#22d3ee", "c1": "#a855f7", "angle": 45,
                    "opacity": 70, "blend": "screen"})
    if name in ("vhs", "shake"):
        eff["speed"] = 50
    return eff


def _borne(eff: dict) -> dict:
    """Même effet, borné à [T0, T1] sans rampe (on teste la porte, pas la
    courbe : une rampe rendrait « appliqué » et « fuite » indissociables)."""
    return {**eff, "t0": T0, "t1": T1, "fade_in": 0, "fade_out": 0}


# ------------------------------------------------------------------- rendus
def _run(cmd, cwd=None, timeout=900):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                       timeout=timeout, encoding="utf-8", errors="replace")
    return r


def render_montage(effects, out: Path, src: Path, src_dur: float):
    """Chemin RÉEL du Montage : un clip V1, effets par clip."""
    v1 = [{"path": src, "src_dur": src_dur, "src_in": 0.0,
           "start": 0.0, "end": DUR,
           "transition": "cut", "transition_s": None,
           "effects": list(effects) if effects else None}]
    cmd, total = _build_montage_command(
        v1, [], [], None, w=W, h=H, fps=FPS, mix_db={}, ducking=False,
        duration_master=True, preview=False, out=out)
    r = _run(cmd)
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        return None, (r.stderr or "")[-700:]
    return cmd, None


def _studio_template(src: Path):
    return {
        "canvas": {"width": W, "height": H, "fps": FPS, "duration_s": DUR,
                   "background_color": "#000000"},
        "regions": [{"id": "r0", "type": "video_slot", "slot_name": "clip",
                     "x": 0, "y": 0, "width": W, "height": H,
                     "fit": "cover", "z_index": 0, "audio_volume": 0}],
    }


def _studio_graph(effects, src: Path, target: str):
    """Graphe Studio minimal : un noeud source + un noeud Effects.
    target = "all" (post_effects) ou l'id du noeud source (effets par calque)."""
    return {"nodes": [
        {"id": "src1", "type": "Upload", "props": {"filename": src.name}},
        {"id": "fx1", "type": "Effects",
         "props": {"effects": list(effects or []), "targets": [target]}},
    ], "edges": []}


def render_studio(effects, out: Path, src: Path, work: Path, *, scope: str):
    """Chemin RÉEL du graphe Studio : inject_effects puis build_ffmpeg_command.
    scope = "global" -> post_effects ; "layer" -> effects sur la région."""
    tpl = _studio_template(src)
    sv = {"clip": {"path": str(src), "source_kind": "upload",
                   "upload_filename": src.name}}
    if effects:
        target = "all" if scope == "global" else "src1"
        tpl = inject_effects(tpl, _studio_graph(effects, src, target), sv)
        attach = (tpl.get("post_effects") if scope == "global"
                  else tpl["regions"][0].get("effects"))
        if not attach:
            return None, f"inject_effects n'a rien attaché ({scope})"
    work.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_command(None, tpl, sv, out, work)
    r = _run(cmd, cwd=str(work))
    if r.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        return None, (r.stderr or "")[-700:]
    return cmd, None


PATHS = {
    "M": ("Montage (effets par clip)", "montage"),
    "G": ("Studio graphe (post_effects)", "global"),
    "L": ("Studio graphe (par calque)", "layer"),
}


def render(path_key, effects, out, src, src_dur, work):
    if path_key == "M":
        return render_montage(effects, out, src, src_dur)
    return render_studio(effects, out, src, work, scope=PATHS[path_key][1])


# ------------------------------------------------------------------ mesures
_FRAMES: dict = {}


def frame(video: Path, t: float) -> Image.Image:
    """Image à l'instant t, extraite PAR INDEX (round(t*fps)) : deux rendus de
    même durée et même cadence donnent ainsi la même image source."""
    n = int(round(t * FPS))
    key = (str(video), n)
    if key in _FRAMES:
        return _FRAMES[key]
    png = video.with_name(f"{video.stem}_f{n}.png")
    r = _run([FF, "-y", "-v", "error", "-i", str(video),
              "-vf", f"select=eq(n\\,{n})", "-fps_mode", "passthrough",
              "-frames:v", "1", str(png)], timeout=180)
    if not png.exists():
        raise RuntimeError(f"extraction image {n} de {video.name} : "
                           f"{(r.stderr or '')[-300:]}")
    im = Image.open(png).convert("RGB")
    im.load()
    _FRAMES[key] = im
    return im


def ecart(a: Image.Image, b: Image.Image) -> tuple[float, float]:
    """(moyenne des |différences| RGB sur 0-255, % de pixels changés > 8)."""
    d = ImageChops.difference(a, b)
    moy = sum(ImageStat.Stat(d).mean) / 3.0
    g = d.convert("L")
    h = g.histogram()
    tot = sum(h) or 1
    pct = 100.0 * sum(h[9:]) / tot
    return moy, pct


# -------------------------------------------------------------------- rapport
def _row(cells, widths):
    return "  ".join(str(c).ljust(w)[:w] for c, w in zip(cells, widths))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--paths", default="MGL")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--json", default="")
    ap.add_argument("--skip-cumul", action="store_true")
    args = ap.parse_args()

    # --- source : un rendu déjà présent, jamais de génération payante -------
    def _dur(p: Path) -> float:
        o = _run([FP, "-v", "error", "-show_entries", "format=duration",
                  "-of", "csv=p=0", str(p)]).stdout.strip()
        try:
            return float(o)
        except ValueError:
            return 0.0

    def _luma(p: Path) -> float:
        """Luminance moyenne d'une image du clip. Un plan quasi noir écrase
        tous les effets : « noir puis sépia » et « sépia puis noir » y rendent
        la même image, et le test d'ORDRE ne mesure plus rien. On choisit donc
        une source claire, pas la première venue."""
        png = Path(tempfile.gettempdir()) / f"dzfxqa_probe_{p.stem[:8]}.png"
        _run([FF, "-y", "-v", "error", "-ss", "1", "-i", str(p),
              "-frames:v", "1", str(png)], timeout=120)
        if not png.exists():
            return 0.0
        try:
            im = Image.open(png).convert("L")
            return ImageStat.Stat(im).mean[0]
        finally:
            png.unlink(missing_ok=True)

    src, src_dur = None, 0.0
    if args.src:
        src = Path(args.src)
        src_dur = _dur(src)
    else:
        best = None
        for c in sorted((APPDATA / "assets" / "outputs" / "final").glob("*.mp4")):
            if c.stat().st_size < 400_000:
                continue
            d = _dur(c)
            if d < DUR + 0.5:
                continue
            lum = _luma(c)
            if best is None or lum > best[2]:
                best = (c, d, lum)
            if lum >= 90:                     # assez clair, on s'arrête là
                break
        if best:
            src, src_dur = best[0], best[1]
            print(f"source retenue : luminance moyenne {best[2]:.1f}/255")
    if not src or not src.is_file():
        print("ABANDON: aucun clip source (passer --src <fichier.mp4>).")
        return 2
    if src_dur < DUR + 0.2:
        print(f"ABANDON: source trop courte ({src_dur:.2f}s < {DUR + 0.2}s).")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="dzfxqa_"))
    names = [n for n in EFFECTS]
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        names = [n for n in names if n in want]
    keys = [k for k in args.paths.upper() if k in PATHS]

    print("=" * 78)
    print("QA VFX — application au rendu (mesurée, pas déduite)")
    print("=" * 78)
    print(f"source        : {src}")
    print(f"durée source  : {src_dur:.2f}s -> clip de test {DUR}s @ {W}x{H} {FPS}fps")
    print(f"intervalle    : t0={T0}s t1={T1}s (aucune rampe)")
    print(f"échantillons  : dans={T_IN}s  avant={T_BEFORE}s  après={T_AFTER}s")
    print(f"effets        : {len(names)}  |  chemins : {', '.join(keys)}")
    print(f"travail       : {tmp}")
    print()

    results = {}
    t_start = time.time()

    for k in keys:
        label, _ = PATHS[k]
        print("-" * 78)
        print(f"[{k}] {label}")
        print("-" * 78)
        work = tmp / f"work_{k}"
        base = tmp / f"{k}_base.mp4"
        cmd, err = render(k, None, base, src, src_dur, work)
        if err:
            print(f"  ABANDON du chemin : référence sans effet en échec — {err}")
            results[k] = {"error": err}
            continue
        print(f"  référence sans effet : {base.name} "
              f"({base.stat().st_size // 1024} Ko)")
        # Contrôle : deux rendus identiques doivent donner des images identiques.
        ctrl = tmp / f"{k}_base2.mp4"
        render(k, None, ctrl, src, src_dur, work)
        c_in = ecart(frame(base, T_IN), frame(ctrl, T_IN))[0]
        print(f"  contrôle déterminisme (même commande deux fois) : "
              f"écart moyen = {c_in:.4f}")
        print()
        print("  " + _row(["effet", "dans", "%chg", "avant", "après",
                           "rapport", "verdict"],
                          [12, 8, 7, 8, 8, 8, 26]))
        rows = {}
        for name in names:
            eff = _borne(_params(name))
            outp = tmp / f"{k}_{name}.mp4"
            cmd, err = render(k, [eff], outp, src, src_dur, work)
            if err:
                rows[name] = {"status": "RENDU EN ECHEC", "err": err}
                print("  " + _row([name, "-", "-", "-", "-", "-",
                                   "RENDU EN ECHEC"],
                                  [12, 8, 7, 8, 8, 8, 26]))
                continue
            m_in, p_in = ecart(frame(base, T_IN), frame(outp, T_IN))
            m_b, _ = ecart(frame(base, T_BEFORE), frame(outp, T_BEFORE))
            m_a, _ = ecart(frame(base, T_AFTER), frame(outp, T_AFTER))
            m_out = max(m_b, m_a)
            ratio = (m_out / m_in) if m_in > 0.0001 else 0.0
            applique = m_in >= SEUIL_APPLIQUE
            fuite = m_out >= SEUIL_FUITE and ratio >= RAPPORT_FUITE
            if not applique:
                verdict = "ECHEC non appliqué"
            elif fuite:
                verdict = "ECHEC bornes qui fuient"
            else:
                verdict = "ok"
            rows[name] = {"status": verdict, "in": round(m_in, 3),
                          "pct_in": round(p_in, 2), "before": round(m_b, 3),
                          "after": round(m_a, 3), "ratio": round(ratio, 4)}
            print("  " + _row([name, f"{m_in:.3f}", f"{p_in:.1f}",
                               f"{m_b:.3f}", f"{m_a:.3f}", f"{ratio:.3f}",
                               verdict], [12, 8, 7, 8, 8, 8, 26]))
        results[k] = {"control": round(c_in, 4), "effects": rows}
        bad = [n for n, r in rows.items() if r["status"] != "ok"]
        print(f"  -> {len(rows) - len(bad)}/{len(rows)} ok"
              + (f" | échecs : {', '.join(bad)}" if bad else ""))
        print()

    # ------------------------------------------------------------- cumul ----
    if not args.skip_cumul and keys:
        k = keys[0]
        work = tmp / f"work_{k}"
        print("-" * 78)
        print(f"[CUMUL] trois effets empilés — chemin {k} ({PATHS[k][0]})")
        print("-" * 78)
        # Trio sensible à l'ORDRE, sans ambiguïté possible : « noir » désature,
        # donc la colorisation sépia posée APRÈS teinte réellement l'image,
        # alors que dans l'autre sens le noir et blanc repasse derrière et
        # efface la teinte. La vignette assombrit le résultat, pas l'inverse.
        trio = [_params("grade"), _params("colorize"), _params("vignette")]
        trio[0]["preset"] = "noir"
        trio[1]["preset"] = "sepia"
        base = tmp / f"{k}_base.mp4"
        cum = {}

        def _r(tag, effs):
            p = tmp / f"cumul_{tag}.mp4"
            _c, e = render(k, effs, p, src, src_dur, work)
            if e:
                print(f"  {tag}: RENDU EN ECHEC — {e[:200]}")
                return None
            return p

        plein = _r("plein", trio)                      # les 3, sans bornes
        borne = _r("borne", [{**e, "t0": T0, "t1": T1,
                              "fade_in": 0, "fade_out": 0} for e in trio])
        inverse = _r("inverse", list(reversed(trio)))  # ordre inversé
        seuls = {}
        stag = [(T0, T1), (T0, T1), (T0, T1)]
        for i, e in enumerate(trio):
            seuls[i] = _r(f"seul{i}", [e])
        # décalés : chaque effet a sa propre fenêtre, jamais superposée
        fen = [(0.6, 1.6), (1.8, 2.8), (3.0, 4.0)]
        dec = _r("decales", [{**e, "t0": f[0], "t1": f[1],
                              "fade_in": 0, "fade_out": 0}
                             for e, f in zip(trio, fen)])
        cumul_ok = True

        def check(txt, cond, detail=""):
            nonlocal cumul_ok
            print(f"  {'PASS' if cond else 'ECHEC'}  {txt} {detail}")
            if not cond:
                cumul_ok = False

        if plein and borne:
            # Force de la pile (référence d'échelle) : sans elle, « écart 5 »
            # ne veut rien dire. On exige que l'écart enveloppe/sans-enveloppe
            # reste petit DEVANT l'effet lui-même.
            force = ecart(frame(base, T_IN), frame(plein, T_IN))[0]
            d = ecart(frame(plein, T_IN), frame(borne, T_IN))[0]
            cum["force_pile"] = round(force, 3)
            cum["borne_vs_plein_dans"] = round(d, 3)
            check("dans l'intervalle, les 3 bornés == les 3 sans bornes",
                  d < max(2.0, 0.10 * force),
                  f"(écart {d:.3f} pour une pile qui pèse {force:.3f})")
            d2 = ecart(frame(base, T_BEFORE), frame(borne, T_BEFORE))[0]
            cum["borne_vs_base_avant"] = round(d2, 3)
            check("hors intervalle, les 3 bornés == aucun effet",
                  d2 < SEUIL_FUITE, f"(écart {d2:.3f})")
        if plein and inverse:
            d = ecart(frame(plein, T_IN), frame(inverse, T_IN))[0]
            cum["ordre"] = round(d, 3)
            check("l'ORDRE de la pile est respecté (inversé != direct)",
                  d > 2.0, f"(écart {d:.3f})")
        if dec and all(seuls.values()):
            for i, (f0, f1) in enumerate(fen):
                t = (f0 + f1) / 2.0
                d = ecart(frame(dec, t), frame(seuls[i], t))[0]
                fo_i = ecart(frame(base, t), frame(seuls[i], t))[0]
                cum[f"decale_{i}"] = round(d, 3)
                cum[f"decale_{i}_force"] = round(fo_i, 3)
                # Deux rendus DIFFÉRENTS : le contrôle de débit de x264 seul
                # produit déjà ~2 d'écart moyen. On exige donc « proche de
                # l'effet seul » relativement à ce que pèse cet effet.
                check(f"fenêtre {i + 1} (t={t}s) : seul l'effet {i + 1} agit, "
                      f"identique à l'effet {i + 1} seul",
                      d < max(3.0, 0.12 * fo_i),
                      f"(écart {d:.3f} pour un effet qui pèse {fo_i:.3f})")
        results["cumul"] = {"ok": cumul_ok, "mesures": cum}
        print()

    dt = time.time() - t_start
    print("=" * 78)
    tot = ko = 0
    for k in keys:
        r = results.get(k) or {}
        for n, e in (r.get("effects") or {}).items():
            tot += 1
            if e["status"] != "ok":
                ko += 1
                print(f"  ECHEC  [{k}] {n} : {e['status']}")
    print(f"  {tot - ko}/{tot} couples (effet, chemin) ok — {dt:.0f}s")
    if "cumul" in results:
        print(f"  cumul : {'ok' if results['cumul']['ok'] else 'ECHEC'}")
    print("=" * 78)

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2,
                                              ensure_ascii=False),
                                   encoding="utf-8")
        print(f"JSON : {args.json}")
    if args.keep:
        print(f"rendus conservés : {tmp}")
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(_SANDBOX, ignore_errors=True)
    return 1 if (ko or not results.get("cumul", {"ok": True})["ok"]) else 0


if __name__ == "__main__":
    sys.exit(main())
