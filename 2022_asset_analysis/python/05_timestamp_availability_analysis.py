import os
import glob
import pandas as pd
import numpy as np


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = r"C:\Users\rajes\solar_PV_project\csv_data\system_id=10\year=2022"

OUTPUT_DIR = r"C:\Users\rajes\solar_PV_project\2022_asset_analysis\outputs"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# TIMESTAMP COLUMN
# ============================================================

# The PVDAQ CSV files use "measured_on" as the timestamp.
TIMESTAMP_COLUMN = "measured_on"


# ============================================================
# EXTRACT DATE FROM FOLDER STRUCTURE
# ============================================================

def extract_folder_date(file_path):

    """
    Expected folder structure:

    year=2022/
        month=1/
            day=1/
                file.csv
    """

    parts = file_path.replace("\\", "/").split("/")

    year = None
    month = None
    day = None

    for part in parts:

        if part.startswith("year="):

            try:
                year = int(
                    part.split("=")[1]
                )
            except ValueError:
                pass

        elif part.startswith("month="):

            try:
                month = int(
                    part.split("=")[1]
                )
            except ValueError:
                pass

        elif part.startswith("day="):

            try:
                day = int(
                    part.split("=")[1]
                )
            except ValueError:
                pass

    if (
        year is not None
        and month is not None
        and day is not None
    ):

        try:

            return pd.Timestamp(
                year=year,
                month=month,
                day=day
            )

        except Exception:

            return pd.NaT

    return pd.NaT


# ============================================================
# FIND ALL CSV FILES
# ============================================================

csv_files = sorted(
    glob.glob(
        os.path.join(
            BASE_DIR,
            "**",
            "*.csv"
        ),
        recursive=True
    )
)


# ============================================================
# HEADER
# ============================================================

print("=" * 100)
print("2022 TIMESTAMP AVAILABILITY ANALYSIS")
print("=" * 100)

print(
    f"Base directory : {BASE_DIR}"
)

print(
    f"CSV files found: {len(csv_files)}"
)

print(
    f"Timestamp column expected: {TIMESTAMP_COLUMN}"
)


if len(csv_files) == 0:

    print()
    print("ERROR: No CSV files found.")

    raise SystemExit


# ============================================================
# STORAGE
# ============================================================

file_results = []

column_inventory = []

date_results = []


# ============================================================
# PROCESS EVERY CSV FILE
# ============================================================

