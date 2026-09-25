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
# EXPECTED PVDAQ METRICS
# ============================================================

METRICS = {
    421: "poa_irradiance",
    422: "dc_power",
    423: "ac_power",
    424: "dc_pos_voltage",
    425: "dc_pos_current",
    426: "ac_voltage",
    427: "ac_current",
    428: "ambient_temp",
    429: "module_temp_1",
    430: "module_temp_2",
    431: "module_temp_3",
    432: "inverter_temp",
    433: "das_temp",
    434: "das_battery_voltage",
}

# ============================================================
# FIND ALL CSV FILES
# ============================================================

csv_files = glob.glob(
    os.path.join(BASE_DIR, "**", "*.csv"),
    recursive=True
)

print("=" * 70)
print("SOLAR PV SYSTEM 10 - 2022 DATA INVENTORY")
print("=" * 70)

print(f"\nBase directory:")
print(BASE_DIR)

print(f"\nCSV files found: {len(csv_files)}")

if len(csv_files) == 0:
    raise FileNotFoundError(
        "No CSV files were found. Check BASE_DIR."
    )

# ============================================================
# STORAGE
# ============================================================

all_data = []

monthly_summary = []

# ============================================================
# READ FILES
# ============================================================

for i, file in enumerate(sorted(csv_files), start=1):

    try:
        df = pd.read_csv(file)

        # ----------------------------------------------------
        # Extract year/month/day from folder structure
        # ----------------------------------------------------

        path_parts = os.path.normpath(file).split(os.sep)

        year = None
        month = None
        day = None

        for part in path_parts:

            if part.startswith("year="):
                year = int(part.split("=")[1])

            elif part.startswith("month="):
                month = int(part.split("=")[1])

            elif part.startswith("day="):
                day = int(part.split("=")[1])

        # ----------------------------------------------------
        # Find timestamp column
        # ----------------------------------------------------

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
            print(f"\nWARNING: No timestamp column found:")
            print(file)
            continue

        # ----------------------------------------------------
        # Convert timestamp
        # ----------------------------------------------------

        df[timestamp_col] = pd.to_datetime(
            df[timestamp_col],
            errors="coerce"
        )

        # ----------------------------------------------------
        # Basic file statistics
        # ----------------------------------------------------

        records = len(df)

        invalid_timestamps = df[timestamp_col].isna().sum()

        duplicate_timestamps = df[timestamp_col].duplicated().sum()

        first_timestamp = df[timestamp_col].min()

        last_timestamp = df[timestamp_col].max()

        # ----------------------------------------------------
        # Sampling interval
        # ----------------------------------------------------

        valid_times = (
            df[timestamp_col]
            .dropna()
            .sort_values()
            .drop_duplicates()
        )

        if len(valid_times) > 1:

            time_diffs = (
                valid_times
                .diff()
                .dropna()
                .dt.total_seconds()
            )

            median_interval = time_diffs.median()

            min_interval = time_diffs.min()

            max_interval = time_diffs.max()

            gaps_over_1min = (time_diffs > 60).sum()

            gaps_over_5min = (time_diffs > 300).sum()

            gaps_over_1hour = (time_diffs > 3600).sum()

        else:

            median_interval = np.nan
            min_interval = np.nan
            max_interval = np.nan
            gaps_over_1min = np.nan
            gaps_over_5min = np.nan
            gaps_over_1hour = np.nan

        # ----------------------------------------------------
        # Missing values
        # ----------------------------------------------------

        total_missing = df.isna().sum().sum()

        # ----------------------------------------------------
        # Metric columns present
        # ----------------------------------------------------

        available_metrics = []

        for metric_id, metric_name in METRICS.items():

            possible_names = [
                f"{metric_name}__{metric_id}",
                metric_name,
                str(metric_id)
            ]

            found = False

            for name in possible_names:
                if name in df.columns:
                    found = True
                    break

            if found:
                available_metrics.append(metric_name)

        # ----------------------------------------------------
        # Save file-level summary
        # ----------------------------------------------------

        monthly_summary.append({
            "year": year,
            "month": month,
            "day": day,
            "file": os.path.basename(file),
            "records": records,
            "invalid_timestamps": invalid_timestamps,
            "duplicate_timestamps": duplicate_timestamps,
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
            "median_interval_seconds": median_interval,
            "minimum_interval_seconds": min_interval,
            "maximum_interval_seconds": max_interval,
            "gaps_over_1min": gaps_over_1min,
            "gaps_over_5min": gaps_over_5min,
            "gaps_over_1hour": gaps_over_1hour,
            "missing_values": total_missing,
            "metrics_found": len(available_metrics),
        })

        # ----------------------------------------------------
        # Keep data for overall analysis
        # ----------------------------------------------------

        df["_source_file"] = os.path.basename(file)
        df["_year"] = year
        df["_month"] = month
        df["_day"] = day

        all_data.append(df)

        print(
            f"[{i:4d}/{len(csv_files)}] "
            f"{year}-{month:02d}-{day:02d} | "
            f"{records:5d} records | "
            f"metrics={len(available_metrics):2d}"
        )

    except Exception as e:

        print("\nERROR reading:")
        print(file)
        print("Reason:", e)

