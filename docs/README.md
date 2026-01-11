# MCP Server Optimization Documentation

This directory contains documentation for the MCP server optimization project.

## Documents

- **OPTIMIZATION_GUIDE.md** - Comprehensive guide for optimizing MCP servers
- **OPTIMIZATION_SUMMARY.md** - Summary of optimization standards and patterns
- **REMAINING_WORK.md** - Tracking document for remaining optimization work

## Progress

- **Completed**: 7/16 servers (43.75%)
- **Remaining**: 9 servers

## Completed Servers

1. lscpu (12202) - CPU architecture info collection
2. numa_topo (12203) - NUMA hardware topology query
3. numastat (12210) - System-wide NUMA memory access status
4. numa_cross_node (12211) - Locate high cross-node memory access processes
5. numa_container (12214) - Monitor Docker container NUMA memory access
6. cache_miss_audit (12217) - Locate CPU cache miss performance loss
7. perf_interrupt (12220) - Locate high-frequency interrupt CPU usage

## Optimization Standards

All servers follow these standards:
- ✅ Import order: stdlib → third-party → custom
- ✅ Single responsibility functions
- ✅ Exception chaining with `from e`
- ✅ Config separation (public/private)
- ✅ Password-only SSH authentication
- ✅ Bilingual descriptions (Chinese/English)
- ✅ Simplified client interface
- ✅ Correct port numbers

## Quick Start

To optimize a server:

1. Read `OPTIMIZATION_GUIDE.md` for detailed patterns
2. Review a completed server as reference (e.g., lscpu)
3. Follow the step-by-step guide in the optimization guide
4. Use the checklist to verify completion
5. Test using the validation steps

## Examples

See the following completed servers for reference:
- Simple server: `servers/numastat/src/server.py`
- Server with config params: `servers/cache_miss_audit/src/server.py`
- Complex server: `servers/numa_cross_node/src/server.py`

