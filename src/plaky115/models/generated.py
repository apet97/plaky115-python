# AUTO-GENERATED. DO NOT EDIT.
# Source: contract/generated/operations.json
# Regenerate: uv run python scripts/generate.py
# pyright: reportAssignmentType=false
from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, RootModel


class BoardDefaultValues(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    default_attributes: Annotated[
        dict[str, Any] | None,
        Field(
            alias="defaultAttributes",
            description='Represents configured default attribute values applied to new items created on this board.\n"The keys are unique attribute keys, and the values are the default data for that attribute.',
            examples=[{"status-1": "1", "tag-1": ["1", "2"]}],
        ),
    ] = None
    group_id: Annotated[
        int | None,
        Field(
            alias="groupId",
            description="Represents configured default item group in the board.",
        ),
    ] = None
    subscribed_team_ids: Annotated[
        list[int] | None,
        Field(
            alias="subscribedTeamIds",
            description="Represents list of configured team ids which are by default added as subscribers to the new item in the board.",
        ),
    ] = None
    subscribed_user_ids: Annotated[
        list[int] | None,
        Field(
            alias="subscribedUserIds",
            description="Represents list of configured user ids which are by default added as subscribers to the new item in the board.",
        ),
    ] = None
    title: Annotated[
        str | None,
        Field(description="Represents configured default item title in the board."),
    ] = None


class EditPermissionsMode(StrEnum):
    """
    Represents permission modes for the board edit actions.
    """

    everything = "EVERYTHING"
    content = "CONTENT"
    updates = "UPDATES"


class Kind(StrEnum):
    """
    Represents type of the board.
    """

    public = "PUBLIC"
    private = "PRIVATE"


class CommentRequest(BaseModel):
    """
    Represents item comment request.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    replies_to_id: Annotated[
        int | None,
        Field(
            alias="repliesToId",
            description="Represents comment ID to reply to.",
            examples=[1],
        ),
    ] = None
    text: Annotated[
        str,
        Field(
            description="Represents text of the comment.",
            examples=["My comment."],
            min_length=1,
        ),
    ]


class FieldValueChangeRequest(BaseModel):
    """
    Represents request for item field value change.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    value: Annotated[
        Any | None,
        Field(
            description='Represents item field value. Field value differs per type and for some types it can be specified in multiple ways.\n\n| Type | Examples (Key / Title) |\n| :--- | :--- |\n| **String** | `{"value" : "test"}`|\n| **Rich Text** | `{"value" : "some rich text"}`\n| **Number** | `{"value" : 13.4}` |\n| **Date** | `{"value" : "2017-06-02T18:10:15.254Z"}` |\n| **Timeline** | `{"value" : {"start" : "2026-01-02T18:10:15.254Z", "end": "2026-02-02T18:10:15.254Z"}}` |\n| **Status** | `{"value" : "1"}`, `{"value" : "To do"}` |\n| **Tag** | `{"value" : ["1", "2"]}`, `{"value" : ["Product", "HR"]}` |\n| **Link** | `{"value" : "https://www.google.com"}`, `{"value" : {"url" : "https://www.google.com", "displayText" : "Google"}}`  |\n| **Person** | `{"value": {"users" : [{"id" : "1"}, {"email" : "test@gmail.com"}], "teams": [{"id" : 1}, {"title" : "Backend Team"}]}}`|\n',
            examples=[{"value": "To do"}],
        ),
    ] = None


class FolderResponse(BaseModel):
    """
    Represents folder response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    id: Annotated[
        int | None,
        Field(description="Represents unique folder identifier across the system."),
    ] = None
    ranking: Annotated[
        str | None,
        Field(description="Represents lexicographical string used for ordering."),
    ] = None
    title: Annotated[str | None, Field(description="Represents title of the item group.")] = None


class ItemAttributeConfiguration(RootModel[Any]):
    root: Any


class Type(StrEnum):
    """
    Represents type of the item attribute.
    """

    string = "STRING"
    number = "NUMBER"
    date_time = "DATE_TIME"
    status = "STATUS"
    tag = "TAG"
    person = "PERSON"
    rich_text = "RICH_TEXT"
    link = "LINK"
    timeline = "TIMELINE"


class ItemCreateRequest(BaseModel):
    """
    Represents item create request.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    fields: Annotated[
        dict[str, Any] | None,
        Field(
            description='Represents item field values added to the item. If it is omitted then item will be created with default values. Field can be\nspecified by it\'s key or by it\'s title. Field value differs per type and for some types it can be specified in multiple ways.\n\n| Type | Examples (Key / Title) |\n| :--- | :--- |\n| **String** | `{"string-1" : "test"}` <br> `{"String Field Title" : "test"}` |\n| **Rich Text** | `{"rich_text-1" : "some rich text"}` <br> `{"Description" : "some rich text"}` |\n| **Number** | `{"number-1" : 13.4}` <br> `{"Price" : 13.4}` |\n| **Date** | `{"date_time-1" : "2017-06-02T18:10:15.254Z"}` <br> `{"Date" : "2017-06-02T18:10:15.254Z"}` |\n| **Timeline** | `{"timeline-1" : {"start" : "2026-01-02T18:10:15.254Z", "end": "2026-02-02T18:10:15.254Z"}}` <br> `{"Timeline" : {"start" : "2026-01-02T18:10:15.254Z", "end": "2026-02-02T18:10:15.254Z"}}` |\n| **Status** | `{"status-1" : "1"}`, `{"status-1" : "To do"}` <br> `{"Status" : "1"}`, `{"Status" : "To do"}` |\n| **Tag** | `{"tag-1" : ["1", "2"]}`, `{"tag-1" : ["Product", "HR"]}` <br> `{"Department" : ["1", "2"]}`, `{"Department" : ["Product", "HR"]}` |\n| **Link** | `{"link-1" : "https://www.google.com"}` <br> `{"link-1" : {"url" : "https://www.google.com", "displayText" : "Google"}}` <br> `{"Link" : "https://www.google.com"}` |\n| **Person** | `{"person-1": {"users" : [{"id" : "1"}, {"email" : "test@gmail.com"}], "teams": [{"id" : 1}, {"title" : "Backend Team"}]}}` <br> `{"Assignee": {"users" : [{"id" : "1"}, {"email" : "test@gmail.com"}], "teams": [{"id" : 1}, {"title" : "Backend Team"}]}}` |\n',
            examples=[{"Description": "Test description", "Status": "To do", "number-1": 50}],
        ),
    ] = None
    group_id: Annotated[
        int | None,
        Field(
            alias="groupId",
            description="Represents ID of the item group in which item is created. If it is not specified then **groupTitle** field\nwill be used for determining in which group item is created.",
            examples=[1],
        ),
    ] = None
    group_title: Annotated[
        str | None,
        Field(
            alias="groupTitle",
            description="Represents title of the item group in which item is created. If neither **groupId** nor **groupTitle** field is\nnot specified then item will be created in the first group in the board.",
            examples=["Backlog"],
        ),
    ] = None
    parent_id: Annotated[
        int | None,
        Field(
            alias="parentId",
            description="Represents ID of the parent under which subitem is created. If it has null value then item is created, if\nit is specified then subitem is created under specified parent.",
            examples=[1],
        ),
    ] = None
    title: Annotated[
        str | None,
        Field(
            description="Represents title of the item. If it is not provided then default title be set. Default title for item is New Item and\nfor subitem it is New Subitem.",
            examples=["My New Item"],
            max_length=255,
        ),
    ] = None


class Type1(StrEnum):
    """
    Represents type of the item field.
    """

    string = "STRING"
    number = "NUMBER"
    date_time = "DATE_TIME"
    status = "STATUS"
    tag = "TAG"
    person = "PERSON"
    rich_text = "RICH_TEXT"
    timeline = "TIMELINE"
    link = "LINK"


class ItemFieldResponse(BaseModel):
    """
    Represents item field response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    key: Annotated[
        str | None,
        Field(
            description="Represents key of the item field.",
            examples=["status-1", "tag-1", "person-1"],
        ),
    ] = None
    title: Annotated[str | None, Field(description="Represents title of the item field.")] = None
    type: Annotated[Type1 | None, Field(description="Represents type of the item field.")] = None
    value: Annotated[
        Any | None,
        Field(
            description="Represents the value of an item field. This field is **expandable**.\nBy default, it returns a **Short** version (primitive/simple ID).\nIf expanded, it returns a **Full** version (object with metadata).\n\n### Value Mapping Table\n\n| Field Type | Short Version (Default) | Full Version (Expanded) |\n| :--- | :--- | :--- |\n| **Text** | `string` | `string` |\n| **Number** | `number` | `number` |\n| **Date** | `string` (ISO 8601) | `string` (ISO 8601) |\n| **Status** | `string` (key) | `object` (key, label, color) |\n| **Tag** | `array<string>` (keys) | `array<object>` (key, label, color) |\n| **Link** | `object` (url, displayText) | `object` (url, displayText) |\n| **Timeline** | `object` (start, end) | `object` (start, end) |\n| **Person** | `object` (assigned IDs) | `object` (full User/Team objects) |\n"
        ),
    ] = None


class ItemFileDownloadResponse(BaseModel):
    """
    Represents item file download response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    expires_in_seconds: Annotated[
        int | None,
        Field(
            alias="expiresInSeconds",
            description="Represents presigned URL validity period in seconds.",
        ),
    ] = None
    url: Annotated[
        str | None, Field(description="Represents presigned URL for file download.")
    ] = None


class ItemFileResponse(BaseModel):
    """
    Represents item file response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    created_at: Annotated[
        AwareDatetime | None,
        Field(
            alias="createdAt",
            description="Represents date and time of the file upload (UTC) in ISO-8601 format.",
        ),
    ] = None
    description: Annotated[str | None, Field(description="Represents item file description.")] = (
        None
    )
    extension: Annotated[
        str | None,
        Field(description="Represents item file extension.", examples=["pdf"]),
    ] = None
    file_type: Annotated[
        str | None,
        Field(alias="fileType", description="Represents item file type.", examples=["PDF"]),
    ] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique item file identifier across the system."),
    ] = None
    name: Annotated[str | None, Field(description="Represents item file name.")] = None
    size: Annotated[int | None, Field(description="Represents item file size in bytes.")] = None
    uploaded_by: Annotated[
        int | None,
        Field(
            alias="uploadedBy",
            description="Represents ID of the user who uploaded the file.",
        ),
    ] = None


class ItemFileUpdateRequest(BaseModel):
    """
    Represents item file update request.
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    description: Annotated[
        str | None,
        Field(
            description="Represents item file description.",
            max_length=255,
            min_length=0,
        ),
    ] = None
    name: Annotated[
        str,
        Field(
            description="The new name for the file. You may include or omit the extension; the system will preserve the original file type regardless.",
            max_length=255,
            min_length=1,
        ),
    ]


class ItemGroupCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    color: Annotated[
        str | None,
        Field(
            description="Represents color of the item group. Color value must be in standard RGB hexadecimal format."
        ),
    ] = None
    ranking: Annotated[
        str | None,
        Field(description="Represents lexicographical string used for custom ordering/sorting."),
    ] = None
    title: Annotated[
        str,
        Field(
            description="Represents title of the item group.",
            max_length=255,
            min_length=1,
        ),
    ]


class ItemGroupResponse(BaseModel):
    """
    Represents item group response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    color: Annotated[
        str | None,
        Field(
            description="Represents color of the item group. Color value is in standard RGB hexadecimal format."
        ),
    ] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique item group identifier across the system."),
    ] = None
    ranking: Annotated[
        str | None,
        Field(description="Represents lexicographical string used for custom ordering/sorting."),
    ] = None
    title: Annotated[str | None, Field(description="Represents title of the item group.")] = None


class ItemGroupUpdateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    color: Annotated[
        str | None,
        Field(
            description="Represents color of the item group. Color value must be in standard RGB hexadecimal format."
        ),
    ] = None
    ranking: Annotated[
        str,
        Field(
            description="Represents lexicographical string used for custom ordering/sorting.",
            min_length=1,
        ),
    ]
    title: Annotated[
        str,
        Field(
            description="Represents title of the item group.",
            max_length=255,
            min_length=1,
        ),
    ]


class NoConfiguration(BaseModel):
    """
    Represent empty configuration object used for attribute types that do not require extra settings.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )


