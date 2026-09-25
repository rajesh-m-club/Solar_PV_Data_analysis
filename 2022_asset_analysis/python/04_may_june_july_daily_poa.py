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

# Months to investigate
TARGET_MONTHS = [5, 6, 7]

# Investigation thresholds
NEGATIVE_LIMIT = -7.0
HIGH_LIMIT = 1500.0
EXTREME_LIMIT = 3000.0


# ============================================================
# FIND CSV FILES
# ============================================================

csv_files = glob.glob(
    os.path.join(BASE_DIR, "**", "*.csv"),
    recursive=True
)

print("=" * 80)
print("MAY-JUNE-JULY DAILY POA INVESTIGATION")
print("=" * 80)

print(f"\nFiles found: {len(csv_files)}")


# ============================================================
# READ DATA
# ============================================================

frames = []

# Separate list for files where POA column is completely absent
no_poa_column_files = []


for file in sorted(csv_files):

    df = pd.read_csv(file)

    # --------------------------------------------------------
    # Find timestamp column
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
    # Convert timestamp
    # --------------------------------------------------------

    timestamps = pd.to_datetime(
        df[timestamp_col],
        errors="coerce"
    )

    # --------------------------------------------------------
    # Find POA column
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
    # If POA column DOES NOT EXIST
    # --------------------------------------------------------

    if poa_col is None:

        # Determine month/date from timestamps
        valid_timestamps = timestamps.dropna()

        if len(valid_timestamps) > 0:

            for date_value in sorted(
                valid_timestamps.dt.date.unique()
            ):

                month_value = pd.Timestamp(date_value).month

                if month_value in TARGET_MONTHS:

                    no_poa_column_files.append({
                        "month": month_value,
                        "date": date_value,
                        "file": file,
                        "records_in_file": len(df)
                    })

        # IMPORTANT:
        # Do NOT discard this information silently.
        # We simply don't add it to the POA numerical analysis.
        continue

    # --------------------------------------------------------
    # Find DC power
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

    # --------------------------------------------------------
    # Create temporary dataframe
    # --------------------------------------------------------

    temp = pd.DataFrame()

    temp["timestamp"] = timestamps

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

    temp["source_file"] = file

    frames.append(temp)


# ============================================================
# NO POA COLUMN SUMMARY
# ============================================================

print("\n")
print("=" * 80)
print("DATES WHERE POA_IRRADIANCE COLUMN IS COMPLETELY ABSENT")
print("=" * 80)


if len(no_poa_column_files) > 0:

    no_poa_df = pd.DataFrame(
        no_poa_column_files
    )

    # --------------------------------------------------------
    # Print file-level information
    # --------------------------------------------------------

    print("\nFiles containing NO POA_IRRADIANCE column:")

    print(
        no_poa_df[
            [
                "month",
                "date",
                "records_in_file",
                "file"
            ]
        ].to_string(index=False)
    )

    # --------------------------------------------------------
    # Unique dates
    # --------------------------------------------------------

    no_poa_dates = (
        no_poa_df[
            [
                "month",
                "date"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            ["month", "date"]
        )
    )

    print("\n")
    print("-" * 80)
    print("UNIQUE DATES WITH NO POA_IRRADIANCE COLUMN")
    print("-" * 80)

    print(
        no_poa_dates.to_string(
            index=False
        )
    )

    print(
        f"\nTotal unique dates with no POA column: "
        f"{len(no_poa_dates)}"
    )

    print(
        f"Total files with no POA column: "
        f"{len(no_poa_df)}"
    )

else:

    no_poa_df = pd.DataFrame(
        columns=[
            "month",
            "date",
            "records_in_file",
            "file"
        ]
    )

    no_poa_dates = pd.DataFrame(
        columns=[
            "month",
            "date"
        ]
    )

    print("\nNo files without POA_IRRADIANCE were found.")


# ============================================================
# SAVE NO-POA-COLUMN OUTPUT
# ============================================================

no_poa_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_may_june_july_no_poa_column_files.csv"
    ),
    index=False
)

no_poa_dates.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_may_june_july_dates_no_poa_column.csv"
    ),
    index=False
)


# ============================================================
# COMBINE POA DATA
# ============================================================

if len(frames) == 0:

    print("\nNo files containing POA data were found.")

    raise SystemExit


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


# ============================================================
# SELECT MAY-JUNE-JULY
# ============================================================

data["month"] = data["timestamp"].dt.month
data["date"] = data["timestamp"].dt.date

data = data[
    data["month"].isin(TARGET_MONTHS)
].copy()

print(
    f"\nMay-June-July records with POA column: "
    f"{len(data):,}"
)


# ============================================================
# CREATE ABNORMAL FLAGS
# ============================================================

# POA column exists but the individual value is missing
data["missing_poa"] = data["poa"].isna()

data["abnormal_negative"] = (
    data["poa"] < NEGATIVE_LIMIT
)

data["high_poa"] = (
    data["poa"] > HIGH_LIMIT
)

data["extreme_poa"] = (
    data["poa"] > EXTREME_LIMIT
)

# Either very negative or very high
data["any_abnormal"] = (
    data["abnormal_negative"] |
    data["high_poa"]
)


# ============================================================
# DAILY SUMMARY
# ============================================================

