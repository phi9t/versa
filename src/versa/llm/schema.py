from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import BaseModel

_JSON_VALUE: dict[str, Any] = {
    "anyOf": [
        {"type": "string"},
        {"type": "number"},
        {"type": "integer"},
        {"type": "boolean"},
        {"type": "null"},
        {"type": "array", "items": {"type": "string"}},
        {"type": "object", "additionalProperties": False},
    ]
}

_STRIP_KEYS = frozenset({"title", "default", "description"})


@lru_cache(maxsize=32)
def pydantic_model_to_codex_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Build strict JSON Schema for codex exec --output-schema."""
    raw = model.model_json_schema(mode="serialization")
    defs = raw.pop("$defs", {})
    schema = _inline_refs(raw, defs)
    schema = _strictify(schema)
    if schema.get("type") == "object" and "properties" in schema:
        props = schema["properties"]
        if isinstance(props, dict):
            schema["additionalProperties"] = False
            schema["required"] = list(props.keys())
    return schema


@lru_cache(maxsize=32)
def codex_schema_json(model: type[BaseModel]) -> str:
    return json.dumps(pydantic_model_to_codex_schema(model))


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            ref = node["$ref"]
            if ref.startswith("#/$defs/"):
                key = ref.removeprefix("#/$defs/")
                return _inline_refs(defs[key], defs)
            return node
        return {k: _inline_refs(v, defs) for k, v in node.items()}
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node


def _strictify(node: Any) -> Any:
    if isinstance(node, list):
        return [_strictify(item) for item in node]

    if not isinstance(node, dict):
        return node

    node = {k: v for k, v in node.items() if k not in _STRIP_KEYS}

    for key in ("anyOf", "oneOf", "allOf"):
        if key in node:
            node[key] = [_ensure_typed_node(branch) for branch in node[key]]

    if "properties" in node and isinstance(node["properties"], dict):
        node["properties"] = {
            name: _ensure_typed_node(schema)
            for name, schema in node["properties"].items()
        }
        if node.get("type") == "object":
            node["additionalProperties"] = False
            node["required"] = list(node["properties"].keys())

    if "items" in node:
        node["items"] = _ensure_typed_node(node["items"])

    for key, value in list(node.items()):
        if key in ("properties", "items", "anyOf", "oneOf", "allOf"):
            continue
        if isinstance(value, dict):
            node[key] = _strictify(value)

    if "type" not in node and not any(
        k in node for k in ("anyOf", "oneOf", "allOf", "properties", "items", "enum")
    ):
        return _JSON_VALUE.copy()

    return node


def _ensure_typed_node(node: Any) -> Any:
    node = _strictify(node)
    if isinstance(node, dict) and not node:
        return _JSON_VALUE.copy()
    if isinstance(node, dict) and "type" not in node and not any(
        k in node for k in ("anyOf", "oneOf", "allOf", "enum", "properties")
    ):
        return _JSON_VALUE.copy()
    return node
