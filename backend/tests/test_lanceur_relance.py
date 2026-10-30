"""Relance du backend : l'ancien est VRAIMENT arrêté, le nouveau VRAIMENT servi (t386, 30/10/2026).

Constat du 30/10, à l'installation de t376 : `netstat` montrait `127.0.0.1:8765 LISTENING 0`. Le socket
d'écoute était attribué au PID 0 alors qu'un backend installé tournait. `scripts/stop.ps1` (et donc
`launch-silent.vbs`, qui l'appelle) cherchait le PID QUI ÉCOUTE : il n'a rien arrêté. Le nouveau uvicorn n'a pas
pu prendre le port et s'est arrêté sans bruit. Le lanceur a vu /api/health répondre et a ouvert le navigateur,
mais c'est l'ANCIEN code qui restait servi. Le 10/10 déjà, un enfant `spawn_main(parent_pid=…)` gardait le socket
d'un parent tué (note backend-preuve-enfant-multiprocessing).

Le banc rejoue ces pièges de bout en bout, sans jamais toucher au 8765 de l'utilisateur :
  - un FAUX runtime (copie de python.exe et de ses DLL, `._pth` vers un faux `backend/uvicorn.py`) dans un faux
    dossier d'application, sur un port libre ;
  - le VRAI `launch-silent.vbs`, exécuté par cscript, dont la copie ne change que le port, l'ouverture du
    navigateur (remplacée par un écho) et les MsgBox (en écho, pour ne pas bloquer) ;
  - le VRAI `stop.ps1`.

R1 l'ancien backend dont un ENFANT tient le socket (le parent dort) est arrêté, enfant compris, et c'est le
   NOUVEAU code qui répond quand le lanceur ouvre le navigateur.
R2 un processus d'une AUTRE application (même ligne de commande, exécutable hors du dossier de l'app) n'est
   jamais touché : stop.ps1 sort 2, le lanceur refuse d'ouvrir le navigateur et le dit.
R3 si l'ancien répond encore (arrêt sauté), le lanceur n'ouvre PAS le navigateur : la réponse doit venir d'un
   processus créé APRÈS le lancement (pid rendu par /api/health).
R4 /api/health rend le pid du processus qui répond.
"""
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
LANCEUR = RACINE / "scripts" / "launch-silent.vbs"
STOP = RACINE / "scripts" / "stop.ps1"
CSCRIPT = shutil.which("cscript") or r"C:\Windows\System32\cscript.exe"
POWERSHELL = shutil.which("powershell") or r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

pytestmark = pytest.mark.skipif(os.name != "nt" or not os.path.isfile(CSCRIPT),
                                reason="lanceur Windows : cscript requis")

# Le faux uvicorn : `python -m uvicorn app.main:app --host H --port P`, comme l'app installée. Il lit sa
# version et son mode dans le dossier backend. En mode « enfant », le parent ouvre le socket, le PARTAGE avec
# un enfant qui sert, puis dort sans servir : le piège du 10/10. Comme uvicorn, il sort sans bruit si le port
# est pris (aucun SO_REUSEADDR, qui sous Windows laisserait partager le port).
FAUX_UVICORN = r'''
import http.server, json, os, socket, subprocess, sys, time

ICI = os.path.dirname(os.path.abspath(__file__))
VERSION = open(os.path.join(ICI, "VERSION"), encoding="utf-8").read().strip()
MODE = open(os.path.join(ICI, "MODE"), encoding="utf-8").read().strip()


class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        corps = json.dumps({"ok": True, "version": VERSION, "pid": os.getpid()}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def log_message(self, *a):
        pass


def servir(s):
    srv = http.server.HTTPServer(s.getsockname(), H, bind_and_activate=False)
    srv.socket.close()
    srv.socket = s
    srv.serve_forever()


if __name__ == "__main__":
    if sys.argv[1:2] == ["--enfant"]:
        servir(socket.fromshare(sys.stdin.buffer.read()))
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", int(sys.argv[sys.argv.index("--port") + 1])))
    except OSError:
        sys.exit(1)
    s.listen(16)
    if MODE == "enfant":
        e = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--enfant"], stdin=subprocess.PIPE)
        e.stdin.write(s.share(e.pid))
        e.stdin.close()
        while True:
            time.sleep(60)
    servir(s)
'''