class Alignment(StrEnum):
    """
    Represents text alignment of the number within the cell.
    """

    left = "LEFT"
    right = "RIGHT"
    center = "CENTER"
    none = "NONE"


class Unit(StrEnum):
    """
    Represents the type of unit to display.
    """

    dollar = "DOLLAR"
    euro = "EURO"
    pound = "POUND"
    percentage = "PERCENTAGE"
    custom_unit = "CUSTOM_UNIT"
    none = "NONE"


class UnitAlignment(StrEnum):
    """
    Represents positioning of the unit relative to the number.
    """

    left = "LEFT"
    right = "RIGHT"


class NumberConfiguration(BaseModel):
    """
    Represents configuration for number attribute.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    alignment: Annotated[
        Alignment | None,
        Field(description="Represents text alignment of the number within the cell."),
    ] = None
    custom_unit_value: Annotated[
        str | None,
        Field(
            alias="customUnitValue",
            description="Represents a custom string value for the unit if unit type is custom.",
        ),
    ] = None
    unit: Annotated[Unit | None, Field(description="Represents the type of unit to display.")] = (
        None
    )
    unit_alignment: Annotated[
        UnitAlignment | None,
        Field(
            alias="unitAlignment",
            description="Represents positioning of the unit relative to the number.",
        ),
    ] = None


class Limit(StrEnum):
    """
    Represents limit configuration for the number of persons that can be assigned.
    """

    one = "ONE"
    two = "TWO"
    three = "THREE"
    unlimited = "UNLIMITED"


class PersonConfiguration(BaseModel):
    """
    Configuration for person attribute.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    limit: Annotated[
        Limit | None,
        Field(
            description="Represents limit configuration for the number of persons that can be assigned."
        ),
    ] = None


