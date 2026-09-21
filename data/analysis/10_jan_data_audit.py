import pandas as pd
import glob
import os

# ============================================================
# SYSTEM 10 - JANUARY 2022 DATA AUDIT
# ============================================================

DATA_PATH = (
    r"C:\Users\rajes\solar_PV_project"
    r"\pvdaq_csv\pvdata\system_id=10\year=2022\month=1"
)

# ------------------------------------------------------------
# 1. Find all CSV files
# ------------------------------------------------------------

files = sorted(
    glob.glob(os.path.join(DATA_PATH, "**", "*.csv"), recursive=True)
)

print("=" * 70)
print("SYSTEM 10 - JANUARY 2022 DATA AUDIT")
print("=" * 70)

print(f"\nCSV files found: {len(files)}")

for f in files:
    print("  ", f)

if not files:
    raise FileNotFoundError("No CSV files found.")

# ------------------------------------------------------------
# 2. Load all January data
# ------------------------------------------------------------

frames = []

for f in files:
    print(f"\nLoading: {os.path.basename(f)}")

    df_day = pd.read_csv(f)

    frames.append(df_day)

df = pd.concat(frames, ignore_index=True)

print("\n" + "=" * 70)
print("BASIC DATASET INFORMATION")
print("=" * 70)

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nColumns:")
for col in df.columns:
    print("  ", col)

# ------------------------------------------------------------
# 3. Parse timestamps
# ------------------------------------------------------------

df["measured_on"] = pd.to_datetime(
    df["measured_on"],
    errors="coerce"
)

print("\n" + "=" * 70)
print("TIMESTAMP INFORMATION")
print("=" * 70)

print("First timestamp:", df["measured_on"].min())
print("Last timestamp :", df["measured_on"].max())

# ------------------------------------------------------------
# 4. Invalid timestamps
# ------------------------------------------------------------

invalid_time = df["measured_on"].isna().sum()

print("\nInvalid timestamps:", invalid_time)

# ------------------------------------------------------------
# 5. Duplicate timestamps
# ------------------------------------------------------------

duplicate_timestamps = df["measured_on"].duplicated().sum()

print("Duplicate timestamps:", duplicate_timestamps)

# ------------------------------------------------------------
# 6. Sort chronologically
# ------------------------------------------------------------

df = df.sort_values("measured_on").reset_index(drop=True)

# ------------------------------------------------------------
# 7. Sampling interval
# ------------------------------------------------------------

time_difference = df["measured_on"].diff().dropna()

print("\n" + "=" * 70)
print("SAMPLING INTERVAL")
print("=" * 70)

print("\nMost common time intervals:")

print(
    time_difference
    .value_counts()
    .head(10)
)

median_interval = time_difference.median()

print("\nMedian sampling interval:", median_interval)

# ------------------------------------------------------------
# 8. Expected number of records
# ------------------------------------------------------------

expected_records = 31 * 1440

print("\n" + "=" * 70)
print("RECORD COUNT")
print("=" * 70)

print("Expected January records:", expected_records)
print("Actual records:", len(df))
print("Difference:", len(df) - expected_records)

# ------------------------------------------------------------
# 9. Missing values
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("MISSING VALUES")
print("=" * 70)

missing = df.isna().sum()

print(missing[missing > 0])

# ------------------------------------------------------------
# 10. Numeric statistics
# ------------------------------------------------------------

numeric_columns = [
    "poa_irradiance__421",
    "dc_power__422",
    "ac_power__423",
    "dc_pos_voltage__424",
    "dc_pos_current__425",
    "ac_voltage__426",
    "ac_current__427",
    "ambient_temp__428",
    "module_temp_1__429",
    "module_temp_2__430",
    "module_temp_3__431",
    "inverter_temp__432",
    "das_temp__433",
    "das_battery_voltage__434",
]

print("\n" + "=" * 70)
print("NUMERIC DATA RANGE")
print("=" * 70)

print(
    df[numeric_columns]
    .describe()
    .T[
        [
            "count",
            "mean",
            "std",
            "min",
            "25%",
            "50%",
            "75%",
            "max",
        ]
    ]
)

# ------------------------------------------------------------
# 11. Negative values
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("NEGATIVE VALUES")
print("=" * 70)

for col in numeric_columns:
    count = (df[col] < 0).sum()

    if count > 0:
        percentage = count / len(df) * 100

        print(
            f"{col:30s} "
            f"{count:6d} "
            f"({percentage:6.2f}%)"
        )

# ------------------------------------------------------------
# 12. Save cleaned chronological January data
# ------------------------------------------------------------

output_file = (
    r"C:\Users\rajes\solar_PV_project"
    r"\analysis\system10_january_2022_loaded.csv"
)

df.to_csv(output_file, index=False)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)

print("\nSaved combined January data to:")
print(output_file)