# Veridoc Specifications

## 1. Overview
Veridoc is a CI-native documentation layer for RTL projects. It parses Verilog source files, extracts structural information (ports, parameters, module instantiations), and generates consistent Markdown documentation.

## 2. Core Capabilities
- **Regex-based Parsing**: Extracts module names, parameters, inputs, outputs, inouts, and instances.
- **Dependency Tracking**: Builds a module dependency graph (`calls` and `called_by`).
- **Diff-Aware Updates**: Rewrites Markdown only if generated content differs.
- **Continuous Integration (CI)**: Asserts architectural rules (no zero-IO modules, no self-instantiations, missing descriptions).
- **JSON Graph Export**: Dumps module relationships.

## 3. Parsing Rules
- **Comments**: All `//` and `/* ... */` comments are stripped before parsing.
- **Module Match**: Identifies `module <name> [#(parameters)] (<ports>);`.
- **Parameters**: Extracted from the parameter block by splitting on commas.
- **Ports**: 
  - Tracks direction (`input`, `output`, `inout`).
  - Supports comma-separated ports with inherited direction (e.g., `output reg a, b, c`).
- **Calls**: Finds instantiations by matching `mod_name [#(params)] instance_name (` where `mod_name` is a known module within the parsing scope.

## 4. Markdown Generation
- Uses existing `.md` files to preserve the manual `Description` section.
- Auto-generates `Parameters`, `Inputs`, `Outputs`, `Inouts`, `Calls`, and `Called By` sections.
- Tracks addition and removal of list items per section for verbose diff logs.

## 5. Logging and Verbosity
- **Level 0 (Default)**: Silent stdout (except completion/errors), writes basic modified files log to a temp file.
- **Level 1 (`-v`)**: Prints modified files to stdout and temp log.
- **Level 2 (`-vv`)**: Prints modified files with detailed section diffs (`+add/-rem`) to stdout and temp log.
- **Error Log**: CI validation failures are logged to `*_errors.log`.
- **`--print-errors`**: Conditionally mirrors error log contents to stdout.

## 6. CI Rules
Fails the build (`sys.exit(1)`) if:
- Module has no inputs and no outputs (`no IO`).
- Module instantiates itself (`self-instantiation`).
- Module description starts with `TODO` (`missing description`).
\n## 7. Graph JSON Schema\nThe `--json-graph` export produces a `graph.json` file. The format is a dictionary where each key is a module name, mapping to its outbound calls (`calls`) and inbound calls (`called_by`).\nSee `docs/graph_schema.json` for the formal JSON Schema.
