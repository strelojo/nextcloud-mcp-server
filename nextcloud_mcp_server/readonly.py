"""Drop every MCP tool that can change Nextcloud.

Reading, searching and downloading stay. A name that is not listed here is
removed as soon as it matches a write marker, so a new mutating tool does not
slip through by default.
"""

from __future__ import annotations

# Substrings of tool function names. Chosen so list/get/search names do not match.
_MARKERS: tuple[str, ...] = (
    "delete",
    "write_",
    "create_",
    "update_",
    "send_",
    "move_",
    "append_",
    "import_",
    "reindex",
    "provision_",
    "revoke",
    "restore_",
    "copy_",
    "complete_",
    "bulk_",
    "archive_card",
    "unarchive",
    "assign",
    "unassign",
    "clear_checked",
    "uncheck",
    "tag_file",
    "untag",
    "create_comment",
    "set_flag",
    "set_tag",
    "remove_",
    "set_config",
    "set_emoji",
    "set_collective",
    "set_page",
    "trash_",
    "add_items",
    "add_participant",
    "talk_react",
    "mark_",
    "insert_row",
    "check_item",
    "attach_",
    "reorder",
    "create",
    "update",
    "manage_",
    "public_link",
)

# These write even though their names look like a search or a status change.
_EXPLICIT: frozenset[str] = frozenset(
    {
        "sar_case_search",
        "sar_case_items",
        "sar_case_export",
    }
)


# Verbs that change the server. POST stays open because WebDAV search uses it;
# tools that write via POST are removed by name instead.
MUTATING_HTTP_METHODS = frozenset(
    {
        "DELETE",
        "PUT",
        "PATCH",
        "MOVE",
        "COPY",
        "MKCOL",
        "PROPPATCH",
        "LOCK",
        "UNLOCK",
    }
)


def refuse_mutating_http(method: str) -> None:
    """Refuse an HTTP verb that can change Nextcloud, before any request is sent."""
    if method.upper() in MUTATING_HTTP_METHODS:
        raise PermissionError(
            f"{method.upper()} ist deaktiviert. Dieser Server liest Nextcloud nur."
        )


def is_mutating(name: str) -> bool:
    """True when this tool can change Nextcloud or send something out of it."""
    if name in _EXPLICIT:
        return True
    return any(marker in name for marker in _MARKERS)


def enforce_readonly(mcp) -> list[str]:
    """Remove mutating tools from an already configured MCP server."""
    manager = mcp._tool_manager
    removed: list[str] = []
    for tool in list(manager.list_tools()):
        if not is_mutating(tool.name):
            continue
        removed.append(tool.name)
        if hasattr(manager, "remove_tool"):
            manager.remove_tool(tool.name)
        else:
            manager._tools.pop(tool.name, None)
    return removed
