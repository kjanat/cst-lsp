# Architecture

Deep dive into CST-LSP's system design and implementation.

## System Overview

CST-LSP is a Language Server Protocol implementation that bridges the gap between code editors and Python refactoring operations. The architecture follows a clean separation of concerns with three main layers:

```
┌─────────────────────────────────────────────────────┐
│                  Editor (Client)                     │
│           VS Code, Neovim, Emacs, etc.              │
└────────────────────┬────────────────────────────────┘
                     │ LSP Protocol (JSON-RPC)
                     │
┌────────────────────▼────────────────────────────────┐
│              LSP Server Layer                        │
│         (cst_lsp/server.py)                         │
│  • Request handling                                  │
│  • Workspace management                              │
│  • Transformation coordination                       │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│         Transformation Layer                         │
│      (cst_lsp/code_actions/)                        │
│  • Extract Method                                    │
│  • Import Resolution                                 │
│  • Variable Analysis                                 │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│           Foundation Layer                           │
│  • libcst (CST manipulation)                        │
│  • pygls (LSP framework)                            │
│  • ripgrep (symbol search)                          │
└─────────────────────────────────────────────────────┘
```

## Core Components

### 1. LSP Server Layer (`cst_lsp/server.py`)

**Purpose**: Protocol handler and orchestration

**Key Responsibilities**:
- Accept LSP requests from editors via stdio
- Parse documents using libcst
- Coordinate transformation execution
- Convert results to LSP TextEdits
- Manage workspace state

**Flow**:
```python
Editor Request
    ↓
CstLspServer.code_action_handler()
    ↓ 1. Get document from workspace
    ↓ 2. Parse with libcst.parse_module()
    ↓ 3. Convert LSP Range → CodeRange (0→1 indexed)
    ↓ 4. For each transformation:
    ↓    • transformation.is_valid()
    ↓    • transformation.refactor()
    ↓    • string_diff_to_text_edits()
    ↓ 5. Create CodeAction objects
    ↓
Return CodeAction[] to editor
```

**string_diff_to_text_edits()**:
Critical algorithm that converts string diffs to LSP TextEdit operations:

```python
1. Split original and modified into lines
2. Use difflib.SequenceMatcher for line-level diff
3. For each operation (replace/insert/delete):
   - Calculate LSP Range (line, character positions)
   - Create TextEdit with range and new_text
4. Return list of TextEdits
```

This approach preserves formatting and allows editors to apply changes atomically.

### 2. Transformation Framework (`cst_lsp/code_actions/`)

**Base Class Pattern** (`base.py`):

```python
class BaseCstLspCodeAction(ABC):
    name: ClassVar[str]           # Display name
    kind: ClassVar[CodeActionKind]  # LSP category

    def is_valid(...) -> bool:
        """Check if refactoring applies"""

    @abstractmethod
    def refactor(...) -> str | None:
        """Perform transformation"""
```

**Key Design Decisions**:

1. **Validation Separation**: `is_valid()` checks applicability without modifying code
2. **String-Based Returns**: Transformations return full source code strings (not AST diffs)
3. **Error Handling**: Exceptions caught silently to prevent one failure from blocking others
4. **Extensibility**: New refactorings simply inherit and implement `refactor()`

### 3. Extract Method (`code_actions/extract_method.py`)

**Architecture**: State machine with visitor pattern

**Components**:

1. **FunctionExtractor** (CSTTransformer):
   - Identifies target code range within function body
   - Transforms AST to extract code into new function
   - Replaces extracted code with function call

2. **VariableCollector** (Visitor):
   - Tracks variable assignments and usages
   - Determines function parameters (used before defined)
   - Determines return values (defined and used after)
   - Preserves type annotations

3. **Configuration** (ExtractMethodConfig):
   - Target code range
   - New function name
   - Receiver context (instance/class/static method)

**Algorithm Flow**:

