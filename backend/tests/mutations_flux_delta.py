# -*- coding: utf-8 -*-
"""Mutations de L4.1 T3 (la réponse de l'agent au fil de l'eau) : casser -> rouge -> remettre.

PAS UN TEST : son nom ne commence pas par `test_`. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_flux_delta.py            # toutes
    python tests/mutations_flux_delta.py 3 7        # celles-là (numéros à partir de 1)

Il MUTE les sources une à une et les REMET à l'octet près (assertion sha256, même en cas d'exception) : ne pas le lancer
pendant qu'un autre banc lit `moteurs_texte.py` / `agent_campagnes.py`. Chaque ancre est UNE ligne exacte. Une VERTE est
une assertion qui manque ; ERREUR = le banc n'a imprimé aucun bilan. Code 0 si TOUTES sont ROUGES."""
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable
MT = "backend/app/services/moteurs_texte.py"
AC = "backend/app/services/agent_campagnes.py"
B = "test_agent_flux_delta.py"
_FIN = re.compile(r"=== \d+ passed")

# (fichier, ancre = UNE ligne exacte, remplacement, banc, étiquettes attendues rouges, intention)
M = [
    (MT, '    body: dict = {"model": modele, "max_tokens": max_tokens, "messages": messages, "stream": True}',
     '    body: dict = {"model": modele, "max_tokens": max_tokens, "messages": messages}',
     B, ["d1b"], "le corps part sans stream:true"),
    (MT, "                    sur_delta(s)", "                    pass",
     B, ["d1", "d2", "d5"], "les text_delta ne sont plus rendus à mesure"),
    (MT, '                morceaux[i].append(str(d.get("partial_json") or ""))', "                pass",
     B, ["d2"], "les input_json_delta ne sont plus recollés"),
    (MT, '                out_tok = int(u.get("output_tokens") or 0)', "                pass",
     B, ["d3"], "l'usage de sortie de message_delta est ignoré"),
    (MT, '            in_tok, out_tok = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)',
     '            in_tok, out_tok = 0, 0',
     B, ["d3", "d4b"], "l'usage d'entrée de message_start est ignoré"),
    (MT, "    if not fini:", "    if False:",
     B, ["d4"], "un flux coupé avant message_stop est pris pour un message entier"),
    (MT, '        elif t == "message_stop":', '        elif t == "message_stop_":',
     B, ["d1", "d2"], "message_stop n'est plus reconnu : aucun flux ne finit"),
    (MT, '        elif t == "error":', '        elif t == "error_":',
     B, ["d5b"], "l'évènement error du flux est ignoré"),
    (MT, '                if arret != "max_tokens":                      # entrée coupée : tolérée seulement si le tour est tronqué',
     "                if False:",
     B, ["d5e"], "une entrée d'outil illisible hors troncature devient {} et s'exécute"),
    (MT, '                m = m.replace(cle, "***")', "                pass",
     B, ["d5b"], "la clé fuit dans l'évènement error du flux"),
    (MT, '            raise RuntimeError(f"Anthropic HTTP {r.status_code} — {texte[:200]}")', "            pass",
     B, ["d5c"], "un statut ≠ 200 est lu comme un flux"),
    (MT, '            texte = str(r.text or "").replace(cle, "***")', '            texte = str(r.text or "")',
     B, ["d5c"], "la clé fuit dans le corps d'une erreur HTTP"),
    (MT, "            fermer()", "            pass",
     B, ["d1c", "d4c"], "la réponse du flux n'est jamais fermée"),
    (MT, "            e = _json.loads(ligne[5:].strip())",
     '            e = _json.loads(ligne[5:].strip() if ligne.endswith(("}", "]")) else None)',
     B, ["d5f"], "une ligne data: illisible n'est plus écartée : elle fait tomber le tour"),
    (MT, "        if not isinstance(e, dict):", "        if False:",
     B, ["d5f"], "un data: qui n'est pas un objet fait tomber le tour"),
    (AC, '                yield {"type": "delta", "texte": prochain.result()}', "                pass",
     B, ["d1", "d2", "d5"], "la boucle n'émet plus aucun delta"),
    (AC, '            perdu = _usd(MT.op_tour(modele, getattr(e, "in_tok", 0), getattr(e, "out_tok", 0)))',
     "            perdu = 0.0",
     B, ["d4b"], "l'usage annoncé par un flux coupé n'est plus noté"),
    (AC, "                evts.append({\"type\": \"texte\", \"texte\": str(b[\"text\"])})", "                pass",
     B, ["d1"], "l'évènement texte entier n'est plus émis"),
]


def lire(banc):
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([PY, f"tests/{banc}"], capture_output=True, cwd=R / "backend", timeout=900, env=env)
    txt = (p.stdout + p.stderr).decode("utf-8", "replace")
    echecs = set(re.findall(r"^\s*FAIL\s+(\S+)", txt, re.M))
    erreur = not _FIN.search(txt) and not echecs
    return echecs, txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus, intention) in enumerate(M, 1):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        sha_avant = hashlib.sha256(src).hexdigest()
        brut = src.decode("utf-8")
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        assert "\n" not in old, (i, "ancre multi-ligne")
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:70])
        p.write_bytes(txt.replace(old, new).replace("\n", eol).encode("utf-8"))
        try:
            echecs, sortie, erreur = lire(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        if erreur:
            verdict = "ERREUR"
            print(sortie[-1500:], file=sys.stderr)
        elif echecs:
            verdict = "ROUGE"
        else:
            verdict = "VERTE"
        manquants = [a for a in attendus if a not in echecs]
        note = f"  (rouge, mais pas sur {manquants})" if verdict == "ROUGE" and manquants else ""
        bilan.append((i, rel, banc, verdict, sorted(echecs), manquants))
        print(f"{verdict} {i} {rel} {intention} [{banc} -> {sorted(echecs)}]{note}")
        sys.stdout.flush()
    n = {v: sum(1 for b in bilan if b[3] == v) for v in ("ROUGE", "VERTE", "ERREUR")}
    print(f"\n{len(bilan)} mutation(s) : {n['ROUGE']} ROUGE, {n['VERTE']} VERTE, {n['ERREUR']} ERREUR")
    for b in bilan:
        if b[3] != "ROUGE":
            print(f"  {b[3]} [{b[0]}] {b[1]} -- banc {b[2]}, attendait {b[5] or b[4]}")
    print(json.dumps([b[:4] for b in bilan], ensure_ascii=False))
    return 0 if bilan and n["ROUGE"] == len(bilan) else 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
