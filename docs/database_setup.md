# CommerceIQ PostgreSQL Setup

The database phase loads only validated files from `data/processed`. Raw source
CSVs are never loaded directly.

## Database Design

The `commerceiq` schema contains:

- `customers`
- `product_categories`
- `products`
- `sellers`
- `geolocation_lookup`
- `geolocation_observations`
- `orders`
- `order_items`
- `order_payments`
- `order_reviews`

Primary keys, composite keys, foreign keys, controlled order statuses,
non-negative monetary checks, review-score checks, and useful analytical
indexes are declared in `sql/schema.sql`.

## Configure a Local Connection

Install PostgreSQL separately using the
[official Windows installer guidance](https://www.postgresql.org/download/windows/),
create an empty database named `commerceiq`, and copy the example environment
file:

```powershell
psql -U postgres -c "CREATE DATABASE commerceiq;"
Copy-Item .env.example .env
```

The same database can be created through pgAdmin if `psql` is not on `PATH`.

Set the local values in `.env`:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=commerceiq
DB_USER=postgres
DB_PASSWORD=your_local_password
```

The `.env` file is excluded from Git. Never place real credentials in source
code, notebooks, SQL files, screenshots, or committed documentation.

## Validate Without Connecting

The dry run validates every processed file, required column, integer field,
timestamp field, and SQL asset:

```powershell
python scripts\run_database_load.py --dry-run
```

## Load PostgreSQL

Run the standard idempotent load:

```powershell
python scripts\run_database_load.py
```

The loader creates missing tables, truncates only the managed CommerceIQ
tables, loads them in dependency order, verifies row counts, and runs the SQL
integrity checks in one transaction. A failure rolls back the load.

During local development, use the following only when intentionally replacing
the entire managed schema:

```powershell
python scripts\run_database_load.py --recreate-schema
```

`--recreate-schema` drops only the `commerceiq` schema and is deliberately not
the default.

Successful database evidence is written to `reports/database/` without storing
credentials or connection URLs.
