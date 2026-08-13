"""Item files resource. Multipart upload in the SDK; list root stays a bare
array; signed download URLs are sensitive and never logged."""

from __future__ import annotations

from typing import Any

from plaky115.http import RequestSpec
from plaky115.ids import IdInput, id_path_segment
from plaky115.models import ItemFile, ItemFileDownload
from plaky115.resources._common import (
    BodyInput,
    Requester,
    RequestOverrides,
    SyncRequester,
    body_as_dict,
    parse_array,
    parse_object,
    with_idempotency,
)
from plaky115.workflows.mutation_plans import (
    normalize_binary_upload_plan,
    normalize_item_file_update_plan,
)


def _files_path(space_id: IdInput, board_id: IdInput, item_id: IdInput) -> str:
    return (
        f"/v1/public/spaces/{id_path_segment(space_id)}"
        f"/boards/{id_path_segment(board_id)}"
        f"/items/{id_path_segment(item_id)}/files"
    )


def _upload_spec(
    space_id: IdInput,
    board_id: IdInput,
    item_id: IdInput,
    file: bytes | bytearray | memoryview,
    file_name: str | None,
    content_type: str | None,
) -> RequestSpec:
    _, metadata = normalize_binary_upload_plan(
        space_id=space_id,
        board_id=board_id,
        item_id=item_id,
        file=file,
        file_name=file_name,
        content_type=content_type,
    )
    return RequestSpec(
        method="POST",
        path=_files_path(space_id, board_id, item_id),
        files={"file": (metadata.file_name, bytes(file), metadata.media_type)},
        operation_id="uploadItemFile",
    )


class AsyncItemFilesResource:
    def __init__(self, client: Requester) -> None:
        self._client = client

    async def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> list[ItemFile]:
        spec = RequestSpec(
            method="GET",
            path=_files_path(space_id, board_id, item_id),
            operation_id="listItemFiles",
        )
        data: Any = await self._client.execute(spec, options)
        return parse_array(data, "listItemFiles", ItemFile)

    async def upload(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        file: bytes | bytearray | memoryview,
        file_name: str | None = None,
        content_type: str | None = None,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemFile:
        spec = _upload_spec(space_id, board_id, item_id, file, file_name, content_type)
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemFile)

    async def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemFile:
        spec = RequestSpec(
            method="GET",
            path=f"{_files_path(space_id, board_id, item_id)}/{id_path_segment(item_file_id)}",
            operation_id="getItemFile",
        )
        data: Any = await self._client.execute(spec, options)
        return parse_object(data, ItemFile)

    async def get_download(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemFileDownload:
        spec = RequestSpec(
            method="GET",
            path=(
                f"{_files_path(space_id, board_id, item_id)}"
                f"/{id_path_segment(item_file_id)}/download"
            ),
            operation_id="getItemFileDownload",
        )
        data: Any = await self._client.execute(spec, options)
        return parse_object(data, ItemFileDownload)

    async def update(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemFile:
        plan = normalize_item_file_update_plan(
            space_id=space_id,
            board_id=board_id,
            item_id=item_id,
            item_file_id=item_file_id,
            body=body_as_dict(body),
        )
        spec = RequestSpec(
            method="PUT",
            path=f"{_files_path(space_id, board_id, item_id)}/{id_path_segment(item_file_id)}",
            body=dict(plan.body),
            operation_id="updateItemFile",
        )
        data: Any = await self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemFile)

    async def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=f"{_files_path(space_id, board_id, item_id)}/{id_path_segment(item_file_id)}",
            response_type="void",
            operation_id="deleteItemFile",
        )
        await self._client.execute(spec, with_idempotency(options, idempotency_key))


class ItemFilesResource:
    def __init__(self, client: SyncRequester) -> None:
        self._client = client

    def list(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> list[ItemFile]:
        spec = RequestSpec(
            method="GET",
            path=_files_path(space_id, board_id, item_id),
            operation_id="listItemFiles",
        )
        data: Any = self._client.execute(spec, options)
        return parse_array(data, "listItemFiles", ItemFile)

    def upload(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        file: bytes | bytearray | memoryview,
        file_name: str | None = None,
        content_type: str | None = None,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemFile:
        spec = _upload_spec(space_id, board_id, item_id, file, file_name, content_type)
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemFile)

    def get(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemFile:
        spec = RequestSpec(
            method="GET",
            path=f"{_files_path(space_id, board_id, item_id)}/{id_path_segment(item_file_id)}",
            operation_id="getItemFile",
        )
        data: Any = self._client.execute(spec, options)
        return parse_object(data, ItemFile)

    def get_download(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        options: RequestOverrides | None = None,
    ) -> ItemFileDownload:
        spec = RequestSpec(
            method="GET",
            path=(
                f"{_files_path(space_id, board_id, item_id)}"
                f"/{id_path_segment(item_file_id)}/download"
            ),
            operation_id="getItemFileDownload",
        )
        data: Any = self._client.execute(spec, options)
        return parse_object(data, ItemFileDownload)

    def update(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        body: BodyInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> ItemFile:
        plan = normalize_item_file_update_plan(
            space_id=space_id,
            board_id=board_id,
            item_id=item_id,
            item_file_id=item_file_id,
            body=body_as_dict(body),
        )
        spec = RequestSpec(
            method="PUT",
            path=f"{_files_path(space_id, board_id, item_id)}/{id_path_segment(item_file_id)}",
            body=dict(plan.body),
            operation_id="updateItemFile",
        )
        data: Any = self._client.execute(spec, with_idempotency(options, idempotency_key))
        return parse_object(data, ItemFile)

    def delete(
        self,
        *,
        space_id: IdInput,
        board_id: IdInput,
        item_id: IdInput,
        item_file_id: IdInput,
        idempotency_key: str | None = None,
        options: RequestOverrides | None = None,
    ) -> None:
        spec = RequestSpec(
            method="DELETE",
            path=f"{_files_path(space_id, board_id, item_id)}/{id_path_segment(item_file_id)}",
            response_type="void",
            operation_id="deleteItemFile",
        )
        self._client.execute(spec, with_idempotency(options, idempotency_key))
