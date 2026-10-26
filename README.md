# SafeC: a memory-safety compiler for a small C-like language

Compiler Design, Review 1 project. Written in Python 3 (no dependencies). Implements the pipeline from the proposal:

    Lexer -> Parser -> Semantic analysis -> IR + CFG -> Ownership analysis -> C codegen

## Run

Requires Python 3. No Python packages are needed. `gcc` is needed for the optional C/ASan comparison.

    python3 -m safec prog.sc -o prog.c        # compile (exit 1 + errors if unsafe)
    python3 -m safec prog.sc --emit-cfg       # show basic blocks / ownership IR
    python3 evaluate.py                       # 30-program evaluation -> RESULTS.md (needs gcc)

For a guided project-review walkthrough, see [REVIEW_GUIDE.md](REVIEW_GUIDE.md).

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
