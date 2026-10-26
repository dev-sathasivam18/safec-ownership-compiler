# SafeC: a memory-safety compiler for a small C-like language

Compiler Design, Review 1 project. Written in Python 3 (no dependencies). Implements the pipeline from the proposal:

    Lexer -> Parser -> Semantic analysis -> IR + CFG -> Ownership analysis -> C codegen

## Run

Requires Python 3. No Python packages are needed. `gcc` is needed for the optional C/ASan comparison.

    python3 -m safec prog.sc -o prog.c        # compile (exit 1 + errors if unsafe)
    python3 -m safec prog.sc --emit-cfg       # show basic blocks / ownership IR
    python3 evaluate.py                       # 30-program evaluation -> RESULTS.md (needs gcc)

For a guided project-review walkthrough, see [REVIEW_GUIDE.md](REVIEW_GUIDE.md).

## Evaluation results

| Check | Result |
|---|---:|
| Safe examples accepted | 15/15 |
| Unsafe examples rejected with the expected error class | 15/15 |
| Safe examples incorrectly rejected | 0/15 |
| Generated C for safe examples ran clean under AddressSanitizer | 15/15 |
| Buggy examples caught by `gcc -Wall` | 3/15 |
| Buggy examples caught by AddressSanitizer | 5/15 |

The test programs are a teaching/demo suite, not a general precision guarantee.
LeakSanitizer is disabled because it is unsupported by some runtimes; SafeC's
compile-time leak checks remain part of its 15/15 unsafe-case result. See the
[full per-program evaluation](RESULTS.md) for details.

## Screenshots

The screenshots below come from the live browser demo. Open the
[complete screenshot gallery](screenshots/README.md) for the slide order and
image descriptions.

![SafeC demo overview](screenshots/01-demo-overview.png)

<details>
<summary>View all 11 browser demo screenshots</summary>

### Accepted program and generated C

![Safe program accepted](screenshots/02-safe-program-accepted.png)

### Rejected program and ownership diagnostics

![Unsafe program diagnostic](screenshots/03-unsafe-program-diagnostic.png)

### Control-flow graph

![Control-flow graph](screenshots/04-control-flow-graph.png)

### Guided walkthrough: source program

![Walkthrough source program](screenshots/05-walkthrough-source.png)

### Guided walkthrough: lexical analysis

![Walkthrough lexical analysis](screenshots/06-lexer-tokens.png)

### Guided walkthrough: parsing and AST

![Walkthrough AST](screenshots/07-parser-ast.png)

### Guided walkthrough: semantic symbols

![Walkthrough semantic symbols](screenshots/08-semantic-symbols.png)

### Guided walkthrough: control-flow graph

![Walkthrough control-flow graph](screenshots/09-control-flow-stage.png)

### Guided walkthrough: ownership fixed point

![Walkthrough ownership facts](screenshots/10-ownership-fixed-point.png)

### Guided walkthrough: generated C

![Walkthrough generated C](screenshots/11-generated-c.png)

</details>

## Browser demo

Start the local UI with `python3 demo_server.py`, then open <http://127.0.0.1:8000>.
Choose any bundled safe or unsafe example, edit the source, and select **Compile**.
Safe programs show generated C; rejected programs show source diagnostics. Enable
**Show CFG** to display the generated control-flow graph. Stop the server with
Ctrl+C. The demo uses only Python's standard library and binds to localhost.

For the animated, stage-by-stage view, use **Start step-by-step**. **Next** and
**Previous** move through the source, tokens, AST, semantic symbols, CFG,
converged ownership facts, and generated C. Each stage includes an explanation,
a pipeline diagram, and highlighted source lines. The examples
`review_complex_safe.sc` and `review_branch_error.sc` are longer walkthroughs.

## Language

    own int* p = alloc(4);     // alloc(n): n bytes, result is an owned pointer
    *p = 10;  print(*p);       // deref read/write, built-in print(int)
    free(p);                   // releases; p is Freed
    own int* q = p;            // move: p becomes invalid
    void eat(own int* x) {..}  // own parameter: caller gives ownership away, callee must free/move it
    void look(int* x) {..}     // borrowed parameter: read/write only, cannot free or move
    own int* make() {..}       // returns ownership
    if / else / while / return / blocks, int arithmetic and comparisons

Rules enforced at compile time: one owner per allocation, move on transfer, free exactly once, no leak at scope exit/return/overwrite.

## Ownership analysis

Forward data-flow over the CFG. Each owned variable maps to a set of facts {Uninit, Owned, Moved(line), Freed(line)};
join at merges is set union (Owned + Freed = MaybeFreed). Fixpoint first, errors reported once on the final states.

## Known limits (be upfront about these in the review)

- Path-insensitive: conditions are never evaluated, so `if (x) free(p); if (x) *p=1;` is rejected although it is safe.
  Bugs on paths that never run in a given execution are still reported (that is the point, but it also means false positives are possible).
- Only `int` and one level of pointer (`int*`). No arrays/bounds checks, no structs, no pointer aliasing (borrows exist only as parameters).
- Temporal memory safety only (use-after-free, double free, leaks). Spatial errors (buffer overflow) are not covered.
- Parser stops at the first syntax error. `break`/`continue`/`for` are not implemented.
- The 30 test programs were written by the authors; results show the implementation matches its own spec, not general real-world precision.
- The evaluator disables LeakSanitizer for portability because some ASan runtimes do not support it. SafeC's static leak checks are evaluated separately; runtime results cover AddressSanitizer-detectable memory errors.
