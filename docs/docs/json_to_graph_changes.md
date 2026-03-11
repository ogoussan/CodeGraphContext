# JSON-to-Graph Transformation: Change Plan

> **Document Type**: Change-Focused Implementation Plan  
> **Status**: Planning Phase  
> **Created**: 2026-03-11  
> **Source**: Based on `ast_to_graph_planning.md`

This document presents a **change-focused plan** for transforming the GraphBuilder from a hybrid pattern-based extractor to a pure JSON-to-Graph transformer. The focus is on **what needs to be removed**, **what needs to be added**, and the **overall goal** for each part of the system.

---

## Top-Down Approach

This plan uses a top-down approach, starting abstract and drilling down into implementation details:

1. **Level 1**: Strategic Goal (Abstract)
2. **Level 2**: System-Wide Changes
3. **Level 3**: Component-Level Changes
4. **Level 4**: File-Level Changes
5. **Level 5**: Implementation Phases

---

## Level 1: Strategic Goal (Abstract)

### Goal

Transform GraphBuilder from a **hybrid pattern-based extractor** to a **pure JSON-to-Graph transformer** that accepts any JSON source.

### Core Change

```
CURRENT: [Source Code] → tree-sitter → pattern matching → graph
TARGET:  [Any JSON]   → transformer  → graph
```

### Key Principle

> **One universal transformation mechanism handles all JSON sources.**
> 
> External adapters produce JSON; the transformer creates graphs.

### What This Enables

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

---

## Level 2: System-Wide Changes

### What Needs to Be REMOVED from GraphBuilder

| Component | Location | Reason |
|-----------|----------|--------|
| **TreeSitterParser class** | `graph_builder.py:18-91` | Moves to adapter layer |
| **Language-specific parsers** | `tools/languages/*.py` (17 files) | Replaced by JSON adapters |
| **tree-sitter dependency** | Imports in `graph_builder.py` | External tools produce JSON |
| **`_pre_scan_for_imports()`** | GraphBuilder method | External tools resolve imports |
| **`_create_all_function_calls()`** | GraphBuilder method | External tools resolve calls |
| **`_create_all_inheritance_links()`** | GraphBuilder method | External tools resolve inheritance |
| **`parse_file()` method** | GraphBuilder method | Replaced by `transform_json()` |
| **`add_file_to_graph()` method** | GraphBuilder method | Replaced by batch transform |
| **Pattern-based extraction logic** | Throughout | Replaced by universal rules |

### What Needs to Be ADDED

| Component | Location | Purpose |
|-----------|----------|---------|
| **JsonToGraphTransformer** | `tools/json_to_graph.py` (NEW) | Universal JSON-to-graph core |
| **ContainMap system** | `tools/contain_map.py` (NEW) | Layer linking configuration |
| **Adapter layer** | `tools/adapters/` (NEW directory) | Convert sources to JSON |
| **TreeSitterAdapter** | `tools/adapters/tree_sitter.py` | tree-sitter → JSON |
| **FilesystemAdapter** | `tools/adapters/filesystem.py` | filesystem → JSON |
| **FalkorDB optimization** | `core/database.py` | FalkorDB-only support |

### Architecture Shift

**Current Architecture:**
```
┌──────────────────────────────────────────────────────────────────┐
│                        GraphBuilder                               │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │ TreeSitter     │  │ Language-Specific│  │ Pattern-Based    │  │
│  │ Parser         │→ │ Parsers (17x)   │→ │ Extraction       │  │
│  └────────────────┘  └─────────────────┘  └──────────────────┘  │
│                              ↓                                    │
│                    ┌─────────────────┐                           │
│                    │ Post-Processing │                           │
│                    │ (calls, inherit)│                           │
│                    └─────────────────┘                           │
└──────────────────────────────────────────────────────────────────┘
                              ↓
                    Neo4j / FalkorDB
```