for file_number, file_path in enumerate(
    csv_files,
    start=1
):

    relative_path = os.path.relpath(
        file_path,
        BASE_DIR
    )

    filename = os.path.basename(
        file_path
    )

    # --------------------------------------------------------
    # Date from folder
    # --------------------------------------------------------

    folder_date = extract_folder_date(
        file_path
    )

    if pd.isna(folder_date):

        month = np.nan
        day = np.nan

    else:

        month = folder_date.month
        day = folder_date.day


    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            file_path
        )

    except Exception as e:

        file_results.append({

            "file": filename,

            "relative_path": relative_path,

            "folder_date": "",

            "month": month,

            "day": day,

            "read_status": "READ_ERROR",

            "error": str(e),

            "records": 0,

            "timestamp_column": TIMESTAMP_COLUMN,

            "timestamp_status": "READ_ERROR",

            "valid_timestamp_count": 0,

            "invalid_timestamp_count": 0,

            "missing_timestamp_count": 0,

            "duplicate_timestamp_count": 0,

            "unique_timestamp_count": 0,

            "first_timestamp": "",

            "last_timestamp": "",

            "median_interval_seconds": np.nan,

            "minimum_interval_seconds": np.nan,

            "maximum_interval_seconds": np.nan

        })

        continue


    # --------------------------------------------------------
    # Basic information
    # --------------------------------------------------------

    records = len(df)

    columns = list(df.columns)

    column_names = " | ".join(
        str(col)
        for col in columns
    )


    # --------------------------------------------------------
    # Save column inventory
    # --------------------------------------------------------

    column_inventory.append({

        "file": filename,

        "relative_path": relative_path,

        "folder_date": (
            folder_date.strftime("%Y-%m-%d")
            if not pd.isna(folder_date)
            else ""
        ),

        "number_of_columns": len(columns),

        "column_names": column_names,

        "measured_on_present":
            TIMESTAMP_COLUMN in df.columns

    })


    # ========================================================
    # CHECK measured_on COLUMN
    # ========================================================

    if TIMESTAMP_COLUMN not in df.columns:

        file_results.append({

            "file": filename,

            "relative_path": relative_path,

            "folder_date": (
                folder_date.strftime("%Y-%m-%d")
                if not pd.isna(folder_date)
                else ""
            ),

            "month": month,

            "day": day,

            "read_status": "READ_OK",

            "error": "",

            "records": records,

            "timestamp_column":
                TIMESTAMP_COLUMN,

            "timestamp_status":
                "NO_MEASURED_ON_COLUMN",

            "valid_timestamp_count": 0,

            "invalid_timestamp_count": 0,

            "missing_timestamp_count": 0,

            "duplicate_timestamp_count": 0,

            "unique_timestamp_count": 0,

            "first_timestamp": "",

            "last_timestamp": "",

            "median_interval_seconds": np.nan,

            "minimum_interval_seconds": np.nan,

            "maximum_interval_seconds": np.nan

        })


        date_results.append({

            "date": (
                folder_date.strftime("%Y-%m-%d")
                if not pd.isna(folder_date)
                else ""
            ),

            "month": month,

            "day": day,

            "file": filename,

            "records": records,

            "timestamp_column":
                TIMESTAMP_COLUMN,

            "timestamp_status":
                "NO_MEASURED_ON_COLUMN",

            "valid_timestamps": 0,

            "invalid_timestamps": 0,

            "missing_timestamps": 0,

            "duplicate_timestamps": 0,

            "unique_timestamps": 0,

            "first_timestamp": "",

            "last_timestamp": "",

            "median_interval_seconds": np.nan

        })

        continue


    # ========================================================
    # measured_on EXISTS
    # ========================================================

    timestamp_raw = df[
        TIMESTAMP_COLUMN
    ]


    # --------------------------------------------------------
    # Missing timestamp values
    # --------------------------------------------------------

    missing_timestamp_count = int(
        timestamp_raw.isna().sum()
    )


    # --------------------------------------------------------
    # Convert to datetime
    # --------------------------------------------------------

    timestamp = pd.to_datetime(
        timestamp_raw,
        errors="coerce"
    )


    # --------------------------------------------------------
    # Valid timestamp count
    # --------------------------------------------------------

    valid_timestamp_count = int(
        timestamp.notna().sum()
    )


    # --------------------------------------------------------
    # Invalid timestamp count
    #
    # Invalid means non-empty values that could not be
    # converted to datetime.
    # --------------------------------------------------------

    invalid_timestamp_count = int(
        len(timestamp)
        - valid_timestamp_count
        - missing_timestamp_count
    )


    # --------------------------------------------------------
    # Valid timestamps
    # --------------------------------------------------------

    valid_ts = timestamp.dropna()


    # --------------------------------------------------------
    # Initialize statistics
    # --------------------------------------------------------

    duplicate_timestamp_count = 0

    unique_timestamp_count = 0

    first_timestamp = ""

    last_timestamp = ""

    median_interval_seconds = np.nan

    minimum_interval_seconds = np.nan

    maximum_interval_seconds = np.nan


    # ========================================================
    # TIMESTAMP STATISTICS
    # ========================================================

    if len(valid_ts) > 0:

        # Number of unique timestamps
        unique_timestamp_count = int(
            valid_ts.nunique()
        )


        # Duplicate timestamp rows
        duplicate_timestamp_count = int(
            valid_ts.duplicated().sum()
        )


        # First timestamp
        first_timestamp = valid_ts.min()


        # Last timestamp
        last_timestamp = valid_ts.max()


        # ----------------------------------------------------
        # Sampling interval
        # ----------------------------------------------------

        sorted_ts = (
            valid_ts
            .sort_values()
            .drop_duplicates()
        )


        if len(sorted_ts) > 1:

            intervals = (
                sorted_ts
                .diff()
                .dropna()
                .dt.total_seconds()
            )


            if len(intervals) > 0:

                median_interval_seconds = float(
                    intervals.median()
                )

                minimum_interval_seconds = float(
                    intervals.min()
                )

                maximum_interval_seconds = float(
                    intervals.max()
                )


    # ========================================================
    # CLASSIFY TIMESTAMP STATUS
    # ========================================================

    if valid_timestamp_count == 0:

        timestamp_status = (
            "MEASURED_ON_PRESENT_BUT_NO_VALID_VALUES"
        )

    elif (
        missing_timestamp_count > 0
        or invalid_timestamp_count > 0
    ):

        timestamp_status = (
            "MEASURED_ON_PRESENT_WITH_INVALID_OR_MISSING_VALUES"
        )

    elif duplicate_timestamp_count > 0:

        timestamp_status = (
            "MEASURED_ON_PRESENT_WITH_DUPLICATES"
        )

    else:

        timestamp_status = (
            "MEASURED_ON_VALID"
        )


    # ========================================================
    # FILE RESULT
    # ========================================================

    file_results.append({

        "file": filename,

        "relative_path": relative_path,

        "folder_date": (
            folder_date.strftime("%Y-%m-%d")
            if not pd.isna(folder_date)
            else ""
        ),

        "month": month,

        "day": day,

        "read_status": "READ_OK",

        "error": "",

        "records": records,

        "timestamp_column":
            TIMESTAMP_COLUMN,

        "timestamp_status":
            timestamp_status,

        "valid_timestamp_count":
            valid_timestamp_count,

        "invalid_timestamp_count":
            invalid_timestamp_count,

        "missing_timestamp_count":
            missing_timestamp_count,

        "duplicate_timestamp_count":
            duplicate_timestamp_count,

        "unique_timestamp_count":
            unique_timestamp_count,

        "first_timestamp":
            first_timestamp,

        "last_timestamp":
            last_timestamp,

        "median_interval_seconds":
            median_interval_seconds,

        "minimum_interval_seconds":
            minimum_interval_seconds,

        "maximum_interval_seconds":
            maximum_interval_seconds

    })


    # ========================================================
    # DATE RESULT
    # ========================================================

    date_results.append({

        "date": (
            folder_date.strftime("%Y-%m-%d")
            if not pd.isna(folder_date)
            else ""
        ),

        "month": month,

        "day": day,

        "file": filename,

        "records": records,

        "timestamp_column":
            TIMESTAMP_COLUMN,

        "timestamp_status":
            timestamp_status,

        "valid_timestamps":
            valid_timestamp_count,

        "invalid_timestamps":
            invalid_timestamp_count,

        "missing_timestamps":
            missing_timestamp_count,

        "duplicate_timestamps":
            duplicate_timestamp_count,

        "unique_timestamps":
            unique_timestamp_count,

        "first_timestamp":
            first_timestamp,

        "last_timestamp":
            last_timestamp,

        "median_interval_seconds":
            median_interval_seconds,

        "minimum_interval_seconds":
            minimum_interval_seconds,

        "maximum_interval_seconds":
            maximum_interval_seconds

    })


