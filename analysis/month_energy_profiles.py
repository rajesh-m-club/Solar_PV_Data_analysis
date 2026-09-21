import pandas as pd
import matplotlib.pyplot as plt
import os


# ============================================================
# PATHS
# ============================================================

BASE_PATH = r"C:\Users\rajes\solar_PV_project"

INPUT_FILE = os.path.join(
    BASE_PATH,
    "analysis",
    "system10_january_2022_loaded.csv"
)

PLOT_DIR = os.path.join(
    BASE_PATH,
    "plots",
    "system10_january_2022"
)

OUTPUT_FILE = os.path.join(
    BASE_PATH,
    "analysis",
    "daily_energy_system10_jan2022.csv"
)

PROFILE_FILE = os.path.join(
    BASE_PATH,
    "analysis",
    "daily_profiles_system10_jan2022.csv"
)

os.makedirs(PLOT_DIR, exist_ok=True)


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("SYSTEM 10 - DAILY PROFILES AND ENERGY")
print("=" * 70)

print("\nLoading:")
print(INPUT_FILE)

df = pd.read_csv(INPUT_FILE)

df["measured_on"] = pd.to_datetime(df["measured_on"])

df = df.sort_values("measured_on").reset_index(drop=True)

print("\nRows:", len(df))
print("First:", df["measured_on"].min())
print("Last :", df["measured_on"].max())


# ============================================================
# CREATE DATE AND TIME COLUMNS
# ============================================================

df["date"] = df["measured_on"].dt.date
df["time"] = df["measured_on"].dt.time


# ============================================================
# ENERGY CALCULATION
# ============================================================

# Data is sampled every 1 minute.
#
# Power is in W.
#
# Energy per minute:
#
#       P(W)
# E = ------- * 1/60
#       1000
#
# Result = kWh

df["ac_energy_kwh"] = (
    df["ac_power__423"] / 1000.0 / 60.0
)

df["dc_energy_kwh"] = (
    df["dc_power__422"] / 1000.0 / 60.0
)


# ============================================================
# DAILY AGGREGATION
# ============================================================

daily = (
    df.groupby("date")
    .agg(
        ac_energy_kwh=("ac_energy_kwh", "sum"),
        dc_energy_kwh=("dc_energy_kwh", "sum"),

        peak_ac_power_w=("ac_power__423", "max"),
        peak_dc_power_w=("dc_power__422", "max"),

        peak_poa_w_m2=("poa_irradiance__421", "max"),

        mean_poa_w_m2=("poa_irradiance__421", "mean"),

        mean_ambient_temp_c=("ambient_temp__428", "mean"),

        mean_module_temp_1_c=("module_temp_1__429", "mean"),
        mean_module_temp_2_c=("module_temp_2__430", "mean"),
        mean_module_temp_3_c=("module_temp_3__431", "mean"),

        mean_inverter_temp_c=("inverter_temp__432", "mean"),

        records=("measured_on", "count")
    )
    .reset_index()
)


# ============================================================
# DAILY DC -> AC ENERGY RATIO
# ============================================================

daily["dc_to_ac_energy_ratio"] = (
    daily["ac_energy_kwh"] /
    daily["dc_energy_kwh"]
)


# ============================================================
# PRINT DAILY RESULTS
# ============================================================

print("\n" + "=" * 70)
print("DAILY ENERGY")
print("=" * 70)

print(
    daily[
        [
            "date",
            "ac_energy_kwh",
            "dc_energy_kwh",
            "peak_ac_power_w",
            "peak_dc_power_w",
            "peak_poa_w_m2",
            "records"
        ]
    ].to_string(index=False)
)


# ============================================================
# TOTAL ENERGY
# ============================================================

total_ac_energy = daily["ac_energy_kwh"].sum()
total_dc_energy = daily["dc_energy_kwh"].sum()

print("\n" + "=" * 70)
print("TOTAL OBSERVED ENERGY")
print("=" * 70)

print(f"AC energy: {total_ac_energy:.3f} kWh")
print(f"DC energy: {total_dc_energy:.3f} kWh")


# ============================================================
# ENERGY PER AVAILABLE DAY
# ============================================================

number_of_days = len(daily)

print("\nNumber of observed days:", number_of_days)

print(
    f"Average AC energy/day: "
    f"{total_ac_energy / number_of_days:.3f} kWh"
)

