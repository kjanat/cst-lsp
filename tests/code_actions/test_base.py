import libcst as cst
import pytest
from libcst.metadata import CodePosition, CodeRange
from lsprotocol.types import CodeActionKind

from cst_lsp.code_actions.base import BaseCstLspCodeAction, code_ranges_interect


# Concrete implementation for testing the abstract class
class TestCodeAction(BaseCstLspCodeAction):
    name = "Test Action"
    kind = CodeActionKind.Refactor

    def refactor(self, module: cst.Module, code_range: CodeRange) -> str | None:
        return module.code


@pytest.mark.parametrize(
    "range1, range2, expected",
    [
        # Test case 1: Ranges overlap
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=3, column=0)
            ),
            CodeRange(
                start=CodePosition(line=2, column=0), end=CodePosition(line=4, column=0)
            ),
            True,
        ),
        # Test case 2: Ranges touch at a point
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            CodeRange(
                start=CodePosition(line=2, column=0), end=CodePosition(line=3, column=0)
            ),
            True,
        ),
        # Test case 3: One range entirely within another
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=5, column=0)
            ),
            CodeRange(
                start=CodePosition(line=2, column=0), end=CodePosition(line=3, column=0)
            ),
            True,
        ),
        # Test case 4: Ranges do not intersect
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            CodeRange(
                start=CodePosition(line=3, column=0), end=CodePosition(line=4, column=0)
            ),
            False,
        ),
        # Test case 5: Ranges are the same
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=2, column=0)
            ),
            True,
        ),
        # Test case 6: Ranges overlap in columns
        (
            CodeRange(
                start=CodePosition(line=1, column=0),
                end=CodePosition(line=1, column=10),
            ),
            CodeRange(
                start=CodePosition(line=1, column=5),
                end=CodePosition(line=1, column=15),
            ),
            True,
        ),
        # Test case 7: Ranges touch at a column
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=1, column=5)
            ),
            CodeRange(
                start=CodePosition(line=1, column=5),
                end=CodePosition(line=1, column=10),
            ),
            True,
        ),
        # Test case 8: One range entirely within another in columns
        (
            CodeRange(
                start=CodePosition(line=1, column=0),
                end=CodePosition(line=1, column=20),
            ),
            CodeRange(
                start=CodePosition(line=1, column=5),
                end=CodePosition(line=1, column=15),
            ),
            True,
        ),
        # Test case 9: Ranges do not intersect in columns
        (
            CodeRange(
                start=CodePosition(line=1, column=0), end=CodePosition(line=1, column=5)
            ),
            CodeRange(
                start=CodePosition(line=1, column=10),
                end=CodePosition(line=1, column=15),
            ),
            False,
        ),
    ],
)
def test_code_ranges_intersect(range1, range2, expected):
    assert code_ranges_interect(range1, range2) == expected


def test_is_valid_with_valid_code():
    """Test is_valid returns True for valid parseable code."""
    action = TestCodeAction()
    source = "def foo():\n    x = 1\n    y = 2\n    return x + y"
    module = cst.parse_module(source)
    # Select the function body (lines 2-4)
    code_range = CodeRange(
        start=CodePosition(line=2, column=0), end=CodePosition(line=4, column=16)
    )

    assert action.is_valid(source, module, code_range) is True


def test_is_valid_with_invalid_code():
    """Test is_valid returns False for invalid unparseable code."""
    action = TestCodeAction()
    # Source with intentionally broken syntax when extracted
    source = "def foo():\n    if x > 0:\n        return True\n    return False"
    module = cst.parse_module(source)
    # Select just the 'if' condition without the body - will fail to parse
    code_range = CodeRange(
        start=CodePosition(line=2, column=0), end=CodePosition(line=2, column=13)
    )

    assert action.is_valid(source, module, code_range) is False


def test_is_valid_with_single_line():
    """Test is_valid with single line selection."""
    action = TestCodeAction()
    source = "x = 1"
    module = cst.parse_module(source)
    code_range = CodeRange(
        start=CodePosition(line=1, column=0), end=CodePosition(line=1, column=5)
    )

    assert action.is_valid(source, module, code_range) is True
