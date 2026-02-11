from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from kotsovolos_pipeline import (  # noqa: E402
    build_menu_dataframe,
    extract_black_friday_flag,
    extract_prices,
    parse_aem_parts,
    parse_product_entry,
    build_product_summaries,
)


def test_build_menu_dataframe_extracts_nested_categories() -> None:
    payload = [
        {
            "navTitle": "Προϊόντα",
            "childMenu": [
                {
                    "level": "1",
                    "uniqueID": "100",
                    "jcr:title": "L1",
                    "seo_url": "/l1",
                    "aem_url": "/a/b/c1",
                    "childMenu": [
                        {
                            "level": "2",
                            "uniqueID": "200",
                            "jcr:title": "L2",
                            "seo_url": "/l2",
                            "aem_url": "/a/b/c2",
                            "childMenu": [
                                {
                                    "level": "3",
                                    "uniqueID": "300",
                                    "jcr:title": "L3",
                                    "seo_url": "/l3",
                                    "aem_url": "/a/b/c3",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    df = build_menu_dataframe(payload)

    assert len(df) == 3
    assert set(df["Level"].tolist()) == {1, 2, 3}


def test_parse_aem_parts() -> None:
    parts = parse_aem_parts("/content/kotsovolos/b2c/gr/products/tv/oled/abc")
    assert parts == ["tv", "oled", "abc"]


def test_extract_black_friday_flag_and_prices() -> None:
    product = {
        "attributes": [{"values": [{"value": "Offer: Black Friday Deal"}]}],
        "price": [{"usage": "Display", "value": 999}, {"usage": "Offer", "value": 849}],
    }
    assert extract_black_friday_flag(product) is True
    assert extract_prices(product) == (999, 849)


def test_parse_product_entry_returns_expected_columns() -> None:
    product = {
        "uniqueID": "u1",
        "singleSKUCatalogEntryID": "sku1",
        "partNumber": "pn1",
        "shortDescription": "desc",
        "name": "Product 1",
        "manufacturer": "BrandX",
        "buyable": True,
        "attributes": [],
        "UserData": [{"seo_url": "/p/1"}],
        "price": [{"usage": "Display", "value": 100}],
    }
    category = {"Category_Title": "TV", "Category_ID_number": "123"}
    row = parse_product_entry(product, category)
    assert row["name"] == "Product 1"
    assert row["Category_Title"] == "TV"
    assert row["Original_Price"] == 100


def test_build_product_summaries() -> None:
    df = pd.DataFrame(
        [
            {"Category_Title": "TV", "manufacturer": "A"},
            {"Category_Title": "TV", "manufacturer": "B"},
            {"Category_Title": "Phones", "manufacturer": "A"},
        ]
    )
    category_summary, brand_summary = build_product_summaries(df)
    assert category_summary.iloc[0]["Category_Title"] == "TV"
    assert brand_summary.iloc[0]["manufacturer"] == "A"
