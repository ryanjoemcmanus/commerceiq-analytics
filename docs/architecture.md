# CommerceIQ Architecture and Data Model

## Analytical architecture

```mermaid
flowchart LR
    A[Public Olist CSV files] --> B[Read-only quality audit]
    B --> C[Validated cleaning pipeline]
    C --> D[(PostgreSQL<br/>commerceiq schema)]
    D --> E[Named KPI and advanced SQL]
    E --> F[Versioned analytical extracts]
    F --> G[Python EDA notebook]
    F --> H[Power BI source workbook]
    H --> I[Three-page stakeholder dashboard]

    B -. evidence .-> J[Quality reports]
    C -. lineage .-> K[Cleaning manifest]
    E -. checksums .-> L[Analytics manifest]
```

The boundaries are deliberate. Raw files remain immutable; reusable Python owns
data validation and cleaning; PostgreSQL owns the normalized analytical model;
SQL owns KPI semantics; notebooks and Power BI consume validated outputs rather
than redefining metrics independently.

## Relational model

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    ORDERS ||--o{ ORDER_ITEMS : contains
    ORDERS ||--o{ ORDER_PAYMENTS : paid_with
    ORDERS ||--o{ ORDER_REVIEWS : receives
    PRODUCTS ||--o{ ORDER_ITEMS : appears_in
    SELLERS ||--o{ ORDER_ITEMS : fulfills
    PRODUCT_CATEGORIES ||--o{ PRODUCTS : classifies
    GEOLOCATION_LOOKUP ||--o{ CUSTOMERS : locates
    GEOLOCATION_LOOKUP ||--o{ SELLERS : locates

    CUSTOMERS {
        string customer_id PK
        string customer_unique_id
        string customer_zip_code_prefix FK
        string customer_city
        string customer_state
    }
    ORDERS {
        string order_id PK
        string customer_id FK
        string order_status
        timestamp purchase_timestamp
        timestamp delivered_customer_date
        timestamp estimated_delivery_date
    }
    ORDER_ITEMS {
        string order_id PK,FK
        int order_item_id PK
        string product_id FK
        string seller_id FK
        numeric price
        numeric freight_value
    }
    ORDER_PAYMENTS {
        string order_id PK,FK
        int payment_sequential PK
        string payment_type
        int payment_installments
        numeric payment_value
    }
    ORDER_REVIEWS {
        string review_id PK
        string order_id FK
        int review_score
        timestamp review_creation_date
    }
    PRODUCTS {
        string product_id PK
        string category_name FK
        numeric product_weight_g
    }
    SELLERS {
        string seller_id PK
        string seller_zip_code_prefix FK
        string seller_state
    }
    PRODUCT_CATEGORIES {
        string category_name PK
        string category_name_english
    }
    GEOLOCATION_LOOKUP {
        string zip_code_prefix PK
        numeric latitude
        numeric longitude
    }
```

## Grain and metric safeguards

- Orders are unique at `order_id`.
- Items are unique at `(order_id, order_item_id)`.
- Payments are unique at `(order_id, payment_sequential)` and are not additive
  as order counts across methods because one order can use multiple records.
- Reviews are aggregated to the order grain before joining to order-level KPIs.
- Delivered GMV is item price on delivered orders and excludes freight.
- Customer retention uses `customer_unique_id`, not the order-specific
  `customer_id`.

See [data_model.md](data_model.md) for implementation details and
[kpi_definitions.md](kpi_definitions.md) for the complete semantic contract.
