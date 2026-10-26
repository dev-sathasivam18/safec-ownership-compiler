"""Stage 1: Lexer. Source text -> tokens."""
import re
from dataclasses import dataclass
from .diagnostics import Diagnostic

KEYWORDS = {"int", "void", "own", "if", "else", "while", "return"}

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>[ \t\r]+)
  | (?P<nl>\n)
  | (?P<lc>//[^\n]*)
  | (?P<bc>/\*.*?\*/)
  | (?P<num>\d+)
  | (?P<id>[A-Za-z_]\w*)
  | (?P<op><=|>=|==|!=|&&|\|\||[-+*/%<>=!(){};,])
    """,
    re.X | re.S,
)


@dataclass
class Token:
    kind: str      # 'num', 'id', 'kw', 'op', 'eof'
    text: str
    line: int
    col: int


def lex(src):
    toks, errs = [], []
    pos, line, col = 0, 1, 1
    while pos < len(src):
        m = _TOKEN_RE.match(src, pos)
        if not m:
            errs.append(Diagnostic(line, col, f"unexpected character {src[pos]!r}", "lexical"))
            pos += 1
            col += 1
            continue
        kind, text = m.lastgroup, m.group()
        if kind in ("ws", "lc"):
            col += len(text)
        elif kind in ("nl", "bc"):
            nls = text.count("\n")
            if nls:
                line += nls
                col = len(text) - text.rfind("\n")
            else:
                col += len(text)
        else:
            k = "kw" if kind == "id" and text in KEYWORDS else kind
            toks.append(Token(k, text, line, col))
            col += len(text)
        pos = m.end()
    toks.append(Token("eof", "", line, col))
    return toks, errs
