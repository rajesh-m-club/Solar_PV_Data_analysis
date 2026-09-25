# ============================================================
# 07_ac_power_negative_near_zero_analysis.py
#
# Solar PV Plant Performance & Asset Management Analysis
#
# Metric:
#   423 = AC Power
#
# Purpose:
#   Identify days with:
#       1. Any negative AC power
#       2. Negative AC power dominated operation
#       3. Negative-or-near-zero AC power dominated operation
#       4. Maximum AC power below 10 W
#       5. Maximum AC power below 100 W
#
# Also updates the central JSON file:
#
#   2022_abnormal_days.json
#
# The JSON file can contain results from multiple metrics.
# This script updates ONLY the "ac_power" section.
#
# ============================================================


import os
import glob
import json
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\rajes\solar_PV_project\csv_data\system_id=10\year=2022"

OUTPUT_DIR = r"C:\Users\rajes\solar_PV_project\2022_asset_analysis\outputs"

# Central abnormal-days JSON file
JSON_FILE = os.path.join(
    OUTPUT_DIR,
    "2022_abnormal_days.json"
)

# ------------------------------------------------------------
# Dataset information
# ------------------------------------------------------------

SYSTEM_ID = 10
YEAR = 2022

METRIC_ID = 423
METRIC_NAME = "AC Power"
UNIT = "W"

TIMESTAMP_COLUMN = "measured_on"

# ------------------------------------------------------------
# Analysis thresholds
# ------------------------------------------------------------

# AC power between 0 and this value is considered near-zero
NEAR_ZERO_THRESHOLD_W = 10.0

# Percentage required for a day to be considered dominated
DOMINATED_PERCENTAGE = 80.0

# Minimum number of valid AC samples required
MINIMUM_VALID_SAMPLES = 100

# Maximum-power thresholds
MAX_POWER_BELOW_10W = 10.0
MAX_POWER_BELOW_100W = 100.0


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_ac_power_column(df):
    """
    Find the AC power column.

    Primary identification:
        metric ID 423

    Several possible naming conventions are supported.
    """

    possible_columns = [
        "423",
        "metric_423",
        "423_ac_power",
        "ac_power",
        "AC_POWER",
        "acPower",
        "AC Power",
    ]

    for col in possible_columns:
        if col in df.columns:
            return col

    # Search more generally for column names containing 423
    for col in df.columns:
        col_str = str(col).lower()

        if "423" in col_str:
            return col

    # Search for AC + power
    for col in df.columns:
        col_str = str(col).lower()

        if "ac" in col_str and "power" in col_str:
            return col

    return None


def clean_for_json(value):
    """
    Convert NumPy/Pandas values into JSON-safe Python values.
    """

    if value is None:
        return None

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        value = float(value)

        if np.isnan(value) or np.isinf(value):
            return None

        return value

    if isinstance(value, (np.bool_,)):
        return bool(value)

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return None

    return value


