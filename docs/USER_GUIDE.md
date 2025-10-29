# User Guide

Complete guide for using CST-LSP in your Python development workflow.

## What is CST-LSP?

CST-LSP is a Language Server that adds intelligent Python refactoring capabilities to your code editor. It uses libcst (Concrete Syntax Tree) to understand and transform your code while preserving formatting, comments, and style.

## Installation

### Requirements

- **Python**: ≥3.10
- **ripgrep**: For symbol search (optional but recommended)

### Install CST-LSP

```bash
pip install cst-lsp
```

### Install Ripgrep

Ripgrep enables import resolution. Install for your platform:

```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
sudo apt install ripgrep

# Fedora
sudo dnf install ripgrep

# Windows (using Chocolatey)
choco install ripgrep

# Or using cargo (all platforms)
cargo install ripgrep
```

Verify installation:
```bash
rg --version
```

## Editor Setup

### VS Code

**Option 1: Using a Generic LSP Client**

1. Install an LSP extension (e.g., "vscode-language-server-extension")
2. Add to your `settings.json`:

```json
{
  "python.languageServer": "custom",
  "customLanguageServer.servers": {
    "cst-lsp": {
      "command": "cst_lsp",
      "args": [],
      "filetypes": ["python"]
    }
  }
}
```

**Option 2: Manual Configuration**

Create `.vscode/settings.json` in your project:

```json
{
  "python.analysis.extraPaths": ["${workspaceFolder}"],
  "cst-lsp": {
    "enabled": true,
    "command": "cst_lsp"
  }
}
```

### Neovim

**Using nvim-lspconfig**:

```lua
-- In your init.lua or lsp config file
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

-- Define cst_lsp if not already defined
if not configs.cst_lsp then
  configs.cst_lsp = {
    default_config = {
      cmd = {'cst_lsp'},
      filetypes = {'python'},
      root_dir = lspconfig.util.root_pattern('.git', 'pyproject.toml', 'setup.py'),
      settings = {},
    },
  }
end

-- Setup cst_lsp
lspconfig.cst_lsp.setup{}
```

**Key Mappings** (optional):

```lua
-- Add to your lsp on_attach function
vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, { buffer = bufnr })
vim.keymap.set('v', '<leader>ca', vim.lsp.buf.range_code_action, { buffer = bufnr })
```

### Vim (using vim-lsp)

```vim
" In your .vimrc
if executable('cst_lsp')
    au User lsp_setup call lsp#register_server({
        \ 'name': 'cst-lsp',
        \ 'cmd': {server_info->['cst_lsp']},
        \ 'allowlist': ['python'],
        \ })
endif
```

### Emacs (using lsp-mode)

```elisp
;; In your init.el
(use-package lsp-mode
  :config
  (add-to-list 'lsp-language-id-configuration '(python-mode . "python"))
  (lsp-register-client
   (make-lsp-client :new-connection (lsp-stdio-connection "cst_lsp")
                    :major-modes '(python-mode)
                    :server-id 'cst-lsp)))

(add-hook 'python-mode-hook #'lsp-deferred)
```

### Emacs (using eglot)

```elisp
;; In your init.el
(require 'eglot)
(add-to-list 'eglot-server-programs
             '(python-mode . ("cst_lsp")))

(add-hook 'python-mode-hook 'eglot-ensure)
```

## Available Refactorings

### 1. Extract Method

**What it does**: Extracts selected code into a new function with intelligent parameter and return value detection.

**When to use**:
- Code blocks that are repeated
- Complex logic that needs a descriptive name
- Functions that are too long

**How to use**:
1. Select the code you want to extract
2. Trigger code actions (Ctrl+. in VS Code, `<leader>ca` in Neovim)
3. Choose "Extract Method"
4. The selected code becomes a new function with appropriate parameters

**Example**:

Before:
```python
def calculate_total(items):
    subtotal = sum(item.price for item in items)
    tax = subtotal * 0.08
    discount = subtotal * 0.1 if subtotal > 100 else 0
    return subtotal + tax - discount
```

Select the tax and discount calculation lines, extract:

