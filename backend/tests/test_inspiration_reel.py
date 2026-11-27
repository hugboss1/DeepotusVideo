# -*- coding: utf-8 -*-
"""t515 (RV5, 26/11/2026) — banc du gabarit « reel en tableaux » et du brouillon au Planificateur.

Spec 2026-11-13-reel-reference-design.md § 3.4 points 3-4, § 9.2, R7, R8, R12.
Sections :
  1. repères (purs) : refus tant que le script n'est pas VALIDÉ (porte 1) ; temps estimés à 2,5 mots/s ; temps des
     mots fournis (et repli s'ils ne collent pas) ; mot déclencheur, objet animé, valeur ; chiffre non sourcé
     marqué « valeur d'illustration » (R8) ; sous-titres en pastille + badge (R7) ; provenance `inspire_de` (R12 a) ;
  2. page motion code : passe le bac à sable (`motion_code.controler`), couleurs de la CHARTE de l'espace (jamais la
     palette de la source), données en base64 (aucun mot du script en clair), frise d'autant de cases que de tableaux ;
  3. commentaire du MP4 (R12 b) : texte exact, posé par ffmpeg sans réencodage ;
  4. routes : repères (409 avant la porte 1, message traduit), rendu local gratuit (job, MP4 commenté, recette de
     fabrication avec `inspire_de`), hors machine 403, brouillon (409 sans rendu ; mode TOUJOURS assisté même si le
     corps demande « auto » (R8) ; brouillon, job lié, `inspire_de` au brief ; ligne publique « Format inspiré de… »
     proposée DÉCOCHÉE, ajoutée seulement si cochée (R12 c)).
Run (depuis backend/) : & $PY tests/test_inspiration_reel.py"""
import base64, json, os, pathlib, re, shutil, subprocess, sys, tempfile, uuid
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzinsreel_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    os.environ[k] = ""
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import inspiration as I                           # noqa: E402
from app.services import motion_code as MC                          # noqa: E402

FFMPEG = shutil.which("ffmpeg")
SCRIPT = {"statut": "valide", "langue": "fr", "valide_le": "2026-11-26T10:00:00+00:00",
          "briques": [{"role": "accroche", "texte": "Un studio vidéo payé une seule fois.", "ecran": "une seule fois"},
                      {"role": "comparaison", "texte": "Un abonnement coûte 99 $ par mois.", "ecran": "99 $"},
                      {"role": "offre", "texte": "Ici il coûte 45 € à vie.", "ecran": "45 €"},
                      {"role": "appel", "texte": "Le lien est en description.", "ecran": "lien"}]}
RECETTE = {"rythme": {"mots_par_minute": 150}, "soustitres": {"lignes": 2, "mots_par_ligne": 3, "mot_en_pastille": True, "badge": True},
           "image": {"fil_de_progression": True},
           "structure": [{"role": "accroche", "debut": 0, "fin": 2, "regle": "r", "visuel": "texte", "mots": 7},
                         {"role": "comparaison", "debut": 2, "fin": 4, "regle": "r", "visuel": "barres", "mots": 7},
                         {"role": "offre", "debut": 4, "fin": 6, "regle": "r", "visuel": "compteur", "mots": 6},
                         {"role": "appel", "debut": 6, "fin": 8, "regle": "r", "visuel": "carte", "mots": 5}],
           "inspire_de": {"plateforme": "instagram", "lien": "https://www.instagram.com/reel/ABC/", "libelle": "Reel de @voisin",
                          "capture_le": "2026-11-13T09:00:00+00:00"}}
CHIFFRES = [{"valeur": "45 €", "libelle": "prix", "source": "page d'achat"}]


def reference(eid: str, statut: str = "valide") -> str:
    iid = uuid.uuid4().hex
    rec = {"id": iid, "espace_id": eid, "cree": I._maintenant(), "langue": "fr", "matiere": "video",
           "source": {"libelle": "Reel de @voisin", "lien": "https://www.instagram.com/reel/ABC/", "plateforme": "instagram"},
           "texte_capte": "texte de la source jamais repris", "palette": ["#fafafa", "#c0392b"],
           "video": {"fiche": {"format": {"duree_s": 8.0}}, "planches": []}, "analyse": None, "brouillons": [],
           "recette": json.loads(json.dumps(RECETTE)), "script": dict(json.loads(json.dumps(SCRIPT)), statut=statut)}
    I._ecrire(rec)
    return iid


def donnees_page(html: str) -> dict:
    m = re.search(r'id="dz-donnees">([^<]+)<', html)
    return json.loads(base64.b64decode(m.group(1).strip()).decode("utf-8")) if m else {}