def clean_dict_for_json(data):
    """
    Recursively convert dictionary/list values
    into JSON-safe values.
    """

    if isinstance(data, dict):
        return {
            str(key): clean_dict_for_json(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [
            clean_dict_for_json(value)
            for value in data
        ]

    return clean_for_json(data)


def load_existing_json():
    """
    Load existing abnormal-days JSON.

    If it does not exist, create the base structure.

    Existing metric results are preserved.
    """

    if not os.path.exists(JSON_FILE):

        print("\nJSON file does not exist.")
        print("Creating new abnormal-days JSON file.")

        return {
            "project": "Solar PV Plant Performance & Asset Management Analysis",
            "system_id": SYSTEM_ID,
            "year": YEAR,
            "abnormal_days": {}
        }

    print("\nExisting JSON file found:")
    print(JSON_FILE)

    try:

        with open(JSON_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    except json.JSONDecodeError as e:

        raise RuntimeError(
            f"\nERROR: Existing JSON file is invalid.\n"
            f"File: {JSON_FILE}\n"
            f"Error: {e}\n"
            f"\nPlease fix or remove the JSON file before running."
        )

    # Ensure required top-level fields exist
    data.setdefault(
        "project",
        "Solar PV Plant Performance & Asset Management Analysis"
    )

    data.setdefault("system_id", SYSTEM_ID)
    data.setdefault("year", YEAR)

    if "abnormal_days" not in data:
        data["abnormal_days"] = {}

    return data


def save_json_atomically(data):
    """
    Save JSON safely.

    A temporary file is written first and then replaced.
    This prevents leaving a partially written JSON file
    if something goes wrong during writing.
    """

    data = clean_dict_for_json(data)

    temp_fd, temp_path = tempfile.mkstemp(
        suffix=".json",
        dir=OUTPUT_DIR
    )

    try:

        with os.fdopen(
            temp_fd,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        os.replace(temp_path, JSON_FILE)

    except Exception:

        if os.path.exists(temp_path):
            os.remove(temp_path)

        raise


# ============================================================
# FIND ALL CSV FILES
# ============================================================

print("=" * 70)
print("AC POWER NEGATIVE / NEAR-ZERO ANALYSIS")
print("=" * 70)

print("\nDataset directory:")
print(BASE_DIR)

csv_pattern = os.path.join(
    BASE_DIR,
    "month=*",
    "day=*",
    "*.csv"
)

csv_files = sorted(
    glob.glob(csv_pattern)
)

print("\nCSV files found:", len(csv_files))


if len(csv_files) == 0:

    raise FileNotFoundError(
        "\nNo CSV files were found.\n"
        f"Checked:\n{csv_pattern}"
    )


# ============================================================
# DAILY RESULTS STORAGE
# ============================================================

daily_results = []

file_problems = []


# ============================================================
# PROCESS EVERY CSV
# ============================================================

for file_path in csv_files:

    try:

        df = pd.read_csv(file_path)

    except Exception as e:

        file_problems.append({
            "file": file_path,
            "problem": f"CSV read error: {str(e)}"
        })

        continue


    # --------------------------------------------------------
    # Timestamp check
    # --------------------------------------------------------

    if TIMESTAMP_COLUMN not in df.columns:

        file_problems.append({
            "file": file_path,
            "problem": f"Missing timestamp column: {TIMESTAMP_COLUMN}"
        })

        continue


    # --------------------------------------------------------
    # Find AC power column
    # --------------------------------------------------------

    ac_column = find_ac_power_column(df)

    if ac_column is None:

        file_problems.append({
            "file": file_path,
            "problem": "AC power metric 423 not found"
        })

        continue


    # --------------------------------------------------------
    # Convert timestamp
    # --------------------------------------------------------

    df[TIMESTAMP_COLUMN] = pd.to_datetime(
        df[TIMESTAMP_COLUMN],
        errors="coerce"
    )

    # Remove invalid timestamps
    df = df.dropna(
        subset=[TIMESTAMP_COLUMN]
    ).copy()

    if len(df) == 0:
        continue


    # --------------------------------------------------------
    # Convert AC power to numeric
    # --------------------------------------------------------

    df["ac_power_W"] = pd.to_numeric(
        df[ac_column],
        errors="coerce"
    )


    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    df["date"] = df[TIMESTAMP_COLUMN].dt.date


    # ========================================================
    # DAILY ANALYSIS
    # ========================================================

    for date_value, day_df in df.groupby("date"):

        power = day_df["ac_power_W"].dropna()

        valid_samples = len(power)

        if valid_samples < MINIMUM_VALID_SAMPLES:
            continue


        # ----------------------------------------------------
        # Basic statistics
        # ----------------------------------------------------

        negative_mask = power < 0

        near_zero_mask = (
            (power >= 0)
            &
            (power < NEAR_ZERO_THRESHOLD_W)
        )

        negative_or_near_zero_mask = (
            power < NEAR_ZERO_THRESHOLD_W
        )

        meaningful_power_mask = (
            power >= NEAR_ZERO_THRESHOLD_W
        )


        negative_samples = int(
            negative_mask.sum()
        )

        near_zero_samples = int(
            near_zero_mask.sum()
        )

        negative_or_near_zero_samples = int(
            negative_or_near_zero_mask.sum()
        )

        meaningful_samples = int(
            meaningful_power_mask.sum()
        )


        # ----------------------------------------------------
        # Percentages
        # ----------------------------------------------------

        negative_percentage = (
            negative_samples
            / valid_samples
            * 100.0
        )

        near_zero_percentage = (
            near_zero_samples
            / valid_samples
            * 100.0
        )

        below_10W_percentage = (
            negative_or_near_zero_samples
            / valid_samples
            * 100.0
        )

        meaningful_percentage = (
            meaningful_samples
            / valid_samples
            * 100.0
        )


        # ----------------------------------------------------
        # Energy
        #
        # Uses actual timestamps.
        #
        # This is kept consistent with the previous analysis.
        # ----------------------------------------------------

        day_df_sorted = day_df.sort_values(
            TIMESTAMP_COLUMN
        ).copy()

        valid_energy_df = (
            day_df_sorted[
                day_df_sorted["ac_power_W"].notna()
            ]
            .copy()
        )

        energy_kWh = 0.0

        if len(valid_energy_df) >= 2:

            timestamps = (
                valid_energy_df[TIMESTAMP_COLUMN]
                .astype("int64")
                .to_numpy()
                / 1e9
            )

            power_values = (
                valid_energy_df["ac_power_W"]
                .to_numpy(dtype=float)
            )

            dt_seconds = np.diff(
                timestamps
            )

            # Trapezoidal integration
            energy_Wh = np.sum(
                (
                    power_values[:-1]
                    + power_values[1:]
                )
                / 2.0
                * dt_seconds
                / 3600.0
            )

            energy_kWh = (
                energy_Wh / 1000.0
            )


        # ----------------------------------------------------
        # Store daily result
        # ----------------------------------------------------

        daily_results.append({

            "date": str(date_value),

            "valid_samples": int(valid_samples),

            "negative_samples": int(
                negative_samples
            ),

            "negative_percentage": float(
                negative_percentage
            ),

            "near_zero_samples": int(
                near_zero_samples
            ),

            "near_zero_percentage": float(
                near_zero_percentage
            ),

            "negative_or_near_zero_samples": int(
                negative_or_near_zero_samples
            ),

            "below_10W_percentage": float(
                below_10W_percentage
            ),

            "meaningful_samples": int(
                meaningful_samples
            ),

            "meaningful_percentage": float(
                meaningful_percentage
            ),

            "mean_power_W": float(
                power.mean()
            ),

            "median_power_W": float(
                power.median()
            ),

            "minimum_power_W": float(
                power.min()
            ),

            "maximum_power_W": float(
                power.max()
            ),

            "energy_kWh": float(
                energy_kWh
            )
        })


# ============================================================
# CREATE DAILY DATAFRAME
# ============================================================

daily_df = pd.DataFrame(
    daily_results
)

if daily_df.empty:

    raise RuntimeError(
        "\nNo valid daily AC-power results were generated."
    )


daily_df = daily_df.sort_values(
    "date"
).reset_index(drop=True)


# ============================================================
# CREATE ALL ANOMALY DATAFRAMES
#
# IMPORTANT:
# These are created BEFORE the JSON section.
#
# This prevents the previous:
#
# NameError:
# negative_dominated_df is not defined
#
# ============================================================


# ------------------------------------------------------------
# 1. ANY NEGATIVE AC POWER
# ------------------------------------------------------------

negative_days = daily_df[
    daily_df["negative_samples"] > 0
].copy()


# ------------------------------------------------------------
# 2. ANY NEAR-ZERO AC POWER
# ------------------------------------------------------------

near_zero_days = daily_df[
    daily_df["near_zero_samples"] > 0
].copy()


# ------------------------------------------------------------
# 3. NEGATIVE DOMINATED
# ------------------------------------------------------------

negative_dominated_df = daily_df[
    daily_df["negative_percentage"]
    >= DOMINATED_PERCENTAGE
].copy()


# ------------------------------------------------------------
# 4. NEAR-ZERO DOMINATED
# ------------------------------------------------------------

near_zero_dominated_df = daily_df[
    daily_df["near_zero_percentage"]
    >= DOMINATED_PERCENTAGE
].copy()


# ------------------------------------------------------------
# 5. NEGATIVE OR NEAR-ZERO DOMINATED
# ------------------------------------------------------------

dominated_days = daily_df[
    daily_df["below_10W_percentage"]
    >= DOMINATED_PERCENTAGE
].copy()


# ------------------------------------------------------------
# 6. MAXIMUM POWER BELOW 10 W
# ------------------------------------------------------------

max_below_10_df = daily_df[
    daily_df["maximum_power_W"]
    < MAX_POWER_BELOW_10W
].copy()


# ------------------------------------------------------------
# 7. MAXIMUM POWER BELOW 100 W
# ------------------------------------------------------------

low_generation_days = daily_df[
    daily_df["maximum_power_W"]
    < MAX_POWER_BELOW_100W
].copy()


# ============================================================
# SAVE DAILY COMPLETE ANALYSIS
# ============================================================

daily_csv = os.path.join(
    OUTPUT_DIR,
    "2022_ac_power_daily_analysis.csv"
)

daily_df.to_csv(
    daily_csv,
    index=False
)


# ============================================================
# SAVE INDIVIDUAL CSV FILES
# ============================================================

negative_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_ac_power_negative_days.csv"
    ),
    index=False
)


near_zero_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_ac_power_near_zero_days.csv"
    ),
    index=False
)


