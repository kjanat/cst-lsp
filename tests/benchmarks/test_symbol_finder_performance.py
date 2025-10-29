"""
Performance benchmarks for RipGrepSymbolFinder.

Measures search performance, caching effectiveness, and scalability
across different project sizes and search patterns.

Run with: pytest tests/benchmarks/ --benchmark-only
"""

import sys
from pathlib import Path

import pytest

from cst_lsp.symbols.symbol_finder import RipGrepSymbolFinder


@pytest.fixture(scope="module")
def small_project(tmp_path_factory):
    """
    Small project (10 files, ~500 lines total).

    Typical single-module Python project structure.
    """
    tmp_path = tmp_path_factory.mktemp("small_project")
    project = tmp_path / "small"
    project.mkdir()

    # Create 10 Python files with common imports
    for i in range(10):
        file = project / f"module_{i}.py"
        content = f'''"""Module {i}."""

from pathlib import Path
from typing import Optional
import json
import os


class DataProcessor:
    """Process data from files."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        """Load data from file."""
        with open(self.path) as f:
            return json.load(f)


def process_file(filepath: str) -> Optional[dict]:
    """Process a single file."""
    path = Path(filepath)
    if path.exists():
        processor = DataProcessor(path)
        return processor.load()
    return None
'''
        file.write_text(content)

    return project


@pytest.fixture(scope="module")
def medium_project(tmp_path_factory):
    """
    Medium project (50 files, ~5000 lines total).

    Typical multi-package Python application.
    """
    tmp_path = tmp_path_factory.mktemp("medium_project")
    project = tmp_path / "medium"
    project.mkdir()

    # Create 5 packages with 10 modules each
    for pkg in range(5):
        pkg_dir = project / f"package_{pkg}"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text('"""Package."""\n')

        for i in range(10):
            file = pkg_dir / f"module_{i}.py"
            content = f'''"""Module {i} in package {pkg}."""

from pathlib import Path
from typing import Optional, List, Dict
import json
import os
import asyncio


class AsyncDataProcessor:
    """Process data asynchronously."""

    def __init__(self, paths: List[Path]):
        self.paths = paths
        self._cache: Dict[str, dict] = {{}}

    async def load_all(self) -> List[dict]:
        """Load all files."""
        tasks = [self._load_one(p) for p in self.paths]
        return await asyncio.gather(*tasks)

    async def _load_one(self, path: Path) -> dict:
        """Load single file."""
        if str(path) in self._cache:
            return self._cache[str(path)]
        with open(path) as f:
            data = json.load(f)
            self._cache[str(path)] = data
            return data


def batch_process(directory: Path) -> List[dict]:
    """Process all files in directory."""
    processor = AsyncDataProcessor(list(directory.glob("*.json")))
    return asyncio.run(processor.load_all())
'''
            file.write_text(content)

    return project


@pytest.fixture(scope="module")
def large_project(tmp_path_factory):
    """
    Large project (200 files, ~20000 lines total).

    Simulates large open-source Python project.
    """
    tmp_path = tmp_path_factory.mktemp("large_project")
    project = tmp_path / "large"
    project.mkdir()

    # Create 20 packages with 10 modules each
    for pkg in range(20):
        pkg_dir = project / f"pkg_{pkg}"
        pkg_dir.mkdir()
        (pkg_dir / "__init__.py").write_text(f'"""Package {pkg}."""\n')

        for i in range(10):
            file = pkg_dir / f"mod_{i}.py"
            content = f'''"""Module {pkg}.{i}."""

from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import json
import os
import asyncio
import logging


logger = logging.getLogger(__name__)


class Status(Enum):
    """Processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingResult:
    """Result of data processing."""
    status: Status
    data: Optional[dict]
    error: Optional[str]


class AdvancedProcessor:
    """Advanced data processing with error handling."""

    def __init__(
        self,
        paths: List[Path],
        validator: Optional[Callable[[dict], bool]] = None,
    ):
        self.paths = paths
        self.validator = validator or (lambda x: True)
        self._results: List[ProcessingResult] = []

    async def process_all(self) -> List[ProcessingResult]:
        """Process all files with error handling."""
        logger.info(f"Processing {{len(self.paths)}} files")
        tasks = [self._process_with_retry(p, max_retries=3) for p in self.paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if isinstance(r, ProcessingResult) else
                ProcessingResult(Status.FAILED, None, str(r)) for r in results]

    async def _process_with_retry(
        self, path: Path, max_retries: int
    ) -> ProcessingResult:
        """Process with retries."""
        for attempt in range(max_retries):
            try:
                return await self._process_one(path)
            except Exception as e:
                if attempt == max_retries - 1:
                    return ProcessingResult(Status.FAILED, None, str(e))
                await asyncio.sleep(0.1 * (attempt + 1))
        return ProcessingResult(Status.FAILED, None, "Max retries exceeded")

    async def _process_one(self, path: Path) -> ProcessingResult:
        """Process single file."""
        if not path.exists():
            return ProcessingResult(Status.FAILED, None, "File not found")

        with open(path) as f:
            data = json.load(f)

        if self.validator(data):
            return ProcessingResult(Status.COMPLETED, data, None)
        return ProcessingResult(Status.FAILED, None, "Validation failed")
'''
            file.write_text(content)

    return project