def _faux_runtime(dossier_app):
    """Copie python.exe et ses DLL dans <app>/runtime/python ; le `._pth` pointe la bibliothèque standard du
    python courant et le faux backend (uvicorn.py), jamais les vrais site-packages."""
    base = pathlib.Path(sys.base_prefix)
    rt = dossier_app / "runtime" / "python"
    rt.mkdir(parents=True)
    for f in base.iterdir():
        if f.is_file() and f.suffix.lower() in (".exe", ".dll", ".pyd", ".zip"):
            shutil.copy2(f, rt / f.name)
    nom = f"python{sys.version_info.major}{sys.version_info.minor}"
    lignes = [str(base / f"{nom}.zip"), str(base / "Lib"), str(base / "DLLs"), str(base), ".",
              str(dossier_app / "backend")]
    (rt / f"{nom}._pth").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    back = dossier_app / "backend"
    back.mkdir()
    (back / "uvicorn.py").write_text(FAUX_UVICORN, encoding="utf-8")
    return rt / "python.exe"


def _poser(dossier_app, version, mode="seul"):
    (dossier_app / "backend" / "VERSION").write_text(version, encoding="utf-8")
    (dossier_app / "backend" / "MODE").write_text(mode, encoding="utf-8")


def _port_libre():
    while True:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        if p != 8765 and _sante(p) is None:
            return p


def _sante(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _attendre_sante(port, version, delai=30):
    fin = time.time() + delai
    while time.time() < fin:
        s = _sante(port)
        if s and s.get("version") == version:
            return s
        time.sleep(0.2)
    raise AssertionError(f"le faux backend {version} ne répond pas sur {port}")


def _demarrer(py, dossier_app, port):
    """Lance `python -m uvicorn app.main:app …` détaché, comme le fait le lanceur."""
    return subprocess.Popen([str(py), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                            cwd=str(dossier_app / "backend"), stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW)


def _vivant(pid):
    r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], capture_output=True, text=True)
    return f'"{pid}"' in r.stdout


