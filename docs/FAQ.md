# Frequently Asked Questions

## General Questions

### What is CST-LSP?

CST-LSP is a Language Server Protocol implementation that provides intelligent Python refactoring operations. It uses libcst (Concrete Syntax Tree) to understand and transform your code while preserving formatting, comments, and code style.

### How is this different from other Python language servers?

| Feature | CST-LSP | Pyright/Pylance | Jedi |
|---------|---------|-----------------|------|
| Type checking | ❌ | ✅ | ❌ |
| Code completion | ❌ | ✅ | ✅ |
| Refactoring | ✅ | Limited | Limited |
| Format preservation | ✅ | ❌ | ❌ |
| Extract method | ✅ (smart) | ❌ | Basic |
| Import resolution | ✅ (project-wide) | Limited | Limited |

**CST-LSP focuses on refactoring**. Use it alongside Pyright/Pylance for type checking and completion.

### Can I use CST-LSP with Pyright/Pylance?

Yes! CST-LSP complements other language servers:

```json
// VS Code settings.json
{
  "python.languageServer": "Pylance",  // For types and completion
  "cst-lsp.enabled": true               // For refactoring
}
```

Most editors support multiple language servers simultaneously.

### What's the difference between AST and CST?

**AST (Abstract Syntax Tree)**:
- Represents code structure abstractly
- Loses formatting details (whitespace, comments)
- Used by Python's `ast` module
- Good for analysis, bad for transformations

**CST (Concrete Syntax Tree)**:
- Represents exact source code structure
- Preserves all formatting details
- Used by libcst
- Perfect for refactoring

**Example**:
```python
# Source code
x  =  1  # comment

# AST representation
Assign(targets=[Name('x')], value=Constant(1))
# Lost: spacing, comment

# CST representation
Assign(
    targets=[Name('x', whitespace_before=SimpleWhitespace('  '))],
    value=Constant(1, whitespace_before=SimpleWhitespace('  ')),
    trailing_whitespace=TrailingWhitespace(comment=Comment('# comment'))
)
# Preserved: all spacing, comment
```

## Installation & Setup

### Why do I need ripgrep?

Ripgrep powers the symbol search for import resolution. It's:
- **10-100x faster** than Python file walking
- **Battle-tested** and reliable
- **Widely available** across platforms

Without ripgrep:
- ✅ Extract Method still works
- ❌ Import Symbol unavailable
- ❌ Import All Missing unavailable

### Can I use CST-LSP without ripgrep?

Yes, but you'll only have Extract Method available. Import resolution features require ripgrep.

Future versions may include a pure-Python fallback (slower but no dependency).

### How do I know if CST-LSP is running?

**VS Code**:
1. Open Command Palette (Ctrl+Shift+P)
2. Run "Developer: Show Running Extensions"
3. Check Output panel → Select "CST-LSP" from dropdown

**Neovim**:
```vim
:LspInfo
```

**Test it**:
1. Open a Python file
2. Select some code in a function
3. Trigger code actions (Ctrl+.)
4. Look for "Extract Method"

## Usage Questions

### Why doesn't "Extract Method" appear?

Common reasons:

1. **Not in a function**:
   ```python
   # ❌ Module-level (not supported)
   x = 1
   y = 2

   # ✅ In a function (supported)
   def foo():
       x = 1
       y = 2
   ```

2. **Invalid Python syntax**:
   ```python
   def foo():
       # ❌ Selection has syntax error
       x = 1
       if  # incomplete
   ```

3. **Unsupported statements**:
   ```python
   def foo():
       for i in range(10):
           # ❌ Contains continue
           if i % 2:
               continue
           print(i)
   ```

4. **Selection not validated**:
   - Must select complete statements
   - Cannot select partial lines

### How does import resolution choose which module?

Three-tier search strategy, in order:

**Tier 1: Existing Imports** (most reliable)
- Searches your project for existing imports
- Frequency-ranked (most common imports first)
- Example: If 10 files import `from pathlib import Path`, that's suggested first