# ============================================================
# CREATE DATAFRAMES
# ============================================================

file_df = pd.DataFrame(
    file_results
)

date_df = pd.DataFrame(
    date_results
)

column_df = pd.DataFrame(
    column_inventory
)


# ============================================================
# MONTH-WISE SUMMARY
# ============================================================

monthly_rows = []


for month in range(1, 13):

    month_files = file_df[
        file_df["month"] == month
    ].copy()


    # --------------------------------------------------------
    # Basic counts
    # --------------------------------------------------------

    total_files = len(
        month_files
    )


    files_no_measured_on = int(
        (
            month_files["timestamp_status"]
            == "NO_MEASURED_ON_COLUMN"
        ).sum()
    )


    files_valid = int(
        (
            month_files["timestamp_status"]
            == "MEASURED_ON_VALID"
        ).sum()
    )


    files_invalid_or_missing = int(
        (
            month_files["timestamp_status"]
            == "MEASURED_ON_PRESENT_WITH_INVALID_OR_MISSING_VALUES"
        ).sum()
    )


    files_duplicates = int(
        (
            month_files["timestamp_status"]
            == "MEASURED_ON_PRESENT_WITH_DUPLICATES"
        ).sum()
    )


    files_no_valid_values = int(
        (
            month_files["timestamp_status"]
            == "MEASURED_ON_PRESENT_BUT_NO_VALID_VALUES"
        ).sum()
    )


    files_read_error = int(
        (
            month_files["timestamp_status"]
            == "READ_ERROR"
        ).sum()
    )


    # --------------------------------------------------------
    # Record counts
    # --------------------------------------------------------

    total_records = int(
        month_files["records"]
        .fillna(0)
        .sum()
    )


    valid_timestamp_values = int(
        month_files[
            "valid_timestamp_count"
        ]
        .fillna(0)
        .sum()
    )


    missing_timestamp_values = int(
        month_files[
            "missing_timestamp_count"
        ]
        .fillna(0)
        .sum()
    )


    invalid_timestamp_values = int(
        month_files[
            "invalid_timestamp_count"
        ]
        .fillna(0)
        .sum()
    )


    duplicate_timestamp_values = int(
        month_files[
            "duplicate_timestamp_count"
        ]
        .fillna(0)
        .sum()
    )


    # --------------------------------------------------------
    # Month name
    # --------------------------------------------------------

    month_name = pd.Timestamp(
        year=2022,
        month=month,
        day=1
    ).strftime("%B")


    # --------------------------------------------------------
    # Store
    # --------------------------------------------------------

    monthly_rows.append({

        "month": month,

        "month_name": month_name,

        "total_files": total_files,

        "files_no_measured_on":
            files_no_measured_on,

        "files_valid_timestamp":
            files_valid,

        "files_invalid_or_missing_timestamp":
            files_invalid_or_missing,

        "files_with_duplicate_timestamp":
            files_duplicates,

        "files_no_valid_timestamp":
            files_no_valid_values,

        "files_read_error":
            files_read_error,

        "total_records":
            total_records,

        "valid_timestamp_values":
            valid_timestamp_values,

        "missing_timestamp_values":
            missing_timestamp_values,

        "invalid_timestamp_values":
            invalid_timestamp_values,

        "duplicate_timestamp_values":
            duplicate_timestamp_values

    })


