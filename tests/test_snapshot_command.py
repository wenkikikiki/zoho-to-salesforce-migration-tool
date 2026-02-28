import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from creator_migration_helper.cli import run_snapshot


FAKE_SCHEMA = {
    "schema_version": 1,
    "generated_at": "2026-02-27T00:00:00+00:00",
    "base_url": "www.zohoapis.com",
    "owner": "owner",
    "app": "fleet_hub",
    "environment": "production",
    "forms": [
        {
            "link_name": "Vehicles",
            "display_name": "Vehicles",
            "type": "Form",
            "fields": [
                {
                    "link_name": "vehicle_id",
                    "display_name": "Vehicle ID",
                    "data_type": "singleline",
                    "mandatory": True,
                    "unique": True,
                    "max_length": 20,
                }
            ],
        }
    ],
}


class SnapshotCommandTests(unittest.TestCase):
    def test_run_snapshot_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            args = Namespace(
                base_url="www.zohoapis.com",
                owner="owner",
                app="fleet_hub",
                token="TOKEN123",
                env="production",
                out_dir=tmp,
            )

            with patch("creator_migration_helper.cli.build_schema_snapshot", return_value=FAKE_SCHEMA):
                exit_code = run_snapshot(args)

            self.assertEqual(exit_code, 0)
            schema_path = Path(tmp) / "schema.production.json"
            dictionary_path = Path(tmp) / "data_dictionary.production.md"
            self.assertTrue(schema_path.exists())
            self.assertTrue(dictionary_path.exists())
            self.assertIn("vehicle_id", schema_path.read_text(encoding="utf-8"))
            self.assertIn("Zoho Creator Data Dictionary", dictionary_path.read_text(encoding="utf-8"))

    def test_run_snapshot_requires_token(self) -> None:
        args = Namespace(
            base_url="www.zohoapis.com",
            owner="owner",
            app="fleet_hub",
            token="",
            env="production",
            out_dir="out",
        )
        with self.assertRaises(ValueError):
            run_snapshot(args)


if __name__ == "__main__":
    unittest.main()
