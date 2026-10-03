# -*- coding: utf-8 -*-
"""Tache #76 du suivi (03/10/2026) — les blocs `transitions` MORTS des gabarits, convertis.
Le bloc PLURIEL `transitions` au niveau du gabarit n'etait lu par personne (plan-templates T9, « dette nommee ») : cinq
des neuf gabarits livres en portaient un rempli, quatre gabarits personnels de l'utilisateur aussi.
DECISIONS DE L'UTILISATEUR (03/10) : livres ET personnels, A LA LECTURE (le fichier de l'utilisateur n'est pas reecrit ;
une animation deja posee sur la region l'emporte) ; « cyan_flash » = « 1+2 » : un VRAI flash de couleur (cyan de la
marque par defaut, `color` au choix), le flash blanc restant `flash`.
Mesure qui fonde le flash (ffmpeg 9.0.1) : fondu enchaine + couleur pleine creee DANS le graphe en rgba, opacite qui
monte puis redescend -> au milieu de la jonction (0,227,253) pour #00e5ff, duree totale inchangee.
Temoin positif : la base (569552b4) n'a pas la conversion et ses gabarits livres portent le bloc.
Run (depuis backend/) : & $PY tests/test_templates_transitions.py"""
import copy, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dztrans_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "FAL_KEY", "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "569552b4"
def base(chemin):
    return subprocess.run(["git", "show", f"{BASE}:{chemin}"], capture_output=True, cwd=str(RACINE)).stdout.decode("utf-8")

LIVRES = sorted(p.name for p in (_ICI.parent / "app" / "templates").glob("tpl_*.json"))
check("T1 temoin : la base n'a pas la conversion, et 5 de ses 9 gabarits livres portent un bloc `transitions` rempli",
      "convertir_transitions" not in base("backend/app/services/template_anim.py") and len(LIVRES) == 9
      and sum(1 for n in LIVRES if json.loads(base(f"backend/app/templates/{n}")).get("transitions")) == 5)

from PIL import Image                                               # noqa: E402
from app.services import template_anim as TA                        # noqa: E402
from app.services import template_service as TSV                    # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
from app.config import settings                                     # noqa: E402
E = TemplateEngine()
FF = shutil.which("ffmpeg")
IMG = pathlib.Path(settings.images_path)
Image.new("RGB", (64, 64), (255, 0, 0)).save(IMG / "rouge.png")
Image.new("RGB", (64, 64), (0, 0, 255)).save(IMG / "bleu.png")
conv = getattr(TA, "convertir_transitions", None)


def reg(i, t, x=0, y=0, w=100, h=100, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, **kw):
    return dict({"id": "tpl_t", "name": "t", "canvas": {"width": 160, "height": 160, "fps": 20, "duration_s": 4,
                                                        "background_color": "#101010"}, "regions": regions}, **kw)


def proche(p, q, tol=14):
    return all(abs(a - b) <= tol for a, b in zip(p, q))


print("[L] les gabarits livres")
lus = {n: json.loads((_ICI.parent / "app" / "templates" / n).read_text(encoding="utf-8")) for n in LIVRES}
check("L1 plus AUCUN gabarit livre ne porte de bloc `transitions`", all("transitions" not in d for d in lus.values()),
      [n for n, d in lus.items() if "transitions" in d])
check("L2 chaque gabarit livre est EXACTEMENT la conversion de celui de la base (rien d'autre n'a bouge)",
      conv is not None and all(lus[n] == conv(json.loads(base(f"backend/app/templates/{n}"))) for n in LIVRES))
def anim(n, rid):
    return next(r for r in lus[n]["regions"] if r["id"] == rid).get("animation")
def trans(n, rid):
    return next(r for r in lus[n]["regions"] if r["id"] == rid).get("transition")
check("L3 les fondus d'entree sont la ou le bloc les annoncait (cases, delais, durees)",
      anim("tpl_news_reel.json", "r_reel") == {"in": {"type": "fade", "duration": 0.4}}
      and anim("tpl_news_reel.json", "r_avatar") == {"in": {"type": "fade", "duration": 0.5, "delay": 0.3}}
      and anim("tpl_alpha_reel_60_30_10.json", "r_mid") == {"in": {"type": "fade", "duration": 0.6, "delay": 0.4}}
      and anim("tpl_oracle_full_with_lower_third.json", "r_lower_third_bg") == {"in": {"type": "fade", "duration": 0.5, "delay": 0.6}}
      and anim("tpl_pip_corner_avatar.json", "r_pip") == {"in": {"type": "fade", "duration": 0.4, "delay": 0.3}})