**Tier 2: __all__ Declarations**
- Searches `__init__.py` files for `__all__` lists
- These are explicitly exported symbols
- More reliable than searching all definitions

**Tier 3: Top-Level Definitions**
- Searches for `class X:` or `def X():` declarations
- Broadest search, may have false positives
- Last resort if not found in tiers 1-2

**Example**:
```python
# If searching for "DataFrame"
# Tier 1 finds: "from pandas import DataFrame" (used in 20 files)
# Result: Suggests pandas.DataFrame
```

### Can I customize which imports are suggested?

Not yet, but planned features:
- Project-specific import preferences
- Blocklist for certain modules
- Custom search order
- Type-based ranking (using type stubs)

Currently: Trust the frequency ranking or manually write the import you prefer.

### Why is the first symbol search slow?

**First search** (1-3 seconds):
- Ripgrep scans entire project + Python path
- Builds symbol caches
- Discovers module structure

**Subsequent searches** (<50ms):
- Results cached in memory
- Only searches for new symbols
- Much faster

**Tip**: Do a few "Import All Missing" operations early in session to warm up caches.

### Can I extract to a different module/file?

Not yet. Current behavior:
- Extracted function placed in same file
- Inserted above the original function

Planned feature: "Extract to Module" will allow:
- Extracting to existing module
- Creating new module
- Organizing related extractions

### Does Extract Method work with async code?

Yes! CST-LSP preserves async/await:

```python
async def fetch_data():
    # Select this code
    response = await client.get(url)
    data = await response.json()
    return data

# After extraction
async def fetch_data():
    return await parse_response(await client.get(url))

async def parse_response(response):
    data = await response.json()
    return data
```

✅ Supports: `async def`, `await`
❌ Doesn't support: `async for`, `async with` (yet)

## Technical Questions

### How does CST-LSP preserve code style?

CST-LSP uses libcst which maintains:
- **All whitespace** (spaces, tabs, newlines)
- **All comments** (inline, block, docstrings)
- **Formatting choices** (quotes, parentheses, trailing commas)

**Example**:
```python
# Your style
def  foo ( x , y , ) :  # weird spacing
    return   x + y   # preserved!

# After extraction still has your style
```

This is why CST-LSP uses libcst instead of Python's `ast` module.

### Can CST-LSP handle type annotations?

Yes! Type annotations are preserved and propagated:

```python
def calculate(x: int, y: int) -> int:
    # Select this
    result: int = x * 2 + y
    return result

# After extraction
def calculate(x: int, y: int) -> int:
    return compute_result(x, y)

def compute_result(x: int, y: int) -> int:
    result: int = x * 2 + y
    return result
```

Variable type annotations are preserved through VariableCollector.

### What Python versions are supported?

- **CST-LSP itself**: Python ≥3.10
- **Code being refactored**: Any Python version that libcst supports (3.7+)

You can run CST-LSP with Python 3.10+ and refactor code written for Python 3.7+.

### Does CST-LSP work with notebooks?

Not directly. LSP typically works with `.py` files.

**Workarounds**:
1. **Jupytext**: Convert notebooks to `.py` files, edit, convert back
2. **nbdev**: Develop in `.py`, generate notebooks
3. **Manual**: Copy code to `.py` file, refactor, copy back

Future: Native notebook support via cell-based LSP.

### How is performance on large codebases?

**Benchmarks** (approximate):

| Project Size | Parse Time | First Import Search | Cached Import |
|--------------|------------|---------------------|---------------|
| Small (100 files) | <100ms | 0.5s | <50ms |
| Medium (1K files) | <100ms | 1-2s | <50ms |
| Large (10K files) | <100ms | 3-5s | <50ms |

**Key insights**:
- Parse time doesn't scale with project size (only parses current file)
- Import search scales with project size but caches well
- Ripgrep is very fast even on large projects

