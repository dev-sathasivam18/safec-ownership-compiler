"""Stage 3: Semantic analysis. Builds symbol tables, checks types, annotates the AST."""
from .diagnostics import Diagnostic
from .nodes import *


class Sym:
    _n = 0

    def __init__(self, name, ty, line, is_param=False):
        Sym._n += 1
        self.uid, self.name, self.ty, self.line, self.is_param = Sym._n, name, ty, line, is_param

    def __repr__(self):
        return f"{self.name}#{self.uid}"


class FuncSig:
    def __init__(self, name, ret, ptypes):
        self.name, self.ret, self.ptypes = name, ret, ptypes


BUILTINS = {"print": FuncSig("print", "void", ["int"])}


def is_fresh(e):
    """An expression that yields a brand-new owned pointer (nobody owns it yet)."""
    return isinstance(e, Alloc) or (isinstance(e, Call) and e.ty == "own")


class Sema:
    def __init__(self, prog):
        self.prog, self.errors, self.funcs = prog, [], dict(BUILTINS)
        self.scopes, self.cur = [], None

    def error(self, node, msg, kind="type", notes=None):
        self.errors.append(Diagnostic(node.line, node.col, msg, kind, notes or []))

    def run(self):
        for f in self.prog.funcs:
            if f.name in self.funcs or f.name in ("alloc", "free"):
                self.error(f, f"redefinition of function '{f.name}'", "name")
            else:
                self.funcs[f.name] = FuncSig(f.name, f.ret, [p.pty for p in f.params])
        for f in self.prog.funcs:
            self.check_func(f)
        if "main" not in self.funcs:
            self.errors.append(Diagnostic(1, 1, "program has no 'main' function", "name"))
        return self.errors

    # -- scopes
    def declare(self, node, name, ty, is_param=False):
        if name in self.scopes[-1]:
            self.error(node, f"'{name}' is already declared in this scope", "name")
        sym = Sym(name, ty, node.line, is_param)
        self.scopes[-1][name] = sym
        return sym

    def lookup(self, node, name):
        for sc in reversed(self.scopes):
            if name in sc:
                return sc[name]
        self.error(node, f"use of undeclared variable '{name}'", "name")
        return None

    def check_func(self, f):
        self.cur = f
        self.scopes = [{}]
        for p in f.params:
            p.sym = self.declare(p, p.name, p.pty, True)
        self.block(f.body, new_scope=False)

    # -- statements
    def block(self, b, new_scope=True):
        if new_scope:
            self.scopes.append({})
        for s in b.stmts:
            self.stmt(s)
        if new_scope:
            self.scopes.pop()

    def stmt(self, s):
        if isinstance(s, Block):
            self.block(s)
        elif isinstance(s, Decl):
            if s.vty == "ptr":
                self.error(s, "local variables cannot be borrowed pointers; use 'own int*'", "type")
            if s.init is not None:
                self.expect_value(s.init, s.vty, s)
            s.sym = self.declare(s, s.name, s.vty)
        elif isinstance(s, Assign):
            s.sym = self.lookup(s, s.name)
            if s.sym:
                if s.sym.ty == "ptr":
                    self.error(s, f"cannot reassign borrowed pointer '{s.name}'", "type")
                else:
                    self.expect_value(s.value, s.sym.ty, s)
            else:
                self.expr(s.value)
        elif isinstance(s, Store):
            self.var(s.target)
            if s.target.sym and s.target.ty not in ("own", "ptr"):
                self.error(s, f"cannot dereference '{s.target.name}': it is not a pointer", "type")
            self.require(s.value, "int")
        elif isinstance(s, Free):
            self.var(s.target)
            if s.target.sym and s.target.ty != "own":
                why = "a borrowed pointer" if s.target.ty == "ptr" else "not a pointer"
                self.error(s, f"cannot free '{s.target.name}': it is {why}", "type")
        elif isinstance(s, ExprStmt):
            t = self.expr(s.expr)
            if not isinstance(s.expr, (Call, Alloc)):
                self.error(s, "expression statement has no effect", "type")
            elif is_fresh(s.expr):
                self.error(s, "result of allocation is discarded (memory leak)", "leak")
        elif isinstance(s, If):
            self.require(s.cond, "int")
            self.scoped(s.then)
            if s.els:
                self.scoped(s.els)
        elif isinstance(s, While):
            self.require(s.cond, "int")
            self.scoped(s.body)
        elif isinstance(s, Return):
            self.ret(s)

    def scoped(self, s):
        self.scopes.append({})
        self.stmt(s)
        self.scopes.pop()

    def ret(self, s):
        want = self.cur.ret
        if s.value is None:
            if want != "void":
                self.error(s, f"function '{self.cur.name}' must return a value", "type")
        elif want == "void":
            self.expr(s.value)
            self.error(s, "void function cannot return a value", "type")
        else:
            self.expect_value(s.value, want, s)

    # -- expressions
    def var(self, v):
        v.sym = self.lookup(v, v.name)
        v.ty = v.sym.ty if v.sym else "error"
        return v.ty

    def require(self, e, ty):
        t = self.expr(e)
        if t != ty and t != "error":
            self.error(e, f"expected {TYPE_NAMES[ty]}, found {TYPE_NAMES.get(t, t)}", "type")

    def expect_value(self, e, ty, ctx):
        """e is used where a value of type ty is stored/returned. Pointers are moved/handed over."""
        t = self.expr(e)
        if t == "error":
            return
        if ty == "own":
            if t != "own":
                if t == "ptr":
                    self.error(e, f"cannot take ownership of borrowed pointer '{getattr(e, 'name', '?')}'", "type")
                else:
                    self.error(e, f"expected own int*, found {TYPE_NAMES.get(t, t)}", "type")
        elif t != ty:
            self.error(e, f"expected {TYPE_NAMES[ty]}, found {TYPE_NAMES.get(t, t)}", "type")

    def expr(self, e):
        if isinstance(e, Num):
            e.ty = "int"
        elif isinstance(e, Var):
            self.var(e)
        elif isinstance(e, Deref):
            self.var(e.target)
            if e.target.sym and e.target.ty not in ("own", "ptr"):
                self.error(e, f"cannot dereference '{e.target.name}': it is not a pointer", "type")
            e.ty = "int"
        elif isinstance(e, Unary):
            self.require(e.operand, "int")
            e.ty = "int"
        elif isinstance(e, Binary):
            self.require(e.left, "int")
            self.require(e.right, "int")
            e.ty = "int"
        elif isinstance(e, Alloc):
            self.require(e.size, "int")
            e.ty = "own"
        elif isinstance(e, Call):
            self.call(e)
        return e.ty

    def call(self, c):
        sig = self.funcs.get(c.name)
        if not sig:
            self.error(c, f"call to undefined function '{c.name}'", "name")
            for a in c.args:
                self.expr(a)
            c.ty = "error"
            return
        c.func, c.ty = sig, sig.ret
        if len(c.args) != len(sig.ptypes):
            self.error(c, f"'{c.name}' expects {len(sig.ptypes)} argument(s), got {len(c.args)}", "type")
        for a, pt in zip(c.args, sig.ptypes):
            t = self.expr(a)
            if t == "error":
                continue
            if pt == "own":
                if t == "ptr":
                    self.error(a, f"'{a.name}' is borrowed; '{c.name}' requires ownership", "type")
                elif t != "own":
                    self.error(a, f"expected own int*, found {TYPE_NAMES.get(t, t)}", "type")
            elif pt == "ptr":
                if t not in ("own", "ptr"):
                    self.error(a, f"expected a pointer, found {TYPE_NAMES.get(t, t)}", "type")
                elif is_fresh(a):
                    self.error(a, "temporary allocation passed to a borrowed parameter (memory leak)", "leak")
            elif t != "int":
                self.error(a, f"expected int, found {TYPE_NAMES.get(t, t)}", "type")
        for a in c.args[len(sig.ptypes):]:
            self.expr(a)


def analyze(prog):
    return Sema(prog).run()