class PublicPagedResponseV1ItemGroupResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    data: Annotated[
        list[ItemGroupResponse] | None,
        Field(description="The list of elements returned for the current page."),
    ] = None
    has_more: Annotated[
        bool | None,
        Field(
            alias="hasMore",
            description="Whether there are more elements available beyond this current set.",
        ),
    ] = None


class Reaction(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    value: Annotated[
        str,
        Field(
            description='A code representing an emoji, like "1f44d" (thumbs up) or "2705" (checkmark button).\nYou\'ll see there are variations on how an emoji could be represented, we need a unicode representation\nwithout "U+" prefix. For example, the unicode for "thumbs up" is "U+1F44D", so take it after the plus\nsign (letter case doesn\'t matter).\n',
            examples=["1f44d"],
            min_length=1,
        ),
    ]


class ReactionDetails(BaseModel):
    """
    Represents user reaction details.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    reacted_at: Annotated[
        AwareDatetime | None,
        Field(
            alias="reactedAt",
            description="Represents date and time of the comment reaction creation (UTC) in ISO-8601 format.",
        ),
    ] = None
    user_id: Annotated[
        int | None,
        Field(
            alias="userId",
            description="Represents unique user identifier accross the system.",
        ),
    ] = None


class ReactionPutRequest(BaseModel):
    """
    Represents request for adding/removing authenticated user's comment reaction(s).
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )
    reactions: Annotated[
        list[Reaction],
        Field(
            description="You can leave multiple reactions, it's overriding the current ones that you've left,\nleave empty to remove them.\n"
        ),
    ]