```
1. analyze_variables()
   → Scan selected code for variable usage patterns
   → Identify: parameters, returns, local-only variables

2. compute_call_information()
   → Determine if instance/class/static method
   → Calculate receiver parameter (self/cls/none)

3. create_new_function()
   → Build function signature with parameters
   → Add type annotations from VariableCollector
   → Handle async/generator keywords
   → Insert at appropriate indentation level

4. create_function_call()
   → Replace selected code with call
   → Pass parameters in correct order
   → Handle return value assignment if needed
```

**Challenges Addressed**:

- **Scope Analysis**: Uses libcst's MetadataWrapper with ScopeProvider
- **Type Preservation**: Maintains annotations through VariableCollector
- **Context Awareness**: Differentiates instance/class/static methods
- **Control Flow**: Limited support (no continue/break/yield)

### 4. Import Resolution (`code_actions/import_symbol.py`)

**Two-Part System**:

**ImportSymbol** - Single symbol import:
```
1. Find symbol at cursor (NameAtLocationVisitor)
2. Identify undefined symbols (ScopeProvider)
3. Search for symbol (SymbolFinder)
4. Add import (AddImportsVisitor)
```

**ImportAll** - Bulk import:
```
1. Find all undefined symbols in file
2. Search for each symbol
3. Add all imports in single operation
```

**Integration Points**:

- **libcst.ScopeProvider**: Determines undefined symbols
- **libcst.AddImportsVisitor**: Inserts imports at correct location
- **SymbolFinder**: Project-wide symbol discovery

### 5. Symbol Discovery (`symbols/symbol_finder.py`)

**Three-Tier Search Strategy**:

```
Tier 1: Existing Imports (Most Reliable)
    ↓ Search existing project imports
    ↓ Frequency-sorted by usage
    ↓
Tier 2: __all__ Declarations
    ↓ Search __init__.py files
    ↓ Explicit exports
    ↓
Tier 3: Top-Level Definitions
    ↓ Search for class/def statements
    ↓ Broadest search
```

**Implementation with Ripgrep**:

```python
# Existing imports pattern
pattern = r"import\s+...{symbol}..."
rg --json --multiline pattern root/

# __all__ pattern
pattern = r"__all__\s*=\s*.*[\"']{symbol}[\"']"
rg --json -g "__init__.py" pattern root/

# Top-level definitions
pattern = r"(?:class|def)\s+{symbol}(?:\(|:)"
rg --json pattern root/
```

**Performance Optimizations**:

- **Caching**: Three separate caches (imports, __all__, top-level)
- **Limits**: Max 25 hits per search to prevent slowdown
- **sys.path**: Searches only Python path directories
- **site-packages**: Explicitly excluded from parent traversal

**Result Processing**:

```python
# Convert file paths to module paths
/path/to/package/module.py → package.module
/path/to/package/__init__.py → package (use_parent=True)

# Validate module paths
all(part.isidentifier() for part in module_path.split('.'))
```

### 6. Variable Tracking (`code_actions/variable_collector.py`)

**Visitor Pattern for Scope Analysis**:

```python
class VariableCollector(MatcherDecoratableVisitor):
    assignments: dict[str, set[CodeRange]]  # Where assigned
    usages: dict[str, set[CodeRange]]       # Where used
    types: dict[str, cst.Annotation]        # Type annotations
```

**Tracking Logic**:

| Node Type | Assignment | Usage | Notes |
|-----------|-----------|-------|-------|
| `Name` | Context-dependent | In expression | Check parent context |
| `AnnAssign` | Yes | No | `x: int = 5` |
| `Attribute` | First element only | First element | `obj.attr` → track `obj` |
| `Subscript` | Assignment context | Expression context | `a[0]` context matters |

**Special Cases**:

1. **Attributes**: Only track first element (`obj.attr.method` → track `obj`)
2. **Subscripts**: Distinguish `a[i] = x` (assignment) from `y = a[i]` (usage)
3. **Parameters**: Marked as assignments (function signature)
4. **Type Annotations**: Stored separately, don't count as usage

**Usage in Extract Method**:

```
Variables to parameterize:
  = {variables used before defined} - {locally assigned only}

Variables to return:
  = {variables defined and used after selection}
```

## Data Flow Examples

### Example 1: Extract Method Full Flow

```python
# Original code
def foo():
    # start
    x = calculate()
    result = x * 2
    # end
    print(result)
```

