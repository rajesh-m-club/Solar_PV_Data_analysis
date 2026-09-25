import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ============================================================
# CONFIGURATION
# ============================================================

# Excel workbook
EXCEL_FILE = r"C:\Users\rajes\solar_PV_project\excel_analysis\raw_data.xlsx"

# Folder where plots will be saved
OUTPUT_DIR = r"C:\Users\rajes\solar_PV_project\excel_analysis\plots"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Excel sheet names
DAY1_SHEET = "cleaned_data"
DAY2_SHEET = "cleaned_data2"

# Plot labels
DAY1_LABEL = "Day 1 - 01-01-2022"
DAY2_LABEL = "Day 2 - 02-01-2022"


# ============================================================
# COLUMN NAMES
# ============================================================

TIME_COL = "measured_on"

POA_COL = "poa_irradiance__421"

DC_CURRENT_COL = "dc_pos_current__425"

DC_VOLTAGE_COL = "dc_pos_voltage__424"

DC_POWER_COL = "dc_power__422"

AC_POWER_COL = "ac_power__423"

AC_CURRENT_COL = "ac_current__427"

AC_VOLTAGE_COL = "ac_voltage__426"

INVERTER_TEMP_COL = "inverter_temp__432"


# ============================================================
# LOAD EXCEL SHEETS
# ============================================================

print("Reading Excel workbook...")

try:
    day1 = pd.read_excel(
        EXCEL_FILE,
        sheet_name=DAY1_SHEET
    )

    day2 = pd.read_excel(
        EXCEL_FILE,
        sheet_name=DAY2_SHEET
    )

except FileNotFoundError:
    raise FileNotFoundError(
        f"\nExcel file not found:\n{EXCEL_FILE}\n"
        f"\nCheck the EXCEL_FILE path."
    )

except Exception as e:
    raise RuntimeError(
        f"\nCould not read the Excel workbook.\n"
        f"Error: {e}"
    )


print(f"Day 1 rows: {len(day1)}")
print(f"Day 2 rows: {len(day2)}")


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    TIME_COL,
    POA_COL,
    DC_CURRENT_COL,
    DC_VOLTAGE_COL,
    DC_POWER_COL,
    AC_POWER_COL,
    AC_CURRENT_COL,
    AC_VOLTAGE_COL,
    INVERTER_TEMP_COL
]

for df_name, df in [
    ("Day 1", day1),
    ("Day 2", day2)
]:

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"\n{df_name} is missing these columns:\n"
            + "\n".join(missing)
        )


# ============================================================
# CONVERT DATA TYPES
# ============================================================

for df in [day1, day2]:

    # Convert timestamp
    df[TIME_COL] = pd.to_datetime(
        df[TIME_COL],
        errors="coerce"
    )

    # Convert numeric columns
    for col in [
        POA_COL,
        DC_CURRENT_COL,
        DC_VOLTAGE_COL,
        DC_POWER_COL,
        AC_POWER_COL,
        AC_CURRENT_COL,
        AC_VOLTAGE_COL,
        INVERTER_TEMP_COL
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


# ============================================================
# DATA CLEANING FUNCTION FOR PLOTS
# ============================================================

def clean_xy(df, x_col, y_col):

    data = df[
        [x_col, y_col]
    ].copy()

    # Remove infinities
    data = data.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # Remove missing values
    data = data.dropna()

    return data


# ============================================================
# DATASETS
# ============================================================

datasets = [
    (day1, DAY1_LABEL),
    (day2, DAY2_LABEL)
]


# ============================================================
# GENERIC 2D PLOT FUNCTION
# ============================================================

def make_2d_comparison_plot(
    x_col,
    y_col,
    x_label,
    y_label,
    title,
    filename
):

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(15, 6)
    )

    for ax, (df, label) in zip(axes, datasets):

        data = clean_xy(
            df,
            x_col,
            y_col
        )

        ax.scatter(
            data[x_col],
            data[y_col],
            s=12,
            alpha=0.6
        )

        ax.set_title(label)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        ax.grid(
            True,
            alpha=0.3
        )

    fig.suptitle(
        title,
        fontsize=16
    )

    plt.tight_layout(
        rect=[0, 0, 1, 0.94]
    )

    output_file = os.path.join(
        OUTPUT_DIR,
        filename
    )

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    print(f"Saved: {output_file}")


# ============================================================
# 1. POA vs RAW DC POWER
# ============================================================

make_2d_comparison_plot(

    x_col=POA_COL,
    y_col=DC_POWER_COL,

    x_label="POA Irradiance (W/m²)",
    y_label="Raw DC Power (W)",

    title="POA Irradiance vs Raw DC Power",

    filename=(
        "01_POA_vs_Raw_DC_Power_Day1_Day2.png"
    )
)


# ============================================================
# 2. RAW DC POWER vs RAW AC POWER
# ============================================================

make_2d_comparison_plot(

    x_col=DC_POWER_COL,
    y_col=AC_POWER_COL,

    x_label="Raw DC Power (W)",
    y_label="Raw AC Power (W)",

    title="Raw DC Power vs Raw AC Power",

    filename=(
        "02_Raw_DC_Power_vs_Raw_AC_Power_Day1_Day2.png"
    )
)


# ============================================================
# 3. INVERTER TEMPERATURE vs RAW DC POWER
# ============================================================

make_2d_comparison_plot(

    x_col=INVERTER_TEMP_COL,
    y_col=DC_POWER_COL,

    x_label="Inverter Temperature (°C)",
    y_label="Raw DC Power (W)",

    title="Inverter Temperature vs Raw DC Power",

    filename=(
        "03_Inverter_Temp_vs_Raw_DC_Power_Day1_Day2.png"
    )
)