# ============================================================
# COMBINE FILE SUMMARIES
# ============================================================

summary_df = pd.DataFrame(monthly_summary)

summary_df = summary_df.sort_values(
    ["year", "month", "day"]
)

# ============================================================
# COMBINE ALL DATA
# ============================================================

print("\nCombining all 2022 data...")

data = pd.concat(
    all_data,
    ignore_index=True
)

# ============================================================
# FIND TIMESTAMP COLUMN
# ============================================================

timestamp_candidates = [
    "measured_on",
    "timestamp",
    "time",
    "datetime",
    "date"
]

TIMESTAMP_COL = None

for col in timestamp_candidates:

    if col in data.columns:
        TIMESTAMP_COL = col
        break

if TIMESTAMP_COL is None:
    raise ValueError("Timestamp column not found.")

# ============================================================
# SORT BY TIME
# ============================================================

data = data.sort_values(
    TIMESTAMP_COL
).reset_index(drop=True)

# ============================================================
# OVERALL TIMESTAMP ANALYSIS
# ============================================================

timestamps = (
    data[TIMESTAMP_COL]
    .dropna()
    .sort_values()
)

unique_timestamps = timestamps.drop_duplicates()

total_records = len(data)

valid_timestamp_count = len(timestamps)

unique_timestamp_count = len(unique_timestamps)

duplicate_timestamp_count = (
    valid_timestamp_count -
    unique_timestamp_count
)

first_timestamp = timestamps.min()

last_timestamp = timestamps.max()

# ============================================================
# OVERALL SAMPLING INTERVAL
# ============================================================

time_diffs = (
    unique_timestamps
    .diff()
    .dropna()
    .dt.total_seconds()
)

median_interval = time_diffs.median()

mean_interval = time_diffs.mean()

minimum_interval = time_diffs.min()

maximum_interval = time_diffs.max()

gaps_over_1min = (time_diffs > 60).sum()

gaps_over_5min = (time_diffs > 300).sum()

gaps_over_10min = (time_diffs > 600).sum()

gaps_over_1hour = (time_diffs > 3600).sum()

# ============================================================
# EXPECTED 1-MINUTE SAMPLES
# ============================================================

expected_minutes = (
    (last_timestamp - first_timestamp)
    .total_seconds() / 60
) + 1

expected_minutes = int(expected_minutes)

missing_from_continuous_range = (
    expected_minutes -
    unique_timestamp_count
)

# ============================================================
# DATA QUALITY
# ============================================================

total_missing_values = data.isna().sum().sum()

missing_by_column = (
    data.isna()
    .sum()
    .sort_values(ascending=False)
)

# ============================================================
# MONTHLY SUMMARY
# ============================================================

monthly_records = (
    data.groupby("_month")
    .size()
    .reset_index(name="records")
)

monthly_days = (
    data.groupby("_month")["_day"]
    .nunique()
    .reset_index(name="active_days")
)

monthly_summary_simple = pd.merge(
    monthly_records,
    monthly_days,
    on="_month",
    how="outer"
)

monthly_summary_simple = monthly_summary_simple.sort_values(
    "_month"
)

# ============================================================
# DAILY RECORD COUNT
# ============================================================

daily_summary = (
    data.groupby(
        ["_year", "_month", "_day"]
    )
    .size()
    .reset_index(name="records")
)

# ============================================================
# PRINT RESULTS
# ============================================================

print("\n")
print("=" * 70)
print("OVERALL 2022 DATASET")
print("=" * 70)

print(f"\nTotal records:")
print(total_records)

print(f"\nValid timestamps:")
print(valid_timestamp_count)

print(f"\nUnique timestamps:")
print(unique_timestamp_count)

print(f"\nDuplicate timestamps:")
print(duplicate_timestamp_count)

print(f"\nFirst timestamp:")
print(first_timestamp)

print(f"\nLast timestamp:")
print(last_timestamp)

print("\nSampling interval:")
print(f"Median : {median_interval:.2f} seconds")
print(f"Mean   : {mean_interval:.2f} seconds")
print(f"Minimum: {minimum_interval:.2f} seconds")
print(f"Maximum: {maximum_interval:.2f} seconds")

