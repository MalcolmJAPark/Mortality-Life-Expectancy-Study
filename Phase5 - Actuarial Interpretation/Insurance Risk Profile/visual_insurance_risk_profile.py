import pandas as pd
import matplotlib.pyplot as plt

# Reload datasets after reset
e0_df = pd.read_csv("./data/outputs/e0_by_decade.csv")
agegroup_df = pd.read_csv("./data/outputs/agegroup_trends.csv")
mortality_df = pd.read_csv("./data/outputs/mortality_rates.csv")

# Prepare life expectancy trend
e0_trend = e0_df.groupby("Decade")["avg_e0"].mean().reset_index()

# Prepare elderly mortality (65+ aggregated)
elderly = agegroup_df[agegroup_df["AgeGroupStart"] >= 65]
elderly_trend = elderly.groupby("Year")["avg_mx_5yr_band"].mean().reset_index()

# Prepare sample insurance group (Age 40–50)
insurance_group = mortality_df[(mortality_df["Age"] >= 40) & (mortality_df["Age"] <= 50)]
insurance_trend = insurance_group.groupby("Year")["MortalityRate"].mean().reset_index()

# Plot dashboard
fig, axes = plt.subplots(3, 1, figsize=(10, 12))

# Life expectancy trend
axes[0].plot(e0_trend["Decade"], e0_trend["avg_e0"], marker='o')
axes[0].set_title("Life Expectancy at Birth (e₀) Trend")
axes[0].set_xlabel("Decade")
axes[0].set_ylabel("Life Expectancy (Years)")
axes[0].grid(True)

# Elderly mortality trend
axes[1].plot(elderly_trend["Year"], elderly_trend["avg_mx_5yr_band"], color='orange')
axes[1].set_title("Average Mortality Rate (Ages 65+)")
axes[1].set_xlabel("Year")
axes[1].set_ylabel("Mortality Rate")
axes[1].grid(True)

# Insurance risk profile (Age 40–50)
axes[2].plot(insurance_trend["Year"], insurance_trend["MortalityRate"], color='green')
axes[2].set_title("Mortality Rate Trend (Ages 40–50)")
axes[2].set_xlabel("Year")
axes[2].set_ylabel("Mortality Rate")
axes[2].grid(True)

plt.tight_layout()
plt.show()
