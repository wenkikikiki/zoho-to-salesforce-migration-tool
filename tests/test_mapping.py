import json
import unittest
from pathlib import Path

from creator_migration_helper.mapping import (
    generate_mapping_rows,
    lint_zoho_field_name,
    load_salesforce_objects,
    type_compatibility_note,
)


FIXTURES = Path(__file__).resolve().parent.parent / "examples"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class MappingTests(unittest.TestCase):
    def test_generates_mapping_rows_with_suggestions(self) -> None:
        schema = load_fixture("schema.development.json")
        objects = load_salesforce_objects(FIXTURES / "salesforce_objects.json")

        rows = generate_mapping_rows(schema, objects)
        self.assertTrue(rows)

        by_field = {(row["zoho_form"], row["zoho_field"]): row for row in rows}
        vehicle_id = by_field[("Vehicles", "vehicle_id")]
        self.assertEqual(vehicle_id["suggested_sf_object"], "Vehicle__c")
        self.assertEqual(vehicle_id["suggested_sf_field"], "Vehicle_ID__c")

        assignment_date = by_field[("Assignments", "assignment_date")]
        self.assertEqual(assignment_date["suggested_sf_object"], "Driver_Assignment__c")
        self.assertEqual(assignment_date["suggested_sf_field"], "Assignment_Date__c")

    def test_lint_flags_problematic_field_names(self) -> None:
        notes = lint_zoho_field_name("123 invalid name!")
        self.assertIn("Zoho field name starts with a digit", notes)
        self.assertIn("Zoho field name contains whitespace", notes)
        self.assertIn("Zoho field name contains non-alphanumeric characters", notes)

    def test_type_compatibility_note_detects_mismatch(self) -> None:
        note = type_compatibility_note("date", "Text")
        self.assertIn("Potential type mismatch", note or "")
        self.assertIsNone(type_compatibility_note("number", "Currency"))


if __name__ == "__main__":
    unittest.main()
