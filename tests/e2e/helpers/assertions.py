"""
Assertion utilities for validating LSP responses and code transformations.

Provides type-safe assertions for:
- LSP response structure validation
- TextEdit correctness verification
- Code action presence checks
- Position/range accuracy validation
"""

import ast
from difflib import unified_diff
from typing import Any

import pytest
from deepdiff import DeepDiff
from jsonschema import ValidationError, validate


def assert_lsp_response(
    actual: dict[str, Any],
    expected: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> None:
    """
    Validate LSP response structure and content.

    Args:
        actual: Received LSP response
        expected: Expected response structure (partial matching allowed)
        schema: Optional JSON schema for LSP protocol compliance

    Raises:
        AssertionError: If response doesn't match expectations or schema
    """
    # Schema validation (LSP protocol compliance)
    if schema:
        try:
            validate(instance=actual, schema=schema)
        except ValidationError as e:
            pytest.fail(
                f"LSP schema validation failed: {e.message}\nPath: {e.json_path}"
            )

    # Structural comparison (allow partial matching)
    diff = DeepDiff(expected, actual, ignore_order=True, view="tree")

    if diff:
        pytest.fail(f"Response mismatch:\n{diff.pretty()}")


def assert_text_edit_correct(
    edit: dict[str, Any],
    original: str,
    expected_result: str,
) -> None:
    """
    Apply TextEdit and validate resulting code.

    Args:
        edit: LSP TextEdit object {range: {...}, newText: "..."}
        original: Original source code
        expected_result: Expected code after applying edit

    Raises:
        AssertionError: If edit produces invalid syntax or wrong result
    """
    # Apply edit
    result = apply_text_edit(original, edit)

    # Syntax validation
    try:
        ast.parse(result)
    except SyntaxError as e:
        pytest.fail(
            f"Edit produced invalid Python syntax:\n"
            f"  Error: {e}\n"
            f"  Line {e.lineno}: {e.text}\n"
            f"  Full result:\n{result}"
        )

    # Content validation (normalize whitespace)
    result_normalized = result.strip()
    expected_normalized = expected_result.strip()

    if result_normalized != expected_normalized:
        diff_lines = list(
            unified_diff(
                expected_normalized.splitlines(keepends=True),
                result_normalized.splitlines(keepends=True),
                fromfile="expected",
                tofile="actual",
                lineterm="",
            )
        )
        pytest.fail(f"Edit result doesn't match expected:\n{''.join(diff_lines)}")


def apply_text_edit(source: str, edit: dict[str, Any]) -> str:
    """
    Apply a single LSP TextEdit to source code.

    Handles LSP Position coordinates (0-indexed) and applies the edit
    by replacing the specified range with new text.

    Args:
        source: Original source code
        edit: TextEdit with {range: {start, end}, newText}

    Returns:
        Source code with edit applied
    """
    lines = source.splitlines(keepends=True)

    # Extract edit components
    range_obj = edit["range"]
    new_text = edit["newText"]

    start_line = range_obj["start"]["line"]
    start_char = range_obj["start"]["character"]
    end_line = range_obj["end"]["line"]
    end_char = range_obj["end"]["character"]

    # Handle empty document
    if not lines:
        return new_text

    # Build result
    result_lines = lines[:start_line]

    # Get text before and after edit range
    start_line_text = lines[start_line][:start_char] if start_line < len(lines) else ""
    end_line_text = lines[end_line][end_char:] if end_line < len(lines) else ""

    # Combine: prefix + new_text + suffix
    modified = start_line_text + new_text + end_line_text
    result_lines.append(modified)

    # Add remaining lines after edit range
    if end_line + 1 < len(lines):
        result_lines.extend(lines[end_line + 1 :])

    return "".join(result_lines)


def assert_code_action_present(
    actions: list[dict[str, Any]],
    title: str,
    kind: str | None = None,
) -> dict[str, Any]:
    """
    Assert specific CodeAction exists in response.

    Args:
        actions: List of CodeAction objects from LSP response
        title: Expected action title (exact match)
        kind: Expected action kind (optional, e.g., "refactor.extract")

    Returns:
        The matching CodeAction dictionary

    Raises:
        AssertionError: If action not found
    """
    matching = [a for a in actions if a.get("title") == title]

    if kind is not None:
        matching = [a for a in matching if a.get("kind") == kind]

    if len(matching) == 0:
        available = [(a.get("title"), a.get("kind")) for a in actions]
        pytest.fail(
            f"CodeAction not found:\n"
            f"  Expected: title='{title}', kind='{kind}'\n"
            f"  Available: {available}"
        )

    return matching[0]


def assert_position_accurate(
    actual: dict[str, Any],
    expected_line: int,
    expected_char: int,
) -> None:
    """
    Validate LSP Position coordinates (0-indexed).

    Args:
        actual: Position object {line: int, character: int}
        expected_line: Expected line number (0-indexed)
        expected_char: Expected character position (0-indexed)

    Raises:
        AssertionError: If position doesn't match
    """
    assert actual["line"] == expected_line, (
        f"Line mismatch: {actual['line']} != {expected_line}"
    )
    assert actual["character"] == expected_char, (
        f"Character mismatch: {actual['character']} != {expected_char}"
    )


def assert_valid_python(code: str) -> None:
    """
    Assert that code is syntactically valid Python.

    Args:
        code: Python source code to validate

    Raises:
        AssertionError: If code has syntax errors
    """
    try:
        ast.parse(code)
    except SyntaxError as e:
        pytest.fail(
            f"Invalid Python syntax:\n"
            f"  Line {e.lineno}: {e.text}\n"
            f"  Error: {e.msg}\n"
            f"  Full code:\n{code}"
        )
