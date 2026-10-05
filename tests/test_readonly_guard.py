"""The fork must not offer any tool that changes Nextcloud."""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from nextcloud_mcp_server.client.webdav import WebDAVClient
from nextcloud_mcp_server.readonly import (
    enforce_readonly,
    is_mutating,
    refuse_mutating_http,
)

ROOT = Path(__file__).resolve().parents[1] / "nextcloud_mcp_server" / "server"

MUST_STAY = {
    "nc_webdav_list_directory",
    "nc_webdav_read_file",
    "nc_webdav_list_comments",
    "nc_webdav_list_trash",
    "nc_webdav_search_files",
    "deck_get_archived_stacks",
    "deck_get_card_comments",
    "collectives_get_trashed_pages",
    "talk_list_reactions",
    "talk_list_conversations",
    "nc_mail_list_messages",
    "nc_mail_get_message",
    "nc_share_list",
    "nc_calendar_list_events",
    "nc_notes_get_note",
    "nc_notes_get_attachment",
    "nc_mail_get_attachment",
    "deck_list_attachments",
    "check_provisioning_status",
}

MUST_GO = {
    "nc_webdav_write_file",
    "nc_webdav_create_directory",
    "nc_webdav_move_resource",
    "nc_webdav_copy_resource",
    "nc_webdav_delete_resource",
    "nc_webdav_create_comment",
    "nc_webdav_restore_from_trash",
    "nc_share_create",
    "nc_share_create_public_link",
    "nc_share_delete",
    "nc_mail_send_message",
    "nc_mail_delete_message",
    "talk_send_message",
    "deck_delete_card",
    "nc_notes_delete_note",
    "nc_calendar_delete_event",
    "nc_contacts_delete_contact",
    "sar_case_export",
    "provision_nextcloud_access",
    "revoke_nextcloud_access",
    "nc_share_create",
    "nc_share_update",
    "nc_calendar_manage_calendar",
    "sar_case_create",
    "sar_case_update",
}


def _tool_names() -> set[str]:
    names: set[str] = set()
    for path in ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.AsyncFunctionDef):
                names.add(node.name)
            for child in ast.walk(node):
                if isinstance(child, ast.AsyncFunctionDef):
                    names.add(child.name)
    return names


def test_known_reads_stay_and_writes_go():
    for name in MUST_STAY:
        assert not is_mutating(name), name
    for name in MUST_GO:
        assert is_mutating(name), name


def test_every_delete_tool_in_the_source_is_blocked():
    offenders = sorted(
        name
        for name in _tool_names()
        if "delete" in name and not name.startswith("_") and not is_mutating(name)
    )
    assert offenders == []


def test_file_delete_never_sends_a_request():
    async def call():
        await WebDAVClient.delete_resource(
            object(), "/Brandcircuit/06 Buchhaltung/rechnung.pdf"
        )

    try:
        asyncio.run(call())
    except PermissionError as exc:
        assert "deaktiviert" in str(exc)
    else:
        raise AssertionError("delete_resource must refuse")


def test_mutating_http_methods_are_refused_before_a_request():
    for method in ("DELETE", "PUT", "PATCH", "MOVE", "COPY", "MKCOL", "PROPPATCH"):
        try:
            refuse_mutating_http(method)
        except PermissionError as exc:
            assert "deaktiviert" in str(exc)
        else:
            raise AssertionError(method)
    for method in ("GET", "PROPFIND", "REPORT", "POST", "HEAD"):
        refuse_mutating_http(method)


def test_registered_webdav_and_mail_tools_are_read_only():
    from mcp.server.mcpserver import MCPServer

    from nextcloud_mcp_server.server.mail import configure_mail_tools
    from nextcloud_mcp_server.server.sharing import configure_sharing_tools
    from nextcloud_mcp_server.server.webdav import configure_webdav_tools

    mcp = MCPServer("test")
    configure_webdav_tools(mcp)
    configure_sharing_tools(mcp)
    configure_mail_tools(mcp)
    removed = enforce_readonly(mcp)
    names = {tool.name for tool in mcp._tool_manager.list_tools()}

    assert "nc_webdav_read_file" in names
    assert "nc_webdav_list_directory" in names
    assert "nc_mail_get_message" in names
    assert "nc_share_list" in names
    assert "nc_webdav_write_file" not in names
    assert "nc_webdav_move_resource" not in names
    assert "nc_webdav_delete_resource" not in names
    assert "nc_share_create_public_link" not in names
    assert "nc_mail_send_message" not in names
    assert "nc_mail_delete_message" not in names
    assert removed
    assert all(is_mutating(name) for name in removed)
