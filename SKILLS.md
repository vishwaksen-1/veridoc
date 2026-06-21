# Skills Reference

Detailed capability map for both veridoc tools. Useful when evaluating what is already handled, what has known limitations, and what is explicitly out of scope.

---

## veridoc

### Parsing

| Capability | Notes |
|-----------|-------|
| Strip `//` and `/* */` comments before parsing | Prevents comment content from poisoning regex matches |
| Match `module name #(...) (...);` | ANSI-2001 style |
| Match `module name (...);` | Port-list style without parameter block |
| Extract parameters from `#(parameter ...)` block | Type qualifiers (`integer`, `logic`, etc.) stripped; stores `NAME = default` |
| Extract `input` / `output` / `inout` ports | Direction keyword required on at least the first port in a group |
| Comma-inherited port direction | `output reg a, b, c` — all three captured as outputs |
| Strip macro prefixes on port declarations | `` `MACRO_NAME port_name `` → bare name extracted |
| Detect module instantiations | Pattern: `mod_name [#(...)] instance_name (` where `mod_name` is a known module |
| Skip testbench files | Auto-excludes `_tb.v`, `_tb.sv`, `_bench.v`, `_bench.sv`, `_testbench.v`, `_testbench.sv` |
| Scan `.v` files | |
| Scan `.sv` files | Basic port/param extraction only; SV-specific constructs (interfaces, packages, etc.) are not parsed |
| Recurse into subdirectories | Via `-d` flag |
| Accept explicit file list | Via `-f` flag, no directory traversal |
| Exclude paths by substring | Via `--exclude` |
| **Not supported**: Pre-2001 Verilog port style | `input clk;` declarations inside module body |
| **Not supported**: Multiple modules per file | Only the first `module` block is parsed |
| **Not supported**: `include` / macro expansion | Macros in port names may partially parse |

### Dependency graph

| Capability | Notes |
|-----------|-------|
| Build `calls` list per module | Instantiations of known modules only |
| Build `called_by` list per module | Inverse of `calls`, computed automatically |
| Self-instantiation detection | Tracked as a CI issue |
| Export graph to `graph.json` | `--json-graph` flag; see `docs/graph_schema.json` |

### Markdown generation

| Capability | Notes |
|-----------|-------|
| Create new `.md` per module | Sections: Description, Parameters, Inputs, Outputs, Inouts, Calls, Called By |
| Preserve existing `Description` section | Never overwritten; defaults to `TODO: Add description` |
| Update managed sections in-place | Regex-based section replacement in existing files |
| Diff-aware writes | File is only written if content changed |
| Track additions / removals per section | Used for verbose diff output |
| Section-level diff in verbose mode | `-vv` shows `+add/-remove` counts per section |

### Logging and output

| Capability | Notes |
|-----------|-------|
| Completion summary | Always printed: `N module(s) processed — M doc(s) written, K unchanged` |
| Log file (always) | Written to a temp `.log` file whenever any docs are modified |
| Print modified file paths | `-v` flag |
| Print section-level diffs | `-vv` flag |
| Missing description report | Printed when descriptions are still TODO (suppressed in `--ci` mode) |
| Dry-run preview | `--dry-run` — no files written; always shows would-be-written list |

### CI mode (`--ci`)

| Check | Trigger |
|-------|---------|
| Missing description | Module description starts with `TODO` |
| No IO | Module has no inputs and no outputs |
| Self-instantiation | Module instantiates itself |

All checks produce a machine-readable `*_errors.log` file. `--print-errors` mirrors them to stdout. Exit code 1 on any failure.

---

## verilint

### Lint execution

| Capability | Notes |
|-----------|-------|
| Run `verilator --lint-only -Wall` | Per-file invocation |
| Pass include directories | `-I DIR` flag, repeatable; forwarded as `-IDIR` to verilator |
| Parse `%Warning-*` lines | Extracts file path, line number, message |
| Parse `%Error:` lines | Same |
| Skip verilator context/arrow lines | Lines not starting with `%Warning`/`%Error` are ignored |
| Filter to target file only | Warnings from included files or other modules are not tagged |
| First message per line wins | Avoids unreadable stacked inline comments |
| Out-of-bounds line guard | Line numbers beyond file length are silently skipped (macro expansions) |

### Source file tagging

| Capability | Notes |
|-----------|-------|
| Append `/* Check: message */` to warned line | Inline, end-of-line |
| Replace existing `/* Check: */` on re-run | Idempotent; does not stack comments |
| Insert `// lint-test: <command>` header | Added after the leading comment block |
| Insert `// tb-test: tba` header | Placeholder for testbench linkage |
| Skip header insertion if already present | Idempotent |
| Preserve leading copyright / file-header comments | Headers inserted after them, not before |

### Run modes

| Mode | Behaviour |
|------|-----------|
| Default | Tag files in place, print count per file |
| `--dry-run` | Print issues per line, write nothing |
| `-v` | Print full raw verilator output |
| Exit code `0` | All files clean |
| Exit code `1` | One or more issues found |

---

## Planned / not yet implemented

| Feature | Area |
|---------|------|
| Multi-module file support | veridoc parser |
| Pre-2001 Verilog port style | veridoc parser |
| SystemVerilog interfaces, packages, typedefs | veridoc parser |
| Graph visualisation (Graphviz / Mermaid) | veridoc output |
| HTML site generation | veridoc output |
| Lint rule: unused ports | veridoc CI |
| Lint rule: naming conventions | veridoc CI |
| `verilint` per-directory batch mode | verilint |
| `verilint` `--clear` to remove all tags | verilint |
| Tree-sitter / pyverilog optional backend | veridoc parser |
| GitHub Actions workflow template | integration |
| Caching for large repos | performance |
