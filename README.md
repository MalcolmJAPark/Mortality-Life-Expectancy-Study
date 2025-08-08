# Mortality-Life-Expectancy-Study

## 📌 Project Overview
This project analyzes mortality data to build **life tables**, calculate **life expectancy**, and visualize mortality trends over time.  
It showcases skills in **SQL** for data extraction and transformation, and **Microsoft Excel** for actuarial modeling and visualization.

**Actuarial relevance:**  
Life tables and mortality analysis are fundamental to actuarial science, forming the basis for **insurance pricing**, **pension funding**, and **risk assessment**.

---

## 🎯 Objectives
- Store and query large mortality datasets using SQL.
- Calculate mortality rates (\( q_x \)), survival probabilities (\( p_x \)), and life expectancies (\( e_x \)).
- Build complete life tables in Excel.
- Visualize mortality trends and interpret demographic changes.
- Connect insights to actuarial applications.

## 📂 Project Structure
mortality-life-expectancy-study/
│
├── data/ # Raw and cleaned datasets (CSV format)
├── sql/ # SQL scripts for creating tables and querying data
├── excel/ # Excel workbooks with life tables, formulas, and charts
├── README.md # Project documentation (this file)
└── report/ # Summary report with findings and actuarial implications

---

## 🗄 Data Source
The data is obtained from **[Human Mortality Database](https://www.mortality.org/)** (or other public mortality datasets such as CDC WONDER or WHO Mortality Database).  
Columns used:
- `Year`
- `Age`
- `Gender`
- `Population`
- `Deaths`

---

## ⚙️ Methodology

### 1. **SQL Data Processing**
- **Create mortality table:**
```sql
CREATE TABLE mortality_data (
    year INT,
    age INT,
    gender VARCHAR(10),
    population INT,
    deaths INT
);
```
To calculate mortality rates:
```
SELECT year, age, gender,
       deaths * 1.0 / population AS mortality_rate
FROM mortality_data;
```
(Can filter by country, gender, or specific years for targeted analysis

### 2. **Excel Life Table Construction**
- ** Imported SQL output into Excel to calculate:
* $q_x$ = Probability of death
* $p_x = 1 - q_x$ = Probability of survival
* $l_x$ = Survivors at age x
* $d_x = l_x - l_{x+1}$ = Deaths at age x
* $L_x$ = Person-years lived between ages x and x+1
* $T_x$ = Total person-years remaining
* $e_x = T_x / l_x$ = Life expectancy

Example formula use in Excel:
```excel
=1 - (Deaths / Population) // p_x
```

### 3. **Visualization**
* Mortality curve: Age vs. $q_x$
* Survival curve: Age vc. $l_x$
* Life expectancy trend: Year vs. $e_0$ (life expectancy at birth)

