import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "examples"


class CLITests(unittest.TestCase):
    def test_diff_command_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "schema_diff.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "creator_migration_helper",
                    "diff",
                    str(FIXTURES / "schema.production.json"),
                    str(FIXTURES / "schema.development.json"),
                    "--out",
                    str(out_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out_path.exists())
            content = out_path.read_text(encoding="utf-8")
            self.assertIn("Schema Diff Report", content)
            self.assertIn("`Service_Logs`", content)

    def test_mapping_command_writes_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "mapping.csv"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "creator_migration_helper",
                    "mapping",
                    "--schema",
                    str(FIXTURES / "schema.development.json"),
                    "--salesforce-objects",
                    str(FIXTURES / "salesforce_objects.json"),
                    "--out",
                    str(out_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out_path.exists())

            with out_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertGreater(len(rows), 0)
            vehicle_rows = [row for row in rows if row["zoho_form"] == "Vehicles" and row["zoho_field"] == "vehicle_id"]
            self.assertEqual(vehicle_rows[0]["suggested_sf_field"], "Vehicle_ID__c")


if __name__ == "__main__":
    unittest.main()
