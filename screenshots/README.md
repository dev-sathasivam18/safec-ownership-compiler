# SafeC demo screenshots for PowerPoint

All screenshots are PNG captures of the running local browser demo at 3200 × 2000 pixels. Suggested slide order:

1. `01-demo-overview.png` — landing page and complex source program.
2. `02-safe-program-accepted.png` — ownership checks pass and C is generated.
3. `03-unsafe-program-diagnostic.png` — path-sensitive use-after-free and possible double-free diagnostics.
4. `04-control-flow-graph.png` — generated control-flow graph alongside the accepted result.
5. `05-walkthrough-source.png` — guided tour start, source program.
6. `06-lexer-tokens.png` — character stream converted to tokens.
7. `07-parser-ast.png` — parsed functions, branches, loops, and calls in AST form.
8. `08-semantic-symbols.png` — resolved function signatures and symbol IDs.
9. `09-control-flow-stage.png` — basic blocks and control-flow edges.
10. `10-ownership-fixed-point.png` — converged ownership facts for reachable blocks.
11. `11-generated-c.png` — verified SafeC program translated to C.

The walkthrough screenshots use the same `review_complex_safe.sc` example. The unsafe diagnostic screenshot uses `review_branch_error.sc`.
