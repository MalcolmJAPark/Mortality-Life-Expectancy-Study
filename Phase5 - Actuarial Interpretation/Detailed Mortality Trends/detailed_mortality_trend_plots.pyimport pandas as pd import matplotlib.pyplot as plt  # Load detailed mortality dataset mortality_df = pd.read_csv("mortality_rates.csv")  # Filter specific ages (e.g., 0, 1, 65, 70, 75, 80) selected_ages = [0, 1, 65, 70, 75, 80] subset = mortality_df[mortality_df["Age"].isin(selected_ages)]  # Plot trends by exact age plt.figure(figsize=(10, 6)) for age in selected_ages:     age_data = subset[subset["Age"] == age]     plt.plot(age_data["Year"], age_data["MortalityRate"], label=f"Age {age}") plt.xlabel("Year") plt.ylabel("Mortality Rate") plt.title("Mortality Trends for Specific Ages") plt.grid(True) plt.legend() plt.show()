import pandas as pd
import matplotlib.pyplot as plt

# Load detailed mortality dataset
mortality_df = pd.read_csv("mortality_rates.csv")

# Filter specific ages (e.g., 0, 1, 65, 70, 75, 80)
selected_ages = [0, 1, 65, 70, 75, 80]
subset = mortality_df[mortality_df["Age"].isin(selected_ages)]

# Plot trends by exact age
plt.figure(figsize=(10, 6))
for age in selected_ages:
    age_data = subset[subset["Age"] == age]
    plt.plot(age_data["Year"], age_data["MortalityRate"], label=f"Age {age}")
plt.xlabel("Year")
plt.ylabel("Mortality Rate")
plt.title("Mortality Trends for Specific Ages")
plt.grid(True)
plt.legend()
plt.show()
