# JSON-to-Graph Transformation Planning

> **Status**: Planning Phase → Implementation

This document tracks the planning and implementation of transforming **any JSON schema** to a connected graph using a unified transformation approach.

**Key Principle**: One mechanism handles all JSON sources - external tools produce JSON, transformer creates graph, contain maps link layers together.

---

## Core Principle: JSON as Universal Graph Input

> **The ONLY mechanism for graph construction is JSON-to-Graph transformation.**

This approach supports **any system** represented as JSON - not just programming languages:

| Input Type | Example JSON Sources |
|------------|---------------------|
| **Programming Languages** | tree-sitter, LSP, SCIP, Babel, esprima |
| **Filesystem** | File tree structures, directory metadata |
| **APIs** | OpenAPI/Swagger, GraphQL schemas |
| **Databases** | SQL DDL, ERD diagrams, schema definitions |
| **Documentation** | Markdown AST, JSDoc, Sphinx |
| **Configuration** | Kubernetes manifests, Terraform, Docker Compose |
| **Data Formats** | CSV (converted to JSON), XML (converted to JSON) |
| **External Systems** | Any system that exports JSON |

**Key Insight**: Once data is in JSON format, the same transformation mechanism applies. The graph schema is derived from the JSON structure itself, not from language-specific patterns.

---

## Current State (as of 2026-03-11)

### GraphBuilder Implementation

The current `GraphBuilder` (`src/codegraphcontext/tools/graph_builder.py`) uses a **hybrid pattern-based approach**:

**Architecture**:
- `TreeSitterParser` - Language-agnostic wrapper that delegates to language-specific parsers
- `GraphBuilder` - Main orchestrator for Neo4j/FalkorDB graph construction
- Supports 18+ languages: Python, JavaScript, TypeScript, Go, C, C++, Rust, Java, Ruby, C#, PHP, Kotlin, Scala, Swift, Haskell, Dart, Perl

