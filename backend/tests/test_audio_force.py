"""t483 (F6.6, lot « Fiches modèle ») — modèles vidéo sans interrupteur de son (`audio_force`).

MiniMax H3, Gemini Omni (deux voies), Kling v3 Turbo Pro et Kling 4.0 n'ont pas d'interrupteur : ils livrent toujours
une piste. Le pipeline la retire au téléchargement (`couper_piste_imposee`, ffmpeg -an, vidéo copiée sans
réencodage), pour que la règle de l'app (« l'audio est posé par l'app ») vaille pour tous les modèles. Un échec
ffmpeg ne perd jamais le clip payé.

Run: <python embarqué> backend/tests/test_audio_force.py
"""
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")

from app.services import fal_service as FS, finition as FI, modeles_fiches as MF  # noqa: E402

ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


FORCES = {"h3-max", "gemini-omni-flash", "gemini-omni-flash-google", "kling-v3-turbo-pro", "kling-v4"}
TMP = pathlib.Path(tempfile.mkdtemp(prefix="audio_force_"))


def clip(nom, son=True):
    """Un clip de 1 s (vidéo testsrc, et un sinus si `son`), fait par le ffmpeg de l'app."""
    p = TMP / nom
    cmd = [FI._bin("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=10:duration=1"]
    if son:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=60)
    return p


def flux_video(p):
    """Empreinte md5 des paquets du flux vidéo (copiés tels quels) : un réencodage la change."""
    r = subprocess.run([FI._bin("ffmpeg"), "-v", "error", "-i", str(p), "-map", "0:v", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True, timeout=30)
    return r.stdout.strip()


def bloc_registre():
    print("\n[1] registre")
    V = FS.VIDEO_MODELS
    vus = {k for k, m in V.items() if m.get("audio_force")}
    check("1.1 audio_force : exactement les cinq modèles sans interrupteur qui livrent une piste", vus == FORCES, vus ^ FORCES)
    check("1.2 aucun audio_force n'a d'interrupteur (sinon on le couperait, pas besoin de retirer)",
          all(not V[k]["audio_param"] for k in vus))
    check("1.3 Seedance 1.0 Pro (muet par nature) n'est pas marqué", not V["seedance-v1-pro"].get("audio_force"))
    sans = {k for k, m in V.items() if not m.get("audio_param") and not m.get("audio_force") and not FS.est_retire(m)}
    check("1.4 parmi les modèles actifs, seul Seedance 1.0 Pro reste sans interrupteur ni retrait", sans == {"seedance-v1-pro"},
          sans)


def bloc_retrait():
    print("\n[2] retrait de la piste (ffmpeg réel)")
    p = clip("force.mp4")
    v0 = flux_video(p)
    check("2.0 témoin : le clip de test a une piste", FI.a_une_piste_audio(p))
    r = FS.couper_piste_imposee(FS.VIDEO_MODELS["kling-v4"], p)
    check("2.1 modèle audio_force : piste retirée, vrai rendu", r is True and not FI.a_une_piste_audio(p))
    check("2.2 vidéo copiée telle quelle (paquets identiques, aucun réencodage)", v0.startswith("MD5=") and flux_video(p) == v0, (v0, flux_video(p)))
    check("2.3 aucun fichier temporaire laissé", not list(TMP.glob("*_sanspiste*")))
    q = clip("libre.mp4")
    r = FS.couper_piste_imposee(FS.VIDEO_MODELS["seedance-2.5"], q)
    check("2.4 modèle avec interrupteur : rien touché", r is False and FI.a_une_piste_audio(q))
    m = clip("muet.mp4", son=False)
    t0 = m.stat().st_mtime_ns
    r = FS.couper_piste_imposee(FS.VIDEO_MODELS["h3-max"], m)
    check("2.5 clip déjà muet : rien réécrit", r is False and m.stat().st_mtime_ns == t0)
    b = clip("panne.mp4")
    taille = b.stat().st_size
    bin0 = FI._bin
    FI._bin = lambda nom: "ffmpeg-introuvable-xyz" if nom == "ffmpeg" else bin0(nom)
    try:
        r = FS.couper_piste_imposee(FS.VIDEO_MODELS["gemini-omni-flash"], b)
    except Exception as e:  # noqa: BLE001
        r = e
    finally:
        FI._bin = bin0
    check("2.6 ffmpeg en panne : ne lève pas, rend faux, le clip payé reste entier",
          r is False and b.exists() and b.stat().st_size == taille and FI.a_une_piste_audio(b), r)
    check("2.7 modèle vide ou None : rien", FS.couper_piste_imposee({}, b) is False and FS.couper_piste_imposee(None, b) is False)


def bloc_pipeline():
    print("\n[3] pipeline")
    t = (ROOT / "backend/app/services/pipeline.py").read_text(encoding="utf-8")
    check("3.1 le job vidéo retire la piste juste après le téléchargement (avant le lip-sync)",
          "await video_client.download_video(video_url, video_dest)\n"
          "                # t483 (F6.6)" in t.replace("\r\n", "\n")
          and "await asyncio.to_thread(couper_piste_imposee, model, video_dest)" in t
          and t.index("couper_piste_imposee, model, video_dest") < t.index("_lip = getattr(request, \"lipsync\""))
    check("3.2 le clip de scène (Chapitres, épisodes) aussi",
          "await asyncio.to_thread(couper_piste_imposee, model, dest)\n        return dest" in t.replace("\r\n", "\n"))
    check("3.3 les deux seuls appels generate_video du pipeline sont couverts",
          t.count(".generate_video(") == 4 and t.count("couper_piste_imposee, model,") == 2)


def bloc_fiches():
    print("\n[4] fiches")
    for lang, mot in (("fr", "retiré"), ("en", "removed")):
        b = MF.bloc_membres(MF.membres(MF.charger(lang)["kling"]["meta"]), lang)
        ligne = [l for l in b.splitlines() if "kling-v4" in l or "Kling 4.0" in l]
        check(f"4.1 Membres {lang} : Kling 4.0 dit « {mot} »", ligne and mot in ligne[0], ligne)
        ligne = [l for l in b.splitlines() if "kling-v3-pro" in l or "Kling v3 Pro" in l]
        check(f"4.2 Membres {lang} : Kling v3 Pro reste « coupé/off »", ligne and ("coupé" in ligne[0] or "off" in ligne[0]))
    for f in ("gemini-omni", "minimax-video", "kling"):
        for lang in ("fr", "en"):
            txt = (ROOT / f"docs/agent/modeles/{lang}/{f}.md").read_text(encoding="utf-8")
            vieux = ("remplacer au montage", "remplacer la piste", "replace it in the edit", "replace the track",
                     "piste son gardée", "track kept", "Sound:", "peut arriver avec une piste", "may arrive with")
            check(f"4.3 {lang}/{f} : la fiche dit que la piste est retirée (plus « à remplacer » ni « à garder »)",
                  not any(v in txt for v in vieux) and ("retir" in txt or "remov" in txt),
                  [v for v in vieux if v in txt])
    check("4.4 contrat des fiches toujours tenu", MF.verifier() == [] if hasattr(MF, "verifier") else True,
          MF.verifier()[:3] if hasattr(MF, "verifier") else "")


if __name__ == "__main__":
    bloc_registre()
    bloc_retrait()
    bloc_pipeline()
    bloc_fiches()
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
