# Port Matrix

Source baseline: `33ae2926aa696f36d9663d44f914d42d9aadc53f` (plaky115 v1.0.11).
Status values: not-started | in-progress | blocked | implemented | verified.
Only a green objective gate permits `verified`.

| ID | Surface | Source proof | Python target | Tests | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| op:archiveItemGroup | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}/archive` | api-1.yaml; operation-metadata.json | `client.item_groups.archive` + `plaky_archive_item_group` | unit + parity + mock-error | not-started | |
| op:createItem | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/items` | api-1.yaml; operation-metadata.json | `client.items.create` + `plaky_create_item` | unit + parity + mock-error | not-started | |
| op:createItemComment | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments` | api-1.yaml; operation-metadata.json | `client.comments.create` + `plaky_create_item_comment` | unit + parity + mock-error | not-started | |
| op:createItemGroup | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups` | api-1.yaml; operation-metadata.json | `client.item_groups.create` + `plaky_create_item_group` | unit + parity + mock-error | not-started | |
| op:deleteItem | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}` | api-1.yaml; operation-metadata.json | `client.items.delete` + `plaky_delete_item` | unit + parity + mock-error | not-started | |
| op:deleteItemComment | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId}` | api-1.yaml; operation-metadata.json | `client.comments.delete` + `plaky_delete_item_comment` | unit + parity + mock-error | not-started | |
| op:deleteItemFile | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}` | api-1.yaml; operation-metadata.json | `client.item_files.delete` + `plaky_delete_item_file` | unit + parity + mock-error | not-started | |
| op:deleteItemGroup | `DELETE /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}` | api-1.yaml; operation-metadata.json | `client.item_groups.delete` + `plaky_delete_item_group` | unit + parity + mock-error | not-started | |
| op:getBoard | `GET /v1/public/spaces/{spaceId}/boards/{boardId}` | api-1.yaml; operation-metadata.json | `client.boards.get` + `plaky_get_board` | unit + parity + mock-error | not-started | |
| op:getCurrentUser | `GET /v1/public/users/me` | api-1.yaml; operation-metadata.json | `client.users.me` + `plaky_get_current_user` | unit + parity + mock-error | not-started | |
| op:getItem | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}` | api-1.yaml; operation-metadata.json | `client.items.get` + `plaky_get_item` | unit + parity + mock-error | not-started | |
| op:getItemFile | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}` | api-1.yaml; operation-metadata.json | `client.item_files.get` + `plaky_get_item_file` | unit + parity + mock-error | not-started | |
| op:getItemFileDownload | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}/download` | api-1.yaml; operation-metadata.json | `client.item_files.get_download` + `plaky_get_item_file_download` | unit + parity + mock-error | not-started | |
| op:getItemGroup | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}` | api-1.yaml; operation-metadata.json | `client.item_groups.get` + `plaky_get_item_group` | unit + parity + mock-error | not-started | |
| op:getSpace | `GET /v1/public/spaces/{spaceId}` | api-1.yaml; operation-metadata.json | `client.spaces.get` + `plaky_get_space` | unit + parity + mock-error | not-started | |
| op:getTeam | `GET /v1/public/teams/{teamId}` | api-1.yaml; operation-metadata.json | `client.teams.get` + `plaky_get_team` | unit + parity + mock-error | not-started | |
| op:listBoards | `GET /v1/public/spaces/{spaceId}/boards` | api-1.yaml; operation-metadata.json | `client.boards.list` + `plaky_list_boards` | unit + parity + mock-error | not-started | |
| op:listItemComments | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments` | api-1.yaml; operation-metadata.json | `client.comments.list` + `plaky_list_item_comments` | unit + parity + mock-error | not-started | |
| op:listItemFiles | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files` | api-1.yaml; operation-metadata.json | `client.item_files.list` + `plaky_list_item_files` | unit + parity + mock-error | not-started | |
| op:listItemGroups | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups` | api-1.yaml; operation-metadata.json | `client.item_groups.list` + `plaky_list_item_groups` | unit + parity + mock-error | not-started | |
| op:listItems | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items` | api-1.yaml; operation-metadata.json | `client.items.list` + `plaky_list_items` | unit + parity + mock-error | not-started | |
| op:listSpaces | `GET /v1/public/spaces` | api-1.yaml; operation-metadata.json | `client.spaces.list` + `plaky_list_spaces` | unit + parity + mock-error | not-started | |
| op:listSubitems | `GET /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/sub-items` | api-1.yaml; operation-metadata.json | `client.items.list_subitems` + `plaky_list_subitems` | unit + parity + mock-error | not-started | |
| op:listTeams | `GET /v1/public/teams` | api-1.yaml; operation-metadata.json | `client.teams.list` + `plaky_list_teams` | unit + parity + mock-error | not-started | |
| op:listUsers | `GET /v1/public/users` | api-1.yaml; operation-metadata.json | `client.users.list` + `plaky_list_users` | unit + parity + mock-error | not-started | |
| op:replaceCommentReactions | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId}/reactions` | api-1.yaml; operation-metadata.json | `client.reactions.replace` + `plaky_replace_comment_reactions` | unit + parity + mock-error | not-started | |
| op:updateItemComment | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/comments/{itemCommentId}` | api-1.yaml; operation-metadata.json | `client.comments.update` + `plaky_update_item_comment` | unit + parity + mock-error | not-started | |
| op:updateItemField | `PATCH /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/fields/{itemFieldKey}` | api-1.yaml; operation-metadata.json | `client.items.update_field` + `plaky_update_item_field` | unit + parity + mock-error | not-started | |
| op:updateItemFields | `PATCH /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/fields` | api-1.yaml; operation-metadata.json | `client.items.update_fields` + `plaky_update_item_fields` | unit + parity + mock-error | not-started | |
| op:updateItemFile | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files/{itemFileId}` | api-1.yaml; operation-metadata.json | `client.item_files.update` + `plaky_update_item_file` | unit + parity + mock-error | not-started | |
| op:updateItemGroup | `PUT /v1/public/spaces/{spaceId}/boards/{boardId}/item-groups/{itemGroupId}` | api-1.yaml; operation-metadata.json | `client.item_groups.update` + `plaky_update_item_group` | unit + parity + mock-error | not-started | |
| op:uploadItemFile | `POST /v1/public/spaces/{spaceId}/boards/{boardId}/items/{itemId}/files` | api-1.yaml; operation-metadata.json | `client.item_files.upload` + `plaky_upload_item_file` | unit + parity + mock-error | not-started | |
| resource:spaces | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.spaces` | resource unit tests | not-started | |
| resource:boards | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.boards` | resource unit tests | not-started | |
| resource:items | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.items` | resource unit tests | not-started | |
| resource:comments | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.comments` | resource unit tests | not-started | |
| resource:reactions | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.reactions` | resource unit tests | not-started | |
| resource:users | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.users` | resource unit tests | not-started | |
| resource:teams | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.teams` | resource unit tests | not-started | |
| resource:item_groups | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.item_groups` | resource unit tests | not-started | |
| resource:item_files | SDK resource (sync+async) | sdk/src/client/* | `plaky115.resources.item_files` | resource unit tests | not-started | |
| export:PlakyClient | public SDK export | sdk/src/index.ts; plan 8.1 | `PlakyClient` | export + behavior tests | not-started | |
| export:AsyncPlakyClient | public SDK export | sdk/src/index.ts; plan 8.1 | `AsyncPlakyClient` | export + behavior tests | not-started | |
| export:DEFAULT_SERVER_URL | public SDK export | sdk/src/index.ts; plan 8.1 | `DEFAULT_SERVER_URL` | export + behavior tests | not-started | |
| export:classify | public SDK export | sdk/src/index.ts; plan 8.1 | `classify` | export + behavior tests | not-started | |
| export:normalize_problem | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_problem` | export + behavior tests | not-started | |
| export:merge_headers_into | public SDK export | sdk/src/index.ts; plan 8.1 | `merge_headers_into` | export + behavior tests | not-started | |
| export:resolve_headers | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_headers` | export + behavior tests | not-started | |
| export:request | public SDK export | sdk/src/index.ts; plan 8.1 | `request` | export + behavior tests | not-started | |
| export:request_with_response | public SDK export | sdk/src/index.ts; plan 8.1 | `request_with_response` | export + behavior tests | not-started | |
| export:new_idempotency_key | public SDK export | sdk/src/index.ts; plan 8.1 | `new_idempotency_key` | export + behavior tests | not-started | |
| export:resolve_idempotency_key | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_idempotency_key` | export + behavior tests | not-started | |
| export:resolve_explicit_idempotency_key | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_explicit_idempotency_key` | export + behavior tests | not-started | |
| export:assert_paged_result | public SDK export | sdk/src/index.ts; plan 8.1 | `assert_paged_result` | export + behavior tests | not-started | |
| export:assert_array_result | public SDK export | sdk/src/index.ts; plan 8.1 | `assert_array_result` | export + behavior tests | not-started | |
| export:build_user_agent | public SDK export | sdk/src/index.ts; plan 8.1 | `build_user_agent` | export + behavior tests | not-started | |
| export:redact | public SDK export | sdk/src/index.ts; plan 8.1 | `redact` | export + behavior tests | not-started | |
| export:redact_value | public SDK export | sdk/src/index.ts; plan 8.1 | `redact_value` | export + behavior tests | not-started | |
| export:with_retries | public SDK export | sdk/src/index.ts; plan 8.1 | `with_retries` | export + behavior tests | not-started | |
| export:RateLimitTracker | public SDK export | sdk/src/index.ts; plan 8.1 | `RateLimitTracker` | export + behavior tests | not-started | |
| export:paginate | public SDK export | sdk/src/index.ts; plan 8.1 | `paginate` | export + behavior tests | not-started | |
| export:iterate_paged_chunks | public SDK export | sdk/src/index.ts; plan 8.1 | `iterate_paged_chunks` | export + behavior tests | not-started | |
| export:read_paged_chunk | public SDK export | sdk/src/index.ts; plan 8.1 | `read_paged_chunk` | export + behavior tests | not-started | |
| export:utf8_byte_length | public SDK export | sdk/src/index.ts; plan 8.1 | `utf8_byte_length` | export + behavior tests | not-started | |
| export:validate_upload_limit | public SDK export | sdk/src/index.ts; plan 8.1 | `validate_upload_limit` | export + behavior tests | not-started | |
| export:validate_upload_file_name | public SDK export | sdk/src/index.ts; plan 8.1 | `validate_upload_file_name` | export + behavior tests | not-started | |
| export:normalize_upload_media_type | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_upload_media_type` | export + behavior tests | not-started | |
| export:normalize_upload_metadata | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_upload_metadata` | export + behavior tests | not-started | |
| export:decode_base64_upload | public SDK export | sdk/src/index.ts; plan 8.1 | `decode_base64_upload` | export + behavior tests | not-started | |
| export:normalize_upload | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_upload` | export + behavior tests | not-started | |
| export:estimate_base64_decoded_bytes | public SDK export | sdk/src/index.ts; plan 8.1 | `estimate_base64_decoded_bytes` | export + behavior tests | not-started | |
| export:validate_binary_upload | public SDK export | sdk/src/index.ts; plan 8.1 | `validate_binary_upload` | export + behavior tests | not-started | |
| export:field_values | public SDK export | sdk/src/index.ts; plan 8.1 | `field_values` | export + behavior tests | not-started | |
| export:omit_none | public SDK export | sdk/src/index.ts; plan 8.1 | `omit_none` | export + behavior tests | not-started | |
| export:string_field | public SDK export | sdk/src/index.ts; plan 8.1 | `string_field` | export + behavior tests | not-started | |
| export:status_field | public SDK export | sdk/src/index.ts; plan 8.1 | `status_field` | export + behavior tests | not-started | |
| export:tag_field | public SDK export | sdk/src/index.ts; plan 8.1 | `tag_field` | export + behavior tests | not-started | |
| export:person_field | public SDK export | sdk/src/index.ts; plan 8.1 | `person_field` | export + behavior tests | not-started | |
| export:timeline_field | public SDK export | sdk/src/index.ts; plan 8.1 | `timeline_field` | export + behavior tests | not-started | |
| export:link_field | public SDK export | sdk/src/index.ts; plan 8.1 | `link_field` | export + behavior tests | not-started | |
| export:number_field | public SDK export | sdk/src/index.ts; plan 8.1 | `number_field` | export + behavior tests | not-started | |
| export:field_label | public SDK export | sdk/src/index.ts; plan 8.1 | `field_label` | export + behavior tests | not-started | |
| export:resolve_space | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_space` | export + behavior tests | not-started | |
| export:resolve_board | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_board` | export + behavior tests | not-started | |
| export:resolve_space_and_board | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_space_and_board` | export + behavior tests | not-started | |
| export:resolve_user | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_user` | export + behavior tests | not-started | |
| export:resolve_team | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_team` | export + behavior tests | not-started | |
| export:resolve_item | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_item` | export + behavior tests | not-started | |
| export:resolve_items_in_board | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_items_in_board` | export + behavior tests | not-started | |
| export:resolve_item_group_in_board | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_item_group_in_board` | export + behavior tests | not-started | |
| export:resolve_item_file_on_item | public SDK export | sdk/src/index.ts; plan 8.1 | `resolve_item_file_on_item` | export + behavior tests | not-started | |
| export:workspace_map | public SDK export | sdk/src/index.ts; plan 8.1 | `workspace_map` | export + behavior tests | not-started | |
| export:search_items | public SDK export | sdk/src/index.ts; plan 8.1 | `search_items` | export + behavior tests | not-started | |
| export:search_items_detailed | public SDK export | sdk/src/index.ts; plan 8.1 | `search_items_detailed` | export + behavior tests | not-started | |
| export:bulk_update_items | public SDK export | sdk/src/index.ts; plan 8.1 | `bulk_update_items` | export + behavior tests | not-started | |
| export:export_items | public SDK export | sdk/src/index.ts; plan 8.1 | `export_items` | export + behavior tests | not-started | |
| export:read_item_chunk | public SDK export | sdk/src/index.ts; plan 8.1 | `read_item_chunk` | export + behavior tests | not-started | |
| export:iterate_item_chunks | public SDK export | sdk/src/index.ts; plan 8.1 | `iterate_item_chunks` | export + behavior tests | not-started | |
| export:read_item_export_chunk | public SDK export | sdk/src/index.ts; plan 8.1 | `read_item_export_chunk` | export + behavior tests | not-started | |
| export:iterate_item_export_chunks | public SDK export | sdk/src/index.ts; plan 8.1 | `iterate_item_export_chunks` | export + behavior tests | not-started | |
| export:normalize_base64_upload_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_base64_upload_plan` | export + behavior tests | not-started | |
| export:normalize_binary_upload_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_binary_upload_plan` | export + behavior tests | not-started | |
| export:normalize_comment_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_comment_plan` | export + behavior tests | not-started | |
| export:normalize_item_create_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_item_create_plan` | export + behavior tests | not-started | |
| export:normalize_item_file_update_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_item_file_update_plan` | export + behavior tests | not-started | |
| export:normalize_item_group_create_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_item_group_create_plan` | export + behavior tests | not-started | |
| export:normalize_item_group_update_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_item_group_update_plan` | export + behavior tests | not-started | |
| export:normalize_item_update_fields_plan | public SDK export | sdk/src/index.ts; plan 8.1 | `normalize_item_update_fields_plan` | export + behavior tests | not-started | |
| export:SpaceId | public SDK export | sdk/src/index.ts; plan 8.1 | `SpaceId` | export + behavior tests | not-started | |
| export:BoardId | public SDK export | sdk/src/index.ts; plan 8.1 | `BoardId` | export + behavior tests | not-started | |
| export:ItemId | public SDK export | sdk/src/index.ts; plan 8.1 | `ItemId` | export + behavior tests | not-started | |
| export:CommentId | public SDK export | sdk/src/index.ts; plan 8.1 | `CommentId` | export + behavior tests | not-started | |
| export:FieldKey | public SDK export | sdk/src/index.ts; plan 8.1 | `FieldKey` | export + behavior tests | not-started | |
| export:UserId | public SDK export | sdk/src/index.ts; plan 8.1 | `UserId` | export + behavior tests | not-started | |
| export:TeamId | public SDK export | sdk/src/index.ts; plan 8.1 | `TeamId` | export + behavior tests | not-started | |
| export:ItemGroupId | public SDK export | sdk/src/index.ts; plan 8.1 | `ItemGroupId` | export + behavior tests | not-started | |
| export:ItemFileId | public SDK export | sdk/src/index.ts; plan 8.1 | `ItemFileId` | export + behavior tests | not-started | |
| export:FolderId | public SDK export | sdk/src/index.ts; plan 8.1 | `FolderId` | export + behavior tests | not-started | |
| export:as_space_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_space_id` | export + behavior tests | not-started | |
| export:as_board_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_board_id` | export + behavior tests | not-started | |
| export:as_item_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_item_id` | export + behavior tests | not-started | |
| export:as_comment_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_comment_id` | export + behavior tests | not-started | |
| export:as_field_key | public SDK export | sdk/src/index.ts; plan 8.1 | `as_field_key` | export + behavior tests | not-started | |
| export:as_user_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_user_id` | export + behavior tests | not-started | |
| export:as_team_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_team_id` | export + behavior tests | not-started | |
| export:as_item_group_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_item_group_id` | export + behavior tests | not-started | |
| export:as_item_file_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_item_file_id` | export + behavior tests | not-started | |
| export:as_folder_id | public SDK export | sdk/src/index.ts; plan 8.1 | `as_folder_id` | export + behavior tests | not-started | |
| export:18 resource root exports (9 sync + 9 async classes) | public SDK export | sdk/src/index.ts; plan 8.1 | `18 resource root exports (9 sync + 9 async classes)` | export + behavior tests | not-started | |
| export:Page | public SDK export | sdk/src/index.ts; plan 8.1 | `Page` | export + behavior tests | not-started | |
| export:errors hierarchy (section 8.3) | public SDK export | sdk/src/index.ts; plan 8.1 | `errors hierarchy (section 8.3)` | export + behavior tests | not-started | |
| curated:plaky_search_docs | curated MCP tool | mcp-server/src/tools/curated/* | `plaky_search_docs` | in-memory MCP tests | not-started | |
| curated:plaky_workspace_context | curated MCP tool | mcp-server/src/tools/curated/* | `plaky_workspace_context` | in-memory MCP tests | not-started | |
| curated:plaky_find | curated MCP tool | mcp-server/src/tools/curated/* | `plaky_find` | in-memory MCP tests | not-started | |
| curated:plaky_plan_mutation | curated MCP tool | mcp-server/src/tools/curated/* | `plaky_plan_mutation` | in-memory MCP tests | not-started | |
| curated:plaky_execute_workflow | curated MCP tool | mcp-server/src/tools/curated/* | `plaky_execute_workflow` | in-memory MCP tests | not-started | |
| curated:plaky_execute_read_workflow | curated MCP tool | mcp-server/src/tools/curated/* | `plaky_execute_read_workflow` | in-memory MCP tests | not-started | |
| curated:plaky_execute_mutation_workflow | curated MCP tool | mcp-server/src/tools/curated/* | `plaky_execute_mutation_workflow` | in-memory MCP tests | not-started | |
| workflow:workspace.map | curated MCP workflow | mcp-server/src/tools/curated/* | `workspace.map` | dispatcher tests | not-started | |
| workflow:items.search | curated MCP workflow | mcp-server/src/tools/curated/* | `items.search` | dispatcher tests | not-started | |
| workflow:comments.thread | curated MCP workflow | mcp-server/src/tools/curated/* | `comments.thread` | dispatcher tests | not-started | |
| workflow:export.items | curated MCP workflow | mcp-server/src/tools/curated/* | `export.items` | dispatcher tests | not-started | |
| workflow:items.create | curated MCP workflow | mcp-server/src/tools/curated/* | `items.create` | dispatcher tests | not-started | |
| workflow:items.updateFields | curated MCP workflow | mcp-server/src/tools/curated/* | `items.updateFields` | dispatcher tests | not-started | |
| workflow:comments.add | curated MCP workflow | mcp-server/src/tools/curated/* | `comments.add` | dispatcher tests | not-started | |
| workflow:itemGroups.create | curated MCP workflow | mcp-server/src/tools/curated/* | `itemGroups.create` | dispatcher tests | not-started | |
| workflow:itemGroups.update | curated MCP workflow | mcp-server/src/tools/curated/* | `itemGroups.update` | dispatcher tests | not-started | |
| workflow:itemFiles.upload | curated MCP workflow | mcp-server/src/tools/curated/* | `itemFiles.upload` | dispatcher tests | not-started | |
| workflow:itemFiles.update | curated MCP workflow | mcp-server/src/tools/curated/* | `itemFiles.update` | dispatcher tests | not-started | |
| runtime:get-only-retries | runtime/MCP behavior | plan sections 8/10 | GET-only retry policy with equal jitter and Retry-After | focused + matrix tests | not-started | |
| runtime:response-limits | runtime/MCP behavior | plan sections 8/10 | 16 MiB default / 64 MiB max bounded bodies | focused + matrix tests | not-started | |
| runtime:root-contracts | runtime/MCP behavior | plan sections 8/10 | strict page/array root validation | focused + matrix tests | not-started | |
| runtime:pagination | runtime/MCP behavior | plan sections 8/10 | iterators, 10k page guard | focused + matrix tests | not-started | |
| runtime:chunks | runtime/MCP behavior | plan sections 8/10 | bounded chunks with exact cursors | focused + matrix tests | not-started | |
| runtime:rate-limit | runtime/MCP behavior | plan sections 8/10 | tracker: headers + rolling window | focused + matrix tests | not-started | |
| runtime:uploads | runtime/MCP behavior | plan sections 8/10 | base64/multipart validation, 25 MiB cap, SHA-256 | focused + matrix tests | not-started | |
| runtime:mutations | runtime/MCP behavior | plan sections 8/10 | plans, receipts, ambiguous outcomes | focused + matrix tests | not-started | |
| runtime:redaction | runtime/MCP behavior | plan sections 8/10 | plk_ redaction, safe URLs, no signed URLs in logs | focused + matrix tests | not-started | |
| runtime:cancellation | runtime/MCP behavior | plan sections 8/10 | async cancellation propagation; timeout classification | focused + matrix tests | not-started | |
| runtime:csv | runtime/MCP behavior | plan sections 8/10 | deterministic spreadsheet-safe CSV/JSONL export | focused + matrix tests | not-started | |
| mcp:transport-stdio | runtime/MCP behavior | plan sections 8/10 | protocol-clean stdio transport | focused + matrix tests | not-started | |
| mcp:transport-http | runtime/MCP behavior | plan sections 8/10 | stateless Streamable HTTP; 36 MiB cap; TransportSecuritySettings | focused + matrix tests | not-started | |
| mcp:result-cap | runtime/MCP behavior | plan sections 8/10 | 128 KiB aggregate CallToolResult budget | focused + matrix tests | not-started | |
| mcp:error-envelope | runtime/MCP behavior | plan sections 8/10 | structured error envelope with attempt state | focused + matrix tests | not-started | |
| mcp:modes-scopes | runtime/MCP behavior | plan sections 8/10 | curated/generated/all modes; read/write/destructive scopes | focused + matrix tests | not-started | |
| mcp:progress-cancel | runtime/MCP behavior | plan sections 8/10 | progress checkpoints and cancellation semantics | focused + matrix tests | not-started | |
| mcp:compat-matrix | runtime/MCP behavior | plan sections 8/10 | modern 2026-07-28 + legacy 2025-11-25 matrix | focused + matrix tests | not-started | |
| gate:offline-verify | gate | plan sections 12-14 | scripts/verify.py --offline | verify.py receipts | not-started | |
| gate:package | gate | plan sections 12-14 | wheel/sdist audit + consumer smoke + installed typing proof | verify.py receipts | not-started | |
| gate:docs | gate | plan sections 12-14 | docs/examples checks + notice gates | verify.py receipts | not-started | |
| gate:ci | gate | plan sections 12-14 | CI matrix + pinned actions | verify.py receipts | not-started | |
| gate:live-read | gate | plan sections 12-14 | 17-op read certification x4 surfaces | verify.py receipts | not-started | |
| gate:live-write | gate | plan sections 12-14 | 15-op write certification (separately authorized) | verify.py receipts | not-started | |
| gate:release | gate | plan sections 12-14 | reproducible artifact + trusted publishing (separately authorized) | verify.py receipts | not-started | |
| gate:final-audit | gate | plan sections 12-14 | adversarial final audit | verify.py receipts | not-started | |
