import unittest

from creator_migration_helper.schema import build_schema_snapshot, render_data_dictionary_markdown


class FakeClient:
    base_url = "www.zohoapis.com"
    owner = "owner"
    app = "fleet_hub"

    def get_forms(self):
        return [
            {"link_name": "Vehicles", "display_name": "Vehicles", "type": "Form"},
            {"link_name": "Assignments", "display_name": "Assignments", "type": "Form"},
        ]

    def get_fields(self, form_link_name):
        if form_link_name == "Vehicles":
            return [
                {"field_name": "registration_number", "display_name": "Registration Number", "data_type": "singleline", "mandatory": True, "unique": True, "max_length": "16"},
                {"field_name": "vehicle_id", "display_name": "Vehicle ID", "data_type": "singleline", "mandatory": True, "unique": True, "max_length": 20},
            ]
        return [
            {"field_name": "driver_id", "display_name": "Driver ID", "data_type": "singleline", "mandatory": True, "unique": False, "max_length": 20},
        ]


class SchemaTests(unittest.TestCase):
    def test_build_schema_snapshot_is_sorted_and_normalized(self):
        schema = build_schema_snapshot(FakeClient(), environment="production")

        self.assertEqual([form["link_name"] for form in schema["forms"]], ["Assignments", "Vehicles"])
        vehicles = schema["forms"][1]
        self.assertEqual([field["link_name"] for field in vehicles["fields"]], ["registration_number", "vehicle_id"])
        self.assertEqual(vehicles["fields"][0]["max_length"], 16)

    def test_render_data_dictionary_contains_form_tables(self):
        schema = build_schema_snapshot(FakeClient(), environment="production")
        rendered = render_data_dictionary_markdown(schema)
        self.assertIn("# Zoho Creator Data Dictionary", rendered)
        self.assertIn("## Vehicles (`Vehicles`)", rendered)
        self.assertIn("`vehicle_id`", rendered)


if __name__ == "__main__":
    unittest.main()
