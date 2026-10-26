"""Stage 4: IR + control-flow graph.

Each function becomes basic blocks of *ownership instructions*:
  define p   p now holds a fresh owned allocation (alloc / call returning own / parameter)
  decl p     p declared without a value
  use p      p is dereferenced or lent to a borrowing parameter
  move p     ownership leaves p (assignment, own-parameter call, return)
  free p     p's allocation is released
  exit p     p goes out of scope (end of block or return): must not still own memory
Plain integer computation does not affect ownership, so it is not in the IR.
"""
from dataclasses import dataclass, field
from .diagnostics import Diagnostic
from .nodes import *
from .sema import is_fresh


@dataclass
class Instr:
    op: str
    sym: object
    line: int
    col: int

    def __str__(self):
        return f"{self.op} {self.sym.name}   (line {self.line})"


@dataclass
class BasicBlock:
    id: int
    instrs: list = field(default_factory=list)
    succs: list = field(default_factory=list)
    preds: list = field(default_factory=list)
    note: str = ""


@dataclass
class FuncCFG:
    name: str
    blocks: list
    entry: BasicBlock
    exit: BasicBlock

    def reachable(self):
        seen, stack = set(), [self.entry]
        while stack:
            b = stack.pop()
            if b.id in seen:
                continue
            seen.add(b.id)
            stack.extend(b.succs)
        return seen

    def dump(self):
        out = [f"function {self.name}:"]
        live = self.reachable()
        for b in self.blocks:
            if b.id not in live:
                continue
            tag = f"  ; {b.note}" if b.note else ""
            out.append(f"  B{b.id}:{tag}")
            out += [f"    {i}" for i in b.instrs]
            out.append("    -> " + (", ".join(f"B{s.id}" for s in b.succs) or "(end)"))
        return "\n".join(out)


class Builder:
    def __init__(self, func):
        self.f, self.blocks, self.errors = func, [], []
        self.entry = self.new("entry")
        self.exit = self.new("exit")
        self.cur = self.entry
        self.scopes = [[]]          # owned symbols declared per scope

    def new(self, note=""):
        b = BasicBlock(len(self.blocks), note=note)
        self.blocks.append(b)
        return b

    def edge(self, a, b):
        a.succs.append(b)
        b.preds.append(a)

    def emit(self, op, sym, node):
        self.cur.instrs.append(Instr(op, sym, node.line, node.col))

    # -- expressions
    def value_out(self, e):
        """e is handed over as an owned value (decl init, assignment, own argument, return)."""
        if isinstance(e, Var):
            if e.ty == "own":
                self.emit("move", e.sym, e)
        else:
            self.eval(e)

    def eval(self, e):
        if isinstance(e, Deref):
            if e.target.ty == "own":
                self.emit("use", e.target.sym, e.target)
        elif isinstance(e, Unary):
            self.eval(e.operand)
        elif isinstance(e, Binary):
            self.eval(e.left)
            self.eval(e.right)
        elif isinstance(e, Alloc):
            self.eval(e.size)
        elif isinstance(e, Call):
            for a, pt in zip(e.args, e.func.ptypes):
                if pt == "own":
                    self.value_out(a)
                elif pt == "ptr":
                    if isinstance(a, Var) and a.ty == "own":
                        self.emit("use", a.sym, a)
                else:
                    self.eval(a)

    # -- statements
    def exits(self, upto, node):
        for sc in reversed(self.scopes[upto:]):
            for sym in reversed(sc):
                self.emit("exit", sym, node)

    def build(self):
        for p in self.f.params:
            if p.pty == "own":
                self.cur.instrs.append(Instr("define", p.sym, p.line, p.col))
                self.scopes[0].append(p.sym)
        self.stmt(self.f.body, fn_body=True)
        end = self.cur
        self.exits(0, Node(self.f.body.end_line, self.f.body.end_col))
        self.edge(self.cur, self.exit)
        if self.f.ret != "void" and end.id in self._reach():
            self.errors.append(Diagnostic(self.f.body.end_line, self.f.body.end_col,
                f"function '{self.f.name}' may reach its end without returning a value", "type"))
        return FuncCFG(self.f.name, self.blocks, self.entry, self.exit)

    def _reach(self):
        return FuncCFG("", self.blocks, self.entry, self.exit).reachable()

    def stmt(self, s, fn_body=False):
        if isinstance(s, Block):
            if not fn_body:
                self.scopes.append([])
            for x in s.stmts:
                self.stmt(x)
            if not fn_body:
                self.exits(len(self.scopes) - 1, Node(s.end_line, s.end_col))
                self.scopes.pop()
        elif isinstance(s, Decl):
            if s.vty == "own":
                if s.init is not None:
                    self.value_out(s.init)
                    self.emit("define", s.sym, s)
                else:
                    self.emit("decl", s.sym, s)
                self.scopes[-1].append(s.sym)
            elif s.init is not None:
                self.eval(s.init)
        elif isinstance(s, Assign):
            if s.sym.ty == "own":
                self.value_out(s.value)
                self.emit("define", s.sym, s)
            else:
                self.eval(s.value)
        elif isinstance(s, Store):
            self.eval(s.value)
            if s.target.ty == "own":
                self.emit("use", s.target.sym, s.target)
        elif isinstance(s, Free):
            self.emit("free", s.target.sym, s.target)
        elif isinstance(s, ExprStmt):
            self.eval(s.expr)
        elif isinstance(s, If):
            self.eval(s.cond)
            head = self.cur
            join = self.new("join")
            th = self.new("then")
            self.edge(head, th)
            self.cur = th
            self.stmt(s.then)
            self.edge(self.cur, join)
            if s.els:
                el = self.new("else")
                self.edge(head, el)
                self.cur = el
                self.stmt(s.els)
                self.edge(self.cur, join)
            else:
                self.edge(head, join)
            self.cur = join
        elif isinstance(s, While):
            hdr = self.new("loop header")
            self.edge(self.cur, hdr)
            self.cur = hdr
            self.eval(s.cond)
            body, after = self.new("loop body"), self.new("loop exit")
            self.edge(hdr, body)
            self.edge(hdr, after)
            self.cur = body
            self.stmt(s.body)
            self.edge(self.cur, hdr)
            self.cur = after
        elif isinstance(s, Return):
            if s.value is not None:
                self.value_out(s.value) if self.f.ret == "own" else self.eval(s.value)
            self.exits(0, s)
            self.edge(self.cur, self.exit)
            self.cur = self.new("unreachable")


def build_cfgs(prog):
    cfgs, errs = [], []
    for f in prog.funcs:
        b = Builder(f)
        cfgs.append(b.build())
        errs += b.errors
    return cfgs, errs
