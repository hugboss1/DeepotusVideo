# -*- coding: utf-8 -*-
"""t318 (28/10/2026) (D4, tâche 4) — le direct côté écran : dz-live-logique.js (joué sous node), dz-live.js (lu),
textes live.json, copies et chargement. Plan docs/superpowers/plans/2026-10-28-t318-live.md, spec §8.2, §8.6.
  [L] logique pure : format d'encodage (H.264 d'abord), corps d'ajout d'une destination (champs requis), lien public,
      santé du flux, débit, instant d'un marqueur, message d'annonce ;
  [T] textes : chaque clé live.* employée existe en FR et EN (préfixes dynamiques compris), variables identiques ;
  [S] sécurité : le bloc d'ajout porte data-dz-secret, la clé est un champ mot de passe, aucune valeur de champ secret
      ni clé n'est lue pour l'affichage, le direct encode scene.flux() + la voix de la session (jamais une autre
      composition), l'écran de repli reste sous le caviardage (z < 900), aucun envoi avant le clic « Passer en direct » ;
  [C] copies octet pour octet dans dist, index.html charge dz-live.js APRÈS dz-capture.js, aucun maillon de bundle.
Run (depuis backend/) : & $PY tests/test_live_ecran.py"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
SH = REPO / "frontend" / "shared"
DIST = REPO / "frontend" / "dist"
NODE = shutil.which("node")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


TXT = (SH / "dz-live.js").read_text("utf-8")
LOG = (SH / "dz-live-logique.js").read_text("utf-8")
DICO = json.loads((SH / "i18n" / "live.json").read_text("utf-8"))


def node(script: str) -> dict:
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzlivejs_"))
    f = d / "banc.mjs"
    f.write_text(script, "utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = r.stdout.strip().splitlines()
    if r.returncode or not out:
        raise RuntimeError((r.stderr or r.stdout)[-1500:])
    return json.loads(out[-1])


print("[L] dz-live-logique.js")
if not NODE:
    check("L0 node présent", False)
else:
    L = node(r"""