**Target Architecture:**
```
┌──────────────────────────────────────────────────────────────────┐
│                        JSON INPUT SOURCES                         │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│  tree-sitter │   OpenAPI   │  Kubernetes │    CSV      │  [Any]  │
│      JSON    │     JSON    │     JSON    │     JSON    │  JSON   │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴────┬────┘
       │              │              │              │           │
       └──────────────┴──────────────┴──────────────┴───────────┘
                                  ↓
                    ┌───────────────────────────┐
                    │  JsonToGraphTransformer   │
                    │  (Single Universal Core)  │
                    └───────────────────────────┘
                                  ↓
                           FalkorDB Graph
```

---

## Level 3: Component-Level Changes

### 3.1 GraphBuilder Transformation

#### REMOVALS (from `graph_builder.py`)

```python
# REMOVE: Entire TreeSitterParser class (lines ~18-91)
class TreeSitterParser:
    def __init__(self, language_name: str):
        # REMOVE: All tree-sitter initialization
        pass
    
    def parse(self, path: Path, **kwargs) -> Dict:
        # REMOVE: Delegation to language-specific parsers
        pass

# REMOVE: tree-sitter imports
from tree_sitter import Language, Parser
from ..utils.tree_sitter_manager import get_tree_sitter_manager

# REMOVE: All language-specific parser imports
from .languages.python import PythonTreeSitterParser
from .languages.javascript import JavascriptTreeSitterParser
from .languages.go import GoTreeSitterParser
# ... (17 language imports total)

# REMOVE: Methods relying on tree-sitter
def parse_file(self, path: Path, language: str, ...) -> Dict:
    # Pattern-based extraction using tree-sitter queries
    # REMOVE entirely

def _pre_scan_for_imports(self, files: list) -> Dict:
    # Import resolution heuristics
    # REMOVE entirely

def _create_all_function_calls(self, file_nodes: list) -> None:
    # Post-process CALLS relationships
    # REMOVE entirely

def _create_all_inheritance_links(self, class_nodes: list) -> None:
    # Post-process INHERITS relationships
    # REMOVE entirely

def add_file_to_graph(self, file_data: Dict, ...) -> None:
    # Direct graph construction from parsed data
    # REMOVE entirely (replaced by transformer)
```

#### ADDITIONS (to `graph_builder.py`)

```python
# ADD: New imports
from .json_to_graph import JsonToGraphTransformer
from .adapters.tree_sitter import TreeSitterAdapter
from .adapters.filesystem import FilesystemAdapter

# ADD: New architecture
class GraphBuilder:
    def __init__(self, db_manager, job_manager, loop):
        self.db_manager = db_manager
        self.job_manager = job_manager
        self.loop = loop
        self.driver = db_manager.get_driver()
        
        # NEW: Transformer and adapters
        self.transformer = JsonToGraphTransformer(db_manager)
        self.ts_adapter = TreeSitterAdapter()
        self.fs_adapter = FilesystemAdapter()
    
    # NEW: Main entry point
    def build_graph_from_json(self, json_data: dict, root_label: str = "Root") -> None:
        """
        Transform JSON directly to graph.
        
        Args:
            json_data: JSON structure from any source
            root_label: Root node label for the graph
        """
        self.transformer.transform(json_data, root_label)
    
    # NEW: Adapter-based workflow (replaces old parse_file flow)
    async def build_graph_from_path_async(self, path: Path, language: str) -> None:
        """
        Use adapter to convert source to JSON, then transform.
        
        Args:
            path: Path to source file or directory
            language: Programming language name
        """
        # 1. Adapter converts source to JSON
        json_data = self.ts_adapter.parse_file(path, language)
        
        # 2. Transformer converts JSON to graph
        self.transformer.transform(json_data, root_label="Repository")
    
    # NEW: Filesystem-based workflow
    async def build_graph_from_directory_async(self, path: Path) -> None:
        """
        Build graph from filesystem structure.
        
        Args:
            path: Directory path to scan
        """
        # 1. Filesystem adapter produces JSON
        json_data = self.fs_adapter.scan_directory(path)
        
        # 2. Transformer converts JSON to graph
        self.transformer.transform(json_data, root_label="FilesystemRoot")
```

---

