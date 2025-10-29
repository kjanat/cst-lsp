"""
Import resolution code actions for undefined symbols.

Provides two refactoring operations:
1. ImportSymbol: Add import for a single undefined symbol at cursor
2. ImportAll: Add all missing imports in current file

Uses SymbolFinder to locate symbols across project scope and
libcst's AddImportsVisitor to insert import statements. Validates
undefined symbols using libcst's ScopeProvider metadata.
"""

import itertools
from collections import defaultdict

import libcst as cst
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import CodeRange, MetadataWrapper, PositionProvider, ScopeProvider
from lsprotocol import types as lsp_types

from cst_lsp.symbols.symbol_finder import SymbolFinder

from .base import BaseCstLspCodeAction, code_ranges_interect


class NameAtLocationVisitor(cst.CSTVisitor):
    """
    Visitor to find the symbol name at a specific code location.

    Uses PositionProvider metadata to match node positions against
    the target location and extracts the symbol name if found.

    Attributes:
        target_location: Code range to search for a symbol
        name: Symbol name found at location (None if not found)
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, target_location: CodeRange):
        self.target_location = target_location
        self.name = None

    def visit_Name(self, node: cst.Name) -> None:
        position = self.get_metadata(PositionProvider, node)
        assert isinstance(position, CodeRange)
        if code_ranges_interect(position, self.target_location):
            self.name = node.value


def get_name_at_location(module: cst.Module, location: CodeRange) -> str | None:
    """
    Extract the symbol name at a specific code location.

    Args:
        module: Parsed libcst module
        location: Code range to search

    Returns:
        Symbol name at the location, or None if no symbol found
    """
    wrapper = MetadataWrapper(module)
    visitor = NameAtLocationVisitor(location)
    wrapper.visit(visitor)
    return visitor.name


class ImportSymbol(BaseCstLspCodeAction):
    """
    Code action to import a single undefined symbol.

    Analyzes the symbol at the cursor position, searches for it across
    the project using SymbolFinder, and adds the appropriate import
    statement using libcst's AddImportsVisitor.

    Attributes:
        symbol_finder: SymbolFinder instance for locating symbols
    """

    name = "Import Symbol"
    kind = lsp_types.CodeActionKind.RefactorExtract

    def __init__(self, symbol_finder: SymbolFinder) -> None:
        super().__init__()
        self.symbol_finder = symbol_finder

    def undefined_symbols(self, module: cst.Module, code_range: CodeRange):
        """
        Find all undefined symbols in the module.

        Uses libcst's ScopeProvider to identify symbols that are accessed
        but have no referents (i.e., not defined in any scope).

        Args:
            module: Parsed libcst module
            code_range: Code range to analyze (currently unused, analyzes whole module)

        Returns:
            Dict mapping symbol names to sets of CodeRange locations where
            they are used but undefined
        """
        wrapper = MetadataWrapper(module)
        scopes = set(wrapper.resolve(ScopeProvider).values())
        ranges = wrapper.resolve(PositionProvider)
        result = defaultdict(set)
        for scope in scopes:
            if not scope:
                continue
            for access in scope.accesses:
                if len(access.referents) == 0:
                    node = access.node
                    if not isinstance(node, cst.Name):
                        continue
                    location = ranges[node]
                    result[node.value].add(location)
        return result

    def is_valid(
        self,
        source: str,
        module: cst.Module,
        code_range: CodeRange,
    ) -> bool:
        """
        Check if the refactor is valid for the given code range.

        This method allows the refactor to fire if the name that's currently
        selected isn't defined in the current scope.
        """
        undefined_symbols = self.undefined_symbols(module, code_range)
        for location in itertools.chain.from_iterable(undefined_symbols.values()):
            if code_ranges_interect(location, code_range):
                return True
        return False

    def import_symbol(self, context: CodemodContext, symbol: str) -> str | None:
        """
        Add import for a symbol using SymbolFinder.

        Searches for the symbol across the project and adds the first
        matching import to the codemod context.

        Args:
            context: CodemodContext to accumulate imports
            symbol: Symbol name to import

        Returns:
            None (import is added to context)
        """
        matching_imports = self.symbol_finder.find_symbol(symbol)
        if not matching_imports:
            return None
        suggested_import = matching_imports[0]
        AddImportsVisitor.add_needed_import(
            context,
            suggested_import.module,
            suggested_import.symbol,
            suggested_import.alias,
        )
        return None

    def refactor(
        self,
        module: cst.Module,
        code_range: CodeRange,
    ) -> str | None:
        """
        Add import statement for the symbol at cursor.

        Finds the symbol name at the selected location, searches for it,
        and adds the appropriate import statement.

        Args:
            module: Parsed libcst module
            code_range: Selected code range (typically cursor position)

        Returns:
            Transformed source code with added import, or original code
            if symbol not found
        """
        symbol = get_name_at_location(module, code_range)
        if symbol is None:
            return module.code
        wrapper = cst.MetadataWrapper(module)
        context = CodemodContext()
        self.import_symbol(context, symbol)
        result = wrapper.visit(AddImportsVisitor(context))
        return result.code


class ImportAll(ImportSymbol):
    """
    Code action to import all undefined symbols in the file.

    Extends ImportSymbol to handle multiple undefined symbols at once.
    Only offered when there are 2+ undefined symbols in the file.

    Inherits:
        symbol_finder: SymbolFinder instance from ImportSymbol
    """

    name = "Import All Missing"
    kind = lsp_types.CodeActionKind.RefactorExtract

    def is_valid(
        self,
        source: str,
        module: cst.Module,
        code_range: CodeRange,
    ) -> bool:
        """
        Check if the refactor is valid for the given code range.

        Valid when the module has more than one undefined symbol, making
        bulk import more useful than single symbol import.

        Args:
            source: Full source code text
            module: Parsed libcst module
            code_range: Code range (unused, analyzes whole module)

        Returns:
            True if 2+ undefined symbols exist, False otherwise
        """
        return len(self.undefined_symbols(module, code_range)) > 1

    def refactor(
        self,
        module: cst.Module,
        code_range: CodeRange,
    ) -> str | None:
        """
        Add import statements for all undefined symbols.

        Finds all undefined symbols in the module, searches for each,
        and adds all import statements in a single transformation.

        Args:
            module: Parsed libcst module
            code_range: Code range (unused, analyzes whole module)

        Returns:
            Transformed source code with all imports added
        """
        context = CodemodContext()
        undefined_symbols = self.undefined_symbols(module, code_range)
        wrapper = cst.MetadataWrapper(module)
        context = CodemodContext()
        for symbol in undefined_symbols.keys():
            self.import_symbol(context, symbol)
        result = wrapper.visit(AddImportsVisitor(context))
        return result.code
