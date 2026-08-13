# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
"""Raw MCP tool registry: one generated tool per operation."""

from __future__ import annotations

from plaky115.async_client import AsyncPlakyClient
from plaky115_mcp.registry import ToolSpec
from plaky115_mcp.tools.raw.generated_archive_item_group import (
    build_tool as _generated_archive_item_group,
)
from plaky115_mcp.tools.raw.generated_create_item import build_tool as _generated_create_item
from plaky115_mcp.tools.raw.generated_create_item_comment import (
    build_tool as _generated_create_item_comment,
)
from plaky115_mcp.tools.raw.generated_create_item_group import (
    build_tool as _generated_create_item_group,
)
from plaky115_mcp.tools.raw.generated_delete_item import build_tool as _generated_delete_item
from plaky115_mcp.tools.raw.generated_delete_item_comment import (
    build_tool as _generated_delete_item_comment,
)
from plaky115_mcp.tools.raw.generated_delete_item_file import (
    build_tool as _generated_delete_item_file,
)
from plaky115_mcp.tools.raw.generated_delete_item_group import (
    build_tool as _generated_delete_item_group,
)
from plaky115_mcp.tools.raw.generated_get_board import build_tool as _generated_get_board
from plaky115_mcp.tools.raw.generated_get_current_user import (
    build_tool as _generated_get_current_user,
)
from plaky115_mcp.tools.raw.generated_get_item import build_tool as _generated_get_item
from plaky115_mcp.tools.raw.generated_get_item_file import build_tool as _generated_get_item_file
from plaky115_mcp.tools.raw.generated_get_item_file_download import (
    build_tool as _generated_get_item_file_download,
)
from plaky115_mcp.tools.raw.generated_get_item_group import build_tool as _generated_get_item_group
from plaky115_mcp.tools.raw.generated_get_space import build_tool as _generated_get_space
from plaky115_mcp.tools.raw.generated_get_team import build_tool as _generated_get_team
from plaky115_mcp.tools.raw.generated_list_boards import build_tool as _generated_list_boards
from plaky115_mcp.tools.raw.generated_list_item_comments import (
    build_tool as _generated_list_item_comments,
)
from plaky115_mcp.tools.raw.generated_list_item_files import (
    build_tool as _generated_list_item_files,
)
from plaky115_mcp.tools.raw.generated_list_item_groups import (
    build_tool as _generated_list_item_groups,
)
from plaky115_mcp.tools.raw.generated_list_items import build_tool as _generated_list_items
from plaky115_mcp.tools.raw.generated_list_spaces import build_tool as _generated_list_spaces
from plaky115_mcp.tools.raw.generated_list_subitems import build_tool as _generated_list_subitems
from plaky115_mcp.tools.raw.generated_list_teams import build_tool as _generated_list_teams
from plaky115_mcp.tools.raw.generated_list_users import build_tool as _generated_list_users
from plaky115_mcp.tools.raw.generated_replace_comment_reactions import (
    build_tool as _generated_replace_comment_reactions,
)
from plaky115_mcp.tools.raw.generated_update_item_comment import (
    build_tool as _generated_update_item_comment,
)
from plaky115_mcp.tools.raw.generated_update_item_field import (
    build_tool as _generated_update_item_field,
)
from plaky115_mcp.tools.raw.generated_update_item_fields import (
    build_tool as _generated_update_item_fields,
)
from plaky115_mcp.tools.raw.generated_update_item_file import (
    build_tool as _generated_update_item_file,
)
from plaky115_mcp.tools.raw.generated_update_item_group import (
    build_tool as _generated_update_item_group,
)
from plaky115_mcp.tools.raw.generated_upload_item_file import (
    build_tool as _generated_upload_item_file,
)


def build_raw_tools(client: AsyncPlakyClient) -> list[ToolSpec]:
    return [
        _generated_archive_item_group(client),
        _generated_create_item(client),
        _generated_create_item_comment(client),
        _generated_create_item_group(client),
        _generated_delete_item(client),
        _generated_delete_item_comment(client),
        _generated_delete_item_file(client),
        _generated_delete_item_group(client),
        _generated_get_board(client),
        _generated_get_current_user(client),
        _generated_get_item(client),
        _generated_get_item_file(client),
        _generated_get_item_file_download(client),
        _generated_get_item_group(client),
        _generated_get_space(client),
        _generated_get_team(client),
        _generated_list_boards(client),
        _generated_list_item_comments(client),
        _generated_list_item_files(client),
        _generated_list_item_groups(client),
        _generated_list_items(client),
        _generated_list_spaces(client),
        _generated_list_subitems(client),
        _generated_list_teams(client),
        _generated_list_users(client),
        _generated_replace_comment_reactions(client),
        _generated_update_item_comment(client),
        _generated_update_item_field(client),
        _generated_update_item_fields(client),
        _generated_update_item_file(client),
        _generated_update_item_group(client),
        _generated_upload_item_file(client),
    ]
