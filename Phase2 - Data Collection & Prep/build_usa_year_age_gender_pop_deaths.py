#!/usr/bin/env python3
"""
Build a tidy Year–Age–Gender table for USA from HMD InputDB.

Inputs (inside --input directory):
  - USAdeath.txt
  - USApop.txt

Output:
  - CSV with columns: Year, Age, Gender, Population, Deaths
"""

import argparse
import os
import sys
import pandas as pd
from typing import Tuple

# ---------------------------------------
# Helpers
# ---------------------------------------
SEX_MAP = {"m": "Male", "f": "Female"}  # 'b' (both) excluded for per-sex table

# Priority for Population Type (best first).
# HMD uses: C=census, O=official estimates, R=register counts, E=other estimates, B=by birth year.
# In practice, many series use E or O around Jan 1; prefer E/O/C/R over B (age by birth-year).
POP_TYPE_PRIORITY = {"E": 1, "O": 2, "C": 3, "R": 4, "B": 9}

def coerce_int(s):
    try:
        return int(s)
    except Exception:
        return None

def is_numeric_age(a: str) -> bool:
    """Accept only numeric ages like '0','1',...; exclude 'UNK','TOT','100+' etc."""
    if a is None:
        return False
    a = str(a).strip()
    return a.isdigit()

def read_csv_loose(path: str) -> pd.DataFrame:
    """
    Read HMD InputDB text files:
      - Comma-delimited with possible spaces
      - Missing values as '.'
      - Preserve headers exactly as spec
    """
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=["."],
        skipinitialspace=True
    )

# ---------------------------------------
# Load & clean deaths
# ---------------------------------------
def load_deaths(death_path: str) -> pd.DataFrame:
    d = read_csv_loose(death_path)
    d.columns = [c.strip() for c in d.columns]

    required = {"Year", "YearInterval", "Sex", "Age", "AgeInterval", "Deaths"}
    missing = required - set(d.columns)
    if missing:
        raise ValueError(f"Missing columns in deaths file: {missing}")

    # normalize + filter
    d["sex"] = d["Sex"].astype(str).str.strip().str.lower()
    d = d[(d["YearInterval"].astype(str).str.strip() == "1") &
          (d["AgeInterval"].astype(str).str.strip() == "1")]
    d = d[d["sex"].isin(["m", "f"])]
    d = d[d["Age"].apply(is_numeric_age)].copy()

    # types
    d["Year"] = d["Year"].apply(coerce_int)
    d["Age"] = d["Age"].apply(coerce_int)
    d["Deaths"] = pd.to_numeric(d["Deaths"], errors="coerce")
    d = d.dropna(subset=["Year", "Age", "Deaths"])

    # aggregate across Lexis shapes
    g = (d.groupby(["Year", "Age", "sex"], as_index=False)["Deaths"].sum())
    return g


# ---------------------------------------
# Load & clean population
# ---------------------------------------
def load_population(pop_path: str) -> pd.DataFrame:
    p = read_csv_loose(pop_path)
    p.columns = [c.strip() for c in p.columns]

    required = {"Year", "Sex", "Age", "AgeInterval", "Population", "Type", "Day", "Month"}
    missing = required - set(p.columns)
    if missing:
        raise ValueError(f"Missing columns in population file: {missing}")

    # normalize + filter
    p["sex"] = p["Sex"].astype(str).str.strip().str.lower()
    p = p[p["AgeInterval"].astype(str).str.strip() == "1"]
    p = p[p["sex"].isin(["m", "f"])]
    p = p[p["Age"].apply(is_numeric_age)].copy()

    # types
    p["Year"] = p["Year"].apply(coerce_int)
    p["Age"] = p["Age"].apply(coerce_int)
    p["Population"] = pd.to_numeric(p["Population"], errors="coerce")
    p["Day_i"] = pd.to_numeric(p["Day"], errors="coerce")
    p["Month_i"] = pd.to_numeric(p["Month"], errors="coerce")

    POP_TYPE_PRIORITY = {"E": 1, "O": 2, "C": 3, "R": 4, "B": 9}
    p["type_rank"] = p["Type"].map(POP_TYPE_PRIORITY).fillna(99).astype(int)

    p = p.dropna(subset=["Year", "Age", "Population"])

    # choose best record per Year–Age–sex
    p = (p.sort_values(["Year", "Age", "sex", "type_rank", "Month_i", "Day_i"])
           .groupby(["Year", "Age", "sex"], as_index=False)
           .first())

    return p[["Year", "Age", "sex", "Population"]]


# ---------------------------------------
# Build final table
# ---------------------------------------
def build_table(death_path: str, pop_path: str) -> pd.DataFrame:
    deaths = load_deaths(death_path)
    pop = load_population(pop_path)

    df = pd.merge(
        pop, deaths,
        on=["Year", "Age", "sex"],
        how="inner",
        validate="one_to_one"
    )

    # Map sex to Gender labels
    df["Gender"] = df["sex"].map(SEX_MAP)

    # Final columns & sort
    out = df[["Year", "Age", "Gender", "Population", "Deaths"]].sort_values(
        ["Year", "Age", "Gender"]
    )
    return out.reset_index(drop=True)

# ---------------------------------------
# CLI
# ---------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build USA Year–Age–Gender Population & Deaths table from HMD InputDB.")
    parser.add_argument("--input", required=True, help="Path to InputDB directory (contains USAdeath.txt, USApop.txt)")
    parser.add_argument("--out", required=True, help="Output CSV path")
    args = parser.parse_args(argv)

    death_path = os.path.join(args.input, "USAdeath.txt")
    pop_path = os.path.join(args.input, "USApop.txt")

    if not os.path.isfile(death_path):
        print(f"ERROR: not found: {death_path}", file=sys.stderr)
        return 2
    if not os.path.isfile(pop_path):
        print(f"ERROR: not found: {pop_path}", file=sys.stderr)
        return 2

    df = build_table(death_path, pop_path)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df):,} rows to {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