negative_dominated_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_ac_power_negative_dominated_days.csv"
    ),
    index=False
)


dominated_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_ac_power_negative_near_zero_dominated_days.csv"
    ),
    index=False
)


max_below_10_df.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_ac_power_max_below_10W_days.csv"
    ),
    index=False
)


low_generation_days.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "2022_ac_power_low_generation_days.csv"
    ),
    index=False
)


# ============================================================
# JSON RECORD CREATION
# ============================================================

# ------------------------------------------------------------
# Negative dominated days
# ------------------------------------------------------------

negative_dominated_records = []

for _, row in negative_dominated_df.iterrows():

    negative_dominated_records.append({

        "date": str(row["date"]),

        "negative_percentage": float(
            row["negative_percentage"]
        ),

        "negative_samples": int(
            row["negative_samples"]
        ),

        "valid_samples": int(
            row["valid_samples"]
        ),

        "mean_power_W": float(
            row["mean_power_W"]
        ),

        "median_power_W": float(
            row["median_power_W"]
        ),

        "minimum_power_W": float(
            row["minimum_power_W"]
        ),

        "maximum_power_W": float(
            row["maximum_power_W"]
        ),

        "energy_kWh": float(
            row["energy_kWh"]
        )
    })


# ------------------------------------------------------------
# Negative OR near-zero dominated days
# ------------------------------------------------------------

