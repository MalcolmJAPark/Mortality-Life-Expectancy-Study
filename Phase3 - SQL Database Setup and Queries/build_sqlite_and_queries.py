#!/usr/bin/env python3
"""
Create a SQLite DB from usa_year_age_gender.csv and run actuarial analyses.

Inputs:
  --csv     Path to cleaned CSV with columns: Year, Age, Gender, Population, Deaths

Outputs:
  --db      SQLite database file to create
  --outdir  Directory to write CSV exports:
              - mortality_rates.csv
              - e0_by_decade.csv
              - gender_mortality_comparison.csv
              - agegroup_trends.csv
"""

import argparse
import os
import sqlite3
import pandas as pd
from math import isnan

def ensure_dir(path: str):
    if path and not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def load_csv_to_sqlite(csv_path: str, db_path: str):
    df = pd.read_csv(csv_path)
    # Basic sanity check
    required = {"Year", "Age", "Gender", "Population", "Deaths"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    # Normalize dtypes
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").astype("Int64")
    df["Gender"] = df["Gender"].astype(str)
    df["Population"] = pd.to_numeric(df["Population"], errors="coerce")
    df["Deaths"] = pd.to_numeric(df["Deaths"], errors="coerce")

    # Drop rows without essentials
    df = df.dropna(subset=["Year", "Age", "Gender", "Population", "Deaths"])

    # Write to SQLite
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    try:
        df.to_sql("usa", con, if_exists="replace", index=False)
        cur = con.cursor()
        # Indexes for speed
        cur.execute("CREATE INDEX idx_usa_year_age_gender ON usa(Year, Age, Gender);")
        cur.execute("CREATE INDEX idx_usa_year ON usa(Year);")
        con.commit()
    finally:
        con.close()

def create_views_and_queries(db_path: str):
    con = sqlite3.connect(db_path)
    con.create_function("exp", 1, __import__("math").exp)  # for qx calc
    try:
        cur = con.cursor()

        # 1) Base rates view: mx and qx
        cur.executescript("""
        DROP VIEW IF EXISTS v_rates;
        CREATE VIEW v_rates AS
        SELECT
            Year,
            Age,
            Gender,
            Population,
            Deaths,
            CASE
              WHEN Population IS NULL OR Population = 0 THEN NULL
              ELSE 1.0 * Deaths / Population
            END AS mx,
            /* qx = 1 - exp(-mx); cap to [0,1] */
            CASE
              WHEN Population IS NULL OR Population = 0 THEN NULL
              WHEN 1.0 * Deaths / Population IS NULL THEN NULL
              ELSE
                CASE
                  WHEN 1.0 - exp(- (1.0 * Deaths / Population)) < 0 THEN 0.0
                  WHEN 1.0 - exp(- (1.0 * Deaths / Population)) > 1 THEN 1.0
                  ELSE 1.0 - exp(- (1.0 * Deaths / Population))
                END
            END AS qx
        FROM usa;
        """)

        # 2) Life table via recursive CTE per (Year, Gender); radix l0 = 100000
        # Lx ≈ l_{x+1} + 0.5 * d_x (ax = 0.5), Tx = sum_{y>=x} L_y, ex = Tx / l_x
        cur.executescript("""
        DROP VIEW IF EXISTS v_life_table;
        CREATE VIEW v_life_table AS
        WITH RECURSIVE
        base AS (
          SELECT Year, Gender, Age, mx, qx
          FROM v_rates
          WHERE Age IS NOT NULL
        ),
        ages AS (
          SELECT DISTINCT Year, Gender FROM base
        ),
        start AS (
          SELECT b.Year, b.Gender, 0 AS Age
          FROM ages b
        ),
        lt(Year, Gender, Age, qx, lx, dx, lx_next, Lx) AS (
          -- Anchor at age 0
          SELECT
            r.Year,
            r.Gender,
            0 AS Age,
            COALESCE((SELECT qx FROM base WHERE Year=r.Year AND Gender=r.Gender AND Age=0), 0.0) AS qx,
            100000.0 AS lx,
            100000.0 * COALESCE((SELECT qx FROM base WHERE Year=r.Year AND Gender=r.Gender AND Age=0), 0.0) AS dx,
            100000.0 * (1.0 - COALESCE((SELECT qx FROM base WHERE Year=r.Year AND Gender=r.Gender AND Age=0), 0.0)) AS lx_next,
            -- L0 ≈ l1 + 0.5*d0
            (100000.0 * (1.0 - COALESCE((SELECT qx FROM base WHERE Year=r.Year AND Gender=r.Gender AND Age=0), 0.0)))
              + 0.5 * (100000.0 * COALESCE((SELECT qx FROM base WHERE Year=r.Year AND Gender=r.Gender AND Age=0), 0.0)) AS Lx
          FROM start r
          UNION ALL
          -- Recurse age -> age+1, up to max age present for that Year/Gender
          SELECT
            lt.Year,
            lt.Gender,
            lt.Age + 1 AS Age,
            COALESCE((SELECT qx FROM base WHERE Year=lt.Year AND Gender=lt.Gender AND Age=lt.Age+1), 0.0) AS qx,
            lt.lx_next AS lx,
            lt.lx_next * COALESCE((SELECT qx FROM base WHERE Year=lt.Year AND Gender=lt.Gender AND Age=lt.Age+1), 0.0) AS dx,
            lt.lx_next * (1.0 - COALESCE((SELECT qx FROM base WHERE Year=lt.Year AND Gender=lt.Gender AND Age=lt.Age+1), 0.0)) AS lx_next,
            -- Lx ≈ l_{x+1} + 0.5*d_x
            (lt.lx_next * (1.0 - COALESCE((SELECT qx FROM base WHERE Year=lt.Year AND Gender=lt.Gender AND Age=lt.Age+1), 0.0)))
              + 0.5 * (lt.lx_next * COALESCE((SELECT qx FROM base WHERE Year=lt.Year AND Gender=lt.Gender AND Age=lt.Age+1), 0.0)) AS Lx
          FROM lt
          WHERE EXISTS (
            SELECT 1 FROM base b
            WHERE b.Year = lt.Year AND b.Gender = lt.Gender AND b.Age = lt.Age + 1
          )
        ),
        lt_with_T AS (
          SELECT
            Year, Gender, Age, qx, lx, dx, lx_next, Lx,
            SUM(Lx) OVER (PARTITION BY Year, Gender ORDER BY Age DESC
                          ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS Tx_desc  -- sum from max age down
          FROM lt
        )
        SELECT
          Year, Gender, Age, qx, lx, dx, lx_next, Lx,
          -- Tx at age x is cumulative sum of Lx from x to omega.
          SUM(Lx) OVER (PARTITION BY Year, Gender ORDER BY Age DESC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS Tx,
          CASE WHEN lx > 0 THEN
            (SUM(Lx) OVER (PARTITION BY Year, Gender ORDER BY Age DESC
                           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)) / lx
          ELSE NULL END AS ex
        FROM lt_with_T;
        """)

        # 3) e0 by year (age=0 rows), then average by decade
        cur.executescript("""
        DROP VIEW IF EXISTS v_e0_by_year;
        CREATE VIEW v_e0_by_year AS
        SELECT Year, Gender, ex AS e0
        FROM v_life_table
        WHERE Age = 0;

        DROP VIEW IF EXISTS v_e0_by_decade;
        CREATE VIEW v_e0_by_decade AS
        SELECT (Year/10)*10 AS Decade,
               Gender,
               AVG(e0) AS avg_e0
        FROM v_e0_by_year
        GROUP BY (Year/10)*10, Gender
        ORDER BY Decade, Gender;
        """)

        # 4) Gender-based mortality comparisons (mx by Year–Age, M vs F + difference)
        cur.executescript("""
        DROP VIEW IF EXISTS v_gender_mortality_comparison;
        CREATE VIEW v_gender_mortality_comparison AS
        SELECT
          rM.Year,
          rM.Age,
          rM.mx AS mx_male,
          rF.mx AS mx_female,
          (rM.mx - rF.mx) AS mx_diff
        FROM v_rates rM
        JOIN v_rates rF
          ON rM.Year = rF.Year AND rM.Age = rF.Age
         AND rM.Gender = 'Male' AND rF.Gender = 'Female'
        ORDER BY rM.Year, rM.Age;
        """)

        # 5) Trends over time for specific age groups (5-year bands): avg mx per year & age_group
        cur.executescript("""
        DROP VIEW IF EXISTS v_agegroup_trends;
        CREATE VIEW v_agegroup_trends AS
        SELECT
          Year,
          Gender,
          (Age/5)*5 AS AgeGroupStart,
          AVG(mx) AS avg_mx_5yr_band
        FROM v_rates
        GROUP BY Year, Gender, (Age/5)*5
        ORDER BY Year, Gender, AgeGroupStart;
        """)

        con.commit()
    finally:
        con.close()

def export_queries(db_path: str, outdir: str):
    ensure_dir(outdir)
    con = sqlite3.connect(db_path)
    try:
        # 1) Mortality rates (cleaned dataset for Excel)
        rates = pd.read_sql_query("""
            SELECT Year, Age, Gender, Population, Deaths,
                   mx AS MortalityRate, qx AS qx_est
            FROM v_rates
            ORDER BY Year, Age, Gender
        """, con)
        rates.to_csv(os.path.join(outdir, "mortality_rates.csv"), index=False)

        # 2) e0 by decade
        e0_dec = pd.read_sql_query("""
            SELECT Decade, Gender, ROUND(avg_e0, 3) AS avg_e0
            FROM v_e0_by_decade
        """, con)
        e0_dec.to_csv(os.path.join(outdir, "e0_by_decade.csv"), index=False)

        # 3) Gender-based mortality comparisons
        gender_cmp = pd.read_sql_query("""
            SELECT Year, Age,
                   mx_male, mx_female, (mx_male - mx_female) AS mx_diff
            FROM v_gender_mortality_comparison
        """, con)
        gender_cmp.to_csv(os.path.join(outdir, "gender_mortality_comparison.csv"), index=False)

        # 4) Trends over time for specific age groups (5-year bands)
        age_trends = pd.read_sql_query("""
            SELECT Year, Gender, AgeGroupStart, avg_mx_5yr_band
            FROM v_agegroup_trends
        """, con)
        age_trends.to_csv(os.path.join(outdir, "agegroup_trends.csv"), index=False)

    finally:
        con.close()

def main():
    ap = argparse.ArgumentParser(description="Build SQLite DB and actuarial queries from USA mortality CSV.")
    ap.add_argument("--csv", required=True, help="Path to usa_year_age_gender.csv")
    ap.add_argument("--db", required=True, help="Path to output SQLite DB (e.g., ./data/usa_mortality.sqlite)")
    ap.add_argument("--outdir", required=True, help="Directory to write CSV outputs")
    args = ap.parse_args()

    load_csv_to_sqlite(args.csv, args.db)
    create_views_and_queries(args.db)
    export_queries(args.db, args.outdir)
    print("Done. Wrote:")
    print(f"  DB: {args.db}")
    print(f"  Outputs in: {args.outdir}")
    print("  - mortality_rates.csv")
    print("  - e0_by_decade.csv")
    print("  - gender_mortality_comparison.csv")
    print("  - agegroup_trends.csv")

if __name__ == "__main__":
    main()
