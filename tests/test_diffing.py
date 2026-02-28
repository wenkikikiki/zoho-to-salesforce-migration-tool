import json
import unittest
from pathlib import Path

from creator_migration_helper.diffing import diff_schemas, render_diff_markdown


FIXTURES = Path(__file__).resolve().parent.parent / "examples"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class DiffingTests(unittest.TestCase):
    def test_detects_form_and_field_changes(self) -> None:
        old_schema = load_fixture("schema.production.json")
        new_schema = load_fixture("schema.development.json")

        diff = diff_schemas(old_schema, new_schema)

        self.assertEqual(diff["added_forms"], ["Service_Logs"])
        self.assertEqual(diff["removed_forms"], [])

        changed_by_form = {entry["form"]: entry for entry in diff["changed_forms"]}
        self.assertIn("Assignments", changed_by_form)
        self.assertIn("Vehicles", changed_by_form)

        assignments = changed_by_form["Assignments"]
        self.assertEqual(assignments["added_fields"], ["assignment_date"])
        self.assertEqual(assignments["removed_fields"], [])
        self.assertEqual(assignments["type_changes"], [])

        vehicles = changed_by_form["Vehicles"]
        self.assertEqual(vehicles["added_fields"], ["vehicle_status"])
        self.assertEqual(vehicles["removed_fields"], [])
        self.assertEqual(
            vehicles["type_changes"],
            [{"field": "mileage_km", "old_type": "number", "new_type": "decimal"}],
        )
        self.assertEqual(len(vehicles["constraint_changes"]), 1)
        self.assertEqual(vehicles["constraint_changes"][0]["field"], "vehicle_id")
        self.assertEqual(
            vehicles["constraint_changes"][0]["changes"],
            {"max_length": {"old": 20, "new": 30}},
        )

    def test_render_diff_markdown_has_risk_markers(self) -> None:
        old_schema = load_fixture("schema.production.json")
        new_schema = load_fixture("schema.development.json")
        diff = diff_schemas(old_schema, new_schema)

        rendered = render_diff_markdown(diff)
        self.assertIn("# Schema Diff Report", rendered)
        self.assertIn("Type changes (high risk):", rendered)
        self.assertIn("`mileage_km`: `number` -> `decimal`", rendered)
        self.assertIn("Added forms: 1", rendered)


if __name__ == "__main__":
    unittest.main()