negative_or_near_zero_records = []

for _, row in dominated_days.iterrows():

    negative_or_near_zero_records.append({

        "date": str(row["date"]),

        "below_10W_percentage": float(
            row["below_10W_percentage"]
        ),

        "negative_percentage": float(
            row["negative_percentage"]
        ),

        "negative_samples": int(
            row["negative_samples"]
        ),

        "valid_samples": int(
            row["valid_samples"]
        ),

        "mean_power_W": float(
            row["mean_power_W"]
        ),

        "median_power_W": float(
            row["median_power_W"]
        ),

        "minimum_power_W": float(
            row["minimum_power_W"]
        ),

        "maximum_power_W": float(
            row["maximum_power_W"]
        ),

        "energy_kWh": float(
            row["energy_kWh"]
        )
    })


# ------------------------------------------------------------
# Maximum power below 10 W
# ------------------------------------------------------------

max_below_10_records = []

for _, row in max_below_10_df.iterrows():

    max_below_10_records.append({

        "date": str(row["date"]),

        "maximum_power_W": float(
            row["maximum_power_W"]
        ),

        "mean_power_W": float(
            row["mean_power_W"]
        ),

        "median_power_W": float(
            row["median_power_W"]
        ),

        "minimum_power_W": float(
            row["minimum_power_W"]
        ),

        "energy_kWh": float(
            row["energy_kWh"]
        )
    })


# ------------------------------------------------------------
# Low generation days
# ------------------------------------------------------------

low_generation_records = []

for _, row in low_generation_days.iterrows():

    low_generation_records.append({

        "date": str(row["date"]),

        "maximum_power_W": float(
            row["maximum_power_W"]
        ),

        "mean_power_W": float(
            row["mean_power_W"]
        ),

        "median_power_W": float(
            row["median_power_W"]
        ),

        "minimum_power_W": float(
            row["minimum_power_W"]
        ),

        "energy_kWh": float(
            row["energy_kWh"]
        )
    })


# ------------------------------------------------------------
# ANY NEGATIVE DAYS
# ------------------------------------------------------------

any_negative_records = []

for _, row in negative_days.iterrows():

    any_negative_records.append({

        "date": str(row["date"]),

        "negative_percentage": float(
            row["negative_percentage"]
        ),

        "negative_samples": int(
            row["negative_samples"]
        ),

        "valid_samples": int(
            row["valid_samples"]
        )
    })


# ------------------------------------------------------------
# ANY NEAR-ZERO DAYS
# ------------------------------------------------------------

