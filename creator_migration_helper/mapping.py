"""Salesforce mapping scaffold generation."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SalesforceField:
    api_name: str
    label: str
    data_type: str


@dataclass(frozen=True, slots=True)
class SalesforceObject:
    api_name: str
    label: str
    fields: tuple[SalesforceField, ...]


def load_salesforce_objects(path: Path) -> list[SalesforceObject]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_objects = payload["objects"] if isinstance(payload, dict) and "objects" in payload else payload
    if not isinstance(raw_objects, list):
        raise ValueError("Salesforce schema file must be a list or contain an `objects` list")

    objects: list[SalesforceObject] = []
    for raw_obj in raw_objects:
        obj_name = _first_str(raw_obj, "api_name", "name", "object")
        if not obj_name:
            continue
        obj_label = _first_str(raw_obj, "label", "display_name") or obj_name
        raw_fields = raw_obj.get("fields", [])
        if isinstance(raw_fields, dict):
            raw_fields = [dict(name=name, **data) for name, data in raw_fields.items()]
        fields = []
        for raw_field in raw_fields:
            field_name = _first_str(raw_field, "api_name", "name", "field")
            if not field_name:
                continue
            field_label = _first_str(raw_field, "label", "display_name") or field_name
            field_type = _first_str(raw_field, "type", "data_type") or "unknown"
            fields.append(
                SalesforceField(
                    api_name=field_name,
                    label=field_label,
                    data_type=field_type,
                )
            )
        objects.append(SalesforceObject(api_name=obj_name, label=obj_label, fields=tuple(fields)))
    return objects


def generate_mapping_rows(
    schema: dict[str, Any], salesforce_objects: list[SalesforceObject]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for form in schema.get("forms", []):
        form_name = str(form.get("link_name", ""))
        form_display = str(form.get("display_name") or form_name)
        best_object, _ = suggest_salesforce_object(form_name, form_display, salesforce_objects)

        for field in form.get("fields", []):
            field_name = str(field.get("link_name", ""))
            field_display = str(field.get("display_name") or field_name)
            field_type = str(field.get("data_type") or "unknown")

            suggested_field, confidence = suggest_salesforce_field(
                form_name=form_name,
                field_name=field_name,
                field_display=field_display,
                object_candidate=best_object,
                objects=salesforce_objects,
            )

            notes = lint_zoho_field_name(field_name)
            if suggested_field:
                mismatch_note = type_compatibility_note(field_type, suggested_field.data_type)
                if mismatch_note:
                    notes.append(mismatch_note)
            elif not best_object:
                notes.append("No Salesforce object candidate found")

            rows.append(
                {
                    "zoho_form": form_name,
                    "zoho_field": field_name,
                    "zoho_type": field_type,
                    "mandatory": bool(field.get("mandatory")),
                    "unique": bool(field.get("unique")),
                    "suggested_sf_object": best_object.api_name if best_object else "",
                    "suggested_sf_field": suggested_field.api_name if suggested_field else "",
                    "confidence": f"{confidence:.2f}",
                    "notes": "; ".join(notes),
                }
            )
    return rows


def write_mapping_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "zoho_form",
        "zoho_field",
        "zoho_type",
        "mandatory",
        "unique",
        "suggested_sf_object",
        "suggested_sf_field",
        "confidence",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def suggest_salesforce_object(
    form_name: str, form_display: str, objects: list[SalesforceObject]
) -> tuple[SalesforceObject | None, float]:
    if not objects:
        return None, 0.0

    target = f"{form_name} {form_display}".strip()
    scored = [(obj, _name_score(target, f"{obj.api_name} {obj.label}")) for obj in objects]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[0]


def suggest_salesforce_field(
    form_name: str,
    field_name: str,
    field_display: str,
    object_candidate: SalesforceObject | None,
    objects: list[SalesforceObject],
) -> tuple[SalesforceField | None, float]:
    target = f"{field_name} {field_display}".strip()

    if object_candidate and object_candidate.fields:
        scored = [(field, _name_score(target, f"{field.api_name} {field.label}")) for field in object_candidate.fields]
        scored.sort(key=lambda item: item[1], reverse=True)
        if scored and scored[0][1] >= 0.42:
            return scored[0]

    # Fallback: search across all objects.
    best_field: SalesforceField | None = None
    best_score = 0.0
    for obj in objects:
        form_score = _name_score(form_name, f"{obj.api_name} {obj.label}")
        for field in obj.fields:
            score = (_name_score(target, f"{field.api_name} {field.label}") * 0.8) + (form_score * 0.2)
            if score > best_score:
                best_score = score
                best_field = field

    if best_field and best_score >= 0.42:
        return best_field, best_score
    return None, 0.0


def lint_zoho_field_name(name: str) -> list[str]:
    notes = []
    if len(name) > 40:
        notes.append("Zoho field name is long; Salesforce API names are easier to manage when <= 40 chars")
    if re.search(r"\s", name):
        notes.append("Zoho field name contains whitespace")
    if re.search(r"[^A-Za-z0-9_]", name):
        notes.append("Zoho field name contains non-alphanumeric characters")
    if name and name[0].isdigit():
        notes.append("Zoho field name starts with a digit")
    if name.lower() in {"id", "name", "type", "owner", "createddate", "lastmodifieddate"}:
        notes.append("Zoho field name may conflict with common Salesforce standard fields")
    return notes


def type_compatibility_note(zoho_type: str, salesforce_type: str) -> str | None:
    allowed = _compatible_salesforce_types(zoho_type)
    if not allowed:
        return None
    normalized_sf_type = salesforce_type.lower()
    if normalized_sf_type in allowed:
        return None
    return f"Potential type mismatch: Zoho `{zoho_type}` vs Salesforce `{salesforce_type}`"


def _compatible_salesforce_types(zoho_type: str) -> set[str]:
    mapping = {
        "singleline": {"text", "string", "textarea"},
        "multiline": {"textarea", "longtextarea", "text"},
        "email": {"email", "text", "string"},
        "url": {"url", "text", "string"},
        "number": {"number", "currency", "percent", "double", "integer"},
        "decimal": {"number", "currency", "percent", "double"},
        "date": {"date"},
        "datetime": {"datetime"},
        "boolean": {"checkbox", "boolean"},
        "lookup": {"lookup", "masterdetail"},
        "picklist": {"picklist", "multipicklist", "text"},
    }
    return mapping.get(zoho_type.lower(), set())


def _name_score(left: str, right: str) -> float:
    left_norm = _normalize_name(left)
    right_norm = _normalize_name(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0

    left_tokens = set(_tokenize(left_norm))
    right_tokens = set(_tokenize(right_norm))
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens) or 1
    jaccard = overlap / union
    seq = SequenceMatcher(a=left_norm, b=right_norm).ratio()
    return (jaccard * 0.55) + (seq * 0.45)


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", " ", value.lower()).strip()


def _tokenize(value: str) -> list[str]:
    return [token for token in re.split(r"[_\s]+", value) if token]


def _first_str(mapping: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