monthly_df = pd.DataFrame(
    monthly_rows
)


# ============================================================
# SAVE OUTPUT FILES
# ============================================================

file_output = os.path.join(
    OUTPUT_DIR,
    "2022_timestamp_file_inventory.csv"
)


monthly_output = os.path.join(
    OUTPUT_DIR,
    "2022_timestamp_monthly_summary.csv"
)


date_output = os.path.join(
    OUTPUT_DIR,
    "2022_timestamp_date_summary.csv"
)


column_output = os.path.join(
    OUTPUT_DIR,
    "2022_csv_column_inventory.csv"
)


no_timestamp_output = os.path.join(
    OUTPUT_DIR,
    "2022_files_without_measured_on.csv"
)


invalid_timestamp_output = os.path.join(
    OUTPUT_DIR,
    "2022_files_with_invalid_or_missing_measured_on.csv"
)


duplicate_timestamp_output = os.path.join(
    OUTPUT_DIR,
    "2022_files_with_duplicate_measured_on.csv"
)


# ------------------------------------------------------------
# Write files
# ------------------------------------------------------------

file_df.to_csv(
    file_output,
    index=False
)


monthly_df.to_csv(
    monthly_output,
    index=False
)


date_df.to_csv(
    date_output,
    index=False
)


column_df.to_csv(
    column_output,
    index=False
)


file_df[
    file_df["timestamp_status"]
    == "NO_MEASURED_ON_COLUMN"
].to_csv(
    no_timestamp_output,
    index=False
)


file_df[
    file_df["timestamp_status"]
    == "MEASURED_ON_PRESENT_WITH_INVALID_OR_MISSING_VALUES"
].to_csv(
    invalid_timestamp_output,
    index=False
)


file_df[
    file_df["duplicate_timestamp_count"] > 0
].to_csv(
    duplicate_timestamp_output,
    index=False
)


# ============================================================
# OVERALL COUNTS
# ============================================================

total_files = len(
    file_df
)


files_valid_timestamp = int(
    (
        file_df["timestamp_status"]
        == "MEASURED_ON_VALID"
    ).sum()
)


files_no_timestamp = int(
    (
        file_df["timestamp_status"]
        == "NO_MEASURED_ON_COLUMN"
    ).sum()
)


files_invalid_timestamp = int(
    (
        file_df["timestamp_status"]
        == "MEASURED_ON_PRESENT_WITH_INVALID_OR_MISSING_VALUES"
    ).sum()
)


files_duplicate_timestamp = int(
    (
        file_df["duplicate_timestamp_count"]
        > 0
    ).sum()
)


files_no_valid_timestamp = int(
    (
        file_df["timestamp_status"]
        == "MEASURED_ON_PRESENT_BUT_NO_VALID_VALUES"
    ).sum()
)


files_read_error = int(
    (
        file_df["timestamp_status"]
        == "READ_ERROR"
    ).sum()
)


# ============================================================
# PRINT OVERALL SUMMARY
# ============================================================

print()
print("=" * 100)
print("OVERALL TIMESTAMP SUMMARY")
print("=" * 100)

print(
    f"Total CSV files                    : "
    f"{total_files}"
)

print(
    f"Files with valid measured_on       : "
    f"{files_valid_timestamp}"
)

print(
    f"Files without measured_on column   : "
    f"{files_no_timestamp}"
)

print(
    f"Files with invalid/missing values  : "
    f"{files_invalid_timestamp}"
)

print(
    f"Files with duplicate timestamps    : "
    f"{files_duplicate_timestamp}"
)

print(
    f"Files with no valid measured_on    : "
    f"{files_no_valid_timestamp}"
)

print(
    f"Files with read errors             : "
    f"{files_read_error}"
)


# ============================================================
# MONTH-WISE SUMMARY
# ============================================================

