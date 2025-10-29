# Contributing to CST-LSP

Thank you for your interest in contributing to CST-LSP! This guide will help you get started.

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

**Before submitting**:
- Search existing issues to avoid duplicates
- Test with the latest version

**Good bug reports include**:
- Python version: `python --version`
- CST-LSP version: `pip show cst-lsp`
- Editor and version
- Minimal reproduction code
- Expected vs. actual behavior
- Error messages or logs

**Submit at**: https://github.com/yourusername/cst-lsp/issues

### Suggesting Features

**Before suggesting**:
- Check existing issues and discussions
- Consider if it fits CST-LSP's scope (refactoring focus)

**Good feature requests include**:
- Use case: Why is this needed?
- Examples: Show how it would work
- Alternatives: What else did you consider?

**Submit at**: https://github.com/yourusername/cst-lsp/discussions

### Contributing Code

#### Development Setup

1. **Fork and clone**:
   ```bash
   git clone https://github.com/yourusername/cst-lsp.git
   cd cst-lsp
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install ripgrep** (for testing import resolution):
   ```bash
   # See README.md for platform-specific instructions
   ```

5. **Verify setup**:
   ```bash
   pytest
   pyright
   ruff check
   ```

#### Development Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**:
   - Write code
   - Add tests
   - Update documentation

3. **Run tests**:
   ```bash
   # All tests
   pytest

   # Specific test
   pytest tests/code_actions/test_extract_method.py

   # With coverage
   pytest --cov=cst_lsp --cov-report=html
   ```

4. **Check types**:
   ```bash
   pyright
   ```

5. **Lint code**:
   ```bash
   # Check for issues
   ruff check

   # Auto-fix issues
   ruff check --fix

   # Format code
   ruff format
   ```

6. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: add new refactoring"
   ```

   **Commit message format**:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test changes
   - `refactor:` Code refactoring
   - `chore:` Build/tooling changes

7. **Push and create PR**:
   ```bash
   git push origin feature/my-feature
   ```
   Then create pull request on GitHub.

## Code Standards

### Style

- **Follow PEP 8**: Use ruff for formatting
- **Type hints**: All function signatures must have type hints
- **Docstrings**: All public functions/classes must have docstrings
- **Line length**: 88 characters (Black/Ruff default)

**Example**:
```python
def string_diff_to_text_edits(original: str, modified: str) -> list[lsp.TextEdit]:
    """
    Convert string diff to LSP TextEdit objects.

    Args:
        original: Original source code
        modified: Modified source code

    Returns:
        List of TextEdit objects
    """
    # Implementation
```

### Testing

**All code must have tests**:

```python
def test_extract_method_simple():
    """Test basic extraction works."""
    source = textwrap.dedent("""
        def foo():
            # start
            x = 1
            # end
    """)
    result = refactor_with_comments(source, "new_func")
    assert "def new_func" in result
    assert "new_func()" in result
```

**Test requirements**:
- Unit tests for new functions/classes
- Integration tests for new refactorings
- Edge case coverage
- Error case testing

**Run tests**:
```bash
# All tests
pytest

# Specific file
pytest tests/code_actions/test_extract_method.py

# Specific test
pytest tests/code_actions/test_extract_method.py::test_extract_method_simple

# With coverage
pytest --cov=cst_lsp --cov-report=html
# Open htmlcov/index.html to see coverage
```

### Documentation

**Update documentation for**:
- New refactorings (README.md, USER_GUIDE.md)
- API changes (docstrings, ARCHITECTURE.md)
- Configuration options
- Breaking changes

**Documentation files**:
- `README.md` - Project overview and quick start
- `CLAUDE.md` - Developer guide for Claude Code
- `docs/USER_GUIDE.md` - End-user documentation
- `docs/ARCHITECTURE.md` - Technical architecture
- `docs/ADDING_CODE_ACTIONS.md` - Contributor guide
- `docs/FAQ.md` - Common questions

## Adding New Refactorings

See [docs/ADDING_CODE_ACTIONS.md](docs/ADDING_CODE_ACTIONS.md) for detailed guide.

**Quick checklist**:
1. Create class inheriting `BaseCstLspCodeAction`
2. Implement `is_valid()` and `refactor()`
3. Register in `server.py`
4. Write comprehensive tests
5. Update documentation

## Pull Request Process

### Before Submitting

- [ ] Tests pass: `pytest`
- [ ] Types check: `pyright`
- [ ] Linting passes: `ruff check`
- [ ] Code formatted: `ruff format`
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)

### PR Description Template

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- List of specific changes
- Bullet points for clarity

## Testing
How was this tested?

## Screenshots (if applicable)
Add screenshots for UI changes

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Types checked
- [ ] Linting passed
```

### Review Process

1. **Automated checks**: CI will run tests, types, and linting
2. **Code review**: Maintainer will review your code
3. **Feedback**: Address review comments
4. **Approval**: Once approved, PR will be merged

### After Merge

- Your contribution will be credited in CHANGELOG.md
- Release notes will mention your feature/fix
- Thank you! 🎉

## Development Tips

### Debugging

**Test specific refactoring**:
```python
import libcst as cst
from cst_lsp.code_actions.extract_method import ExtractMethod

source = "def foo():\n    x = 1\n    return x"
module = cst.parse_module(source)
action = ExtractMethod()
result = action.refactor(module, CodeRange(...))
print(result)
```

**Run server manually**:
```bash
# Server reads from stdin, writes to stdout
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | cst_lsp
```

**Enable debug logging**:
```bash
export CST_LSP_LOG_LEVEL=debug
cst_lsp
```

### Common Patterns

**Using metadata**:
```python
wrapper = MetadataWrapper(module)
positions = wrapper.resolve(PositionProvider)
scopes = wrapper.resolve(ScopeProvider)
```

**Visitor pattern**:
```python
class MyVisitor(cst.CSTVisitor):
    def visit_Name(self, node: cst.Name) -> None:
        print(f"Found name: {node.value}")

module.walk(MyVisitor())
```

**Transformer pattern**:
```python
class MyTransformer(cst.CSTTransformer):
    def leave_Name(self, original, updated):
        return updated.with_changes(value="new_name")

modified = module.visit(MyTransformer())
```

### Performance Tips

- Use caching for expensive operations
- Limit scope of metadata resolution
- Profile with `pytest --profile`
- Benchmark with `time pytest`

## Release Process

(For maintainers)

1. **Update version**: `pyproject.toml`
2. **Update CHANGELOG.md**: Add release notes
3. **Create tag**: `git tag v0.1.4`
4. **Push tag**: `git push origin v0.1.4`
5. **Build**: `python -m build`
6. **Upload to PyPI**: `python -m twine upload dist/*`

## Getting Help

- **Development questions**: [GitHub Discussions](https://github.com/yourusername/cst-lsp/discussions)
- **Bug reports**: [GitHub Issues](https://github.com/yourusername/cst-lsp/issues)
- **Chat**: [Discord/Slack link if available]

## Resources

- [libcst Documentation](https://libcst.readthedocs.io/)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [pygls Documentation](https://pygls.readthedocs.io/)
- [Python AST](https://docs.python.org/3/library/ast.html)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to CST-LSP! 🚀