def _enfants(pid):
    r = subprocess.run([POWERSHELL, "-NoProfile", "-Command",
                        f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={pid}').ProcessId"],
                       capture_output=True, text=True, timeout=60)
    return [int(x) for x in r.stdout.split()]


def _tuer_sous(*dossiers):
    """Ménage : tout processus dont l'exécutable est sous un dossier du banc."""
    for d in dossiers:
        motif = str(d).replace("'", "''")
        subprocess.run([POWERSHELL, "-NoProfile", "-Command",
                        f"Get-CimInstance Win32_Process | Where-Object {{ $_.ExecutablePath -and "
                        f"$_.ExecutablePath.StartsWith('{motif}', 'OrdinalIgnoreCase') }} | "
                        f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"],
                       capture_output=True, timeout=60)


def _installer_lanceur(dossier_app, port, sans_arret=False, essais=None):
    """Copie le VRAI lanceur et le VRAI stop.ps1 dans <app>/scripts. Seuls changent le port, l'ouverture du
    navigateur (écho « OUVERT ») et les MsgBox (en écho) ; R3 saute en plus l'arrêt et raccourcit l'attente."""
    src = LANCEUR.read_bytes().decode("utf-8")
    ouvre = "shell.Run urlApp, 1, False"
    assert src.count(ouvre) == 1 and "MsgBox(" not in src
    src = src.replace("8765", str(port)).replace(ouvre, 'WScript.Echo "OUVERT " & urlApp')
    src = src.replace("MsgBox ", "WScript.Echo ")
    # garde : la copie arrête le port du BANC, jamais le 8765 de l'utilisateur (l'ancien stop.ps1 l'avait en dur)
    assert f"-Port {port}" in src and "8765" not in src
    assert "8765" not in STOP.read_text(encoding="utf-8").split("param(", 1)[1].split(")", 1)[1]
    if sans_arret:
        assert re.search(r"(?m)^StopExistingBackend\(\)\r?$", src)
        src = re.sub(r"(?m)^StopExistingBackend\(\)(\r?)$", r"' (banc t386) arret saute\1", src)
    if essais:
        assert "Do While attempts < 90" in src
        src = src.replace("Do While attempts < 90", f"Do While attempts < {essais}")
    sc = dossier_app / "scripts"
    sc.mkdir(exist_ok=True)
    (sc / "launch-silent.vbs").write_bytes(src.encode("utf-8"))
    shutil.copy2(STOP, sc / "stop.ps1")
    return sc / "launch-silent.vbs"


def _lancer(vbs, donnees):
    env = dict(os.environ, DEEPOTUS_DATA_DIR=str(donnees))
    return subprocess.run([CSCRIPT, "//nologo", str(vbs)], capture_output=True, text=True, env=env, timeout=180)


@pytest.fixture
def banc():
    d = pathlib.Path(tempfile.mkdtemp(prefix="dz_t386_"))
    app, autre, donnees = d / "App", d / "AutreApp", d / "Donnees"
    for x in (app, autre, donnees):
        x.mkdir()
    try:
        yield {"app": app, "py": _faux_runtime(app), "autre": autre, "donnees": donnees,
               "port": _port_libre()}
    finally:
        _tuer_sous(app, autre)
        shutil.rmtree(d, ignore_errors=True)


def test_r1_l_ancien_et_son_enfant_sont_arretes_et_le_nouveau_repond(banc):
    app, port = banc["app"], banc["port"]
    # témoin : le backend d'une autre application, plus ancien, sur un autre port (comme le 8765 de
    # l'utilisateur pendant le banc) ne doit pas être touché par la relance
    py_temoin = _faux_runtime(banc["autre"])
    _poser(banc["autre"], "temoin")
    port_temoin = _port_libre()
    temoin = _demarrer(py_temoin, banc["autre"], port_temoin)
    _attendre_sante(port_temoin, "temoin")
    _poser(app, "ancien", "enfant")
    parent = _demarrer(banc["py"], app, port)
    ancien = _attendre_sante(port, "ancien")
    enfant = ancien["pid"]
    assert enfant != parent.pid and enfant in _enfants(parent.pid)      # c'est l'ENFANT qui sert

    _poser(app, "nouveau")
    r = _lancer(_installer_lanceur(app, port), banc["donnees"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"OUVERT http://deepotus.localhost:{port}" in r.stdout
    neuf = _sante(port)
    assert neuf and neuf["version"] == "nouveau", neuf
    assert not _vivant(parent.pid) and not _vivant(enfant)
    assert _vivant(temoin.pid) and _sante(port_temoin)["version"] == "temoin"


def test_r2_un_processus_d_une_autre_application_n_est_jamais_touche(banc):
    app, autre, port = banc["app"], banc["autre"], banc["port"]
    py_autre = _faux_runtime(autre)
    _poser(autre, "etranger")
    etranger = _demarrer(py_autre, autre, port)        # même ligne de commande, exécutable hors de l'app
    _attendre_sante(port, "etranger")

    _installer_lanceur(app, port)
    s = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(app / "scripts" / "stop.ps1"), "-Port", str(port), "-AppDir", str(app),
                        "-DelaiSec", "2"], capture_output=True, text=True, timeout=120)
    assert s.returncode == 2, s.stdout + s.stderr
    assert _vivant(etranger.pid)

    _poser(app, "nouveau")
    r = _lancer(app / "scripts" / "launch-silent.vbs", banc["donnees"])
    assert r.returncode == 1 and "OUVERT" not in r.stdout, r.stdout
    assert str(port) in r.stdout                      # le message nomme le port occupé
    assert _vivant(etranger.pid) and _sante(port)["version"] == "etranger"


def test_r3_une_reponse_de_l_ancien_processus_n_ouvre_pas_le_navigateur(banc):
    app, port = banc["app"], banc["port"]
    _poser(app, "ancien")
    _demarrer(banc["py"], app, port)
    _attendre_sante(port, "ancien")
    time.sleep(2.5)                                    # l'ancien est franchement plus vieux que le lancement

    _poser(app, "nouveau")
    r = _lancer(_installer_lanceur(app, port, sans_arret=True, essais=12), banc["donnees"])
    assert r.returncode == 1 and "OUVERT" not in r.stdout, r.stdout
    assert _sante(port)["version"] == "ancien"


def test_r4_api_health_rend_le_pid_du_processus_qui_repond():
    src = (RACINE / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8")
    i = src.index("async def health():")
    corps = src[i:src.index("\n@router", i)]
    assert '"pid": os.getpid()' in corps
    assert re.search(r"(?m)^import os\b|^import .*\bos\b", src)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