**Step-by-Step**:

1. **User Selection**: Lines with `# start` to `# end` markers
2. **LSP Request**: `CodeActionParams` with range
3. **Server Parsing**:
   ```python
   module = libcst.parse_module(source)
   code_range = CodeRange(start_line+1, end_line+1)  # 0→1 indexed
   ```

4. **Validation** (`ExtractMethod.is_valid`):
   ```python
   # Check if selection is within a function
   # Check if code parses as valid Python
   ```

5. **Variable Analysis** (`VariableCollector`):
   ```python
   assignments = {'x': [line 2], 'result': [line 3]}
   usages = {'result': [line 5]}  # After selection
   # Conclusion: return 'result'
   ```

6. **Transformation** (`FunctionExtractor`):
   ```python
   def new_function():
       x = calculate()
       result = x * 2
       return result

   def foo():
       result = new_function()
       print(result)
   ```

7. **Diff Conversion** (`string_diff_to_text_edits`):
   ```python
   [
     TextEdit(range=Range(1,0 to 3,end), new_text="result = new_function()"),
     TextEdit(range=Range(0,0 to 0,0), new_text="def new_function():\n    x = calculate()\n    result = x * 2\n    return result\n\n")
   ]
   ```

8. **Editor Application**: Editor applies TextEdits atomically

### Example 2: Import Symbol Flow

```python
# Original
def example():
    path = Path("/tmp")  # Path undefined
```

**Step-by-Step**:

1. **User Trigger**: Code action at cursor on `Path`
2. **LSP Request**: `CodeActionParams` with cursor position
3. **Undefined Symbol Detection** (`ImportSymbol.undefined_symbols`):
   ```python
   # Use ScopeProvider to find symbols with no referents
   undefined = {'Path': [CodeRange(...)]}
   ```

4. **Symbol Extraction** (`get_name_at_location`):
   ```python
   # Find Name node at cursor position
   symbol = "Path"
   ```

5. **Symbol Search** (`SymbolFinder.find_symbol`):
   ```python
   # Tier 1: Search existing imports
   results = [
     SuggestedImport('pathlib', 'Path', None),  # from pathlib import Path
     SuggestedImport('pathlib', None, 'Path'),  # import pathlib as Path
   ]
   ```

6. **Import Addition** (`AddImportsVisitor`):
   ```python
   # Insert at top of file, after any existing imports
   "from pathlib import Path\n"
   ```

7. **Result**:
   ```python
   from pathlib import Path

   def example():
       path = Path("/tmp")
   ```

## Key Design Decisions

### Why libcst over ast?

**Concrete vs Abstract Syntax Trees**:

- **ast**: Abstract representation, loses formatting/comments
- **libcst**: Concrete representation, preserves all source details

**Impact**: Refactorings maintain code style and comments, critical for production code.

### Why String Diffs instead of AST Diffs?

**Alternatives Considered**:
1. Direct AST manipulation → TextEdit generation
2. Positional tracking through transformation
3. String diff approach (chosen)

**Rationale**:
- Simpler implementation and reasoning
- More reliable position tracking
- Easier debugging (can compare string outputs)
- difflib is battle-tested

**Trade-off**: Slightly less efficient, but reliability and maintainability more important.

### Why Visitor Pattern?

**Alternatives**:
- Imperative tree traversal
- Query-based node selection
- Visitor pattern (chosen)

**Rationale**:
- Idiomatic libcst approach
- Composable metadata providers (PositionProvider, ScopeProvider)
- Clear separation of concerns (one visitor per analysis type)
- Easy testing of individual visitors

### Why Ripgrep over Pure Python?

**Alternatives**:
- Python's `ast` module + file walking
- `grep` or `ag`
- Ripgrep (chosen)

**Rationale**:
- **Performance**: 10-100x faster than Python walking
- **Correctness**: Respects .gitignore naturally
- **Features**: JSON output, multiline patterns, glob support
- **Availability**: Widely installed on developer machines

**Trade-off**: External dependency, but graceful degradation (ImportSymbol disabled if missing).

## Extension Points

