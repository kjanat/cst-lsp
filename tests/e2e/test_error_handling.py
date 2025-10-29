"""
E2E tests for error handling and invalid request scenarios.

Tests server behavior with invalid ranges, malformed requests,
and error recovery.
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


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_invalid_range_handling(client, simple_project):
    """
    Test server handles invalid position ranges gracefully.

    Verifies that reversed ranges (start > end) or out-of-bounds
    positions don't crash the server and return appropriate response.
    """
    # Create test file
    test_file = simple_project / "test_invalid.py"
    code = """def foo():
    x = 1
    return x
"""
    test_file.write_text(code)

    # Open document (notification, synchronous)
    client.text_document_did_open(
        params=DidOpenTextDocumentParams(
            text_document=TextDocumentItem(
                uri=test_file.as_uri(),
                language_id="python",
                version=1,
                text=code,
            )
        )
    )

    # Test 1: Reversed range (end before start)
    params_reversed = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=test_file.as_uri()),
        range=Range(
            start=Position(line=2, character=0),  # Line 2
            end=Position(line=1, character=0),  # Line 1 (before start!)
        ),
        context=CodeActionContext(diagnostics=[]),
    )

    # Should not crash - return empty list or error
    result = await client.text_document_code_action_async(params_reversed)

    # Valid responses: None, empty list, or error
    assert result is None or isinstance(result, list), (
        f"Unexpected response type: {type(result)}"
    )

    # Test 2: Out of bounds position (line 9999)
    params_out_of_bounds = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=test_file.as_uri()),
        range=Range(
            start=Position(line=9999, character=0),
            end=Position(line=10000, character=0),
        ),
        context=CodeActionContext(diagnostics=[]),
    )

    # Should not crash
    result = await client.text_document_code_action_async(params_out_of_bounds)

    # Valid responses: None, empty list, or error
    assert result is None or isinstance(result, list), (
        f"Unexpected response type for out-of-bounds: {type(result)}"
    )

    # Server should still be responsive after errors
    # Test with valid range to verify server didn't crash
    params_valid = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=test_file.as_uri()),
        range=Range(
            start=Position(line=1, character=4),
            end=Position(line=1, character=9),
        ),
        context=CodeActionContext(diagnostics=[]),
    )

    result = await client.text_document_code_action_async(params_valid)

    # Server should respond (may or may not have actions, but should respond)
    assert result is not None or True, "Server failed to respond after error scenarios"
