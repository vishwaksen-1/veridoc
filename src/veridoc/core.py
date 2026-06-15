import re
import os
import tempfile
import json
import sys

class VerilogWikiParser(object):
    def __init__(self, paths, verbose=0, ci=False, json_graph=False, print_errors=False, exclude=None):
        self.paths = paths
        self.modules = {}
        self.called_by = {}
        self.modified_files = []
        self.verbose = verbose
        self.ci = ci
        self.json_graph = json_graph
        self.print_errors = print_errors
        self.exclude = exclude or []
        self.issues = []

    # -------------------------
    # CLEAN COMMENTS
    # -------------------------
    def clean(self, text):
        text = re.sub(r"//[^\n]*", "\n", text)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return text

    # -------------------------
    # PARSING
    # -------------------------
    def extract_module_and_ports(self, text):
        pattern = r"module\s+(\w+)\s*(#\s*\((.*?)\))?\s*\((.*?)\)\s*;"
        m = re.search(pattern, text, flags=re.S)
        if not m:
            return None

        mod_name = m.group(1)
        param_block = m.group(3) or ""
        port_block = m.group(4)

        inputs, outputs, inouts = [], [], []
        parameters = []

        for p in re.split(r",\s*\n|,\s*", param_block):
            p = p.strip()
            if p.startswith("parameter"):
                parameters.append(p.replace("parameter", "").strip())

        ports = re.split(r",\s*\n|,\s*", port_block)

        current_direction = None
        for p in ports:
            p = p.strip()
            if not p:
                continue

            p = re.sub(r"`\w+\s+", "", p)
            tokens = p.split()
            if not tokens:
                continue

            name = tokens[-1]

            if "input" in tokens:
                current_direction = "input"
            elif "output" in tokens:
                current_direction = "output"
            elif "inout" in tokens:
                current_direction = "inout"

            if current_direction == "input":
                inputs.append(name)
            elif current_direction == "output":
                outputs.append(name)
            elif current_direction == "inout":
                inouts.append(name)

        return {
            "name": mod_name,
            "inputs": inputs,
            "outputs": outputs,
            "inouts": inouts,
            "parameters": parameters
        }

    def remove_module_header(self, text):
        return re.sub(r"\bmodule\s+\w+.*?;\s*", "", text, flags=re.S)

    def extract_calls(self, text, known_modules, current_module):
        calls = set()
        text = self.remove_module_header(text)

        pattern = r"\b(\w+)\s*(?:#\s*\(.*?\))?\s+\w+\s*\("
        for m in re.finditer(pattern, text, flags=re.S):
            mod_name = m.group(1)
            if mod_name in known_modules:
                calls.add(mod_name)

        return sorted(list(calls))

    # -------------------------
    # SCAN
    # -------------------------
    def scan(self):
        file_texts = {}
        all_files = []

        def is_excluded(path):
            for ex in self.exclude:
                if ex in path:
                    return True
            return False

        for p in self.paths:
            if os.path.isfile(p):
                if not is_excluded(p):
                    all_files.append(p)
            else:
                for root, dirs, files in os.walk(p):
                    dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d))]
                    if is_excluded(root):
                        continue
                    for f in files:
                        if f.endswith(".v") and not f.endswith("_tb.v"):
                            full_path = os.path.join(root, f)
                            if not is_excluded(full_path):
                                all_files.append(full_path)

        for path in all_files:
            with open(path, "r") as fh:
                text = self.clean(fh.read())

            file_texts[path] = text

            mod = self.extract_module_and_ports(text)
            if not mod:
                continue

            self.modules[mod["name"]] = {
                "file": path,
                "calls": [],
                "inputs": mod["inputs"],
                "outputs": mod["outputs"],
                "inouts": mod["inouts"],
                "parameters": mod["parameters"]
            }

        known_modules = set(self.modules.keys())

        for path, text in file_texts.items():
            mod = self.extract_module_and_ports(text)
            if not mod:
                continue

            mod_name = mod["name"]
            self.modules[mod_name]["calls"] = self.extract_calls(
                text, known_modules, mod_name
            )

        self.build_called_by()

    def build_called_by(self):
        for mod in self.modules:
            self.called_by[mod] = []

        for caller, data in self.modules.items():
            for callee in data["calls"]:
                if callee in self.called_by:
                    self.called_by[callee].append(caller)

    # -------------------------
    # EXISTING MD PARSE
    # -------------------------
    def parse_existing_sections(self, path):
        if not os.path.exists(path):
            return {}

        with open(path) as f:
            content = f.read()

        sections = {}
        for sec in ["Description", "Parameters", "Inputs", "Outputs", "Inouts", "Calls", "Called By"]:
            m = re.search(rf"## {sec}\n(.*?)(\n##|\Z)", content, re.S)
            if m:
                sections[sec] = m.group(1).strip()

        return sections

    # -------------------------
    # DIFF
    # -------------------------
    def diff_lists(self, old, new):
        old_set = set(old)
        new_set = set(new)
        return len(new_set - old_set), len(old_set - new_set)

    # -------------------------
    # MARKDOWN
    # -------------------------
    def generate_markdown(self, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
        managed_sections = ["Parameters", "Inputs", "Outputs", "Inouts", "Calls", "Called By"]

        for mod, data in self.modules.items():
            fname = os.path.join(out_dir, f"{mod}.md")

            old_content = ""
            if os.path.exists(fname):
                with open(fname) as f:
                    old_content = f.read()

            old_sections = self.parse_existing_sections(fname)
            desc = old_sections.get("Description", "TODO: Add description")

            if desc.startswith("TODO"):
                self.issues.append(f"{mod}: missing description")

            def format_list(lst):
                return "\n".join([f"- {x}" for x in lst]) if lst else "- None"

            new_sections = {
                "Parameters": format_list(data["parameters"]),
                "Inputs": format_list(data["inputs"]),
                "Outputs": format_list(data["outputs"]),
                "Inouts": format_list(data["inouts"]),
                "Calls": format_list([f"[{c}]({c}.md)" for c in data["calls"]]),
                "Called By": format_list([f"[{c}]({c}.md)" for c in self.called_by.get(mod, [])]),
            }

            # DIFF LOGIC
            diffs = {}
            for key in ["Parameters", "Inputs", "Outputs", "Inouts", "Calls"]:
                old_list = re.findall(r"- (.+)", old_sections.get(key, ""))
                new_list = re.findall(r"- (.+)", new_sections[key])
                add, rem = self.diff_lists(old_list, new_list)
                diffs[key] = (add, rem)

            content = ""
            if not old_content:
                content = f"# {mod}\n\n## Description\n{desc}\n\n"
                for k, v in new_sections.items():
                    content += f"## {k}\n{v}\n\n"
            else:
                content = old_content
                for sec in managed_sections:
                    new_sec_text = f"## {sec}\n{new_sections[sec]}\n"
                    pattern = rf"## {sec}\n.*?(?=\n##|\Z)"
                    if re.search(pattern, content, flags=re.S):
                        content = re.sub(pattern, new_sec_text, content, flags=re.S)
                    else:
                        content += f"\n{new_sec_text}\n"

            content = content.strip() + "\n"

            if content != old_content:
                with open(fname, "w") as f:
                    f.write(content)
                
                diff_str = f"{mod}: " + ", ".join([f"{k} +{a}/-{r}" for k, (a, r) in diffs.items()])
                self.modified_files.append((fname, diff_str))

    # -------------------------
    # LOGGING
    # -------------------------
    def write_log(self):
        if not self.modified_files:
            return

        log_lines = []
        if self.verbose >= 1:
            log_lines.append("Modified files:")
            for fname, _ in self.modified_files:
                log_lines.append(fname)

        if self.verbose >= 2:
            log_lines.append("\nDetailed section diffs:")
            for _, diff_str in self.modified_files:
                log_lines.append(diff_str)

        if log_lines:
            tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".log")
            tmp.write("\n".join(log_lines) + "\n")
            tmp.close()

            print("\n" + "\n".join(log_lines))
            print(f"\nLog file: {tmp.name}")

        missing_docs = [mod for mod, _ in self.modules.items() if any(f"{mod}: missing description" in i for i in self.issues)]
        if missing_docs:
            print("\nMissing Docs Summary Report:")
            for m in missing_docs:
                print(f"  - {m}")

    # -------------------------
    # JSON GRAPH
    # -------------------------
    def write_json(self, out_dir):
        if not self.json_graph:
            return

        graph = {}
        for m, d in self.modules.items():
            graph[m] = {
                "calls": d["calls"],
                "called_by": self.called_by.get(m, [])
            }

        path = os.path.join(out_dir, "graph.json")
        with open(path, "w") as f:
            json.dump(graph, f, indent=2)

    # -------------------------
    # CI VALIDATION
    # -------------------------
    def run_ci_checks(self):
        if not self.ci:
            return

        for mod, data in self.modules.items():
            if not data["inputs"] and not data["outputs"]:
                self.issues.append(f"{mod}: no IO")

            if mod in data["calls"]:
                self.issues.append(f"{mod}: self-instantiation")

        if self.issues:
            tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix="_errors.log")
            tmp.write("CI FAIL:\n")
            for i in self.issues:
                tmp.write(i + "\n")
            tmp.close()

            if self.print_errors:
                print("\nCI FAIL:")
                for i in self.issues:
                    print(i)
            print(f"\nError log file: {tmp.name}")
            sys.exit(1)
