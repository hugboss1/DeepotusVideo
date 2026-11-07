# t418 (Photolab N8, photocraft 0.21) : formats — ouverture depuis l'ordinateur et export élargis, compression TIFF et DDS.
# Lancement : python embarqué, `python tests/test_photolab_n8.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, struct, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt418_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                 # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


def ilbm(l=8, h=8):
    """ILBM minimal : 1 plan, sans compression, 2 couleurs."""
    bmhd = struct.pack(">HHhhBBBBHBBhh", l, h, 0, 0, 1, 0, 0, 0, 0, 1, 1, l, h)
    corps = b"\xf0" * (2 * h)
    parties = b"BMHD" + struct.pack(">I", len(bmhd)) + bmhd + b"CMAP" + struct.pack(">I", 6) + bytes([0, 0, 0, 255, 0, 0]) + b"BODY" + struct.pack(">I", len(corps)) + corps
    return b"FORM" + struct.pack(">I", len(parties) + 4) + b"ILBM" + parties


def xcf(l=8, h=8):
    """XCF v0 minimal : un calque RGBA 8 bits, sans compression (une seule tuile, moins de 64 px de côté)."""
    u32 = lambda n: struct.pack(">I", n)
    prop = lambda t, v: u32(t) + u32(len(v)) + v
    fin = prop(0, b"")
    nom = lambda s: u32(len(s) + 1) + s + b"\0"
    tete = b"gimp xcf file\0" + u32(l) + u32(h) + u32(0) + prop(17, b"\0") + fin
    # entête, puis pointeurs : calques (1 + 0), couches (0)
    base = len(tete) + 4 * 3
    calque = u32(l) + u32(h) + u32(1) + nom(b"Fond") + fin
    pos_h = base + len(calque) + 8
    calque_c = calque + u32(pos_h) + u32(0)
    hier = u32(l) + u32(h) + u32(4)
    pos_n = pos_h + len(hier) + 8
    hier += u32(pos_n) + u32(0)
    pos_t = pos_n + 12 + 8
    niveau = u32(l) + u32(h) + u32(pos_t) + u32(0)
    # tuile non compressée, composantes à plat (R…, G…, B…, A…)
    tuile = bytes(l * h * 4)
    return tete + u32(base) + u32(0) + u32(0) + calque_c + hier + niveau + u32(0) + tuile


def dicom(l=8, h=8):
    """DICOM Part 10 explicite, une image 8 bits en gris, sans compression."""
    el = lambda g, e, vr, v: struct.pack("<HH", g, e) + vr + struct.pack("<H", len(v)) + v
    meta = el(2, 0x10, b"UI", b"1.2.840.10008.1.2.1\0")
    tete = b"\0" * 128 + b"DICM" + el(2, 0, b"UL", struct.pack("<I", len(meta))) + meta
    pix = bytes(range(l * h))
    data = (el(0x28, 2, b"US", struct.pack("<H", 1)) + el(0x28, 4, b"CS", b"MONOCHROME2 ") + el(0x28, 0x10, b"US", struct.pack("<H", h)) + el(0x28, 0x11, b"US", struct.pack("<H", l))
            + el(0x28, 0x100, b"US", struct.pack("<H", 8)) + el(0x28, 0x101, b"US", struct.pack("<H", 8)) + el(0x28, 0x102, b"US", struct.pack("<H", 7)) + el(0x28, 0x103, b"US", struct.pack("<H", 0))
            + struct.pack("<HH", 0x7fe0, 0x10) + b"OB\0\0" + struct.pack("<I", len(pix)) + pix)
    return tete + data


