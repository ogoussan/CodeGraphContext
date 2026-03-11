# Graph Builder

The `GraphBuilder` module is the core component responsible for building and managing the Neo4j code graph. It parses source code files using tree-sitter, extracts code elements (functions, classes, variables, etc.), and creates relationships between them in the graph database.

## Overview

**Location**: `src/codegraphcontext/tools/graph_builder.py`

**Primary Responsibilities**:
- Parse source code files using tree-sitter
- Extract code elements and metadata
- Build the code graph in Neo4j/FalkorDB
- Manage repository, file, and code element nodes
- Create relationships (CONTAINS, CALLS, INHERITS, IMPORTS, etc.)

## Architecture

### TreeSitterParser

A language-agnostic parser wrapper that:
- Initializes language-specific parsers
- Delegates parsing to language-specific implementations
- Supports 18+ programming languages

**Supported Languages**:
- Python, JavaScript/TypeScript, Go
- C, C++, Rust, Java
- Ruby, C#, PHP, Kotlin, Scala
- Swift, Haskell, Dart, Perl

### GraphBuilder

The main class that orchestrates graph construction:

```python
class GraphBuilder:
    def __init__(self, db_manager, job_manager, loop):
        self.db_manager = db_manager  # Database connection
        self.job_manager = job_manager  # Job tracking
        self.loop = loop  # Event loop
        self.parsers = {...}  # Language-specific parsers
```

## Key Methods

### Database Schema Management

#### `create_schema()`

Creates Neo4j constraints and indexes for efficient querying:

**Node Constraints**:
- `Repository` - Unique by `path`
- `File` - Unique by `path`
- `Directory` - Unique by `path`
- `Function` - Unique by `(name, path, line_number)`
- `Class` - Unique by `(name, path, line_number)`
- `Trait`, `Interface`, `Macro`, `Variable`, `Module`
- `Struct`, `Enum`, `Union`, `Annotation`, `Record`, `Property`

**Indexes**:
- Language attribute indexes for Function, Class, Annotation
- Full-text search index for code elements (name, source, docstring)
- FalkorDB-specific full-text indexes (when using FalkorDB backend)

### Repository & File Management

#### `add_repository_to_graph(repo_path, is_dependency)`

Adds a repository node to the graph:
```python
# Creates: (:Repository {path: "/path/to/repo", name: "repo", is_dependency: false})
```

#### `add_file_to_graph(file_data, repo_name, imports_map)`

Adds a file and its contents in a single transaction:

**Operations**:
1. Creates `File` node with path and metadata
2. Builds directory hierarchy with `CONTAINS` relationships
3. Creates code element nodes (functions, classes, variables, etc.)
4. Links elements to their containing file
5. Processes imports and creates `IMPORTS` relationships
6. Handles nested functions with `CONTAINS` relationships
7. Creates class-method relationships

**Supported Elements**:
```python
item_mappings = [
    (functions, 'Function'),
    (classes, 'Class'),
    (traits, 'Trait'),
    (variables, 'Variable'),
    (interfaces, 'Interface'),
    (macros, 'Macro'),
    (structs, 'Struct'),
    (enums, 'Enum'),
    (unions, 'Union'),
    (records, 'Record'),
    (properties, 'Property'),
    (modules, 'Module'),
]
```

#### `delete_file_from_graph(path)`

Deletes a file and all its contained elements:
- Removes file node and all contained elements
- Cleans up empty parent directories

#### `delete_repository_from_graph(repo_path)`

Deletes a repository and all its contents:
- Returns `True` if deleted, `False` if not found

#### `update_file_in_graph(path, repo_path, imports_map)`

Updates a single file's nodes:
1. Deletes existing file from graph
2. Re-parses and re-adds if file exists

### Parsing

#### `parse_file(repo_path, path, is_dependency)`

Parses a file with the appropriate language parser:

**Returns**:
```python
{
    "path": "/path/to/file.py",
    "repo_path": "/path/to/repo",
    "functions": [...],
    "classes": [...],
    "imports": [...],
    "variables": [...],
    # Or on error:
    "error": "Error message"
}
```

**Configuration**:
- `INDEX_SOURCE`: Controls whether source code is stored in the graph
- Respects `.cgcignore` file for file filtering

### Import Resolution

#### `_pre_scan_for_imports(files)`

Performs a pre-scan to build an imports map for cross-file resolution:

**Process**:
1. Groups files by language/extension
2. Delegates to language-specific pre-scan modules
3. Returns a map of symbol names to file paths

**Example**:
```python
imports_map = {
    "MyClass": ["/path/to/myclass.py"],
    "utils.helper": ["/path/to/utils/helper.py"],
}
```

### Relationship Creation

#### `_create_function_calls(session, file_data, imports_map)`

Creates `CALLS` relationships between functions:

**Resolution Logic**:
1. **Local context**: Check for `self`, `this`, `super`, `cls` keywords
2. **Local names**: Check if called name exists in same file
3. **Inferred types**: Use type inference if available
4. **Imports map**: Resolve using pre-scanned imports
5. **Fallback**: Use global candidate resolution

**Features**:
- Handles method calls on `self`/`this`
- Resolves chained calls (`self.graph_builder.method()`)
- Tracks call arguments and line numbers
- Supports external call resolution skipping via `SKIP_EXTERNAL_RESOLUTION` config

#### `_create_all_function_calls(all_file_data, imports_map)`

Batch processes function calls for all files after initial parsing.

#### `_create_inheritance_links(session, file_data, imports_map)`

Creates `INHERITS` relationships for class inheritance:

**Resolution**:
- Handles qualified names (`module.Class`)
- Resolves imported base classes
- Supports same-file inheritance

