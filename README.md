# Mortality & Life Expectancy Study

## 📌 Project Overview
This project analyzes U.S. mortality data from the Human Mortality Database (HMD), builds actuarial life tables, and visualizes life expectancy trends.  
It demonstrates **SQL**, **Microsoft Excel**, and **data interpretation** skills that are directly relevant to actuarial science.

---

## 🎯 Objectives
1. Store and process historical mortality data in a structured **SQL database**.
2. Calculate key actuarial metrics:
   - Mortality rates (mₓ)
   - Probability of death (qₓ)
   - Survivorship (lₓ)
   - Life expectancy (eₓ)
3. Build complete life tables in Excel.
4. Visualize mortality trends over time and across age groups.
5. Interpret findings in an actuarial and policy context.

---

## 📂 Project Structure

### **Phase 1 – Define Project Scope**
- Established project goals, deliverables, and methodology.

### **Phase 2 – Data Collection & Preparation**
- Source: **Human Mortality Database (HMD)** USA InputDB files.
- Extracted **Year**, **Age**, **Gender**, **Population**, **Deaths** from:
  - `USAdeath.txt`
  - `USApop.txt`
- Cleaned data:
  - Kept `AgeInterval=1` and `YearInterval=1`
  - Removed `UNK` and `TOT`
  - Aggregated across Lexis shapes
  - Selected best population record per year–age–gender using Type priority and earliest date.
- Script: `build_usa_year_age_gender_pop_deaths.py`

### **Phase 3 – SQL Database Setup and Queries**
- Imported cleaned CSV into **SQLite**.
- Created tables and views for:
  - Mortality rate (`mx`)
  - Estimated qₓ (`1 - exp(-mₓ)`)
  - Life expectancy at birth (`e₀`) by year/decade
  - Gender mortality comparisons
  - Age-group mortality trends
- Output CSVs:
  - `mortality_rates.csv`
  - `e0_by_decade.csv`
  - `gender_mortality_comparison.csv`
  - `agegroup_trends.csv`
- Script: `build_sqlite_and_queries.py`

### **Phase 4 – Excel Life Table Construction**
- Imported SQL outputs into Excel.
- Built dynamic life tables with columns:
  - Age, qₓ, pₓ, lₓ, dₓ, Lₓ, Tₓ, eₓ
- Added automated charts:
  - Mortality curve (Age vs. qₓ)
  - Survival curve (Age vs. lₓ)
  - Life expectancy trends (e₀ over time)
- Script: `build_excel_from_sql_outputs.py`
- File: `Mortality_LifeTables.xlsx`

### **Phase 5 – Actuarial Interpretation**
- Insights generated from processed datasets:
  1. **Gender differences in life expectancy** (`e0_by_decade.csv`, `gender_mortality_comparison.csv`)
  2. **Mortality trends for specific age groups** (`agegroup_trends.csv`)
  3. **Implications for insurance pricing, pension liabilities, and healthcare planning** (`e0_by_decade.csv`, `mortality_rates.csv`, `agegroup_trends.csv`)
  4. Additional insights:
     - Longevity risk trends
     - Survivorship curve shifts
     - Mortality improvement rates

---

## 🛠 Tools & Skills Used
- **SQL / SQLite** – data storage, querying, aggregation.
- **Python** – data cleaning, transformation, and automation scripts.
- **Microsoft Excel** – life table construction, formulas, and charting.
- **Actuarial Methods** – mortality and life expectancy calculations, longevity analysis.

---

## 📊 Key Files
- **Phase 2**: `usa_year_age_gender.csv`
- **Phase 3** Outputs:
  - `mortality_rates.csv`
  - `e0_by_decade.csv`
  - `gender_mortality_comparison.csv`
  - `agegroup_trends.csv`
- **Phase 4**: `Mortality_LifeTables.xlsx`
