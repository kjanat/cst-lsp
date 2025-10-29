# CST-LSP

A Language Server Protocol (LSP) implementation for Python refactoring operations powered by [libcst](https://github.com/Instagram/LibCST). Transform your Python code with intelligent, structure-aware refactorings directly in your editor.

## Features

- **Extract Method**: Automatically extracts selected code into a new function with intelligent parameter and return value detection
  - Preserves type annotations
  - Handles async/await and generators
  - Supports instance, class, and static methods
  - Smart variable tracking for minimal parameters

- **Import Resolution**: Automatically adds missing imports for undefined symbols
  - Single symbol import at cursor
  - Bulk import for all undefined symbols in file
  - Fast project-wide symbol search using ripgrep
  - Respects `__all__` declarations and existing patterns

- **Structure Preservation**: Uses libcst's Concrete Syntax Tree to maintain formatting, comments, and code style

## Installation

```bash
pip install cst-lsp
```

### Requirements

- Python ≥3.10
- [ripgrep](https://github.com/BurntSushi/ripgrep) (for symbol search)

Install ripgrep:
```bash
# macOS
brew install ripgrep

# Ubuntu/Debian
apt install ripgrep

# Fedora
dnf install ripgrep

# Windows
choco install ripgrep
```

## Editor Setup

### VS Code

Install a generic LSP client extension or configure manually in `settings.json`:

```json
{
  "python.languageServer": "cst-lsp",
  "cst-lsp.serverPath": "cst_lsp"
}
```

### Neovim

Using [nvim-lspconfig](https://github.com/neovim/nvim-lspconfig):

```lua
require('lspconfig').cst_lsp.setup{}
```

### Other Editors

CST-LSP follows the standard LSP protocol. Configure your editor to run `cst_lsp` as a language server for Python files.

See [docs/EDITOR_SETUP.md](docs/EDITOR_SETUP.md) for detailed setup instructions.

## Quick Start

1. **Extract Method**: Select code in a function, trigger code actions (Ctrl+. in VS Code), choose "Extract Method"
   ```python
   def example():
       # Select these lines
       x = calculate_value()
       result = x * 2
       return result

   # Becomes:
   def example():
       return new_function()

   def new_function():
       x = calculate_value()
       result = x * 2
       return result
   ```

2. **Import Symbol**: Place cursor on undefined name, trigger code actions, choose "Import symbol"
   ```python
   def example():
       path = Path("/tmp")  # Path is undefined

   # Becomes:
   from pathlib import Path

   def example():
       path = Path("/tmp")
   ```

## Architecture

CST-LSP processes refactoring requests through the following pipeline:

```
Editor Selection → LSP Request → Parse with libcst → Transform → Diff → TextEdits → Editor
```

Key components:
- **Server** (`cst_lsp/server.py`): LSP protocol handler using [pygls](https://github.com/openlawlibrary/pygls)
- **Code Actions** (`cst_lsp/code_actions/`): Refactoring transformations using libcst visitors
- **Symbol Finder** (`cst_lsp/symbols/`): Fast symbol discovery via ripgrep
- **Variable Collector** (`cst_lsp/code_actions/variable_collector.py`): Scope analysis for parameter inference

See [CLAUDE.md](CLAUDE.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/cst-lsp.git
cd cst-lsp

# Install with dev dependencies
pip install -e ".[dev]"
```

### Commands

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=cst_lsp --cov-report=html

# Type checking
pyright

# Linting
ruff check

# Format code
ruff format
```

### Contributing

Contributions are welcome! See [docs/ADDING_CODE_ACTIONS.md](docs/ADDING_CODE_ACTIONS.md) for a guide on adding new refactorings.

## Known Limitations

- Extract method doesn't support:
  - `continue`, `break`, `yield`, `yield from` statements
  - Module-level code extraction
  - Incomplete branch analysis for return statements
- Import resolution requires ripgrep for symbol search

See our [issue tracker](https://github.com/yourusername/cst-lsp/issues) for planned improvements.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with:
- [libcst](https://github.com/Instagram/LibCST) - Concrete Syntax Tree manipulation
- [pygls](https://github.com/openlawlibrary/pygls) - Language Server Protocol framework
- [ripgrep](https://github.com/BurntSushi/ripgrep) - Fast text search
