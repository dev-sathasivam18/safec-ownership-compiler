#!/usr/bin/env python3
"""Evaluate SafeC on tests/safe (15) and tests/unsafe (15) against gcc -Wall and AddressSanitizer.

For unsafe programs the C baseline is produced with `--no-ownership` (same program, no SafeC check),
so gcc and ASan see exactly the code SafeC refused to emit.
"""
import glob, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from safec.driver import compile_source

# LeakSanitizer is not available in every AddressSanitizer runtime (notably some
# macOS toolchains). Keep ASan's use-after-free/double-free checks enabled and
# report leak checking separately instead of treating runtime startup failures
# as evidence that a test program is buggy.
ENV = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV, **kw)


def expected(path):
    return re.search(r"//\s*expect:\s*(\S+)", open(path).read()).group(1)


def gcc_warns(cfile, extra):
    r = sh(["gcc", "-Wall", *extra, "-c", cfile, "-o", os.devnull])
    return [l for l in r.stderr.splitlines() if "warning:" in l and re.search(r"free|freed|leak", l, re.I)]


def asan_result(cfile, tmp):
    exe = os.path.join(tmp, "a.out")
    r = sh(["gcc", "-g", "-O0", "-fsanitize=address", cfile, "-o", exe])
    if r.returncode:
        return "build-failed", r.stderr
    r = sh([exe], timeout=20)
    err = r.stderr
    if "LeakSanitizer" in err and "ERROR: LeakSanitizer" in err:
        return "memory-leak", err
    if "ERROR: AddressSanitizer:" in err:
        m = re.search(r"AddressSanitizer: (?:attempting )?([\w-]+)", err)
        return (m.group(1) if m else "sanitizer-error"), err
    if r.returncode != 0:
        # A crash/abort is not automatically a sanitizer finding. Keep it
        # distinct so the summary cannot claim the tool caught the injected bug.
        return f"runtime-error ({r.returncode})", err
    return ("ok" if r.returncode == 0 else f"exit-{r.returncode}"), err


def main():
    rows, tmp = [], tempfile.mkdtemp()
    safe = sorted(glob.glob(os.path.join(ROOT, "tests/safe/*.sc")))
    unsafe = sorted(glob.glob(os.path.join(ROOT, "tests/unsafe/*.sc")))
    for path in safe + unsafe:
        name, want = os.path.basename(path)[:-3], expected(path)
        src = open(path).read()
        c, diags, _, _ = compile_source(src, path)
        kinds = sorted({d.kind for d in diags})
        row = dict(name=name, want=want, safec="rejected" if diags else "accepted", kinds=kinds)
        if want == "safe":
            if c:
                cf = os.path.join(tmp, name + ".c")
                open(cf, "w").write(c)
                row["asan_on_generated"], _ = asan_result(cf, tmp)
                row["gcc_warn_on_generated"] = len(gcc_warns(cf, []))
        else:
            base, _, _, _ = compile_source(src, path, ownership=False)
            cf = os.path.join(tmp, name + ".c")
            open(cf, "w").write(base)
            row["gcc_Wall"] = len(gcc_warns(cf, []))
            row["gcc_Wall_O2"] = len(gcc_warns(cf, ["-O2"]))
            row["asan"], _ = asan_result(cf, tmp)
        rows.append(row)

    L = []
    L.append("# SafeC evaluation\n")
    L.append("## Safe programs (15): should be accepted, and the generated C should run clean under ASan (LeakSanitizer disabled for portability)\n")
    L.append("| program | SafeC | ASan on generated C | gcc -Wall warnings on generated C |")
    L.append("|---|---|---|---|")
    for r in rows:
        if r["want"] == "safe":
            L.append(f"| {r['name']} | {r['safec']} | {r.get('asan_on_generated','-')} | {r.get('gcc_warn_on_generated','-')} |")
    L.append("\n## Buggy programs (15): SafeC should reject; compared with the same code under gcc and ASan (LeakSanitizer disabled)\n")
    L.append("| program | injected bug | SafeC (compile time) | gcc -Wall | gcc -Wall -O2 | ASan (run time) |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        if r["want"] != "safe":
            hit = r["want"] in r["kinds"]
            sc = ("caught: " + ", ".join(r["kinds"])) if r["safec"] == "rejected" else "MISSED"
            if r["safec"] == "rejected" and not hit:
                sc += f" (expected {r['want']})"
            g = lambda n: f"warns ({n})" if n else "silent"
            a = "caught: " + r["asan"] if r["asan"] in ("heap-use-after-free", "double-free", "use-after-free", "memory-leak") else ("MISSED (clean run)" if r["asan"] == "ok" else "runtime/tool error: " + r["asan"])
            L.append(f"| {r['name']} | {r['want']} | {sc} | {g(r['gcc_Wall'])} | {g(r['gcc_Wall_O2'])} | {a} |")

    s = [r for r in rows if r["want"] == "safe"]
    u = [r for r in rows if r["want"] != "safe"]
    tp = sum(r["safec"] == "rejected" and r["want"] in r["kinds"] for r in u)
    fp = sum(r["safec"] == "rejected" for r in s)
    clean = sum(r.get("asan_on_generated") == "ok" for r in s)
    L.append("\n## Summary\n")
    L.append("| tool | buggy programs flagged (of 15) | safe programs wrongly flagged (of 15) |")
    L.append("|---|---|---|")
    L.append(f"| SafeC | {tp} (with the expected error class) | {fp} |")
    L.append(f"| gcc -Wall | {sum(r['gcc_Wall']>0 for r in u)} | {sum(r.get('gcc_warn_on_generated',0)>0 for r in s)} |")
    L.append(f"| gcc -Wall -O2 | {sum(r['gcc_Wall_O2']>0 for r in u)} | n/a |")
    L.append(f"| ASan (without LSan) | {sum(r['asan'] in ('heap-use-after-free', 'double-free', 'use-after-free') for r in u)} | {sum(r.get('asan_on_generated') not in ('ok', None) for r in s)} |")
    L.append(f"\nGenerated C for accepted safe programs ran clean under ASan: {clean}/{len(s)}.")
    out = "\n".join(L) + "\n"
    open(os.path.join(ROOT, "RESULTS.md"), "w").write(out)
    print(out)


if __name__ == "__main__":
    main()
