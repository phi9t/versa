import json

from versa.llm.schema import pydantic_model_to_codex_schema
from versa.models.delta import TurnDelta


def _all_nodes_have_type_or_anyof(node: object) -> bool:
    if isinstance(node, dict):
        if "anyOf" in node or "oneOf" in node or "allOf" in node:
            branches = node.get("anyOf") or node.get("oneOf") or node.get("allOf") or []
            return all(_all_nodes_have_type_or_anyof(b) for b in branches)
        if "enum" in node or "type" in node:
            node_type = node.get("type")
            if node_type == "array":
                return "items" in node and _all_nodes_have_type_or_anyof(node["items"])
            if node_type == "object":
                if "properties" in node:
                    return all(_all_nodes_have_type_or_anyof(v) for v in node["properties"].values())
                return True
            return True
        if "properties" in node:
            return all(_all_nodes_have_type_or_anyof(v) for v in node["properties"].values())
        if "items" in node:
            return _all_nodes_have_type_or_anyof(node["items"])
        return False
    elif isinstance(node, list):
        return all(_all_nodes_have_type_or_anyof(item) for item in node)
    return True


def test_turn_delta_schema_is_strict_object():
    schema = pydantic_model_to_codex_schema(TurnDelta)
    assert schema["type"] == "object"
    assert schema.get("additionalProperties") is False
    assert "$ref" not in json.dumps(schema)
    assert _all_nodes_have_type_or_anyof(schema)


def test_fact_patch_value_has_typed_schema():
    schema = pydantic_model_to_codex_schema(TurnDelta)
    value = schema["properties"]["fact_patches"]["items"]["properties"]["value"]
    assert "anyOf" in value or "type" in value


def test_turn_delta_schema_validates_empty_delta():
    fixture = {
        "user_intent_summary": None,
        "fact_patches": [],
        "assumption_patches": [],
        "new_questions_for_user": [],
    }
    delta = TurnDelta.model_validate(fixture)
    assert delta.fact_patches == []
