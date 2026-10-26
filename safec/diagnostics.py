from dataclasses import dataclass, field


@dataclass
class Diagnostic:
    line: int
    col: int
    msg: str
    kind: str = "error"          # error category, e.g. use-after-free, double-free, leak
    notes: list = field(default_factory=list)

    def render(self, filename):
        out = [f"{filename}:{self.line}:{self.col}: error: {self.msg}"]
        out += [f"    note: {n}" for n in self.notes]
        return "\n".join(out)


class CompileError(Exception):
    """Raised for the first syntax error (the parser does not recover)."""

    def __init__(self, diag):
        super().__init__(diag.msg)
        self.diag = diag