daily = data.groupby(
    ["month", "date"]
).agg(

    records=("poa", "size"),

    missing_poa=(
        "poa",
        lambda x: x.isna().sum()
    ),

    valid_poa=(
        "poa",
        lambda x: x.notna().sum()
    ),

    minimum_poa=(
        "poa",
        "min"
    ),

    maximum_poa=(
        "poa",
        "max"
    ),

    median_poa=(
        "poa",
        "median"
    ),

    mean_poa=(
        "poa",
        "mean"
    ),

    negative_below_minus7=(
        "poa",
        lambda x: (x < NEGATIVE_LIMIT).sum()
    ),

    above_1500=(
        "poa",
        lambda x: (x > HIGH_LIMIT).sum()
    ),

    above_3000=(
        "poa",
        lambda x: (x > EXTREME_LIMIT).sum()
    ),

    dc_power_mean=(
        "dc_power",
        "mean"
    ),

    dc_power_max=(
        "dc_power",
        "max"
    )

).reset_index()


# ============================================================
# DAILY PERCENTAGES
# ============================================================

daily["negative_below_minus7_pct"] = (
    daily["negative_below_minus7"]
    / daily["records"]
    * 100
)

daily["above_1500_pct"] = (
    daily["above_1500"]
    / daily["records"]
    * 100
)

daily["above_3000_pct"] = (
    daily["above_3000"]
    / daily["records"]
    * 100
)

daily["missing_poa_pct"] = (
    daily["missing_poa"]
    / daily["records"]
    * 100
)


# ============================================================
# FLAG DAYS
# ============================================================

# Any day containing abnormal negative values
negative_days = daily[
    daily["negative_below_minus7"] > 0
].copy()

# Any day containing POA > 1500
high_days = daily[
    daily["above_1500"] > 0
].copy()

# Any day containing POA > 3000
extreme_days = daily[
    daily["above_3000"] > 0
].copy()

# Any day containing either type
abnormal_days = daily[
    (
        (daily["negative_below_minus7"] > 0) |
        (daily["above_1500"] > 0)
    )
].copy()


# ============================================================
# PRINT DAILY SUMMARY
# ============================================================

print("\n")
print("=" * 80)
print("ALL MAY-JUNE-JULY DAYS WITH POA COLUMN")
print("=" * 80)

print(
    daily[
        [
            "month",
            "date",
            "records",
            "missing_poa",
            "minimum_poa",
            "maximum_poa",
            "negative_below_minus7",
            "above_1500",
            "above_3000"
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)


# ============================================================
# NEGATIVE POA DAYS
# ============================================================

print("\n")
print("=" * 80)
print("DAYS WITH POA < -7 W/m²")
print("=" * 80)

print(
    negative_days[
        [
            "date",
            "records",
            "minimum_poa",
            "maximum_poa",
            "negative_below_minus7",
            "negative_below_minus7_pct"
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)


# ============================================================
# HIGH POA DAYS
# ============================================================

print("\n")
print("=" * 80)
print("DAYS WITH POA > 1500 W/m²")
print("=" * 80)

print(
    high_days[
        [
            "date",
            "records",
            "minimum_poa",
            "maximum_poa",
            "above_1500",
            "above_1500_pct"
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)


# ============================================================
# EXTREME POA DAYS
# ============================================================

print("\n")
print("=" * 80)
print("DAYS WITH POA > 3000 W/m²")
print("=" * 80)

if len(extreme_days) > 0:

    print(
        extreme_days[
            [
                "date",
                "records",
                "minimum_poa",
                "maximum_poa",
                "above_3000",
                "above_3000_pct"
            ]
        ].to_string(
            index=False,
            float_format=lambda x: f"{x:.2f}"
        )
    )

else:

    print("No days found.")


# ============================================================
# MOST ABNORMAL DAYS
# ============================================================

print("\n")
print("=" * 80)
print("MOST ABNORMAL DAYS")
print("=" * 80)

ranked = abnormal_days.copy()

ranked["abnormal_count"] = (
    ranked["negative_below_minus7"]
    + ranked["above_1500"]
)

ranked = ranked.sort_values(
    "abnormal_count",
    ascending=False
)

print(
    ranked[
        [
            "date",
            "records",
            "minimum_poa",
            "maximum_poa",
            "negative_below_minus7",
            "above_1500",
            "above_3000",
            "abnormal_count"
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.2f}"
    )
)


# ============================================================
# SAVE OUTPUTS
# ============================================================

daily.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_may_june_july_daily_poa_summary.csv"
    ),
    index=False
)

negative_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_days_poa_below_minus7.csv"
    ),
    index=False
)

high_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_days_poa_above_1500.csv"
    ),
    index=False
)

extreme_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_days_poa_above_3000.csv"
    ),
    index=False
)

abnormal_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_abnormal_poa_days.csv"
    ),
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 80)
print("SUMMARY")
print("=" * 80)

print(
    f"\nDays with POA < -7 W/m² : "
    f"{len(negative_days)}"
)

print(
    f"Days with POA > 1500 W/m² : "
    f"{len(high_days)}"
)

print(
    f"Days with POA > 3000 W/m² : "
    f"{len(extreme_days)}"
)

print(
    f"Days with any abnormal POA : "
    f"{len(abnormal_days)}"
)

print(
    f"Dates with NO POA_IRRADIANCE column : "
    f"{len(no_poa_dates)}"
)

print(
    f"Files with NO POA_IRRADIANCE column : "
    f"{len(no_poa_df)}"
)

print("\nOutput files saved to:")
print(OUTPUT_DIR)

print("\nAnalysis complete.")