"""Stage 5: Ownership analysis (forward data-flow on the CFG).

Abstract state per owned variable = a SET of possible facts (a powerset lattice):
    ('U',)       declared, no value yet
    ('O',)       owns a live allocation
    ('M', line)  ownership moved away at `line`
    ('F', line)  allocation freed at `line`
Join at a control-flow merge is set union, so Owned + Freed = {O, F} = "MaybeFreed".
The analysis is path-insensitive: it does not evaluate branch conditions, so it assumes
both sides of every `if` and every loop iteration can happen (sound but conservative).
"""
from .diagnostics import Diagnostic


def join(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = out[k] | v if k in out else v
    return out


def _lines(items, tag):
    return sorted(x[1] for x in items if x[0] == tag)


class Analyzer:
    def __init__(self, cfg):
        self.cfg, self.diags, self.seen = cfg, [], set()
        self.in_states, self.out_states = {}, {}

    def report(self, ins, msg, kind, notes=()):
        key = (ins.line, ins.col, msg)
        if key not in self.seen:
            self.seen.add(key)
            self.diags.append(Diagnostic(ins.line, ins.col, msg, kind, list(notes)))

    # -- transfer function
    def step(self, st, ins, report):
        st = dict(st)
        sym, name = ins.sym, ins.sym.name
        items = st.get(sym.uid, frozenset())
        has = lambda t: any(x[0] == t for x in items)
        only_o = items == frozenset({("O",)})

        def check_live(verb):
            """Common check for use / move: pointer must be definitely owned."""
            if not report:
                return
            if has("U"):
                maybe = "" if items == frozenset({("U",)}) else "may be "
                self.report(ins, f"'{name}' {maybe}used before it is initialised", "uninitialised")
            if has("F"):
                ln = _lines(items, "F")
                if has("O") or has("M") or has("U"):
                    self.report(ins, f"'{name}' may be used after free", "use-after-free",
                                [f"freed at line {ln[0]} on some path"])
                else:
                    self.report(ins, f"'{name}' used after free", "use-after-free",
                                [f"freed at line {ln[0]}"])
            if has("M"):
                ln = _lines(items, "M")
                if has("O") or has("F") or has("U"):
                    self.report(ins, f"'{name}' may be used after its ownership was moved", "use-after-move",
                                [f"moved at line {ln[0]} on some path"])
                else:
                    self.report(ins, f"'{name}' used after its ownership was moved", "use-after-move",
                                [f"moved at line {ln[0]}"])

        if ins.op == "define":
            if report and has("O"):
                if only_o:
                    self.report(ins, f"'{name}' is overwritten while it still owns memory (leak)", "leak")
                else:
                    self.report(ins, f"'{name}' may be overwritten while it still owns memory (possible leak)", "leak")
            st[sym.uid] = frozenset({("O",)})
        elif ins.op == "decl":
            st[sym.uid] = frozenset({("U",)})
        elif ins.op == "use":
            check_live("use")
        elif ins.op == "move":
            check_live("move")
            st[sym.uid] = frozenset({("M", ins.line)})
        elif ins.op == "free":
            if report:
                if has("U"):
                    check_live("free")
                if has("F"):
                    ln = _lines(items, "F")
                    if has("O") or has("M") or has("U"):
                        self.report(ins, f"possible double free of '{name}'", "double-free",
                                    [f"already freed at line {ln[0]} on some path"])
                    else:
                        self.report(ins, f"double free of '{name}'", "double-free",
                                    [f"first freed at line {ln[0]}"])
                if has("M"):
                    ln = _lines(items, "M")
                    self.report(ins, f"'{name}' is freed after its ownership was moved"
                                + ("" if items == frozenset({("M", ln[0])}) else " on some path"),
                                "use-after-move", [f"moved at line {ln[0]}"])
            st[sym.uid] = frozenset({("F", ins.line)})
        elif ins.op == "exit":
            if report and has("O"):
                if only_o:
                    self.report(ins, f"memory leak: '{name}' is never freed or moved", "leak",
                                [f"allocated by '{name}' declared at line {sym.line}"])
                else:
                    self.report(ins, f"possible memory leak: '{name}' is not freed or moved on some path", "leak",
                                [f"declared at line {sym.line}"])
            st.pop(sym.uid, None)
        return st

    def run(self):
        blocks = {b.id: b for b in self.cfg.blocks}
        IN = {self.cfg.entry.id: {}}
        OUT = {}
        work = [self.cfg.entry]
        while work:                                   # phase 1: fixpoint, no reporting
            b = work.pop(0)
            st = IN[b.id]
            for ins in b.instrs:
                st = self.step(st, ins, False)
            if OUT.get(b.id) == st:
                continue
            OUT[b.id] = st
            for s in b.succs:
                new = join(IN[s.id], st) if s.id in IN else st
                if IN.get(s.id) != new:
                    IN[s.id] = new
                    work.append(s)
        self.in_states = IN
        self.out_states = OUT
        for bid in sorted(IN):                        # phase 2: report once, on the final states
            st = IN[bid]
            for ins in blocks[bid].instrs:
                st = self.step(st, ins, True)
        return sorted(self.diags, key=lambda d: (d.line, d.col))

    def dump_states(self):
        """Human-readable converged data-flow states for the teaching UI."""
        labels = {"U": "Uninit", "O": "Owned", "M": "Moved", "F": "Freed"}

        def show(state):
            if not state:
                return "(no owned values)"
            rows = []
            for uid, facts in sorted(state.items()):
                sym = next((i.sym for b in self.cfg.blocks for i in b.instrs
                            if i.sym.uid == uid), None)
                name = sym.name if sym else f"value#{uid}"
                fs = []
                for fact in sorted(facts):
                    tag = labels[fact[0]]
                    fs.append(f"{tag}@{fact[1]}" if len(fact) > 1 else tag)
                rows.append(f"{name} = {{{', '.join(fs)}}}")
            return "; ".join(rows)

        lines = ["Converged ownership facts at each reachable basic block:"]
        for block in self.cfg.blocks:
            if block.id not in self.in_states:
                continue
            lines.append(f"B{block.id} IN:  {show(self.in_states[block.id])}")
            lines.append(f"B{block.id} OUT: {show(self.out_states.get(block.id, {}))}")
        return "\n".join(lines)


def check_ownership(cfgs):
    out = []
    for c in cfgs:
        out += Analyzer(c).run()
    return out
