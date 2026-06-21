# veridoc

CI-native documentation layer for RTL projects.

Parses Verilog/SystemVerilog source files, extracts module structure, and generates Markdown documentation that stays in sync with your RTL — automatically.

---

## Tools

| Command | Purpose |
|---------|---------|
| `veridoc` | Generate and maintain module documentation |
| `verilint` | Run verilator lint and tag warnings inline in source |

---

## Installation

```bash
pip install veridoc
```

Or from source:

```bash
git clone https://github.com/vishwaksen-1/veridoc
cd veridoc
pip install -e .
```

**Requirements**

- Python 3.7+
- `verilint` requires [verilator](https://verilator.org) — a system binary, not installable via pip:

```bash
# Debian / Ubuntu
sudo apt install verilator

# macOS
brew install verilator
```

`veridoc` has no external dependencies. If verilator is missing, `verilint` will exit with a clear error and install instructions.

---

## veridoc

### Quick start

```bash
# Document all modules in a directory
veridoc -d rtl/

# Document specific files
veridoc -f rtl/core/alu.v rtl/core/decoder.v

# Custom output directory
veridoc -d rtl/ -o docs/modules/
```

### What gets generated

For each module, a Markdown file is created or updated:

```markdown
# alu

## Description
TODO: Add description

## Parameters
- DATA_WIDTH = 8
- OP_WIDTH = 4

## Inputs
- clk
- rst
- op
- operand_a
- operand_b

## Outputs
- result
- overflow

## Calls
- [mux4](mux4.md)

## Called By
- [cpu_core](cpu_core.md)
```

The `Description` section is **never overwritten** — you write it once, veridoc preserves it on every run. All other sections are auto-managed.

### CLI reference

```
veridoc (-d DIR [DIR...] | -f FILE [FILE...]) [options]

Input:
  -d, --dir DIR [DIR...]    Recursively scan directories for .v / .sv files
  -f, --file FILE [FILE...]  Parse specific files (no directory traversal)

Output:
  -o, --out OUT_DIR          Output directory (default: temp/docs/modules)
  --json-graph               Write dependency graph to graph.json

Filtering:
  --exclude PATTERN [...]    Exclude paths containing any of these strings

Run modes:
  --dry-run                  Show what would be written without touching files
  --ci                       Fail (exit 1) on missing descriptions, no-IO modules,
                             or self-instantiations
  --print-errors             Print CI issues to stdout (in addition to the error log)

Verbosity:
  -v                         Print modified file paths
  -vv                        Print modified files + section-level diffs (+adds/-removals)
```

### CI integration

```yaml
# .github/workflows/docs.yml
- name: Check RTL docs
  run: veridoc -d rtl/ -o docs/modules/ --ci --print-errors
```

Exit codes: `0` = clean, `1` = CI check failed.

Testbench files (`_tb.v`, `_tb.sv`, `_bench.v`, `_testbench.v`, and `.sv` variants) are automatically excluded from scanning.

### Dry run

Preview what would change before committing:

```bash
veridoc -d rtl/ --dry-run
```

```
[DRY RUN] Would write:
  docs/modules/alu.md
  docs/modules/decoder.md

5 module(s) processed — 2 doc(s) would be written, 3 unchanged
```

### Dependency graph

```bash
veridoc -d rtl/ --json-graph -o docs/modules/
```

Writes `docs/modules/graph.json`:

```json
{
  "cpu_core": {
    "calls": ["alu", "decoder", "register_file"],
    "called_by": []
  },
  "alu": {
    "calls": ["mux4"],
    "called_by": ["cpu_core"]
  }
}
```

---

## verilint

Runs `verilator --lint-only -Wall` on a file and tags each warned line with an inline comment. Useful for tracking lint debt without blocking a build.

### Usage

```bash
verilint rtl/core/alu.v

# With include directories
verilint -I rtl/includes -I rtl/common rtl/core/alu.v

# Multiple files
verilint rtl/core/*.v

# Preview without modifying files
verilint --dry-run rtl/core/alu.v
```

### What gets written

Given a verilator warning on line 75:

```
%Warning-WIDTHEXPAND: rtl/alu.v:75:12: Operator ADD generates 9 bits ...
```

verilint modifies `alu.v` in place:

```verilog
// lint-test: verilator --lint-only -Wall rtl/alu.v
// tb-test: tba
...
assign result = a + b;  /* Check: Operator ADD generates 9 bits ... */
```

Re-running verilint replaces existing `/* Check: */` tags — it does not stack duplicates.

### CLI reference

```
verilint FILE [FILE...] [options]

  -I, --include DIR    Add include directory (repeatable)
  --dry-run            Show issues without modifying files
  -v                   Print full verilator output
```

Exit codes: `0` = no issues found, `1` = one or more warnings/errors.

---

## Design principles

- **No heavy dependencies** — stdlib only, no parser frameworks
- **CI-first** — every flag is designed for scripted use
- **Safe for teams** — manual descriptions are never overwritten
- **Diff-aware** — files are only touched when content actually changes

---

## Supported syntax

| Feature | Status |
|---------|--------|
| Verilog-2001 (`.v`) | Supported |
| SystemVerilog (`.sv`) | Supported (port/param parsing) |
| ANSI port declarations | Supported |
| Comma-inherited port direction (`output reg a, b`) | Supported |
| Parameterised modules (`#(parameter ...)`) | Supported |
| Module instantiations with `#()` param override | Supported |
| Testbench auto-exclusion | Supported |
| Pre-2001 Verilog style | Not supported |
| Multi-module files | Not supported (first module only) |
