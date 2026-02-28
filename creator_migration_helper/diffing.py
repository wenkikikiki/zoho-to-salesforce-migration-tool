"""Schema diffing utilities."""

from __future__ import annotations

from typing import Any


CONSTRAINT_KEYS = ("mandatory", "unique", "max_length")


def diff_schemas(old_schema: dict[str, Any], new_schema: dict[str, Any]) -> dict[str, Any]:
    old_forms = _forms_by_link_name(old_schema)
    new_forms = _forms_by_link_name(new_schema)

    old_form_names = set(old_forms)
    new_form_names = set(new_forms)

    added_forms = sorted(new_form_names - old_form_names)
    removed_forms = sorted(old_form_names - new_form_names)
    changed_forms: list[dict[str, Any]] = []

    for form_name in sorted(old_form_names & new_form_names):
        old_fields = _fields_by_link_name(old_forms[form_name])
        new_fields = _fields_by_link_name(new_forms[form_name])

        old_field_names = set(old_fields)
        new_field_names = set(new_fields)

        added_fields = sorted(new_field_names - old_field_names)
        removed_fields = sorted(old_field_names - new_field_names)
        type_changes = []
        constraint_changes = []

        for field_name in sorted(old_field_names & new_field_names):
            old_field = old_fields[field_name]
            new_field = new_fields[field_name]

            old_type = str(old_field.get("data_type", "unknown"))
            new_type = str(new_field.get("data_type", "unknown"))
            if old_type != new_type:
                type_changes.append(
                    {
                        "field": field_name,
                        "old_type": old_type,
                        "new_type": new_type,
                    }
                )

            changed_constraints = {}
            for key in CONSTRAINT_KEYS:
                old_value = old_field.get(key)
                new_value = new_field.get(key)
                if old_value != new_value:
                    changed_constraints[key] = {"old": old_value, "new": new_value}

            if changed_constraints:
                constraint_changes.append(
                    {
                        "field": field_name,
                        "changes": changed_constraints,
                    }
                )

        if added_fields or removed_fields or type_changes or constraint_changes:
            changed_forms.append(
                {
                    "form": form_name,
                    "added_fields": added_fields,
                    "removed_fields": removed_fields,
                    "type_changes": type_changes,
                    "constraint_changes": constraint_changes,
                }
            )

    return {
        "old_environment": old_schema.get("environment"),
        "new_environment": new_schema.get("environment"),
        "added_forms": added_forms,
        "removed_forms": removed_forms,
        "changed_forms": changed_forms,
    }


def render_diff_markdown(diff: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Schema Diff Report")
    lines.append("")
    old_env = diff.get("old_environment") or "unknown"
    new_env = diff.get("new_environment") or "unknown"
    lines.append(f"- Old environment: `{old_env}`")
    lines.append(f"- New environment: `{new_env}`")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Added forms: {len(diff.get('added_forms', []))}")
    lines.append(f"- Removed forms: {len(diff.get('removed_forms', []))}")
    lines.append(f"- Changed forms: {len(diff.get('changed_forms', []))}")
    lines.append("")

    added_forms = diff.get("added_forms", [])
    if added_forms:
        lines.append("## Added Forms")
        lines.append("")
        for form in added_forms:
            lines.append(f"- `{form}`")
        lines.append("")

    removed_forms = diff.get("removed_forms", [])
    if removed_forms:
        lines.append("## Removed Forms")
        lines.append("")
        for form in removed_forms:
            lines.append(f"- `{form}`")
        lines.append("")

    changed_forms = diff.get("changed_forms", [])
    if not changed_forms and not added_forms and not removed_forms:
        lines.append("No schema changes detected.")
        lines.append("")
        return "\n".join(lines)

    if changed_forms:
        lines.append("## Changed Forms")
        lines.append("")
        for changed in changed_forms:
            form = changed["form"]
            lines.append(f"### `{form}`")
            lines.append("")

            if changed.get("added_fields"):
                lines.append("Added fields:")
                for field in changed["added_fields"]:
                    lines.append(f"- `{field}`")
                lines.append("")

            if changed.get("removed_fields"):
                lines.append("Removed fields (high risk):")
                for field in changed["removed_fields"]:
                    lines.append(f"- `{field}`")
                lines.append("")

            if changed.get("type_changes"):
                lines.append("Type changes (high risk):")
                for change in changed["type_changes"]:
                    lines.append(
                        f"- `{change['field']}`: `{change['old_type']}` -> `{change['new_type']}`"
                    )
                lines.append("")

            if changed.get("constraint_changes"):
                lines.append("Constraint changes:")
                for change in changed["constraint_changes"]:
                    parts = []
                    for key, values in sorted(change["changes"].items()):
                        parts.append(f"{key} `{values['old']}` -> `{values['new']}`")
                    lines.append(f"- `{change['field']}`: " + ", ".join(parts))
                lines.append("")

    return "\n".join(lines)


def _forms_by_link_name(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for form in schema.get("forms", []):
        name = str(form.get("link_name") or "").strip()
        if name:
            output[name] = form
    return output


def _fields_by_link_name(form: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for field in form.get("fields", []):
        name = str(field.get("link_name") or "").strip()
        if name:
            output[name] = field
    return output