import * as L from %s;
const T = (k, v) => k + (v ? JSON.stringify(v) : "");
const tw = {plateforme: "twitch", handle: "@ma_chaine", champs: [{nom: "TWITCH_STREAM_KEY", secret: true, pose: true}, {nom: "TWITCH_SERVEUR", secret: false, valeur: ""}]};
const yt = {plateforme: "youtube_live", handle: "", champs: [{nom: "YOUTUBE_LIVE_LIEN", secret: false, valeur: "https://youtube.com/live/x"}]};
console.log(JSON.stringify({
  mime: [L.choisirMimeLive(() => true), L.choisirMimeLive((m) => !m.includes("h264")), L.choisirMimeLive(() => false),
         L.choisirMimeLive(() => { throw new Error("x"); })],
  ajoutTw: L.corpsAjout("twitch", {libelle: " Chaîne ", handle: "@ma_chaine", cle: " live_1 ", serveur: ""}),
  ajoutKickSansServeur: L.corpsAjout("kick", {cle: "sk"}),
  ajoutRtmpSansCle: L.corpsAjout("rtmp", {serveur: "rtmp://h/app"}),
  ajoutTwSansCle: L.corpsAjout("twitch", {cle: "  "}),
  ajoutDiscord: L.corpsAjout("discord", {cle: "https://discord.com/api/webhooks/1/x", serveur: "ignoré"}),
  inconnu: L.corpsAjout("x", {cle: "a"}),
  liens: [L.lienDe(tw), L.lienDe(yt), L.lienDe({plateforme: "kick", handle: "a b"}), L.lienDe(null)],
  niveaux: [L.niveauFlux(null), L.niveauFlux({etat: "demarrage"}), L.niveauFlux({etat: "en_direct", vitesse: 1, fps: 30}),
            L.niveauFlux({etat: "en_direct", vitesse: 0.7, fps: 30}), L.niveauFlux({etat: "arrete"}), L.niveauFlux({etat: "en_panne"})],
  debits: [L.formatDebit(4500, "fr"), L.formatDebit(4500, "en"), L.formatDebit(850), L.formatDebit(null)],
  instants: [L.instantMarqueur(5000.4, 1000), L.instantMarqueur(10, 50)],
  annonces: [L.messageAnnonce("", T), L.messageAnnonce(" Atelier ", T)],
  morceau: L.MORCEAU_MS, plateformes: L.PLATEFORMES,
}));
""" % json.dumps((SH / "dz-live-logique.js").resolve().as_uri()))
    check("L1 H.264 d'abord, puis VP8 ; rien si rien n'est lu ; une exception n'arrête pas le choix",
          L["mime"] == ["video/webm;codecs=h264,opus", "video/webm;codecs=vp8,opus", "", ""], L["mime"])
    check("L2 ajout Twitch : clé et libellé nettoyés, @ du handle retiré, serveur vide omis",
          L["ajoutTw"] == {"plateforme": "twitch", "libelle": "Chaîne", "handle": "ma_chaine", "valeurs": {"TWITCH_STREAM_KEY": "live_1"}},
          L["ajoutTw"])
    check("L3 requis : Kick sans serveur et Twitch sans clé refusés ; RTMP sans clé accepté ; Discord sans serveur",
          L["ajoutKickSansServeur"] is None and L["ajoutTwSansCle"] is None and L["inconnu"] is None
          and L["ajoutRtmpSansCle"]["valeurs"] == {"RTMP_SERVEUR": "rtmp://h/app"}
          and L["ajoutDiscord"]["valeurs"] == {"DISCORD_WEBHOOK": "https://discord.com/api/webhooks/1/x"})
    check("L4 lien public : handle Twitch, lien YouTube posé, handle invalide vide",
          L["liens"] == ["https://www.twitch.tv/ma_chaine", "https://youtube.com/live/x", "", ""], L["liens"])
    check("L5 santé : attente, bon, faible (vitesse < 0,9), coupé (arrêté, toutes en panne)",
          L["niveaux"] == ["attente", "attente", "bon", "faible", "coupe", "coupe"], L["niveaux"])
    check("L6 débit lisible FR/EN", L["debits"] == ["4,5 Mb/s", "4.5 Mb/s", "850 kb/s", "—"], L["debits"])
    check("L7 marqueur en ms depuis le début de la capture, jamais négatif", L["instants"] == [4000, 0])
    check("L8 annonce par défaut, avec le titre", L["annonces"] == ["live.annonce.defaut", 'live.annonce.defaut_titre{"titre":"Atelier"}'])
    check("L9 morceaux de 250 ms ; plateformes = comptes.LIVE", L["morceau"] == 250
          and set(L["plateformes"]) == {"twitch", "youtube_live", "kick", "rtmp", "discord"})

print("[T] textes")
cles = set(re.findall(r'"(live\.[a-z0-9_.]+)"', TXT + LOG))
fixes = {c for c in cles if not c.endswith((".", "_"))}
prefixes = {"live.etat.": ["ok", "attente", "panne"], "live.niveau.": ["bon", "faible", "coupe", "attente"],
            "live.plateforme.": ["twitch", "youtube_live", "kick", "rtmp", "discord"],
            "live.ajout.aide_": ["twitch", "youtube_live", "kick", "rtmp", "discord"]}
dyn = {p + s for p, l in prefixes.items() for s in l}
check("T1 chaque clé employée existe (fixes et dynamiques)", (fixes | dyn) <= set(DICO), sorted((fixes | dyn) - set(DICO)))
check("T2 aucune clé orpheline dans live.json", set(DICO) <= (fixes | dyn), sorted(set(DICO) - (fixes | dyn)))
var = lambda s: sorted(re.findall(r"\{(\w+)\}", s))                 # noqa: E731
check("T3 FR et EN non vides, mêmes variables", all(v["fr"].strip() and v["en"].strip() and var(v["fr"]) == var(v["en"])
                                                    for v in DICO.values()))
check("T4 le guide Discord dit qu'aucune vidéo n'y entre (spec §8.6)", "ne reçoit pas de vidéo" in DICO["live.annonce.guide"]["fr"])
check("T5 dico assemblé à jour", subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"],
                                                capture_output=True).returncode == 0)

print("[S] sécurité")
bloc = TXT[TXT.index("const noeud = el(\"div\""):TXT.index("peindre();\n      return noeud;")]
check("S1 le bloc d'ajout porte data-dz-secret (flouté et caviardé si filmé)", '"data-dz-secret": true' in bloc)
check("S2 la clé (et le webhook) se saisit dans un champ mot de passe, sans saisie automatique",
      re.search(r'const cle = el\("input", \{ type: "password",[^}]*autocomplete: "off"', TXT) is not None)
check("S3 aucune valeur de champ SECRET n'est lue pour l'affichage (seuls les champs publics : !ch.secret)",
      "if (!ch.secret) pub[ch.nom] = ch.valeur" in LOG and ".champs" not in TXT)
check("S4 la clé saisie est effacée après l'enregistrement et à l'annulation", TXT.count('cle.value = ""') >= 2)
check("S5 le direct encode scene.flux() + la voix de la session (jamais une autre composition)",
      "ses.scene.flux(30).getVideoTracks()" in TXT and "ses.audio.getAudioTracks()" in TXT
      and "captureStream" not in TXT and "getDisplayMedia" not in TXT)
check("S6 écran de repli sous le caviardage (z 790 < 900)", 'id: "live-ecran", z: 790' in TXT)
i_ws = TXT.index("new WebSocket(")
check("S7 rien ne part avant « Passer en direct » : WebSocket et session ouverts dans demarrer() seulement",
      TXT.count("new WebSocket(") == 1 and TXT.rfind("async function demarrer(", 0, i_ws) > TXT.rfind("function ouvrir(", 0, i_ws)
      and TXT.count('"/api/live/sessions"') == 1)
check("S8 aucune journalisation (console) ni stockage local d'une clé", "console." not in TXT and "setItem" not in TXT)
check("S9 nos contrôles portent data-dz-capture-ui (jamais dans la piste des clics)",
      TXT.count('"data-dz-capture-ui": true') >= 3)

check("S10 la pause coupe le son du DIRECT (pistes clonées), pas celui de l'enregistrement ; pistes coupées à la fin",
      "x.clone()" in TXT and "p.enabled = !direct.pause" in TXT and "d.audio.forEach(couperPiste)" in TXT)
check("S11 engorgement : aucun morceau jeté au milieu du WebM, le direct s'arrête proprement",
      "direct.engorge = true" in TXT and "arreter();" in TXT and "perdus++" not in TXT)
check("S12 une panne entre la capture et le WebSocket coupe la capture et abandonne le direct",
      "await abandon();" in TXT and "await cap.arreter();" in TXT)
print("[C] copies et chargement")
for f in ("dz-live.js", "dz-live-logique.js"):
    check(f"C1 {f} copié octet pour octet dans dist", (SH / f).read_bytes() == (DIST / "shared" / f).read_bytes())
idx = (DIST / "index.html").read_text("utf-8")
check("C2 index.html charge dz-live.js (module) après dz-capture.js",
      idx.count('<script type="module" src="/shared/dz-live.js"></script>') == 1
      and idx.index("/shared/dz-capture.js") < idx.index("/shared/dz-live.js"))
check("C3 aucun maillon de bundle pour ce lot", not (REPO / "scripts" / "patch_bundle_dzlive.py").exists())

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
