"""
Shared fixtures and configuration for e2e LSP tests.

Provides base fixtures for LSP client/server communication, sample projects,
and common test utilities.
"""

import sys
from pathlib import Path

import pytest
import pytest_lsp
from lsprotocol import types
from pytest_lsp import ClientServerConfig, LanguageClient, client_capabilities


@pytest.fixture(scope="session")
def simple_project(tmp_path_factory) -> Path:
    """
    Create a simple 5-file Python project for testing.

    Structure:
        simple_project/
        ├── __init__.py
        ├── main.py      # Entry point using utils
        ├── utils.py     # Helper functions
        ├── models.py    # Simple class
        └── constants.py # Module constants

    Returns:
        Path to project root directory
    """
    tmp_path = tmp_path_factory.mktemp("test_projects")
    project = tmp_path / "simple_project"
    project.mkdir()

    # __init__.py
    (project / "__init__.py").write_text('"""Simple test project."""\n')

    # main.py
    (project / "main.py").write_text(
        """\"\"\"Main entry point.\"\"\"


def main():
    from utils import calculate_sum

    result = calculate_sum(10, 20)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
"""
    )

    # utils.py
    (project / "utils.py").write_text(
        """\"\"\"Utility functions.\"\"\"


def calculate_sum(a: int, b: int) -> int:
    \"\"\"Calculate sum of two numbers.\"\"\"
    return a + b


def calculate_product(a: int, b: int) -> int:
    \"\"\"Calculate product of two numbers.\"\"\"
    return a * b
"""
    )

    # models.py
    (project / "models.py").write_text(
        """\"\"\"Data models.\"\"\"


class User:
    \"\"\"Simple user model.\"\"\"

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def display_name(self) -> str:
        \"\"\"Get display name.\"\"\"
        return f"{self.name} <{self.email}>"
"""
    )

    # constants.py
    (project / "constants.py").write_text(
        """\"\"\"Project constants.\"\"\"

VERSION = "1.0.0"
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
"""
    )

    return project


@pytest_lsp.fixture(
    scope="module",
    config=ClientServerConfig(
        server_command=[sys.executable, "-m", "cst_lsp.server"],
    ),
)
async def client(lsp_client: LanguageClient, simple_project: Path):
    """
    LSP client connected to cst-lsp server.

    Automatically initializes server with simple_project as workspace root.
    Server is shutdown when fixture context exits.

    Yields:
        Connected and initialized LanguageClient instance
    """
    # Initialize session with workspace folder
    await lsp_client.initialize_session(
        types.InitializeParams(
            capabilities=client_capabilities("visual-studio-code"),
            root_uri=simple_project.as_uri(),
            workspace_folders=[
                types.WorkspaceFolder(
                    uri=simple_project.as_uri(),
                    name="simple_project",
                ),
            ],
        )
    )

    yield lsp_client  # Yield the actual client!

    # Shutdown
    await lsp_client.shutdown_session()


@pytest.fixture
def extract_method_sample():
    """Sample code for extract method testing."""
    return """def calculate_total(price: float, quantity: int) -> float:
    subtotal = price * quantity
    tax = subtotal * 0.08
    discount = subtotal * 0.1 if subtotal > 100 else 0
    return subtotal + tax - discount
"""


@pytest.fixture
def import_symbol_sample():
    """Sample code with undefined symbols for import testing."""
    return """def process_data(filename: str):
    path = Path(filename)
    data = json.load(path.open())
    return data
"""


@pytest.fixture
def async_function_sample():
    """Sample async function for async extraction testing."""
    return """async def fetch_data(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data
"""
