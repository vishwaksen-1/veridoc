# veridoc & verilint skill

Use this skill whenever you add, modify, or are asked to document a Verilog/SystemVerilog RTL file.
Also use it when asked to lint a file or check for Verilator warnings.

---

## Tools

Both tools live in the project venv. Always activate it first:

```bash
source .venv/bin/activate
```

- **`veridoc`** — generates and updates Markdown docs from RTL source
- **`verilint`** — runs Verilator lint and tags warnings inline in source files

---

## Critical: always pass `-o docs/modules`

The default output directory is `temp/docs/modules`. The project docs live in `docs/modules`.
**Every veridoc invocation must include `-o docs/modules`** or docs land in the wrong place.

---

## When to run veridoc

| Situation | Command |
|-----------|---------|
| Single file added or modified | `veridoc -f rtl/path/to/file.v -o docs/modules` |
| Multiple files modified | `veridoc -f rtl/a.v rtl/b.v -o docs/modules` |
| Full rescan (e.g. after a refactor that touches many files) | `veridoc -d rtl/ -o docs/modules` |
| Also regenerate the dependency graph | add `--json-graph` → writes `docs/modules/graph.json` |
| Preview without writing anything | add `--dry-run` |
| See which files changed | add `-v` |
| See which sections changed within each file | add `-vv` |

### What veridoc manages (auto-updated from source):
- Parameters, Inputs, Outputs, Inouts, Calls, Called By

### What veridoc never touches:
- The `## Description` section — preserved as-is once written; defaults to `TODO: Add description` on first generation
- Any extra sections you add manually (e.g. `## State Machine`, `## Notes`) — left alone

### After generating a new module doc:
Open the generated `docs/modules/<module>.md` and fill in the `## Description` section. veridoc will never overwrite it.

---

## When to run verilint

Run verilint on any RTL file you have just edited or created, before updating its doc.

```bash
# See issues without modifying the file
verilint rtl/path/to/file.v --dry-run

# Tag issues inline (idempotent — re-running updates existing tags)
verilint rtl/path/to/file.v

# If the file uses `include with headers in another dir
verilint rtl/path/to/file.v -I rtl/include/
```

### What verilint does to the source file:
1. Inserts `// lint-test: verilator --lint-only -Wall <file>` header (once, idempotent)
2. Inserts `// tb-test: tba` header placeholder (once, idempotent)
3. Appends `/* Check: <message> */` at the end of any warned line
4. Re-running replaces existing `/* Check: */` tags — does not stack them

### What to do with Check tags:
- Fix the underlying issue in the RTL
- Re-run verilint to confirm the tag disappears (exit 0 = clean)
- Do not remove tags manually unless you are deliberately suppressing a known false positive

---

## Standard workflow (modify an existing RTL file)

```bash
source .venv/bin/activate

# 1. Lint the file — fix any Check-tagged lines
verilint rtl/path/to/module.v
# fix issues in source, then re-run until exit 0

# 2. Regenerate the doc
veridoc -f rtl/path/to/module.v -o docs/modules -vv
```

## Standard workflow (add a new RTL file)

```bash
source .venv/bin/activate

# 1. Lint the new file
verilint rtl/path/to/new_module.v

# 2. Generate its doc (also rebuild graph so new module appears)
veridoc -f rtl/path/to/new_module.v -o docs/modules --json-graph -vv

# 3. Open the generated doc and write the Description section
# docs/modules/new_module.md  →  replace "TODO: Add description" with real text
```

---

## CI check (do not run routinely — only when asked)

```bash
veridoc -d rtl/ -o docs/modules --ci --print-errors
```

Exits 1 if any module has: missing description, no IO, or self-instantiation.

---

## Known limitations (do not work around — just be aware)

- Pre-2001 Verilog port style (`input clk;` inside body) is not parsed
- Only the first `module` block in a file is parsed
- SV-specific constructs (interfaces, packages, typedefs) are not extracted
- `include` / macro expansion is not supported — macro-prefixed port names may partially parse
