from flask_smorest import Blueprint, abort
from flask.views import MethodView
from marshmallow import Schema, fields, validate, EXCLUDE
from typing import Any, Dict

from ..db import (
    init_db,
    list_notes,
    create_note,
    get_note,
    update_note,
    delete_note,
    list_all_tags,
)

# Initialize DB when routes module loads (idempotent)
init_db()

blp = Blueprint(
    "Notes",
    "notes",
    url_prefix="/api",
    description="CRUD endpoints for managing notes with tags and categories",
)


class NoteBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=True, validate=validate.Length(min=1, max=255), metadata={"description": "Note title"})
    content = fields.String(required=True, validate=validate.Length(min=1), metadata={"description": "Note content"})
    category = fields.String(required=False, allow_none=True, validate=validate.Length(max=64), metadata={"description": "Optional category"})
    tags = fields.List(fields.String(validate=validate.Length(min=1, max=64)), required=False, metadata={"description": "Optional list of tag names"})


class NoteCreateSchema(NoteBaseSchema):
    pass


class NoteUpdateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.String(required=False, validate=validate.Length(min=1, max=255))
    content = fields.String(required=False, validate=validate.Length(min=1))
    category = fields.String(required=False, allow_none=True, validate=validate.Length(max=64))
    tags = fields.List(fields.String(validate=validate.Length(min=1, max=64)), required=False)


class NoteSchema(NoteBaseSchema):
    id = fields.Integer(required=True)
    created_at = fields.DateTime(required=True)
    updated_at = fields.DateTime(required=True)


class NoteQuerySchema(Schema):
    q = fields.String(required=False, metadata={"description": "Search text in title and content"})
    tag = fields.String(required=False, metadata={"description": "Filter by tag name"})
    category = fields.String(required=False, metadata={"description": "Filter by category"})


class TagListSchema(Schema):
    tags = fields.List(fields.String(), required=True)


# PUBLIC_INTERFACE
@blp.route("/notes")
class NotesCollection(MethodView):
    """List and create notes.
    GET: List notes with optional search/filter.
    POST: Create a new note.
    """

    @blp.arguments(NoteQuerySchema, location="query")
    @blp.response(200, NoteSchema(many=True))
    @blp.doc(summary="List notes", description="List notes with optional search by text, filter by tag and category")
    def get(self, args):
        q = args.get("q")
        tag = args.get("tag")
        category = args.get("category")
        return list_notes(q=q, tag=tag, category=category)

    @blp.arguments(NoteCreateSchema)
    @blp.response(201, NoteSchema)
    @blp.doc(summary="Create note", description="Create a new note with optional tags and category")
    def post(self, data: Dict[str, Any]):
        try:
            note = create_note(data)
            return note
        except Exception as e:
            abort(400, message=f"Failed to create note: {e}")


# PUBLIC_INTERFACE
@blp.route("/notes/<int:note_id>")
class NotesItem(MethodView):
    """Retrieve, update, or delete a single note by ID."""

    @blp.response(200, NoteSchema)
    @blp.doc(summary="Get note", description="Retrieve a single note by its ID")
    def get(self, note_id: int):
        note = get_note(note_id)
        if not note:
            abort(404, message="Note not found")
        return note

    @blp.arguments(NoteUpdateSchema)
    @blp.response(200, NoteSchema)
    @blp.doc(summary="Update note", description="Update fields on a note; fields not provided remain unchanged")
    def patch(self, data: Dict[str, Any], note_id: int):
        if not data:
            abort(400, message="No fields provided for update")
        note = update_note(note_id, data)
        if not note:
            abort(404, message="Note not found")
        return note

    @blp.response(204)
    @blp.doc(summary="Delete note", description="Delete a note by ID")
    def delete(self, note_id: int):
        ok = delete_note(note_id)
        if not ok:
            abort(404, message="Note not found")
        return ""


# PUBLIC_INTERFACE
@blp.route("/tags")
class TagsCollection(MethodView):
    """List all tags in the system."""

    @blp.response(200, TagListSchema)
    @blp.doc(summary="List tags", description="Return all known tags across notes")
    def get(self):
        return {"tags": list_all_tags()}
