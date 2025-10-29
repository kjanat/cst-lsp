"""
Simple code action test to debug timeout issues.
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
@pytest.mark.timeout(5)
async def test_code_action_request_basic(client, simple_project):
    """
    Test basic code action request.

    Just validate that server responds to code action requests,
    even if it returns empty list.
    """
    # Create minimal test file
    test_file = simple_project / "minimal.py"
    code = """def foo():
    x = 1
    return x
"""
    test_file.write_text(code)

    # Open document
    print(f"Opening: {test_file.as_uri()}")
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

    # Request code actions (any selection)
    print("Requesting code actions...")
    params = CodeActionParams(
        text_document=TextDocumentIdentifier(uri=test_file.as_uri()),
        range=Range(
            start=Position(line=1, character=4),
            end=Position(line=1, character=9),
        ),
        context=CodeActionContext(diagnostics=[]),
    )

    try:
        # Use async version
        print("Calling text_document_code_action_async...")
        import asyncio

        actions = await asyncio.wait_for(
            client.text_document_code_action_async(params), timeout=3.0
        )
        print(f"Got response: {actions}")
        print(f"Response type: {type(actions)}")
        print(f"Number of actions: {len(actions) if actions else 0}")

        # Just validate we got a response (empty list is OK)
        assert True, "Server responded!"

    except asyncio.TimeoutError:
        print("TIMEOUT waiting for response")
        raise
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        raise