### 3.2 New Components (ADDITIONS)

#### JsonToGraphTransformer (`tools/json_to_graph.py`)

```python
"""
Universal JSON-to-Graph transformer for FalkorDB.

This module provides a single, unified mechanism for transforming
any JSON structure into a graph database representation.

Key Principles:
1. Objects → Nodes (label from `type` field or key name)
2. Nested objects → Relationships (key becomes relationship type)
3. Primitive values → Node properties
4. Arrays → Multiple relationships or list properties
"""

from typing import Any, Dict, List, Optional
from pathlib import Path
from falkordb import FalkorDB

from ..core.database import DatabaseManager


class JsonToGraphTransformer:
    """Universal JSON-to-Graph transformer for FalkorDB."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the transformer.
        
        Args:
            db_manager: DatabaseManager instance for FalkorDB connection
        """
        self.db_manager = db_manager
        self.driver = db_manager.get_driver()
        self._node_id_counter = 0
    
    def transform(self, json_data: dict, root_label: str = "Root") -> None:
        """
        Transform JSON structure to graph nodes and edges.
        
        Args:
            json_data: JSON structure to transform
            root_label: Label for the root node
        """
        # 1. Generate node IDs for all objects
        nodes = self._generate_node_ids(json_data)
        
        # 2. Create nodes from JSON objects
        node_queries = self._create_node_queries(nodes)
        
        # 3. Create edges from JSON relationships
        edge_queries = self._create_edge_queries(nodes)
        
        # 4. Batch write to FalkorDB with pipelining
        self._batch_write(node_queries, edge_queries)
    
    def transform_batch(self, json_list: List[dict], root_label: str = "Root") -> None:
        """
        Transform multiple JSON objects.
        
        Args:
            json_list: List of JSON structures to transform
            root_label: Label for root nodes
        """
        for json_data in json_list:
            self.transform(json_data, root_label)
    
    def _generate_node_ids(self, obj: Any, parent_path: str = "") -> Dict:
        """
        Recursively generate unique IDs for all objects.
        
        Args:
            obj: JSON object or value
            parent_path: Path in parent structure for key generation
            
        Returns:
            Dict with node IDs and metadata
        """
        # Implementation
        pass
    
    def _create_node_queries(self, nodes: Dict) -> List[str]:
        """Generate Cypher CREATE queries for nodes."""
        # Implementation
        pass
    
    def _create_edge_queries(self, nodes: Dict) -> List[str]:
        """Generate Cypher MATCH/CREATE queries for relationships."""
        # Implementation
        pass
    
    def _batch_write(self, node_queries: List[str], edge_queries: List[str]) -> None:
        """
        Write all queries to FalkorDB using pipelining.
        
        Args:
            node_queries: List of node creation queries
            edge_queries: List of relationship creation queries
        """
        with self.driver.pipeline() as pipeline:
            for query in node_queries + edge_queries:
                pipeline.run_query(query)
```

#### ContainMap (`tools/contain_map.py`)

