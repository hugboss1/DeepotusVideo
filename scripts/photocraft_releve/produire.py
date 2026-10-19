"""Ordonne les specs extraites comme build() et écrit le JSON au format de photocraft_commandes_0.3.0.json.
Usage: python -I produire.py <racine> <x.json> <sortie.json> [verite.json]"""
import json, os, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
root, xp, outp = sys.argv[1:4]
truth = sys.argv[4] if len(sys.argv) > 4 else None
src = os.path.join(root, "crates", "engine", "src")
x = json.load(open(xp, encoding="utf-8"))

def mod_file(mod):
    parts = mod.split("::")
    for cand in (os.path.join(src, *parts) + ".rs", os.path.join(src, *parts, "mod.rs")):
        if os.path.exists(cand): return os.path.relpath(cand, root).replace("\\", "/")
    return None

order = {}
def visit(relf, base):
    """Assign rank to file relf; then the specs() calls it makes (in source order)."""
    if relf in order: return
    order[relf] = len(order)
    txt = open(os.path.join(root, relf), encoding="utf-8").read()
    for m in re.finditer(r"(?:crate::|super::|self::)?([a-z_][a-z0-9_:]*)::specs\(\)", txt):
        mod = m.group(1)
        if m.group(0).startswith("crate::"): f = mod_file(mod)
        else:
            here = os.path.splitext(relf)[0]
            if here.endswith("/mod"): here = here[:-4]
            f = mod_file(os.path.relpath(os.path.join(root, here), os.path.join(root, "crates/engine/src")).replace("\\", "/").replace("/", "::") + "::" + mod) or mod_file(mod)
        if f: visit(f, base)
visit("crates/engine/src/commands.rs", 0)
miss_rank = sorted({s["_file"] for s in x["specs"]} - set(order))
for f in miss_rank: order[f] = len(order)

ALWAYS = {"always", "native", "crate :: file_cmds :: native", "has_pattern", "crate :: commands :: always", "has_swatches", "has_groups"}
def enabled(fn):
    if fn in ALWAYS: return True
    if re.fullmatch(r"\| _?s? \| Ok G", fn or ""): return True
    return False

specs = sorted(x["specs"], key=lambda s: (order[s["_file"]], s["_line"], s.get("_sub", 0)))
out = [{"enabled": enabled(s.get("_enabled_fn", "")), "id": s["id"], "label": s["label"], "menu": s["menu"], "params": s["params"], "shortcut": s["shortcut"]} for s in specs]
json.dump(out, open(outp, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=2)
print(len(out), "commandes ;", sum(o["enabled"] for o in out), "enabled ; fichiers hors arbre specs():", miss_rank)
if truth:
    T = json.load(open(truth, encoding="utf-8"))
    same = sum(1 for a, b in zip(T, out) if a == b)
    print("identiques entrée par entrée (ordre compris):", same, "/", len(T))
    print("ensemble identique:", sorted(json.dumps(a, sort_keys=True) for a in T) == sorted(json.dumps(b, sort_keys=True) for b in out))
    fns = {}