**Current Dependencies**:
```
asyncio (stdlib)
pathspec (stdlib)
pathlib (stdlib)
datetime (stdlib)
tree-sitter (external)
├── DatabaseManager (internal) - Neo4j/FalkorDB connection
├── JobManager (internal) - Background job tracking
├── get_tree_sitter_manager (internal) - Language parser management
├── get_config_value (internal) - Configuration retrieval
└── Logging utilities (internal) - debug_log, info_logger, error_logger, warning_logger

TO BE REMOVED:
├── tree-sitter (moves to adapter)
├── get_tree_sitter_manager (moves to adapter)
└── Language-specific parsers (replaced by adapters)

**Current Workflow** (TO BE REMOVED):
1. `build_graph_from_path_async()` - Main entry point
2. `_pre_scan_for_imports()` - Build imports map for cross-file resolution
3. `parse_file()` - Parse with tree-sitter, extract code elements
4. `add_file_to_graph()` - Create nodes and relationships in single transaction
5. `_create_all_function_calls()` - Post-process CALLS relationships
6. `_create_all_inheritance_links()` - Post-process INHERITS relationships

**Target Workflow**:
1. Adapter converts source (tree-sitter, OpenAPI, etc.) to JSON
2. JsonToGraphTransformer transforms JSON to graph nodes/edges
3. Direct batch write to FalkorDB

**Current Graph Schema**:
- **Node Labels**: Repository, File, Directory, Function, Class, Trait, Interface, Variable, Module, Macro, Struct, Enum, Union, Record, Property, Parameter, Annotation

**To Be Removed** (replaced by JSON-to-Graph approach):
- Pattern-based extraction (in `parse_file()`)
- Language-specific parsers (`tools/languages/*.py`)
- TreeSitterParser class
- Import resolution heuristics (`_pre_scan_for_imports()`)
- Function call resolution (`_create_all_function_calls()`)
- Inheritance link inference (`_create_all_inheritance_links()`)

---

## Target State: Pure JSON-to-Graph Transformation

If GraphBuilder's task was purely transforming JSON to graph in FalkorDB, the architecture would simplify significantly:

**Key Change**: JSON sources directly feed the transformer - no intermediate adapter layer needed.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        JSON INPUT SOURCES                            │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┤
│  tree-sitter │   OpenAPI   │  Kubernetes │    CSV      │   [Any]     │
│      JSON     │     JSON    │     JSON    │     JSON    │     JSON    │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┘
       │              │              │              │              │
       └──────────────┴──────────────┴──────────────┴──────────────┘
                                  ↓
                    ┌───────────────────────────┐
                    │  JsonToGraphTransformer   │
                    │  (Single Universal Core)  │
                    └───────────────────────────┘
                                  ↓
                           FalkorDB Graph
```

**Required Dependencies**:
```
json (stdlib)
pathlib (stdlib)
falkordb (external) - Instead of neo4j driver
├── DatabaseManager (simplified) - FalkorDB connection only
└── Configuration (minimal)
```

**Removed from Core**:
- tree-sitter (JSON input comes from external tools)
- tree_sitter_manager (not needed in core)
- Language-specific parsers (external tools produce JSON)
- Complex import resolution logic (external tools produce JSON)

### New Components

```python
class JsonToGraphTransformer:
    """Pure JSON-to-Graph transformer for FalkorDB."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.driver = db_manager.get_driver()
    
    def transform(self, json_data: dict, root_label: str = "Root") -> None:
        """Transform JSON structure to graph nodes and edges."""
        # 1. Generate node IDs
        # 2. Create nodes from JSON objects
        # 3. Create edges from JSON relationships
        # 4. Batch write to FalkorDB
    
    def transform_batch(self, json_list: list[dict], root_label: str) -> None:
        """Transform multiple JSON objects."""
```

### JSON-to-Graph Schema (Refined)

| JSON Construct | Graph Representation |
|----------------|---------------------|
| `{ "id": "uuid", "type": "function", "name": "main" }` | `(:Function {id: "uuid", name: "main"})` |
| `{ "type": "function", "body": {...} }` | `(:Function) -[:body]->(:Block)` |
| `{ "type": "call", "function": "foo", "args": [...] }` | `(:Call) -[:function]->(:Identifier {name: "foo"})` |
| `{ "imports": [...] }` | `(:File) -[:imports]->(:Import)` |

### Input Format (External JSON)

The transformer expects JSON from external parsers:

```json
{
  "repository": {
    "path": "/repo",
    "name": "myrepo"
  },
  "files": [
    {
      "path": "/repo/src/main.py",
      "type": "file",
      "functions": [
        {
          "id": "fn-001",
          "name": "main",
          "line_number": 10,
          "body": {...}
        }
      ],
      "classes": [...],
      "imports": [
        {"name": "os", "alias": null}
      ]
    }
  ]
}
```

### FalkorDB-Specific Optimizations

```python
# Use FalkorDB pipelining for batch inserts
def transform_batch_pipelined(self, json_data: list[dict]):
    with self.driver.pipeline():
        for item in json_data:
            self._transform_item(item)
        self.driver.commit()
```

### Migration Path

1. **Phase 1**: Keep existing tree-sitter parsing, add JSON output option
2. **Phase 2**: External parser generates JSON, JsonToGraphTransformer consumes it
3. **Phase 3**: Full JSON-to-graph pipeline, remove tree-sitter dependency from GraphBuilder

---

## Universal JSON-to-Graph Transformation

### The Single Mechanism

All graph construction flows through one path:

```
[Any JSON Source] → [JsonToGraphTransformer] → [FalkorDB Graph]
```

**No more**:
- Language-specific tree-sitter queries
- Pattern matching for specific code elements
- Hardcoded relationships per language

**Only**:
- JSON schema defines structure
- Transformation rules apply uniformly
- Visualization via Cypher queries

### How It Works

1. **Input**: Any JSON document (AST, API schema, config, etc.)
2. **Transform**: Apply universal JSON-to-Graph rules:
   - Objects → Nodes (label from `type` or key)
   - Nested objects → Relationships
   - Primitive values → Node properties
   - Arrays → Multiple relationships
3. **Output**: FalkorDB graph with full relationship structure

### Example: OpenAPI to Graph

```json
{
  "openapi": "3.0.0",
  "paths": {
    "/users": {
      "get": {
        "operationId": "getUsers",
        "responses": {"200": {...}}
      }
    }
  }
}
```

**Becomes Graph:**
```
(:OpenAPI {version: "3.0.0"})
  -[:paths]->(:Object {key: "/users"})
    -[:get]->(:Operation {operationId: "getUsers"})
      -[:responses]->(:Object {key: "200"})
```

### Example: Kubernetes Manifest to Graph

```json
{
  "kind": "Deployment",
  "metadata": {"name": "myapp"},
  "spec": {
    "replicas": 3,
    "template": {
      "spec": {
        "containers": [{"name": "web"}]
      }
    }
  }
}
```

**Becomes Graph:**
```
(:Deployment {kind: "Deployment"})
  -[:metadata]->(:Metadata {name: "myapp"})
  -[:spec]->(:Spec {replicas: 3})
    -[:template]->(:Template)
      -[:spec]->(:ContainerSpec)
        -[:containers]->(:Container {name: "web"})
```

---

## Related Files (Current)

---

## Unified JSON-to-Graph Schema

This approach treats both AST and filesystem JSON as graphs directly.

**Relationship types are derived from JSON keys** - each key becomes its own relationship type:

| JSON Construct | Graph Representation |
|----------------|---------------------|
| `{ "key": {} }` | Node with label from `type`; parent -[:key]-> child |
| `{ "key": [{},{},...] }` | Multiple relationships; parent -[:key]-> node1, parent -[:key]-> node2 |
| `{ "simple_key": "value" }` | Node attribute: `simple_key: "value"` |
| `{ "simple_key": 123 }` | Node attribute: `simple_key: 123` |
| `{ "simple_key": true }` | Node attribute: `simple_key: true` |
| `{ "simple_key": [1,2,3] }` | Node attribute (stored as JSON string) or expand to separate nodes |
| `[{},{}]` (no key) | Multiple standalone nodes (requires parent context for relationship name) |

**Relationship types = JSON keys** - e.g., `functions`, `imports`, `body`, `children`, `metadata`, etc.

### Contain Maps: Linking Graph Layers

**Problem**: How do we connect separate graphs (e.g., filesystem graph to AST graph)?

**Solution**: Contain maps define how leaf nodes or properties in one graph layer connect to the root of another graph layer.

```python
class ContainMap:
    """Defines how to link a parent graph layer to a child graph layer."""
    
    def __init__(self, source_path: str, target_root: str):
        """
        Args:
            source_path: JSON path to source node/property (e.g., "files[].path")
            target_root: Root node label/type of the target graph
        """
        self.source_path = source_path
        self.target_root = target_root
```

**Example: Filesystem → AST Connection**

```json
{
  "name": "src",
  "type": "directory",
  "children": [
    { "name": "main.py", "type": "file", "ast": {...} }
  ]
}
```

**Contain Map**: `"files[].ast"` → AST root node

**Result**:
```
(:Directory {name: "src"})
  -[:children]->(:File {name: "main.py"})
    -[:ast]->(:Program)  ← linked via contain map
```

The `ast` property becomes a node that links to the AST subgraph.

**How it works**:
1. Transform layer 1 (Filesystem) to graph
2. Identify leaf nodes/properties to link (via contain map config)
3. Transform layer 2 (AST) to graph
4. Create edge (from key) from leaf node to layer 2 root

**Multiple Layers**:
- Layer 1: Filesystem → File nodes
- Layer 2: AST → Program nodes (linked to each File)
- Layer 3: Types → Type nodes (linked to AST nodes)
- etc.

Each layer only knows its own JSON structure. Contain maps are configuration that links them.

### Node Identification

**Every node must have a unique identifier** - this is critical for graph operations:

| Strategy | Description | Example |
|----------|-------------|---------|
| `id` | Auto-generated UUID | `"id": "uuid-1234-abcd"` |
| `key` | Composite from path + type | `"key": "/src/main.py:function:main:10"` |
| `name + type` | Combined natural key | `"name": "main", "node_type": "function"` |

**Identifier Properties:**
- `id` - Globally unique (UUID)
- `key` - Locally unique within parent scope (path-based)
- `name` - Human-readable identifier
- `node_type` - AST node type or filesystem type

**Example with ID:**
```json
{
  "id": "node-001",
  "type": "function_definition",
  "name": "main",
  "body": { "id": "node-002", "type": "block" }
}
```

**Graph nodes:**
```
(:FunctionDefinition {id: "node-001", name: "main"})
  -[:body]->(:Block {id: "node-002"})
```

---

## Layer Example: Tree-sitter Grammar JSON

Tree-sitter grammars export as JSON (`tree-sitter generate --json`). This is just another JSON source - same transformation rules apply.

```json
{
  "name": "python",
  "rules": {
    "function_definition": {
      "type": "SEQ",
      "children": [...]
    }
  }
}
```

**Becomes Graph** (same as any JSON):
```
(:Grammar {name: "python"})
  -[:rules]->(:Object {key: "function_definition"})
    -[:type]->(:Type {value: "SEQ"})
```

No special rules needed - just standard JSON-to-Graph.

### Scope

#### Phase 3A: Grammar Extraction
- [ ] Add grammar JSON export to tree-sitter manager
- [ ] Cache grammar definitions per language
- [ ] Support grammar version tracking

#### Phase 3B: Grammar-to-Graph
- [ ] Implement grammar JSON-to-graph transformer
- [ ] Create grammar node types (Rule, Type, Field, Symbol)
- [ ] Build rule relationship edges
- [ ] Handle ALIAS, PREC, CHOICE complex types

#### Phase 3C: Integration
- [ ] Connect grammar nodes to AST nodes (AST node → Grammar rule)
- [ ] Enable queries across grammar + AST
- [ ] Documentation generation from grammar graph

### Example: AST JSON to Graph

```json
{
  "type": "program",
  "body": [
    {
      "type": "function_definition",
      "name": "main",
      "body": {
        "type": "block",
        "statements": [...]
      }
    }
  ]
}
```

**Becomes Graph:**
```
(:Program)
  -[:body]->(:FunctionDefinition {name: "main"})
    -[:body]->(:Block {type: "block"})
```

---

## Phase 1: Universal JSON-to-Graph Transformer

### Goal

Implement the core transformer that handles any JSON schema, creating graph nodes and edges (from JSON keys) based on JSON structure alone.

### Scope

#### Phase 1A: Research & Planning (DONE)
- [x] Document current tree-sitter pattern usage across all languages
- [x] Identify all AST node types for each supported language
- [x] Map AST relationships to potential graph edges
- [x] Define node/edge schema for full AST transformation

#### Phase 1B: Architecture Design (DONE)
- [x] Design JSON-to-graph transformation rules
- [x] Define contain map concept for layer linking
- [x] Plan incremental migration path (backward compatible)
- [x] Design adapter pattern for various JSON sources

#### Phase 1C: Core Implementation
- [ ] Implement JsonToGraphTransformer (universal)
- [ ] Implement tree-sitter adapter → JSON
- [ ] Validate with tree-sitter JSON output (any language)
- [ ] Measure performance impact
- [ ] Remove legacy tree-sitter integration from GraphBuilder
- [ ] Update CLI/server/handlers to use new transformer

---

## Phase 2: Multi-Layer Graph Integration

### Goal

Transform multiple JSON sources into connected graph layers using contain maps.

### Scope

#### Phase 2A: Filesystem Layer
- [ ] Implement filesystem-to-graph transformer
- [ ] Create filesystem JSON structure
- [ ] Test filesystem → graph transformation

#### Phase 2B: AST Layer Integration
- [ ] Add AST layer with contain maps to filesystem
- [ ] Configure: File.ast → AST root
- [ ] Test cross-layer queries

#### Phase 2C: Additional Layers
- [ ] Add more layers as needed (types, dependencies, etc.)
- [ ] Unified query interface across all layers
- [ ] Performance optimization

---

## Unified Graph Schema

**Relationship types are derived from JSON keys** - each key becomes its own relationship type (e.g., `functions`, `imports`, `body`, `children`).

### Node Labels (from JSON `type` field)

**Filesystem:**
```
FilesystemRoot, Directory, File, SymLink, BinaryFile
```

**AST:**
```
Program, Module, Function, Class, Method, Statement, Expression,
Assignment, Call, Identifier, Literal, ControlFlow, etc.
```

### Relationship Types

**Relationship type = JSON key:**
```
functions - From { "functions": [...] }
imports  - From { "imports": [...] }
body     - From { "body": {...} }
children - From { "children": [...] }
metadata - From { "metadata": {...} }
```

Each JSON key defines its own relationship type - no hardcoded relationship types needed.

---

## Key Questions

1. **Adapter Structure**: How do adapters expose standard JSON format for different sources?
2. **Contain Map Configuration**: How is the linking between layers configured?
3. **Performance**: How will full JSON traversal impact indexing time?
4. **Deduplication**: How to avoid creating redundant nodes/edges with existing pattern matches?
5. **Query Patterns**: What new queries become possible with full JSON-to-graph?
6. **Incremental Updates**: How to handle JSON changes efficiently?
7. **Symlink Handling**: Follow symlinks? Create separate nodes? Circular reference prevention?
8. **Large Repositories**: Pagination/streaming for huge JSON documents?

---

## Implementation Priority

1. **Phase 1B**: Complete architecture design (DONE)
2. **Phase 1C**: Implement JSON-to-graph transformer and tree-sitter adapter
3. **Migration**: Update CLI/server/handlers to use new pipeline
4. **Phase 2**: Add filesystem layer with contain maps
5. **Validate**: Test cross-layer queries and optimize

---

## Related Files (Current - TO BE DEPRECATED/REMOVED)

- `src/codegraphcontext/tools/graph_builder.py` - Main graph builder (hybrid approach) → **Replace with JSON-to-Graph**
- `src/codegraphcontext/tools/languages/*.py` - Language-specific parsers → **Remove**
- `src/codegraphcontext/utils/tree_sitter_manager.py` - Tree-sitter wrapper → **Move to adapter**
- `src/codegraphcontext/core/database.py` - DatabaseManager (supports Neo4j/FalkorDB) → FalkorDB-only
- `src/codegraphcontext/core/jobs.py` - JobManager for tracking → Keep

## Related Files (Target - JSON-to-Graph)

- `src/codegraphcontext/tools/json_to_graph.py` - **NEW** Universal JSON-to-graph transformer
- `src/codegraphcontext/tools/contain_map.py` - **NEW** Layer linking configuration
- `src/codegraphcontext/tools/adapters/` - **NEW** Adapters for various JSON sources
  - `tree_sitter_adapter.py` - tree-sitter output → JSON
  - `filesystem_adapter.py` - filesystem walk → JSON
  - `openapi_adapter.py` - OpenAPI → JSON
  - `kubernetes_adapter.py` - K8s manifests → JSON
  - `csv_adapter.py` - CSV → JSON
- `src/codegraphcontext/core/database.py` - FalkorDB-only DatabaseManager

### Visualization

Once data is in FalkorDB, visualization is just a Cypher query away:

```python
# Generate visualization URL
from codegraphcontext.tools.visualizer import visualize_graph_query

url = visualize_graph_query("MATCH (n) RETURN n LIMIT 100")
# Opens Neo4j Browser with results
```

---

*Last updated: 2026-03-11*
