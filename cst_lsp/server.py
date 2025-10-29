"""
CST-LSP Server: Language Server Protocol implementation for Python refactoring.

This module implements the core LSP server that coordinates refactoring operations
using libcst transformations. The server handles code action requests from LSP clients,
applies appropriate transformations, and converts results to LSP TextEdit operations.

The server lifecycle:
1. Initialize: Sets up transformations and symbol finder based on workspace root
2. Code Action Handler: Processes user selections and applies valid transformations
3. Diff Conversion: Converts transformed code to LSP-compatible TextEdits

Key components:
    - CstLspServer: Main LSP server class extending pygls LanguageServer
    - string_diff_to_text_edits: Converts string diffs to LSP TextEdit objects
"""

import difflib
import sys
from pathlib import Path

import libcst
from libcst.metadata import CodePosition, CodeRange
from lsprotocol import types as lsp
from pygls.server import LanguageServer

from cst_lsp.code_actions.base import BaseCstLspCodeAction
from cst_lsp.code_actions.extract_method import ExtractMethod
from cst_lsp.code_actions.import_symbol import ImportAll, ImportSymbol
from cst_lsp.symbols.symbol_finder import SymbolFinder


def string_diff_to_text_edits(original: str, modified: str) -> list[lsp.TextEdit]:
    """
    Convert the difference between two strings into a list of LSP TextEdit objects.

    Uses difflib.SequenceMatcher to compute line-level diffs and converts them
    to LSP TextEdit operations. Handles replace, insert, and delete operations
    with proper LSP Range and Position coordinates.

    Args:
        original: The original source code text
        modified: The transformed source code text

    Returns:
        List of LSP TextEdit objects representing the changes needed to
        transform original into modified text
    """
    original_lines = original.splitlines()
    modified_lines = modified.splitlines()

    matcher = difflib.SequenceMatcher(None, original_lines, modified_lines)

    text_edits = {}

    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "replace":
            # Handle replacements
            new_text = "\n".join(modified_lines[j1:j2])
            text_edits[i1] = lsp.TextEdit(
                range=lsp.Range(
                    start=lsp.Position(i1, 0),
                    end=lsp.Position(i2 - 1, len(original_lines[i2 - 1])),
                ),
                new_text=new_text,
            )
        elif op == "insert":
            # Handle insertions
            insert_at_line = i1
            new_text = "\n".join(modified_lines[j1:j2]) + "\n"
            if insert_at_line in text_edits:
                # Append to existing edit if there's one for this line
                text_edits[insert_at_line].new_text += new_text
            else:
                text_edits[insert_at_line] = lsp.TextEdit(
                    range=lsp.Range(
                        start=lsp.Position(insert_at_line, 0),
                        end=lsp.Position(insert_at_line, 0),
                    ),
                    new_text=new_text,
                )
        elif op == "delete":
            # Handle deletions
            text_edits[i1] = lsp.TextEdit(
                range=lsp.Range(
                    start=lsp.Position(i1, 0),
                    end=lsp.Position(i2, len(original_lines[i2 - 1])),
                ),
                new_text="",
            )

    # Convert the dictionary to a list of TextEdits
    result = list(text_edits.values())
    return result


class CstLspServer(LanguageServer):
    """
    LSP Server implementation for Python refactoring operations.

    Coordinates code action requests with CST transformations, applying
    libcst-based refactorings to Python source code and converting results
    to LSP TextEdit operations for editor display.

    The server maintains a list of registered transformations (Extract Method,
    Import Symbol, etc.) and applies them to user selections when code actions
    are requested.

    Attributes:
        transformations: List of registered code action handlers
    """

    def __init__(self):
        """Initialize the CST-LSP server with empty transformations list."""
        super().__init__("cst-lsp-server", "v0.1")
        self.transformations: list[BaseCstLspCodeAction] = []

    async def initialize(self, params: lsp.InitializeParams):
        """
        Initialize the server with transformations based on workspace configuration.

        Sets up available refactoring operations. Extract Method is always available.
        Import-related operations (ImportSymbol, ImportAll) are only enabled if
        a SymbolFinder can be created (requires ripgrep).

        Args:
            params: LSP initialization parameters containing workspace root URI

        Note:
            If params.root_uri is not provided, only Extract Method will be available.
            Symbol finder uses sys.executable for Python path (TODO: make configurable).
        """
        self.transformations = [ExtractMethod()]
        if params.root_uri:
            root_path = Path(params.root_uri.replace("file://", ""))
            # TODO: Make `python_path` configurable.
            symbol_finder = SymbolFinder.create(Path(sys.executable), Path(root_path))
            if symbol_finder:
                self.transformations.append(ImportSymbol(symbol_finder))
                self.transformations.append(ImportAll(symbol_finder))

    async def code_action_handler(
        self, params: lsp.CodeActionParams
    ) -> list[lsp.CodeAction] | None:
        """
        Handle code action requests from the LSP client.

        Processes user selections and applies all valid transformations, converting
        results to LSP CodeAction objects with TextEdit changes.

        Workflow:
        1. Get document from workspace
        2. Parse with libcst
        3. Convert LSP range to libcst CodeRange (0-indexed → 1-indexed)
        4. For each transformation:
           - Check if valid for selection
           - Apply refactoring
           - Convert result to TextEdits
           - Create CodeAction with edits
        5. Return all applicable code actions

        Args:
            params: Code action parameters containing document URI and selection range

        Returns:
            List of LSP CodeAction objects if any transformations apply,
            None otherwise

        Note:
            Exceptions during transformation are silently caught to prevent
            one failing transformation from blocking others.
        """
        document = self.workspace.get_document(params.text_document.uri)
        start, end = params.range.start, params.range.end

        code_actions = []
        module = libcst.parse_module(document.source)
        code_range = CodeRange(
            CodePosition(start.line + 1, start.character),
            CodePosition(end.line + 1, end.character),
        )
        for transformation in self.transformations:
            if not transformation.is_valid(document.source, module, code_range):
                continue
            try:
                result = transformation.refactor(module, code_range)
                if not result or result == document.source:
                    continue
                edits = string_diff_to_text_edits(document.source, result)
            except Exception:
                continue

            code_actions.append(
                lsp.CodeAction(
                    title=f"{transformation.name}",
                    kind=lsp.CodeActionKind.RefactorExtract,
                    edit=lsp.WorkspaceEdit(changes={params.text_document.uri: edits}),
                )
            )

        return code_actions if code_actions else None


server = CstLspServer()


@server.feature(lsp.TEXT_DOCUMENT_CODE_ACTION)
async def code_action(params: lsp.CodeActionParams) -> list[lsp.CodeAction] | None:
    return await server.code_action_handler(params)


@server.feature(lsp.INITIALIZE)
async def initialize(params: lsp.InitializeParams):
    return await server.initialize(params)


def main():
    """
    Start the CST-LSP server in stdio mode.

    Entry point for the language server. Reads LSP protocol messages from
    stdin and writes responses to stdout, following the standard LSP
    communication model.
    """
    server.start_io()


if __name__ == "__main__":
    main()