### Adding New Code Actions

1. **Create Transformer Class**:
   ```python
   class MyRefactoring(BaseCstLspCodeAction):
       name = "My Refactoring"
       kind = CodeActionKind.RefactorRewrite
   ```

2. **Implement is_valid()**:
   ```python
   def is_valid(self, source, module, code_range):
       # Check if refactoring applies
       return check_conditions()
   ```

3. **Implement refactor()**:
   ```python
   def refactor(self, module, code_range):
       # Transform code
       transformer = MyTransformer(code_range)
       modified = module.visit(transformer)
       return modified.code
   ```

4. **Register in Server**:
   ```python
   # server.py initialize()
   self.transformations.append(MyRefactoring())
   ```

### Adding New Symbol Finders

```python
class CustomSymbolFinder(SymbolFinder):
    def find_symbol(self, symbol: str) -> list[SuggestedImport]:
        # Custom search logic
        return results

# server.py
symbol_finder = CustomSymbolFinder.create(python_path, root)
```

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Parse module | O(n) | n = file size |
| Extract Method | O(n) | Single AST traversal |
| Find undefined symbols | O(n) | ScopeProvider traversal |
| Symbol search (ripgrep) | O(m) | m = project size, cached |
| Diff conversion | O(d) | d = number of changed lines |

### Space Complexity

| Component | Space | Notes |
|-----------|-------|-------|
| Parsed module | O(n) | AST size |
| Metadata wrappers | O(n) | Position/Scope maps |
| Symbol caches | O(s) | s = unique symbols searched |
| Transformation results | O(n) | Full source code strings |

### Optimization Strategies

1. **Symbol Search Caching**: Three-tier cache prevents redundant searches
2. **Lazy Metadata**: PositionProvider/ScopeProvider only resolved when needed
3. **Early Validation**: `is_valid()` fails fast before expensive operations
4. **Ripgrep Limits**: Max 25 hits prevents runaway searches
5. **Module Reuse**: Single parse per code action request serves all transformations

## Testing Strategy

### Unit Tests

- **Base Classes**: Validation logic, interface contracts
- **Transformers**: Input → Output verification with fixtures
- **Symbol Finder**: Mock ripgrep output, test tier fallback
- **Variable Collector**: Track assignments/usages for various patterns

### Marker-Based Testing

```python
def test_extract_method():
    source = '''
    def foo():
        # start
        x = 1
        # end
    '''
    # Markers converted to CodeRange
    result = refactor_with_comments(source, "new_func")
    assert "def new_func" in result
```

**Rationale**: Line numbers fragile, markers semantic.

### Integration Tests

- Full LSP request → response cycle
- Multiple transformations on same document
- Error handling and edge cases

## Known Limitations & Future Work

### Current Limitations

1. **Extract Method**:
   - No `continue`, `break`, `yield`, `yield from` support
   - Module-level extraction not supported
   - Incomplete branch analysis for returns

2. **Import Resolution**:
   - Requires ripgrep (no fallback)
   - Single module resolution (doesn't handle ambiguous imports)
   - No auto-organize imports

3. **Symbol Search**:
   - Basic pattern matching (no semantic analysis)
   - No type-based import suggestions
   - Doesn't respect __future__ imports

### Future Enhancements

1. **Rename Symbol**: Workspace-wide renaming with reference tracking
2. **Inline Function**: Reverse of extract method
3. **Move to Module**: Extract code to separate file
4. **Organize Imports**: Sort and group import statements
5. **Type Stub Generation**: Auto-generate .pyi files
6. **Smart Import Ranking**: ML-based import suggestion ranking

### Architecture Evolution

**Next Steps**:
1. **Plugin System**: Allow external code actions via entry points
2. **Configuration**: Per-project settings for refactoring behavior
3. **Undo Stack**: Better error recovery for failed transformations
4. **Streaming**: Handle large files without full parse
5. **Incremental Updates**: Parse only changed regions

## References

- [libcst Documentation](https://libcst.readthedocs.io/)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [pygls Framework](https://pygls.readthedocs.io/)
- [Ripgrep](https://github.com/BurntSushi/ripgrep)