# Benchmark: Symbol Search Performance


@pytest.mark.benchmark(group="search-common-symbol")
def test_search_common_symbol_small(benchmark, small_project):
    """Benchmark searching for common symbol (Path) in small project."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=small_project)

    def search():
        return finder.find_symbol("Path")

    results = benchmark(search)
    assert len(results) > 0, "Should find Path in project"


@pytest.mark.benchmark(group="search-common-symbol")
def test_search_common_symbol_medium(benchmark, medium_project):
    """Benchmark searching for common symbol (Path) in medium project."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=medium_project)

    def search():
        return finder.find_symbol("Path")

    results = benchmark(search)
    assert len(results) > 0, "Should find Path in project"


@pytest.mark.benchmark(group="search-common-symbol")
def test_search_common_symbol_large(benchmark, large_project):
    """Benchmark searching for common symbol (Path) in large project."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=large_project)

    def search():
        return finder.find_symbol("Path")

    results = benchmark(search)
    assert len(results) > 0, "Should find Path in project"


# Benchmark: Caching Effectiveness


@pytest.mark.benchmark(group="cache-effectiveness")
def test_cache_first_vs_second_search(benchmark, medium_project):
    """Benchmark cache effectiveness (first vs second search)."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=medium_project)

    # Prime cache with first search
    first_result = finder.find_symbol("Path")
    assert len(first_result) > 0

    # Benchmark second search (should hit cache)
    def search_cached():
        return finder.find_symbol("Path")

    results = benchmark(search_cached)
    assert results == first_result, "Cached result should match first"


@pytest.mark.benchmark(group="cache-effectiveness")
def test_multiple_symbol_searches(benchmark, medium_project):
    """Benchmark searching multiple different symbols (cache misses)."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=medium_project)

    symbols = ["Path", "Optional", "List", "Dict", "asyncio", "json"]

    def search_multiple():
        results = []
        for symbol in symbols:
            results.append(finder.find_symbol(symbol))
        return results

    all_results = benchmark(search_multiple)
    assert all(len(r) > 0 for r in all_results), "Should find all symbols"


# Benchmark: Search Pattern Complexity


@pytest.mark.benchmark(group="search-patterns")
def test_search_class_definition(benchmark, large_project):
    """Benchmark searching for class definitions (performance only, no accuracy check)."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=large_project)

    def search():
        return finder.find_symbol("AdvancedProcessor")

    # Benchmark measures search performance, not whether results are found
    benchmark(search)


@pytest.mark.benchmark(group="search-patterns")
def test_search_function_definition(benchmark, large_project):
    """Benchmark searching for function definitions (performance only, no accuracy check)."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=large_project)

    def search():
        return finder.find_symbol("batch_process")

    # Benchmark measures search performance, not whether results are found
    benchmark(search)


@pytest.mark.benchmark(group="search-patterns")
def test_search_enum_definition(benchmark, large_project):
    """Benchmark searching for enum definitions (performance only, no accuracy check)."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=large_project)

    def search():
        return finder.find_symbol("Status")

    # Benchmark measures search performance, not whether results are found
    benchmark(search)


# Benchmark: Scalability Analysis


@pytest.mark.benchmark(group="scalability")
def test_scalability_10_files(benchmark, small_project):
    """Scalability: 10 files."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=small_project)

    def search():
        return finder.find_symbol("DataProcessor")

    benchmark(search)


@pytest.mark.benchmark(group="scalability")
def test_scalability_50_files(benchmark, medium_project):
    """Scalability: 50 files."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=medium_project)

    def search():
        return finder.find_symbol("AsyncDataProcessor")

    benchmark(search)


@pytest.mark.benchmark(group="scalability")
def test_scalability_200_files(benchmark, large_project):
    """Scalability: 200 files."""
    finder = RipGrepSymbolFinder(python_path=Path(sys.executable), root=large_project)

    def search():
        return finder.find_symbol("AdvancedProcessor")

    benchmark(search)
