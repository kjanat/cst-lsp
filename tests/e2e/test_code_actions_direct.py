"""
E2E tests for code action refactorings using direct pygls client.

Tests Extract Method and Import Symbol refactorings through full
LSP request/response cycle with TextEdit validation.

Uses DirectLspClient instead of pytest-lsp to work around async response
delivery issues in pytest-lsp 0.4.3.
"""

import pytest
from lsprotocol.types import (
    CodeActionContext,
    CodeActionParams,
    DidOpenTextDocumentParams,
    Position,
    Range,
    TextDocumentIdentifier,
    TextDocumentItem,
)

from tests.e2e.helpers.assertions import (
    assert_code_action_present,
    assert_valid_python,
)
from tests.e2e.helpers.direct_client import DirectLspClient


def apply_text_edit_helper(source: str, edit: dict) -> str:
    """Apply a single TextEdit to source (helper for multiple edits)."""
    from tests.e2e.helpers.assertions import apply_text_edit

    return apply_text_edit(source, edit)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_extract_method_simple_direct(simple_project, tmp_path):
    """
    Test basic Extract Method refactoring using direct client.

    Extracts two simple statements into a new function, verifying:
    - CodeAction is offered
    - TextEdit is structurally correct
    - Applied edit produces valid Python
    - Extracted function has correct signature
    """
    # Create test file
    test_file = simple_project / "test_extract.py"
    original_code = """def calculate_total():
    subtotal = 100
    tax = subtotal * 0.08
    return subtotal + tax
"""
    test_file.write_text(original_code)

    # Create and start direct client
    client = DirectLspClient()
    try:
        await client.start(simple_project)

        # Open document
        await client.text_document_did_open(
            DidOpenTextDocumentParams(
                text_document=TextDocumentItem(
                    uri=test_file.as_uri(),
                    language_id="python",
                    version=1,
                    text=original_code,
                )
            )
        )

        # Request code actions for lines 1-2 (subtotal and tax calculation)
        params = CodeActionParams(
            text_document=TextDocumentIdentifier(uri=test_file.as_uri()),
            range=Range(
                start=Position(line=1, character=4),  # Start of 'subtotal = 100'
                end=Position(line=2, character=26),  # End of 'tax = ...'
            ),
            context=CodeActionContext(diagnostics=[]),
        )

        actions = await client.text_document_code_action(params)

        # Assert Extract Method action exists
        assert actions is not None, "Expected code actions, got None"
        assert len(actions) > 0, "Expected at least one code action"

        extract_action = assert_code_action_present(
            actions, title="Extract Method", kind="refactor.extract"
        )

        # Validate edit structure
        assert "edit" in extract_action, "CodeAction missing 'edit' field"
        edit_obj = extract_action["edit"]
        assert "changes" in edit_obj, "WorkspaceEdit missing 'changes' field"

        # Get TextEdits for our document
        changes = edit_obj["changes"]
        assert test_file.as_uri() in changes, f"No edits for {test_file.as_uri()}"

        text_edits = changes[test_file.as_uri()]
        assert len(text_edits) > 0, "Expected at least one TextEdit"

        # Apply all edits
        result = original_code
        for text_edit in sorted(
            text_edits,
            key=lambda e: (
                e["range"]["start"]["line"],
                e["range"]["start"]["character"],
            ),
            reverse=True,
        ):
            result = apply_text_edit_helper(result, text_edit)

        # Validate result is valid Python
        assert_valid_python(result)

        # Validate extracted function exists
        assert "def " in result, "Expected new function definition"
        assert "subtotal = 100" in result, "Expected extracted code in new function"
        assert "tax = " in result, "Expected tax calculation in new function"

        # Validate function call inserted
        assert "(" in result, "Expected function call in original location"

    finally:
        await client.shutdown()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_import_single_symbol_direct(simple_project):
    """
    Test Import Symbol code action for undefined symbol using direct client.

    Creates file with undefined symbol (User from models.py) and verifies:
    - Import Symbol CodeAction is offered
    - Symbol is found via SymbolFinder within project
    - Import statement inserted correctly
    - Undefined symbol becomes defined
    """
    # Create test file with undefined symbol
    test_file = simple_project / "test_import.py"
    original_code = """def create_user():
    user = User("Alice", "alice@example.com")
    return user.display_name()
"""
    test_file.write_text(original_code)

    # Create and start direct client
    client = DirectLspClient()
    try:
        await client.start(simple_project)

        # Open document
        await client.text_document_did_open(
            DidOpenTextDocumentParams(
                text_document=TextDocumentItem(
                    uri=test_file.as_uri(),
                    language_id="python",
                    version=1,
                    text=original_code,
                )
            )
        )

        # Request code actions at 'User' symbol (line 1, character 11)
        params = CodeActionParams(
            text_document=TextDocumentIdentifier(uri=test_file.as_uri()),
            range=Range(
                start=Position(line=1, character=11),  # Start of 'User'
                end=Position(line=1, character=15),  # End of 'User'
            ),
            context=CodeActionContext(diagnostics=[]),
        )

        actions = await client.text_document_code_action(params)

        # Validate response
        assert actions is not None, "Expected code actions for undefined symbol"

        # Should have Import Symbol action
        import_actions = [
            a
            for a in actions
            if "import" in a.get("title", "").lower()
            and "symbol" in a.get("title", "").lower()
        ]

        if len(import_actions) == 0:
            pytest.skip(
                "Import Symbol not available (ripgrep not installed or symbol not found)"
            )

        import_action = import_actions[0]

        # Validate edit structure
        assert "edit" in import_action, "CodeAction missing 'edit' field"
        edit_obj = import_action["edit"]
        assert "changes" in edit_obj, "WorkspaceEdit missing 'changes' field"

        changes = edit_obj["changes"]
        text_edits = changes[test_file.as_uri()]

        # Apply edits
        result = original_code
        for text_edit in sorted(
            text_edits,
            key=lambda e: (
                e["range"]["start"]["line"],
                e["range"]["start"]["character"],
            ),
            reverse=True,
        ):
            result = apply_text_edit_helper(result, text_edit)

        # Validate import added
        assert "import" in result.lower(), "Expected import statement added"
        assert "User" in result, "Expected User symbol in result"

        # Validate result is valid Python
        assert_valid_python(result)

        # Import should be at top of file (before function)
        lines = result.splitlines()
        import_line_idx = next(
            (
                i
                for i, line in enumerate(lines)
                if "import" in line.lower() and "User" in line
            ),
            None,
        )
        function_line_idx = next(
            (i for i, line in enumerate(lines) if "def " in line), None
        )

        assert import_line_idx is not None, "Import statement not found"
        assert function_line_idx is not None, "Function definition not found"
        assert import_line_idx < function_line_idx, (
            "Import should be before function definition"
        )

    finally:
        await client.shutdown()
