"""
Side-by-Side Diff Generator.

Generates side-by-side diff views for PRD changes,
with word-level highlighting for better comparison.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any

from context_graph.core.models import (
    DiffLine,
    DiffStats,
    SideBySideDiff,
    WordChange,
    PRDChange,
)


class SideBySideDiffGenerator:
    """Generates side-by-side diffs from PRD changes."""
    
    # Number of context lines to show before and after the change
    CONTEXT_LINES_BEFORE = 3
    CONTEXT_LINES_AFTER = 3
    
    def generate_diff(
        self,
        change: PRDChange,
        prd_content: str,
        file_name: str = "PRD.md",
    ) -> SideBySideDiff:
        """
        Generate a side-by-side diff for a PRD change with context.
        
        Args:
            change: The PRD change with current and suggested text
            prd_content: Full PRD content for context
            file_name: Name of the PRD file
            
        Returns:
            SideBySideDiff with aligned original and suggested lines, including context
        """
        prd_lines = prd_content.split("\n") if prd_content else []
        
        # Get the change location
        start_line = change.start_line if change.start_line else 1
        end_line = change.end_line if change.end_line else start_line
        
        # Ensure valid line numbers (0-indexed internally, 1-indexed for display)
        start_idx = max(0, start_line - 1)
        end_idx = min(len(prd_lines), end_line)
        
        # Calculate context boundaries
        context_start_idx = max(0, start_idx - self.CONTEXT_LINES_BEFORE)
        context_end_idx = min(len(prd_lines), end_idx + self.CONTEXT_LINES_AFTER)
        
        # Extract context lines before the change
        before_context = prd_lines[context_start_idx:start_idx]
        
        # Extract the original text at the change location
        original_at_location = prd_lines[start_idx:end_idx]
        
        # Extract context lines after the change
        after_context = prd_lines[end_idx:context_end_idx]
        
        # Get the suggested text
        suggested_text = change.suggested_text or ""
        suggested_lines = suggested_text.split("\n") if suggested_text else []
        
        # Build the original side: before_context + original_at_location + after_context
        original_with_context = before_context + original_at_location + after_context
        
        # Build the suggested side: before_context + suggested_lines + after_context
        suggested_with_context = before_context + suggested_lines + after_context
        
        # Generate aligned diff lines with proper line numbers
        diff_original, diff_suggested, stats = self._align_lines_with_context(
            original_with_context,
            suggested_with_context,
            context_start_idx + 1,  # 1-indexed line number
            len(before_context),
            len(original_at_location),
            len(suggested_lines),
        )
        
        return SideBySideDiff(
            change_id=str(change.id),
            file_name=file_name,
            section=change.section,
            original_lines=diff_original,
            suggested_lines=diff_suggested,
            stats=stats,
        )
    
    def _align_lines_with_context(
        self,
        original: list[str],
        suggested: list[str],
        start_line_num: int,
        before_context_count: int,
        original_change_count: int,
        suggested_change_count: int,
    ) -> tuple[list[DiffLine], list[DiffLine], DiffStats]:
        """
        Align lines with context awareness.
        
        Marks context lines as unchanged and change lines appropriately.
        """
        diff_original: list[DiffLine] = []
        diff_suggested: list[DiffLine] = []
        stats = DiffStats()
        
        orig_line_num = start_line_num
        sugg_line_num = start_line_num
        
        # Process before context (always unchanged)
        for i in range(before_context_count):
            if i < len(original) and i < len(suggested):
                diff_original.append(DiffLine(
                    line_number=orig_line_num,
                    content=original[i],
                    status="unchanged",
                ))
                diff_suggested.append(DiffLine(
                    line_number=sugg_line_num,
                    content=suggested[i],
                    status="unchanged",
                ))
                orig_line_num += 1
                sugg_line_num += 1
        
        # Calculate where the change region starts and ends in the arrays
        change_start = before_context_count
        orig_change_end = change_start + original_change_count
        sugg_change_end = change_start + suggested_change_count
        
        # Calculate where after context starts
        after_context_start_orig = orig_change_end
        after_context_start_sugg = sugg_change_end
        
        # Process the change region
        orig_change_lines = original[change_start:orig_change_end] if change_start < len(original) else []
        sugg_change_lines = suggested[change_start:sugg_change_end] if change_start < len(suggested) else []
        
        # Use the standard alignment for the change region
        if orig_change_lines or sugg_change_lines:
            change_orig, change_sugg, change_stats = self._align_lines(
                orig_change_lines,
                sugg_change_lines,
                orig_line_num,
            )
            diff_original.extend(change_orig)
            diff_suggested.extend(change_sugg)
            stats.lines_added = change_stats.lines_added
            stats.lines_removed = change_stats.lines_removed
            stats.lines_modified = change_stats.lines_modified
            
            # Update line numbers
            orig_line_num += original_change_count
            sugg_line_num += suggested_change_count
        
        # Process after context (always unchanged)
        after_context_orig = original[after_context_start_orig:] if after_context_start_orig < len(original) else []
        after_context_sugg = suggested[after_context_start_sugg:] if after_context_start_sugg < len(suggested) else []
        
        # After context should be the same on both sides
        after_count = min(len(after_context_orig), len(after_context_sugg))
        for i in range(after_count):
            diff_original.append(DiffLine(
                line_number=orig_line_num,
                content=after_context_orig[i],
                status="unchanged",
            ))
            diff_suggested.append(DiffLine(
                line_number=sugg_line_num,
                content=after_context_sugg[i],
                status="unchanged",
            ))
            orig_line_num += 1
            sugg_line_num += 1
        
        return diff_original, diff_suggested, stats
    
    def generate_full_file_diff(
        self,
        original_content: str,
        updated_content: str,
        file_name: str = "PRD.md",
        context_lines: int = 3,
    ) -> SideBySideDiff:
        """
        Generate a side-by-side diff for the entire file.
        
        Args:
            original_content: Original file content
            updated_content: Updated file content
            file_name: Name of the file
            context_lines: Number of context lines around changes
            
        Returns:
            SideBySideDiff for the entire file
        """
        original_lines = original_content.split("\n")
        updated_lines = updated_content.split("\n")
        
        diff_original, diff_suggested, stats = self._align_lines(
            original_lines,
            updated_lines,
            start_line=1,
        )
        
        return SideBySideDiff(
            change_id="full_file",
            file_name=file_name,
            section="Full File",
            original_lines=diff_original,
            suggested_lines=diff_suggested,
            stats=stats,
        )
    
    def _align_lines(
        self,
        original: list[str],
        suggested: list[str],
        start_line: int = 1,
    ) -> tuple[list[DiffLine], list[DiffLine], DiffStats]:
        """
        Align original and suggested lines for side-by-side display.
        
        Uses difflib to find matching and differing lines,
        then aligns them with empty placeholders where needed.
        """
        diff_original: list[DiffLine] = []
        diff_suggested: list[DiffLine] = []
        
        stats = DiffStats()
        
        # Use SequenceMatcher for better alignment
        matcher = difflib.SequenceMatcher(None, original, suggested)
        
        orig_line_num = start_line
        sugg_line_num = start_line
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                # Lines are the same
                for i in range(i2 - i1):
                    diff_original.append(DiffLine(
                        line_number=orig_line_num,
                        content=original[i1 + i],
                        status="unchanged",
                    ))
                    diff_suggested.append(DiffLine(
                        line_number=sugg_line_num,
                        content=suggested[j1 + i],
                        status="unchanged",
                    ))
                    orig_line_num += 1
                    sugg_line_num += 1
                    
            elif tag == "replace":
                # Lines are modified - show both with word-level diff
                orig_count = i2 - i1
                sugg_count = j2 - j1
                max_count = max(orig_count, sugg_count)
                
                for i in range(max_count):
                    if i < orig_count and i < sugg_count:
                        # Both lines exist - show as modified with word changes
                        orig_text = original[i1 + i]
                        sugg_text = suggested[j1 + i]
                        orig_words, sugg_words = self._get_word_changes(orig_text, sugg_text)
                        
                        diff_original.append(DiffLine(
                            line_number=orig_line_num,
                            content=orig_text,
                            status="modified",
                            word_changes=orig_words,
                        ))
                        diff_suggested.append(DiffLine(
                            line_number=sugg_line_num,
                            content=sugg_text,
                            status="modified",
                            word_changes=sugg_words,
                        ))
                        orig_line_num += 1
                        sugg_line_num += 1
                        stats.lines_modified += 1
                    elif i < orig_count:
                        # Extra original line (deleted)
                        diff_original.append(DiffLine(
                            line_number=orig_line_num,
                            content=original[i1 + i],
                            status="deleted",
                        ))
                        diff_suggested.append(DiffLine(
                            line_number=None,
                            content="",
                            status="empty",
                        ))
                        orig_line_num += 1
                        stats.lines_removed += 1
                    else:
                        # Extra suggested line (added)
                        diff_original.append(DiffLine(
                            line_number=None,
                            content="",
                            status="empty",
                        ))
                        diff_suggested.append(DiffLine(
                            line_number=sugg_line_num,
                            content=suggested[j1 + i],
                            status="added",
                        ))
                        sugg_line_num += 1
                        stats.lines_added += 1
                        
            elif tag == "delete":
                # Lines only in original (deleted)
                for i in range(i2 - i1):
                    diff_original.append(DiffLine(
                        line_number=orig_line_num,
                        content=original[i1 + i],
                        status="deleted",
                    ))
                    diff_suggested.append(DiffLine(
                        line_number=None,
                        content="",
                        status="empty",
                    ))
                    orig_line_num += 1
                    stats.lines_removed += 1
                    
            elif tag == "insert":
                # Lines only in suggested (added)
                for i in range(j2 - j1):
                    diff_original.append(DiffLine(
                        line_number=None,
                        content="",
                        status="empty",
                    ))
                    diff_suggested.append(DiffLine(
                        line_number=sugg_line_num,
                        content=suggested[j1 + i],
                        status="added",
                    ))
                    sugg_line_num += 1
                    stats.lines_added += 1
        
        return diff_original, diff_suggested, stats
    
    def _get_word_changes(
        self,
        original: str,
        suggested: str,
    ) -> tuple[list[WordChange], list[WordChange]]:
        """
        Find word-level changes between two lines.
        
        Returns lists of WordChange for both original and suggested,
        marking which parts were removed/added.
        """
        orig_changes: list[WordChange] = []
        sugg_changes: list[WordChange] = []
        
        # Tokenize by words while keeping track of positions
        orig_words = self._tokenize_with_positions(original)
        sugg_words = self._tokenize_with_positions(suggested)
        
        # Get just the words for comparison
        orig_word_list = [w for w, _, _ in orig_words]
        sugg_word_list = [w for w, _, _ in sugg_words]
        
        # Use SequenceMatcher on words
        matcher = difflib.SequenceMatcher(None, orig_word_list, sugg_word_list)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "delete":
                # Words removed from original
                for i in range(i1, i2):
                    _, start, end = orig_words[i]
                    orig_changes.append(WordChange(
                        start=start,
                        end=end,
                        change_type="removed",
                    ))
            elif tag == "insert":
                # Words added in suggested
                for j in range(j1, j2):
                    _, start, end = sugg_words[j]
                    sugg_changes.append(WordChange(
                        start=start,
                        end=end,
                        change_type="added",
                    ))
            elif tag == "replace":
                # Words changed
                for i in range(i1, i2):
                    _, start, end = orig_words[i]
                    orig_changes.append(WordChange(
                        start=start,
                        end=end,
                        change_type="removed",
                    ))
                for j in range(j1, j2):
                    _, start, end = sugg_words[j]
                    sugg_changes.append(WordChange(
                        start=start,
                        end=end,
                        change_type="added",
                    ))
        
        return orig_changes, sugg_changes
    
    def _tokenize_with_positions(self, text: str) -> list[tuple[str, int, int]]:
        """
        Tokenize text into words with their start and end positions.
        
        Returns list of (word, start_pos, end_pos) tuples.
        """
        tokens: list[tuple[str, int, int]] = []
        
        # Match words and keep track of positions
        for match in re.finditer(r'\S+', text):
            tokens.append((match.group(), match.start(), match.end()))
        
        return tokens


def generate_side_by_side_diff(
    change: PRDChange,
    prd_content: str,
    file_name: str = "PRD.md",
) -> SideBySideDiff:
    """
    Convenience function to generate a side-by-side diff.
    """
    generator = SideBySideDiffGenerator()
    return generator.generate_diff(change, prd_content, file_name)
