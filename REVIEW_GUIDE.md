# SafeC project review guide

## One-minute overview

SafeC is a small compiler for a C-like language. It adds explicit ownership to
heap pointers and rejects common temporal memory errors before emitting C.
The implementation is dependency-free Python and follows this pipeline:

```text
source -> lexer -> parser -> semantic checks -> CFG -> ownership analysis -> C
```

The ownership pass propagates possible states through a control-flow graph:
uninitialized, owned, moved, or freed. At branch joins it combines the possible
states, which lets it catch cases where a pointer is only freed on one path.

## Live demo (about five minutes)

### Browser presentation (recommended)

Start the app in a terminal:

```sh
python3 demo_server.py
```

Open <http://127.0.0.1:8000>. Select `s02_transfer_to_function` and click
**Compile** to show accepted code and the generated C. Then select
`u01_use_after_free` and compile it to show the diagnostic. Turn on **Show CFG**
to expose the control-flow graph. The source editor is editable, so you can also
make a small change and compile again. Stop the local server with Ctrl+C.

For the full explanation, select `review_complex_safe` and click
**Start step-by-step**. Use **Next** to walk from source through tokenization,
AST construction, symbol/type checks, CFG building, ownership fixed-point
analysis, and C generation. Each step highlights its source lines and shows the
actual intermediate representation. **Previous** returns to the preceding
stage. `review_branch_error` demonstrates the same progression ending with
ownership diagnostics and blocked C generation.

### Terminal walkthrough

Run these commands from this directory:

```sh
# 1. Compile a valid ownership transfer and run the generated C.
python3 -m safec tests/safe/s02_transfer_to_function.sc -o /tmp/safec_demo.c
gcc -Wall /tmp/safec_demo.c -o /tmp/safec_demo
/tmp/safec_demo

# 2. Inspect the control-flow / ownership IR.
python3 -m safec tests/safe/s04_branch_both_free.sc --emit-cfg

# 3. Show a use-after-free rejected before C is generated.
python3 -m safec tests/unsafe/u01_use_after_free.sc -o /tmp/should_not_exist.c

# 4. Run the 30-case comparison (requires gcc and AddressSanitizer support).
python3 evaluate.py
```

The unsafe compile command exits with status 1 and prints a source location and
diagnostic. That is the expected result for step 3. `RESULTS.md` is regenerated
by step 4.

## Suggested explanation

1. **Problem:** C lets aliases outlive allocations; use-after-free, double-free,
   and leaks may only appear at runtime.
2. **Language rule:** `own int*` has a single owner. Assigning it to another
   owning variable moves the allocation. `free` consumes the owner. Plain `int*`
   function parameters borrow and cannot consume ownership.
3. **Analysis:** each function becomes a CFG. A forward data-flow fixed point
   tracks ownership facts; joins retain all possible facts. Diagnostics are
   emitted after convergence so loops are handled without repeatedly reporting
   the same issue.
4. **Output:** only programs that pass parsing, semantic checks, and ownership
   analysis reach C code generation.
5. **Evidence:** the bundled examples cover 15 intended-safe and 15 intentionally
   unsafe programs. This is a demonstration suite, not a general-purpose C
   safety guarantee.

## Scope and limitations

- The analysis is path-insensitive, so it can reject code that is safe only
  because two branch conditions happen to match.
- The language has `int` and one-level `int*` only. It does not model arrays,
  pointer aliasing, structs, or bounds safety.
- The evaluator disables LeakSanitizer because support varies by platform.
  SafeC's static leak diagnostics are still included in the evaluation.
- Generated C should be reviewed as compiler output; SafeC is a teaching
  prototype and does not claim production-grade safety.
