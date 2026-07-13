"""Tests for conservative CommerceIQ cleaning transformations."""

import pandas as pd

from src.data_cleaning import build_geolocation_lookup, clean_source_table


def test_order_cleaning_parses_timestamps_and_preserves_sequence_issue() -> None:
    """Reversed operational timestamps should be flagged, not overwritten."""

    frame = pd.DataFrame(
        {
            "order_id": ["order-1"],
            "customer_id": ["customer-1"],
            "order_status": [" DELIVERED "],
            "order_purchase_timestamp": ["2024-01-02 12:00:00"],
            "order_approved_at": ["2024-01-02 13:00:00"],
            "order_delivered_carrier_date": ["2024-01-01 12:00:00"],
            "order_delivered_customer_date": ["2024-01-03 12:00:00"],
            "order_estimated_delivery_date": ["2024-01-04 12:00:00"],
        }
    )

    result = clean_source_table(frame, file_name="olist_orders_dataset.csv").frame

    assert result.loc[0, "order_status"] == "delivered"
    assert pd.api.types.is_datetime64_any_dtype(result["order_purchase_timestamp"])
    assert bool(result.loc[0, "dq_purchase_after_carrier_handoff"])
    assert bool(result.loc[0, "dq_has_timestamp_sequence_issue"])


def test_product_cleaning_retains_untranslated_category_with_flag() -> None:
    """An untranslated product should remain analyzable with a transparent fallback."""

    frame = pd.DataFrame(
        {
            "product_id": ["product-1"],
            "product_category_name": ["categoria_sem_traducao"],
            "product_name_lenght": [10],
            "product_description_lenght": [20],
            "product_photos_qty": [1],
            "product_weight_g": [100],
            "product_length_cm": [10],
            "product_height_cm": [5],
            "product_width_cm": [8],
        }
    )
    translation = pd.DataFrame(
        {
            "product_category_name": ["categoria_conhecida"],
            "product_category_name_english": ["known_category"],
        }
    )

    result = clean_source_table(
        frame,
        file_name="olist_products_dataset.csv",
        category_translation=translation,
    ).frame

    assert "product_name_length" in result.columns
    assert "product_name_lenght" not in result.columns
    assert result.loc[0, "product_category_name_english"] == "categoria_sem_traducao"
    assert bool(result.loc[0, "dq_category_translation_missing"])


def test_geolocation_cleaning_and_lookup_are_deterministic() -> None:
    """Exact duplicates should be removed before one-row-per-ZIP aggregation."""

    source = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": [1000, 1000, 1000],
            "geolocation_lat": [-23.0, -23.0, -24.0],
            "geolocation_lng": [-46.0, -46.0, -47.0],
            "geolocation_city": ["sao paulo", "sao paulo", "são paulo"],
            "geolocation_state": ["SP", "SP", "SP"],
        }
    )

    cleaned = clean_source_table(
        source,
        file_name="olist_geolocation_dataset.csv",
    ).frame
    lookup = build_geolocation_lookup(
        cleaned,
        source_geolocation=source,
    ).frame

    assert len(cleaned) == 2
    assert len(lookup) == 1
    assert lookup.loc[0, "source_observation_count"] == 3
    assert lookup.loc[0, "unique_observation_count"] == 2
    assert lookup.loc[0, "city"] == "sao paulo"