check("L4 le sequentiel en trois actes : un flash CYAN de 0,3 s a l'entree du 2e et du 3e acte, rien sur le 1er",
      trans("tpl_three_act_sequential.json", "r_develop") == {"type": "cyan_flash", "duration_s": 0.3}
      and trans("tpl_three_act_sequential.json", "r_payoff") == {"type": "cyan_flash", "duration_s": 0.3}
      and trans("tpl_three_act_sequential.json", "r_hook") is None)
def valide(t):
    try:
        E._validate(E.resoudre(t)); return None
    except Exception as e:
        return str(e)
check("L5 les neuf gabarits livres, lus par le moteur, passent la validation", all(valide(E.get_template(n[:-5])) is None for n in LIVRES),
      {n: valide(E.get_template(n[:-5])) for n in LIVRES})

print("[C] la conversion")
if conv:
    S = tpl([reg("a", "image_slot", slot_name="pic"), reg("b", "text", text="x"),
             reg("c", "image_slot", slot_name="pic", animation={"in": {"type": "pop"}}),
             reg("d", "image_slot", slot_name="pic", animation={"out": {"type": "fade"}}), reg("au", "audio_slot", slot_name="m"),
             reg("e", "image_slot", slot_name="pic"), reg("f", "image_slot", slot_name="pic")],
            transitions=[{"type": "fade_in", "duration_s": 0.4, "target": "a"}, {"type": "fade_in", "target": "b", "delay_s": 1},
                         {"type": "fade_in", "duration_s": 0.3, "target": "c"}, {"type": "fade_in", "duration_s": 0.3, "target": "d"},
                         {"type": "fade_in", "target": "absente"}, {"type": "zoom_in", "target": "a"}, {"type": "fade_in", "target": "au"},
                         {"type": "fade_in", "duration_s": 99, "delay_s": -1, "target": "d"}, "pas un objet",
                         {"type": "fade_in", "duration_s": 99, "delay_s": -1, "target": "e"},
                         {"type": "zoom_in", "duration_s": 0.4, "target": "f"}])
    gele = copy.deepcopy(S)
    C = conv(S)
    R = {r["id"]: r for r in C["regions"]}
    check("C1 spatial : fade_in -> animation.in fondu (duree, delai) ; sans duree, le defaut du moteur",
          R["a"]["animation"] == {"in": {"type": "fade", "duration": 0.4}} and R["b"]["animation"] == {"in": {"type": "fade", "delay": 1}})
    check("C2 ce que la region porte DEJA l'emporte (une entree pop reste) ; une sortie deja posee garde sa place a cote de l'entree",
          R["c"]["animation"] == {"in": {"type": "pop"}} and R["d"]["animation"] == {"out": {"type": "fade"}, "in": {"type": "fade", "duration": 0.3}})
    check("C3 abandonne sans bruit : cible absente, type inconnu, piste son (rien d'animable), entree qui n'est pas un objet ; plus de bloc",
          "transitions" not in C and "animation" not in R["au"] and "animation" not in R["f"] and len(C["regions"]) == 7)
    check("C3b une duree ou un delai HORS des bornes du moteur n'est pas repris (le defaut s'applique, la validation passe)",
          R["e"]["animation"] == {"in": {"type": "fade"}})
    check("C4 l'entree n'est PAS modifiee (copie) ; sans bloc, le gabarit revient tel quel (meme objet)",
          S == gele and (lambda t: conv(t) is t)(tpl([reg("a", "text")])))
    Q = tpl([reg("h", "video_slot", slot_name="h"), reg("p", "video_slot", slot_name="p"),
             reg("q", "video_slot", slot_name="q", transition={"type": "dissolve", "duration_s": 1}), reg("t", "text", text="x")],
            render_mode="sequential",
            transitions=[{"type": "cyan_flash", "duration_s": 0.3, "target": "p"}, {"type": "flash", "target": "q"},
                         {"type": "cyan_flash", "target": "t"}, {"type": "fade_in", "duration_s": 0, "target": "h"}])
    RQ = {r["id"]: r for r in conv(Q)["regions"]}
    check("C5 sequentiel : l'entree devient la `transition` de l'ACTE vise ; une transition deja posee l'emporte ; un texte n'est pas un acte ; une duree nulle n'est pas reprise",
          RQ["p"]["transition"] == {"type": "cyan_flash", "duration_s": 0.3} and RQ["q"]["transition"] == {"type": "dissolve", "duration_s": 1}
          and "transition" not in RQ["t"] and RQ["h"]["transition"] == {"type": "fade_in"})
    check("C6 un bloc qui n'est pas une liste est simplement retire", conv(tpl([reg("a", "text")], transitions="x")) == tpl([reg("a", "text")]))
