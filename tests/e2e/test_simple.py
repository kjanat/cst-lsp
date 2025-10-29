"""
Simple diagnostic test to validate basic pytest-lsp functionality.
"""

import pytest
from lsprotocol.types import (
    DidOpenTextDocumentParams,
    TextDocumentItem,
)


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_client_connects(client, simple_project):
    """
    Simplest possible test: verify client fixture works.

    If this passes, pytest-lsp infrastructure is correct.
    """
    # If we reach here, client initialized successfully
    assert client is not None, "Client should be initialized"
    print(f"Client type: {type(client)}")
    print(f"Client methods: {[m for m in dir(client) if 'code_action' in m]}")


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_open_document(client, simple_project):
    """
    Test opening a document without requesting actions.

    Validates text_document_did_open notification works.
    """
    # Create test file
    test_file = simple_project / "simple.py"
    code = "x = 1\n"
    test_file.write_text(code)

    # Open document
    print(f"Opening document: {test_file.as_uri()}")
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

    # If no exception, success
    assert True, "Document opened successfully"