any_near_zero_records = []

for _, row in near_zero_days.iterrows():

    any_near_zero_records.append({

        "date": str(row["date"]),

        "near_zero_percentage": float(
            row["near_zero_percentage"]
        ),

        "near_zero_samples": int(
            row["near_zero_samples"]
        ),

        "valid_samples": int(
            row["valid_samples"]
        )
    })


# ============================================================
# LOAD EXISTING CENTRAL JSON
# ============================================================

json_data = load_existing_json()


# ============================================================
# UPDATE ONLY AC POWER SECTION
#
# Any existing POA/DC/etc. sections remain untouched.
# ============================================================

json_data["abnormal_days"]["ac_power"] = {

    "metric_id": METRIC_ID,

    "metric_name": METRIC_NAME,

    "unit": UNIT,

    "analysis_parameters": {

        "near_zero_threshold_W": (
            NEAR_ZERO_THRESHOLD_W
        ),

        "dominated_percentage": (
            DOMINATED_PERCENTAGE
        ),

        "minimum_valid_samples": (
            MINIMUM_VALID_SAMPLES
        ),

        "negative_condition": (
            "P < 0 W"
        ),

        "near_zero_condition": (
            "0 <= P < 10 W"
        ),

        "negative_or_near_zero_condition": (
            "P < 10 W"
        ),

        "low_generation_condition": (
            "maximum AC power < 100 W"
        )
    },

    "negative_dominated_days":
        negative_dominated_records,

    "negative_or_near_zero_dominated_days":
        negative_or_near_zero_records,

    "max_power_below_10W_days":
        max_below_10_records,

    "low_generation_days":
        low_generation_records,

    "any_negative_days":
        any_negative_records,

    "any_near_zero_days":
        any_near_zero_records
}


# ============================================================
# ADD UPDATE INFORMATION
# ============================================================

json_data["last_updated"] = datetime.now().isoformat(
    timespec="seconds"
)


# ============================================================
# SAVE CENTRAL JSON
# ============================================================

save_json_atomically(
    json_data
)


# ============================================================
# SUMMARY TEXT FILE
# ============================================================

summary_file = os.path.join(
    OUTPUT_DIR,
    "2022_ac_power_negative_near_zero_summary.txt"
)


