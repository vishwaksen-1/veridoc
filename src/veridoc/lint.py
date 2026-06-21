import re
import subprocess
import sys
import os
import argparse
import shutil


def _get_verilator_version():
    try:
        out = subprocess.check_output(["verilator", "--version"], text=True)
        return out.strip().splitlines()[0]
    except Exception:
        return None


def _check_verilator():
    if not shutil.which("verilator"):
        print(
            "Error: verilator is not installed or not in PATH.\n"
            "\n"
            "Install it:\n"
            "  Debian / Ubuntu:  sudo apt install verilator\n"
            "  macOS:            brew install verilator\n"
            "  From source:      https://verilator.org/guide/latest/install.html\n"
            "\n"
            "Note: verilator is a system tool and cannot be installed via pip.",
            file=sys.stderr,
        )
        sys.exit(1)


def _run_lint(filepath, include_dirs):
    cmd = ["verilator", "--lint-only", "-Wall"]
    for d in include_dirs:
        cmd.extend(["-I", d])
    cmd.append(filepath)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout + result.stderr, cmd


def parse_lint_output(output, filepath):
    """Return {line_num: message} for warnings/errors in filepath only.

    Only the first issue per line is kept — multiple warnings on the same
    line would produce unreadable inline comments. Verilator continuation
    lines (context arrows, notes) are skipped; only lines starting with
    '%Warning' or '%Error' are matched.
    """
    issues = {}
    target_base = os.path.basename(filepath)
    target_abs = os.path.abspath(filepath)

    # Format: %Warning-TYPE: path:line:col: message
    #         %Error: path:line:col: message
    pattern = re.compile(r"^%(Warning[^:]*|Error[^:]*): (.+?):(\d+):\d+: (.+)$")
    for line in output.splitlines():
        m = pattern.match(line)
        if not m:
            continue
        warn_file = m.group(2)
        line_num = int(m.group(3))
        message = m.group(4).strip()

        if (os.path.basename(warn_file) == target_base
                or os.path.abspath(warn_file) == target_abs):
            if line_num not in issues:
                issues[line_num] = message

    return issues


def tag_file(filepath, issues, lint_cmd):
    """Tag warned lines inline and add lint/tb-test header lines.

    Idempotent: re-running replaces existing /* Check: */ tags and
    skips header lines that are already present.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    # Tag each warned line with a trailing /* Check: ... */ comment.
    # Verilator line numbers are 1-based; Python list is 0-based.
    # Guard against line numbers that fall outside the file — this can
    # happen when a warning originates inside a macro expansion.
    for line_num, message in sorted(issues.items()):
        idx = line_num - 1
        if idx < 0 or idx >= len(lines):
            continue
        line = lines[idx].rstrip("\n")
        line = re.sub(r"\s*/\* Check:.*?\*/", "", line).rstrip()
        lines[idx] = f"{line}  /* Check: {message} */\n"

    # Insert lint/tb-test headers after the leading comment block (copyright
    # headers, file-level comments, blank lines at the top).
    insert_idx = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("//") or s.startswith("/*") or s.startswith("*") or s == "":
            insert_idx = i + 1
        else:
            break

    lint_cmd_str = " ".join(lint_cmd)
    full_content = "".join(lines)
    new_headers = []
    if "// lint-test:" not in full_content:
        new_headers.append(f"// lint-test: {lint_cmd_str}\n")
    if "// tb-test:" not in full_content:
        new_headers.append("// tb-test: tba\n")

    if new_headers:
        lines = lines[:insert_idx] + new_headers + lines[insert_idx:]

    with open(filepath, "w") as f:
        f.writelines(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="verilint",
        description="Run verilator lint on Verilog files and tag warnings inline"
    )
    parser.add_argument(
        "file",
        nargs="+",
        metavar="FILE",
        help="Verilog/SystemVerilog file(s) to lint"
    )
    parser.add_argument(
        "-I", "--include",
        dest="include_dirs",
        action="append",
        metavar="DIR",
        default=[],
        help="Add include directory (passed to verilator as -I, repeatable)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show issues without modifying any files"
    )
    parser.add_argument(
        "-v",
        action="store_true",
        help="Print full verilator output"
    )
    args = parser.parse_args()

    _check_verilator()

    if args.v:
        print(f"Using {_get_verilator_version()}")

    any_issues = False
    for filepath in args.file:
        if not os.path.isfile(filepath):
            print(f"Error: {filepath}: file not found", file=sys.stderr)
            continue

        output, cmd = _run_lint(filepath, args.include_dirs)
        issues = parse_lint_output(output, filepath)

        if args.v and output.strip():
            print(output.strip())

        if not issues:
            print(f"{filepath}: clean")
            continue

        any_issues = True
        if args.dry_run:
            print(f"\n{filepath}: {len(issues)} issue(s) would be tagged:")
            for ln, msg in sorted(issues.items()):
                print(f"  Line {ln}: {msg}")
        else:
            tag_file(filepath, issues, cmd)
            print(f"{filepath}: tagged {len(issues)} issue(s)")

    sys.exit(1 if any_issues else 0)


if __name__ == "__main__":
    main()