print("\nTimestamp gaps:")
print(f"> 1 minute : {gaps_over_1min}")
print(f"> 5 minutes: {gaps_over_5min}")
print(f"> 10 minutes: {gaps_over_10min}")
print(f"> 1 hour   : {gaps_over_1hour}")

print("\nExpected continuous 1-minute samples:")
print(expected_minutes)

print("\nMissing samples relative to continuous range:")
print(missing_from_continuous_range)

print("\nTotal missing values:")
print(total_missing_values)

# ============================================================
# MONTHLY RESULTS
# ============================================================

print("\n")
print("=" * 70)
print("MONTHLY DATA COVERAGE")
print("=" * 70)

print(
    monthly_summary_simple.to_string(
        index=False
    )
)

# ============================================================
# DAILY RECORD STATISTICS
# ============================================================

print("\n")
print("=" * 70)
print("DAILY RECORD STATISTICS")
print("=" * 70)

print(
    daily_summary["records"].describe()
)

# ============================================================
# METRIC AVAILABILITY
# ============================================================

print("\n")
print("=" * 70)
print("METRIC AVAILABILITY")
print("=" * 70)

for metric_id, metric_name in METRICS.items():

    possible_names = [
        f"{metric_name}__{metric_id}",
        metric_name,
        str(metric_id)
    ]

    found_column = None

    for name in possible_names:

        if name in data.columns:
            found_column = name
            break

    if found_column:

        missing = data[found_column].isna().sum()

        print(
            f"{metric_id:3d} | "
            f"{metric_name:25s} | "
            f"FOUND | "
            f"missing={missing}"
        )

    else:

        print(
            f"{metric_id:3d} | "
            f"{metric_name:25s} | "
            f"NOT FOUND"
        )

# ============================================================
# SAVE OUTPUTS
# ============================================================

summary_file = os.path.join(
    OUTPUT_DIR,
    "2022_file_inventory.csv"
)

monthly_file = os.path.join(
    OUTPUT_DIR,
    "2022_monthly_coverage.csv"
)

daily_file = os.path.join(
    OUTPUT_DIR,
    "2022_daily_record_counts.csv"
)

missing_file = os.path.join(
    OUTPUT_DIR,
    "2022_missing_values_by_column.csv"
)

summary_df.to_csv(
    summary_file,
    index=False
)

monthly_summary_simple.to_csv(
    monthly_file,
    index=False
)

daily_summary.to_csv(
    daily_file,
    index=False
)

missing_by_column.to_csv(
    missing_file,
    header=["missing_values"]
)

# ============================================================
# SAVE TEXT REPORT
# ============================================================

report_file = os.path.join(
    OUTPUT_DIR,
    "2022_data_quality_report.txt"
)

with open(
    report_file,
    "w",
    encoding="utf-8"
) as f:

    f.write("SOLAR PV SYSTEM 10 - 2022 DATA QUALITY REPORT\n")
    f.write("=" * 60 + "\n\n")

    f.write(f"Total records: {total_records}\n")
    f.write(f"Valid timestamps: {valid_timestamp_count}\n")
    f.write(f"Unique timestamps: {unique_timestamp_count}\n")
    f.write(f"Duplicate timestamps: {duplicate_timestamp_count}\n\n")

    f.write(f"First timestamp: {first_timestamp}\n")
    f.write(f"Last timestamp: {last_timestamp}\n\n")

    f.write(
        f"Median sampling interval: "
        f"{median_interval:.2f} seconds\n"
    )

    f.write(
        f"Mean sampling interval: "
        f"{mean_interval:.2f} seconds\n"
    )

    f.write(
        f"Minimum sampling interval: "
        f"{minimum_interval:.2f} seconds\n"
    )

    f.write(
        f"Maximum sampling interval: "
        f"{maximum_interval:.2f} seconds\n\n"
    )

    f.write(
        f"Gaps > 1 minute: {gaps_over_1min}\n"
    )

    f.write(
        f"Gaps > 5 minutes: {gaps_over_5min}\n"
    )

    f.write(
        f"Gaps > 10 minutes: {gaps_over_10min}\n"
    )

    f.write(
        f"Gaps > 1 hour: {gaps_over_1hour}\n\n"
    )

    f.write(
        f"Expected continuous 1-minute samples: "
        f"{expected_minutes}\n"
    )

    f.write(
        f"Missing samples from continuous range: "
        f"{missing_from_continuous_range}\n\n"
    )

    f.write(
        f"Total missing values: "
        f"{total_missing_values}\n"
    )

print("\n")
print("=" * 70)
print("OUTPUT FILES CREATED")
print("=" * 70)

print(summary_file)
print(monthly_file)
print(daily_file)
print(missing_file)
print(report_file)

print("\nInventory and data-quality analysis completed.")