class ReactionResponse(BaseModel):
    """
    Represents detailed comment reaction response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    reacted_users: Annotated[
        list[ReactionDetails] | None,
        Field(
            alias="reactedUsers",
            description="Represents a list of users who left the comment reaction.",
        ),
    ] = None
    reaction_code: Annotated[
        str | None,
        Field(
            alias="reactionCode",
            description='Represents the string code of the emoji. For example, for thumbs up emoji, we have "1f44d" code.\n',
        ),
    ] = None


class ReactionResponseNoCode(BaseModel):
    """
    Represents item comment reaction response without reaction code.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    created_at: Annotated[
        AwareDatetime | None,
        Field(
            alias="createdAt",
            description="Represents date and time of the comment reaction creation (UTC) in ISO-8601 format.",
        ),
    ] = None
    created_by_id: Annotated[
        int | None,
        Field(
            alias="createdById",
            description="Represents ID of the user who created the comment reaction.",
        ),
    ] = None


class Type2(StrEnum):
    """
    Represents type of the user.
    """

    owner = "OWNER"
    admin = "ADMIN"
    member = "MEMBER"
    viewer = "VIEWER"


class ShortUserResponse(BaseModel):
    """
    Represents short user response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    email: Annotated[str | None, Field(description="Represents user's email.")] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique user identifier across the system."),
    ] = None
    name: Annotated[str | None, Field(description="Represents user's name.")] = None
    type: Annotated[Type2 | None, Field(description="Represents type of the user.")] = None


class Kind1(StrEnum):
    """
    Represent kind of the space.
    """

    open = "OPEN"
    closed = "CLOSED"


class StatusLabelDefinition(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    color: Annotated[
        str | None,
        Field(description="Represents the hexadecimal color code representing the status."),
    ] = None
    is_final: Annotated[
        bool | None,
        Field(
            alias="isFinal",
            description="Indicates if this status represents a 'completed' state in the workflow.",
        ),
    ] = None
    key: Annotated[
        str | None,
        Field(description="Represents the unique identifier/key for the status label."),
    ] = None
    title: Annotated[
        str | None, Field(description="Represents the display title of the status.")
    ] = None


class TagLabelDefinition(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    color: Annotated[
        str | None,
        Field(description="Represents the hexadecimal color code representing the status."),
    ] = None
    key: Annotated[
        str | None,
        Field(description="Represents the unique identifier/key for the status label."),
    ] = None
    title: Annotated[
        str | None, Field(description="Represents the display title of the status.")
    ] = None


class TeamResponse(BaseModel):
    """
    Represents team response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    all_users_team: Annotated[
        bool | None,
        Field(
            alias="allUsersTeam",
            description="Indicates if the team is all users team (all workspace users are part of this team).",
        ),
    ] = None
    icon_url: Annotated[
        str | None,
        Field(alias="iconUrl", description="Represents url of the team's icon."),
    ] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique team identifier across the system."),
    ] = None
    members: Annotated[
        list[int] | None,
        Field(description="Represents the list of user ids which are members of the team"),
    ] = None
    title: Annotated[str | None, Field(description="Represents title of the team.")] = None


