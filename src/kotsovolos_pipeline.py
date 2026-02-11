import argparse
import logging
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MENU_URL = "https://new-content.kotsovolos.gr/content/kotsovolos/b2c/gr/home.navMenu.json"
MODEL_URL_TEMPLATE = "https://new-content.kotsovolos.gr/content/kotsovolos/b2c/gr/products/{path}.model.json"
CATALOG_URL_TEMPLATE = (
    "https://www.kotsovolos.gr/api/ext/search/store/10151/productview/byCategory/{category_key}"
    "?searchType=1002&searchSource=E&pageNumber={page}&pageSize={page_size}"
    "&responseFormat=json&catalogId=10551&p_mode=mixed&currency=EUR&langId=-24&orderBy=10"
)


def setup_logger(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def build_session(retries: int, backoff_factor: float) -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }
    )
    return session


def fetch_json(session: requests.Session, url: str, timeout: int) -> dict[str, Any] | list[Any] | None:
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed request %s: %s", url, exc)
        return None


def find_products_root(nav_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for item in nav_data:
        if item.get("navTitle") == "Προϊόντα" and isinstance(item.get("childMenu"), list):
            return item["childMenu"]
    for item in nav_data:
        if isinstance(item.get("childMenu"), list):
            return item["childMenu"]
    raise ValueError("Could not find products root menu in nav response.")


def extract_categories_recursive(
    menu: list[dict[str, Any]],
    level: int,
    parent_unique_id: str | None,
    rows: list[dict[str, Any]],
) -> None:
    for category in menu:
        unique_id = str(category.get("uniqueID", "")).strip() or None
        row = {
            "Level": level,
            "UniqueID": unique_id,
            "ParentUniqueID": parent_unique_id,
            "Title": category.get("jcr:title", "N/A"),
            "SEO_URL": category.get("seo_url", "N/A"),
            "AEM_URL": category.get("aem_url", "N/A"),
        }
        rows.append(row)

        child_menu = category.get("childMenu")
        if isinstance(child_menu, list) and child_menu:
            extract_categories_recursive(child_menu, level + 1, unique_id, rows)


def build_menu_dataframe(nav_data: list[dict[str, Any]]) -> pd.DataFrame:
    root_menu = find_products_root(nav_data)
    rows: list[dict[str, Any]] = []
    extract_categories_recursive(root_menu, level=1, parent_unique_id=None, rows=rows)
    return pd.DataFrame(rows, columns=["Level", "UniqueID", "ParentUniqueID", "Title", "SEO_URL", "AEM_URL"])


def save_menu_workbook(menu_df: pd.DataFrame, menu_file: Path) -> None:
    menu_file.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(menu_file, engine="openpyxl") as writer:
        if menu_df.empty:
            pd.DataFrame(columns=menu_df.columns).to_excel(writer, sheet_name="Level_1", index=False)
            logging.info("Saved empty menu workbook to %s", menu_file)
            return

        max_level = int(menu_df["Level"].max())
        for level in range(1, max_level + 1):
            level_data = menu_df[menu_df["Level"] == level].copy()
            level_data.to_excel(writer, sheet_name=f"Level_{level}", index=False)

        level_3_data = menu_df[menu_df["Level"] == 3][["UniqueID", "Title", "AEM_URL"]].copy()
        level_3_data.to_excel(writer, sheet_name="Level_3_UniqueIDs", index=False)
    logging.info("Saved menu workbook to %s", menu_file)


def load_categories_from_menu(menu_file: Path, level: int, max_categories: int | None = None) -> pd.DataFrame:
    if not menu_file.exists():
        raise FileNotFoundError(f"Menu file not found: {menu_file}")

    xls = pd.ExcelFile(menu_file)
    preferred_sheet = f"Level_{level}"
    sheet = preferred_sheet if preferred_sheet in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(menu_file, sheet_name=sheet)

    if "Level" in df.columns:
        df = df[df["Level"] == level]
    if "AEM_URL" not in df.columns:
        raise ValueError(f"Column 'AEM_URL' not found in sheet '{sheet}' of {menu_file}")

    categories = df[df["AEM_URL"].notna()].copy()
    categories["AEM_URL"] = categories["AEM_URL"].astype(str).str.strip()
    categories = categories[categories["AEM_URL"] != ""]
    categories = categories.drop_duplicates(subset=["AEM_URL"])
    categories = categories.reset_index(drop=True)
    if max_categories:
        categories = categories.head(max_categories)
    return categories


def parse_aem_parts(aem_url: str) -> list[str] | None:
    parts = [part for part in str(aem_url).split("/") if part]
    if len(parts) < 3:
        return None
    return parts[-3:]


def fetch_category_metadata(session: requests.Session, aem_parts: list[str], timeout: int) -> dict[str, Any]:
    model_url = MODEL_URL_TEMPLATE.format(path="/".join(aem_parts))
    payload = fetch_json(session, model_url, timeout=timeout)
    if not isinstance(payload, dict):
        return {"Category_ID_number": "N/A", "Category_Title": "N/A", "Category_URL": "N/A"}
    return {
        "Category_ID_number": payload.get("categoryId", "N/A"),
        "Category_Title": payload.get("title", "N/A"),
        "Category_URL": payload.get("remoteSPAUrl", "N/A"),
    }


def build_catalog_url(category_key: str, page: int, page_size: int) -> str:
    return CATALOG_URL_TEMPLATE.format(category_key=category_key, page=page, page_size=page_size)


def extract_black_friday_flag(product: dict[str, Any]) -> bool:
    attributes = product.get("attributes", [])
    if not isinstance(attributes, list):
        return False
    for attr in attributes:
        values = attr.get("values", []) if isinstance(attr, dict) else []
        for value in values:
            text = str(value.get("value", "")) if isinstance(value, dict) else ""
            if "black friday" in text.lower():
                return True
    return False


def extract_prices(product: dict[str, Any]) -> tuple[Any, Any]:
    original_price: Any = "N/A"
    current_price: Any = "N/A"
    prices = product.get("price", [])
    if not isinstance(prices, list):
        return original_price, current_price

    for price in prices:
        if not isinstance(price, dict):
            continue
        usage = price.get("usage")
        value = price.get("value", "N/A")
        if usage == "Display":
            original_price = value
        elif usage == "Offer":
            current_price = value
    return original_price, current_price


def extract_seo_url(product: dict[str, Any]) -> str:
    user_data = product.get("UserData", [])
    if isinstance(user_data, list) and user_data and isinstance(user_data[0], dict):
        return str(user_data[0].get("seo_url", "N/A"))
    return "N/A"


def parse_product_entry(product: dict[str, Any], category_info: dict[str, Any]) -> dict[str, Any]:
    original_price, current_price = extract_prices(product)
    return {
        **category_info,
        "uniqueID": product.get("uniqueID", "N/A"),
        "singleSKUCatalogEntryID": product.get("singleSKUCatalogEntryID", "N/A"),
        "partNumber": product.get("partNumber", "N/A"),
        "shortDescription": product.get("shortDescription", "N/A"),
        "name": product.get("name", "N/A"),
        "manufacturer": product.get("manufacturer", "N/A"),
        "buyable": product.get("buyable", "N/A"),
        "Black_Friday_Campaign": extract_black_friday_flag(product),
        "seo_url": extract_seo_url(product),
        "Original_Price": original_price,
        "Current_Price": current_price,
    }


def build_product_summaries(products_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if products_df.empty:
        return (
            pd.DataFrame(columns=["Category_Title", "Products"]),
            pd.DataFrame(columns=["manufacturer", "Products"]),
        )

    category_summary = (
        products_df["Category_Title"].fillna("N/A").value_counts().rename_axis("Category_Title").reset_index(name="Products")
    )
    brand_summary = (
        products_df["manufacturer"].fillna("N/A").value_counts().rename_axis("manufacturer").reset_index(name="Products")
    )
    return category_summary, brand_summary


def write_markdown_summary(
    summary_file: Path,
    total_categories: int,
    products_df: pd.DataFrame,
    failed_categories: list[str],
    category_summary: pd.DataFrame,
    brand_summary: pd.DataFrame,
) -> None:
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Kotsovolos Catalog Summary",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Categories processed: {total_categories}",
        f"- Products captured: {len(products_df)}",
        f"- Failed categories: {len(failed_categories)}",
    ]
    if failed_categories:
        lines.append(f"- Failed list: {', '.join(failed_categories)}")

    lines.extend(["", "## Top Categories", "", "| Category | Products |", "|---|---:|"])
    for row in category_summary.head(15).itertuples(index=False):
        lines.append(f"| {row.Category_Title} | {row.Products} |")

    lines.extend(["", "## Top Brands", "", "| Brand | Products |", "|---|---:|"])
    for row in brand_summary.head(15).itertuples(index=False):
        lines.append(f"| {row.manufacturer} | {row.Products} |")

    summary_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logging.info("Saved markdown summary to %s", summary_file)


def save_products_output(
    records: list[dict[str, Any]],
    output_file: Path,
    summary_markdown: Path | None,
    total_categories: int,
    failed_categories: list[str],
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    products_df = pd.DataFrame(records)
    if not products_df.empty:
        dedupe_cols = [col for col in ["uniqueID", "partNumber", "Category_ID_number"] if col in products_df.columns]
        if dedupe_cols:
            products_df = products_df.drop_duplicates(subset=dedupe_cols)
    category_summary, brand_summary = build_product_summaries(products_df)

    if output_file.suffix.lower() == ".csv":
        products_df.to_csv(output_file, index=False)
        category_summary.to_csv(output_file.with_name(f"{output_file.stem}_category_summary.csv"), index=False)
        brand_summary.to_csv(output_file.with_name(f"{output_file.stem}_brand_summary.csv"), index=False)
    else:
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            products_df.to_excel(writer, sheet_name="products", index=False)
            category_summary.to_excel(writer, sheet_name="category_summary", index=False)
            brand_summary.to_excel(writer, sheet_name="brand_summary", index=False)

    logging.info("Saved product output (%s rows) to %s", len(products_df), output_file)

    if summary_markdown:
        write_markdown_summary(
            summary_file=summary_markdown,
            total_categories=total_categories,
            products_df=products_df,
            failed_categories=failed_categories,
            category_summary=category_summary,
            brand_summary=brand_summary,
        )


def scrape_products(
    session: requests.Session,
    categories_df: pd.DataFrame,
    output_file: Path,
    timeout: int,
    delay_seconds: float,
    page_size: int,
    max_pages_per_category: int | None,
    max_products: int | None,
    save_interval: int,
    summary_markdown: Path | None,
) -> int:
    records: list[dict[str, Any]] = []
    failed_categories: list[str] = []
    total_categories = len(categories_df)
    progress_file = output_file.with_name(f"{output_file.stem}_progress{output_file.suffix}")

    for idx, row in enumerate(categories_df.itertuples(index=False), start=1):
        row_dict = row._asdict()
        aem_url = str(row_dict.get("AEM_URL", "")).strip()
        title = str(row_dict.get("Title", "N/A"))
        unique_id = str(row_dict.get("UniqueID", "N/A"))
        logging.info("Category %s/%s: %s", idx, total_categories, title)

        aem_parts = parse_aem_parts(aem_url)
        if not aem_parts:
            failed_categories.append(title)
            logging.warning("Skipping category with invalid AEM_URL: %s", aem_url)
            continue

        category_meta = fetch_category_metadata(session, aem_parts=aem_parts, timeout=timeout)
        category_info = {
            "Category_Source_UniqueID": unique_id,
            "Category_Source_Title": title,
            "Category_AEM_URL": aem_url,
            **category_meta,
        }

        category_key = aem_parts[-1]
        page = 1
        saw_data = False

        while True:
            if max_pages_per_category and page > max_pages_per_category:
                break
            if max_products and len(records) >= max_products:
                break

            url = build_catalog_url(category_key=category_key, page=page, page_size=page_size)
            payload = fetch_json(session, url=url, timeout=timeout)
            if not isinstance(payload, dict):
                failed_categories.append(title)
                break

            entries = payload.get("catalogEntryView", [])
            if not isinstance(entries, list) or not entries:
                break

            saw_data = True
            for product in entries:
                if not isinstance(product, dict):
                    continue
                records.append(parse_product_entry(product=product, category_info=category_info))
                if max_products and len(records) >= max_products:
                    break

            if save_interval > 0 and len(records) > 0 and len(records) % save_interval == 0:
                save_products_output(
                    records=records,
                    output_file=progress_file,
                    summary_markdown=None,
                    total_categories=total_categories,
                    failed_categories=failed_categories,
                )

            page += 1
            if delay_seconds > 0:
                sleep(delay_seconds)

        if not saw_data:
            logging.info("No products returned for category: %s", title)

    save_products_output(
        records=records,
        output_file=output_file,
        summary_markdown=summary_markdown,
        total_categories=total_categories,
        failed_categories=failed_categories,
    )

    logging.info(
        "Done. Categories: %s | Products: %s | Failed categories: %s",
        total_categories,
        len(records),
        len(failed_categories),
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kotsovolos catalog pipeline: menu extraction + product scraping.")
    parser.add_argument("--mode", choices=["menu", "products", "all"], default="all", help="Pipeline mode.")
    parser.add_argument("--menu-file", type=Path, default=Path("output/menu_structure.xlsx"), help="Menu workbook path.")
    parser.add_argument(
        "--products-file",
        type=Path,
        default=Path("output/kotsovolos_products.xlsx"),
        help="Product output file (.xlsx/.csv).",
    )
    parser.add_argument(
        "--summary-markdown",
        type=str,
        default="output/kotsovolos_summary.md",
        help="Summary markdown path. Use 'none' to disable.",
    )
    parser.add_argument("--level", type=int, default=3, help="Category level to scrape from menu workbook.")
    parser.add_argument("--max-categories", type=int, default=None, help="Optional category limit.")
    parser.add_argument("--max-products", type=int, default=None, help="Optional total product limit.")
    parser.add_argument("--max-pages-per-category", type=int, default=None, help="Optional page limit per category.")
    parser.add_argument("--page-size", type=int, default=15, help="Page size for catalog API.")
    parser.add_argument("--delay-seconds", type=float, default=0.2, help="Delay between page requests.")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Retry attempts for transient failures.")
    parser.add_argument("--backoff-factor", type=float, default=0.8, help="Retry backoff factor.")
    parser.add_argument("--save-interval", type=int, default=500, help="Save progress every N products.")
    parser.add_argument("--log-level", type=str, default="INFO", help="Logging level.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logger(args.log_level)
    session = build_session(retries=args.retries, backoff_factor=args.backoff_factor)

    if args.mode in {"menu", "all"}:
        nav_payload = fetch_json(session=session, url=MENU_URL, timeout=args.timeout)
        if not isinstance(nav_payload, list):
            raise SystemExit("Failed to fetch menu payload.")
        menu_df = build_menu_dataframe(nav_payload)
        save_menu_workbook(menu_df=menu_df, menu_file=args.menu_file)

    if args.mode in {"products", "all"}:
        categories_df = load_categories_from_menu(
            menu_file=args.menu_file,
            level=args.level,
            max_categories=args.max_categories,
        )
        if categories_df.empty:
            raise SystemExit("No categories available to scrape.")

        summary_arg = (args.summary_markdown or "").strip()
        summary_md = None if summary_arg.lower() in {"", "none", "null"} else Path(summary_arg)

        exit_code = scrape_products(
            session=session,
            categories_df=categories_df,
            output_file=args.products_file,
            timeout=args.timeout,
            delay_seconds=args.delay_seconds,
            page_size=args.page_size,
            max_pages_per_category=args.max_pages_per_category,
            max_products=args.max_products,
            save_interval=args.save_interval,
            summary_markdown=summary_md,
        )
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
