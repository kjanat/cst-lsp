"""
Base classes and utilities for code action transformations.

This module defines the abstract interface that all refactoring operations
must implement. Code actions analyze selected code ranges and transform them
using libcst visitors.

Key components:
    - BaseCstLspCodeAction: Abstract base class for all refactorings
    - code_ranges_interect: Utility for checking code range overlap
"""

import textwrap
from abc import ABC, abstractmethod
from typing import ClassVar

import libcst as cst
from libcst.metadata import CodeRange
from lsprotocol.types import CodeActionKind


def code_ranges_interect(first: CodeRange, second: CodeRange):
    """
    Check if two code ranges overlap or intersect.

    Compares two CodeRange objects to determine if they share any overlapping
    lines or columns. Used to determine if a refactoring should apply to
    a user selection.

    Args:
        first: The first code range to compare
        second: The second code range to compare

    Returns:
        True if ranges overlap, False otherwise

    Note:
        Function name has typo: should be "intersect" but kept for compatibility
    """
    overlap_start_line = max(first.start.line, second.start.line)
    overlap_end_line = min(first.end.line, second.end.line)
    if overlap_start_line > overlap_end_line:
        return False
    if first.start.line == first.end.line and second.start.line == second.end.line:
        overlap_start_column = max(first.start.column, second.start.column)
        overlap_end_column = min(first.end.column, second.end.column)
        if overlap_start_column > overlap_end_column:
            return False
    return True


class BaseCstLspCodeAction(ABC):
    """
    Abstract base class for all code action refactorings.

    Defines the interface that all refactoring operations must implement.
    Subclasses must provide a name, LSP code action kind, and implement
    the refactor() method to perform the actual transformation.

    The default is_valid() implementation checks if the selected code
    can be parsed as valid Python. Subclasses can override for more
    specific validation logic.

    Attributes:
        name: Human-readable name for the refactoring (e.g., "Extract Method")
        kind: LSP CodeActionKind for categorizing the refactoring
    """

    name: ClassVar[str]
    kind: ClassVar[CodeActionKind]

    def is_valid(self, source: str, module: cst.Module, code_range: CodeRange) -> bool:
        """
        Check if the selected code range is valid for this refactoring.

        Default implementation extracts the selected lines, dedents them,
        and attempts to parse as a Python module. Subclasses can override
        for more specific validation logic.

        Args:
            source: Full source code text
            module: Parsed libcst module
            code_range: Selected code range (1-indexed lines)

        Returns:
            True if the refactoring can be applied to this selection,
            False otherwise
        """
        lines = source.splitlines()
        dedented = textwrap.dedent(
            "\n".join(lines[code_range.start.line - 1 : code_range.end.line])
        )
        try:
            cst.parse_module(dedented)
            return True
        except Exception:
            return False

    @abstractmethod
    def refactor(self, module: cst.Module, code_range: CodeRange) -> str | None:
        """
        Perform the refactoring transformation.

        Subclasses must implement this method to apply their specific
        transformation using libcst visitors and return the modified
        source code.

        Args:
            module: Parsed libcst module to transform
            code_range: Selected code range to refactor (1-indexed lines)

        Returns:
            Transformed source code as a string, or None if the
            refactoring cannot be applied

        Note:
            This method should not raise exceptions. Return None instead.
        """
        pass
