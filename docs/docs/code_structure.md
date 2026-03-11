# Code Structure

This document provides a detailed breakdown of the `src/codegraphcontext/` directory structure.

## Directory Overview

```
src/codegraphcontext/
├── __init__.py           # Package initialization
├── __main__.py           # CLI entry point (python -m codegraphcontext)
├── server.py             # MCP Server implementation
├── tool_definitions.py   # MCP tool definitions
├── prompts.py            # LLM prompts and templates
├── cli/                  # Command-line interface
├── core/                 # Core functionality
├── tools/                # Tool implementations
└── utils/                # Utility modules
```

## Top-Level Files

| File | Purpose |
| :--- | :--- |
| `__init__.py` | Package metadata and imports |
| `__main__.py` | Enables `python -m codegraphcontext` execution |
| `server.py` | MCP server host - translates JSON requests to database queries |
| `tool_definitions.py` | Defines all MCP tools available to AI clients |
| `prompts.py` | LLM prompts for code analysis and query generation |

## CLI Module (`cli/`)

The CLI module provides the command-line interface using Typer.

| File | Purpose |
| :--- | :--- |
| `main.py` | Main CLI entry point with all commands (index, query, visualize, etc.) |
| `config_manager.py` | Configuration file management |
| `cli_helpers.py` | Helper functions for CLI operations |
| `visualizer.py` | Graph visualization generation (Vis.js HTML output) |
| `setup_wizard.py` | Interactive setup wizard for Neo4j/MCP configuration |
| `registry_commands.py` | Bundle registry commands |
| `setup_macos.py` | macOS-specific setup utilities |

## Core Module (`core/`)

The core module contains the essential backend functionality.

| File | Purpose |
| :--- | :--- |
| `database.py` | Database abstraction layer |
| `database_falkordb.py` | FalkorDB (embedded) implementation |
| `database_falkordb_remote.py` | Remote FalkorDB implementation |
| `watcher.py` | File system monitoring for incremental indexing |
| `jobs.py` | Background job management |
| `bundle_registry.py` | Bundle registry for on-demand code loading |
| `cgc_bundle.py` | `.cgc` bundle format handling |
| `falkor_worker.py` | FalkorDB worker for async operations |

## Tools Module (`tools/`)

The tools module implements the MCP tools and indexing logic.

| File | Purpose |
| :--- | :--- |
| `graph_builder.py` | Builds knowledge graph from source code (indexer) |
| `code_finder.py` | Code search and discovery tool |
| `scip_indexer.py` | SCIP-based indexing implementation |
| `scip_pb2.py` | Protocol buffer definitions for SCIP |
| `package_resolver.py` | Resolves package dependencies |
| `system.py` | System-level operations |
| `advanced_language_query_tool.py` | Advanced query capabilities |

### Tools Subdirectories

#### `tools/handlers/`

Event handlers for MCP requests.

| File | Purpose |
| :--- | :--- |
| `indexing_handlers.py` | Indexing operation handlers |
| `query_handlers.py` | Query execution handlers |
| `analysis_handlers.py` | Code analysis handlers |
| `management_handlers.py` | Repository management handlers |
| `watcher_handlers.py` | File watcher event handlers |

#### `tools/languages/`

Language-specific parsers and analyzers.

| Language | Files |
| :--- | :--- |
| Python | `python.py` |
| JavaScript | `javascript.py` |
| TypeScript | `typescript.py`, `typescriptjsx.py` |
| Go | `go.py` |
| Rust | `rust.py` |
| Java | `java.py` |
| C/C++ | `c.py`, `cpp.py` |
| Ruby | `ruby.py` |
| PHP | `php.py` |
| Swift | `swift.py` |
| Scala | `scala.py` |
| Haskell | `haskell.py` |
| Kotlin | `kotlin.py` |
| C# | `csharp.py` |
| Dart | `dart.py` |
| Perl | `perl.py` |

#### `tools/query_tool_languages/`

Query tool implementations per language (for advanced querying).

Contains: `python_toolkit.py`, `javascript_toolkit.py`, `typescript_toolkit.py`, `go_toolkit.py`, `rust_toolkit.py`, `java_toolkit.py`, `c_toolkit.py`, `cpp_toolkit.py`, `swift_toolkit.py`, `ruby_toolkit.py`, `scala_toolkit.py`, `csharp_toolkit.py`, `haskell_toolkit.py`, `dart_toolkit.py`, `perl_toolkit.py`

## Utils Module (`utils/`)

Utility modules for supporting functionality.

| File | Purpose |
| :--- | :--- |
| `debug_log.py` | Debug logging utilities |
| `tree_sitter_manager.py` | Tree-sitter parser management |
| `visualize_graph.py` | Graph visualization utilities |

## Data Flow

```
User (CLI/MCP)
      │
      ▼
┌─────────────────┐
│  cli/main.py    │  (CLI commands)
│  server.py      │  (MCP server)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  tools/handlers │  (Request routing)
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌─────────┐
│ Graph │ │ Query   │
│Builder│ │ Tools   │
└───┬───┘ └───┬─────┘
    │         │
    ▼         ▼
┌─────────────────┐
│   core/database │
└────────┬────────┘
         │
         ▼
   Graph Database
(FalkorDB or Neo4j)
```

## Key Technologies

- **CLI Framework**: Typer
- **Protocol**: Model Context Protocol (MCP)
- **Parsing**: Tree-sitter for multi-language AST extraction
- **Databases**: FalkorDB (embedded via Redis) or Neo4j
- **Serialization**: Protocol Buffers (SCIP format)