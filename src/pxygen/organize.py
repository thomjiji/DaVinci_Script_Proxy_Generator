"""File and folder organisation by path depth."""
from __future__ import annotations

from dataclasses import dataclass

from .paths import compute_key_path, path_name, path_parts, subfolder_key_from_parts

_BATCH_CONTAINER_NAMES = frozenset({"多机位", "纪录"})


@dataclass(frozen=True)
class FolderOption:
    """Display metadata for a selectable top-level folder."""

    full_path: str
    item_count: int


def parse_selection(choice: str, max_num: int) -> list[int]:
    """Parse a selection string such as '1 3 5-7' into sorted 0-based indices.

    Tokens are separated by whitespace (commas also tolerated); ranges use '-'.
    Numbers outside [1, max_num] are silently ignored.
    Invalid tokens are silently ignored.
    """
    indices: set[int] = set()
    for token in choice.replace(",", " ").split():
        if "-" in token:
            try:
                start_s, end_s = token.split("-", 1)
                start, end = int(start_s.strip()), int(end_s.strip())
                for n in range(start, end + 1):
                    idx = n - 1
                    if 0 <= idx < max_num:
                        indices.add(idx)
            except ValueError:
                continue
        else:
            try:
                idx = int(token) - 1
                if 0 <= idx < max_num:
                    indices.add(idx)
            except ValueError:
                continue
    return sorted(indices)


def is_batch_container(path: str) -> bool:
    """Return whether *path* is an optional category above camera folders."""
    return path_name(path) in _BATCH_CONTAINER_NAMES


def organize_json_mode_files(
    file_paths: list[str],
    in_depth: int,
    out_depth: int,
    *,
    items_are_directories: bool = False,
) -> dict[str, dict[str, list[str]]]:
    """Group file paths into ``{key_path: {subfolder_key: [file_paths]}}``

    *key_path* is the absolute path up to *in_depth* components.
    *subfolder_key* is the path fragment between *in_depth* and *out_depth*
    (empty string when depths are equal). Optional ``多机位`` and ``纪录``
    containers at *out_depth* are preserved, with their child camera folder
    included in the subfolder key. Files whose depth is less than *in_depth*
    are skipped.
    """
    organized: dict[str, dict[str, list[str]]] = {}
    for file_path in file_paths:
        parts = path_parts(file_path)
        key_path = compute_key_path(parts, in_depth)
        if key_path is None:
            continue
        effective_out_depth = out_depth
        trailing_item_parts = 0 if items_are_directories else 1
        if (
            out_depth > in_depth
            and len(parts) > out_depth + trailing_item_parts
            and parts[out_depth - 1] in _BATCH_CONTAINER_NAMES
        ):
            effective_out_depth += 1
        if effective_out_depth > in_depth:
            subfolder_parts = parts[in_depth:effective_out_depth]
            subfolder_key = subfolder_key_from_parts(subfolder_parts)
        else:
            subfolder_key = ""
        organized.setdefault(key_path, {}).setdefault(subfolder_key, []).append(file_path)
    return organized


def organize_directory_mode_folders(
    folders: list[str],
    in_depth: int,
) -> dict[str, dict[str, list[str]]]:
    """Group folder paths where in_depth == out_depth (no subfolder nesting).

    Each folder becomes its own key with a single empty-string subfolder entry.
    Folders shallower than *in_depth* are skipped.
    """
    organized: dict[str, dict[str, list[str]]] = {}
    for folder in folders:
        parts = path_parts(folder)
        key_path = compute_key_path(parts, in_depth)
        if key_path is None:
            continue
        organized.setdefault(key_path, {})[""] = [folder]
    return organized


def describe_folders_at_in_depth(
    organized_files: dict[str, dict[str, list[str]]],
) -> list[FolderOption]:
    """Return display-friendly folder options without performing any I/O."""
    return [
        FolderOption(
            full_path=full_path,
            item_count=sum(len(v) for v in organized_files[full_path].values()),
        )
        for full_path in sorted(organized_files)
    ]


def select_folders_at_in_depth(
    organized_files: dict[str, dict[str, list[str]]],
    selected_indices: list[int],
) -> dict[str, dict[str, list[str]]]:
    """Return only folders referenced by *selected_indices* in sorted order."""
    sorted_paths = sorted(organized_files)
    return {
        sorted_paths[index]: organized_files[sorted_paths[index]]
        for index in selected_indices
        if 0 <= index < len(sorted_paths)
    }


def normalize_filter_names(filter_list: list[str]) -> list[str]:
    """Flatten filter tokens, tolerating comma-joined names inside a token."""
    return [
        part.strip()
        for token in filter_list
        for part in token.split(",")
        if part.strip()
    ]


def filter_folders_at_in_depth(
    organized_files: dict[str, dict[str, list[str]]],
    filter_list: list[str] | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Filter *organized_files* to a subset of top-level keys by folder name."""
    if not filter_list:
        return organized_files

    # Build name → full_path mapping (last path component as display name)
    folder_map: dict[str, str] = {
        path_name(key_path): key_path for key_path in organized_files
    }
    return {
        folder_map[n]: organized_files[folder_map[n]]
        for n in normalize_filter_names(filter_list)
        if n in folder_map
    }
