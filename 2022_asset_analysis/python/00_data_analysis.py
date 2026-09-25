import os
import glob
import json
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\rajes\solar_PV_project\csv_data\system_id=10\year=2022"

OUTPUT_DIR = r"C:\Users\rajes\solar_PV_project\2022_asset_analysis\outputs"

ABNORMAL_JSON = os.path.join(
    OUTPUT_DIR,
    "2022_abnormal_days.json"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# COLUMN CONFIGURATION
# ============================================================

DATE_COLUMN = "measured_on"

ID_COLUMN = "system_id"


ENTITIES = [
    "ac_power__423",
    "ac_current__427",
    "ac_voltage__426",

    "ambient_temp__428",

    "das_battery_voltage__434",
    "das_temp__433",

    "dc_pos_current__425",
    "dc_pos_voltage__424",
    "dc_power__422",

    "inverter_temp__432",

    "module_temp_1__429",
    "module_temp_2__430",
    "module_temp_3__431",

    "poa_irradiance__421"
]


# ============================================================
# LOAD ABNORMAL-DAY JSON
# ============================================================

def load_abnormal_days(json_path):

    if not os.path.exists(json_path):

        print("WARNING: abnormal_days.json not found.")
        print("All days will be treated as normal.")

        return {
            entity: []
            for entity in ENTITIES
        }

    with open(json_path, "r") as f:
        data = json.load(f)

    abnormal_days = {}

    for entity in ENTITIES:

        if entity in data:

            abnormal_days[entity] = set(
                data[entity].get("abnormal_days", [])
            )

        else:

            abnormal_days[entity] = set()

    return abnormal_days


# ============================================================
# LOAD ALL CSV FILES
# ============================================================

def load_data():

    csv_files = glob.glob(
        os.path.join(BASE_DIR, "**", "*.csv"),
        recursive=True
    )

    if not csv_files:

        raise FileNotFoundError(
            f"No CSV files found inside:\n{BASE_DIR}"
        )

    print(f"Found {len(csv_files)} CSV files.")

    dataframes = []

    for file in csv_files:

        print(f"Reading: {file}")

        try:

            df = pd.read_csv(file)

            dataframes.append(df)

        except Exception as e:

            print(f"ERROR reading {file}: {e}")

    if not dataframes:

        raise RuntimeError("No CSV files could be loaded.")

    data = pd.concat(
        dataframes,
        ignore_index=True
    )

    print(f"\nTotal rows loaded: {len(data):,}")

    return data


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(df):

    # --------------------------------------------------------
    # Convert measured_on to datetime
    # --------------------------------------------------------

    df[DATE_COLUMN] = pd.to_datetime(
        df[DATE_COLUMN],
        errors="coerce"
    )

    # Remove invalid timestamps

    invalid_dates = df[DATE_COLUMN].isna().sum()

    if invalid_dates > 0:

        print(
            f"Removing {invalid_dates:,} rows "
            f"with invalid measured_on."
        )

        df = df.dropna(
            subset=[DATE_COLUMN]
        )

    # --------------------------------------------------------
    # Keep only 2022
    # --------------------------------------------------------

    df = df[
        df[DATE_COLUMN].dt.year == 2022
    ].copy()

    # --------------------------------------------------------
    # Create date column
    # --------------------------------------------------------

    df["date"] = df[DATE_COLUMN].dt.date

    # Convert entity columns to numeric

    for column in ENTITIES:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

        else:

            print(
                f"WARNING: Column missing: {column}"
            )

    # Sort chronologically

    df = df.sort_values(
        DATE_COLUMN
    ).reset_index(drop=True)

    return df


# ============================================================
# CREATE WEEK NUMBER
# ============================================================

def add_week_information(df):

    # Week is based on the calendar year.
    #
    # Monday = beginning of week.
    #
    # We use a custom week number starting from the first
    # day of 2022 so that the output contains approximately
    # 52-53 weeks depending on the calendar/data coverage.

    first_date = pd.Timestamp("2022-01-01")

    df["week_number"] = (
        (
            pd.to_datetime(df["date"])
            - first_date
        ).dt.days // 7
    ) + 1

    return df


# ============================================================
# DAILY STATISTICS
# ============================================================

def calculate_daily_statistics(df, entity):

    daily = (
        df.groupby("date")[entity]
        .agg(
            mean="mean",
            min="min",
            max="max",
            count="count"
        )
        .reset_index()
    )

    return daily


# ============================================================
# WEEKLY NORMAL ANALYSIS
# ============================================================

def analyze_normal_days(df, entity, abnormal_dates):

    # --------------------------------------------------------
    # Create daily abnormal flag
    # --------------------------------------------------------

    daily = calculate_daily_statistics(
        df,
        entity
    )

    daily["is_abnormal"] = (
        daily["date"]
        .astype(str)
        .isin(abnormal_dates)
    )

    # --------------------------------------------------------
    # Add week number to daily data
    # --------------------------------------------------------

    daily["week_number"] = (
        (
            pd.to_datetime(daily["date"])
            - pd.Timestamp("2022-01-01")
        ).dt.days // 7
    ) + 1

    # --------------------------------------------------------
    # Weekly analysis
    # --------------------------------------------------------

    weekly_results = []

    for week_number, week_df in daily.groupby(
        "week_number"
    ):

        total_days = len(week_df)

        abnormal_df = week_df[
            week_df["is_abnormal"]
        ]

        normal_df = week_df[
            ~week_df["is_abnormal"]
        ]

        abnormal_days = len(abnormal_df)

        normal_days = len(normal_df)

        abnormal_percentage = (
            abnormal_days / total_days * 100
            if total_days > 0
            else 0
        )

        # ----------------------------------------------------
        # Normal-day statistics
        # ----------------------------------------------------

        if normal_days > 0:

            normal_mean = normal_df["mean"].mean()

            normal_min = normal_df["min"].min()

            normal_max = normal_df["max"].max()

        else:

            normal_mean = np.nan
            normal_min = np.nan
            normal_max = np.nan

        weekly_results.append({

            "week": int(week_number),

            "start_date": str(
                week_df["date"].min()
            ),

            "end_date": str(
                week_df["date"].max()
            ),

            "total_days": total_days,

            "normal_days": normal_days,

            "abnormal_days": abnormal_days,

            "abnormal_percentage":
                abnormal_percentage,

            "normal_mean":
                normal_mean,

            "normal_min":
                normal_min,

            "normal_max":
                normal_max
        })

    return pd.DataFrame(
        weekly_results
    )


# ============================================================
# ABNORMAL-DAY ANALYSIS
# ============================================================

def analyze_abnormal_days(
    df,
    entity,
    abnormal_dates
):

    daily = calculate_daily_statistics(
        df,
        entity
    )

    daily["date"] = (
        daily["date"]
        .astype(str)
    )

    abnormal_df = daily[
        daily["date"].isin(abnormal_dates)
    ].copy()

    abnormal_df = abnormal_df.sort_values(
        "date"
    )

    return abnormal_df


# ============================================================
# ENTITY ANALYSIS
# ============================================================

def analyze_entity(
    df,
    entity,
    abnormal_dates
):

    print("\n")
    print("=" * 80)
    print(f"ENTITY: {entity}")
    print("=" * 80)

    # --------------------------------------------------------
    # Weekly normal analysis
    # --------------------------------------------------------

    weekly = analyze_normal_days(
        df,
        entity,
        abnormal_dates
    )

    print("\nNORMAL DAYS — WEEKLY ANALYSIS")
    print("-" * 80)

    print(
        weekly.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Abnormal-day analysis
    # --------------------------------------------------------

    abnormal = analyze_abnormal_days(
        df,
        entity,
        abnormal_dates
    )

    print("\nABNORMAL DAYS")
    print("-" * 80)

    if abnormal.empty:

        print("No abnormal days.")

    else:

        print(
            abnormal.to_string(
                index=False
            )
        )

    return weekly, abnormal


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("2022 PVDAQ ANALYSIS")
    print("=" * 80)

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    df = load_data()

    # --------------------------------------------------------
    # Prepare data
    # --------------------------------------------------------

    df = prepare_data(df)

    print(
        f"\nRows after preparation: {len(df):,}"
    )

    print(
        f"Date range: "
        f"{df['date'].min()} → {df['date'].max()}"
    )

    # --------------------------------------------------------
    # Load abnormal-day information
    # --------------------------------------------------------

    abnormal_days = load_abnormal_days(
        ABNORMAL_JSON
    )

    # --------------------------------------------------------
    # Run analysis entity by entity
    # --------------------------------------------------------

    all_weekly = {}
    all_abnormal = {}

    for entity in ENTITIES:

        if entity not in df.columns:

            print(
                f"\nSkipping missing column: {entity}"
            )

            continue

        weekly, abnormal = analyze_entity(
            df,
            entity,
            abnormal_days.get(
                entity,
                set()
            )
        )

        all_weekly[entity] = weekly

        all_abnormal[entity] = abnormal

        # ----------------------------------------------------
        # Save weekly analysis
        # ----------------------------------------------------

        safe_name = entity.replace(
            "__",
            "_"
        )

        weekly_file = os.path.join(
            OUTPUT_DIR,
            f"{safe_name}_weekly.csv"
        )

        weekly.to_csv(
            weekly_file,
            index=False
        )

        # ----------------------------------------------------
        # Save abnormal analysis
        # ----------------------------------------------------

        abnormal_file = os.path.join(
            OUTPUT_DIR,
            f"{safe_name}_abnormal_days.csv"
        )

        abnormal.to_csv(
            abnormal_file,
            index=False
        )

    print("\n")
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    print(
        f"\nResults saved to:\n{OUTPUT_DIR}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()