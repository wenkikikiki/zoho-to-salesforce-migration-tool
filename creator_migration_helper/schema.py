"""Schema snapshot and data dictionary generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .zoho import ZohoClient


SCHEMA_VERSION = 1


def build_schema_snapshot(client: ZohoClient, environment: str) -> dict[str, Any]:
    forms = []
    for raw_form in client.get_forms():
        form_link_name = str(raw_form.get("link_name") or "").strip()
        if not form_link_name:
            continue
        raw_fields = client.get_fields(form_link_name)
        forms.append(normalize_form(raw_form, raw_fields))

    forms.sort(key=lambda form: form["link_name"])
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": client.base_url,
        "owner": client.owner,
        "app": client.app,
        "environment": environment,
        "forms": forms,
    }


def normalize_form(raw_form: dict[str, Any], raw_fields: list[dict[str, Any]]) -> dict[str, Any]:
    link_name = str(raw_form.get("link_name") or "").strip()
    fields = [normalize_field(field) for field in raw_fields if _field_link_name(field)]
    fields.sort(key=lambda field: field["link_name"])
    return {
        "link_name": link_name,
        "display_name": str(raw_form.get("display_name") or link_name),
        "type": str(raw_form.get("type") or "form"),
        "fields": fields,
    }


def normalize_field(raw_field: dict[str, Any]) -> dict[str, Any]:
    link_name = _field_link_name(raw_field)
    max_length = _to_int(raw_field.get("max_length"))
    return {
        "link_name": link_name,
        "display_name": str(raw_field.get("display_name") or link_name),
        "data_type": str(raw_field.get("data_type") or "unknown"),
        "mandatory": _to_bool(raw_field.get("mandatory")),
        "unique": _to_bool(raw_field.get("unique")),
        "max_length": max_length,
    }


def write_schema_json(schema: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_schema_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_data_dictionary_markdown(schema: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Zoho Creator Data Dictionary")
    lines.append("")
    lines.append(f"- Owner: `{schema.get('owner', 'unknown')}`")
    lines.append(f"- App: `{schema.get('app', 'unknown')}`")
    lines.append(f"- Environment: `{schema.get('environment', 'unknown')}`")
    lines.append(f"- Generated At (UTC): `{schema.get('generated_at', 'unknown')}`")
    lines.append("")

    forms = schema.get("forms", [])
    if not forms:
        lines.append("_No forms discovered._")
        return "\n".join(lines) + "\n"

    for form in forms:
        form_link = str(form.get("link_name", ""))
        form_name = str(form.get("display_name") or form_link)
        lines.append(f"## {escape_markdown(form_name)} (`{form_link}`)")
        lines.append("")
        lines.append("| Field | Display Name | Type | Mandatory | Unique | Max Length |")
        lines.append("|---|---|---|---|---|---|")
        for field in form.get("fields", []):
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{field.get('link_name', '')}`",
                        escape_markdown(str(field.get("display_name", ""))),
                        f"`{field.get('data_type', 'unknown')}`",
                        "yes" if field.get("mandatory") else "no",
                        "yes" if field.get("unique") else "no",
                        str(field.get("max_length") or ""),
                    ]
                )
                + " |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_data_dictionary_markdown(schema: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_data_dictionary_markdown(schema), encoding="utf-8")


def _field_link_name(raw_field: dict[str, Any]) -> str:
    return str(
        raw_field.get("link_name")
        or raw_field.get("field_name")
        or raw_field.get("column_name")
        or ""
    ).strip()


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            return int(stripped)
    return None


def escape_markdown(text: str) -> str:
    return text.replace("|", "\\|")
