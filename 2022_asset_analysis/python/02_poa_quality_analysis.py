import os
import glob
import pandas as pd
import numpy as np

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\rajes\solar_PV_project\csv_data\system_id=10\year=2022"

OUTPUT_DIR = r"C:\Users\rajes\solar_PV_project\project_2_2022_asset_analysis\outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# FIND CSV FILES
# ============================================================

csv_files = glob.glob(
    os.path.join(BASE_DIR, "**", "*.csv"),
    recursive=True
)

print("=" * 70)
print("2022 POA IRRADIANCE DATA-QUALITY ANALYSIS")
print("=" * 70)

print(f"\nFiles found: {len(csv_files)}")

# ============================================================
# READ DATA
# ============================================================

frames = []

for file in sorted(csv_files):

    df = pd.read_csv(file)

    # Find timestamp
    timestamp_candidates = [
        "measured_on",
        "timestamp",
        "time",
        "datetime",
        "date"
    ]

    timestamp_col = None

    for col in timestamp_candidates:
        if col in df.columns:
            timestamp_col = col
            break

    if timestamp_col is None:
        continue

    df[timestamp_col] = pd.to_datetime(
        df[timestamp_col],
        errors="coerce"
    )

    # Find POA column
    poa_candidates = [
        "poa_irradiance__421",
        "poa_irradiance",
        "421"
    ]

    poa_col = None

    for col in poa_candidates:
        if col in df.columns:
            poa_col = col
            break

    if poa_col is None:
        continue

    # Keep only required columns
    temp = df[
        [timestamp_col, poa_col]
    ].copy()

    temp.columns = [
        "timestamp",
        "poa"
    ]

    frames.append(temp)

# ============================================================
# COMBINE
# ============================================================

data = pd.concat(
    frames,
    ignore_index=True
)

data = data.sort_values(
    "timestamp"
).reset_index(drop=True)

# Remove invalid timestamps
data = data.dropna(
    subset=["timestamp"]
)

print(f"\nTotal records: {len(data):,}")

# ============================================================
# BASIC POA STATISTICS
# ============================================================

missing = data["poa"].isna()

valid = ~missing

print("\nPOA statistics")
print("-" * 70)

print(f"Missing POA values : {missing.sum():,}")
print(f"Valid POA values   : {valid.sum():,}")

print(
    f"Missing percentage : "
    f"{missing.mean() * 100:.2f}%"
)

# ============================================================
# VALID POA DISTRIBUTION
# ============================================================

print("\nValid POA distribution")
print("-" * 70)

print(
    data.loc[valid, "poa"].describe()
)

# ============================================================
# TIME INFORMATION
# ============================================================

data["date"] = data["timestamp"].dt.date

data["month"] = data["timestamp"].dt.month

data["hour"] = data["timestamp"].dt.hour

data["minute"] = data["timestamp"].dt.minute

# ============================================================
# MISSING POA BY MONTH
# ============================================================

monthly = (
    data.groupby("month")
    .agg(
        total_samples=("poa", "size"),
        missing_poa=("poa", lambda x: x.isna().sum()),
        valid_poa=("poa", lambda x: x.notna().sum())
    )
    .reset_index()
)

monthly["missing_percentage"] = (
    monthly["missing_poa"] /
    monthly["total_samples"] *
    100
)

print("\n")
print("=" * 70)
print("MISSING POA BY MONTH")
print("=" * 70)

print(
    monthly.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)

# ============================================================
# MISSING POA BY HOUR
# ============================================================

hourly = (
    data.groupby("hour")
    .agg(
        total_samples=("poa", "size"),
        missing_poa=("poa", lambda x: x.isna().sum()),
        valid_poa=("poa", lambda x: x.notna().sum())
    )
    .reset_index()
)

hourly["missing_percentage"] = (
    hourly["missing_poa"] /
    hourly["total_samples"] *
    100
)

print("\n")
print("=" * 70)
print("MISSING POA BY HOUR")
print("=" * 70)

print(
    hourly.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)