#### `_create_csharp_inheritance_and_interfaces(session, file_data, imports_map)`

C#-specific handling for:
- `INHERITS` relationships (class inheritance)
- `IMPLEMENTS` relationships (interface implementation)
- Supports classes, structs, records, and interfaces

### Graph Building Pipeline

#### `build_graph_from_path_async(path, is_dependency, job_id)`

Main async method for building the graph from a path:

**Process**:
1. **SCIP Indexer** (optional): If `SCIP_INDEXER=true`, uses SCIP for precise indexing
2. **Repository Setup**: Adds repository node
3. **File Discovery**: Finds all supported files, respecting `.cgcignore` and `IGNORE_DIRS`
4. **Pre-scan**: Builds imports map for cross-file resolution
5. **Parse & Add**: Parses each file and adds to graph
6. **Post-processing**: Creates inheritance and function call relationships

**Configuration**:
- `SCIP_INDEXER`: Enable SCIP-based indexing (experimental)
- `SCIP_LANGUAGES`: Comma-separated list of languages for SCIP
- `IGNORE_DIRS`: Comma-separated list of directories to ignore
- `.cgcignore`: Git-style ignore file for fine-grained control

**Job Tracking**:
- Updates job status (RUNNING, COMPLETED, FAILED, CANCELLED)
- Tracks progress (current_file, processed_files, total_files)
- Records errors and completion time

#### `_build_graph_from_scip(path, is_dependency, job_id, lang)`

SCIP-based indexing path (experimental):

**Steps**:
1. Run `scip-<lang>` CLI to generate `index.scip`
2. Parse SCIP index to extract nodes and references
3. Write nodes to graph using standard queries
4. Supplement with tree-sitter for source text and complexity
5. Write precise `CALLS` edges from SCIP data

**Fallback**: Gracefully falls back to tree-sitter if SCIP fails

### Utilities

#### `estimate_processing_time(path)`

Estimates processing time and file count:
- Returns `(file_count, estimated_time_seconds)`
- Uses ~0.05 seconds per file estimate (tree-sitter)
- Respects ignore patterns

#### `_name_from_symbol(symbol)`

Extracts human-readable names from SCIP symbol IDs:
```python
_name_from_symbol("rust/method().#")  # Returns "method"
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `SCIP_INDEXER` | Enable SCIP-based indexing | `false` |
| `SCIP_LANGUAGES` | Languages for SCIP indexing | `python,typescript,go,rust,java` |
| `INDEX_SOURCE` | Store source code in graph | `false` |
| `IGNORE_DIRS` | Directories to ignore | `""` |
| `SKIP_EXTERNAL_RESOLUTION` | Skip unresolved external calls | `false` |

## Graph Schema

### Node Labels

```
Repository, File, Directory
Function, Class, Trait, Interface
Variable, Module, Macro
Struct, Enum, Union
Record, Property, Annotation
Parameter
```

### Relationship Types

```
CONTAINS     - Repository→Directory→File→Elements
CALLS        - Function→Function/Class (with line_number, args, full_call_name)
INHERITS     - Class→Class
IMPLEMENTS   - Class/Struct/Record→Interface
IMPORTS      - File→Module (with alias, line_number, imported_name)
INCLUDES     - Class→Module (Ruby mixins)
HAS_PARAMETER - Function→Parameter
```

### Example Graph Pattern

```cypher
(:Repository {path: "/repo"})
  -[:CONTAINS]->(:Directory {path: "/repo/src"})
    -[:CONTAINS]->(:File {path: "/repo/src/main.py"})
      -[:CONTAINS]->(:Function {name: "main", line_number: 10})
        -[:CALLS {line_number: 15}]->(:Function {name: "helper"})
      -[:CONTAINS]->(:Class {name: "MyClass", line_number: 20})
        -[:CONTAINS]->(:Function {name: "__init__"})
        -[:INCLUDES]->(:Module {name: "MyMixin"})
```

## Error Handling

- **Parsing errors**: Returns error dict, skips file
- **Database errors**: Logged as warnings, continues processing
- **File not found**: Returns deletion confirmation
- **Job failures**: Updates job status with error details

## Performance Considerations

1. **Batch Processing**: Uses unified sessions for file operations
2. **Pre-scanning**: Builds imports map before full parsing
3. **Async Operations**: Non-blocking file processing
4. **Indexing**: Database indexes for efficient querying
5. **SCIP Integration**: Optional precise indexing for supported languages

## Usage Example

```python
from codegraphcontext.tools.graph_builder import GraphBuilder
from codegraphcontext.core.database import DatabaseManager
from codegraphcontext.core.jobs import JobManager
import asyncio

# Initialize
db_manager = DatabaseManager()
job_manager = JobManager()
loop = asyncio.get_event_loop()

builder = GraphBuilder(db_manager, job_manager, loop)

# Build graph for a repository
repo_path = Path("/path/to/repo")
await builder.build_graph_from_path_async(repo_path, is_dependency=False, job_id="job123")

# Query the graph
with builder.driver.session() as session:
    result = session.run("""
        MATCH (f:Function)-[:CALLS]->(g:Function)
        RETURN f.name, g.name
        LIMIT 10
    """)
```

## Related Documentation

- [Tree-sitter Manager](tree_sitter_manager.md) - Language parsing infrastructure
- [Database Manager](database_manager.md) - Neo4j/FalkorDB connection management
- [Job Manager](job_manager.md) - Background job tracking
- [SCIP Indexer](scip_indexer.md) - Precise code indexing (experimental)

## See Also

- [Architecture Overview](architecture.md) - System architecture
- [Supported Languages](supported_languages.md) - Language-specific features
- [Configuration Guide](configuration.md) - Configuration options