class TeamShortResponse(BaseModel):
    """
    Represents team response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    all_users_team: Annotated[
        bool | None,
        Field(
            alias="allUsersTeam",
            description="Indicates if the team is all users team (all workspace users are part of this team).",
        ),
    ] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique team identifier across the system."),
    ] = None
    title: Annotated[str | None, Field(description="Represents title of the team.")] = None


class TimelineConfiguration(BaseModel):
    """
    Configuration for timeline range attribute.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    show_current_year: Annotated[
        bool | None,
        Field(
            alias="showCurrentYear",
            description="Represents whether the year is displayed.",
        ),
    ] = None
    show_time: Annotated[
        bool | None,
        Field(alias="showTime", description="Represents whether the time is displayed."),
    ] = None


class UserDetails(BaseModel):
    """
    Represents user details.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    birth_day: Annotated[
        date | None,
        Field(alias="birthDay", description="Represents status of the user"),
    ] = None
    custom_fields: Annotated[
        list[UserDetails] | None,
        Field(
            alias="customFields",
            description="Represents list of custom fields of the user",
        ),
    ] = None
    location: Annotated[str | None, Field(description="Represents location of the user")] = None
    mobile_phone: Annotated[
        str | None,
        Field(
            alias="mobilePhone",
            description="Represents mobile phone number of the user",
        ),
    ] = None
    phone: Annotated[str | None, Field(description="Represents phone number of the user")] = None
    title: Annotated[str | None, Field(description="Represents title of the user")] = None
    work_anniversary: Annotated[
        date | None,
        Field(alias="workAnniversary", description="Represents status of the user"),
    ] = None


class Status(StrEnum):
    """
    Represents status of the user
    """

    active = "ACTIVE"
    inactive = "INACTIVE"
    pending = "PENDING"


class UserResponse(BaseModel):
    """
    Represents short user response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    details: Annotated[UserDetails | None, Field(description="Represents details of the user")] = (
        None
    )
    email: Annotated[str | None, Field(description="Represents user's email.")] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique user identifier across the system."),
    ] = None
    name: Annotated[str | None, Field(description="Represents user's name.")] = None
    photo_url: Annotated[
        str | None,
        Field(alias="photoUrl", description="Represents url of the user profile photo"),
    ] = None
    status: Annotated[Status | None, Field(description="Represents status of the user")] = None
    type: Annotated[Type2 | None, Field(description="Represents type of the user.")] = None


