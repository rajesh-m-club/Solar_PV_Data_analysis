import os
import glob
import json
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = (
    r"C:\Users\rajes\solar_PV_project"
    r"\csv_data\system_id=10\year=2022"
)

OUTPUT_DIR = (
    r"C:\Users\rajes\solar_PV_project"
    r"\2022_asset_analysis\outputs"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

ABNORMAL_JSON = os.path.join(
    OUTPUT_DIR,
    "2022_abnormal_days.json"
)

DATE_COLUMN = "measured_on"


# ============================================================
# ENTITIES AND HARD BOUNDARIES
# ============================================================

LIMITS = {

    "poa_irradiance__421": (-10, 1550),

    "dc_power__422": (-20, 1650),

    "ac_power__423": (-10, 1300),

    "dc_pos_voltage__424": (-2, 325),

    "dc_pos_current__425": (-0.2, 8.0),

    "ac_voltage__426": (114, 126),

    "ac_current__427": (1.5, 11.0),

    "ambient_temp__428": (-30, 42),

    "module_temp_1__429": (-30, 75),

    "module_temp_2__430": (-30, 75),

    "module_temp_3__431": (-30, 75),

    "inverter_temp__432": (-30, 65),

    "das_temp__433": (-25, 55),

    "das_battery_voltage__434": (12.4, 14.5)
}


ENTITIES = list(
    LIMITS.keys()
)


# ============================================================
# LOAD ALL CSV FILES
# ============================================================

def load_data():

    csv_files = glob.glob(
        os.path.join(
            BASE_DIR,
            "**",
            "*.csv"
        ),
        recursive=True
    )

    if not csv_files:

        raise FileNotFoundError(
            f"No CSV files found in:\n{BASE_DIR}"
        )

    print(
        f"Found {len(csv_files)} CSV files."
    )

    frames = []

    for file in csv_files:

        print(
            f"Reading: {file}"
        )

        try:

            df = pd.read_csv(
                file
            )

            frames.append(
                df
            )

        except Exception as e:

            print(
                f"ERROR reading {file}: {e}"
            )

    if not frames:

        raise RuntimeError(
            "No CSV files could be loaded."
        )

    data = pd.concat(
        frames,
        ignore_index=True
    )

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

    # --------------------------------------------------------
    # Remove invalid timestamps
    # --------------------------------------------------------

    invalid_timestamp_count = (
        df[DATE_COLUMN].isna().sum()
    )

    if invalid_timestamp_count > 0:

        print(
            f"Removing "
            f"{invalid_timestamp_count:,} rows "
            f"with invalid measured_on."
        )

        df = df.dropna(
            subset=[DATE_COLUMN]
        ).copy()

    # --------------------------------------------------------
    # Keep only 2022
    # --------------------------------------------------------

    df = df[
        df[DATE_COLUMN].dt.year == 2022
    ].copy()

    # --------------------------------------------------------
    # Create calendar date
    # --------------------------------------------------------

    df["date"] = (
        df[DATE_COLUMN]
        .dt.strftime("%Y-%m-%d")
    )

    # --------------------------------------------------------
    # Convert entity columns to numeric
    # --------------------------------------------------------

    for entity in ENTITIES:

        if entity in df.columns:

            df[entity] = pd.to_numeric(
                df[entity],
                errors="coerce"
            )

        else:

            print(
                f"WARNING: Missing column: {entity}"
            )

    # --------------------------------------------------------
    # Sort chronologically
    # --------------------------------------------------------

    df = df.sort_values(
        DATE_COLUMN
    ).reset_index(
        drop=True
    )

    return df


# ============================================================
# INITIALIZE ABNORMAL-DAY STRUCTURE
# ============================================================

def initialize_abnormal_days():

    return {
        entity: set()
        for entity in ENTITIES
    }


# ============================================================
# CHECK POINT-WISE HARD LIMITS
# ============================================================

def check_limits(
    df,
    abnormal_days
):

    print(
        "\nChecking point-wise limits..."
    )

    for entity, (
        lower,
        upper
    ) in LIMITS.items():

        if entity not in df.columns:

            print(
                f"Skipping missing column: "
                f"{entity}"
            )

            continue

        values = df[entity]

        # ----------------------------------------------------
        # POA NaN / missing
        #
        # Your rule specifically says:
        # NaN or missing = abnormal
        # ----------------------------------------------------

        if entity == "poa_irradiance__421":

            missing_mask = (
                values.isna()
            )

            missing_dates = df.loc[
                missing_mask,
                "date"
            ].unique()

            abnormal_days[
                entity
            ].update(
                missing_dates
            )

        # ----------------------------------------------------
        # Lower boundary
        # ----------------------------------------------------

        below_lower_mask = (
            values < lower
        )

        below_lower_dates = df.loc[
            below_lower_mask,
            "date"
        ].unique()

        abnormal_days[
            entity
        ].update(
            below_lower_dates
        )

        # ----------------------------------------------------
        # Upper boundary
        # ----------------------------------------------------

        above_upper_mask = (
            values > upper
        )

        above_upper_dates = df.loc[
            above_upper_mask,
            "date"
        ].unique()

        abnormal_days[
            entity
        ].update(
            above_upper_dates
        )


# ============================================================
# CHECK DAILY MEAN POWER
# ============================================================

def check_daily_mean_power(
    df,
    abnormal_days
):

    print(
        "\nChecking daily mean power..."
    )

    # ========================================================
    # DC POWER
    #
    # Daily mean DC power must be >= 100 W
    #
    # Mean DC power < 100 W = abnormal
    # ========================================================

    dc_entity = "dc_power__422"

    if dc_entity in df.columns:

        dc_daily_mean = (
            df.groupby("date")[
                dc_entity
            ]
            .mean()
            .reset_index()
        )

        dc_abnormal_mask = (
            dc_daily_mean[
                dc_entity
            ] < 100
        )

        dc_abnormal_dates = (
            dc_daily_mean.loc[
                dc_abnormal_mask,
                "date"
            ].unique()
        )

        abnormal_days[
            dc_entity
        ].update(
            dc_abnormal_dates
        )

    # ========================================================
    # AC POWER
    #
    # Daily mean AC power must be > 50 W
    #
    # Mean AC power <= 50 W = abnormal
    # ========================================================

    ac_entity = "ac_power__423"

    if ac_entity in df.columns:

        ac_daily_mean = (
            df.groupby("date")[
                ac_entity
            ]
            .mean()
            .reset_index()
        )

        ac_abnormal_mask = (
            ac_daily_mean[
                ac_entity
            ] <= 50
        )

        ac_abnormal_dates = (
            ac_daily_mean.loc[
                ac_abnormal_mask,
                "date"
            ].unique()
        )

        abnormal_days[
            ac_entity
        ].update(
            ac_abnormal_dates
        )


# ============================================================
# SAVE ABNORMAL-DAY JSON
# ============================================================

def save_abnormal_days(
    abnormal_days
):

    output = {}

    for entity in ENTITIES:

        output[entity] = {
            "abnormal_days": sorted(
                abnormal_days[entity]
            )
        }

    with open(
        ABNORMAL_JSON,
        "w"
    ) as f:

        json.dump(
            output,
            f,
            indent=4
        )


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(
    abnormal_days
):

    print("\n")
    print("=" * 80)
    print(
        "ABNORMAL DAY SEPARATION SUMMARY"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # Entity-wise abnormal days
    # --------------------------------------------------------

    for entity in ENTITIES:

        dates = sorted(
            abnormal_days[entity]
        )

        print("\n" + "-" * 80)

        print(
            f"Entity: {entity}"
        )

        print(
            f"Abnormal days: {len(dates)}"
        )

        if dates:

            print(
                ", ".join(dates)
            )

    # --------------------------------------------------------
    # UNIQUE ABNORMAL CALENDAR DAYS
    #
    # If the same date is abnormal for multiple entities,
    # it is counted ONLY ONCE.
    # --------------------------------------------------------

    all_abnormal_days = set()

    for entity in ENTITIES:

        all_abnormal_days.update(
            abnormal_days[entity]
        )

    all_abnormal_days = sorted(
        all_abnormal_days
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print("\n")
    print("=" * 80)
    print(
        "OVERALL 2022 ABNORMAL DAYS"
    )
    print("=" * 80)

    print(
        f"Total unique abnormal days: "
        f"{len(all_abnormal_days)}"
    )

    if all_abnormal_days:

        print("\nUnique abnormal dates:")

        for date in all_abnormal_days:

            print(
                f"    {date}"
            )

    print("=" * 80)
# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "2022 PVDAQ ABNORMAL-DAY SEPARATION"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    df = load_data()

    print(
        f"\nTotal rows loaded: "
        f"{len(df):,}"
    )

    # --------------------------------------------------------
    # PREPARE
    # --------------------------------------------------------

    df = prepare_data(
        df
    )

    print(
        f"\nRows belonging to 2022: "
        f"{len(df):,}"
    )

    if df.empty:

        raise RuntimeError(
            "No 2022 data found."
        )

    print(
        f"Date range: "
        f"{df['date'].min()} "
        f"→ "
        f"{df['date'].max()}"
    )

    print(
        f"Number of dates: "
        f"{df['date'].nunique()}"
    )

    # --------------------------------------------------------
    # INITIALIZE
    # --------------------------------------------------------

    abnormal_days = (
        initialize_abnormal_days()
    )

    # --------------------------------------------------------
    # 1. POINT-WISE HARD LIMITS
    # --------------------------------------------------------

    check_limits(
        df,
        abnormal_days
    )

    # --------------------------------------------------------
    # 2. DAILY MEAN POWER RULES
    # --------------------------------------------------------

    check_daily_mean_power(
        df,
        abnormal_days
    )

    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    save_abnormal_days(
        abnormal_days
    )

    # --------------------------------------------------------
    # PRINT SUMMARY
    # --------------------------------------------------------

    print_summary(
        abnormal_days
    )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print("\n")
    print("=" * 80)
    print(
        "ABNORMAL-DAY SEPARATION COMPLETE"
    )
    print("=" * 80)

    print(
        f"\nOutput file:"
        f"\n{ABNORMAL_JSON}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
