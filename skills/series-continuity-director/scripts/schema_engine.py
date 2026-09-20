#!/usr/bin/env python3
"""Shared JSON Schema subset used by SCD protocol validators."""
from __future__ import annotations

import json
import re
from typing import Any, Callable

SchemaResolver = Callable[[str], dict[str, Any]]
CanonicalEncoder = Callable[[Any], str]

SUPPORTED_SCHEMA_KEYWORDS = frozenset({
    "$ref", "anyOf", "oneOf", "const", "enum", "type",
    "minLength", "maxLength", "pattern", "minimum", "maximum",
    "minItems", "maxItems", "uniqueItems", "items",
    "minProperties", "maxProperties", "required", "properties",
    "propertyNames", "additionalProperties",
})

ANNOTATION_SCHEMA_KEYWORDS = frozenset({
    "$schema", "$id", "$comment", "title", "description",
    "examples", "default", "deprecated", "readOnly", "writeOnly",
})


def type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def unsupported_schema_keywords(schema: Any, path: str = "$") -> list[str]:
    findings: list[str] = []
    if not isinstance(schema, dict):
        return findings
    for key in schema:
        if key not in SUPPORTED_SCHEMA_KEYWORDS and key not in ANNOTATION_SCHEMA_KEYWORDS:
            findings.append(f"{path}.{key}")
    for key in ("items", "additionalProperties", "propertyNames"):
        findings.extend(unsupported_schema_keywords(schema.get(key), f"{path}.{key}"))
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for name, child in properties.items():
            findings.extend(unsupported_schema_keywords(child, f"{path}.properties.{name}"))
    for key in ("anyOf", "oneOf"):
        branches = schema.get(key)
        if isinstance(branches, list):
            for index, child in enumerate(branches):
                findings.extend(unsupported_schema_keywords(child, f"{path}.{key}[{index}]"))
    return findings


def validate_against_schema(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
    *,
    resolve_ref: SchemaResolver,
    canonical_json: CanonicalEncoder | None = None,
) -> list[str]:
    """Validate the JSON Schema subset implemented by this package."""
    encode = canonical_json or (
        lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    errors: list[str] = []
    if "$ref" in schema:
        return validate_against_schema(
            value,
            resolve_ref(str(schema["$ref"])),
            path,
            resolve_ref=resolve_ref,
            canonical_json=encode,
        )

    any_of = schema.get("anyOf")
    if isinstance(any_of, list):
        branch_errors = [
            validate_against_schema(
                value, branch, path, resolve_ref=resolve_ref, canonical_json=encode
            )
            for branch in any_of
            if isinstance(branch, dict)
        ]
        if not branch_errors or not any(not item for item in branch_errors):
            details = [item[0] for item in branch_errors if item]
            suffix = f"; first branch errors: {details}" if details else ""
            errors.append(f"{path}: value does not satisfy anyOf{suffix}")

    one_of = schema.get("oneOf")
    if isinstance(one_of, list):
        branch_errors = [
            validate_against_schema(
                value, branch, path, resolve_ref=resolve_ref, canonical_json=encode
            )
            for branch in one_of
            if isinstance(branch, dict)
        ]
        matching = sum(1 for item in branch_errors if not item)
        if matching != 1:
            errors.append(f"{path}: value must satisfy exactly one oneOf branch, matched {matching}")

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in {schema['enum']!r}")

    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(type_matches(value, str(item)) for item in types):
            errors.append(f"{path}: expected type {types}, got {type(value).__name__}")
            return errors

    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append(f"{path}: string is shorter than minLength")
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            errors.append(f"{path}: string is longer than maxLength")
        pattern = schema.get("pattern")
        if pattern and re.search(str(pattern), value) is None:
            errors.append(f"{path}: string does not match pattern {pattern!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value is above maximum {schema['maximum']}")

    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{path}: array is shorter than minItems")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            errors.append(f"{path}: array is longer than maxItems")
        if schema.get("uniqueItems"):
            encoded = [encode(item) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    validate_against_schema(
                        item,
                        item_schema,
                        f"{path}[{index}]",
                        resolve_ref=resolve_ref,
                        canonical_json=encode,
                    )
                )

    if isinstance(value, dict):
        if len(value) < int(schema.get("minProperties", 0)):
            errors.append(f"{path}: object has fewer properties than minProperties")
        if "maxProperties" in schema and len(value) > int(schema["maxProperties"]):
            errors.append(f"{path}: object has more properties than maxProperties")
        required = schema.get("required", [])
        for name in required:
            if name not in value:
                errors.append(f"{path}: missing required property {name!r}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for name, child_schema in properties.items():
                if name in value and isinstance(child_schema, dict):
                    errors.extend(
                        validate_against_schema(
                            value[name],
                            child_schema,
                            f"{path}.{name}",
                            resolve_ref=resolve_ref,
                            canonical_json=encode,
                        )
                    )
        property_names = schema.get("propertyNames")
        if isinstance(property_names, dict):
            for name in value:
                errors.extend(
                    validate_against_schema(
                        str(name),
                        property_names,
                        f"{path}.<property-name:{name}>",
                        resolve_ref=resolve_ref,
                        canonical_json=encode,
                    )
                )
        if isinstance(properties, dict):
            extras = sorted(set(value) - set(properties))
            additional = schema.get("additionalProperties", True)
            if additional is False and extras:
                errors.append(f"{path}: unexpected properties {extras}")
            elif isinstance(additional, dict):
                for name in extras:
                    errors.extend(
                        validate_against_schema(
                            value[name],
                            additional,
                            f"{path}.{name}",
                            resolve_ref=resolve_ref,
                            canonical_json=encode,
                        )
                    )
    return errors