class Violation(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    field_name: Annotated[str | None, Field(alias="fieldName")] = None
    message: str | None = None


class CommentResponse(BaseModel):
    """
    Represents item comment response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    content: Annotated[str | None, Field(description="Represents content of the comment.")] = None
    created_at: Annotated[
        AwareDatetime | None,
        Field(
            alias="createdAt",
            description="Represents date and time of the comment creation (UTC) in ISO-8601 format.",
        ),
    ] = None
    created_by: Annotated[
        int | None,
        Field(
            alias="createdBy",
            description="Represents ID of the user who created the comment.",
        ),
    ] = None
    deleted: Annotated[
        bool | None,
        Field(description="Indicates whether the comment is softly deleted."),
    ] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique item comment identifier across the system."),
    ] = None
    pinned: Annotated[
        bool | None, Field(description="Indicates whether the comment is pinned.")
    ] = None
    reactions: Annotated[
        list[ReactionResponse] | None,
        Field(description="Represents reactions to the comment."),
    ] = None
    replies: Annotated[
        list[CommentResponse] | None,
        Field(description="Represents replies to the comment."),
    ] = None
    updated_at: Annotated[
        AwareDatetime | None,
        Field(
            alias="updatedAt",
            description="Represents date and time of the comment update (UTC) in ISO-8601 format.",
        ),
    ] = None


class DateTimeConfiguration(BaseModel):
    """
    Represents configuration for date-time attribute.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    always_keep_add_time_on: Annotated[
        bool | None,
        Field(
            alias="alwaysKeepAddTimeOn",
            description="Represents whether the time component is displayed.",
        ),
    ] = None
    show_current_year: Annotated[
        bool | None,
        Field(
            alias="showCurrentYear",
            description="Represents whether the year in the date format is displayed.",
        ),
    ] = None
    show_day_of_the_week: Annotated[
        bool | None,
        Field(
            alias="showDayOfTheWeek",
            description="Represents whether the name of the day is displayed.",
        ),
    ] = None
    show_week_numbers: Annotated[
        bool | None,
        Field(
            alias="showWeekNumbers",
            description="Represents whether week number is displayed.",
        ),
    ] = None


class PublicPagedResponseV1TeamResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    data: Annotated[
        list[TeamResponse] | None,
        Field(description="The list of elements returned for the current page."),
    ] = None
    has_more: Annotated[
        bool | None,
        Field(
            alias="hasMore",
            description="Whether there are more elements available beyond this current set.",
        ),
    ] = None


class PublicPagedResponseV1UserResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    data: Annotated[
        list[UserResponse] | None,
        Field(description="The list of elements returned for the current page."),
    ] = None
    has_more: Annotated[
        bool | None,
        Field(
            alias="hasMore",
            description="Whether there are more elements available beyond this current set.",
        ),
    ] = None


class ReactionPutResponse(BaseModel):
    """
    Represents response on reaction(s) change.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    reactions: Annotated[
        dict[str, list[ReactionResponseNoCode]] | None,
        Field(
            description="A map containing reaction code as a key and the list of reactions without code\n(ReactionResponseNoCode) as a value.\n"
        ),
    ] = None


class StatusConfiguration(BaseModel):
    """
    Represents configuration for status attribute.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    default_value: Annotated[
        str | None,
        Field(
            alias="defaultValue",
            description="Represents the key of the default status label.",
        ),
    ] = None
    values: Annotated[
        list[StatusLabelDefinition] | None,
        Field(description="Represents list of possible status labels."),
    ] = None


class TagConfiguration(BaseModel):
    """
    Configuration for tag attribute.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    values: Annotated[
        list[TagLabelDefinition] | None,
        Field(description="List of possible tag definitions available."),
    ] = None


class ValidationErrorResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    error_code: Annotated[int | None, Field(alias="errorCode")] = None
    error_label: Annotated[str | None, Field(alias="errorLabel")] = None
    violations: list[Violation] | None = None


class ItemAttributeDefinition(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    configuration: Annotated[
        DateTimeConfiguration
        | NoConfiguration
        | NumberConfiguration
        | PersonConfiguration
        | StatusConfiguration
        | TagConfiguration
        | TimelineConfiguration
        | None,
        Field(description="Represents configuration of the item attribute."),
    ] = None
    description: Annotated[
        str | None, Field(description="Represents description of the item attribute.")
    ] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique identifier of the item attribute."),
    ] = None
    key: Annotated[str | None, Field(description="Represents key of the item attribute.")] = None
    name: Annotated[str | None, Field(description="Represents name of the item attribute.")] = None
    type: Annotated[Type | None, Field(description="Represents type of the item attribute.")] = (
        None
    )


class BoardResponse(BaseModel):
    """
    Represents board response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    default_board: Annotated[
        bool | None,
        Field(alias="defaultBoard", description="Indicates if the board is default."),
    ] = None
    default_values: Annotated[
        BoardDefaultValues | None,
        Field(
            alias="defaultValues",
            description="Represents configured default values used when creating new item.",
        ),
    ] = None
    description: Annotated[
        str | None, Field(description="Represents description of the board.")
    ] = None
    edit_permissions_mode: Annotated[
        EditPermissionsMode | None,
        Field(
            alias="editPermissionsMode",
            description="Represents permission modes for the board edit actions.",
        ),
    ] = None
    fields: list[ItemAttributeDefinition] | None = None
    folder: Annotated[
        FolderResponse | int | None,
        Field(
            description="Represents folder containing the board. Can be returned as an ID or a full object if expanded."
        ),
    ] = None
    groups: list[ItemGroupResponse] | None = None
    id: Annotated[int | None, Field(description="Represents unique identifier of the board.")] = (
        None
    )
    kind: Annotated[Kind | None, Field(description="Represents type of the board.")] = None
    ranking: Annotated[
        str | None,
        Field(description="Represents lexicographical string used for the board ordering."),
    ] = None
    space: Annotated[
        SpaceResponse | int | None,
        Field(
            description="Represents space containing the board. Can be returned as an ID or a full object if expanded."
        ),
    ] = None
    template: Annotated[
        bool | None,
        Field(
            description="If true, it means the board serves as a template for generating other production-ready boards."
        ),
    ] = None
    title: Annotated[str | None, Field(description="Represents title of the board.")] = None


class ItemResponse(BaseModel):
    """
    Represents extendable item response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    archived: Annotated[
        bool | None, Field(description="Indicates whether the item is archived.")
    ] = None
    board: Annotated[
        BoardResponse | int | None,
        Field(
            description="Represents ID of the board in which item is created, it can be expanded to include full board details."
        ),
    ] = None
    comment_count: Annotated[
        int | None,
        Field(
            alias="commentCount",
            description="Represents number of comments added on the item.",
        ),
    ] = None
    created_at: Annotated[
        AwareDatetime | None,
        Field(
            alias="createdAt",
            description="Represents date and time of the item creation (UTC) in ISO-8601 format.",
        ),
    ] = None
    created_by: Annotated[
        ShortUserResponse | int | None,
        Field(
            alias="createdBy",
            description="Represents ID of the user who created the item, it can be expanded to retrieve full user details.",
        ),
    ] = None
    deleted: Annotated[
        bool | None, Field(description="Indicates whether the item is softly deleted.")
    ] = None
    deleted_at: Annotated[
        AwareDatetime | None,
        Field(
            alias="deletedAt",
            description="Represents date and time of the item soft deletion (UTC) in ISO-8601 format.",
        ),
    ] = None
    fields: Annotated[
        list[ItemFieldResponse] | None,
        Field(
            description="Represents list of the item fields present on the item. In default response values for status, tag and person\nfields are simple IDs. Response can be expanded to include full details for status, tag and person fields.\n"
        ),
    ] = None
    file_count: Annotated[
        int | None,
        Field(
            alias="fileCount",
            description="Represents number of files uploaded on the item.",
        ),
    ] = None
    group: Annotated[
        ItemGroupResponse | int | None,
        Field(
            description="Represents ID of the group in which item is created, it can be expanded to include full group details."
        ),
    ] = None
    id: Annotated[
        int | None,
        Field(description="Represents unique item identifier across the system."),
    ] = None
    parent: Annotated[
        ItemResponse | int | None,
        Field(
            description="Represents ID of the parent for subitem, it can be expanded to include full item details. It is non-null only for subitems."
        ),
    ] = None
    ranking: Annotated[str | None, Field(description="Represents item ranking.")] = None
    space: Annotated[
        SpaceResponse | int | None,
        Field(
            description="Represents ID of the space in which item is created, it can be expanded to include full space details"
        ),
    ] = None
    subitems: list[ItemResponse] | None = None
    subscribed_teams: Annotated[
        list[TeamShortResponse | int] | None, Field(alias="subscribedTeams")
    ] = None
    subscribed_users: Annotated[
        list[ShortUserResponse | int] | None, Field(alias="subscribedUsers")
    ] = None
    title: Annotated[str | None, Field(description="Represents item title.")] = None


class PublicPagedResponseV1BoardResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    data: Annotated[
        list[BoardResponse] | None,
        Field(description="The list of elements returned for the current page."),
    ] = None
    has_more: Annotated[
        bool | None,
        Field(
            alias="hasMore",
            description="Whether there are more elements available beyond this current set.",
        ),
    ] = None


class PublicPagedResponseV1ItemResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    data: Annotated[
        list[ItemResponse] | None,
        Field(description="The list of elements returned for the current page."),
    ] = None
    has_more: Annotated[
        bool | None,
        Field(
            alias="hasMore",
            description="Whether there are more elements available beyond this current set.",
        ),
    ] = None


class PublicPagedResponseV1SpaceResponse(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    data: Annotated[
        list[SpaceResponse] | None,
        Field(description="The list of elements returned for the current page."),
    ] = None
    has_more: Annotated[
        bool | None,
        Field(
            alias="hasMore",
            description="Whether there are more elements available beyond this current set.",
        ),
    ] = None


class SpaceResponse(BaseModel):
    """
    Represents space response.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
    )
    boards: list[BoardResponse] | None = None
    default_space: Annotated[
        bool | None,
        Field(
            alias="defaultSpace",
            description="Indicates whether the space is the default one.",
        ),
    ] = None
    description: Annotated[
        str | None, Field(description="Represents description of the space.")
    ] = None
    icon_url: Annotated[
        str | None,
        Field(alias="iconUrl", description="Represents url of the space icon."),
    ] = None
    id: Annotated[int | None, Field(description="Represents unique identifier of the space.")] = (
        None
    )
    kind: Annotated[Kind1 | None, Field(description="Represent kind of the space.")] = None
    title: Annotated[str | None, Field(description="Represents title of the space.")] = None


UserDetails.model_rebuild()
CommentResponse.model_rebuild()
BoardResponse.model_rebuild()
ItemResponse.model_rebuild()
PublicPagedResponseV1SpaceResponse.model_rebuild()