else:
    check("C0 la conversion existe", False)

print("[R] la lecture : livres, personnels, envoyes en ligne")
PERSO = tpl([reg("a", "image_slot", 20, 20, 120, 120, slot_name="pic")], id="tpl_user_perso",
            transitions=[{"type": "fade_in", "duration_s": 0.4, "target": "a", "delay_s": 1}])
fp = E.templates_dir / "tpl_user_perso.json"
fp.write_text(json.dumps(PERSO, indent=2), encoding="utf-8")
octets = fp.read_bytes()
g = E.get_template("tpl_user_perso")
lst = next((t for t in E.list_templates() if t.get("id") == "tpl_user_perso"), {})
check("R1 un gabarit PERSONNEL est converti a la lecture (get et liste), et son fichier n'est PAS reecrit",
      "transitions" not in g and g["regions"][0].get("animation") == {"in": {"type": "fade", "duration": 0.4, "delay": 1}}
      and "transitions" not in lst and lst["regions"][0].get("animation") == g["regions"][0]["animation"] and fp.read_bytes() == octets)
check("R2 un gabarit envoye EN LIGNE avec un bloc (editeur ouvert avant la mise a jour) est converti par resoudre",
      E.resoudre(copy.deepcopy(PERSO))["regions"][0].get("animation") == g["regions"][0]["animation"])
if FF:
    mp4 = E.render("x", {"pic": {"path": IMG / "rouge.png"}}, _tmp / "outputs" / "perso.mp4", template=copy.deepcopy(PERSO))
    def image(src, s):
        png = _tmp / f"i{abs(hash((str(src), s)))}.png"
        subprocess.run([FF, "-v", "error", "-y", "-ss", str(s), "-i", str(src), "-frames:v", "1", str(png)], check=True)
        return Image.open(png).convert("RGB")
    a, b = image(mp4, 0.5).getpixel((80, 80)), image(mp4, 2.0).getpixel((80, 80))
    check("R3 RENDU : le fondu annonce par le bloc se VOIT enfin — fond avant le delai, case rouge apres", proche(a, (16, 16, 16)) and proche(b, (254, 0, 0), 20), f"{a} {b}")

print("[F] le flash cyan")
def seq(t1):
    return tpl([reg("h", "image_slot", 0, 0, 160, 160, slot_name="r", duration_s=2), reg("p", "image_slot", 0, 0, 160, 160, slot_name="b", duration_s=2, transition=t1)],
               render_mode="sequential")
SVS = {"r": {"path": IMG / "rouge.png"}, "b": {"path": IMG / "bleu.png"}}
def cmd(t, mod=TSV):
    return mod.build_sequential_command(E, E.resoudre(t), SVS, _tmp / "o.mp4")[0]
fc = " ".join(cmd(seq({"type": "cyan_flash", "duration_s": 0.4})))
check("F1 la commande : fondu enchaine + couleur #00e5ff nee dans le graphe en rgba, opacite qui monte puis redescend, posee a la jonction",
      "xfade=transition=fade:duration=0.4:offset=1.6" in fc and "color=c=0x00e5ff:s=160x160:r=20:d=0.4,format=rgba,fade=t=in:st=0:d=0.2:alpha=1,fade=t=out:st=0.2:d=0.2:alpha=1,setpts=PTS+1.6/TB" in fc
      and "overlay=eof_action=pass" in fc and "fadewhite" not in fc, fc[-600:])