**Performance tips**:
- Use `.gitignore` to exclude `node_modules`, `venv`, etc.
- Warm up caches early in session
- Close unused editor tabs to reduce memory

### Is CST-LSP safe for production code?

**Safety guarantees**:
- ✅ Never modifies files automatically (editor applies changes)
- ✅ Changes are atomic (all-or-nothing via TextEdits)
- ✅ Preserves code functionality (AST semantics maintained)
- ✅ Preserves formatting (CST used)
- ✅ Tested extensively (unit + integration tests)

**Recommendations**:
- Review changes before accepting (as with any refactoring)
- Use version control (git) for easy rollback
- Test after refactoring (as you should anyway)

**Known limitations**:
- Some edge cases may not handle perfectly
- Report bugs at: https://github.com/yourusername/cst-lsp/issues

## Troubleshooting

### LSP server crashed, what do I do?

1. **Check logs**:
   - VS Code: Output → CST-LSP
   - Neovim: `:LspLog`

2. **Restart server**:
   - VS Code: Reload window (Ctrl+Shift+P → "Reload Window")
   - Neovim: `:LspRestart`

3. **Report crash**:
   - Copy logs
   - File issue: https://github.com/yourusername/cst-lsp/issues
   - Include Python version, editor version, stack trace

### Imports keep suggesting wrong module

**Check search order**:
```bash
# Find where symbol is most commonly imported
rg "from .* import YourSymbol" /path/to/project
```

**Workaround**:
- Delete suggested import
- Write correct import manually
- CST-LSP will learn from your choice (next time searches existing imports first)

**Report issue** if consistently wrong:
- Include symbol name
- Expected module vs. suggested module
- Project structure (public repo if possible)

### Extract Method breaks my code

**Before reporting**:

1. **Check limitations**: Does code have `continue`, `break`, `yield`?
2. **Verify selection**: Is it complete statements?
3. **Test minimal reproduction**: Can you reproduce with simple example?

**Report with**:
- Python version
- Code before refactoring
- Code after refactoring
- What's broken
- Minimal reproduction if possible

## Contributing

### How can I add a new refactoring?

See [Adding Code Actions](./ADDING_CODE_ACTIONS.md) for complete guide.

**Quick overview**:
1. Create class inheriting `BaseCstLspCodeAction`
2. Implement `is_valid()` and `refactor()`
3. Write tests
4. Submit pull request

**Example refactorings to add**:
- Inline function (reverse of extract method)
- Rename symbol (workspace-wide)
- Move to module
- Introduce variable
- Organize imports

### What's on the roadmap?

**Near-term** (v0.2-0.3):
- Rename symbol refactoring
- Inline function
- Configuration file support
- Improved error messages

**Mid-term** (v0.4-0.6):
- Move to module refactoring
- Organize imports
- Type stub generation
- Performance optimizations

**Long-term** (v1.0+):
- Plugin system for custom refactorings
- Machine learning-based import suggestions
- Notebook support
- Multi-file refactorings

**See**: https://github.com/yourusername/cst-lsp/projects

### How do I report a bug?

**Good bug report includes**:

1. **Environment**:
   - Python version (`python --version`)
   - CST-LSP version (`pip show cst-lsp`)
   - Editor and version
   - OS

2. **Reproduction**:
   - Minimal code example
   - Steps to reproduce
   - Expected vs. actual behavior

3. **Logs** (if crash):
   - LSP server logs
   - Stack trace
   - Error messages

**Submit at**: https://github.com/yourusername/cst-lsp/issues

## More Questions?

- **Documentation**: See [User Guide](./USER_GUIDE.md) and [Architecture](./ARCHITECTURE.md)
- **GitHub**: [Issues](https://github.com/yourusername/cst-lsp/issues) and [Discussions](https://github.com/yourusername/cst-lsp/discussions)
- **Stack Overflow**: Tag with `cst-lsp`
