# CommerceIQ Cleaning Rules

The cleaning pipeline is conservative by design. It standardizes representation
and adds transparent quality flags while preserving source grain and retaining
records needed for analysis.

## Global Rules

- Raw CSV files are read-only and never overwritten.
- Surrounding whitespace is removed from text values.
- Blank text values are standardized as missing.
- Declared numeric columns are converted explicitly. A populated value that
  cannot be converted stops the pipeline with a clear error.
- Declared timestamp columns are parsed explicitly. Unparseable populated
  values are retained as missing timestamps and identified by `dq_invalid_*`
  flags.
- Processed CSVs use UTF-8 and standardized `YYYY-MM-DD HH:MM:SS` timestamps.
- Every processed file and source file receives a SHA-256 checksum in the
  cleaning manifest.

## Table-Specific Rules

### Orders

- Normalize `order_status` to lowercase.
- Preserve all timestamps.
- Flag purchase-after-carrier, approval-after-carrier, and
  carrier-after-customer-delivery sequences.
- Add the combined `dq_has_timestamp_sequence_issue` flag.

### Order Items and Payments

- Validate monetary and sequence fields as numeric.
- Normalize payment type to lowercase.
- Flag negative price, freight, payment, or installment values instead of
  silently removing rows.

### Reviews

- Parse creation and answer timestamps.
- Flag review scores outside the expected 1–5 range.
- Preserve the source composite grain of `review_id + order_id`.

### Products and Categories

- Correct `product_name_lenght` and `product_description_lenght` only in the
  processed output.
- Add the English category through the translation table.
- Use the Portuguese source category as the fallback when a populated category
  lacks a translation.
- Add untranslated source categories to the processed translation dimension
  with a transparent `dq_translation_missing` flag so database foreign keys can
  be enforced.
- Use `unknown` only when the source category itself is missing.
- Add separate flags for missing categories and missing translations.
- Never drop a product because its category is missing or untranslated.

### Geolocation

- Remove exact duplicate observations only.
- Preserve distinct coordinate, city, and state variants in the cleaned source
  table.
- Produce `geolocation_lookup.csv` at one row per ZIP-code prefix.
- Use median coordinates across unique observations.
- Select the most frequent city/state pair, with alphabetical tie-breaking.
- Retain observation and variant counts and flag prefixes associated with
  multiple state codes.

## Validation Gates

Cleaning stops before writing output if a required source schema, declared key,
or strict foreign-key relationship fails. After transformation, keys and
relationships are checked again. Timestamp exceptions and untranslated
categories remain review items because the pipeline intentionally preserves
them with quality flags.

## Generated Outputs

Processed tables are written to `data/processed/`. Validation and lineage files
are written to `reports/data_cleaning/`:

- `cleaning_manifest.json`
- `post_cleaning_key_checks.csv`
- `post_cleaning_relationship_checks.csv`
- `post_cleaning_business_rule_checks.csv`