# ============================================================
# MISSING POA BY DAY
# ============================================================

daily = (
    data.groupby("date")
    .agg(
        total_samples=("poa", "size"),
        missing_poa=("poa", lambda x: x.isna().sum()),
        valid_poa=("poa", lambda x: x.notna().sum())
    )
    .reset_index()
)

daily["missing_percentage"] = (
    daily["missing_poa"] /
    daily["total_samples"] *
    100
)

# ============================================================
# DAYS WITH HIGH POA MISSINGNESS
# ============================================================

high_missing_days = daily[
    daily["missing_percentage"] > 50
].copy()

print("\n")
print("=" * 70)
print("DAYS WITH >50% POA DATA MISSING")
print("=" * 70)

if len(high_missing_days) == 0:

    print("No days exceed 50% missing POA.")

else:

    print(
        high_missing_days.to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )

# ============================================================
# POTENTIAL DAYLIGHT MISSING DATA
# ============================================================
#
# We use valid POA > 50 W/m² as evidence of meaningful
# irradiance. This does NOT assume that missing POA means
# zero irradiance.
#
# We first identify hours where valid POA measurements
# demonstrate solar activity.
# ============================================================

hourly_valid_poa = (
    data[
        data["poa"].notna()
    ]
    .groupby("hour")["poa"]
    .max()
)

solar_hours = hourly_valid_poa[
    hourly_valid_poa > 50
].index.tolist()

print("\n")
print("=" * 70)
print("HOURS WITH OBSERVED SOLAR ACTIVITY")
print("=" * 70)

print(solar_hours)

# ============================================================
# MISSING POA DURING OBSERVED SOLAR HOURS
# ============================================================

daylight_candidate = data[
    data["hour"].isin(solar_hours)
]

daylight_missing = daylight_candidate["poa"].isna()

print("\n")
print("=" * 70)
print("POA MISSINGNESS DURING HOURS WITH OBSERVED SOLAR ACTIVITY")
print("=" * 70)

print(
    f"Samples in solar-active hours : "
    f"{len(daylight_candidate):,}"
)

print(
    f"Missing POA samples           : "
    f"{daylight_missing.sum():,}"
)

if len(daylight_candidate) > 0:

    print(
        f"Missing percentage            : "
        f"{daylight_missing.mean() * 100:.2f}%"
    )

# ============================================================
# CONTINUOUS MISSING PERIODS
# ============================================================

data["poa_missing"] = data["poa"].isna()

data["missing_group"] = (
    data["poa_missing"]
    .ne(
        data["poa_missing"].shift()
    )
    .cumsum()
)

missing_periods = (
    data[
        data["poa_missing"]
    ]
    .groupby("missing_group")
    .agg(
        start=("timestamp", "min"),
        end=("timestamp", "max"),
        samples=("timestamp", "size")
    )
    .reset_index(drop=True)
)

missing_periods["duration_minutes"] = (
    missing_periods["samples"]
)

missing_periods = missing_periods.sort_values(
    "samples",
    ascending=False
)

print("\n")
print("=" * 70)
print("LONGEST CONTINUOUS POA MISSING PERIODS")
print("=" * 70)

print(
    missing_periods.head(20).to_string(
        index=False
    )
)

# ============================================================
# SAVE OUTPUTS
# ============================================================

monthly.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_poa_missing_by_month.csv"
    ),
    index=False
)

hourly.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_poa_missing_by_hour.csv"
    ),
    index=False
)

daily.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_poa_missing_by_day.csv"
    ),
    index=False
)

missing_periods.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_poa_missing_periods.csv"
    ),
    index=False
)

print("\n")
print("=" * 70)
print("POA QUALITY ANALYSIS COMPLETE")
print("=" * 70)

print("\nFiles created:")

print(
    "2022_poa_missing_by_month.csv"
)

print(
    "2022_poa_missing_by_hour.csv"
)

print(
    "2022_poa_missing_by_day.csv"
)

print(
    "2022_poa_missing_periods.csv"
)