# Editor Setup Guide

Detailed configuration instructions for integrating CST-LSP with popular code editors.

## Prerequisites

Before configuring your editor:

1. **Install CST-LSP**:
   ```bash
   pip install cst-lsp
   ```

2. **Verify installation**:
   ```bash
   which cst_lsp  # Should show path to executable
   ```

3. **Install ripgrep** (optional but recommended):
   ```bash
   # See README.md for platform-specific instructions
   rg --version
   ```

## VS Code

### Method 1: Generic LSP Extension

1. **Install Extension**:
   - Search for "LSP" or "Language Server Protocol" in Extensions
   - Or use a Python-specific LSP extension

2. **Configure Settings** (`settings.json`):
   ```json
   {
     "python.languageServer": "None",  // Disable built-in
     "[python]": {
       "editor.codeActionsOnSave": {
         "source.organizeImports": true
       }
     },
     "lsp": {
       "servers": {
         "cst-lsp": {
           "command": "cst_lsp",
           "args": [],
           "filetypes": ["python"],
           "initializationOptions": {}
         }
       }
     }
   }
   ```

### Method 2: Task-Based Launch

Create `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Start CST-LSP",
      "type": "shell",
      "command": "cst_lsp",
      "isBackground": true,
      "problemMatcher": {
        "owner": "python",
        "fileLocation": ["relative", "${workspaceFolder}"],
        "pattern": {
          "regexp": "^(.*):(\\d+):(\\d+):\\s+(warning|error):\\s+(.*)$",
          "file": 1,
          "line": 2,
          "column": 3,
          "severity": 4,
          "message": 5
        }
      }
    }
  ]
}
```

### Method 3: Using with Pylance

Run both servers simultaneously:

```json
{
  "python.languageServer": "Pylance",  // For types and completion
  "python.analysis.typeCheckingMode": "basic",

  // Add CST-LSP via extension or task
  "lsp.servers.cst-lsp": {
    "command": "cst_lsp",
    "filetypes": ["python"]
  }
}
```

### Key Bindings

Add to `keybindings.json`:

```json
[
  {
    "key": "ctrl+shift+r",
    "command": "editor.action.refactor",
    "when": "editorHasCodeActionsProvider && editorTextFocus"
  },
  {
    "key": "ctrl+.",
    "command": "editor.action.quickFix",
    "when": "editorHasCodeActionsProvider && editorTextFocus"
  }
]
```

### Workspace Settings

Create `.vscode/settings.json` in project root:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "cst-lsp.enabled": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true,
    "source.fixAll": true
  }
}
```

## Neovim

### Using nvim-lspconfig

**Install lspconfig**:
```vim
" Using vim-plug
Plug 'neovim/nvim-lspconfig'

" Using packer
use 'neovim/nvim-lspconfig'
```

**Configure in `init.lua`**:

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

-- Register cst_lsp if not already registered
if not configs.cst_lsp then
  configs.cst_lsp = {
    default_config = {
      cmd = {'cst_lsp'},
      filetypes = {'python'},
      root_dir = function(fname)
        return lspconfig.util.root_pattern(
          '.git',
          'pyproject.toml',
          'setup.py',
          'setup.cfg',
          'requirements.txt',
          'Pipfile'
        )(fname) or lspconfig.util.path.dirname(fname)
      end,
      settings = {},
      init_options = {},
    },
  }
end

-- Setup cst_lsp with custom options
lspconfig.cst_lsp.setup({
  on_attach = function(client, bufnr)
    -- Enable completion triggered by <c-x><c-o>
    vim.api.nvim_buf_set_option(bufnr, 'omnifunc', 'v:lua.vim.lsp.omnifunc')

    -- Mappings
    local bufopts = { noremap=true, silent=true, buffer=bufnr }
    vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, bufopts)
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, bufopts)
    vim.keymap.set('n', 'K', vim.lsp.buf.hover, bufopts)
    vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, bufopts)
    vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, bufopts)
    vim.keymap.set('v', '<leader>ca', vim.lsp.buf.range_code_action, bufopts)
    vim.keymap.set('n', 'gr', vim.lsp.buf.references, bufopts)
    vim.keymap.set('n', '<leader>f', function()
      vim.lsp.buf.format { async = true }
    end, bufopts)
  end,
  flags = {
    debounce_text_changes = 150,
  },
  capabilities = require('cmp_nvim_lsp').default_capabilities()  -- If using nvim-cmp
})
```

### Alternative: Manual Registration (init.vim)