```python
"""
Contain Map system for linking graph layers.

Contain maps define how leaf nodes or properties in one graph layer
connect to the root of another graph layer.

Example: Filesystem → AST Connection
  - Filesystem layer creates File nodes
  - AST layer creates Program nodes
  - Contain map: "files[].ast" → AST root node
  - Result: (:File) -[:ast]-> (:Program)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ContainMap:
    """Defines how to link a parent graph layer to a child graph layer."""
    
    source_path: str
    """JSON path to source node/property (e.g., 'files[].ast')"""
    
    target_root: str
    """Root node label/type of the target graph (e.g., 'Program')"""
    
    relationship_name: Optional[str] = None
    """Name of the relationship to create (defaults to last path segment)"""
    
    def __post_init__(self):
        if self.relationship_name is None:
            # Extract from path: "files[].ast" → "ast"
            self.relationship_name = self.source_path.split(".")[-1].replace("[]", "")


class ContainMapRegistry:
    """Registry of contain maps for multi-layer graph construction."""
    
    def __init__(self):
        self._maps: Dict[str, List[ContainMap]] = {}
    
    def register(self, layer_name: str, contain_map: ContainMap) -> None:
        """Register a contain map for a layer."""
        if layer_name not in self._maps:
            self._maps[layer_name] = []
        self._maps[layer_name].append(contain_map)
    
    def get_maps(self, layer_name: str) -> List[ContainMap]:
        """Get all contain maps for a layer."""
        return self._maps.get(layer_name, [])
    
    def apply_links(self, layer_name: str, transformer: "JsonToGraphTransformer") -> None:
        """
        Apply contain map links between layers.
        
        Args:
            layer_name: Name of the layer to apply links for
            transformer: Transformer instance to use for link creation
        """
        for contain_map in self.get_maps(layer_name):
            self._create_layer_links(contain_map, transformer)
    
    def _create_layer_links(self, contain_map: ContainMap, 
                            transformer: "JsonToGraphTransformer") -> None:
        """Create edges defined by contain map."""
        # Implementation
        pass


# Example: Filesystem → AST linking
FILESYSTEM_TO_AST_MAPS = [
    ContainMap(
        source_path="files[].ast",
        target_root="Program",
        relationship_name="ast"
    ),
    ContainMap(
        source_path="files[].types",
        target_root="TypeGraph",
        relationship_name="types"
    ),
]
```

#### TreeSitterAdapter (`tools/adapters/tree_sitter.py`)

```python
"""
Tree-sitter to JSON adapter.

This adapter converts tree-sitter AST output to a standardized
JSON format that can be consumed by JsonToGraphTransformer.
"""

from pathlib import Path
from typing import Dict, List, Optional
from tree_sitter import Parser, Language

from ...utils.tree_sitter_manager import TreeSitterManager


class TreeSitterAdapter:
    """Converts tree-sitter output to standardized JSON format."""
    
    def __init__(self):
        self.ts_manager = TreeSitterManager()
        self._parser_cache: Dict[str, Parser] = {}
    
    def parse_file(self, path: Path, language: str) -> dict:
        """
        Parse file with tree-sitter, return standardized JSON.
        
        Args:
            path: Path to source file
            language: Programming language name
            
        Returns:
            {
                "repository": {"path": "...", "name": "..."},
                "files": [
                    {
                        "path": "...",
                        "type": "file",
                        "functions": [...],
                        "classes": [...],
                        "imports": [...],
                        "ast": {...}  # Full AST
                    }
                ]
            }
        """
        # 1. Get parser for language
        parser = self._get_parser(language)
        
        # 2. Parse file
        with open(path, "rb") as f:
            source_code = f.read()
        
        tree = parser.parse(source_code)
        
        # 3. Convert AST to standardized JSON
        ast_json = self._tree_to_json(tree.root_node, source_code)
        
        # 4. Wrap in standard structure
        return {
            "repository": {
                "path": str(path.parent),
                "name": path.parent.name
            },
            "files": [
                {
                    "path": str(path),
                    "type": "file",
                    "ast": ast_json,
                    # Extract high-level elements for convenience
                    "functions": self._extract_functions(ast_json),
                    "classes": self._extract_classes(ast_json),
                    "imports": self._extract_imports(ast_json)
                }
            ]
        }
    
    def _tree_to_json(self, node, source_code: bytes, 
                      node_id: Optional[str] = None) -> dict:
        """
        Recursively convert tree-sitter node to JSON.
        
        Args:
            node: tree-sitter node
            source_code: Original source code bytes
            node_id: Unique node identifier
            
        Returns:
            JSON representation of node
        """
        # Implementation
        pass
    
    def _get_parser(self, language: str) -> Parser:
        """Get or create parser for language (cached)."""
        if language not in self._parser_cache:
            lang = self.ts_manager.get_language_safe(language)
            self._parser_cache[language] = Parser(lang)
        return self._parser_cache[language]
    
    def _extract_functions(self, ast_json: dict) -> List[dict]:
        """Extract function definitions from AST."""
        # Implementation
        pass
    
    def _extract_classes(self, ast_json: dict) -> List[dict]:
        """Extract class definitions from AST."""
        # Implementation
        pass
    
    def _extract_imports(self, ast_json: dict) -> List[dict]:
        """Extract import statements from AST."""
        # Implementation
        pass
```

