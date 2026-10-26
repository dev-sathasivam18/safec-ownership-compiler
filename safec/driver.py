"""SafeC command line driver: lex -> parse -> sema -> IR/CFG -> ownership -> C."""
import argparse
import sys
from .lexer import lex
from .parser import parse
from .sema import analyze
from .cfg import build_cfgs
from .ownership import check_ownership
from .codegen import generate
from .diagnostics import CompileError


def compile_source(src, name="<input>", ownership=True):
    """Returns (c_code | None, diagnostics, cfgs, ast)."""
    toks, lex_errs = lex(src)
    if lex_errs:
        return None, lex_errs, [], None
    try:
        prog = parse(toks)
    except CompileError as e:
        return None, [e.diag], [], None
    errs = analyze(prog)
    if not ownership:       # unsafe-baseline mode: keep type/name errors, drop the leak checks
        errs = [e for e in errs if e.kind != "leak"]
    if errs:
        return None, errs, [], prog
    cfgs, cfg_errs = build_cfgs(prog)
    errs = list(cfg_errs)
    if ownership:
        errs += check_ownership(cfgs)
    errs.sort(key=lambda d: (d.line, d.col))
    if errs:
        return None, errs, cfgs, prog
    return generate(prog, name), [], cfgs, prog


def main(argv=None):
    ap = argparse.ArgumentParser(prog="safec", description="SafeC memory-safety compiler")
    ap.add_argument("file")
    ap.add_argument("-o", "--output", help="write generated C here (default: stdout)")
    ap.add_argument("--emit-cfg", action="store_true", help="print the control-flow graph and exit")
    ap.add_argument("--no-ownership", action="store_true",
                    help="skip the ownership check (used only to build unsafe baselines for evaluation)")
    a = ap.parse_args(argv)
    src = open(a.file).read()
    c, diags, cfgs, _ = compile_source(src, a.file, ownership=not a.no_ownership)
    if a.emit_cfg:
        for g in cfgs:
            print(g.dump())
            print()
    for d in diags:
        print(d.render(a.file), file=sys.stderr)
    if diags:
        n = len(diags)
        print(f"{n} error{'s' if n != 1 else ''}; no C code generated.", file=sys.stderr)
        return 1
    if a.emit_cfg:
        return 0
    if a.output:
        open(a.output, "w").write(c + "\n")
    else:
        print(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