print()
print("=" * 100)
print("MONTH-WISE TIMESTAMP SUMMARY")
print("=" * 100)

print(
    monthly_df.to_string(
        index=False
    )
)


# ============================================================
# DATE-WISE SUMMARY
# ============================================================

print()
print("=" * 100)
print("DATE-WISE TIMESTAMP SUMMARY")
print("=" * 100)

if len(date_df) > 0:

    display_columns = [

        "date",

        "month",

        "day",

        "file",

        "records",

        "timestamp_status",

        "valid_timestamps",

        "invalid_timestamps",

        "missing_timestamps",

        "duplicate_timestamps",

        "unique_timestamps",

        "first_timestamp",

        "last_timestamp",

        "median_interval_seconds",

        "minimum_interval_seconds",

        "maximum_interval_seconds"

    ]


    print(
        date_df[
            display_columns
        ]
        .sort_values(
            ["month", "day"]
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# FILES WITHOUT measured_on
# ============================================================

no_ts_df = file_df[
    file_df["timestamp_status"]
    == "NO_MEASURED_ON_COLUMN"
].copy()


print()
print("=" * 100)
print("FILES WITHOUT measured_on COLUMN")
print("=" * 100)

print(
    f"Total: {len(no_ts_df)}"
)


if len(no_ts_df) > 0:

    print()

    print(
        no_ts_df[
            [
                "folder_date",
                "file",
                "records"
            ]
        ]
        .sort_values(
            ["folder_date"]
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# INVALID / MISSING measured_on
# ============================================================

invalid_df = file_df[
    file_df["timestamp_status"]
    == "MEASURED_ON_PRESENT_WITH_INVALID_OR_MISSING_VALUES"
].copy()


print()
print("=" * 100)
print(
    "FILES WITH INVALID OR MISSING measured_on VALUES"
)
print("=" * 100)

print(
    f"Total: {len(invalid_df)}"
)


if len(invalid_df) > 0:

    print()

    print(
        invalid_df[
            [
                "folder_date",
                "file",
                "records",
                "valid_timestamp_count",
                "missing_timestamp_count",
                "invalid_timestamp_count"
            ]
        ]
        .sort_values(
            ["folder_date"]
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# DUPLICATE measured_on VALUES
# ============================================================

duplicate_df = file_df[
    file_df["duplicate_timestamp_count"] > 0
].copy()


print()
print("=" * 100)
print("FILES WITH DUPLICATE measured_on VALUES")
print("=" * 100)

print(
    f"Total: {len(duplicate_df)}"
)


if len(duplicate_df) > 0:

    print()

    print(
        duplicate_df[
            [
                "folder_date",
                "file",
                "records",
                "duplicate_timestamp_count"
            ]
        ]
        .sort_values(
            ["folder_date"]
        )
        .to_string(
            index=False
        )
    )


# ============================================================
# SAMPLING INTERVAL SUMMARY
# ============================================================

valid_interval_df = file_df[
    file_df["median_interval_seconds"].notna()
].copy()


print()
print("=" * 100)
print("SAMPLING INTERVAL SUMMARY")
print("=" * 100)


if len(valid_interval_df) > 0:

    print(
        valid_interval_df[
            [
                "folder_date",
                "file",
                "median_interval_seconds",
                "minimum_interval_seconds",
                "maximum_interval_seconds"
            ]
        ]
        .sort_values(
            ["folder_date"]
        )
        .to_string(
            index=False
        )
    )

else:

    print(
        "No valid timestamp intervals available."
    )


# ============================================================
# TIMESTAMP COLUMN CHECK
# ============================================================

print()
print("=" * 100)
print("TIMESTAMP COLUMN CHECK")
print("=" * 100)

measured_on_present_count = int(
    column_df[
        "measured_on_present"
    ].sum()
)

measured_on_absent_count = int(
    (
        ~column_df[
            "measured_on_present"
        ]
    ).sum()
)

print(
    f"Files containing measured_on : "
    f"{measured_on_present_count}"
)

print(
    f"Files without measured_on     : "
    f"{measured_on_absent_count}"
)


# ============================================================
# OUTPUT FILES
# ============================================================

print()
print("=" * 100)
print("OUTPUT FILES")
print("=" * 100)

print(
    f"1. {file_output}"
)

print(
    f"2. {monthly_output}"
)

print(
    f"3. {date_output}"
)

print(
    f"4. {column_output}"
)

print(
    f"5. {no_timestamp_output}"
)

print(
    f"6. {invalid_timestamp_output}"
)

print(
    f"7. {duplicate_timestamp_output}"
)

print()
print("=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)