# ============================================================
# 4. INVERTER TEMPERATURE vs RAW AC POWER
# ============================================================

make_2d_comparison_plot(

    x_col=INVERTER_TEMP_COL,
    y_col=AC_POWER_COL,

    x_label="Inverter Temperature (°C)",
    y_label="Raw AC Power (W)",

    title="Inverter Temperature vs Raw AC Power",

    filename=(
        "04_Inverter_Temp_vs_Raw_AC_Power_Day1_Day2.png"
    )
)


# ============================================================
# 5. DC VOLTAGE vs DC CURRENT
# ============================================================

make_2d_comparison_plot(

    x_col=DC_VOLTAGE_COL,
    y_col=DC_CURRENT_COL,

    x_label="Raw DC Voltage (V)",
    y_label="Raw DC Current (A)",

    title="Raw DC Voltage vs Raw DC Current",

    filename=(
        "05_Raw_DC_Voltage_vs_Raw_DC_Current_Day1_Day2.png"
    )
)


# ============================================================
# 6. POA vs DC CURRENT
# ============================================================
# This is useful because Day 1 showed unusual DC current behavior.
# It directly relates available irradiance to measured DC current.

make_2d_comparison_plot(

    x_col=POA_COL,
    y_col=DC_CURRENT_COL,

    x_label="POA Irradiance (W/m²)",
    y_label="Raw DC Current (A)",

    title="POA Irradiance vs Raw DC Current",

    filename=(
        "06_POA_vs_Raw_DC_Current_Day1_Day2.png"
    )
)


# ============================================================
# 7. POA vs DC VOLTAGE
# ============================================================

make_2d_comparison_plot(

    x_col=POA_COL,
    y_col=DC_VOLTAGE_COL,

    x_label="POA Irradiance (W/m²)",
    y_label="Raw DC Voltage (V)",

    title="POA Irradiance vs Raw DC Voltage",

    filename=(
        "07_POA_vs_Raw_DC_Voltage_Day1_Day2.png"
    )
)


# ============================================================
# 8. 3D:
#    RAW DC POWER vs RAW AC POWER vs INVERTER TEMPERATURE
# ============================================================

fig = plt.figure(
    figsize=(15, 7)
)

for plot_number, (df, label) in enumerate(
    datasets,
    start=1
):

    ax = fig.add_subplot(
        1,
        2,
        plot_number,
        projection="3d"
    )

    data = df[
        [
            DC_POWER_COL,
            AC_POWER_COL,
            INVERTER_TEMP_COL
        ]
    ].copy()

    data = data.replace(
        [np.inf, -np.inf],
        np.nan
    )

    data = data.dropna()

    ax.scatter(
        data[DC_POWER_COL],
        data[AC_POWER_COL],
        data[INVERTER_TEMP_COL],
        s=8,
        alpha=0.5
    )

    ax.set_title(label)

    ax.set_xlabel(
        "Raw DC Power (W)",
        labelpad=8
    )

    ax.set_ylabel(
        "Raw AC Power (W)",
        labelpad=8
    )

    ax.set_zlabel(
        "Inverter Temperature (°C)",
        labelpad=8
    )

    ax.view_init(
        elev=25,
        azim=-55
    )


fig.suptitle(
    "3D Relationship: Raw DC Power, Raw AC Power and Inverter Temperature",
    fontsize=15
)

plt.tight_layout(
    rect=[0, 0, 1, 0.93]
)

output_file = os.path.join(
    OUTPUT_DIR,
    "08_3D_DC_AC_Power_vs_Inverter_Temp_Day1_Day2.png"
)

plt.savefig(
    output_file,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

print(f"Saved: {output_file}")


# ============================================================
# BASIC NUMERICAL COMPARISON
# ============================================================

print("\n============================================")
print("DAY 1 vs DAY 2 BASIC COMPARISON")
print("============================================")

for df, label in datasets:

    print(f"\n{label}")

    print(
        f"POA range: "
        f"{df[POA_COL].min():.3f} to "
        f"{df[POA_COL].max():.3f} W/m²"
    )

    print(
        f"DC voltage range: "
        f"{df[DC_VOLTAGE_COL].min():.3f} to "
        f"{df[DC_VOLTAGE_COL].max():.3f} V"
    )

    print(
        f"DC current range: "
        f"{df[DC_CURRENT_COL].min():.3f} to "
        f"{df[DC_CURRENT_COL].max():.3f} A"
    )

    print(
        f"DC power range: "
        f"{df[DC_POWER_COL].min():.3f} to "
        f"{df[DC_POWER_COL].max():.3f} W"
    )

    print(
        f"AC power range: "
        f"{df[AC_POWER_COL].min():.3f} to "
        f"{df[AC_POWER_COL].max():.3f} W"
    )

    print(
        f"Inverter temperature range: "
        f"{df[INVERTER_TEMP_COL].min():.3f} to "
        f"{df[INVERTER_TEMP_COL].max():.3f} °C"
    )


# ============================================================
# FINAL MESSAGE
# ============================================================

print("\n============================================")
print("ALL ANALYSIS PLOTS GENERATED")
print("============================================")

print(f"\nPlots saved to:")
print(OUTPUT_DIR)

print("\nGenerated figures:")

print("1. POA vs Raw DC Power")
print("2. Raw DC Power vs Raw AC Power")
print("3. Inverter Temperature vs Raw DC Power")
print("4. Inverter Temperature vs Raw AC Power")
print("5. Raw DC Voltage vs Raw DC Current")
print("6. POA vs Raw DC Current")
print("7. POA vs Raw DC Voltage")
print("8. 3D DC Power vs AC Power vs Inverter Temperature")