async def scenario():
    import httpx
    from app.main import app
    API = "/api/photolab"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t", timeout=120) as c:
        post = lambda u, j=None: c.post(API + u, json=j if j is not None else {})
        imp = lambda nom, o: c.post(f"{API}/importer", params={"nom": nom}, content=o)
        ins = lambda: asyncio.to_thread(PM.session().appeler, "doc.inspect")
        assert (await post("/nouveau", {"width": 120, "height": 80, "background": "white"})).status_code == 200

        print("[1] enregistrer")
        for f in ("jxl", "dds", "exr", "dpx", "cin", "hdr", "bmp", "gif", "qoi"):
            r = await post("/enregistrer", {"format": f, "nom": "essai"})
            j = r.json() if r.status_code == 200 else {}
            o = (PM.dossier_travail() / "exports" / j.get("fichier", "x"))
            check(f"1.1 {f} écrit", r.status_code == 200 and j["fichier"].endswith("." + f) and o.is_file() and o.stat().st_size > 0, (r.status_code, r.text[:200]))
        for f, v in (("tif", "lzw"), ("tif", "zip"), ("dds", "bc1"), ("dds", "bc3")):
            r = await post("/enregistrer", {"format": f, "nom": f"c{v}", "compression": v})
            check(f"1.2 {f} compression {v}", r.status_code == 200, (r.status_code, r.text[:200]))
        brut = (await post("/enregistrer", {"format": "dds", "nom": "brut", "compression": "none"})).json()["fichier"]
        comp = (await post("/enregistrer", {"format": "dds", "nom": "comp", "compression": "bc1"})).json()["fichier"]
        d = PM.dossier_travail() / "exports"
        check("1.3 la compression agit vraiment", (d / comp).stat().st_size < (d / brut).stat().st_size, ((d / comp).stat().st_size, (d / brut).stat().st_size))
        for corps, lib in (({"format": "png", "compression": "lzw"}, "compression sur un PNG"), ({"format": "tif", "compression": "zorg"}, "compression inconnue"),
                           ({"format": "dds", "compression": "lzw"}, "LZW sur un DDS"), ({"format": "xcf"}, "XCF ne s'enregistre pas"), ({"format": "svg"}, "format inconnu")):
            r = await post("/enregistrer", corps)
            check(f"1.4 {lib} : refus", r.status_code == 400, (r.status_code, r.text[:160]))
        r = await post("/copie", {"format": "dds", "nom": "cp", "compression": "bc1", "destination": "telecharger"})
        fc = (r.json().get("fichier") or "x") if r.status_code == 200 else "x"
        check("1.5 /copie applique la compression", r.status_code == 200 and (d / fc).stat().st_size < (d / brut).stat().st_size, (r.status_code, r.text[:200]))

        print("[2] ouvrir depuis l'ordinateur")
        for f, nom in (("hdr", "essai.hdr"), ("cin", "essai.cin"), ("qoi", "essai.qoi"), ("dpx", "essai.dpx")):
            r = await imp(nom, (d / nom).read_bytes())
            check(f"2.1 {f} rouvert", r.status_code == 200 and r.json().get("width") == 120, (r.status_code, r.text[:200]))
        r = await imp("planche.iff", ilbm())
        check("2.2 IFF/ILBM", r.status_code == 200 and r.json().get("width") == 8, (r.status_code, r.text[:200]))
        r = await imp("gimp.xcf", xcf())
        check("2.2b XCF de GIMP", r.status_code == 200 and r.json().get("width") == 8, (r.status_code, r.text[:200]))
        r = await imp("radio.dcm", dicom())
        check("2.3 DICOM", r.status_code == 200 and r.json().get("width") == 8, (r.status_code, r.text[:200]))
        for nom in ("faux.xcf", "faux.dcm", "faux.fits"):
            r = await imp(nom, b"pas une image")
            check(f"2.4 {nom} abîmé : refus du moteur", r.status_code == 422, (r.status_code, r.text[:160]))
        r = await imp("x.jxl", (d / "essai.jxl").read_bytes())
        check("2.5 JPEG XL reste fermé en ouverture", r.status_code == 415, (r.status_code, r.text[:160]))
        r = await imp("x.heic", b"x")
        check("2.6 HEIC reste fermé", r.status_code == 415, (r.status_code, r.text[:160]))
        restes = [f.name for f in (PM.dossier_travail() / "entrees").iterdir() if "faux" in f.name]
        check("2.7 un fichier refusé est effacé", not restes, restes)


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