---

### 3.3 DatabaseManager Changes

#### REMOVALS (from `core/database.py`)

```python
# REMOVE: Neo4j support
from neo4j import GraphDatabase, Driver

# REMOVE: Neo4jDriverWrapper class entirely
class Neo4jDriverWrapper:
    def __init__(self, driver: Driver, database: str = None):
        self._driver = driver
        self._database = database
    
    def session(self, **kwargs):
        if self._database and 'database' not in kwargs:
            kwargs["database"] = self._database
        return self._driver.session(**kwargs)
    
    def close(self):
        self._driver.close()

# REMOVE: All Neo4j-specific code from DatabaseManager
def validate_config(self, uri, username, password) -> Tuple[bool, Optional[str]]:
    # Neo4j validation logic
    # REMOVE
```

#### ADDITIONS (to `core/database.py`)

```python
# ADD: FalkorDB-only support
from falkordb import FalkorDB


class DatabaseManager:
    """
    Manages the FalkorDB database connection as a singleton.
    
    This pattern is crucial for performance and resource management
    in a multi-threaded or asynchronous application.
    """
    _instance = None
    _driver: Optional[FalkorDB] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Standard singleton pattern implementation."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the manager by reading credentials from environment."""
        if hasattr(self, '_initialized'):
            return
        
        self.falkordb_host = os.getenv('FALKORDB_HOST', 'localhost')
        self.falkordb_port = int(os.getenv('FALKORDB_PORT', '6379'))
        self.falkordb_database = os.getenv('FALKORDB_DATABASE', 'codegraph')
        self._initialized = True
    
    def get_driver(self) -> FalkorDB:
        """
        Gets the FalkorDB driver instance, creating it if it doesn't exist.
        
        Returns:
            FalkorDB driver instance
        """
        if self._driver is None:
            with self._lock:
                if self._driver is None:
                    info_logger(
                        f"Creating FalkorDB driver connection to "
                        f"{self.falkordb_host}:{self.falkordb_port}"
                    )
                    self._driver = FalkorDB(
                        host=self.falkordb_host,
                        port=self.falkordb_port,
                        database=self.falkordb_database
                    )
        return self._driver
    
    def close(self) -> None:
        """Close the database connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
```

---

## Level 4: File-Level Changes

