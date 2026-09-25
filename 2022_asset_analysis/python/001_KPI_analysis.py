import os
import glob
import json
import numpy as np
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

ABNORMAL_JSON = os.path.join(
    OUTPUT_DIR,
    "2022_abnormal_days.json"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# IMPORTANT:
# ENTER ACTUAL RATED AC CAPACITY OF THE PV PLANT
# ============================================================

RATED_AC_CAPACITY_KW = 1.12


# ============================================================
# COLUMN NAMES
# ============================================================

DATE_COLUMN = "measured_on"

POA_COLUMN = "poa_irradiance__421"
DC_POWER_COLUMN = "dc_power__422"
AC_POWER_COLUMN = "ac_power__423"


# ============================================================
# CONSTANTS
# ============================================================

W_TO_KW = 1000.0
SECONDS_PER_HOUR = 3600.0


# ============================================================
# LOAD DATA
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
        f"\nFound {len(csv_files)} CSV files."
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

    return pd.concat(
        frames,
        ignore_index=True
    )


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(df):

    required_columns = [
        DATE_COLUMN,
        POA_COLUMN,
        DC_POWER_COLUMN,
        AC_POWER_COLUMN
    ]

    for column in required_columns:

        if column not in df.columns:

            raise KeyError(
                f"Required column missing: {column}"
            )

    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    df[DATE_COLUMN] = pd.to_datetime(
        df[DATE_COLUMN],
        errors="coerce"
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
    # Numeric conversion
    # --------------------------------------------------------

    for column in [
        POA_COLUMN,
        DC_POWER_COLUMN,
        AC_POWER_COLUMN
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Date information
    # --------------------------------------------------------

    df["date"] = (
        df[DATE_COLUMN]
        .dt.normalize()
    )

    df["year"] = (
        df[DATE_COLUMN]
        .dt.year
    )

    df["month"] = (
        df[DATE_COLUMN]
        .dt.month
    )

    df["month_name"] = (
        df[DATE_COLUMN]
        .dt.strftime("%B")
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    df = df.sort_values(
        DATE_COLUMN
    ).reset_index(
        drop=True
    )

    # --------------------------------------------------------
    # Actual timestamp interval
    # --------------------------------------------------------

    df["next_timestamp"] = (
        df[DATE_COLUMN]
        .shift(-1)
    )

    df["interval_hours"] = (
        df["next_timestamp"]
        - df[DATE_COLUMN]
    ).dt.total_seconds() / SECONDS_PER_HOUR

    # --------------------------------------------------------
    # Don't integrate across midnight
    # --------------------------------------------------------

    current_date = (
        df[DATE_COLUMN]
        .dt.date
    )

    next_date = (
        df["next_timestamp"]
        .dt.date
    )

    same_day = (
        current_date == next_date
    )

    df.loc[
        ~same_day,
        "interval_hours"
    ] = np.nan

    # --------------------------------------------------------
    # Remove invalid intervals
    # --------------------------------------------------------

    df.loc[
        df["interval_hours"] <= 0,
        "interval_hours"
    ] = np.nan

    return df


# ============================================================
# LOAD ABNORMAL JSON
# ============================================================

def load_abnormal_days():

    if not os.path.exists(
        ABNORMAL_JSON
    ):

        raise FileNotFoundError(
            f"Abnormal JSON not found:\n"
            f"{ABNORMAL_JSON}"
        )

    with open(
        ABNORMAL_JSON,
        "r"
    ) as f:

        return json.load(
            f
        )


# ============================================================
# BUILD NORMAL / ABNORMAL DAY SETS
# ============================================================

def build_day_groups(
    df,
    abnormal_data
):

    # --------------------------------------------------------
    # Overall abnormal days
    #
    # IMPORTANT:
    # If the same date occurs under multiple entities,
    # it is counted ONLY ONCE here.
    # --------------------------------------------------------

    all_abnormal_days = set()

    for entity_data in abnormal_data.values():

        for date in entity_data.get(
            "abnormal_days",
            []
        ):

            all_abnormal_days.add(
                pd.Timestamp(
                    date
                ).normalize()
            )

    # --------------------------------------------------------
    # All days present in data
    # --------------------------------------------------------

    all_data_days = set(
        df["date"].unique()
    )

    # --------------------------------------------------------
    # Normal days
    # --------------------------------------------------------

    normal_days = (
        all_data_days
        -
        all_abnormal_days
    )

    return (
        all_data_days,
        normal_days,
        all_abnormal_days
    )


# ============================================================
# ENERGY
# ============================================================

def calculate_energy(group):

    dc_energy = (
        group[DC_POWER_COLUMN]
        *
        group["interval_hours"]
    ).sum() / W_TO_KW

    ac_energy = (
        group[AC_POWER_COLUMN]
        *
        group["interval_hours"]
    ).sum() / W_TO_KW

    return (
        dc_energy,
        ac_energy
    )


# ============================================================
# POA IRRADIATION
# ============================================================

def calculate_irradiation(group):

    return (
        group[POA_COLUMN]
        *
        group["interval_hours"]
    ).sum() / W_TO_KW


# ============================================================
# DC -> AC EFFICIENCY
# ============================================================

def calculate_efficiency(
    dc_energy,
    ac_energy
):

    if (
        pd.isna(dc_energy)
        or
        dc_energy <= 0
    ):

        return np.nan

    return (
        ac_energy
        /
        dc_energy
        *
        100.0
    )


# ============================================================
# IRRADIANCE-POWER CHARACTERISTICS
# ============================================================

def calculate_irradiance_metrics(group):

    valid = group[
        [
            POA_COLUMN,
            DC_POWER_COLUMN,
            AC_POWER_COLUMN
        ]
    ].dropna()

    if len(valid) < 2:

        return {

            "irradiance_dc_correlation":
                np.nan,

            "irradiance_ac_correlation":
                np.nan,

            "dc_power_per_irradiance":
                np.nan,

            "ac_power_per_irradiance":
                np.nan,

            "peak_poa_irradiance":
                np.nan,

            "peak_dc_power":
                np.nan,

            "peak_ac_power":
                np.nan
        }

    # --------------------------------------------------------
    # POA vs DC correlation
    # --------------------------------------------------------

    dc_corr = (
        valid[POA_COLUMN]
        .corr(
            valid[DC_POWER_COLUMN]
        )
    )

    # --------------------------------------------------------
    # POA vs AC correlation
    # --------------------------------------------------------

    ac_corr = (
        valid[POA_COLUMN]
        .corr(
            valid[AC_POWER_COLUMN]
        )
    )

    # --------------------------------------------------------
    # Positive irradiance response
    # --------------------------------------------------------

    positive = valid[
        valid[POA_COLUMN] > 0
    ]

    if not positive.empty:

        dc_response = (
            positive[DC_POWER_COLUMN]
            /
            positive[POA_COLUMN]
        ).median()

        ac_response = (
            positive[AC_POWER_COLUMN]
            /
            positive[POA_COLUMN]
        ).median()

    else:

        dc_response = np.nan
        ac_response = np.nan

    return {

        "irradiance_dc_correlation":
            dc_corr,

        "irradiance_ac_correlation":
            ac_corr,

        "dc_power_per_irradiance":
            dc_response,

        "ac_power_per_irradiance":
            ac_response,

        "peak_poa_irradiance":
            valid[POA_COLUMN].max(),

        "peak_dc_power":
            valid[DC_POWER_COLUMN].max(),

        "peak_ac_power":
            valid[AC_POWER_COLUMN].max()
    }


# ============================================================
# ANALYZE SELECTED DAYS
# ============================================================

def analyze_group(
    df,
    selected_days
):

    if not selected_days:
        return None

    selected_days = set(
        pd.Timestamp(day).normalize()
        for day in selected_days
    )

    group = df[
        df["date"].isin(
            selected_days
        )
    ].copy()

    if group.empty:
        return None

    # --------------------------------------------------------
    # Energy
    # --------------------------------------------------------

    dc_energy, ac_energy = (
        calculate_energy(
            group
        )
    )

    # --------------------------------------------------------
    # POA irradiation
    # --------------------------------------------------------

    poa_energy = (
        calculate_irradiation(
            group
        )
    )

    # --------------------------------------------------------
    # DC -> AC efficiency
    # --------------------------------------------------------

    efficiency = (
        calculate_efficiency(
            dc_energy,
            ac_energy
        )
    )

    # --------------------------------------------------------
    # Capacity factor
    # --------------------------------------------------------

    number_of_days = len(
        selected_days
    )

    theoretical_energy = (
        RATED_AC_CAPACITY_KW
        *
        24.0
        *
        number_of_days
    )

    if theoretical_energy > 0:

        capacity_factor = (
            ac_energy
            /
            theoretical_energy
            *
            100.0
        )

    else:

        capacity_factor = np.nan

    # --------------------------------------------------------
    # Mean values
    # --------------------------------------------------------

    mean_dc = group[
        DC_POWER_COLUMN
    ].mean()

    mean_ac = group[
        AC_POWER_COLUMN
    ].mean()

    mean_poa = group[
        POA_COLUMN
    ].mean()

    # --------------------------------------------------------
    # Maximum values
    # --------------------------------------------------------

    max_dc = group[
        DC_POWER_COLUMN
    ].max()

    max_ac = group[
        AC_POWER_COLUMN
    ].max()

    max_poa = group[
        POA_COLUMN
    ].max()

    # --------------------------------------------------------
    # Irradiance characteristics
    # --------------------------------------------------------

    irr = calculate_irradiance_metrics(
        group
    )

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    result = {

        "days":
            number_of_days,

        "samples":
            len(group),

        "dc_energy_kwh":
            dc_energy,

        "ac_energy_kwh":
            ac_energy,

        "poa_irradiation_kwh_m2":
            poa_energy,

        "capacity_factor_percent":
            capacity_factor,

        "dc_to_ac_efficiency_percent":
            efficiency,

        "mean_dc_power_w":
            mean_dc,

        "mean_ac_power_w":
            mean_ac,

        "mean_poa_irradiance_w_m2":
            mean_poa,

        "max_dc_power_w":
            max_dc,

        "max_ac_power_w":
            max_ac,

        "max_poa_irradiance_w_m2":
            max_poa
    }

    result.update(
        irr
    )

    return result


# ============================================================
# PRINT KPI RESULT
# ============================================================

def print_kpis(
    result,
    title,
    normal_days=None,
    abnormal_days=None
):

    print("\n")
    print("=" * 80)
    print(title)
    print("=" * 80)

    if normal_days is not None:

        print(
            f"Normal days       : {normal_days}"
        )

    if abnormal_days is not None:

        print(
            f"Abnormal days     : {abnormal_days}"
        )

    if result is None:

        print(
            "No data available."
        )

        return

    print(
        f"Days              : "
        f"{result['days']}"
    )

    print(
        f"Samples           : "
        f"{result['samples']:,}"
    )

    print(
        f"DC Energy         : "
        f"{result['dc_energy_kwh']:.3f} kWh"
    )

    print(
        f"AC Energy         : "
        f"{result['ac_energy_kwh']:.3f} kWh"
    )

    print(
        f"POA Irradiation   : "
        f"{result['poa_irradiation_kwh_m2']:.3f} kWh/m²"
    )

    print(
        f"Capacity Factor   : "
        f"{result['capacity_factor_percent']:.3f} %"
    )

    print(
        f"DC-AC Efficiency  : "
        f"{result['dc_to_ac_efficiency_percent']:.3f} %"
    )

    print(
        f"Mean DC Power     : "
        f"{result['mean_dc_power_w']:.3f} W"
    )

    print(
        f"Mean AC Power     : "
        f"{result['mean_ac_power_w']:.3f} W"
    )

    print(
        f"Mean POA          : "
        f"{result['mean_poa_irradiance_w_m2']:.3f} W/m²"
    )

    print(
        f"Max DC Power      : "
        f"{result['max_dc_power_w']:.3f} W"
    )

    print(
        f"Max AC Power      : "
        f"{result['max_ac_power_w']:.3f} W"
    )

    print(
        f"Max POA           : "
        f"{result['max_poa_irradiance_w_m2']:.3f} W/m²"
    )

    print(
        f"POA-DC Corr.      : "
        f"{result['irradiance_dc_correlation']:.4f}"
    )

    print(
        f"POA-AC Corr.      : "
        f"{result['irradiance_ac_correlation']:.4f}"
    )

    print(
        f"DC/POA Response   : "
        f"{result['dc_power_per_irradiance']:.6f}"
    )

    print(
        f"AC/POA Response   : "
        f"{result['ac_power_per_irradiance']:.6f}"
    )


# ============================================================
# MONTHLY ANALYSIS
# ============================================================

def analyze_monthly(
    df,
    normal_days,
    abnormal_days,
    print_output=True
):

    results = []

    for month in range(1, 13):

        # ----------------------------------------------------
        # Days in this month
        # ----------------------------------------------------

        month_all_days = set(
            df.loc[
                df["month"] == month,
                "date"
            ].unique()
        )

        month_normal_days = (
            month_all_days
            &
            normal_days
        )

        month_abnormal_days = (
            month_all_days
            &
            abnormal_days
        )

        month_name = pd.Timestamp(
            2022,
            month,
            1
        ).strftime("%B")

        # ----------------------------------------------------
        # MONTH HEADER
        # ----------------------------------------------------

        if print_output:

            print("\n\n")
            print("#" * 80)

            print(
                f"MONTH {month:02d} - "
                f"{month_name.upper()}"
            )

            print("#" * 80)

            print(
                f"Total days        : "
                f"{len(month_all_days)}"
            )

            print(
                f"Normal days       : "
                f"{len(month_normal_days)}"
            )

            print(
                f"Abnormal days     : "
                f"{len(month_abnormal_days)}"
            )

        # ----------------------------------------------------
        # NORMAL ANALYSIS
        # ----------------------------------------------------

        normal_result = analyze_group(
            df,
            month_normal_days
        )

        if normal_result is not None:

            normal_result["month"] = month

            normal_result[
                "month_name"
            ] = month_name

            normal_result[
                "normal_days"
            ] = len(
                month_normal_days
            )

            normal_result[
                "abnormal_days"
            ] = len(
                month_abnormal_days
            )

            normal_result[
                "population"
            ] = "normal"

            results.append(
                normal_result
            )

        if print_output:

            print_kpis(
                normal_result,
                "NORMAL DAYS",
                normal_days=len(
                    month_normal_days
                ),
                abnormal_days=len(
                    month_abnormal_days
                )
            )

        # ----------------------------------------------------
        # ABNORMAL ANALYSIS
        # ----------------------------------------------------

        abnormal_result = analyze_group(
            df,
            month_abnormal_days
        )

        if abnormal_result is not None:

            abnormal_result["month"] = month

            abnormal_result[
                "month_name"
            ] = month_name

            abnormal_result[
                "normal_days"
            ] = len(
                month_normal_days
            )

            abnormal_result[
                "abnormal_days"
            ] = len(
                month_abnormal_days
            )

            abnormal_result[
                "population"
            ] = "abnormal"

            results.append(
                abnormal_result
            )

        if print_output:

            print_kpis(
                abnormal_result,
                "ABNORMAL DAYS",
                normal_days=len(
                    month_normal_days
                ),
                abnormal_days=len(
                    month_abnormal_days
                )
            )

    return pd.DataFrame(
        results
    )


# ============================================================
# YEARLY NORMAL / ABNORMAL ANALYSIS
# ============================================================

def analyze_yearly(
    df,
    normal_days,
    abnormal_days
):

    print("\n\n")

    print("#" * 80)

    print(
        "2022 YEARLY ANALYSIS"
    )

    print("#" * 80)

    total_days = (
        normal_days
        |
        abnormal_days
    )

    print(
        f"Total days        : "
        f"{len(total_days)}"
    )

    print(
        f"Normal days       : "
        f"{len(normal_days)}"
    )

    print(
        f"Abnormal days     : "
        f"{len(abnormal_days)}"
    )

    print(
        f"Normal + abnormal : "
        f"{len(normal_days) + len(abnormal_days)}"
    )

    # --------------------------------------------------------
    # NORMAL
    # --------------------------------------------------------

    normal_result = analyze_group(
        df,
        normal_days
    )

    print_kpis(
        normal_result,
        "2022 NORMAL DAYS",
        normal_days=len(normal_days),
        abnormal_days=len(abnormal_days)
    )

    # --------------------------------------------------------
    # ABNORMAL
    # --------------------------------------------------------

    abnormal_result = analyze_group(
        df,
        abnormal_days
    )

    print_kpis(
        abnormal_result,
        "2022 ABNORMAL DAYS",
        normal_days=len(normal_days),
        abnormal_days=len(abnormal_days)
    )

    # --------------------------------------------------------
    # Save yearly results
    # --------------------------------------------------------

    yearly_rows = []

    if normal_result is not None:

        normal_result["population"] = "normal"

        normal_result[
            "normal_days"
        ] = len(normal_days)

        normal_result[
            "abnormal_days"
        ] = len(abnormal_days)

        yearly_rows.append(
            normal_result
        )

    if abnormal_result is not None:

        abnormal_result["population"] = "abnormal"

        abnormal_result[
            "normal_days"
        ] = len(normal_days)

        abnormal_result[
            "abnormal_days"
        ] = len(abnormal_days)

        yearly_rows.append(
            abnormal_result
        )

    return pd.DataFrame(
        yearly_rows
    )


# ============================================================
# ABNORMAL ENTITY-WISE ANALYSIS
# ============================================================

def analyze_abnormal_entities(
    df,
    abnormal_data
):

    print("\n\n")

    print("=" * 80)

    print(
        "ABNORMAL ENTITY-WISE ANALYSIS"
    )

    print("=" * 80)

    entity_output_dir = os.path.join(
        OUTPUT_DIR,
        "abnormal_entity_analysis"
    )

    os.makedirs(
        entity_output_dir,
        exist_ok=True
    )

    # ========================================================
    # EACH ENTITY
    # ========================================================

    for entity, entity_data in (
        abnormal_data.items()
    ):

        dates = entity_data.get(
            "abnormal_days",
            []
        )

        # ----------------------------------------------------
        # Unique abnormal dates for this entity
        # ----------------------------------------------------

        entity_days = set()

        for date in dates:

            entity_days.add(
                pd.Timestamp(
                    date
                ).normalize()
            )

        print("\n\n")

        print("*" * 80)

        print(
            f"ENTITY: {entity}"
        )

        print(
            f"Total abnormal days: "
            f"{len(entity_days)}"
        )

        print("*" * 80)

        if not entity_days:

            print(
                "No abnormal days for this entity."
            )

            continue

        # ----------------------------------------------------
        # Monthly entity analysis
        # ----------------------------------------------------

        monthly_rows = []

        for month in range(1, 13):

            month_entity_days = set(
                df.loc[
                    df["month"] == month,
                    "date"
                ].unique()
            )

            month_entity_days &= (
                entity_days
            )

            if not month_entity_days:

                continue

            result = analyze_group(
                df,
                month_entity_days
            )

            if result is None:

                continue

            month_name = pd.Timestamp(
                2022,
                month,
                1
            ).strftime("%B")

            print("\n")

            print("-" * 80)

            print(
                f"{entity} - "
                f"{month_name.upper()}"
            )

            print("-" * 80)

            print(
                f"Abnormal days: "
                f"{len(month_entity_days)}"
            )

            print_kpis(
                result,
                f"{entity} - {month_name}"
            )

            result["month"] = month

            result[
                "month_name"
            ] = month_name

            result[
                "abnormal_days"
            ] = len(
                month_entity_days
            )

            result[
                "population"
            ] = "abnormal"

            result[
                "entity"
            ] = entity

            monthly_rows.append(
                result
            )

        # ----------------------------------------------------
        # Yearly entity analysis
        # ----------------------------------------------------

        yearly_result = analyze_group(
            df,
            entity_days
        )

        print("\n")

        print("-" * 80)

        print(
            f"{entity} - YEAR 2022"
        )

        print("-" * 80)

        print(
            f"Abnormal days: "
            f"{len(entity_days)}"
        )

        print_kpis(
            yearly_result,
            f"{entity} - 2022"
        )

        # ----------------------------------------------------
        # Save entity analysis
        # ----------------------------------------------------

        safe_name = (
            entity
            .replace(
                "/",
                "_"
            )
            .replace(
                "\\",
                "_"
            )
        )

        entity_dir = os.path.join(
            entity_output_dir,
            safe_name
        )

        os.makedirs(
            entity_dir,
            exist_ok=True
        )

        monthly_df = pd.DataFrame(
            monthly_rows
        )

        monthly_file = os.path.join(
            entity_dir,
            "monthly_kpis.csv"
        )

        yearly_file = os.path.join(
            entity_dir,
            "yearly_kpis.csv"
        )

        monthly_df.to_csv(
            monthly_file,
            index=False
        )

        if yearly_result is not None:

            yearly_result[
                "entity"
            ] = entity

            yearly_result[
                "population"
            ] = "abnormal"

            yearly_result[
                "abnormal_days"
            ] = len(entity_days)

            pd.DataFrame(
                [yearly_result]
            ).to_csv(
                yearly_file,
                index=False
            )

        print("\nSaved entity analysis:")

        print(
            f"  {monthly_file}"
        )

        print(
            f"  {yearly_file}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")

    print("=" * 80)

    print(
        "2022 PVDAQ NORMAL / ABNORMAL KPI ANALYSIS"
    )

    print("=" * 80)

    print(
        f"\nRated AC capacity: "
        f"{RATED_AC_CAPACITY_KW} kW"
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    df = load_data()

    print(
        f"\nRows loaded: "
        f"{len(df):,}"
    )

    # --------------------------------------------------------
    # PREPARE
    # --------------------------------------------------------

    df = prepare_data(
        df
    )

    print(
        f"2022 rows: "
        f"{len(df):,}"
    )

    print(
        f"Date range: "
        f"{df['date'].min().date()} "
        f"→ "
        f"{df['date'].max().date()}"
    )

    # --------------------------------------------------------
    # LOAD ABNORMAL JSON
    # --------------------------------------------------------

    abnormal_data = (
        load_abnormal_days()
    )

    # --------------------------------------------------------
    # BUILD DAY GROUPS
    # --------------------------------------------------------

    (
        all_days,
        normal_days,
        abnormal_days
    ) = build_day_groups(
        df,
        abnormal_data
    )

    # --------------------------------------------------------
    # OVERALL DAY POPULATION
    # --------------------------------------------------------

    print("\n")

    print("=" * 80)

    print(
        "DAY POPULATION"
    )

    print("=" * 80)

    print(
        f"Total unique days : "
        f"{len(all_days)}"
    )

    print(
        f"Normal days       : "
        f"{len(normal_days)}"
    )

    print(
        f"Abnormal days     : "
        f"{len(abnormal_days)}"
    )

    print(
        f"Normal + abnormal : "
        f"{len(normal_days) + len(abnormal_days)}"
    )

    # --------------------------------------------------------
    # MONTHLY ANALYSIS
    # --------------------------------------------------------

    print("\n\n")

    print("=" * 80)

    print(
        "MONTHLY NORMAL / ABNORMAL ANALYSIS"
    )

    print("=" * 80)

    monthly_df = analyze_monthly(
        df,
        normal_days,
        abnormal_days,
        print_output=True
    )

    monthly_file = os.path.join(
        OUTPUT_DIR,
        "normal_abnormal_monthly_kpis.csv"
    )

    monthly_df.to_csv(
        monthly_file,
        index=False
    )

    # --------------------------------------------------------
    # YEARLY ANALYSIS
    # --------------------------------------------------------

    yearly_df = analyze_yearly(
        df,
        normal_days,
        abnormal_days
    )

    yearly_file = os.path.join(
        OUTPUT_DIR,
        "normal_abnormal_yearly_kpis.csv"
    )

    yearly_df.to_csv(
        yearly_file,
        index=False
    )

    # --------------------------------------------------------
    # ENTITY-WISE ABNORMAL ANALYSIS
    # --------------------------------------------------------

    analyze_abnormal_entities(
        df,
        abnormal_data
    )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    entity_output_dir = os.path.join(
        OUTPUT_DIR,
        "abnormal_entity_analysis"
    )

    print("\n\n")

    print("=" * 80)

    print(
        "ANALYSIS COMPLETE"
    )

    print("=" * 80)

    print(
        f"\nMonthly output:"
        f"\n{monthly_file}"
    )

    print(
        f"\nYearly output:"
        f"\n{yearly_file}"
    )

    print(
        f"\nEntity-wise outputs:"
        f"\n{entity_output_dir}"
    )

    print("\n")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()