After:
```python
def calculate_total(items):
    subtotal = sum(item.price for item in items)
    tax, discount = calculate_adjustments(subtotal)
    return subtotal + tax - discount

def calculate_adjustments(subtotal):
    tax = subtotal * 0.08
    discount = subtotal * 0.1 if subtotal > 100 else 0
    return tax, discount
```

**Features**:
- ✅ Automatically detects parameters (variables used but not defined)
- ✅ Automatically detects returns (variables defined and used after)
- ✅ Preserves type annotations
- ✅ Handles instance methods, class methods, and static methods
- ✅ Supports async functions
- ❌ Cannot extract with `continue`, `break`, `yield`, `yield from`
- ❌ Module-level extraction not supported

### 2. Import Symbol

**What it does**: Adds an import statement for an undefined symbol at your cursor.

**When to use**:
- You've referenced a class/function that isn't imported
- Quick fix for import errors

**How to use**:
1. Place cursor on undefined symbol (red squiggle)
2. Trigger code actions
3. Choose "Import Symbol"

**Example**:

Before:
```python
def create_temp_file():
    path = Path("/tmp/myfile.txt")  # Path undefined
    return path
```

Place cursor on `Path`, trigger code action:

After:
```python
from pathlib import Path

def create_temp_file():
    path = Path("/tmp/myfile.txt")
    return path
```

**How it works**:
1. Searches existing imports in your project (most reliable)
2. Searches `__all__` declarations in `__init__.py` files
3. Searches top-level class/function definitions

**Features**:
- ✅ Finds symbols across entire project and Python path
- ✅ Respects `__all__` declarations
- ✅ Frequency-ranked suggestions (uses most common imports first)
- ✅ Fast (results cached per session)
- ⚠️ Requires ripgrep

### 3. Import All Missing

**What it does**: Adds imports for ALL undefined symbols in the current file.

**When to use**:
- Working on new files with many imports needed
- Cleaning up after code refactoring
- Faster than adding imports one-by-one

**How to use**:
1. Trigger code actions anywhere in file
2. Choose "Import All Missing"
3. All undefined symbols will be imported

**Example**:

Before:
```python
def process_data(filename):
    path = Path(filename)
    data = json.load(path.open())
    df = DataFrame(data)
    return df
```

Trigger "Import All Missing":

After:
```python
import json
from pathlib import Path
from pandas import DataFrame

def process_data(filename):
    path = Path(filename)
    data = json.load(path.open())
    df = DataFrame(data)
    return df
```

**Features**:
- ✅ Batch import operation
- ✅ Same intelligent search as Import Symbol
- ✅ Only appears when 2+ symbols are undefined
- ⚠️ Requires ripgrep

## Workflow Tips

### Quick Refactoring Workflow

1. **Write code quickly** without worrying about imports:
   ```python
   def analyze(data):
       df = DataFrame(data)
       result = np.mean(df['values'])
       return result
   ```

2. **Trigger "Import All Missing"** to add imports automatically

3. **Extract complex sections** into well-named functions

4. **Repeat** as your code evolves

### Keyboard-First Development

Set up key bindings for fast access:

**VS Code**:
- `Ctrl+.` (default) - Code actions
- `Ctrl+Shift+R` - Rename symbol
- `F2` - Rename

**Neovim**:
```lua
vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action)
vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename)
```

### Best Practices

1. **Extract Early, Extract Often**
   - Small functions are easier to test and reuse
   - Descriptive names improve code readability
   - Extract before refactoring gets harder

2. **Let CST-LSP Handle Imports**
   - Write code first, add imports later
   - Use "Import All Missing" for batch operations
   - Trust the frequency-ranked suggestions

3. **Preserve Your Style**
   - CST-LSP maintains your formatting
   - Comments and docstrings are preserved
   - Type annotations carried through refactorings

## Troubleshooting

### Code Action Doesn't Appear

**Problem**: "Extract Method" or other actions don't show up

**Solutions**:
1. **Check selection validity**:
   - Must be inside a function (not module-level)
   - Selected code must be valid Python
   - Cannot contain unsupported statements (continue, break, yield)

2. **Verify server is running**:
   ```bash
   # Check if cst_lsp is in PATH
   which cst_lsp

   # VS Code: Check Output → Language Server
   # Neovim: :LspInfo
   ```

