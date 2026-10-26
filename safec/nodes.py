"""AST node definitions. Types are the strings 'int', 'void', 'own' (own int*), 'ptr' (borrowed int*)."""
from dataclasses import dataclass, field
from typing import Any, List, Optional

TYPE_NAMES = {"int": "int", "void": "void", "own": "own int*", "ptr": "int*"}


@dataclass
class Node:
    line: int
    col: int


# ---- expressions -------------------------------------------------------
@dataclass
class Num(Node):
    value: int
    ty: Any = None

@dataclass
class Var(Node):
    name: str
    ty: Any = None
    sym: Any = None

@dataclass
class Deref(Node):          # *p  (operand is always a variable)
    target: Var
    ty: Any = None

@dataclass
class Unary(Node):
    op: str
    operand: Any
    ty: Any = None

@dataclass
class Binary(Node):
    op: str
    left: Any
    right: Any
    ty: Any = None

@dataclass
class Alloc(Node):          # alloc(n): n bytes on the heap, result is a fresh owned pointer
    size: Any
    ty: Any = None

@dataclass
class Call(Node):
    name: str
    args: List[Any]
    ty: Any = None
    func: Any = None


# ---- statements --------------------------------------------------------
@dataclass
class Decl(Node):
    vty: str
    name: str
    init: Optional[Any]
    sym: Any = None

@dataclass
class Assign(Node):
    name: str
    value: Any
    sym: Any = None

@dataclass
class Store(Node):          # *p = e;
    target: Var
    value: Any

@dataclass
class Free(Node):
    target: Var

@dataclass
class ExprStmt(Node):
    expr: Any

@dataclass
class If(Node):
    cond: Any
    then: Any
    els: Optional[Any]

@dataclass
class While(Node):
    cond: Any
    body: Any

@dataclass
class Return(Node):
    value: Optional[Any]

@dataclass
class Block(Node):
    stmts: List[Any]
    end_line: int = 0
    end_col: int = 0


# ---- top level ---------------------------------------------------------
@dataclass
class Param:
    pty: str
    name: str
    line: int
    col: int
    sym: Any = None

@dataclass
class Func(Node):
    ret: str
    name: str
    params: List[Param]
    body: Block

@dataclass
class Program:
    funcs: List[Func]