_sp = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
(_tmp / "ts_base.py").write_text(base("backend/app/services/template_service.py"), encoding="utf-8")
TSB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TSB)
idem = [{"type": "crossfade", "duration_s": 0.5}, {"type": "flash", "duration_s": 0.3}, {"type": "cut"}, {"type": "dissolve"}, None]
check("F2 IDENTITE : toute autre transition (fondu, flash BLANC, coupe, dissolve, aucune) donne la commande de la base a l'octet",
      all(cmd(seq(t)) == cmd(seq(t), TSB) for t in idem))
if FF:
    def rendu(t, nom):
        out = _tmp / "outputs" / f"{nom}.mp4"
        E.render("x", SVS, out, template=seq(t))
        return out
    def duree(p):
        r = subprocess.run([shutil.which("ffprobe") or "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
        return float(r.stdout.strip() or 0)
    cy, wh, cf = rendu({"type": "cyan_flash", "duration_s": 0.4}, "cy"), rendu({"type": "flash", "duration_s": 0.4}, "wh"), rendu({"type": "crossfade", "duration_s": 0.4}, "cf")
    m = image(cy, 1.8).getpixel((80, 80))
    check("F3 RENDU : au milieu de la jonction l'image est CYAN ; rouge avant, bleu apres", proche(m, (0, 229, 255), 20)
          and proche(image(cy, 1.0).getpixel((80, 80)), (254, 0, 0), 20) and proche(image(cy, 3.0).getpixel((80, 80)), (0, 0, 254), 20), str(m))
    check("F4 la duree est celle d'un fondu enchaine de meme longueur (le flash ne decale rien)", abs(duree(cy) - duree(cf)) < 0.06, f"{duree(cy)} {duree(cf)}")
    mm = image(rendu({"type": "cyan_flash", "duration_s": 0.4, "color": "#ff00ff"}, "mg"), 1.8).getpixel((80, 80))
    w, x = image(wh, 1.8).getpixel((80, 80)), image(cf, 1.8).getpixel((80, 80))
    # fadewhite ne passe pas par le blanc PUR (mesure : 180,182,255 au milieu) : il BLANCHIT, le fondu enchaine non (vert ~0)
    check("F5 `color` choisit la couleur (magenta) ; « flash » reste le flash BLANC d'avant (il blanchit ; le fondu enchaine non)",
          proche(mm, (255, 0, 255), 24) and w[1] > 150 and x[1] < 40, f"{mm} {w} {x}")
else:
    check("F0 ffmpeg present", False)

print("[V] la couleur entre dans le graphe : elle est verifiee")
def err(t1):
    try:
        E._validate(seq(t1)); return None
    except ValueError as e:
        return str(e)
e1 = err({"type": "cyan_flash", "color": "red:s=1x1[x];[x]drawtext"})
check("V1 une couleur qui n'est pas #rrggbb est REFUSEE en nommant l'acte et le champ ; une transition qui n'est pas un objet aussi",
      e1 is not None and "p" in e1 and "transition.color" in e1 and err("cyan_flash") is not None and err({"type": 5}) is not None
      and err({"type": "cyan_flash", "color": "#00e5ff:s=1x1,drawtext"}) is not None and err({"type": "cyan_flash", "color": "#00e5ff0"}) is not None, e1)
check("V2 #00e5ff, 00E5FF, et une transition sans couleur passent", err({"type": "cyan_flash", "color": "#00e5ff"}) is None
      and err({"type": "cyan_flash", "color": "00E5FF"}) is None and err({"type": "cyan_flash"}) is None)
fc2 = " ".join(cmd(dict(seq({"type": "cyan_flash", "duration_s": 0.4}), regions=[reg("h", "image_slot", 0, 0, 160, 160, slot_name="r", duration_s=2),
                                                                                   reg("p", "image_slot", 0, 0, 160, 160, slot_name="b", duration_s=2,
                                                                                       transition={"type": "cyan_flash", "color": "x;y"})])))
check("V3 meme sans validation (rendu direct), une couleur invalide retombe sur le cyan par defaut — rien n'entre dans le graphe",
      "color=c=0x00e5ff:" in fc2 and "x;y" not in fc2)

shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n#76 transitions converties : {ok} PASS, {fail} FAILED")
if __name__ == "__main__":
    sys.exit(1 if fail else 0)