```vim
if executable('cst_lsp')
    augroup LspCstLsp
        autocmd!
        autocmd User lsp_setup call lsp#register_server({
            \ 'name': 'cst-lsp',
            \ 'cmd': {server_info->['cst_lsp']},
            \ 'whitelist': ['python'],
            \ 'workspace_config': {},
            \ })
    augroup END
endif
```

### Using with Pyright

Run both servers:

```lua
-- Pyright for types and completion
lspconfig.pyright.setup({
  on_attach = on_attach,
  settings = {
    python = {
      analysis = {
        typeCheckingMode = "basic",
        autoSearchPaths = true,
        useLibraryCodeForTypes = true,
      }
    }
  }
})

-- CST-LSP for refactoring
lspconfig.cst_lsp.setup({
  on_attach = on_attach,
})
```

### Recommended Key Mappings

```lua
-- Add to your on_attach function
local function on_attach(client, bufnr)
  local bufopts = { noremap=true, silent=true, buffer=bufnr }

  -- Code actions
  vim.keymap.set('n', '<leader>ca', vim.lsp.buf.code_action, bufopts)
  vim.keymap.set('v', '<leader>ca', vim.lsp.buf.range_code_action, bufopts)

  -- Refactoring
  vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, bufopts)
  vim.keymap.set('n', '<F2>', vim.lsp.buf.rename, bufopts)

  -- Formatting
  vim.keymap.set('n', '<leader>f', function()
    vim.lsp.buf.format { async = true }
  end, bufopts)

  -- Hover documentation
  vim.keymap.set('n', 'K', vim.lsp.buf.hover, bufopts)

  -- Diagnostics
  vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, bufopts)
  vim.keymap.set('n', ']d', vim.diagnostic.goto_next, bufopts)
end
```

### Debugging LSP

```vim
:LspInfo          " Show LSP server status
:LspLog           " Show LSP server logs
:LspRestart       " Restart LSP server
```

## Vim (using vim-lsp)

### Install vim-lsp

```vim
" Using vim-plug
Plug 'prabirshrestha/vim-lsp'
Plug 'mattn/vim-lsp-settings'  " Optional: Auto-configuration
```

### Configure

```vim
" In your .vimrc
if executable('cst_lsp')
    augroup LspCstLsp
        autocmd!
        autocmd User lsp_setup call lsp#register_server({
            \ 'name': 'cst-lsp',
            \ 'cmd': {server_info->['cst_lsp']},
            \ 'allowlist': ['python'],
            \ 'workspace_config': {},
            \ })
    augroup END
endif

" Key mappings
function! s:on_lsp_buffer_enabled() abort
    setlocal omnifunc=lsp#complete
    nmap <buffer> gd <plug>(lsp-definition)
    nmap <buffer> gr <plug>(lsp-references)
    nmap <buffer> <leader>rn <plug>(lsp-rename)
    nmap <buffer> <leader>ca <plug>(lsp-code-action)
    vmap <buffer> <leader>ca <plug>(lsp-code-action)
    nmap <buffer> K <plug>(lsp-hover)
endfunction

augroup lsp_install
    autocmd!
    autocmd User lsp_buffer_enabled call s:on_lsp_buffer_enabled()
augroup END
```

## Emacs (lsp-mode)

### Install

```elisp
;; Using use-package
(use-package lsp-mode
  :ensure t
  :commands lsp
  :config
  (setq lsp-prefer-flymake nil))
```

### Configure

```elisp
;; In your init.el or .emacs
(require 'lsp-mode)

;; Register cst-lsp
(lsp-register-client
 (make-lsp-client
  :new-connection (lsp-stdio-connection "cst_lsp")
  :major-modes '(python-mode)
  :server-id 'cst-lsp
  :priority 1))

;; Enable for Python
(add-hook 'python-mode-hook #'lsp-deferred)

;; Key bindings
(define-key lsp-mode-map (kbd "C-c l a") #'lsp-execute-code-action)
(define-key lsp-mode-map (kbd "C-c l r") #'lsp-rename)
(define-key lsp-mode-map (kbd "C-c l f") #'lsp-format-buffer)
```

### With Pyright

```elisp
;; Use both servers
(setq lsp-pyright-server-command '("pyright" "--stdio"))

(add-hook 'python-mode-hook
          (lambda ()
            (require 'lsp-pyright)
            (lsp-deferred)))

;; CST-LSP automatically registered above
```

## Emacs (eglot)

### Install

```elisp
(use-package eglot
  :ensure t)
```

