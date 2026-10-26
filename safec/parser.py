"""Stage 2: Parser. Tokens -> AST (recursive descent, stops at the first syntax error)."""
from .diagnostics import Diagnostic, CompileError
from .nodes import *


class Parser:
    def __init__(self, toks):
        self.toks, self.i = toks, 0

    # -- helpers
    @property
    def t(self):
        return self.toks[self.i]

    def err(self, msg, tok=None):
        tok = tok or self.t
        raise CompileError(Diagnostic(tok.line, tok.col, msg, "syntax"))

    def at(self, text):
        return self.t.kind in ("op", "kw") and self.t.text == text

    def accept(self, text):
        if self.at(text):
            tok = self.t
            self.i += 1
            return tok
        return None

    def expect(self, text):
        tok = self.accept(text)
        if not tok:
            found = self.t.text or "end of file"
            self.err(f"expected '{text}', found '{found}'")
        return tok

    def ident(self):
        if self.t.kind != "id":
            self.err(f"expected identifier, found '{self.t.text or 'end of file'}'")
        tok = self.t
        self.i += 1
        return tok

    # -- top level
    def program(self):
        funcs = []
        while self.t.kind != "eof":
            funcs.append(self.func())
        return Program(funcs)

    def type_(self):
        if self.accept("own"):
            self.expect("int")
            self.expect("*")
            return "own"
        if self.accept("void"):
            return "void"
        self.expect("int")
        return "ptr" if self.accept("*") else "int"

    def func(self):
        start = self.t
        ret = self.type_()
        if ret == "ptr":
            self.err("a function cannot return a borrowed pointer; use 'own int*'", start)
        name = self.ident()
        self.expect("(")
        params = []
        if not self.at(")"):
            while True:
                pt = self.t
                ty = self.type_()
                if ty == "void":
                    self.err("parameter cannot have type void", pt)
                pn = self.ident()
                params.append(Param(ty, pn.text, pn.line, pn.col))
                if not self.accept(","):
                    break
        self.expect(")")
        body = self.block()
        return Func(name.line, name.col, ret, name.text, params, body)

    # -- statements
    def block(self):
        lb = self.expect("{")
        stmts = []
        while not self.at("}"):
            if self.t.kind == "eof":
                self.err("unexpected end of file, missing '}'")
            stmts.append(self.stmt())
        rb = self.expect("}")
        return Block(lb.line, lb.col, stmts, rb.line, rb.col)

    def stmt(self):
        t = self.t
        if self.at("{"):
            return self.block()
        if self.at("own") or self.at("int") or self.at("void"):
            vty = self.type_()
            if vty == "void":
                self.err("variable cannot have type void", t)
            name = self.ident()
            init = None
            if self.accept("="):
                init = self.expr()
            self.expect(";")
            return Decl(name.line, name.col, vty, name.text, init)
        if self.accept("if"):
            self.expect("(")
            c = self.expr()
            self.expect(")")
            th = self.stmt()
            el = self.stmt() if self.accept("else") else None
            return If(t.line, t.col, c, th, el)
        if self.accept("while"):
            self.expect("(")
            c = self.expr()
            self.expect(")")
            return While(t.line, t.col, c, self.stmt())
        if self.accept("return"):
            v = None if self.at(";") else self.expr()
            self.expect(";")
            return Return(t.line, t.col, v)
        if self.at("*"):
            self.i += 1
            name = self.ident()
            self.expect("=")
            v = self.expr()
            self.expect(";")
            return Store(t.line, t.col, Var(name.line, name.col, name.text), v)
        if t.kind == "id":
            nxt = self.toks[self.i + 1]
            if nxt.text == "=" and nxt.kind == "op":
                self.i += 2
                v = self.expr()
                self.expect(";")
                return Assign(t.line, t.col, t.text, v)
            if t.text == "free" and nxt.text == "(":
                self.i += 2
                name = self.ident()
                self.expect(")")
                self.expect(";")
                return Free(t.line, t.col, Var(name.line, name.col, name.text))
        e = self.expr()
        self.expect(";")
        return ExprStmt(t.line, t.col, e)

    # -- expressions (precedence climbing by levels)
    def _binary(self, sub, ops):
        left = sub()
        while self.t.kind == "op" and self.t.text in ops:
            op = self.t
            self.i += 1
            left = Binary(op.line, op.col, op.text, left, sub())
        return left

    def expr(self):
        return self._binary(self.and_, {"||"})

    def and_(self):
        return self._binary(self.eq, {"&&"})

    def eq(self):
        return self._binary(self.rel, {"==", "!="})

    def rel(self):
        return self._binary(self.add, {"<", ">", "<=", ">="})

    def add(self):
        return self._binary(self.mul, {"+", "-"})

    def mul(self):
        return self._binary(self.unary, {"*", "/", "%"})

    def unary(self):
        t = self.t
        if self.accept("-") or self.accept("!"):
            return Unary(t.line, t.col, t.text, self.unary())
        if self.accept("*"):
            name = self.ident()
            return Deref(t.line, t.col, Var(name.line, name.col, name.text))
        return self.primary()

    def primary(self):
        t = self.t
        if t.kind == "num":
            self.i += 1
            return Num(t.line, t.col, int(t.text))
        if t.kind == "id":
            self.i += 1
            if self.accept("("):
                args = []
                if not self.at(")"):
                    while True:
                        args.append(self.expr())
                        if not self.accept(","):
                            break
                self.expect(")")
                if t.text == "alloc":
                    if len(args) != 1:
                        self.err("alloc takes exactly one argument (size in bytes)", t)
                    return Alloc(t.line, t.col, args[0])
                return Call(t.line, t.col, t.text, args)
            return Var(t.line, t.col, t.text)
        if self.accept("("):
            e = self.expr()
            self.expect(")")
            return e
        self.err(f"expected expression, found '{t.text or 'end of file'}'")


def parse(tokens):
    return Parser(tokens).program()
