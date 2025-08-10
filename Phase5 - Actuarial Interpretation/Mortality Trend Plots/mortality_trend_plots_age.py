import pandas as pd
import matplotlib.pyplot as plt

# Load dataset
agegroup_df = pd.read_csv("./data/outputs/agegroup_trends.csv")

# Filter infant and elderly groups
infant = agegroup_df[agegroup_df["AgeGroupStart"] == 0]
elderly = agegroup_df[agegroup_df["AgeGroupStart"].isin([65, 70, 75, 80, 85, 90])]

# Plot infant mortality trend
plt.figure(figsize=(8, 4))
plt.plot(infant["Year"], infant["avg_mx_5yr_band"], label="Infant (0 years)")
plt.xlabel("Year")
plt.ylabel("Mortality Rate")
plt.title("Infant Mortality Over Time")
plt.grid(True)
plt.legend()
plt.show()

# Plot elderly mortality trends
plt.figure(figsize=(10, 6))
for age in [65, 70, 75, 80, 85, 90]:
    subset = elderly[elderly["AgeGroupStart"] == age]
    plt.plot(subset["Year"], subset["avg_mx_5yr_band"], label=f"Age {age}+")
plt.xlabel("Year")
plt.ylabel("Mortality Rate")
plt.title("Elderly Mortality Over Time")
plt.grid(True)
plt.legend()
plt.show()
