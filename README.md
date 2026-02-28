# creator-migration-helper

`creator-migration-helper` is a small CLI for:

- snapshotting Zoho Creator form/field metadata
- generating a markdown data dictionary
- diffing schema snapshots
- generating a Zoho-to-Salesforce mapping seed CSV

## Install

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Commands

### 1) Snapshot Zoho schema + dictionary

```bash
creator-migration-helper snapshot \
  --base-url www.zohoapis.com \
  --owner <zoho_owner> \
  --app <zoho_app_link_name> \
  --token <oauth_token> \
  --env production \
  --out-dir out
```

Outputs:

- `out/schema.production.json`
- `out/data_dictionary.production.md`

### 2) Diff snapshots

```bash
creator-migration-helper diff \
  out/schema.production.json \
  out/schema.development.json \
  --out out/schema_diff.md \
  --json-out out/schema_diff.json
```

### 3) Generate Salesforce mapping scaffold

```bash
creator-migration-helper mapping \
  --schema out/schema.production.json \
  --salesforce-objects examples/salesforce_objects.json \
  --out out/sf_mapping_seed.csv
```

## Example fixtures

The `examples/` folder includes sample fleet-style artifacts:

- `schema.production.json`
- `schema.development.json`
- `salesforce_objects.json`

You can run diff/mapping commands against these fixtures without live Zoho access.

## Test

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -v
```
