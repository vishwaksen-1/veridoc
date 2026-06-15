import unittest
import os
import tempfile
import json
from veridoc.core import VerilogWikiParser

class TestVerilogWikiParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.module_a_path = os.path.join(self.test_dir.name, "mod_a.v")
        self.module_b_path = os.path.join(self.test_dir.name, "mod_b.v")
        
        with open(self.module_a_path, "w") as f:
            f.write("""
            module mod_a #(
                parameter WIDTH = 8,
                parameter DEPTH = 16
            ) (
                input clk,
                input rst,
                output reg s_read, s_write,
                inout bus
            );
                // instantiated mod_b
                mod_b #(.W(WIDTH)) u_b (
                    .clk(clk)
                );
                
                // self instantiation test
                mod_a u_a_self ();
            endmodule
            """)
            
        with open(self.module_b_path, "w") as f:
            f.write("""
            module mod_b (
                input clk
            );
            endmodule
            """)

        self.empty_mod_path = os.path.join(self.test_dir.name, "empty_mod.v")
        with open(self.empty_mod_path, "w") as f:
            f.write("module empty_mod (); endmodule")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parsing_ports_and_parameters(self):
        parser = VerilogWikiParser([self.test_dir.name])
        parser.scan()
        
        self.assertIn("mod_a", parser.modules)
        mod_a = parser.modules["mod_a"]
        
        # Check params
        self.assertEqual(len(mod_a["parameters"]), 2)
        self.assertTrue(any("WIDTH" in p for p in mod_a["parameters"]))
        
        # Check ports with comma inheritance
        self.assertEqual(mod_a["inputs"], ["clk", "rst"])
        self.assertEqual(mod_a["outputs"], ["s_read", "s_write"])
        self.assertEqual(mod_a["inouts"], ["bus"])

    def test_dependency_extraction(self):
        parser = VerilogWikiParser([self.test_dir.name])
        parser.scan()
        
        # mod_a calls mod_b and mod_a
        self.assertIn("mod_b", parser.modules["mod_a"]["calls"])
        self.assertIn("mod_a", parser.modules["mod_a"]["calls"])
        
        # mod_b is called by mod_a
        self.assertIn("mod_a", parser.called_by["mod_b"])

    def test_ci_validation(self):
        parser = VerilogWikiParser([self.test_dir.name], ci=True)
        parser.scan()
        
        # mock generate_markdown to create issues for missing description
        out_dir = os.path.join(self.test_dir.name, "docs")
        parser.generate_markdown(out_dir)
        
        # Catch sys.exit
        with self.assertRaises(SystemExit) as cm:
            parser.run_ci_checks()
        self.assertEqual(cm.exception.code, 1)
        
        # Check issues
        self.assertIn("empty_mod: no IO", parser.issues)
        self.assertIn("mod_a: self-instantiation", parser.issues)
        self.assertIn("mod_a: missing description", parser.issues)

    def test_json_graph(self):
        out_dir = os.path.join(self.test_dir.name, "docs")
        os.makedirs(out_dir, exist_ok=True)
        
        parser = VerilogWikiParser([self.test_dir.name], json_graph=True)
        parser.scan()
        parser.write_json(out_dir)
        
        graph_path = os.path.join(out_dir, "graph.json")
        self.assertTrue(os.path.exists(graph_path))
        
        with open(graph_path) as f:
            data = json.load(f)
            self.assertIn("mod_a", data)
            self.assertIn("mod_b", data["mod_a"]["calls"])

    def test_markdown_generation_and_logging(self):
        out_dir = os.path.join(self.test_dir.name, "docs")
        parser = VerilogWikiParser([self.module_b_path], verbose=2)
        parser.scan()
        parser.generate_markdown(out_dir)
        
        md_path = os.path.join(out_dir, "mod_b.md")
        self.assertTrue(os.path.exists(md_path))
        
        # Check it recognized the file was modified
        self.assertTrue(any(md_path in entry[0] for entry in parser.modified_files))
        
        # Run again, should not modify
        parser2 = VerilogWikiParser([self.module_b_path])
        parser2.scan()
        parser2.generate_markdown(out_dir)
        self.assertEqual(len(parser2.modified_files), 0)

if __name__ == "__main__":
    unittest.main()
