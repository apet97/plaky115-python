"""Workflow and plan-mutation inputs: schemas, validators, and bulk bounds."""

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from plaky115.errors import PlakyCancelledError, PlakyDecodeError
from plaky115.runtime.mutations import AttemptTracker
from plaky115_mcp.errors import envelope_wire, error_envelope, internal_error
from plaky115_mcp.tools.curated.plan_mutation import normalize_for_operation
from plaky115_mcp.workflow_models import (
    MAX_BULK_UPDATES,
    MAX_BULK_UPDATES_BYTES,
    MUTATION_WORKFLOW_SCHEMA,
    PLAN_MUTATION_SCHEMA,
    validate_mutation_workflow,
    validate_plan_mutation,
)


def test_plan_normalizer_defends_missing_operation_specific_ids() -> None:
    cases = [
        ("updateItemFields", None, None, None, None),
        ("createItemComment", None, None, None, None),
        ("updateItemComment", "1", None, None, None),
        ("updateItemGroup", None, None, None, None),
        ("updateItemFile", None, None, None, None),
        ("uploadItemFile", None, None, None, None),
    ]
    for operation, item_id, comment_id, group_id, file_id in cases:
        with pytest.raises(ValueError):
            normalize_for_operation(
                operation,
                "1",
                "2",
                {"fileBase64": "aGk=", "fileName": "a.txt"},
                item_id,
                comment_id,
                group_id,
                file_id,
            )


def test_workflow_bulk_bounds_and_error_diagnostics_are_stable() -> None:
    with pytest.raises(ValueError, match="itemId and body, or updates"):
        validate_mutation_workflow("items.updateFields", {"spaceId": 1, "boardId": 2}, True)
    with pytest.raises(ValueError, match="at most"):
        validate_mutation_workflow(
            "items.updateFields",
            {
                "spaceId": 1,
                "boardId": 2,
                "updates": [
                    {"itemId": index, "body": {}} for index in range(MAX_BULK_UPDATES + 1)
                ],
            },
            True,
        )

    decoded = envelope_wire(error_envelope(PlakyDecodeError("bad", status=502, request_id="r-1")))
    assert decoded["error"]["status"] == 502
    assert decoded["error"]["requestId"] == "r-1"
    assert envelope_wire(error_envelope(PlakyCancelledError()))["error"]["category"] == "abort"

    tracker = AttemptTracker("write")
    tracker.request_started()
    internal = envelope_wire(internal_error(RuntimeError("boom"), tracker, (tracker.receipt,)))
    assert internal["error"]["mayHaveCommitted"] is True
    assert internal["error"]["receipts"][0]["operation"] == "write"


def test_workflow_bulk_size_uses_compact_utf8_json() -> None:
    updates = [{"itemId": 1, "body": {"text": {"value": "😀" * 6000}}}]
    actual_utf8 = json.dumps(
        updates,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    escaped_utf8 = json.dumps(
        updates,
        separators=(",", ":"),
    ).encode("utf-8")

    assert len(actual_utf8) <= MAX_BULK_UPDATES_BYTES
    assert len(escaped_utf8) > MAX_BULK_UPDATES_BYTES
    validate_mutation_workflow(
        "items.updateFields",
        {"spaceId": 1, "boardId": 2, "updates": updates},
        True,
    )

    too_large_updates = [{"itemId": 1, "body": {"text": {"value": "😀" * 17000}}}]
    too_large_actual_utf8 = json.dumps(
        too_large_updates,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    assert len(too_large_actual_utf8) > MAX_BULK_UPDATES_BYTES
    with pytest.raises(ValueError, match="updates must not exceed"):
        validate_mutation_workflow(
            "items.updateFields",
            {"spaceId": 1, "boardId": 2, "updates": too_large_updates},
            True,
        )


def test_workflow_body_contracts_reject_unknown_fixed_keys() -> None:
    """Schemas and validators must agree before a workflow can dispatch."""
    cases: tuple[tuple[str, str, dict[str, Any], dict[str, Any]], ...] = (
        ("items.create", "createItem", {}, {"title": "Item"}),
        ("items.updateFields", "updateItemFields", {"itemId": "3"}, {"field-1": {"value": "x"}}),
        ("comments.add", "createItemComment", {"itemId": "3"}, {"text": "Note"}),
        ("itemGroups.create", "createItemGroup", {}, {"title": "Group", "color": "#AABBCC"}),
        (
            "itemGroups.update",
            "updateItemGroup",
            {"itemGroupId": "4"},
            {"title": "Group", "ranking": "a", "color": "#AABBCC"},
        ),
        (
            "itemFiles.upload",
            "uploadItemFile",
            {"itemId": "3"},
            {"fileBase64": "aGVsbG8=", "fileName": "file.txt"},
        ),
        (
            "itemFiles.update",
            "updateItemFile",
            {"itemId": "3", "itemFileId": "5"},
            {"name": "file.txt"},
        ),
    )
    mutation_schema = Draft202012Validator(MUTATION_WORKFLOW_SCHEMA)
    plan_schema = Draft202012Validator(PLAN_MUTATION_SCHEMA)

    for workflow, operation, identifiers, body in cases:
        args = {"spaceId": "1", "boardId": "2", **identifiers, "body": body}
        mutation = {"workflow": workflow, "args": args, "dryRun": True}
        plan = {"operation": operation, **args}

        assert not list(
            mutation_schema.iter_errors(mutation)  # pyright: ignore[reportUnknownMemberType]
        ), workflow
        assert not list(
            plan_schema.iter_errors(plan)  # pyright: ignore[reportUnknownMemberType]
        ), operation
        validate_mutation_workflow(workflow, args, True)
        validate_plan_mutation(plan)

        invalid_args = {**args, "body": {**body, "definitelyUnknown": True}}
        invalid_mutation = {"workflow": workflow, "args": invalid_args, "dryRun": True}
        invalid_plan = {"operation": operation, **invalid_args}
        assert list(
            mutation_schema.iter_errors(invalid_mutation)  # pyright: ignore[reportUnknownMemberType]
        ), workflow
        assert list(
            plan_schema.iter_errors(invalid_plan)  # pyright: ignore[reportUnknownMemberType]
        ), operation
        with pytest.raises(ValidationError):
            validate_mutation_workflow(workflow, invalid_args, True)
        with pytest.raises(ValidationError):
            validate_plan_mutation(invalid_plan)

    valid_dynamic_args = {
        "spaceId": "1",
        "boardId": "2",
        "itemId": "3",
        "body": {"contract-defined-field": {"value": "x"}},
    }
    validate_mutation_workflow("items.updateFields", valid_dynamic_args, True)
