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
print("2022 POA VALUE VALIDATION")
print("=" * 70)

print(f"\nFiles found: {len(csv_files)}")

# ============================================================
# READ POA + POWER
# ============================================================

frames = []

for file in sorted(csv_files):

    df = pd.read_csv(file)

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    timestamp_col = None

    for col in [
        "measured_on",
        "timestamp",
        "time",
        "datetime",
        "date"
    ]:
        if col in df.columns:
            timestamp_col = col
            break

    if timestamp_col is None:
        continue

    # --------------------------------------------------------
    # POA
    # --------------------------------------------------------

    poa_col = None

    for col in [
        "poa_irradiance__421",
        "poa_irradiance",
        "421"
    ]:
        if col in df.columns:
            poa_col = col
            break

    # --------------------------------------------------------
    # DC power
    # --------------------------------------------------------

    dc_col = None

    for col in [
        "dc_power__422",
        "dc_power",
        "422"
    ]:
        if col in df.columns:
            dc_col = col
            break

    if poa_col is None:
        continue

    temp = pd.DataFrame()

    temp["timestamp"] = pd.to_datetime(
        df[timestamp_col],
        errors="coerce"
    )

    temp["poa"] = pd.to_numeric(
        df[poa_col],
        errors="coerce"
    )

    if dc_col is not None:
        temp["dc_power"] = pd.to_numeric(
            df[dc_col],
            errors="coerce"
        )
    else:
        temp["dc_power"] = np.nan

    frames.append(temp)

# ============================================================
# COMBINE
# ============================================================

data = pd.concat(
    frames,
    ignore_index=True
)

data = data.dropna(
    subset=["timestamp"]
)

data = data.sort_values(
    "timestamp"
).reset_index(drop=True)

print(f"\nTotal records: {len(data):,}")

# ============================================================
# RAW POA COUNTS
# ============================================================

print("\n")
print("=" * 70)
print("RAW POA VALUE RANGES")
print("=" * 70)

conditions = {
    "Missing": data["poa"].isna(),

    "Negative (< 0)": data["poa"] < 0,

    "Near zero (0 to 10)": (
        (data["poa"] >= 0) &
        (data["poa"] <= 10)
    ),

    "10 to 50": (
        (data["poa"] > 10) &
        (data["poa"] <= 50)
    ),

    "50 to 200": (
        (data["poa"] > 50) &
        (data["poa"] <= 200)
    ),

    "200 to 500": (
        (data["poa"] > 200) &
        (data["poa"] <= 500)
    ),

    "500 to 800": (
        (data["poa"] > 500) &
        (data["poa"] <= 800)
    ),

    "800 to 1000": (
        (data["poa"] > 800) &
        (data["poa"] <= 1000)
    ),

    "1000 to 1200": (
        (data["poa"] > 1000) &
        (data["poa"] <= 1200)
    ),

    "1200 to 1500": (
        (data["poa"] > 1200) &
        (data["poa"] <= 1500)
    ),

    "Above 1500": (
        data["poa"] > 1500
    ),

    "Above 2000": (
        data["poa"] > 2000
    ),

    "Above 3000": (
        data["poa"] > 3000
    ),

    "Above 4000": (
        data["poa"] > 4000
    ),
}

for name, mask in conditions.items():

    count = mask.sum()

    percentage = (
        count /
        len(data) *
        100
    )

    print(
        f"{name:25s}: "
        f"{count:8,d} "
        f"({percentage:6.2f}%)"
    )

# ============================================================
# POA QUANTILES
# ============================================================

print("\n")
print("=" * 70)
print("POA QUANTILES")
print("=" * 70)

print(
    data["poa"].describe(
        percentiles=[
            0.001,
            0.005,
            0.01,
            0.05,
            0.10,
            0.25,
            0.50,
            0.75,
            0.90,
            0.95,
            0.99,
            0.995,
            0.999
        ]
    )
)

# ============================================================
# EXTREME VALUES
# ============================================================

print("\n")
print("=" * 70)
print("HIGHEST POA VALUES")
print("=" * 70)

print(
    data[
        ["timestamp", "poa", "dc_power"]
    ]
    .sort_values(
        "poa",
        ascending=False
    )
    .head(20)
    .to_string(index=False)
)

print("\n")
print("=" * 70)
print("LOWEST POA VALUES")
print("=" * 70)

print(
    data[
        ["timestamp", "poa", "dc_power"]
    ]
    .sort_values(
        "poa",
        ascending=True
    )
    .head(20)
    .to_string(index=False)
)

# ============================================================
# EXTREME POA + DC POWER RELATIONSHIP
# ============================================================

print("\n")
print("=" * 70)
print("SUSPICIOUS POA VALUES AND DC POWER")
print("=" * 70)

suspicious = data[
    (data["poa"] < -100) |
    (data["poa"] > 1500)
].copy()

print(
    f"\nSuspicious POA records: "
    f"{len(suspicious):,}"
)

if len(suspicious) > 0:

    print(
        suspicious[
            [
                "timestamp",
                "poa",
                "dc_power"
            ]
        ]
        .head(50)
        .to_string(index=False)
    )

# ============================================================
# MONTHLY EXTREME POA
# ============================================================

data["month"] = data["timestamp"].dt.month

monthly = (
    data.groupby("month")
    .agg(
        records=("poa", "size"),
        missing=("poa", lambda x: x.isna().sum()),
        minimum_poa=("poa", "min"),
        maximum_poa=("poa", "max"),
        median_poa=("poa", "median"),
        mean_poa=("poa", "mean"),
        negative_poa=("poa", lambda x: (x < 0).sum()),
        above_1500=("poa", lambda x: (x > 1500).sum())
    )
    .reset_index()
)

print("\n")
print("=" * 70)
print("MONTHLY POA VALIDATION")
print("=" * 70)

print(
    monthly.to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)

# ============================================================
# SAVE RESULTS
# ============================================================

data[
    [
        "timestamp",
        "poa",
        "dc_power"
    ]
].to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_poa_raw_for_validation.csv"
    ),
    index=False
)

monthly.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_poa_monthly_validation.csv"
    ),
    index=False
)

print("\n")
print("=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)