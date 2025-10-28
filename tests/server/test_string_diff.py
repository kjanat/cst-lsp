from lsprotocol.types import Position, Range, TextEdit

from cst_lsp.server import string_diff_to_text_edits


def test_replace_single_line():
    """Test replacing a single line."""
    original = "line1\nline2\nline3"
    modified = "line1\nmodified\nline3"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert edits[0].new_text == "modified"
    assert edits[0].range.start.line == 1
    assert edits[0].range.end.line == 1


def test_replace_multiple_lines():
    """Test replacing multiple consecutive lines."""
    original = "line1\nline2\nline3\nline4"
    modified = "line1\nreplaced2\nreplaced3\nline4"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert edits[0].new_text == "replaced2\nreplaced3"
    assert edits[0].range.start.line == 1
    assert edits[0].range.end.line == 2


def test_insert_lines():
    """Test inserting new lines."""
    original = "line1\nline3"
    modified = "line1\nline2\nline3"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert "line2" in edits[0].new_text
    assert edits[0].range.start.line == 1
    assert edits[0].range.end.line == 1


def test_insert_at_beginning():
    """Test inserting lines at the beginning."""
    original = "line2\nline3"
    modified = "line1\nline2\nline3"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert "line1" in edits[0].new_text
    assert edits[0].range.start.line == 0


def test_insert_at_end():
    """Test inserting lines at the end."""
    original = "line1\nline2"
    modified = "line1\nline2\nline3"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert "line3" in edits[0].new_text


def test_delete_lines():
    """Test deleting lines."""
    original = "line1\nline2\nline3"
    modified = "line1\nline3"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert edits[0].new_text == ""
    assert edits[0].range.start.line == 1


def test_delete_multiple_lines():
    """Test deleting multiple consecutive lines."""
    original = "line1\nline2\nline3\nline4"
    modified = "line1\nline4"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert edits[0].new_text == ""
    assert edits[0].range.start.line == 1


def test_multiple_operations():
    """Test combination of insert, delete, and replace operations."""
    original = "line1\nline2\nline3\nline4"
    modified = "line0\nline1\nmodified3\nline4\nline5"

    edits = string_diff_to_text_edits(original, modified)

    # Should have multiple edits for different operations
    assert len(edits) >= 1
    # Verify that edits contain expected text
    all_new_text = "".join(edit.new_text for edit in edits)
    assert "line0" in all_new_text or any(edit.range.start.line == 0 for edit in edits)


def test_no_changes():
    """Test when strings are identical - should return empty list."""
    original = "line1\nline2\nline3"
    modified = "line1\nline2\nline3"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 0


def test_empty_strings():
    """Test with both strings empty."""
    original = ""
    modified = ""

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 0


def test_empty_to_content():
    """Test inserting content into empty string."""
    original = ""
    modified = "new content"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert "new content" in edits[0].new_text


def test_content_to_empty():
    """Test deleting all content."""
    original = "some content"
    modified = ""

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert edits[0].new_text == ""


def test_single_line_change():
    """Test changing a single line without newlines."""
    original = "original"
    modified = "modified"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    assert edits[0].new_text == "modified"


def test_whitespace_changes():
    """Test changes involving whitespace."""
    original = "line1\n  line2\nline3"
    modified = "line1\nline2\nline3"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    # Should detect the whitespace removal
    assert "  " not in edits[0].new_text or edits[0].new_text == "line2"


def test_text_edit_structure():
    """Test that TextEdit objects have correct structure."""
    original = "line1\nline2"
    modified = "line1\nmodified"

    edits = string_diff_to_text_edits(original, modified)

    assert len(edits) == 1
    edit = edits[0]

    # Verify it's a TextEdit object
    assert isinstance(edit, TextEdit)
    assert isinstance(edit.range, Range)
    assert isinstance(edit.range.start, Position)
    assert isinstance(edit.range.end, Position)
    assert isinstance(edit.new_text, str)


def test_preserves_line_order():
    """Test that edits maintain correct line ordering."""
    original = "a\nb\nc\nd\ne"
    modified = "a\nB\nc\nD\ne"

    edits = string_diff_to_text_edits(original, modified)

    # Should have edits for lines 1 and 3 (0-indexed)
    assert len(edits) >= 1

    # Verify edits are for correct lines
    for edit in edits:
        assert edit.range.start.line in [1, 3]


def test_complex_multiline_replacement():
    """Test complex scenario with multiple types of changes."""
    original = """def foo():
    x = 1
    y = 2
    return x + y"""

    modified = """def foo():
    x = 1
    z = 3
    return x + z"""

    edits = string_diff_to_text_edits(original, modified)

    # Should detect the changes to lines with 'y' and 'z'
    assert len(edits) >= 1

    # Verify changes contain the new variable name
    all_new_text = "".join(edit.new_text for edit in edits)
    assert "z = 3" in all_new_text or any("z" in edit.new_text for edit in edits)
