import json, sys, collections, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
truth = json.load(open(sys.argv[1], encoding="utf-8"))
x = json.load(open(sys.argv[2], encoding="utf-8"))
T = {c["id"]: c for c in truth}
X = collections.defaultdict(list)
for s in x["specs"]: X[s["id"]].append(s)
print("truth", len(T), "extracted ids", len(X), "dups", sum(1 for v in X.values() if len(v) > 1))
miss = [i for i in T if i not in X]; extra = [i for i in X if i not in T]
print("manquants", len(miss)); print(" ", miss[:80])
print("en trop", len(extra)); print(" ", extra[:40])
diff = collections.Counter()
ex = collections.defaultdict(list)
for i, t in T.items():
    if i not in X: continue
    s = X[i][0]
    for k in ("label", "menu", "shortcut", "params"):
        if s.get(k) != t.get(k):
            diff[k] += 1; ex[k].append((i, s.get(k), t.get(k), s.get("_unres", {}).get(k)))
print(diff)
for k, v in ex.items():
    for e in v[:6]: print(k, repr(e)[:300])
print("non résolues:")
for u in x["unresolved"][:60]: print(" ", u["_file"], u["_line"], u.get("_unres"))
