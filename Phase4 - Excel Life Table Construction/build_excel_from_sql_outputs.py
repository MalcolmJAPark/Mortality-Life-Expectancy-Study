#!/usr/bin/env python3
"""
Build an Excel workbook from SQL outputs:
1) Imports CSVs exported from SQLite:
   - mortality_rates.csv  (Year, Age, Gender, Population, Deaths, MortalityRate, qx_est)
   - e0_by_year.csv       (Year, Gender, e0)  [optional but recommended]

2) Creates an Excel file with:
   - Sheet 'Rates' (all rows from mortality_rates.csv)
   - Sheet 'LifeTable' for a chosen Year & Gender, with Excel formulas:
       Age, q_x, p_x=1-q_x, l_x, d_x, L_x, T_x, e_x = T_x / l_x
   - Sheet 'E0_Trend' (optional) + chart of life expectancy over time
   - Charts sheet containing:
       * Mortality curve (Age vs q_x)
       * Survival curve (Age vs l_x)
       * Life expectancy trend (Year vs e0), if e0_by_year provided
"""
import argparse
import os
import pandas as pd

def main():
    ap = argparse.ArgumentParser(description="Build Excel workbook from SQL output CSVs.")
    ap.add_argument("--rates_csv", required=True, help="Path to mortality_rates.csv")
    ap.add_argument("--e0_csv", default=None, help="Optional path to e0_by_year.csv")
    ap.add_argument("--year", type=int, default=None, help="Year to build the life table for (default: latest in data)")
    ap.add_argument("--gender", default="Male", choices=["Male", "Female"], help="Gender for the life table")
    ap.add_argument("--out_xlsx", required=True, help="Output Excel path, e.g. ./excel/Mortality_LifeTables.xlsx")
    args = ap.parse_args()

    # --- Load rates CSV ---
    rates = pd.read_csv(args.rates_csv)
    # Normalize expected columns
    # Use qx_est if present; else compute from MortalityRate (mx)
    if "qx_est" in rates.columns:
        rates["qx"] = rates["qx_est"]
    elif "MortalityRate" in rates.columns:
        # qx ≈ 1 - exp(-mx); but we’ll leave mx as-is and compute qx in Excel if missing
        rates["qx"] = rates["MortalityRate"].map(lambda x: None if pd.isna(x) else 1 - pow(2.718281828, -x))
    else:
        raise ValueError("Input must contain either column 'qx_est' or 'MortalityRate' to derive qx.")

    # Choose default year if not provided
    if args.year is None:
        args.year = int(rates["Year"].max())

    # Filter for life table slice (Year, Gender)
    lt_source = rates[(rates["Year"] == args.year) & (rates["Gender"] == args.gender)].copy()
    if lt_source.empty:
        raise ValueError(f"No rows found for Year={args.year}, Gender={args.gender}")

    # Keep only ages that are integers and sort
    lt_source = lt_source[pd.to_numeric(lt_source["Age"], errors="coerce").notna()]
    lt_source["Age"] = lt_source["Age"].astype(int)
    lt_source = lt_source.sort_values("Age")

    # Build a minimal frame for writing to LifeTable (Age & qx values only; formulas will fill the rest)
    life_table = pd.DataFrame({
        "Age": lt_source["Age"].values,
        "q_x": lt_source["qx"].values
    })

    # Optional e0 trend
    e0_df = None
    if args.e0_csv and os.path.exists(args.e0_csv):
        e0_df = pd.read_csv(args.e0_csv)
        # Normalize possible column names
        # Expect: Year, Gender, e0  (or Year, Gender, avg_e0 from decade file — both okay)
        if "e0" not in e0_df.columns and "avg_e0" in e0_df.columns:
            e0_df = e0_df.rename(columns={"avg_e0": "e0"})
        if not {"Year", "Gender", "e0"}.issubset(e0_df.columns):
            # It might be a decade-level file; skip if not Year-based
            e0_df = None

    # --- Write Excel ---
    os.makedirs(os.path.dirname(args.out_xlsx) or ".", exist_ok=True)
    with pd.ExcelWriter(args.out_xlsx, engine="xlsxwriter") as writer:
        # Sheet 1: full rates
        rates.to_excel(writer, sheet_name="Rates", index=False)

        # Sheet 2: LifeTable (write Age, q_x; formulas next)
        life_table.to_excel(writer, sheet_name="LifeTable", index=False)
        wb  = writer.book
        ws  = writer.sheets["LifeTable"]

        # Header row is row 0; data starts row 1 in xlsxwriter coordinates
        n = len(life_table)                 # number of ages
        start_row = 1
        last_row  = start_row + n - 1

        # Add remaining headers
        headers = ["Age", "q_x", "p_x", "l_x", "d_x", "L_x", "T_x", "e_x"]
        for col_idx, name in enumerate(headers):
            ws.write(0, col_idx, name)

        # Fill p_x, l_x, d_x, L_x, T_x, e_x formulas
        # Columns: A Age, B qx, C px, D lx, E dx, F Lx, G Tx, H ex
        # Parameters
        radix = 100000  # l0
        # Row addresses are 1-based in Excel, so add +1 to 0-based indices
        for i in range(n):
            row = start_row + i
            # p_x = 1 - q_x
            ws.write_formula(row, 2, f"=1-B{row+1}")
            if i == 0:
                # l_0 = 100000
                ws.write_number(row, 3, radix)
            else:
                # l_x = l_{x-1} - d_{x-1}
                ws.write_formula(row, 3, f"=D{row} - E{row}")
            # d_x = l_x * q_x
            ws.write_formula(row, 4, f"=D{row+1}*B{row+1}")
            # L_x = l_x - 0.5 * d_x   (ax = 0.5)
            ws.write_formula(row, 5, f"=D{row+1}-0.5*E{row+1}")

        # T_x: sum of L_x from current row to last_row
        for i in range(n):
            row = start_row + i
            ws.write_formula(row, 6, f"=SUM(F{row+1}:F{last_row+1})")
            # e_x = T_x / l_x
            ws.write_formula(row, 7, f"=IF(D{row+1}>0, G{row+1}/D{row+1}, NA())")

        # Sheet 3: E0_Trend (optional)
        if e0_df is not None and not e0_df.empty:
            e0_df.to_excel(writer, sheet_name="E0_Trend", index=False)

        # --- Charts sheet ---
        charts = wb.add_worksheet("Charts")

        # Mortality curve (Age vs q_x)
        mort_chart = wb.add_chart({"type": "line"})
        mort_chart.add_series({
            "name":       f"Mortality qx ({args.year}, {args.gender})",
            "categories": ["LifeTable", start_row, 0, last_row, 0],  # Age
            "values":     ["LifeTable", start_row, 1, last_row, 1],  # q_x
        })
        mort_chart.set_title({"name": "Mortality Curve (Age vs q_x)"})
        mort_chart.set_x_axis({"name": "Age"})
        mort_chart.set_y_axis({"name": "q_x"})
        charts.insert_chart("A2", mort_chart, {"x_scale": 1.2, "y_scale": 1.2})

        # Survival curve (Age vs l_x)
        surv_chart = wb.add_chart({"type": "line"})
        surv_chart.add_series({
            "name":       f"Survival l_x ({args.year}, {args.gender})",
            "categories": ["LifeTable", start_row, 0, last_row, 0],  # Age
            "values":     ["LifeTable", start_row, 3, last_row, 3],  # l_x
        })
        surv_chart.set_title({"name": "Survival Curve (Age vs l_x)"})
        surv_chart.set_x_axis({"name": "Age"})
        surv_chart.set_y_axis({"name": "l_x"})
        charts.insert_chart("A20", surv_chart, {"x_scale": 1.2, "y_scale": 1.2})

        # Life expectancy trends over years (if e0 available)
        if e0_df is not None and not e0_df.empty:
            # Build a line series per gender present
            e0_sheet = "E0_Trend"
            e0_gender_groups = sorted(e0_df["Gender"].dropna().unique().tolist())
            e0_chart = wb.add_chart({"type": "line"})
            for g in e0_gender_groups:
                sub = e0_df[e0_df["Gender"] == g]
                if sub.empty:
                    continue
                first_row = 1 + sub.index.min()  # Excel row index (header is row 0)
                last_row2 = 1 + sub.index.max()
                # To avoid discontiguous ranges, we’ll reference whole columns with categories/values filtered by Gender using helper columns.
                # Simpler: write a pivoted temp table for charting.
            # Simpler approach: pivot in-memory and write for chart
            pivot = e0_df.pivot_table(index="Year", columns="Gender", values="e0", aggfunc="mean").reset_index()
            pivot.to_excel(writer, sheet_name="E0_Trend_Pivot", index=False)
            # Ranges
            year_rows = len(pivot)
            categories = ["E0_Trend_Pivot", 1, 0, year_rows, 0]  # Year col
            for j, g in enumerate(pivot.columns[1:], start=1):
                e0_chart.add_series({
                    "name":       g,
                    "categories": categories,
                    "values":     ["E0_Trend_Pivot", 1, j, year_rows, j],
                })
            e0_chart.set_title({"name": "Life Expectancy (e0) Trend"})
            e0_chart.set_x_axis({"name": "Year"})
            e0_chart.set_y_axis({"name": "e0 (years)"})
            charts.insert_chart("A38", e0_chart, {"x_scale": 1.2, "y_scale": 1.2})

    print(f"Done. Wrote Excel to: {args.out_xlsx}")
    print(f"Life table built for Year={args.year}, Gender={args.gender} (l0=100000, a_x=0.5).")

if __name__ == "__main__":
    main()