3. **Check editor logs**:
   - VS Code: Developer Tools → Console
   - Neovim: `:mess` or `:LspLog`

### Symbol Finder Not Available

**Problem**: "Import Symbol" and "Import All Missing" don't appear

**Cause**: Ripgrep not installed or not in PATH

**Solutions**:
```bash
# Verify ripgrep
rg --version

# If not installed, see Installation section above

# Check PATH
echo $PATH  # Should include ripgrep location
```

### Slow Performance

**Problem**: Code actions take a long time to appear

**Solutions**:
1. **First search is slower**: Symbol search caches results, subsequent searches are faster

2. **Large project?**: Symbol finder limits to 25 results per search for performance

3. **Check ripgrep performance**:
   ```bash
   time rg "def" --json /path/to/project
   ```

4. **Reduce search scope**: Ensure `.gitignore` excludes unnecessary directories

### Import Resolution Issues

**Problem**: Wrong module imported or symbol not found

**Causes**:
1. Symbol exists in multiple modules
2. Module not in Python path
3. Symbol not exported in `__all__`

**Solutions**:
1. **Check search order**:
   - Existing project imports (most reliable)
   - `__all__` declarations
   - Top-level definitions

2. **Verify Python path**:
   ```bash
   python -c "import sys; print('\n'.join(sys.path))"
   ```

3. **Manually specify import**: If auto-import chooses wrong module, delete and write import manually

### Extract Method Limitations

**Problem**: "Extract Method" doesn't work with my code

**Known Limitations**:
- ❌ Code with `continue` or `break` statements
- ❌ Code with `yield` or `yield from`
- ❌ Module-level code (must be in function)
- ❌ Incomplete branch analysis for returns

**Workarounds**:
1. **Refactor first**: Simplify code to avoid unsupported constructs
2. **Extract smaller pieces**: Break into multiple extractions
3. **Manual extraction**: Some code may need manual refactoring

## Configuration

### Server Options

Currently CST-LSP has minimal configuration. Future versions will support:

- Python interpreter path (currently uses `sys.executable`)
- Symbol search depth
- Extract method naming conventions
- Import organization preferences

### Project-Specific Settings

Create `.cst-lsp.json` in project root (future):

```json
{
  "python_path": "/path/to/python",
  "exclude_paths": ["build/", "dist/"],
  "import_style": "from_import",
  "extract_method_prefix": "extracted_"
}
```

## Performance Characteristics

### Speed

| Operation | Speed | Notes |
|-----------|-------|-------|
| Extract Method | <100ms | Single file parse |
| Import Symbol (first) | 1-3s | Searches project + Python path |
| Import Symbol (cached) | <50ms | Results cached |
| Import All Missing | 1-5s | Multiple symbol searches |

### Memory

- **Per file**: ~5-10MB for parsed AST
- **Symbol cache**: ~1-5MB per session
- **Total**: ~20-50MB for typical projects

### Best Performance Tips

1. **Use .gitignore**: Excludes unnecessary files from search
2. **Let caches warm up**: First search slower, subsequent faster
3. **Batch imports**: Use "Import All Missing" over multiple "Import Symbol"
4. **Close unused files**: Reduces memory footprint

## Getting Help

### Documentation

- [Architecture](./ARCHITECTURE.md) - System design details
- [Adding Code Actions](./ADDING_CODE_ACTIONS.md) - Contributor guide
- [FAQ](./FAQ.md) - Common questions
- [GitHub Issues](https://github.com/yourusername/cst-lsp/issues) - Bug reports

### Community

- Report bugs: [GitHub Issues](https://github.com/yourusername/cst-lsp/issues)
- Feature requests: [GitHub Discussions](https://github.com/yourusername/cst-lsp/discussions)
- Questions: Stack Overflow with tag `cst-lsp`

### Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for:
- Development setup
- Code style guidelines
- Pull request process
- Testing requirements

## Next Steps

1. **Try Extract Method**: Select some code and refactor it
2. **Test Import Resolution**: Reference an undefined symbol and auto-import it
3. **Configure Your Editor**: Set up comfortable key bindings
4. **Explore Limitations**: Understand what CST-LSP can and cannot do
5. **Report Issues**: Help improve CST-LSP by reporting bugs

Happy refactoring! 🎉
