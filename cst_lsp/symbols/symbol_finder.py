"""
Symbol finding for import resolution using ripgrep.

This module provides fast symbol search across Python projects using ripgrep.
Symbols are discovered through three tiers:
1. Existing imports in other project files (most reliable)
2. Symbols defined in __all__ declarations in __init__.py files
3. Top-level class/function definitions

Results are cached per session for performance.
"""

import json
import re
import subprocess
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

IMPORT_PATTERN = re.compile(r"import\s+(\w+)(?:\s+as\s+(\w+))?")


@dataclass(frozen=True)
class SuggestedImport:
    """
    Represents a suggested import for a symbol.

    Attributes:
        module: The module to import from (e.g., 'os.path')
        symbol: The symbol name to import (None for 'import module' style)
        alias: Optional alias if symbol is imported as different name
    """

    module: str
    symbol: str | None
    alias: str | None


@dataclass
class SymbolFinder(ABC):
    """
    Abstract interface for finding Python symbols across project scope.

    Implementations search for symbols through tiered strategies:
    1. Existing imports in other modules (most reliable)
    2. Symbols defined in __all__ declarations
    3. Top-level class/function definitions

    Factory method `create()` returns platform-appropriate implementation
    (RipGrepSymbolFinder if ripgrep is available, None otherwise).

    Attributes:
        python_path: Path to Python executable for sys.path discovery
        root: Project root directory to search
        _paths_cache: Cached sys.path list
    """

    python_path: Path
    root: Path
    _paths_cache: list[Path] | None = None

    @abstractmethod
    def find_symbol(self, symbol: str) -> list[SuggestedImport]:
        """
        Find import suggestions for a symbol.

        Args:
            symbol: Symbol name to search for

        Returns:
            List of SuggestedImport objects, ordered by relevance
        """
        pass

    def paths(self) -> list[Path]:
        """
        Get Python sys.path directories to search.

        Executes Python to discover sys.path and caches the result.

        Returns:
            List of Path objects representing directories in sys.path
        """
        if self._paths_cache is None:
            result = subprocess.run(
                [
                    str(self.python_path),
                    "-c",
                    r'import sys; print("\n".join(sys.path))',
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self._paths_cache = [
                Path(x) for x in result.stdout.splitlines() if x.strip()
            ]
        return self._paths_cache

    @classmethod
    def create(cls, python_path: Path, root: Path) -> "SymbolFinder | None":
        """
        Factory method to create a SymbolFinder implementation.

        Checks if ripgrep is available and returns RipGrepSymbolFinder
        if found, None otherwise.

        Args:
            python_path: Path to Python executable
            root: Project root directory

        Returns:
            RipGrepSymbolFinder if ripgrep is available, None otherwise
        """
        try:
            subprocess.run(["rg", "--version"], check=True, capture_output=True)
            return RipGrepSymbolFinder(python_path, root)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None


@dataclass
class RipGrepSymbolFinder(SymbolFinder):
    """
    A symbol finder that uses ripgrep to search for symbols in Python files.

    This class extends the SymbolFinder abstract base class and implements
    methods to find symbols using the ripgrep command-line tool. It can
    search for existing imports, symbols in __all__ declarations, and
    top-level class or function definitions.
    """

    def __post_init__(self):
        self._import_cache: dict[str, list[SuggestedImport]] = {}
        self._all_cache: dict[str, list[SuggestedImport]] = {}
        self._top_level_cache: dict[str, list[SuggestedImport]] = {}

    def _ripgrep_generator(
        self, pattern: str, root: Path, glob: str = "*.py", max_hits: int = 25
    ):
        """
        Generate ripgrep search results as (path, line) tuples.

        Executes ripgrep with JSON output and yields matching lines.
        Limits results to max_hits and avoids site-packages directories.

        Args:
            pattern: Regular expression pattern to search for
            root: Directory to search in
            glob: File glob pattern (default: "*.py")
            max_hits: Maximum number of results to return (default: 25)

        Yields:
            Tuples of (file_path, matching_line)
        """
        cmd = [
            "rg",
            "-m1",
            "-g",
            glob,
            "--no-ignore",
            "--multiline",
            pattern,
            str(root),
            "--json",
        ]
        if (root / "site-packages").is_dir():
            # Avoid crawling `site-packages` from it's parent since it won't
            # be valid to import from the parent anyway.
            cmd.extend(["-g", "!{**/site-packages/*}"])
        with subprocess.Popen(
            cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ) as process:
            if not process.stdout:
                return
            hits = 0
            for json_line in process.stdout:
                try:
                    data = json.loads(json_line)
                    if (
                        "data" in data
                        and "lines" in data["data"]
                        and "path" in data["data"]
                    ):
                        line: str = data["data"]["lines"]["text"].strip()
                        path: str = data["data"]["path"]["text"].strip()
                        yield path, line
                        hits += 1
                    if hits >= max_hits:
                        return
                except json.JSONDecodeError:
                    continue

    def find_existing_imports(self, symbol: str) -> list[SuggestedImport]:
        """
        Find existing imports of the given symbol in the project.

        This method searches for import statements that import the specified symbol,
        either directly or as an alias. It handles both 'import' and 'from ... import' statements.

        Args:
            symbol (str): The symbol to search for in import statements.

        Returns:
            list[SuggestedImport]: A list of SuggestedImport objects, where each object contains:
                - The module from which the symbol is imported
                - The original name of the symbol (if using 'from ... import')
                - The alias of the symbol (if an alias is used)
            The list is sorted by frequency of occurrence, with the most common imports first.
        """
        if symbol in self._import_cache:
            return self._import_cache[symbol]

        pattern = rf"import\s+(?:\(\s*(?:\w+,\s*)*)?(?:(?:\w+\s+as\s+))?{symbol}(?:,|\s+|\)|$)"
        imports = []
        for _, line in self._ripgrep_generator(pattern, self.root):
            if line.startswith("from"):
                if match := re.search(
                    rf"from\s+(\w+)\s+import.*[,\s]+(\w+)\s+as\s+({symbol})", line
                ):
                    imports.append(
                        SuggestedImport(match.group(1), match.group(2), match.group(3))
                    )
                else:
                    imports.append(SuggestedImport(line.split()[1], symbol, None))
            elif match := re.search(IMPORT_PATTERN, line):
                module, alias = match.groups()
                imports.append(
                    SuggestedImport(module, None, alias if alias == symbol else None)
                )
        counter = Counter(imports)
        sorted_imports = sorted(counter.items(), key=lambda x: x[1], reverse=True)
        result = [item[0] for item in sorted_imports]
        self._import_cache[symbol] = result
        return result

    def find_symbol_from_all(self, symbol: str) -> list[SuggestedImport]:
        """
        Search for the given symbol in __all__ declarations within __init__.py files.

        Modules add symbols to their `__all__` in their `__init__.py` to make importing
        those symbols easier.  It's also much faster to check these first before doing
        a full scan.

        Args:
            symbol (str): The symbol to search for in __all__ declarations.

        Returns:
            list[SuggestedImport]: A list of SuggestedImport objects containing:
                - The module path where the symbol was found in __all__
                - The symbol itself
                - None (as no alias is used in __all__ declarations)
        """
        if symbol in self._all_cache:
            return self._all_cache[symbol]

        result = self._find_pattern_in_files(
            symbol,
            f"__all__\\s*=\\s*(?:\\(|\\[)(?s:.)*[\"']{symbol}[\"']",
            glob="__init__.py",
            use_parent=True,
        )
        self._all_cache[symbol] = result
        return result

    def find_top_level_symbol(self, symbol: str) -> list[SuggestedImport]:
        """
        Search for top-level class or function definitions of the given symbol.

        This method looks for class or function definitions that match the provided symbol
        at the top level of Python files.

        Args:
            symbol (str): The symbol to search for in top-level definitions.

        Returns:
            list[SuggestedImport]: A list of SuggestedImport objects containing:
                - The module path where the symbol was found
                - The symbol itself
                - None (as no alias is used in top-level definitions)
        """
        if symbol in self._top_level_cache:
            return self._top_level_cache[symbol]

        result = self._find_pattern_in_files(
            symbol, rf"(?:class|def)\s+{symbol}(?:\(|:)"
        )
        self._top_level_cache[symbol] = result
        return result

    def _find_pattern_in_files(
        self, symbol: str, pattern: str, glob: str = "*.py", use_parent: bool = False
    ) -> list[SuggestedImport]:
        """
        Search for a pattern across Python path and generate import suggestions.

        Args:
            symbol: Symbol name for the import suggestion
            pattern: Regular expression to search for
            glob: File glob pattern (default: "*.py")
            use_parent: If True, use parent directory as module path (for __init__.py)

        Returns:
            List of SuggestedImport objects for matching files
        """
        matches = []
        for root in self.paths():
            if not root.is_dir():
                continue
            for path, _ in self._ripgrep_generator(pattern, root=root, glob=glob):
                relative_path = Path(path).relative_to(root)
                if use_parent:
                    relative_path = relative_path.parent
                module_path = str(relative_path.with_suffix("")).replace("/", ".")
                if all(part.isidentifier() for part in module_path.split(".")):
                    matches.append(SuggestedImport(module_path, symbol, None))
        return matches

    def find_symbol(self, symbol: str) -> list[SuggestedImport]:
        """
        Find import suggestions for a symbol using three-tier search.

        Search strategy (in order of reliability):
        1. Existing imports in project (most reliable)
        2. __all__ declarations in __init__.py
        3. Top-level class/function definitions

        Args:
            symbol: Symbol name to search for

        Returns:
            List of SuggestedImport objects, ordered by relevance.
            Returns first non-empty result from the search tiers.
        """
        return (
            self.find_existing_imports(symbol)
            or self.find_symbol_from_all(symbol)
            or self.find_top_level_symbol(symbol)
        )
