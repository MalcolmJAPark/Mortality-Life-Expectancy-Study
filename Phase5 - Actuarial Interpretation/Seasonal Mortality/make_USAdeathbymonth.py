import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from calendar import monthrange

def is_leap(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

def month_day_weights(year: int) -> pd.Series:
    days = [monthrange(year, m)[1] for m in range(1, 13)]
    s = pd.Series(days, index=range(1, 13), dtype=float)
    return s / s.sum()

def main():
    ap = argparse.ArgumentParser(description="Build USAdeathbymonth.txt from USAdeath.txt")
    ap.add_argument("input", help="Path to USAdeath.txt (CSV-formatted)")
    ap.add_argument("-o", "--output", default="USAdeathbymonth.txt", help="Output path")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"ERROR: Input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    # Read input (comma-separated)
    try:
        df = pd.read_csv(in_path, dtype=str)
    except Exception:
        # Try tab-separated as fallback
        df = pd.read_csv(in_path, sep="\t", dtype=str)

    # Normalize column names (strip spaces)
    df.columns = [c.strip() for c in df.columns]

    # Coerce Deaths to numeric, non-numeric -> NaN -> 0
    if "Deaths" not in df.columns:
        print("ERROR: 'Deaths' column not found in input.", file=sys.stderr)
        sys.exit(1)
    df["Deaths"] = pd.to_numeric(df["Deaths"], errors="coerce").fillna(0).astype(float)

    # Choose id columns if present
    pop_cols = [c for c in ["PopName", "Area"] if c in df.columns]
    # Get Year column
    year_col = "Year"
    if year_col not in df.columns:
        print("ERROR: 'Year' column not found in input.", file=sys.stderr)
        sys.exit(1)

    # If Month exists, aggregate by Year+Month (and PopName/Area if available)
    if "Month" in df.columns:
        df["Month"] = pd.to_numeric(df["Month"], errors="coerce")
        d = df.dropna(subset=["Month"]).copy()
        d["Month"] = d["Month"].astype(int)
        group_cols = pop_cols + [year_col, "Month"]
        out = d.groupby(group_cols, as_index=False)["Deaths"].sum()
    else:
        # No Month: sum annual total deaths then distribute across months by day weights
        # Sum across all other dimensions (sex, age, etc.), keeping PopName/Area if present
        group_cols = pop_cols + [year_col]
        annual = df.groupby(group_cols, as_index=False)["Deaths"].sum()

        rows = []
        for _, row in annual.iterrows():
            year = int(row[year_col])
            total = float(row["Deaths"])
            weights = month_day_weights(year)
            for m, w in weights.items():
                rows.append({**{c: row[c] for c in pop_cols}, year_col: year, "Month": m, "Deaths": total * w})
        out = pd.DataFrame(rows, columns=pop_cols + [year_col, "Month", "Deaths"])

    # Sort and round Deaths to nearest integer for reporting (keep a raw column if desired)
    out = out.sort_values(pop_cols + [year_col, "Month"] if pop_cols else [year_col, "Month"]).reset_index(drop=True)
    out["Deaths"] = out["Deaths"].round().astype(int)

    # Write output
    out_path = Path(args.output)
    out.to_csv(out_path, index=False)
    print(f"Wrote {out_path} with {len(out):,} rows.")

if __name__ == "__main__":
    main()