### Configure

```elisp
;; In your init.el
(require 'eglot)

;; Register cst-lsp
(add-to-list 'eglot-server-programs
             '(python-mode . ("cst_lsp")))

;; Auto-start eglot for Python
(add-hook 'python-mode-hook 'eglot-ensure)

;; Key bindings
(define-key eglot-mode-map (kbd "C-c l a") #'eglot-code-actions)
(define-key eglot-mode-map (kbd "C-c l r") #'eglot-rename)
(define-key eglot-mode-map (kbd "C-c l f") #'eglot-format-buffer)
```

## Sublime Text

### Install LSP Package

1. Install Package Control
2. Install "LSP" package
3. Install "LSP-pyright" (optional, for types)

### Configure

Create `LSP-cst-lsp.sublime-settings`:

```json
{
  "clients": {
    "cst-lsp": {
      "command": ["cst_lsp"],
      "enabled": true,
      "selector": "source.python",
      "initializationOptions": {}
    }
  }
}
```

### Key Bindings

Add to `Default.sublime-keymap`:

```json
[
  {
    "keys": ["ctrl+."],
    "command": "lsp_code_actions",
    "context": [{"key": "lsp.session_exists"}]
  },
  {
    "keys": ["f2"],
    "command": "lsp_symbol_rename",
    "context": [{"key": "lsp.session_exists"}]
  }
]
```

## Kate/KWrite

### Configure

1. Open Settings → Configure Kate → Plugins
2. Enable "LSP Client"
3. Settings → Configure Kate → LSP Client → User Server Settings

Add configuration:

```json
{
  "servers": {
    "python": {
      "command": ["cst_lsp"],
      "rootIndicationFileNames": ["pyproject.toml", ".git"],
      "highlightingModeRegex": "^Python$"
    }
  }
}
```

## Troubleshooting

### Server Not Starting

**Check executable**:
```bash
which cst_lsp
# Should output path like: /usr/local/bin/cst_lsp
```

**Check Python path**:
```bash
python -m pip show cst-lsp
# Should show installation location
```

**Test manually**:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | cst_lsp
# Should output LSP response
```

### No Code Actions Appearing

1. **Verify server is running**:
   - VS Code: Check Output → LSP logs
   - Neovim: `:LspInfo`
   - Vim: `:LspStatus`

2. **Check file type**: Must be `.py` file

3. **Test with simple code**:
   ```python
   def foo():
       x = 1
       return x
   ```
   Select `x = 1` and `return x`, trigger code actions.

### Multiple Servers Conflict

If running multiple Python language servers:

**VS Code**: Explicitly configure which server handles what
```json
{
  "python.languageServer": "Pylance",
  "lsp.servers.cst-lsp": {
    "initializationOptions": {
      "diagnosticsEnabled": false  // Let Pylance handle diagnostics
    }
  }
}
```

**Neovim**: Control server capabilities
```lua
lspconfig.cst_lsp.setup({
  on_attach = function(client, bufnr)
    -- Disable diagnostics for cst-lsp
    client.server_capabilities.diagnosticProvider = false
  end,
})
```

### Slow Performance

1. **Check Python path search**:
   ```bash
   python -c "import sys; print('\n'.join(sys.path))"
   # Ensure no huge directories in path
   ```

2. **Limit ripgrep scope**:
   Add `.gitignore`:
   ```
   node_modules/
   .venv/
   venv/
   __pycache__/
   *.egg-info/
   ```

3. **Monitor resource usage**:
   ```bash
   # While LSP running
   ps aux | grep cst_lsp
   ```

## Advanced Configuration

### Custom Python Interpreter

Not yet supported, but planned:

```json
{
  "cst-lsp.pythonPath": "/path/to/python",
  "cst-lsp.pythonPath": "${workspaceFolder}/.venv/bin/python"
}
```

Currently uses `sys.executable`.

### Logging

Enable debug logging:

```bash
# Set environment variable
export CST_LSP_LOG_LEVEL=debug
cst_lsp
```

### Multiple Workspace Folders

LSP protocol supports multi-root workspaces. CST-LSP searches symbols in all workspace roots.

**VS Code**: Add folders to workspace
**Neovim**: Use `workspace_folders` in setup

## Getting Help

- **Editor-specific issues**: Check editor's LSP documentation
- **CST-LSP issues**: [GitHub Issues](https://github.com/yourusername/cst-lsp/issues)
- **General LSP help**: [LSP Specification](https://microsoft.github.io/language-server-protocol/)
