# SafeC evaluation

## Safe programs (15): should be accepted, and the generated C should run clean under ASan (LeakSanitizer disabled for portability)

| program | SafeC | ASan on generated C | gcc -Wall warnings on generated C |
|---|---|---|---|
| s01_basic | accepted | ok | 0 |
| s02_transfer_to_function | accepted | ok | 0 |
| s03_return_ownership | accepted | ok | 0 |
| s04_branch_both_free | accepted | ok | 0 |
| s05_loop_alloc_free | accepted | ok | 0 |
| s06_borrow_param | accepted | ok | 0 |
| s07_move_chain | accepted | ok | 0 |
| s08_realloc_after_free | accepted | ok | 0 |
| s09_nested_scope | accepted | ok | 0 |
| s10_early_return | accepted | ok | 0 |
| s11_ownership_in_loop | accepted | ok | 0 |
| s12_recursion | accepted | ok | 0 |
| s13_two_buffers | accepted | ok | 0 |
| s14_conditional_store | accepted | ok | 0 |
| s15_pipeline | accepted | ok | 0 |

## Buggy programs (15): SafeC should reject; compared with the same code under gcc and ASan (LeakSanitizer disabled)

| program | injected bug | SafeC (compile time) | gcc -Wall | gcc -Wall -O2 | ASan (run time; LSan disabled) |
|---|---|---|---|---|---|
| u01_use_after_free | use-after-free | caught: use-after-free | silent | silent | caught: heap-use-after-free |
| u02_double_free | double-free | caught: double-free | silent | silent | caught: double-free |
| u03_leak | leak | caught: leak | silent | silent | MISSED (clean run) |
| u04_use_after_move | use-after-move | caught: use-after-move | silent | silent | MISSED (clean run) |
| u05_leak_early_return | leak | caught: leak | silent | silent | MISSED (clean run) |
| u06_maybe_freed_use | use-after-free | caught: double-free, use-after-free | warns (1) | warns (1) | MISSED (clean run) |
| u07_double_free_branch | double-free | caught: double-free | warns (1) | warns (1) | MISSED (clean run) |
| u08_overwrite_leak | leak | caught: leak | silent | silent | MISSED (clean run) |
| u09_leak_one_branch | leak | caught: leak | warns (1) | warns (1) | MISSED (clean run) |
| u10_free_after_move | use-after-move | caught: use-after-move | silent | silent | caught: double-free |
| u11_free_in_loop | double-free | caught: double-free, leak | silent | silent | caught: double-free |
| u12_discarded_alloc | leak | caught: leak | silent | silent | MISSED (clean run) |
| u13_callee_leak | leak | caught: leak | silent | silent | MISSED (clean run) |
| u14_use_after_move_call | use-after-move | caught: use-after-move | silent | silent | caught: heap-use-after-free |
| u15_loop_overwrite_leak | leak | caught: leak | silent | silent | MISSED (clean run) |

## Summary

| tool | buggy programs flagged (of 15) | safe programs wrongly flagged (of 15) |
|---|---|---|
| SafeC | 15 (with the expected error class) | 0 |
| gcc -Wall | 3 | 0 |
| gcc -Wall -O2 | 3 | n/a |
| ASan (without LSan) | 5 | 0 |

Generated C for accepted safe programs ran clean under ASan: 15/15.