with open(
    summary_file,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "AC POWER NEGATIVE / NEAR-ZERO ANALYSIS\n"
    )

    f.write(
        "=" * 60 + "\n\n"
    )

    f.write(
        f"System ID: {SYSTEM_ID}\n"
    )

    f.write(
        f"Year: {YEAR}\n"
    )

    f.write(
        f"Metric ID: {METRIC_ID}\n"
    )

    f.write(
        f"Metric: {METRIC_NAME}\n"
    )

    f.write(
        f"Unit: {UNIT}\n\n"
    )

    f.write(
        f"Days analyzed: {len(daily_df)}\n"
    )

    f.write(
        f"Days with any negative AC power: "
        f"{len(negative_days)}\n"
    )

    f.write(
        f"Days with any near-zero AC power: "
        f"{len(near_zero_days)}\n"
    )

    f.write(
        f"Negative-power dominated days "
        f"({DOMINATED_PERCENTAGE:.0f}%): "
        f"{len(negative_dominated_df)}\n"
    )

    f.write(
        f"Negative-or-near-zero dominated days "
        f"({DOMINATED_PERCENTAGE:.0f}%): "
        f"{len(dominated_days)}\n"
    )

    f.write(
        f"Days maximum AC power < 10 W: "
        f"{len(max_below_10_df)}\n"
    )

    f.write(
        f"Days maximum AC power < 100 W: "
        f"{len(low_generation_days)}\n"
    )

    f.write(
        f"Files/data problems: "
        f"{len(file_problems)}\n\n"
    )


    # --------------------------------------------------------
    # Negative dominated
    # --------------------------------------------------------

    f.write(
        "\nNEGATIVE-POWER DOMINATED DAYS\n"
    )

    f.write(
        "-" * 60 + "\n"
    )

    for _, row in negative_dominated_df.iterrows():

        f.write(
            f"{row['date']} | "
            f"{row['negative_percentage']:.2f}% negative | "
            f"{int(row['negative_samples'])}/"
            f"{int(row['valid_samples'])} samples | "
            f"mean={row['mean_power_W']:.3f} W | "
            f"median={row['median_power_W']:.3f} W | "
            f"min={row['minimum_power_W']:.3f} W | "
            f"max={row['maximum_power_W']:.3f} W | "
            f"energy={row['energy_kWh']:.6f} kWh\n"
        )


    # --------------------------------------------------------
    # Negative or near-zero dominated
    # --------------------------------------------------------

    f.write(
        "\nNEGATIVE-OR-NEAR-ZERO DOMINATED DAYS\n"
    )

    f.write(
        "-" * 60 + "\n"
    )

    for _, row in dominated_days.iterrows():

        f.write(
            f"{row['date']} | "
            f"{row['below_10W_percentage']:.2f}% below 10 W | "
            f"{row['negative_percentage']:.2f}% negative | "
            f"mean={row['mean_power_W']:.3f} W | "
            f"max={row['maximum_power_W']:.3f} W | "
            f"energy={row['energy_kWh']:.6f} kWh\n"
        )


    # --------------------------------------------------------
    # Max < 10 W
    # --------------------------------------------------------

    f.write(
        "\nDAYS WITH MAXIMUM AC POWER < 10 W\n"
    )

    f.write(
        "-" * 60 + "\n"
    )

    for _, row in max_below_10_df.iterrows():

        f.write(
            f"{row['date']} | "
            f"max={row['maximum_power_W']:.3f} W | "
            f"mean={row['mean_power_W']:.3f} W | "
            f"energy={row['energy_kWh']:.6f} kWh\n"
        )


    # --------------------------------------------------------
    # Max < 100 W
    # --------------------------------------------------------

    f.write(
        "\nDAYS WITH MAXIMUM AC POWER < 100 W\n"
    )

    f.write(
        "-" * 60 + "\n"
    )

    for _, row in low_generation_days.iterrows():

        f.write(
            f"{row['date']} | "
            f"max={row['maximum_power_W']:.3f} W | "
            f"mean={row['mean_power_W']:.3f} W | "
            f"energy={row['energy_kWh']:.6f} kWh\n"
        )


    # --------------------------------------------------------
    # Problems
    # --------------------------------------------------------

    if file_problems:

        f.write(
            "\nFILE / DATA PROBLEMS\n"
        )

        f.write(
            "-" * 60 + "\n"
        )

        for problem in file_problems:

            f.write(
                f"{problem['file']} | "
                f"{problem['problem']}\n"
            )


# ============================================================
# PRINT FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)

print(
    f"\nDays analyzed: "
    f"{len(daily_df)}"
)

print(
    f"Days with any negative AC power: "
    f"{len(negative_days)}"
)

print(
    f"Days with any near-zero AC power: "
    f"{len(near_zero_days)}"
)

print(
    f"Negative-power dominated days "
    f"({DOMINATED_PERCENTAGE:.0f}%): "
    f"{len(negative_dominated_df)}"
)

print(
    f"Negative-or-near-zero dominated days "
    f"({DOMINATED_PERCENTAGE:.0f}%): "
    f"{len(dominated_days)}"
)

print(
    f"Days maximum AC power < 10 W: "
    f"{len(max_below_10_df)}"
)

print(
    f"Days maximum AC power < 100 W: "
    f"{len(low_generation_days)}"
)

print(
    f"File/data problems: "
    f"{len(file_problems)}"
)


# ============================================================
# PRINT NEGATIVE DOMINATED DAYS
# ============================================================

print(
    "\nNEGATIVE-POWER DOMINATED DAYS"
)

print(
    "-" * 70
)

for _, row in negative_dominated_df.iterrows():

    print(
        f"{row['date']} | "
        f"{row['negative_percentage']:.2f}% negative | "
        f"{int(row['negative_samples'])}/"
        f"{int(row['valid_samples'])} | "
        f"mean={row['mean_power_W']:.3f} W | "
        f"max={row['maximum_power_W']:.3f} W | "
        f"energy={row['energy_kWh']:.6f} kWh"
    )


# ============================================================
# OUTPUT FILES
# ============================================================

print("\nOUTPUT FILES")
print("-" * 70)

print(
    "\nDaily analysis:"
)
print(daily_csv)

print(
    "\nCentral abnormal-days JSON:"
)
print(JSON_FILE)

print(
    "\nSummary:"
)
print(summary_file)

print(
    "\nIndividual anomaly CSV files saved in:"
)
print(OUTPUT_DIR)

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)