| File | Status | Changes |
|------|--------|---------|
| `tools/graph_builder.py` | **REFACTOR** | Remove tree-sitter, add transformer |
| `tools/languages/python.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/javascript.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/go.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/typescript.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/cpp.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/rust.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/c.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/java.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/ruby.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/csharp.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/php.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/kotlin.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/scala.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/swift.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/haskell.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/dart.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `tools/languages/perl.py` | **DELETE** | Replaced by TreeSitterAdapter |
| `utils/tree_sitter_manager.py` | **MOVE** | To `tools/adapters/tree_sitter.py` |
| `core/database.py` | **REFACTOR** | Remove Neo4j, FalkorDB-only |
| `tools/json_to_graph.py` | **NEW** | Universal transformer |
| `tools/contain_map.py` | **NEW** | Layer linking |
| `tools/adapters/__init__.py` | **NEW** | Adapter package |
| `tools/adapters/tree_sitter.py` | **NEW** | tree-sitter → JSON |
| `tools/adapters/filesystem.py` | **NEW** | filesystem → JSON |

---

## Level 5: Implementation Phases

### Phase 1: Core Transformer (Priority: HIGH)

**Goal**: Implement the universal JSON-to-Graph transformer.

| Task | Type | Description |
|------|------|-------------|
| **ADD** `JsonToGraphTransformer` class | Addition | Core transformation logic |
| **ADD** Basic JSON-to-graph transformation rules | Addition | Object→Node, Key→Edge rules |
| **ADD** FalkorDB batch write optimization | Addition | Pipelined writes |
| **ADD** Node ID generation strategy | Addition | UUID or path-based IDs |
| **REMOVE** None yet | — | Keep backward compatible |

**Success Criteria**:
- [ ] Can transform simple JSON to graph
- [ ] Batch writes work with FalkorDB
- [ ] Tests pass for basic transformation

---

### Phase 2: Adapter Layer (Priority: HIGH)

**Goal**: Create adapter layer for JSON source conversion.

| Task | Type | Description |
|------|------|-------------|
| **ADD** `TreeSitterAdapter` | Addition | tree-sitter → JSON |
| **ADD** `FilesystemAdapter` | Addition | filesystem → JSON |
| **MOVE** `tree_sitter_manager.py` → `adapters/` | Move | Relocate to adapter layer |
| **REMOVE** Pattern-based extraction from GraphBuilder | Removal | Replace with adapter calls |
| **REMOVE** Direct tree-sitter imports from GraphBuilder | Removal | Use adapter instead |

**Success Criteria**:
- [ ] TreeSitterAdapter produces valid JSON
- [ ] FilesystemAdapter scans directories
- [ ] GraphBuilder uses adapters instead of direct parsing

---

### Phase 3: Migration (Priority: MEDIUM)

**Goal**: Remove legacy code and complete migration.

| Task | Type | Description |
|------|------|-------------|
| **REMOVE** Language-specific parsers (`tools/languages/*.py`) | Removal | Delete 17 files |
| **REMOVE** TreeSitterParser class from GraphBuilder | Removal | Delete class |
| **REMOVE** Post-processing methods (calls, inheritance) | Removal | Delete methods |
| **REMOVE** Neo4j support from DatabaseManager | Removal | FalkorDB-only |
| **UPDATE** CLI/server/handlers | Refactor | Use new transformer API |

**Success Criteria**:
- [ ] All legacy code removed
- [ ] CLI commands work with new system
- [ ] Server endpoints functional
- [ ] Performance benchmarks met

---

### Phase 4: Multi-Layer (Priority: LOW)

**Goal**: Enable multi-layer graph integration.

| Task | Type | Description |
|------|------|-------------|
| **ADD** ContainMap system | Addition | Layer linking |
| **ADD** Cross-layer queries | Addition | Query across layers |
| **ADD** Additional adapters | Addition | OpenAPI, Kubernetes, CSV |
| **ADD** Layer configuration | Addition | Configure layer linking |

**Success Criteria**:
- [ ] Filesystem → AST linking works
- [ ] Cross-layer queries functional
- [ ] At least one additional adapter implemented

---

## Summary: Change-Focused View

### By Category

| Aspect | REMOVE | ADD |
|--------|--------|-----|
| **Parsing** | tree-sitter in core, pattern matching | Adapters produce JSON |
| **Transformation** | Language-specific logic | Universal JSON-to-Graph rules |
| **Graph Construction** | Incremental, per-file | Batch JSON transformation |
| **Database** | Neo4j + FalkorDB | FalkorDB only |
| **File Structure** | `tools/languages/*.py` (17 files) | `tools/adapters/*.py` |
| **Key Classes** | TreeSitterParser, language parsers | JsonToGraphTransformer, ContainMap |

### By Effort

| Effort Level | Tasks |
|--------------|-------|
| **High** | Implement JsonToGraphTransformer, Migrate GraphBuilder |
| **Medium** | Create adapters, Remove legacy code |
| **Low** | Add ContainMap system, Additional adapters |

### By Risk

| Risk Level | Tasks | Mitigation |
|------------|-------|------------|
| **High** | Remove Neo4j support | Keep backward compatible until Phase 3 |
| **Medium** | Delete language parsers | Ensure adapters fully functional first |
| **Low** | Add new transformer | Run parallel tests during development |

---

## Related Documents

- `ast_to_graph_planning.md` - Original planning document
- `TESTING.md` - Testing strategy
- `CONTRIBUTING.md` - Contribution guidelines

---

*Last updated: 2026-03-11*
