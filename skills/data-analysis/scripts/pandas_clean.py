"""
Safe snippet for basic pandas cleaning. Copy and adapt for your dataset.
Run: python pandas_clean.py [path/to/data.csv]  (ensure pandas is installed)
"""
import sys
from pathlib import Path

import pandas as pd

INPUT_DEFAULT = "data.csv"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(axis=1, how="all")
    print("df_shape_after_drop_all_null_cols", df.shape)

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    print("df_columns", list(df.columns))

    before = len(df)
    df = df.drop_duplicates()
    print("rows_dropped_duplicates", before - len(df))

    print("df_head", df.head())
    return df


def main() -> int:
    input_path = Path(sys.argv[1] if len(sys.argv) > 1 else INPUT_DEFAULT)

    if not input_path.is_file():
        print(f"Error: could not read {input_path.name} — file not found.", file=sys.stderr)
        return 1

    try:
        df = pd.read_csv(input_path)
    except pd.errors.EmptyDataError:
        print(f"Error: {input_path.name} is empty or has no valid data.", file=sys.stderr)
        return 1
    except pd.errors.ParserError:
        print(
            f"Error: could not parse {input_path.name} — the file does not appear to be valid CSV.",
            file=sys.stderr,
        )
        return 1
    except OSError:
        print(f"Error: could not read {input_path.name}.", file=sys.stderr)
        return 1

    if df.empty:
        print(f"Error: {input_path.name} is empty or has no valid data.", file=sys.stderr)
        return 1

    print("df_shape", df.shape)
    print("df_dtypes", df.dtypes)
    clean_dataframe(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
