#!/usr/bin/env python3
"""Build a Power BI-ready star schema from the Tim Hortons sales workbook.

The pipeline reads the ``SalesData`` worksheet, cleans the transaction data,
builds store/product/date dimensions, and writes four CSV files:

* FactSales.csv
* DimStore.csv
* DimProduct.csv
* DimDate.csv

Run with the defaults (the workbook is expected beside this script):

    py tim_hortons_etl.py

Or provide explicit locations:

    py tim_hortons_etl.py --input path/to/source.xlsx --output-dir path/to/output
"""

from __future__ import annotations

import argparse
import logging
import numbers
import sys
import tempfile
from datetime import date, datetime, time
from pathlib import Path
from typing import Final, Mapping

import numpy as np
import pandas as pd


LOGGER = logging.getLogger("tim_hortons_etl")

DEFAULT_WORKBOOK: Final = "Tim_Hortons_Portfolio_Dataset.xlsx"
DEFAULT_SHEET: Final = "SalesData"
DEFAULT_OUTPUT_DIR: Final = "power_bi_exports"

ROUND_COLUMNS: Final = ["UnitPrice", "Discount", "Revenue", "Cost", "Profit"]

REQUIRED_COLUMNS: Final = [
    "OrderID",
    "OrderDate",
    "OrderTime",
    "Hour",
    "Store",
    "City",
    "Category",
    "Product",
    "Size",
    "Quantity",
    "UnitPrice",
    "Discount",
    "Revenue",
    "Cost",
    "Profit",
    "PaymentMethod",
    "CustomerType",
]

FACT_COLUMNS: Final = [
    "OrderID",
    "OrderDate",
    "OrderTime",
    "Hour",
    "StoreID",
    "ProductID",
    "Quantity",
    "UnitPrice",
    "Discount",
    "Revenue",
    "Cost",
    "Profit",
    "PaymentMethod",
    "CustomerType",
]


class ETLValidationError(ValueError):
    """Raised when source data cannot safely be transformed."""


def _sample_bad_rows(mask: pd.Series, limit: int = 5) -> str:
    """Return one-based Excel row numbers for a failed validation mask."""

    # Data starts on Excel row 2 because row 1 contains column headings.
    rows = [str(int(index) + 2) for index in mask[mask].index[:limit]]
    return ", ".join(rows)


def _parse_date_value(value: object) -> pd.Timestamp | pd.NaT:
    """Parse one date, including Excel serial dates, and remove any time part."""

    if pd.isna(value):
        return pd.NaT

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(value).normalize()

    # Excel stores dates as days from 1899-12-30. Exclude booleans because
    # bool is a subclass of int in Python.
    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        try:
            return (
                pd.Timestamp("1899-12-30")
                + pd.to_timedelta(float(value), unit="D")
            ).normalize()
        except (OverflowError, TypeError, ValueError):
            return pd.NaT

    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    return pd.NaT if pd.isna(parsed) else pd.Timestamp(parsed).normalize()


def _parse_time_value(value: object) -> time | None:
    """Parse one time value, including an Excel fractional-day time."""

    if pd.isna(value):
        return None

    if isinstance(value, datetime):
        return value.time().replace(microsecond=0)
    if isinstance(value, pd.Timestamp):
        return value.time().replace(microsecond=0)
    if isinstance(value, time):
        return value.replace(microsecond=0)
    if isinstance(value, pd.Timedelta):
        total_seconds = int(round(value.total_seconds())) % 86_400
        return time(
            hour=total_seconds // 3_600,
            minute=(total_seconds % 3_600) // 60,
            second=total_seconds % 60,
        )

    if isinstance(value, numbers.Real) and not isinstance(value, bool):
        numeric_value = float(value)
        if not np.isfinite(numeric_value) or not 0 <= numeric_value <= 1:
            return None
        total_seconds = int(round(numeric_value * 86_400)) % 86_400
        return time(
            hour=total_seconds // 3_600,
            minute=(total_seconds % 3_600) // 60,
            second=total_seconds % 60,
        )

    parsed = pd.to_datetime(str(value).strip(), errors="coerce")
    if pd.isna(parsed):
        return None
    return pd.Timestamp(parsed).time().replace(microsecond=0)


def _clean_required_text(df: pd.DataFrame, columns: list[str]) -> None:
    """Trim required text fields and reject null or blank values in place."""

    for column in columns:
        cleaned = df[column].astype("string").str.strip()
        invalid = cleaned.isna() | cleaned.eq("")
        if invalid.any():
            raise ETLValidationError(
                f"Column {column!r} has blank values at Excel row(s): "
                f"{_sample_bad_rows(invalid)}"
            )
        df[column] = cleaned


