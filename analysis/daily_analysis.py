import pandas as pd
import matplotlib.pyplot as plt
import os


# ============================================================
# SYSTEM 10 - DAILY PV ANALYSIS
# ============================================================
#
# First test day:
# January 1, 2022
#
# Analysis:
#   1. POA irradiance vs time
#   2. DC power vs AC power vs time
#   3. POA irradiance vs DC power
#   4. Daily DC and AC energy
#
# IMPORTANT:
# Raw data is NOT modified.
# Negative values are NOT removed or clipped.
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_PATH = r"C:\Users\rajes\solar_PV_project"

INPUT_FILE = os.path.join(
    BASE_PATH,
    "analysis",
    "system10_january_2022_loaded.csv"
)

PLOT_BASE_DIR = os.path.join(
    BASE_PATH,
    "plots",
    "system10_january_2022"
)

OUTPUT_BASE_DIR = os.path.join(
    BASE_PATH,
    "analysis"
)

# Day we are analyzing
ANALYSIS_DATE = "2022-01-01"

# Create output folder for this day
DAY_FOLDER_NAME = "Jan01"

PLOT_DIR = os.path.join(
    PLOT_BASE_DIR,
    DAY_FOLDER_NAME
)

os.makedirs(PLOT_DIR, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("SYSTEM 10 - DAILY PV ANALYSIS")
print("=" * 70)

print("\nInput file:")
print(INPUT_FILE)

df = pd.read_csv(INPUT_FILE)

# Convert timestamp
df["measured_on"] = pd.to_datetime(
    df["measured_on"],
    errors="coerce"
)

# Sort chronologically
df = df.sort_values(
    "measured_on"
).reset_index(drop=True)


# ============================================================
# SELECT ONE DAY
# ============================================================

analysis_date = pd.Timestamp(ANALYSIS_DATE).date()

day_df = df[
    df["measured_on"].dt.date == analysis_date
].copy()

day_df = day_df.sort_values(
    "measured_on"
).reset_index(drop=True)


# ============================================================
# CHECK DATA
# ============================================================

print("\n" + "=" * 70)
print("DAY INFORMATION")
print("=" * 70)

print("Date:", ANALYSIS_DATE)

print("Records:", len(day_df))

if len(day_df) > 0:

    print(
        "First timestamp:",
        day_df["measured_on"].min()
    )

    print(
        "Last timestamp:",
        day_df["measured_on"].max()
    )

else:

    raise ValueError(
        f"No data found for {ANALYSIS_DATE}"
    )


# ============================================================
# SAMPLING INTERVAL
# ============================================================

time_difference = (
    day_df["measured_on"]
    .diff()
    .dropna()
)

print("\nSampling interval:")

print(
    time_difference
    .value_counts()
    .head()
)


# ============================================================
# ENERGY CALCULATION
# ============================================================
#
# Power is measured in W.
#
# Convert W → kW:
#
#     P_kW = P_W / 1000
#
# Sampling interval:
#
#     1 minute = 1/60 hour
#
# Therefore:
#
#     Energy per sample =
#         P_W / 1000 / 60
#
# ============================================================

day_df["dc_energy_kwh"] = (
    day_df["dc_power__422"]
    / 1000.0
    / 60.0
)

day_df["ac_energy_kwh"] = (
    day_df["ac_power__423"]
    / 1000.0
    / 60.0
)


# Total energy for the day

dc_energy = day_df[
    "dc_energy_kwh"
].sum()

ac_energy = day_df[
    "ac_energy_kwh"
].sum()


# ============================================================
# BASIC STATISTICS
# ============================================================

peak_poa = day_df[
    "poa_irradiance__421"
].max()

peak_dc = day_df[
    "dc_power__422"
].max()

peak_ac = day_df[
    "ac_power__423"
].max()


mean_poa = day_df[
    "poa_irradiance__421"
].mean()

mean_dc = day_df[
    "dc_power__422"
].mean()

mean_ac = day_df[
    "ac_power__423"
].mean()


# ============================================================
# PRINT SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("DAILY SUMMARY")
print("=" * 70)

print(f"Date:                  {ANALYSIS_DATE}")
print(f"Records:               {len(day_df)}")

print(
    f"Peak POA irradiance:   {peak_poa:.2f} W/m²"
)

print(
    f"Peak DC power:         {peak_dc:.2f} W"
)

print(
    f"Peak AC power:         {peak_ac:.2f} W"
)

print(
    f"Mean POA irradiance:   {mean_poa:.2f} W/m²"
)

print(
    f"Mean DC power:         {mean_dc:.2f} W"
)

print(
    f"Mean AC power:         {mean_ac:.2f} W"
)

print(
    f"DC energy:             {dc_energy:.4f} kWh"
)

print(
    f"AC energy:             {ac_energy:.4f} kWh"
)


# ============================================================
# DC -> AC ENERGY RATIO
# ============================================================

if dc_energy != 0:

    dc_to_ac_ratio = (
        ac_energy / dc_energy
    )

    print(
        f"AC/DC energy ratio:    {dc_to_ac_ratio:.4f}"
    )

else:

    dc_to_ac_ratio = None

    print(
        "AC/DC energy ratio:    undefined"
    )


# ============================================================
# NEGATIVE VALUES
# ============================================================

print("\n" + "=" * 70)
print("NEGATIVE VALUE CHECK")
print("=" * 70)

negative_columns = [
    "poa_irradiance__421",
    "dc_power__422",
    "ac_power__423"
]

for column in negative_columns:

    count = (
        day_df[column] < 0
    ).sum()

    percentage = (
        count / len(day_df) * 100
    )

    print(
        f"{column:25s}: "
        f"{count:4d} "
        f"({percentage:6.2f}%)"
    )


# ============================================================
# PLOT 1
# POA IRRADIANCE VS TIME
# ============================================================

plt.figure(figsize=(14, 6))

plt.plot(
    day_df["measured_on"],
    day_df["poa_irradiance__421"],
    linewidth=1.2
)

plt.xlabel("Time")
plt.ylabel("POA Irradiance (W/m²)")

plt.title(
    "System 10 - January 1, 2022 - POA Irradiance"
)

plt.grid(True)

plt.tight_layout()

plot_file = os.path.join(
    PLOT_DIR,
    "01_poa_irradiance_vs_time.png"
)

plt.savefig(
    plot_file,
    dpi=150
)

plt.close()

print("\nSaved:")
print(plot_file)


# ============================================================
# PLOT 2
# DC POWER VS AC POWER
# ============================================================

plt.figure(figsize=(14, 6))

plt.plot(
    day_df["measured_on"],
    day_df["dc_power__422"],
    label="DC Power",
    linewidth=1.2
)

plt.plot(
    day_df["measured_on"],
    day_df["ac_power__423"],
    label="AC Power",
    linewidth=1.2
)

plt.xlabel("Time")
plt.ylabel("Power (W)")

plt.title(
    "System 10 - January 1, 2022 - DC vs AC Power"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

plot_file = os.path.join(
    PLOT_DIR,
    "02_dc_vs_ac_power.png"
)

plt.savefig(
    plot_file,
    dpi=150
)

plt.close()

print("Saved:")
print(plot_file)


# ============================================================
# PLOT 3
# POA IRRADIANCE VS DC POWER
# ============================================================

plt.figure(figsize=(8, 6))

plt.scatter(
    day_df["poa_irradiance__421"],
    day_df["dc_power__422"],
    s=8,
    alpha=0.5
)

plt.xlabel(
    "POA Irradiance (W/m²)"
)

plt.ylabel(
    "DC Power (W)"
)

plt.title(
    "System 10 - January 1, 2022 - Irradiance vs DC Power"
)

plt.grid(True)

plt.tight_layout()

plot_file = os.path.join(
    PLOT_DIR,
    "03_irradiance_vs_dc_power.png"
)

plt.savefig(
    plot_file,
    dpi=150
)

plt.close()

print("Saved:")
print(plot_file)


# ============================================================
# SAVE DAILY DATA
# ============================================================

daily_output_file = os.path.join(
    OUTPUT_BASE_DIR,
    "system10_2022-01-01_analysis.csv"
)

day_df.to_csv(
    daily_output_file,
    index=False
)

print("\nSaved daily dataset:")
print(daily_output_file)


# ============================================================
# SAVE DAILY SUMMARY
# ============================================================

summary = pd.DataFrame(
    {
        "date": [ANALYSIS_DATE],
        "records": [len(day_df)],
        "peak_poa_w_m2": [peak_poa],
        "peak_dc_power_w": [peak_dc],
        "peak_ac_power_w": [peak_ac],
        "mean_poa_w_m2": [mean_poa],
        "mean_dc_power_w": [mean_dc],
        "mean_ac_power_w": [mean_ac],
        "dc_energy_kwh": [dc_energy],
        "ac_energy_kwh": [ac_energy],
        "ac_dc_energy_ratio": [dc_to_ac_ratio]
    }
)

summary_file = os.path.join(
    OUTPUT_BASE_DIR,
    "system10_daily_summary.csv"
)

summary.to_csv(
    summary_file,
    index=False
)

print("\nSaved summary:")
print(summary_file)


# ============================================================
# FINISHED
# ============================================================

print("\n" + "=" * 70)
print("DAILY ANALYSIS COMPLETE")
print("=" * 70)

print("\nPlots are located in:")
print(PLOT_DIR)

print("\nFiles created:")

print("1. POA irradiance vs time")
print("2. DC vs AC power")
print("3. Irradiance vs DC power")
print("4. Daily raw analysis CSV")
print("5. Daily summary CSV")
