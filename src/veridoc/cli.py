import argparse
from .core import VerilogWikiParser

def main():
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=True)
    
    group.add_argument(
        "-d", "--dir",
        nargs="+",
        metavar="DIR",
        help="One or more directories to recursively scan for Verilog (.v) files"
    )
    
    group.add_argument(
        "-f", "--file",
        nargs="+",
        metavar="FILE",
        help="One or more specific Verilog files to parse (no directory traversal)"
    )
    
    parser.add_argument(
        "-o", "--out",
        default="temp/docs/modules",
        metavar="OUT_DIR",
        help="Output directory for generated markdown docs (default: temp/docs/modules)"
    )
    
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        help="Verbose mode: -v shows modified files, -vv shows detailed section diffs"
    )
    
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Enable CI mode: fail (exit 1) on issues like missing docs, no IO, or invalid structures"
    )
    
    parser.add_argument(
        "--print-errors",
        action="store_true",
        help="Print errors to stdout in addition to the error log file"
    )
    
    parser.add_argument(
        "--json-graph",
        action="store_true",
        help="Generate dependency graph as JSON (graph.json) in output directory"
    )
    
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="EXCLUDE",
        help="Directories or files to exclude from scanning"
    )

    args = parser.parse_args()

    paths = args.dir if args.dir else args.file

    v = VerilogWikiParser(
        paths, 
        verbose=args.v, 
        ci=args.ci, 
        json_graph=args.json_graph, 
        print_errors=args.print_errors,
        exclude=args.exclude
    )
    v.scan()
    v.generate_markdown(args.out)
    v.write_json(args.out)
    v.write_log()
    v.run_ci_checks()

    print("Done.")

if __name__ == "__main__":
    main()
