# ToDos:

- [x] verilint bug
	```
	// lint-test: verilator --lint-only -Wall -Irtl/core/ rtl/afe/clk_cross_bus.v
	// tb-test: tba
	```
	Include directories `-I` should have a space,
	It should be `-I rtl/core/` instead of `-Irtl/core/`.

- [x] verilint feature check
	- When it adds lint-test, tb-test commands on the top, it should check if it's doing a dubplicate job, and behave appropriately.


- [ ] Add a Graphviz export for the dependency graph of callgraph. Preferably as a separate tool to work on the generated json graph.

- [ ] MCP server wrapper
	Expose veridoc and verilint as MCP tools so agents (Claude, Cursor, Devin, etc.) can call them natively without subprocess invocation.
	See examples/mcp_server_description.md for the proposed tool schema and implementation notes.
