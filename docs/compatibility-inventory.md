# Compatibility inventory

All 32 operations at pinned source 33ae2926 (v1.0.11).

| Operation | HTTP | SDK | Raw MCP tool | Scopes |
| --- | --- | --- | --- | --- |
| archiveItemGroup | PUT /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}/archive | `client.item_groups.archive` | `plaky_archive_item_group` | write, destructive |
| createItem | POST /v1/public/spaces/{spaceId}/boards/{boardId}/items | `client.items.create` | `plaky_create_item` | write |
| createItemComment | POST /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments | `client.comments.create` | `plaky_create_item_comment` | write |
| createItemGroup | POST /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups | `client.item_groups.create` | `plaky_create_item_group` | write |
| deleteItem | DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId} | `client.items.delete` | `plaky_delete_item` | write, destructive |
| deleteItemComment | DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId} | `client.comments.delete` | `plaky_delete_item_comment` | write, destructive |
| deleteItemFile | DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId} | `client.item_files.delete` | `plaky_delete_item_file` | write, destructive |
| deleteItemGroup | DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId} | `client.item_groups.delete` | `plaky_delete_item_group` | write, destructive |
| getBoard | GET /v1/public/spaces/{spaceId}/boards/{boardId} | `client.boards.get` | `plaky_get_board` | read |
| getCurrentUser | GET /v1/public/users/me | `client.users.me` | `plaky_get_current_user` | read |
| getItem | GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId} | `client.items.get` | `plaky_get_item` | read |
| getItemFile | GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId} | `client.item_files.get` | `plaky_get_item_file` | read |
| getItemFileDownload | GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}/download | `client.item_files.get_download` | `plaky_get_item_file_download` | read |
| getItemGroup | GET /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId} | `client.item_groups.get` | `plaky_get_item_group` | read |
| getSpace | GET /v1/public/spaces/{spaceId} | `client.spaces.get` | `plaky_get_space` | read |
| getTeam | GET /v1/public/teams/{teamId} | `client.teams.get` | `plaky_get_team` | read |
| listBoards | GET /v1/public/spaces/{spaceId}/boards | `client.boards.list` | `plaky_list_boards` | read |
| listItemComments | GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments | `client.comments.list` | `plaky_list_item_comments` | read |
| listItemFiles | GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files | `client.item_files.list` | `plaky_list_item_files` | read |
| listItemGroups | GET /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups | `client.item_groups.list` | `plaky_list_item_groups` | read |
| listItems | GET /v1/public/spaces/{spaceId}/boards/{boardId}/items | `client.items.list` | `plaky_list_items` | read |
| listSpaces | GET /v1/public/spaces | `client.spaces.list` | `plaky_list_spaces` | read |
| listSubitems | GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/sub-items | `client.items.list_subitems` | `plaky_list_subitems` | read |
| listTeams | GET /v1/public/teams | `client.teams.list` | `plaky_list_teams` | read |
| listUsers | GET /v1/public/users | `client.users.list` | `plaky_list_users` | read |
| replaceCommentReactions | PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId}/reactions | `client.reactions.replace` | `plaky_replace_comment_reactions` | write |
| updateItemComment | PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId} | `client.comments.update` | `plaky_update_item_comment` | write |
| updateItemField | PATCH /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/fields/{itemFieldKey} | `client.items.update_field` | `plaky_update_item_field` | write |
| updateItemFields | PATCH /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/fields | `client.items.update_fields` | `plaky_update_item_fields` | write |
| updateItemFile | PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId} | `client.item_files.update` | `plaky_update_item_file` | write |
| updateItemGroup | PUT /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId} | `client.item_groups.update` | `plaky_update_item_group` | write |
| uploadItemFile | POST /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files | `client.item_files.upload` | `plaky_upload_item_file` | write |

Default curated read tools: plaky_search_docs, plaky_workspace_context,
plaky_find, plaky_board_view, plaky_plan_mutation,
plaky_execute_read_workflow. The active write-scoped curated tool is
plaky_execute_mutation_workflow. plaky_execute_workflow is compatibility-only
and requires its explicit flag.

Workflow IDs: workspace.map, items.search, comments.thread, export.items,
items.create, items.updateFields, comments.add, itemGroups.create,
itemGroups.update, itemFiles.upload, itemFiles.update.
