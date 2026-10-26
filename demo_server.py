#!/usr/bin/env python3
"""Local browser demo for SafeC. Uses only Python's standard library."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import sys
from dataclasses import fields, is_dataclass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from safec.driver import compile_source  # noqa: E402
from safec.lexer import lex  # noqa: E402
from safec.parser import parse  # noqa: E402
from safec.diagnostics import CompileError  # noqa: E402
from safec.sema import analyze  # noqa: E402
from safec.cfg import build_cfgs  # noqa: E402
from safec.ownership import Analyzer  # noqa: E402
from safec.codegen import generate  # noqa: E402
from safec.nodes import *  # noqa: E402,F403


def examples():
    result = []
    for category in ("safe", "unsafe"):
        for path in sorted((ROOT / "tests" / category).glob("*.sc")):
            result.append({"id": f"{category}/{path.name}", "category": category,
                           "name": path.stem, "source": path.read_text()})
    for path in sorted((ROOT / "examples").glob("*.sc")):
        category = "safe" if "safe" in path.name else "unsafe"
        result.append({"id": f"review/{path.name}", "category": category,
                       "name": path.stem, "source": path.read_text()})
    return result


EXAMPLES = {item["id"]: item for item in examples()}


def expr_text(node):
    if isinstance(node, Num): return str(node.value)
    if isinstance(node, Var): return node.name
    if isinstance(node, Deref): return f"*{node.target.name}"
    if isinstance(node, Unary): return f"{node.op}{expr_text(node.operand)}"
    if isinstance(node, Binary): return f"({expr_text(node.left)} {node.op} {expr_text(node.right)})"
    if isinstance(node, Alloc): return f"alloc({expr_text(node.size)})"
    if isinstance(node, Call): return f"{node.name}({', '.join(expr_text(a) for a in node.args)})"
    return "?"


def ast_dump(prog):
    lines = []
    def stmt(node, depth):
        p = "  " * depth
        if isinstance(node, Block):
            for child in node.stmts: stmt(child, depth)
        elif isinstance(node, Decl):
            init = f" = {expr_text(node.init)}" if node.init else ""
            lines.append(f"{p}Declare {node.vty} {node.name}{init}  [line {node.line}]")
        elif isinstance(node, Assign): lines.append(f"{p}Assign {node.name} = {expr_text(node.value)}  [line {node.line}]")
        elif isinstance(node, Store): lines.append(f"{p}Write through *{node.target.name} = {expr_text(node.value)}  [line {node.line}]")
        elif isinstance(node, Free): lines.append(f"{p}Release {node.target.name}  [line {node.line}]")
        elif isinstance(node, ExprStmt): lines.append(f"{p}Evaluate {expr_text(node.expr)}  [line {node.line}]")
        elif isinstance(node, Return): lines.append(f"{p}Return {expr_text(node.value) if node.value else 'void'}  [line {node.line}]")
        elif isinstance(node, If):
            lines.append(f"{p}Branch if {expr_text(node.cond)}  [line {node.line}]")
            stmt(node.then, depth + 1)
            if node.els:
                lines.append(f"{p}else"); stmt(node.els, depth + 1)
        elif isinstance(node, While):
            lines.append(f"{p}Loop while {expr_text(node.cond)}  [line {node.line}]"); stmt(node.body, depth + 1)
    for fn in prog.funcs:
        params = ", ".join(f"{p.pty} {p.name}" for p in fn.params)
        lines.append(f"Function {fn.name}({params}) -> {fn.ret}  [line {fn.line}]")
        stmt(fn.body, 1)
    return "\n".join(lines)


def walk_source(source, label):
    source_lines = source.splitlines()
    tokens, lex_errors = lex(source)
    token_lines = {}
    for tok in tokens:
        if tok.kind != "eof": token_lines.setdefault(tok.line, []).append(tok.text)
    steps = [{"title": "Lexical analysis", "why": "The lexer groups characters into tokens such as keywords, names, numbers, and operators. This gives later stages meaningful pieces instead of raw characters.",
              "diagram": "Characters  →  Tokens", "output": "\n".join(f"{n:>3}: {'  '.join(ts)}" for n, ts in sorted(token_lines.items())),
              "lines": sorted(token_lines)}]
    if lex_errors:
        msg = "\n".join(d.render(label) for d in lex_errors)
        steps.append({"title": "Lexing stopped", "why": "Invalid characters prevent the compiler from forming a complete token stream.", "diagram": "Lexer  ✕  invalid token", "output": msg, "lines": [d.line for d in lex_errors]})
        return steps, None, lex_errors
    try:
        prog = parse(tokens)
    except CompileError as exc:
        d = exc.diag
        steps.append({"title": "Parsing stopped", "why": "The parser checks whether tokens follow SafeC grammar and builds the tree used by later compiler passes.", "diagram": "Tokens  →  Parser  ✕", "output": d.render(label), "lines": [d.line]})
        return steps, None, [d]
    steps.append({"title": "Parsing · AST", "why": "Recursive-descent parsing turns the token stream into a structured abstract syntax tree. Each declaration, branch, loop, and call is now an explicit node.", "diagram": "Tokens  →  AST", "output": ast_dump(prog), "lines": sorted({f.line for f in prog.funcs} | {n.line for f in prog.funcs for n in f.body.stmts})})
    sema_errors = analyze(prog)
    sig_lines = []
    for fn in prog.funcs:
        ps = ", ".join(f"{p.pty} {p.name} [symbol #{p.sym.uid}]" for p in fn.params)
        sig_lines.append(f"function {fn.name}({ps}) -> {fn.ret}")
    def declarations(node):
        out = []
        if isinstance(node, Decl) and node.sym:
            out.append(f"{node.name}: {node.vty} [symbol #{node.sym.uid}, scope line {node.line}]")
        if is_dataclass(node):
            for field in fields(node):
                if field.name in ("sym", "func", "ty", "target"):
                    continue
                value = getattr(node, field.name)
                if is_dataclass(value): out.extend(declarations(value))
                elif isinstance(value, list):
                    for child in value:
                        if is_dataclass(child): out.extend(declarations(child))
        return out
    symbols = sig_lines + declarations(prog)
    sema_out = "Collected function signatures and scoped symbols:\n" + "\n".join(symbols)
    if sema_errors: sema_out += "\n\n" + "\n".join(d.render(label) for d in sema_errors)
    steps.append({"title": "Semantic analysis", "why": "The type and name checker resolves each identifier, assigns symbol IDs, and verifies function arguments, return types, and pointer kinds. Owned and borrowed pointers have different rules.", "diagram": "AST  →  types + symbols", "output": sema_out, "lines": sorted({fn.line for fn in prog.funcs} | {node.line for fn in prog.funcs for node in fn.body.stmts if isinstance(node, Decl)})})
    if sema_errors:
        steps.append({"title": "Compilation stopped", "why": "Later ownership analysis and C generation require a well-typed program.", "diagram": "Type check  ✕", "output": "\n".join(d.render(label) for d in sema_errors), "lines": [d.line for d in sema_errors]})
        return steps, None, sema_errors
    cfgs, cfg_errors = build_cfgs(prog)
    cfg_dump = "\n\n".join(cfg.dump() for cfg in cfgs)
    cfg_lines = sorted({ins.line for cfg in cfgs for block in cfg.blocks for ins in block.instrs})
    steps.append({"title": "CFG construction", "why": "Each function becomes a control-flow graph. Branches split into paths, loops connect back to their headers, and ownership-relevant operations become IR instructions.", "diagram": "AST  →  basic blocks  →  edges", "output": cfg_dump or "No reachable basic blocks.", "lines": cfg_lines})
    if cfg_errors:
        steps.append({"title": "CFG validation", "why": "Control-flow checks catch functions that can fall through without returning a required value.", "diagram": "CFG  ✕  invalid exit", "output": "\n".join(d.render(label) for d in cfg_errors), "lines": [d.line for d in cfg_errors]})
        return steps, None, cfg_errors
    ownership_errors, state_dumps = [], []
    for cfg in cfgs:
        analyzer = Analyzer(cfg)
        ownership_errors.extend(analyzer.run())
        state_dumps.append(analyzer.dump_states())
    own_output = "\n\n".join(state_dumps)
    if ownership_errors:
        own_output += "\n\nDiagnostics:\n" + "\n".join(d.render(label) for d in ownership_errors)
    else:
        own_output += "\n\nNo ownership violations: every live allocation is freed, moved, or returned exactly once."
    steps.append({"title": "Ownership analysis", "why": "A forward data-flow pass reaches a fixed point across branches and loops. It tracks possible Uninit, Owned, Moved, and Freed facts; a use must be valid on every possible path.", "diagram": "CFG  →  state propagation  →  fixed point", "output": own_output, "lines": sorted({d.line for d in ownership_errors} | {ins.line for cfg in cfgs for block in cfg.blocks for ins in block.instrs})})
    if ownership_errors:
        steps.append({"title": "C generation blocked", "why": "SafeC does not emit C when ownership analysis finds an error, preventing unsafe code from being presented as verified output.", "diagram": "Ownership check  ✕  no C emitted", "output": "\n".join(d.render(label) for d in ownership_errors), "lines": sorted({d.line for d in ownership_errors})})
        return steps, None, ownership_errors
    code = generate(prog, label)
    steps.append({"title": "C code generation", "why": "The verified AST is translated into ordinary C. SafeC's ownership annotations are compile-time rules; the generated program uses malloc/free and standard C calls.", "diagram": "Verified AST  →  C source", "output": code, "lines": list(range(1, len(source_lines) + 1))})
    return steps, code, []


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/examples":
            return self.send_json(list(EXAMPLES.values()))
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        page = (ROOT / "demo.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        if self.path not in ("/api/compile", "/api/walkthrough"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 200_000:
                return self.send_json({"error": "Source is too large (200 KB limit)."}, 413)
            payload = json.loads(self.rfile.read(length))
            source = payload.get("source", "")
            if not isinstance(source, str):
                return self.send_json({"error": "Source must be text."}, 400)
            label = str(payload.get("name", "demo.sc"))[:100]
            if self.path == "/api/walkthrough":
                steps, c_code, diagnostics = walk_source(source, label)
                return self.send_json({"steps": steps, "accepted": not diagnostics,
                                       "c_code": c_code or "",
                                       "diagnostics": [d.render(label) for d in diagnostics]})
            show_cfg = bool(payload.get("show_cfg", False))
            c_code, diagnostics, cfgs, _ = compile_source(source, label)
            return self.send_json({
                "accepted": not diagnostics,
                "diagnostics": [d.render(label) for d in diagnostics],
                "c_code": c_code or "",
                "cfg": "\n\n".join(g.dump() for g in cfgs) if show_cfg else "",
            })
        except (ValueError, json.JSONDecodeError) as exc:
            return self.send_json({"error": f"Invalid request: {exc}"}, 400)

    def log_message(self, fmt, *args):
        print(f"[SafeC demo] {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    host = os.environ.get("SAFEC_DEMO_HOST", "127.0.0.1")
    port = int(os.environ.get("SAFEC_DEMO_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"SafeC demo running at http://{host}:{port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SafeC demo.")
    finally:
        server.server_close()
