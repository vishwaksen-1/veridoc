# AGENTS.md — veridoc

Machine-readable reference for AI agents and agentic workflows.

## What this is

Two CLI tools for Verilog/SystemVerilog RTL projects:

- `veridoc` — generates per-module Markdown docs from source. Extracts ports, parameters, and instantiation graph. Diff-aware: only rewrites changed files. Safe to run on every commit.
- `verilint` — runs verilator lint on a file and tags each warned line inline with `/* Check: message */`. Idempotent. Does not block builds.

Primary agentic value: index an unfamiliar RTL codebase without reading every file. Use docs and the JSON graph to navigate module hierarchy, understand interfaces, and locate problems — at a fraction of the token cost of reading raw Verilog.

## Install

```
pip install veridoc
```

No Python runtime dependencies. Requires Python 3.7+. `verilint` requires verilator (system binary — `apt install verilator` / `brew install verilator`). If verilator is absent, `verilint` exits 1 with install instructions; `veridoc` is unaffected.

## veridoc

### Syntax

```
veridoc (-d DIR [DIR...] | -f FILE [FILE...]) [-o OUT_DIR] [flags]
```

### Flags

| Flag | Effect |
|------|--------|
| `-d DIR` | Scan directory recursively for .v / .sv |
| `-f FILE` | Parse specific files |
| `-o OUT_DIR` | Output directory (default: temp/docs/modules) |
| `--dry-run` | Show what would change, write nothing |
| `--ci` | Exit 1 if missing descriptions, no-IO modules, or self-instantiation |
| `--print-errors` | Print CI failures to stdout |
| `--json-graph` | Write dependency graph to OUT_DIR/graph.json |
| `--exclude STR` | Skip paths containing STR |
| `-v` / `-vv` | Verbose: file list / file list + section diffs |

### Outputs

**Per-module Markdown** at `OUT_DIR/<module_name>.md`

Sections always present: Description, Parameters, Inputs, Outputs, Inouts, Calls, Called By.

`Description` is user-managed — never overwritten. All other sections are auto-generated.

**graph.json** (with `--json-graph`):

```json
{
  "module_name": {
    "calls": ["child_module_a", "child_module_b"],
    "called_by": ["parent_module"]
  }
}
```

**stdout summary** (always):

```
N module(s) processed — M doc(s) written, K unchanged
```

**Log file** (when docs are modified): path printed to stdout. Contains modified file list and section diffs.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | CI checks failed (only with `--ci`) |

### Agentic patterns

Understand a codebase without reading source:
```
veridoc -d rtl/ -o .agent/docs/ --json-graph
```
Then read `.agent/docs/<module>.md` for any module and `graph.json` for the full dependency map.

Check if docs are in sync before editing:
```
veridoc -d rtl/ -o docs/ --dry-run
```
Zero "would be written" = docs are current.

Enforce documentation completeness in CI:
```
veridoc -d rtl/ -o docs/ --ci --print-errors
```

Preview impact of a source change:
```
veridoc -f rtl/changed_module.v -o docs/ --dry-run -vv
```
Shows exactly which sections would change.

## verilint

### Syntax

```
verilint FILE [FILE...] [-I DIR] [--dry-run] [-v]
```

### Flags

| Flag | Effect |
|------|--------|
| `-I DIR` | Include directory for verilator (repeatable) |
| `--dry-run` | Show issues per line, write nothing |
| `-v` | Print full verilator output |

### Output

Modifies source file in-place:
- Appends `/* Check: message */` to each warned line
- Inserts `// lint-test: <command>` and `// tb-test: tba` after the leading comment block
- Re-running replaces existing `/* Check: */` tags — does not stack

`--dry-run` stdout:
```
rtl/module.v: 3 issue(s) would be tagged:
  Line 42: Operator EQ expects 32 bits on the LHS ...
  Line 87: Signal is not used: 'temp_wire'
  Line 103: ...
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | One or more warnings/errors found |

### Agentic patterns

Find all lint issues in a file without reading it:
```
verilint --dry-run rtl/module.v
```
Returns line numbers and messages. Agent can jump directly to flagged lines.

Tag and surface lint debt for code review:
```
verilint rtl/module.v
```
`/* Check: */` comments are then searchable with grep or any code search tool.

## Key behaviors for agents

- **Testbench files are auto-excluded**: `_tb.v`, `_tb.sv`, `_bench.v`, `_testbench.v` and `.sv` variants
- **Idempotent**: running either tool twice on unchanged input produces no changes
- **Diff-aware writes**: veridoc never writes a file unless content changed — safe to run unconditionally
- **Structured JSON output**: `--json-graph` produces machine-parseable dependency data
- **First run on a legacy codebase**: use `--dry-run` first to preview scope, then run without it

## Limitations agents should know

- One module parsed per file (first `module` block only)
- Pre-2001 Verilog port style not supported
- SystemVerilog interfaces, packages, and typedefs not extracted
- verilint line-number tagging may be imprecise inside macro expansions (guarded, not fatal)
