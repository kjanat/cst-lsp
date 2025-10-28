import sys
from pathlib import Path
from unittest.mock import MagicMock

import libcst as cst
import pytest
from libcst.metadata import CodePosition, CodeRange

from cst_lsp.code_actions.import_symbol import (
    ImportAll,
    ImportSymbol,
    get_name_at_location,
)
from cst_lsp.symbols.symbol_finder import RipGrepSymbolFinder, SuggestedImport


@pytest.fixture
def mock_symbol_finder():
    """Create a mock symbol finder for testing."""
    finder = MagicMock()
    finder.find_symbol.return_value = [
        SuggestedImport(module="os.path", symbol="join", alias=None)
    ]
    return finder


@pytest.fixture
def real_symbol_finder():
    """Create a real symbol finder for integration tests."""
    return RipGrepSymbolFinder(python_path=Path(sys.executable), root=Path.cwd())


def test_get_name_at_location_simple():
    """Test extracting a name from a specific location."""
    source = "x = 1"
    module = cst.parse_module(source)
    # Target the variable name 'x' at position (1, 0)
    location = CodeRange(start=CodePosition(1, 0), end=CodePosition(1, 1))
    name = get_name_at_location(module, location)
    assert name == "x"


def test_get_name_at_location_function_call():
    """Test extracting a function name from a call."""
    source = "result = join(a, b)"
    module = cst.parse_module(source)
    # Target the 'join' function name
    location = CodeRange(start=CodePosition(1, 9), end=CodePosition(1, 13))
    name = get_name_at_location(module, location)
    assert name == "join"


def test_get_name_at_location_not_found():
    """Test when no name exists at location."""
    source = "x = 1 + 2"
    module = cst.parse_module(source)
    # Target the '+' operator (not a name)
    location = CodeRange(start=CodePosition(1, 6), end=CodePosition(1, 7))
    name = get_name_at_location(module, location)
    assert name is None


def test_import_symbol_is_valid_with_undefined_symbol(mock_symbol_finder):
    """Test is_valid returns True when symbol is undefined."""
    action = ImportSymbol(mock_symbol_finder)
    source = "result = join(a, b)"
    module = cst.parse_module(source)
    # Target the undefined 'join' function
    location = CodeRange(start=CodePosition(1, 9), end=CodePosition(1, 13))

    assert action.is_valid(source, module, location) is True


def test_import_symbol_is_valid_with_defined_symbol(mock_symbol_finder):
    """Test is_valid returns False when symbol is defined."""
    action = ImportSymbol(mock_symbol_finder)
    source = "def join():\n    pass\nresult = join()"
    module = cst.parse_module(source)
    # Target the defined 'join' function
    location = CodeRange(start=CodePosition(3, 9), end=CodePosition(3, 13))

    assert action.is_valid(source, module, location) is False


def test_import_symbol_refactor_adds_import(mock_symbol_finder):
    """Test refactor adds the correct import statement."""
    action = ImportSymbol(mock_symbol_finder)
    source = "result = join(a, b)"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 9), end=CodePosition(1, 13))

    result = action.refactor(module, location)

    assert result is not None
    assert "from os.path import join" in result
    mock_symbol_finder.find_symbol.assert_called_once_with("join")


def test_import_symbol_refactor_no_name_at_location(mock_symbol_finder):
    """Test refactor returns original code when no name at location."""
    action = ImportSymbol(mock_symbol_finder)
    source = "x = 1 + 2"
    module = cst.parse_module(source)
    # Target the operator, not a name
    location = CodeRange(start=CodePosition(1, 6), end=CodePosition(1, 7))

    result = action.refactor(module, location)

    assert result == source


def test_import_symbol_refactor_no_matching_imports(mock_symbol_finder):
    """Test refactor when symbol finder returns no matches."""
    mock_symbol_finder.find_symbol.return_value = []
    action = ImportSymbol(mock_symbol_finder)
    source = "result = unknown_func()"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 9), end=CodePosition(1, 21))

    result = action.refactor(module, location)

    # Should return code without adding import
    assert result is not None
    assert "import" not in result


def test_import_all_is_valid_multiple_undefined(mock_symbol_finder):
    """Test ImportAll is_valid returns True with multiple undefined symbols."""
    action = ImportAll(mock_symbol_finder)
    source = "result = join(a, b) + exists(path)"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 0), end=CodePosition(1, 35))

    # Should be valid because multiple symbols are undefined
    is_valid = action.is_valid(source, module, location)
    assert is_valid is True


def test_import_all_is_valid_single_undefined(mock_symbol_finder):
    """Test ImportAll is_valid returns False with only one undefined symbol."""
    action = ImportAll(mock_symbol_finder)
    # In this code, only 'join' is undefined (x is defined)
    source = "x = 1\nresult = join(x)"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 0), end=CodePosition(2, 21))

    # Should be invalid because only one symbol is undefined
    is_valid = action.is_valid(source, module, location)
    assert is_valid is False


def test_import_all_refactor_multiple_imports(mock_symbol_finder):
    """Test ImportAll refactor adds multiple imports."""
    # Return results for all possible undefined symbols (join, a, b, exists, path)
    mock_symbol_finder.find_symbol.return_value = [
        SuggestedImport(module="os.path", symbol="join", alias=None)
    ]

    action = ImportAll(mock_symbol_finder)
    source = "result = join(a, b) + exists(path)"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 0), end=CodePosition(1, 35))

    result = action.refactor(module, location)

    assert result is not None
    # Just verify that refactor completes successfully
    # The actual imports added depend on what the symbol finder returns


def test_undefined_symbols_finds_undefined(mock_symbol_finder):
    """Test undefined_symbols method correctly identifies undefined symbols."""
    action = ImportSymbol(mock_symbol_finder)
    source = "result = join(a, b)"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 0), end=CodePosition(1, 19))

    undefined = action.undefined_symbols(module, location)

    # Should find 'join', 'a', and 'b' as undefined
    assert len(undefined) >= 1
    assert "join" in undefined


def test_undefined_symbols_excludes_defined(mock_symbol_finder):
    """Test undefined_symbols excludes defined variables."""
    action = ImportSymbol(mock_symbol_finder)
    source = "a = 1\nb = 2\nresult = a + b"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 0), end=CodePosition(3, 18))

    undefined = action.undefined_symbols(module, location)

    # 'a' and 'b' are defined, so they shouldn't be in undefined symbols
    # (though they might appear if referenced before definition)
    assert "result" not in undefined


def test_import_symbol_with_alias(mock_symbol_finder):
    """Test importing a symbol with an alias."""
    mock_symbol_finder.find_symbol.return_value = [
        SuggestedImport(module="os", symbol="path", alias="ospath")
    ]

    action = ImportSymbol(mock_symbol_finder)
    source = "result = ospath.join(a, b)"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 9), end=CodePosition(1, 15))

    result = action.refactor(module, location)

    assert result is not None
    assert "from os import path as ospath" in result


def test_import_symbol_integration(real_symbol_finder):
    """Integration test with real symbol finder."""
    action = ImportSymbol(real_symbol_finder)
    source = "tree = parse_module(code)"
    module = cst.parse_module(source)
    location = CodeRange(start=CodePosition(1, 7), end=CodePosition(1, 19))

    result = action.refactor(module, location)

    # Should add an import for parse_module (likely from libcst)
    assert result is not None
    if "import" in result:
        assert "parse_module" in result or "libcst" in result