print(
    f"Average DC energy/day: "
    f"{total_dc_energy / number_of_days:.3f} kWh"
)


# ============================================================
# SAVE DAILY DATA
# ============================================================

daily.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\nDaily energy table saved to:")
print(OUTPUT_FILE)


# ============================================================
# CREATE DAILY PROFILE DATASET
# ============================================================

profile_columns = [
    "measured_on",
    "poa_irradiance__421",
    "dc_power__422",
    "ac_power__423",
    "ambient_temp__428",
    "module_temp_1__429",
    "module_temp_2__430",
    "module_temp_3__431",
    "inverter_temp__432"
]

profiles = df[profile_columns].copy()

profiles.to_csv(
    PROFILE_FILE,
    index=False
)

print("\nProfile dataset saved to:")
print(PROFILE_FILE)


# ============================================================
# PLOT 1
# POA IRRADIANCE
# ============================================================

plt.figure(figsize=(14, 6))

plt.plot(
    df["measured_on"],
    df["poa_irradiance__421"]
)

plt.xlabel("Time")
plt.ylabel("POA Irradiance (W/m²)")
plt.title("System 10 - January 2022 POA Irradiance")

plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        PLOT_DIR,
        "01_poa_irradiance_january.png"
    ),
    dpi=150
)

plt.close()


# ============================================================
# PLOT 2
# DC AND AC POWER
# ============================================================

plt.figure(figsize=(14, 6))

plt.plot(
    df["measured_on"],
    df["dc_power__422"],
    label="DC Power"
)

plt.plot(
    df["measured_on"],
    df["ac_power__423"],
    label="AC Power"
)

plt.xlabel("Time")
plt.ylabel("Power (W)")
plt.title("System 10 - January 2022 DC and AC Power")

plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        PLOT_DIR,
        "02_dc_ac_power_january.png"
    ),
    dpi=150
)

plt.close()


# ============================================================
# PLOT 3
# TEMPERATURES
# ============================================================

plt.figure(figsize=(14, 6))

plt.plot(
    df["measured_on"],
    df["ambient_temp__428"],
    label="Ambient"
)

plt.plot(
    df["measured_on"],
    df["module_temp_1__429"],
    label="Module 1"
)

plt.plot(
    df["measured_on"],
    df["module_temp_2__430"],
    label="Module 2"
)

plt.plot(
    df["measured_on"],
    df["module_temp_3__431"],
    label="Module 3"
)

plt.plot(
    df["measured_on"],
    df["inverter_temp__432"],
    label="Inverter"
)

plt.xlabel("Time")
plt.ylabel("Temperature (°C)")
plt.title("System 10 - January 2022 Temperatures")

plt.legend()
plt.grid(True)
plt.tight_layout()

plt.savefig(
    os.path.join(
        PLOT_DIR,
        "03_temperatures_january.png"
    ),
    dpi=150
)

plt.close()


# ============================================================
# PLOT 4
# DAILY AC ENERGY
# ============================================================

plt.figure(figsize=(14, 6))

plt.bar(
    daily["date"].astype(str),
    daily["ac_energy_kwh"]
)

plt.xlabel("Date")
plt.ylabel("AC Energy (kWh)")
plt.title("System 10 - Daily AC Energy - January 2022")

plt.xticks(rotation=45)
plt.grid(axis="y")

plt.tight_layout()

plt.savefig(
    os.path.join(
        PLOT_DIR,
        "04_daily_ac_energy.png"
    ),
    dpi=150
)

plt.close()


# ============================================================
# PLOT 5
# DAILY DC ENERGY
# ============================================================

plt.figure(figsize=(14, 6))

plt.bar(
    daily["date"].astype(str),
    daily["dc_energy_kwh"]
)

plt.xlabel("Date")
plt.ylabel("DC Energy (kWh)")
plt.title("System 10 - Daily DC Energy - January 2022")

plt.xticks(rotation=45)
plt.grid(axis="y")

plt.tight_layout()

plt.savefig(
    os.path.join(
        PLOT_DIR,
        "05_daily_dc_energy.png"
    ),
    dpi=150
)

plt.close()


# ============================================================
# FINISHED
# ============================================================

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)

print("\nPlots saved in:")
print(PLOT_DIR)