def faux_rendu(html, sortie, *, W, H, fps=30, duree_s=8, delai=None, langue="fr", edge=None):
    """Le bac à sable remplacé par un MP4 de 1 s fabriqué par ffmpeg (le contrôle de la page est rejoué)."""
    assert not MC.controler(html), MC.controler(html)
    FAUX["html"] = html
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=108x192:d=1", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(sortie)], check=True)
    return {"images": 30, "fps": fps, "W": W, "H": H, "duree_s": duree_s, "erreurs_js": 0}


FAUX = {}


def commentaire_de(mp4) -> str:
    sonde = shutil.which("ffprobe")
    if not sonde:
        return ""
    r = subprocess.run([sonde, "-v", "error", "-show_entries", "format_tags=comment", "-of", "json", str(mp4)],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(r.stdout)["format"]["tags"]["comment"]
    except (ValueError, KeyError):
        return ""


def run():
    from app.services import brand_kits, espaces
    from app.services import inspiration_reel as IRL
    from app.services import offre as OF
    kit = brand_kits.enregistrer({"name": "Kit banc", "brand_color": "#123456", "accent_color": "#abcdef"})
    EA = espaces.creer({"nom": "Studio Reel", "kit_id": kit})["id"]
    OF.ecrire(EA, {"produit": "VideoGen", "pour_qui": "créateurs", "promesse": "payé une fois", "preuves": ["mises à jour"],
                   "appels": ["lien"], "chiffres": CHIFFRES})

    print("[1] repères")
    nv = reference(EA, statut="a_valider")
    try:
        IRL.fabriquer_reperes(nv)
        check("1a script non validé -> refus", False)
    except I.RefusInspiration as e:
        check("1a script non validé -> refus script_non_valide (porte 1)", e.code == "script_non_valide", e.code)
    IID = reference(EA)
    r = IRL.fabriquer_reperes(IID)
    tb = r["tableaux"]
    check("1b un tableau par brique, dans l'ordre, rôles et visuels de la recette", [t["role"] for t in tb] ==
          ["accroche", "comparaison", "offre", "appel"] and tb[1]["visuel"] == "barres", [t["role"] for t in tb])
    check("1c sans temps de mots : temps ESTIMÉS à 2,5 mots/s", r["temps"] == "estimes" and r["debit_mots_s"] == 2.5
          and abs((tb[0]["fin"] - tb[0]["debut"]) - (7 / 2.5)) < 0.6, (r["temps"], tb[0]))
    check("1d tableaux contigus, durée = fin du dernier (+ queue)", all(abs(tb[i]["fin"] - tb[i + 1]["debut"]) < 1e-6 for i in range(3))
          and r["duree_s"] >= tb[-1]["fin"] and tb[0]["debut"] == 0, [(t["debut"], t["fin"]) for t in tb])
    check("1e mot déclencheur pris dans le texte à l'écran, à son temps", tb[0]["declencheur"]["mot"] in ("une", "seule", "fois")
          and tb[0]["debut"] <= tb[0]["declencheur"]["t"] < tb[0]["fin"], tb[0]["declencheur"])
    check("1f objet animé : barres, compteur (chiffre), carte", [t["objet"] for t in tb] == ["texte", "barres", "compteur", "carte"],
          [t["objet"] for t in tb])
    check("1g valeur : le chiffre de la brique", tb[1]["valeur"] == "99 $" and tb[2]["valeur"] == "45 €", (tb[1]["valeur"], tb[2]["valeur"]))
    check("1h R8 : 99 $ non sourcé -> valeur d'illustration ; 45 € sourcé -> réel", tb[1]["illustration"] is True
          and tb[2]["illustration"] is False and r["mention_illustration"] is True, (tb[1]["illustration"], tb[2]["illustration"]))
    st = r["soustitres"]
    lignes = [l for g in st for l in g["l"]]
    check("1i sous-titres : 3 mots par ligne au plus, 2 lignes par groupe", lignes and all(len(l) <= 3 for l in lignes)
          and all(len(g["l"]) <= 2 for g in st), [len(l) for l in lignes])
    mots = [w for l in lignes for w in l]
    check("1j R7 : pastille sur les mots de l'écran, badge sur le déclencheur chiffré",
          any(w["p"] and w["t"].strip(".,").lower() == "seule" for w in mots) and any(w["g"] == "45 €" for w in mots)
          and not any(w["p"] and w["t"].lower().startswith("abonnement") for w in mots), [w for w in mots if w["p"] or w["g"]])
    check("1k R12 a : inspire_de de la recette recopié dans les repères", r["inspire_de"]["lien"] == RECETTE["inspire_de"]["lien"])
    check("1l rangés dans l'inspiration", (I.lire(IID).get("reel") or {}).get("reperes", {}).get("tableaux") == tb)
    temps = []
    t = 0.5
    for b in SCRIPT["briques"]:
        for m in b["texte"].split():
            temps.append({"text": m, "start": round(t, 2), "end": round(t + 0.3, 2)})
            t += 0.32
        t += 0.4
    r2 = IRL.fabriquer_reperes(IID, temps=temps)
    check("1m temps des mots fournis : repères sur les VRAIS temps", r2["temps"] == "mots"
          and r2["tableaux"][2]["declencheur"]["t"] == next(x["start"] for x in temps if x["text"] == "45"), r2["tableaux"][2]["declencheur"])
    r3 = IRL.fabriquer_reperes(IID, temps=temps[:5])
    check("1n temps incomplets : repli sur l'estimation (dit)", r3["temps"] == "estimes")

    print("[2] page motion code")
    ch = IRL.charte(EA)
    check("2a charte de l'espace : kit (accent, marque)", ch["accent"] == "#abcdef" and ch["marque"] == "#123456", ch)
    html = IRL.page(r, ch)
    check("2b la page passe le bac à sable du motion code", MC.controler(html) == [], MC.controler(html))
    check("2d aucun mot du script en clair (données en base64)", "abonnement" not in html and "dzFrame" in html)
    d = donnees_page(html)
    check("2c couleurs de la charte (fond, accent), jamais la palette de la source", "#123456" in html
          and d.get("charte", {}).get("accent") == "#abcdef" and "#c0392b" not in html + json.dumps(d), d.get("charte"))
    check("2e frise : autant de cases que de tableaux ; mention d'illustration traduite", d.get("frise", {}).get("n") == 4
          and d.get("libelles", {}).get("illustration") == "valeur d'illustration", (d.get("frise"), d.get("libelles")))
    d_en = donnees_page(IRL.page(dict(r, langue="en"), ch))
    check("2f libellés anglais", d_en.get("libelles", {}).get("illustration") == "illustrative value")

    print("[3] commentaire du MP4 (R12 b)")
    c = IRL.commentaire(RECETTE["inspire_de"], "fr")
    check("3a texte exact", c == "Structure inspirée de https://www.instagram.com/reel/ABC/. Texte, images et voix originaux.", c)
    check("3b anglais", IRL.commentaire(RECETTE["inspire_de"], "en").startswith("Structure inspired by https://"))
    if FFMPEG:
        src, dst = _tmp / "a.mp4", _tmp / "b.mp4"
        faux_rendu("<p>x</p>", src, W=108, H=192)
        IRL.poser_commentaire(src, dst, c)
        check("3c posé par ffmpeg sans réencodage, lu par ffprobe", dst.is_file() and (commentaire_de(dst) == c or not shutil.which("ffprobe")),
              commentaire_de(dst))
    else:
        check("3c ffmpeg absent : commentaire non vérifiable (noté)", True)

    print("[4] routes")
    from fastapi.testclient import TestClient
    from app.main import app
    MC.rendre_page = faux_rendu
    with TestClient(app, client=("127.0.0.1", 50000)) as client, TestClient(app, client=("192.168.1.20", 50000)) as dehors:
        H = {"X-Dz-Espace": EA}
        nv2 = reference(EA, statut="a_valider")
        r = client.post(f"/api/inspiration/{nv2}/reel/reperes", headers=H, json={})
        check("4a repères avant la porte 1 -> 409 script_non_valide", r.status_code == 409 and r.json()["detail"]["code"] == "script_non_valide", r.text[:200])
        r = client.post(f"/api/inspiration/{nv2}/reel/reperes", headers={**H, "Accept-Language": "en"}, json={})
        check("4b message traduit en anglais", "approve" in r.text.lower(), r.text[:200])
        R2 = reference(EA)
        r = dehors.post(f"/api/inspiration/{R2}/reel/reperes", json={})
        check("4c hors machine -> 401 ou 403", r.status_code in (401, 403), r.status_code)
        r = client.post(f"/api/inspiration/{R2}/reel/brouillon", headers=H, json={})
        check("4d brouillon sans rendu -> 409 sans_rendu", r.status_code == 409 and r.json()["detail"]["code"] == "sans_rendu", r.text[:200])
        r = client.post(f"/api/inspiration/{R2}/reel/rendu", headers=H, json={})
        check("4e rendu sans repères -> 409 sans_reperes", r.status_code == 409 and r.json()["detail"]["code"] == "sans_reperes", r.text[:200])
        r = client.post(f"/api/inspiration/{R2}/reel/reperes", headers=H, json={"temps": temps})
        check("4f repères 200 (temps des mots)", r.status_code == 200 and r.json()["temps"] == "mots" and len(r.json()["tableaux"]) == 4, r.text[:200])
        r = client.get(f"/api/inspiration/{R2}/reel", headers=H)
        p = r.json().get("proposition", {})
        check("4g proposition : ligne publique « Format inspiré… » proposée DÉCOCHÉE (R12 c)", r.status_code == 200
              and p.get("mention_publique", {}).get("coche") is False and "Format inspiré d'un Reel de @voisin" in p["mention_publique"]["texte"], p)
        if FFMPEG:
            r = client.post(f"/api/inspiration/{R2}/reel/rendu", headers=H, json={"fps": 30})
            j = r.json()
            check("4h rendu : un job, gratuit (aucun devis)", r.status_code == 200 and j.get("job_id") and j.get("usd") == 0, r.text[:200])
            r = client.get(f"/api/jobs/{j.get('job_id')}")
            jr = r.json() if r.status_code == 200 else {}
            check("4i job terminé", str(jr.get("status", "")).lower() in ("done", "completed"), str(jr.get("error"))[:300])
            rec = I.lire(R2)
            v = pathlib.Path((rec.get("reel") or {}).get("rendu", {}).get("video") or "")
            check("4j MP4 commenté (R12 b)", v.is_file() and (commentaire_de(v).startswith("Structure inspirée de https://www.instagram.com/reel/ABC/")
                                                              or not shutil.which("ffprobe")), commentaire_de(v) if v.is_file() else v)
            fab = v.with_name(v.stem + ".recette.json")
            fj = json.loads(fab.read_text(encoding="utf-8")) if fab.is_file() else {}
            check("4k recette de fabrication à côté du rendu, avec inspire_de (R12 a)", fj.get("inspire_de", {}).get("lien") == RECETTE["inspire_de"]["lien"]
                  and fj.get("genre") == "reel_tableaux" and fj.get("inspiration_id") == R2, fj)
            rr = client.get(f"/api/jobs/{j.get('job_id')}/recette").json()
            check("4l recette unifiée du job : la fabrication et sa provenance", (rr.get("fabrication") or {}).get("inspire_de", {}).get("lien")
                  == RECETTE["inspire_de"]["lien"], rr.get("fabrication"))
            check("4m la page rendue est le gabarit à la charte", "#123456" in FAUX.get("html", "") and "dz-frise" in FAUX.get("html", ""))
            r = client.post(f"/api/inspiration/{R2}/reel/brouillon", headers=H, json={"titre": "Payé une fois", "mode": "auto",
                                                                                      "status": "scheduled"})
            b = r.json()
            post = b.get("post") or {}
            check("4n R8 : brouillon, mode ASSISTÉ même si « auto » est demandé", r.status_code == 200 and post.get("mode") == "assisted"
                  and post.get("status") in ("draft", "a_valider"), r.text[:300])
            check("4o le rendu est lié au post, format reel", post.get("job_id") == j.get("job_id") and post.get("format") == "reel", post)
            brief = post.get("brief") if isinstance(post.get("brief"), dict) else json.loads(post.get("brief") or "{}")
            check("4p R12 a : inspire_de sur le brouillon (brief), Reel Instagram", brief.get("inspire_de", {}).get("lien") == RECETTE["inspire_de"]["lien"]
                  and (brief.get("instagram") or {}).get("forme") == "reel", brief)
            check("4q R12 c : sans case cochée, aucune mention publique", "inspiré" not in (post.get("caption") or "")
                  and "instagram.com" not in (post.get("caption") or ""), post.get("caption"))
            r = client.post(f"/api/inspiration/{R2}/reel/brouillon", headers=H, json={"titre": "Payé une fois", "mention_publique": True})
            cap = (r.json().get("post") or {}).get("caption") or ""
            check("4r case cochée : la ligne « Format inspiré d'un Reel de @voisin. » est ajoutée", r.status_code == 200
                  and "Format inspiré d'un Reel de @voisin." in cap, r.text[:300])
            check("4s brouillons notés dans l'inspiration", len(I.lire(R2).get("brouillons") or []) == 2)
            r = client.post(f"/api/inspiration/{R2}/reel/brouillon", headers=H, json={"titre": "x", "legende": "merci à @voisin pour l idée"})
            check("4t la source dans la légende libre reste refusée (409 source)", r.status_code == 409 and r.json()["detail"]["code"] == "source", r.text[:200])
        else:
            check("4h-4t ffmpeg absent : rendu non jouable ici (noté)", True)


def test_inspiration_reel():
    run()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    try:
        run()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
