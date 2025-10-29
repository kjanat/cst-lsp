# Adding New Code Actions

Step-by-step guide for implementing new refactoring operations in CST-LSP.

## Prerequisites

Before adding a code action, ensure you understand:
- Python's Abstract Syntax Trees (AST)
- [libcst](https://libcst.readthedocs.io/) Concrete Syntax Trees
- The visitor pattern for tree traversal
- LSP [Code Actions](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_codeAction)

## Overview

A code action in CST-LSP consists of:
1. A class inheriting from `BaseCstLspCodeAction`
2. Validation logic (`is_valid()`)
3. Transformation logic (`refactor()`)
4. Registration in the server
5. Tests

## Step 1: Understand the Base Class

```python
from cst_lsp.code_actions.base import BaseCstLspCodeAction
from lsprotocol.types import CodeActionKind
import libcst as cst
from libcst.metadata import CodeRange

class BaseCstLspCodeAction(ABC):
    name: ClassVar[str]              # Display name in editor
    kind: ClassVar[CodeActionKind]   # LSP category

    def is_valid(self, source: str, module: cst.Module,
                 code_range: CodeRange) -> bool:
        """Check if refactoring applies to selection"""

    @abstractmethod
    def refactor(self, module: cst.Module,
                 code_range: CodeRange) -> str | None:
        """Perform transformation, return new source"""
```

**Key Points**:
- `is_valid()` should be fast (no expensive operations)
- `refactor()` returns full source code as string, or `None` on failure
- Both receive `code_range` in 1-indexed line numbers (libcst convention)
- Exceptions in `refactor()` are caught silently by the server

## Step 2: Create Your Action Class

Let's implement "Remove Unused Imports" as an example:

```python
# cst_lsp/code_actions/remove_unused_imports.py

import libcst as cst
from libcst.metadata import CodeRange, MetadataWrapper, ScopeProvider
from lsprotocol.types import CodeActionKind

from .base import BaseCstLspCodeAction


class RemoveUnusedImports(BaseCstLspCodeAction):
    """Remove import statements that are never used in the file."""

    name = "Remove Unused Imports"
    kind = CodeActionKind.SourceOrganizeImports

    def is_valid(self, source: str, module: cst.Module,
                 code_range: CodeRange) -> bool:
        """Valid if file has any imports (we'll check usage later)."""
        # Quick check: does file have import statements?
        has_imports = any(
            isinstance(stmt, (cst.Import, cst.ImportFrom))
            for stmt in module.body
        )
        return has_imports

    def refactor(self, module: cst.Module,
                 code_range: CodeRange) -> str | None:
        """Remove unused import statements."""
        # Use MetadataWrapper for scope analysis
        wrapper = MetadataWrapper(module)
        scopes = wrapper.resolve(ScopeProvider)

        # Find unused imports
        transformer = UnusedImportRemover(scopes)
        modified = module.visit(transformer)

        # Return None if no changes
        if modified.code == module.code:
            return None

        return modified.code
```

## Step 3: Implement the Transformer

Create a `CSTTransformer` to modify the AST:

```python
class UnusedImportRemover(cst.CSTTransformer):
    """Visitor that removes unused import statements."""

    def __init__(self, scopes):
        self.scopes = scopes
        self.used_names = self._collect_used_names()

    def _collect_used_names(self) -> set[str]:
        """Find all names that are actually used."""
        used = set()
        for scope in self.scopes.values():
            if scope is None:
                continue
            for access in scope.accesses:
                if len(access.referents) > 0:  # Has definition
                    used.add(access.node.value)
        return used

    def leave_Import(self, original: cst.Import,
                     updated: cst.Import) -> cst.Import | cst.RemovalSentinel:
        """Remove import if all names unused."""
        # Check each imported name
        for name in original.names:
            if isinstance(name, cst.ImportAlias):
                # Use alias if present, otherwise module name
                check_name = name.asname.name.value if name.asname else name.name.value
                if check_name in self.used_names:
                    return updated  # Keep this import

        # All names unused, remove the import
        return cst.RemovalSentinel.REMOVE

    def leave_ImportFrom(self, original: cst.ImportFrom,
                         updated: cst.ImportFrom) -> cst.ImportFrom | cst.RemovalSentinel:
        """Remove from-import if all names unused."""
        if isinstance(original.names, cst.ImportStar):
            return updated  # Keep wildcard imports

        # Filter to used names only
        used_imports = [
            name for name in original.names
            if isinstance(name, cst.ImportAlias) and
               (name.asname.name.value if name.asname else name.name.value) in self.used_names
        ]

        if not used_imports:
            return cst.RemovalSentinel.REMOVE
        elif len(used_imports) < len(original.names):
            # Some unused, update import list
            return updated.with_changes(names=used_imports)
        else:
            return updated  # All used, keep as-is
```

## Step 4: Register in Server

Add your code action to the server initialization:

```python
# cst_lsp/server.py

from cst_lsp.code_actions.remove_unused_imports import RemoveUnusedImports

class CstLspServer(LanguageServer):
    async def initialize(self, params: lsp.InitializeParams):
        self.transformations = [
            ExtractMethod(),
            RemoveUnusedImports(),  # Add your action
            # ... other actions
        ]
```

## Step 5: Write Tests

Create test file following the marker pattern:

```python
# tests/code_actions/test_remove_unused_imports.py

import textwrap
from cst_lsp.code_actions.remove_unused_imports import RemoveUnusedImports
from tests.helpers import refactor_code


def test_removes_unused_import():
    source = textwrap.dedent("""
        import os
        import sys  # unused

        def main():
            print(os.name)
    """)

    action = RemoveUnusedImports()
    result = refactor_code(source, action)

    assert "import os" in result
    assert "import sys" not in result


def test_keeps_used_import():
    source = textwrap.dedent("""
        import os

        def main():
            return os.name
    """)

    action = RemoveUnusedImports()
    result = refactor_code(source, action)

    assert "import os" in result


def test_partial_from_import():
    source = textwrap.dedent("""
        from pathlib import Path, PurePath

        def main():
            return Path("/tmp")
    """)

    action = RemoveUnusedImports()
    result = refactor_code(source, action)

    assert "from pathlib import Path" in result
    assert "PurePath" not in result
```

## Common Patterns

### Using Metadata Providers

libcst's `MetadataWrapper` provides position and scope information:

```python
from libcst.metadata import MetadataWrapper, PositionProvider, ScopeProvider

# Position information
wrapper = MetadataWrapper(module)
positions = wrapper.resolve(PositionProvider)
for node, position in positions.items():
    print(f"{node}: Line {position.start.line}")

# Scope information
scopes = wrapper.resolve(ScopeProvider)
for scope in scopes.values():
    if scope:
        print(f"Scope: {scope.name}")
        for access in scope.accesses:
            print(f"  Accesses: {access.node.value}")
```

### Checking if Selection is Within Function

```python
from libcst.metadata import ParentNodeProvider

def is_within_function(module: cst.Module, code_range: CodeRange) -> bool:
    wrapper = MetadataWrapper(module)
    parents = wrapper.resolve(ParentNodeProvider)

    # Find node at selection
    for node in module.walk():
        position = wrapper.resolve(PositionProvider).get(node)
        if position and code_ranges_intersect(position, code_range):
            # Walk up parent chain
            current = node
            while current in parents:
                if isinstance(parents[current], cst.FunctionDef):
                    return True
                current = parents[current]

    return False
```

### Preserving Type Annotations

```python
def preserve_annotations(original: cst.FunctionDef) -> cst.FunctionDef:
    # Keep return type annotation
    new_func = cst.FunctionDef(
        name=cst.Name("new_function"),
        params=original.params,  # Includes type annotations
        body=original.body,
        returns=original.returns,  # Return type annotation
    )
    return new_func
```

### Handling Async Functions

```python
def make_async_if_needed(func: cst.FunctionDef,
                         should_be_async: bool) -> cst.FunctionDef:
    if should_be_async:
        return func.with_changes(
            asynchronous=cst.Asynchronous(
                whitespace_after=cst.SimpleWhitespace(" ")
            )
        )
    return func
```

## Testing Best Practices

### Use Marker-Based Ranges

```python
def test_with_markers():
    source = '''
    def foo():
        # start
        x = 1
        y = 2
        # end
        return x + y
    '''
    result = refactor_with_comments(source, ExtractMethod())
    assert "def new_function" in result
```

### Test Edge Cases

Always test:
- Empty selections
- Selections with syntax errors
- Selections at module boundaries
- Nested structures (functions within functions)
- Multiple occurrences
- Comments and docstrings preservation

### Test Error Paths

```python
def test_invalid_selection_returns_none():
    source = "x = 1"  # Not in a function
    action = ExtractMethod()

    # Should not raise, should return None
    result = action.refactor(cst.parse_module(source), CodeRange(...))
    assert result is None
```

## Common Pitfalls

### 1. Forgetting to Use MetadataWrapper

❌ **Wrong**:
```python
def refactor(self, module, code_range):
    # This won't have metadata!
    transformer = MyTransformer()
    return module.visit(transformer).code
```

✅ **Right**:
```python
def refactor(self, module, code_range):
    wrapper = MetadataWrapper(module)
    transformer = MyTransformer()
    modified = wrapper.visit(transformer)
    return modified.code
```

### 2. Not Handling Whitespace

libcst preserves all whitespace. Be explicit:

```python
# Creating nodes
cst.Name("foo")  # Wrong - no whitespace handling

cst.Name(
    value="foo",
    lpar=[],  # No left parens
    rpar=[],  # No right parens
)  # Right
```

### 3. Modifying Without with_changes()

❌ **Wrong**:
```python
node.name = cst.Name("new_name")  # libcst nodes are immutable!
```

✅ **Right**:
```python
updated = node.with_changes(name=cst.Name("new_name"))
```

### 4. Index Confusion

LSP uses 0-indexed lines/columns, libcst uses 1-indexed:

```python
# Server converts for you
lsp_range = params.range  # 0-indexed
code_range = CodeRange(
    CodePosition(lsp_range.start.line + 1, lsp_range.start.character),
    CodePosition(lsp_range.end.line + 1, lsp_range.end.character),
)  # 1-indexed
```

## Debugging Tips

### 1. Print the CST

```python
module = cst.parse_module(source)
print(module)  # Shows full CST structure
```

### 2. Use code attribute

```python
node = cst.parse_expression("foo.bar.baz")
print(node.code)  # "foo.bar.baz"
```

### 3. Test Transformations Independently

```python
# Test transformer without full server
module = cst.parse_module("def foo(): pass")
transformer = MyTransformer()
result = module.visit(transformer)
print(result.code)
```

### 4. Check Metadata Resolution

```python
wrapper = MetadataWrapper(module)
print("Available metadata:", wrapper.resolve_many([
    PositionProvider,
    ScopeProvider,
    # ... others
]))
```

## Performance Considerations

### Be Efficient in is_valid()

This is called for every code action request:

```python
# Fast validation
def is_valid(self, source, module, code_range):
    # Quick syntactic checks
    return "import" in source

# Slow validation (avoid)
def is_valid(self, source, module, code_range):
    # Full scope analysis on every request!
    wrapper = MetadataWrapper(module)
    scopes = wrapper.resolve(ScopeProvider)
    # ...expensive computation...
```

### Cache Expensive Computations

```python
class MyAction(BaseCstLspCodeAction):
    def __init__(self):
        self._cache = {}

    def refactor(self, module, code_range):
        key = (id(module), code_range)
        if key not in self._cache:
            self._cache[key] = expensive_computation()
        return self._cache[key]
```

### Limit Scope of Analysis

Only analyze what you need:

```python
# Only parse selected lines
lines = source.splitlines()
selected = "\n".join(lines[start:end])
mini_module = cst.parse_module(selected)  # Smaller AST
```

## Next Steps

1. Review existing code actions in `cst_lsp/code_actions/`
2. Study libcst's [Codemods Tutorial](https://libcst.readthedocs.io/en/latest/codemods_tutorial.html)
3. Read [LSP Code Action spec](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_codeAction)
4. Contribute your code action via pull request!

## Resources

- [libcst API Documentation](https://libcst.readthedocs.io/en/latest/api.html)
- [libcst Matchers](https://libcst.readthedocs.io/en/latest/matchers_tutorial.html)
- [Python AST Module](https://docs.python.org/3/library/ast.html)
- [CST-LSP Architecture](./ARCHITECTURE.md)