def _clean_integer_column(
    df: pd.DataFrame,
    column: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> None:
    """Coerce a required whole-number column and enforce optional bounds."""

    numeric = pd.to_numeric(df[column], errors="coerce")
    invalid = numeric.isna() | numeric.mod(1).ne(0)
    if minimum is not None:
        invalid |= numeric.lt(minimum)
    if maximum is not None:
        invalid |= numeric.gt(maximum)
    if invalid.any():
        raise ETLValidationError(
            f"Column {column!r} has invalid whole numbers at Excel row(s): "
            f"{_sample_bad_rows(invalid)}"
        )
    df[column] = numeric.astype("int64")


def load_sales_data(input_path: Path, sheet_name: str = DEFAULT_SHEET) -> pd.DataFrame:
    """Load and validate the required source worksheet."""

    if not input_path.is_file():
        raise FileNotFoundError(f"Input workbook not found: {input_path}")

    LOGGER.info("Loading worksheet %s from %s", sheet_name, input_path)
    try:
        df = pd.read_excel(input_path, sheet_name=sheet_name, engine="openpyxl")
    except ValueError as exc:
        raise ETLValidationError(
            f"Could not load worksheet {sheet_name!r} from {input_path}: {exc}"
        ) from exc

    df.columns = [str(column).strip() for column in df.columns]
    duplicated_columns = df.columns[df.columns.duplicated()].tolist()
    if duplicated_columns:
        raise ETLValidationError(
            f"Source contains duplicate column names: {duplicated_columns}"
        )

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ETLValidationError(f"Source is missing required columns: {missing}")
    if df.empty:
        raise ETLValidationError("The source worksheet contains no transaction rows.")

    LOGGER.info("Loaded %s transaction rows", f"{len(df):,}")
    return df


def clean_sales_data(source: pd.DataFrame) -> pd.DataFrame:
    """Clean dates, times, numbers, and business-key text fields."""

    df = source.copy()

    parsed_dates = df["OrderDate"].map(_parse_date_value)
    invalid_dates = parsed_dates.isna()
    if invalid_dates.any():
        raise ETLValidationError(
            "Column 'OrderDate' has invalid dates at Excel row(s): "
            f"{_sample_bad_rows(invalid_dates)}"
        )
    df["_ParsedOrderDate"] = pd.to_datetime(parsed_dates)
    df["OrderDate"] = df["_ParsedOrderDate"].dt.strftime("%Y-%m-%d")

    parsed_times = df["OrderTime"].map(_parse_time_value)
    invalid_times = parsed_times.isna()
    if invalid_times.any():
        raise ETLValidationError(
            "Column 'OrderTime' has invalid times at Excel row(s): "
            f"{_sample_bad_rows(invalid_times)}"
        )
    standardized_times = parsed_times.map(lambda value: value.strftime("%H:%M:%S"))
    derived_hours = parsed_times.map(lambda value: value.hour).astype("int64")

    # Keep Hour aligned with the standardized OrderTime. Source inconsistencies
    # are reported and repaired because Hour is a derived transaction attribute.
    source_hours = pd.to_numeric(df["Hour"], errors="coerce")
    hour_mismatches = source_hours.isna() | source_hours.ne(derived_hours)
    if hour_mismatches.any():
        LOGGER.warning(
            "Replaced Hour with the value derived from OrderTime for %s row(s)",
            f"{int(hour_mismatches.sum()):,}",
        )
    df["OrderTime"] = standardized_times
    df["Hour"] = derived_hours

    _clean_integer_column(df, "Quantity", minimum=0)
    if df["OrderID"].isna().any():
        invalid_order_ids = df["OrderID"].isna()
        raise ETLValidationError(
            "Column 'OrderID' has missing values at Excel row(s): "
            f"{_sample_bad_rows(invalid_order_ids)}"
        )

    for column in ROUND_COLUMNS:
        numeric = pd.to_numeric(df[column], errors="coerce")
        invalid = numeric.isna()
        if invalid.any():
            raise ETLValidationError(
                f"Column {column!r} has invalid numeric values at Excel row(s): "
                f"{_sample_bad_rows(invalid)}"
            )
        df[column] = numeric.round(2)

    _clean_required_text(
        df,
        [
            "Store",
            "City",
            "Product",
            "Category",
            "Size",
            "PaymentMethod",
            "CustomerType",
        ],
    )

    return df


def build_star_schema(cleaned: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build deterministic dimensions and a referentially intact fact table."""

    dim_store = (
        cleaned[["Store", "City"]]
        .drop_duplicates()
        .sort_values(["Store", "City"], kind="stable")
        .reset_index(drop=True)
    )
    dim_store.insert(
        0,
        "StoreID",
        [f"STR_{sequence:03d}" for sequence in range(1, len(dim_store) + 1)],
    )

    dim_product = (
        cleaned[["Product", "Category", "Size"]]
        .drop_duplicates()
        .sort_values(["Product", "Category", "Size"], kind="stable")
        .reset_index(drop=True)
    )
    dim_product.insert(
        0,
        "ProductID",
        [f"PRD_{sequence:04d}" for sequence in range(1, len(dim_product) + 1)],
    )

    unique_dates = (
        cleaned["_ParsedOrderDate"]
        .drop_duplicates()
        .sort_values(kind="stable")
        .reset_index(drop=True)
    )
    dim_date = pd.DataFrame({"_ParsedOrderDate": unique_dates})
    dim_date["OrderDate"] = dim_date["_ParsedOrderDate"].dt.strftime("%Y-%m-%d")
    dim_date["Year"] = dim_date["_ParsedOrderDate"].dt.year.astype("int64")
    dim_date["Quarter"] = dim_date["_ParsedOrderDate"].dt.quarter.astype("int64")
    dim_date["Month"] = dim_date["_ParsedOrderDate"].dt.strftime("%b")
    dim_date["Day"] = dim_date["_ParsedOrderDate"].dt.day.astype("int64")
    dim_date["DayName"] = dim_date["_ParsedOrderDate"].dt.day_name()
    dim_date = dim_date[["OrderDate", "Year", "Quarter", "Month", "Day", "DayName"]]

    fact_sales = cleaned.merge(
        dim_store,
        on=["Store", "City"],
        how="left",
        validate="many_to_one",
        sort=False,
    ).merge(
        dim_product,
        on=["Product", "Category", "Size"],
        how="left",
        validate="many_to_one",
        sort=False,
    )
    fact_sales = fact_sales[FACT_COLUMNS]

    if len(fact_sales) != len(cleaned):
        raise ETLValidationError(
            "FactSales row count changed while mapping dimension keys."
        )
    for foreign_key in ("StoreID", "ProductID"):
        if fact_sales[foreign_key].isna().any():
            raise ETLValidationError(
                f"FactSales contains unmapped values for foreign key {foreign_key}."
            )

    if not dim_store["StoreID"].is_unique:
        raise ETLValidationError("DimStore primary keys are not unique.")
    if not dim_product["ProductID"].is_unique:
        raise ETLValidationError("DimProduct primary keys are not unique.")
    if not dim_date["OrderDate"].is_unique:
        raise ETLValidationError("DimDate OrderDate values are not unique.")

    return {
        "FactSales.csv": fact_sales,
        "DimStore.csv": dim_store,
        "DimProduct.csv": dim_product,
        "DimDate.csv": dim_date,
    }


def export_csvs(tables: Mapping[str, pd.DataFrame], output_dir: Path) -> None:
    """Write each table via a temporary file, then atomically replace its CSV."""

    output_dir.mkdir(parents=True, exist_ok=True)
    staged_files: list[tuple[Path, Path]] = []

    try:
        for filename, table in tables.items():
            destination = output_dir / filename
            with tempfile.NamedTemporaryFile(
                mode="w",
                prefix=f".{destination.stem}_",
                suffix=".tmp",
                dir=output_dir,
                encoding="utf-8-sig",
                newline="",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                table.to_csv(
                    temporary_file,
                    index=False,
                    float_format="%.2f",
                    lineterminator="\n",
                )
            staged_files.append((temporary_path, destination))

        for temporary_path, destination in staged_files:
            temporary_path.replace(destination)
            LOGGER.info(
                "Exported %-14s (%s rows)",
                destination.name,
                f"{len(tables[destination.name]):,}",
            )
    finally:
        for temporary_path, _ in staged_files:
            temporary_path.unlink(missing_ok=True)


def run_pipeline(input_path: Path, output_dir: Path, sheet_name: str) -> dict[str, pd.DataFrame]:
    """Run the complete ETL pipeline and return the exported tables."""

    source = load_sales_data(input_path, sheet_name)
    cleaned = clean_sales_data(source)
    tables = build_star_schema(cleaned)
    export_csvs(tables, output_dir)
    LOGGER.info("ETL completed successfully; output directory: %s", output_dir.resolve())
    return tables


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Create Power BI-ready Tim Hortons fact and dimension CSVs."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / DEFAULT_WORKBOOK,
        help=f"Source Excel workbook (default: {DEFAULT_WORKBOOK} beside this script).",
    )
    parser.add_argument(
        "--sheet",
        default=DEFAULT_SHEET,
        help=f"Source worksheet name (default: {DEFAULT_SHEET}).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=script_dir / DEFAULT_OUTPUT_DIR,
        help=f"CSV output directory (default: {DEFAULT_OUTPUT_DIR} beside this script).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include debug-level log messages.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        run_pipeline(args.input.resolve(), args.output_dir.resolve(), args.sheet)
    except (ETLValidationError, FileNotFoundError, ImportError, OSError) as exc:
        LOGGER.error("ETL failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
