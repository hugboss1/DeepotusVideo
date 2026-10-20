"""Extraction statique des CommandSpec de photocraft (crates/engine/src), sans compiler.
Mini lexer Rust + expanseur macro_rules simplifié. Usage: python -I extraire_cmds.py <racine_depot> <sortie.json>
"""
import json, os, re, sys

# ---------------- lexer ----------------
class Tok:
    __slots__ = ("k", "v", "pos")
    def __init__(s, k, v, pos): s.k, s.v, s.pos = k, v, pos
    def __repr__(s): return f"{s.k}:{s.v!r}"

ESC = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", "'": "'", '"': '"'}

def lex(src):
    i, n, out = 0, len(src), []
    while i < n:
        c = src[i]
        if c.isspace(): i += 1; continue
        if src.startswith("//", i):
            j = src.find("\n", i); i = n if j < 0 else j; continue
        if src.startswith("/*", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if src.startswith("/*", i): depth += 1; i += 2
                elif src.startswith("*/", i): depth -= 1; i += 2
                else: i += 1
            continue
        m = re.match(r'b?r(#*)"', src[i:i+20])
        if m and (i == 0 or not (src[i-1].isalnum() or src[i-1] == "_")):
            hashes = m.group(1); start = i + m.end(); end = src.find('"' + hashes, start)
            out.append(Tok("S", src[start:end], i)); i = end + 1 + len(hashes); continue
        if c == '"' or (c == "b" and i + 1 < n and src[i+1] == '"' and not (i and (src[i-1].isalnum() or src[i-1]=="_"))):
            if c == "b": i += 1
            j, buf = i + 1, []
            while src[j] != '"':
                if src[j] == "\\":
                    e = src[j+1]
                    if e == "\n":
                        j += 2
                        while src[j] in " \t\r\n": j += 1
                        continue
                    if e == "u":
                        k = src.find("}", j); buf.append(chr(int(src[j+3:k], 16))); j = k + 1; continue
                    if e == "x":
                        buf.append(chr(int(src[j+2:j+4], 16))); j += 4; continue
                    buf.append(ESC.get(e, e)); j += 2; continue
                buf.append(src[j]); j += 1
            out.append(Tok("S", "".join(buf), i)); i = j + 1; continue
        if c == "'":
            if i + 1 < n and src[i+1] == "\\":
                j = src.find("'", i + 3); out.append(Tok("C", src[i:j+1], i)); i = j + 1; continue
            if i + 2 < n and src[i+2] == "'":
                out.append(Tok("C", src[i:i+3], i)); i += 3; continue
            m = re.match(r"'[A-Za-z_][A-Za-z0-9_]*", src[i:])
            out.append(Tok("L", m.group(0), i)); i += m.end(); continue
        if c.isalpha() or c == "_":
            m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", src[i:])
            out.append(Tok("I", m.group(0), i)); i += m.end(); continue
        if c.isdigit():
            m = re.match(r"[0-9][0-9_]*(\.[0-9][0-9_]*)?([eE][+-]?[0-9]+)?[A-Za-z0-9_]*", src[i:])
            out.append(Tok("N", m.group(0), i)); i += m.end(); continue
        if src.startswith("=>", i) or src.startswith("::", i) or src.startswith("->", i):
            out.append(Tok("P", src[i:i+2], i)); i += 2; continue
        out.append(Tok("P", c, i)); i += 1
    return out

class Grp:
    __slots__ = ("open", "kids", "pos", "binds")
    def __init__(s, o, kids, pos): s.open, s.kids, s.pos, s.binds = o, kids, pos, None
    k = "G"
    def __repr__(s): return f"G{s.open}{s.kids!r}"

PAIR = {"(": ")", "[": "]", "{": "}"}

def tree(toks):
    stack = [[]]; opens = []
    for t in toks:
        if t.k == "P" and t.v in PAIR:
            stack.append([]); opens.append(t)
        elif t.k == "P" and t.v in ")]}":
            kids = stack.pop(); o = opens.pop(); stack[-1].append(Grp(o.v, kids, o.pos))
        else:
            stack[-1].append(t)
    return stack[0]

def is_p(t, v): return getattr(t, "k", None) == "P" and t.v == v
def is_i(t, v=None): return getattr(t, "k", None) == "I" and (v is None or t.v == v)

# ---------------- macro_rules ----------------
def parse_macro(body):
    arms, i, ks = [], 0, body.kids
    while i < len(ks):
        if isinstance(ks[i], Grp) and i + 2 < len(ks) and is_p(ks[i+1], "=>") and isinstance(ks[i+2], Grp):
            arms.append((ks[i].kids, ks[i+2].kids)); i += 3
        else: i += 1
    return arms

class NoMatch(Exception): pass

def match(pat, toks):
    b = {}
    pi = ti = 0
    while pi < len(pat):
        p = pat[pi]
        if is_p(p, "$") and pi + 1 < len(pat):
            q = pat[pi+1]
            if isinstance(q, Grp) and q.open == "(":
                # repetition $( ... ) sep? op
                sep = None; j = pi + 2
                if j < len(pat) and not (is_p(pat[j], "*") or is_p(pat[j], "+") or is_p(pat[j], "?")):
                    sep = pat[j]; j += 1
                op = pat[j].v; nxt = pat[j+1] if j + 1 < len(pat) else None
                reps = []
                while ti < len(toks):
                    if nxt is not None and not isinstance(nxt, Grp) and _tok_eq(toks[ti], nxt) and not _could_start(q.kids):
                        break
                    seg_end = ti
                    # segment = until sep at top level
                    if sep is not None:
                        while seg_end < len(toks) and not _tok_eq(toks[seg_end], sep): seg_end += 1
                    else:
                        seg_end = len(toks) if nxt is None else _find(toks, ti, nxt)
                    seg = toks[ti:seg_end]
                    if not seg: break
                    try: reps.append(match(q.kids, seg))
                    except NoMatch: break
                    ti = seg_end
                    if sep is not None and ti < len(toks) and _tok_eq(toks[ti], sep): ti += 1
                    else: break
                for name in _names(q.kids): b[name] = [r.get(name) for r in reps]
                b.setdefault("__reps__", {})
                pi = j + 1; continue
            if q.k == "I":
                name = q.v; frag = None
                if pi + 3 < len(pat) and is_p(pat[pi+2], ":") and is_i(pat[pi+3]):
                    frag = pat[pi+3].v; pi += 4
                else: pi += 2
                nxt = pat[pi] if pi < len(pat) else None
                if frag in ("literal", "ident", "lifetime", "tt"):
                    if ti >= len(toks): raise NoMatch
                    if frag == "literal" and is_p(toks[ti], "-"):
                        b[name] = toks[ti:ti+2]; ti += 2
                    else:
                        if frag == "literal" and toks[ti].k not in ("S", "N", "C") and not is_i(toks[ti], "true") and not is_i(toks[ti], "false"): raise NoMatch
                        if frag == "ident" and toks[ti].k != "I": raise NoMatch
                        b[name] = toks[ti:ti+1]; ti += 1
                else:
                    st = ti
                    if st < len(toks) and is_i(toks[st], "move"): st += 1
                    if st < len(toks) and is_p(toks[st], "|"):
                        st += 1
                        while st < len(toks) and not is_p(toks[st], "|"): st += 1
                        st += 1
                    end = _find(toks, st, nxt) if nxt is not None else _find(toks, st, Tok("P", ",", 0))
                    if end == ti: raise NoMatch
                    b[name] = toks[ti:end]; ti = end
                continue
        # literal token / group
        if ti >= len(toks): raise NoMatch
        t = toks[ti]
        if isinstance(p, Grp):
            if not isinstance(t, Grp) or t.open != p.open: raise NoMatch
            b.update(match(p.kids, t.kids)); pi += 1; ti += 1; continue
        if not _tok_eq(t, p): raise NoMatch
        pi += 1; ti += 1
    # allow trailing comma
    if ti < len(toks) and not (ti == len(toks) - 1 and is_p(toks[ti], ",")): raise NoMatch
    return b

def _could_start(kids): return False
def _tok_eq(a, b): return not isinstance(a, Grp) and not isinstance(b, Grp) and a.k == b.k and a.v == b.v
def _find(toks, start, nxt):
    j = start
    while j < len(toks) and not _tok_eq(toks[j], nxt): j += 1
    return j
def _names(kids):
    out = []
    for i, k in enumerate(kids):
        if is_p(k, "$") and i + 1 < len(kids) and is_i(kids[i+1]): out.append(kids[i+1].v)
        if isinstance(k, Grp): out += _names(k.kids)
    return out

def transcribe(body, b):
    out, i = [], 0
    while i < len(body):
        t = body[i]
        if is_p(t, "$") and i + 1 < len(body):
            q = body[i+1]
            if isinstance(q, Grp) and q.open == "(":
                j = i + 2; sep = None
                if not (is_p(body[j], "*") or is_p(body[j], "+") or is_p(body[j], "?")): sep = body[j]; j += 1
                names = [n for n in _names(q.kids) if n in b and isinstance(b[n], list) and b[n] and isinstance(b[n][0], (list, type(None)))]
                cnt = max((len(b[n]) for n in names), default=0)
                for r in range(cnt):
                    sub = dict(b)
                    for n in names: sub[n] = b[n][r]
                    out += transcribe(q.kids, sub)
                    if sep is not None and r < cnt - 1: out.append(sep)
                i = j + 1; continue
            if is_i(q) and q.v in b:
                v = b[q.v]; out += v if v else []; i += 2; continue
        if isinstance(t, Grp): out.append(Grp(t.open, transcribe(t.kids, b), t.pos))
        else: out.append(t)
        i += 1
    return out

# ---------------- evaluation ----------------
class Unres(Exception): pass

def split_commas(toks):
    parts, cur = [], []
    for t in toks:
        if is_p(t, ","): parts.append(cur); cur = []
        else: cur.append(t)
    if cur: parts.append(cur)
    return parts

class Ctx:
    def __init__(s, consts): s.consts = consts; s.macros = {}

GALLERY = {}
METHODS_STRIP = {"into_boxed_str", "to_string", "as_str", "into", "to_owned"}

def fmt(template, args, ctx, depth):
    pos = [a for a in args if not (len(a) >= 2 and is_i(a[0]) and is_p(a[1], "="))]
    named = {a[0].v: a[2:] for a in args if len(a) >= 2 and is_i(a[0]) and is_p(a[1], "=")}
    it = iter(pos)
    def rep(m):
        inner = m.group(1)
        if inner == "{{": return "{"
        if inner == "}}": return "}"
        name = inner[1:-1].split(":")[0]
        if name == "": return str(ev(next(it), ctx, depth+1))
        if name.isdigit(): return str(ev(pos[int(name)], ctx, depth+1))
        if name in named: return str(ev(named[name], ctx, depth+1))
        return str(ev([Tok("I", name, 0)], ctx, depth+1))
    return re.sub(r"(\{\{|\}\}|\{[^{}]*\})", rep, template)

def ev(toks, ctx, depth=0):
    toks = [t for t in toks]
    if depth > 30: raise Unres("depth")
    while toks and is_p(toks[0], "&"): toks = toks[1:]
    while toks and is_p(toks[-1], ","): toks = toks[:-1]
    # cut `as` casts
    for k, t in enumerate(toks):
        if is_i(t, "as"): toks = toks[:k]; break
    # strip trailing .method()
    while len(toks) >= 4 and is_p(toks[-3], ".") and is_i(toks[-2]) and toks[-2].v in METHODS_STRIP and isinstance(toks[-1], Grp):
        toks = toks[:-3]
    # Box::leak(x) / leak(x)
    if len(toks) >= 2 and is_i(toks[-2], "leak") and isinstance(toks[-1], Grp) and toks[-1].open == "(":
        return ev(toks[-1].kids, ctx, depth+1)
    # GalleryFilter::V.method()
    if len(toks) == 6 and is_i(toks[0], "GalleryFilter") and is_p(toks[1], "::") and is_p(toks[3], ".") and toks[2].v in GALLERY:
        g = GALLERY[toks[2].v]; m = toks[4].v
        if m in g: return g[m]
    if len(toks) == 1 and getattr(toks[0], "k", "") == "I" and toks[0].v in getattr(ctx, "local", {}):
        return ctx.local[toks[0].v]
    if len(toks) == 1:
        t = toks[0]
        if t.k == "S": return t.v
        if is_i(t, "None"): return None
        if is_i(t, "true"): return True
        if is_i(t, "false"): return False
        if t.k == "I" and t.v in ctx.consts: return ctx.consts[t.v]
        if isinstance(t, Grp) and t.open == "[": return [ev(p, ctx, depth+1) for p in split_commas(t.kids)]
        if isinstance(t, Grp) and t.open == "(":
            parts = split_commas(t.kids)
            if len(parts) > 1: return [ev(p, ctx, depth+1) for p in parts]
            return ev(t.kids, ctx, depth+1)
        raise Unres(str(t)[:80])
    if len(toks) == 2 and is_i(toks[0], "Some") and isinstance(toks[1], Grp): return ev(toks[1].kids, ctx, depth+1)
    # path::CONST
    if all((t.k == "I" or is_p(t, "::")) for t in toks if not isinstance(t, Grp)) and not any(isinstance(t, Grp) for t in toks):
        last = toks[-1].v
        if last in ctx.consts: return ctx.consts[last]
        raise Unres("path " + last)
    # macro invocation (possibly path-qualified): ... ident ! group
    if len(toks) >= 3 and is_p(toks[-2], "!") and isinstance(toks[-1], Grp) and is_i(toks[-3]):
        name = toks[-3].v; args = toks[-1].kids
        if name == "concat": return "".join(str(ev(p, ctx, depth+1)) for p in split_commas(args))
        if name == "stringify": return " ".join(getattr(t, "v", "") for t in args)
        if name == "format":
            parts = split_commas(args)
            return fmt(ev(parts[0], ctx, depth+1), parts[1:], ctx, depth)
        exp = expand(name, args, ctx)
        if exp is not None: return ev(exp, ctx, depth+1)
    raise Unres(" ".join(getattr(t, "v", "G") for t in toks)[:100])

def expand(name, args, ctx):
    for arms in reversed(ctx.macros.get(name, [])):
        for pat, body in arms:
            try: b = match(pat, args)
            except (NoMatch, IndexError): continue
            return transcribe(body, b)
    return None

# ---------------- scan ----------------
def strip_tests(ks):
    out, i = [], 0
    while i < len(ks):
        t = ks[i]
        # #[cfg(test)] mod x { }
        if is_p(t, "#") and i + 1 < len(ks) and isinstance(ks[i+1], Grp) and ks[i+1].open == "[":
            attr = ks[i+1].kids
            if len(attr) >= 2 and is_i(attr[0], "cfg") and isinstance(attr[1], Grp) and any(is_i(x, "test") for x in attr[1].kids) and not any(is_i(x,"not") for x in attr[1].kids):
                # skip the attributed item up to its {} group or ;
                j = i + 2
                while j < len(ks) and not (isinstance(ks[j], Grp) and ks[j].open == "{") and not is_p(ks[j], ";"): j += 1
                i = j + 1; continue
        out.append(Grp(t.open, strip_tests(t.kids), t.pos) if isinstance(t, Grp) else t)
        i += 1
    return out

def collect_macros(ks, ctx):
    for i, t in enumerate(ks):
        if is_i(t, "macro_rules") and i + 3 < len(ks) and is_p(ks[i+1], "!") and is_i(ks[i+2]) and isinstance(ks[i+3], Grp):
            ctx.macros.setdefault(ks[i+2].v, []).append(parse_macro(ks[i+3]))
        if isinstance(t, Grp): collect_macros(t.kids, ctx)

def collect_consts(ks, consts):
    """consts: name -> [(pos, toks)] pour const/static/let."""
    for i, t in enumerate(ks):
        if (is_i(t, "const") or is_i(t, "static") or is_i(t, "let")) and i + 1 < len(ks) and is_i(ks[i+1]):
            j = i + 1
            if is_i(ks[j], "mut"): j += 1
            if not is_i(ks[j]): continue
            name = ks[j].v
            k = j + 1
            while k < len(ks) and not is_p(ks[k], "=") and not is_p(ks[k], ";"): k += 1
            if k < len(ks) and is_p(ks[k], "="):
                e = k + 1
                while e < len(ks) and not is_p(ks[e], ";"): e += 1
                consts.setdefault(name, []).append((t.pos, ks[k+1:e]))
        if isinstance(t, Grp): collect_consts(t.kids, consts)

class Lazy(dict):
    def __init__(s, defs, pos, ctxf):
        super().__init__(); s.defs, s.pos, s.ctxf = defs, pos, ctxf; s.busy = set()
    def __contains__(s, name):
        return name in s.defs and s._get(name) is not KeyError
    def __getitem__(s, name):
        v = s._get(name)
        if v is KeyError: raise KeyError(name)
        return v
    def _get(s, name):
        if name in s.busy: return KeyError
        cands = sorted(s.defs.get(name, []), key=lambda d: d[0])
        before = [d for d in cands if d[0] < s.pos] or cands
        for d in reversed(before):
            s.busy.add(name)
            try:
                v = ev(d[1], s.ctxf(), 0)
                if isinstance(v, (str, list)) or v is None: return v
            except Exception: pass
            finally: s.busy.discard(name)
        return KeyError

HELPERS = {}

def _params_of(toks):
    names = []
    for part in split_commas(toks):
        if part and is_i(part[0]): names.append(part[0].v if not is_i(part[0], "mut") else part[1].v)
    return names

def collect_helpers(ks, helpers):
    for i, t in enumerate(ks):
        # let NAME = |a: T, b: T| CommandSpec { .. }
        if is_i(t, "let") and i + 3 < len(ks) and is_i(ks[i+1]) and is_p(ks[i+2], "=") and is_p(ks[i+3], "|"):
            j = i + 4
            while j < len(ks) and not is_p(ks[j], "|"): j += 1
            params = _params_of(ks[i+4:j])
            if j + 2 < len(ks) and is_i(ks[j+1], "CommandSpec") and isinstance(ks[j+2], Grp):
                helpers[ks[i+1].v] = (params, ks[j+2])
        # fn NAME(a: T, ..) -> CommandSpec { CommandSpec { .. } }
        if is_i(t, "fn") and i + 2 < len(ks) and is_i(ks[i+1]) and isinstance(ks[i+2], Grp) and ks[i+2].open == "(":
            j = i + 3
            while j < len(ks) and not (isinstance(ks[j], Grp) and ks[j].open == "{"): j += 1
            if j < len(ks):
                body = ks[j].kids
                if len(body) == 2 and is_i(body[0], "CommandSpec") and isinstance(body[1], Grp):
                    helpers[ks[i+1].v] = (_params_of(ks[i+2].kids), body[1])
        if isinstance(t, Grp): collect_helpers(t.kids, helpers)

def subst_helper(params, g, args):
    argl = split_commas(args)
    m = {n: argl[k] for k, n in enumerate(params) if k < len(argl)}
    parts = []
    for part in split_commas(g.kids):
        if len(part) == 1 and is_i(part[0]): part = [part[0], Tok("P", ":", 0), part[0]]
        if len(part) >= 2 and is_i(part[0]) and is_p(part[1], ":"):
            parts.append(part[:2] + _sub(part[2:], m))
        else: parts.append(part)
    kids = []
    for part in parts: kids += part + [Tok("P", ",", 0)]
    ng = Grp("{", kids, g.pos); ng.binds = m
    return ng

def _sub(toks, m):
    out = []
    for t in toks:
        if isinstance(t, Grp): out.append(Grp(t.open, _sub(t.kids, m), t.pos))
        elif t.k == "I" and t.v in m: out += m[t.v]
        else: out.append(t)
    return out

def find_specs(ks, ctx, out, fname, in_macro_def=False, depth=0):
    i = 0
    while i < len(ks):
        t = ks[i]
        if is_i(t, "macro_rules") and i + 3 < len(ks):
            i += 4; continue
        if is_i(t, "CommandSpec") and i + 1 < len(ks) and isinstance(ks[i+1], Grp) and ks[i+1].open == "{" and not (i > 0 and is_i(ks[i-1], "struct")):
            out.append((fname, ks[i+1], t.pos))
            find_specs(ks[i+1].kids, ctx, out, fname, depth=depth)
            i += 2; continue
        if is_i(t) and i + 2 < len(ks) and is_p(ks[i+1], "!") and isinstance(ks[i+2], Grp) and t.v in ctx.macros and depth < 20:
            exp = expand(t.v, ks[i+2].kids, ctx)
            if exp is not None:
                sub = []
                find_specs(exp, ctx, sub, fname, depth=depth+1)
                for (f, g, _) in sub: out.append((f, g, t.pos))
                i += 3; continue
        hk = getattr(ctx, "helpers", {})
        if is_i(t) and t.v in hk and i + 1 < len(ks) and isinstance(ks[i+1], Grp) and ks[i+1].open == "(" and not (i > 0 and (is_i(ks[i-1], "fn") or is_p(ks[i-1], "."))):
            params, g = hk[t.v]
            out.append((fname, subst_helper(params, g, ks[i+1].kids), t.pos))
            i += 2; continue
        if isinstance(t, Grp): find_specs(t.kids, ctx, out, fname, depth=depth)
        i += 1

def fields(g):
    d = {}
    for part in split_commas(g.kids):
        if len(part) >= 2 and is_i(part[0]) and is_p(part[1], ":"):
            d[part[0].v] = part[2:]
        elif len(part) == 1 and is_i(part[0]):
            d[part[0].v] = part  # shorthand `label,`
    return d

def main(root, outp):
    src_dir = os.path.join(root, "crates", "engine", "src")
    art = os.path.join(root, "crates", "algo", "src", "artistic.rs")
    if os.path.exists(art):
        for m in re.finditer(r'(\w+) = "(\w+)", "([^"]+)", "([^"]+)", r#"(.*?)"#;', open(art, encoding="utf-8").read()):
            GALLERY[m.group(1)] = {"command_id": "filter.gallery." + m.group(2), "name": m.group(3), "params_doc": m.group(5)}
    files = []
    for dp, dn, fn in os.walk(src_dir):
        for f in fn:
            if f.endswith(".rs") and f != "tests.rs" and not f.endswith("_tests.rs"):
                files.append(os.path.join(dp, f))
    trees, perfile, glob = {}, {}, {}
    for f in files:
        src = open(f, encoding="utf-8").read()
        ks = strip_tests(tree(lex(src)))
        trees[f] = (ks, src)
        d = {}; collect_consts(ks, d); perfile[f] = d
        for k, v in d.items():
            if k.isupper(): glob.setdefault(k, []).extend((-1, t) for (_, t) in v)
    gctx = Ctx({})
    for f, (ks, _) in trees.items(): collect_macros(ks, gctx)
    results, unresolved = [], []
    for f, (ks, src) in sorted(trees.items()):
        fctx = Ctx({}); collect_macros(ks, fctx)
        fctx.helpers = {}; collect_helpers(ks, fctx.helpers)
        for k, v in gctx.macros.items(): fctx.macros.setdefault(k, v)
        found = []
        find_specs(ks, fctx, found, f)
        for (fname, g, pos) in found:
            defs = dict(glob); defs.update(perfile[f])
            # local defs take precedence: merge lists, local positions are real
            merged = {k: list(glob.get(k, [])) + list(perfile[f].get(k, [])) for k in set(glob) | set(perfile[f])}
            for k in merged:
                if perfile[f].get(k): merged[k] = list(perfile[f][k])
            c = Ctx({}); c.macros = fctx.macros
            c.consts = Lazy(merged, pos, lambda c=c: c)
            fd = fields(g)
            c.local = {}
            for bn, bt in (g.binds or {}).items():
                try: c.local[bn] = ev(bt, c)
                except Exception: pass
            rec = {"_file": os.path.relpath(fname, root).replace("\\", "/"), "_line": src.count(chr(10), 0, pos) + 1}
            if "id" not in fd: continue
            if len(fd["id"]) == 1 and is_i(fd["id"][0]) and fd["id"][0].v in ("id",) and fctx.helpers: continue
            rec["_enabled_fn"] = " ".join(getattr(t, "v", "G") for t in fd.get("enabled", []))
            rec["_journal"] = " ".join(getattr(t, "v", "G") for t in fd.get("journal", []))
            for key in ("id", "label", "menu", "shortcut", "params"):
                if key not in fd: rec[key] = "<?>"; continue
                try: rec[key] = ev(fd[key], c)
                except Exception as e:
                    rec[key] = "<?>"; rec.setdefault("_unres", {})[key] = " ".join(getattr(t, "v", "G") for t in fd[key])[:160]
            if os.path.basename(f) == "commands.rs" and rec["id"] == "<?>" and fd["id"] and getattr(fd["id"][0], "v", None) in ("layer_id", "image_id"):
                rec["_adj"] = fd["id"][0].v
                unresolved.append(rec); continue
            (results if isinstance(rec.get("id"), str) and rec["id"] != "<?>" else unresolved).append(rec)
    # boucle ADJ de commands.rs
    cf = [f for f in trees if os.path.basename(f) == "commands.rs" and os.path.dirname(f) == src_dir][0]
    csrc = trees[cf][1]
    c = Ctx({}); c.macros = gctx.macros
    merged = {k: v for k, v in glob.items()}; merged.update(perfile[cf])
    c.consts = Lazy(merged, 10**9, lambda c=c: c)
    adj = c.consts["ADJ"]
    recs = {u["_adj"]: u for u in unresolved if "_adj" in u}
    lp = recs["layer_id"].get("_unres", {}).get("params", "")
    nlp = c.consts["NEW_LAYER_PATH"] if "NEW_LAYER_PATH" in lp else None
    mshort = re.search(r'shortcut: match kind \{(.*?)\}', csrc, re.S)
    sc = dict(re.findall(r'"(\w+)" => Some\("([^"]+)"\)', mshort.group(1))) if mshort else {}
    for kk, (kind, label, params) in enumerate(adj):
        results.append({"_file": "crates/engine/src/commands.rs", "_line": recs["layer_id"]["_line"], "_sub": 2 * kk, "id": f"layer.newAdjustmentLayer.{kind}", "label": label,
                        "menu": recs["layer_id"]["menu"], "shortcut": None, "_enabled_fn": recs["layer_id"]["_enabled_fn"], "params": f"{params} + {{{nlp}}}" if nlp else params})
        results.append({"_file": "crates/engine/src/commands.rs", "_line": recs["layer_id"]["_line"], "_sub": 2 * kk + 1, "id": f"image.adjustments.{kind}", "label": label,
                        "menu": recs["image_id"]["menu"], "shortcut": sc.get(kind), "_enabled_fn": recs["image_id"]["_enabled_fn"], "params": params})
    unresolved = [u for u in unresolved if "_adj" not in u]
    json.dump({"specs": results, "unresolved": unresolved}, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(results), "resolues,", len(unresolved), "non resolues")

def _mk(consts, macros):
    c = Ctx(consts); c.macros = macros; return c

if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main(sys.argv[1], sys.argv[2])
