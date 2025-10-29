"""
Direct LSP client for e2e testing.

Provides a lightweight client using raw JSON-RPC over stdin/stdout,
bypassing pytest-lsp for code action requests that timeout with pytest-lsp.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from lsprotocol import types
from lsprotocol.converters import get_converter


class DirectLspClient:
    """
    Direct LSP client using raw JSON-RPC over stdin/stdout.

    Lighter weight than pytest-lsp LanguageClient, for cases where
    pytest-lsp async response delivery has issues.
    """

    def __init__(self):
        self.converter = get_converter()
        self.process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task | None = None
        self._response_futures: dict[str | int, asyncio.Future] = {}
        self._next_id = 1

    async def start(self, workspace_root: Path) -> None:
        """Start LSP server process and initialize."""
        # Start server process
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "cst_lsp.server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Start reading responses
        self._reader_task = asyncio.create_task(self._read_responses())

        # Initialize
        init_params = types.InitializeParams(
            process_id=None,
            root_uri=workspace_root.as_uri(),
            capabilities=types.ClientCapabilities(
                text_document=types.TextDocumentClientCapabilities(
                    code_action=types.CodeActionClientCapabilities(
                        dynamic_registration=False,
                    )
                )
            ),
            workspace_folders=[
                types.WorkspaceFolder(
                    uri=workspace_root.as_uri(),
                    name="test_workspace",
                )
            ],
        )

        init_result = await self._request("initialize", init_params)

        # Send initialized notification
        await self._notify("initialized", {})

        return init_result

    async def _read_responses(self) -> None:
        """Read and dispatch responses from server."""
        if not self.process or not self.process.stdout:
            return

        while True:
            try:
                # Read headers
                headers = {}
                while True:
                    line = await self.process.stdout.readline()
                    if not line:
                        return
                    line = line.decode("utf-8").strip()
                    if not line:
                        break
                    key, value = line.split(": ", 1)
                    headers[key] = value

                # Read body
                content_length = int(headers["Content-Length"])
                body = await self.process.stdout.readexactly(content_length)
                message = json.loads(body.decode("utf-8"))

                # Dispatch response
                if "id" in message and message["id"] in self._response_futures:
                    future = self._response_futures.pop(message["id"])
                    if "result" in message:
                        future.set_result(message["result"])
                    elif "error" in message:
                        future.set_exception(
                            Exception(f"LSP error: {message['error']}")
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error reading response: {e}")
                break

    async def _request(self, method: str, params: Any) -> Any:
        """Send request and wait for response."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Server not started")

        msg_id = self._next_id
        self._next_id += 1

        # Convert params to dict if it's an lsprotocol type
        if hasattr(params, "__class__") and hasattr(params.__class__, "__name__"):
            params_dict = self.converter.unstructure(params)
        else:
            params_dict = params

        message = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params_dict,
        }

        # Serialize and send
        content = json.dumps(message)
        content_bytes = content.encode("utf-8")
        headers = f"Content-Length: {len(content_bytes)}\r\n\r\n"

        self.process.stdin.write(headers.encode("utf-8"))
        self.process.stdin.write(content_bytes)
        await self.process.stdin.drain()

        # Wait for response
        future: asyncio.Future = asyncio.Future()
        self._response_futures[msg_id] = future

        return await asyncio.wait_for(future, timeout=5.0)

    async def _notify(self, method: str, params: Any) -> None:
        """Send notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Server not started")

        # Convert params to dict if it's an lsprotocol type
        if hasattr(params, "__class__") and hasattr(params.__class__, "__name__"):
            params_dict = self.converter.unstructure(params)
        else:
            params_dict = params

        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params_dict,
        }

        content = json.dumps(message)
        content_bytes = content.encode("utf-8")
        headers = f"Content-Length: {len(content_bytes)}\r\n\r\n"

        self.process.stdin.write(headers.encode("utf-8"))
        self.process.stdin.write(content_bytes)
        await self.process.stdin.drain()

    async def text_document_did_open(
        self, params: types.DidOpenTextDocumentParams
    ) -> None:
        """Send didOpen notification."""
        await self._notify("textDocument/didOpen", params)

    async def text_document_code_action(
        self, params: types.CodeActionParams
    ) -> list[types.CodeAction]:
        """Request code actions."""
        result = await self._request("textDocument/codeAction", params)
        return result or []

    async def shutdown(self) -> None:
        """Shutdown server."""
        if self.process and self.process.stdin:
            await self._request("shutdown", None)
            await self._notify("exit", None)

        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self.process:
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
