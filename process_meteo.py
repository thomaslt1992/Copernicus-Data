from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


# ==================================================
# SETTINGS
# ==================================================

TIMEZONE = "Europe/Berlin"
MINIMUM_COVERAGE = 0.75
WET_HOUR_THRESHOLD_MM = 0.1

START_DATE = "2015-01-01"
END_DATE = "2024-12-31"

WEATHER_COLUMNS = [
    "t2m",
    "d2m",
    "u10",
    "v10",
    "tp",
    "ssrd",
    "sp",
]


# ==================================================
# READ NETCDF
# ==================================================

def nc_to_pandas(file_path):
    """Read a NetCDF file and return a pandas DataFrame."""
    with xr.open_dataset(file_path) as dataset:
        df = dataset.to_dataframe().reset_index()

    return df


def load_monthly_hourly(file_path):
    """
    Read one monthly NetCDF file and spatially average
    its ERA5-Land grid cells.

    Returns one row per UTC hour.
    """
    df = nc_to_pandas(file_path)

    if "valid_time" not in df.columns:
        raise ValueError(
            f"'valid_time' is missing from {file_path}"
        )

    missing_columns = [
        column
        for column in WEATHER_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns in {file_path}: "
            f"{missing_columns}"
        )

    df["valid_time"] = pd.to_datetime(
        df["valid_time"],
        utc=True,
    )

    # Average the nine Berlin grid cells for each hour
    monthly_hourly = (
        df.groupby("valid_time", as_index=False)[WEATHER_COLUMNS]
        .mean()
        .sort_values("valid_time")
        .reset_index(drop=True)
    )

    return monthly_hourly


# ==================================================
# ERA5-LAND DE-ACCUMULATION
# ==================================================

def deaccumulate_era5_land(series, timestamps):
    """
    Convert ERA5-Land cumulative values into hourly increments.

    All monthly hourly data must be concatenated before this
    function is applied.
    """
    hours = timestamps.dt.hour

    consecutive = timestamps.diff().eq(
        pd.Timedelta(hours=1)
    )

    hourly = series.diff()

    # At 01:00, the value represents the first hour
    # accumulated since 00:00.
    hourly.loc[hours == 1] = series.loc[hours == 1]

    # Do not calculate a difference across missing hours
    hourly.loc[
        ~consecutive & (hours != 1)
    ] = np.nan

    # Remove tiny negative floating-point artefacts
    return hourly.clip(lower=0)


# ==================================================
# HOURLY VARIABLE PREPROCESSING
# ==================================================

def preprocess_hourly_data(df_hourly):
    """
    Convert units and create derived hourly variables.
    """
    hourly = df_hourly.copy()

    hourly = (
        hourly.sort_values("valid_time")
        .reset_index(drop=True)
    )

    # Kelvin → Celsius
    hourly["t2m_c"] = hourly["t2m"] - 273.15
    hourly["d2m_c"] = hourly["d2m"] - 273.15

    # Accumulated metres → hourly millimetres
    hourly["tp_mm"] = (
        deaccumulate_era5_land(
            hourly["tp"],
            hourly["valid_time"],
        )
        * 1000
    )

    # Accumulated J/m² → hourly-average W/m²
    hourly["ssrd_w_m2"] = (
        deaccumulate_era5_land(
            hourly["ssrd"],
            hourly["valid_time"],
        )
        / 3600
    )

    # Pa → hPa
    hourly["sp_hpa"] = hourly["sp"] / 100

    # Wind-vector magnitude
    hourly["wind_speed_m_s"] = np.hypot(
        hourly["u10"],
        hourly["v10"],
    )

    # Relative humidity using the Magnus approximation
    hourly["relative_humidity"] = (
        100
        * np.exp(
            (17.625 * hourly["d2m_c"])
            / (243.04 + hourly["d2m_c"])
        )
        / np.exp(
            (17.625 * hourly["t2m_c"])
            / (243.04 + hourly["t2m_c"])
        )
    ).clip(0, 100)

    # Remove original-unit columns
    hourly.drop(
        columns=[
            "t2m",
            "d2m",
            "tp",
            "ssrd",
            "sp",
            "number",
            "expver",
        ],
        errors="ignore",
        inplace=True,
    )

    return hourly


# ==================================================
# DAILY AGGREGATION HELPERS
# ==================================================

def expected_hours_for_day(day):
    """
    Return 23, 24 or 25 hours depending on daylight saving.
    """
    start = pd.Timestamp(day).tz_localize(TIMEZONE)

    end = (
        pd.Timestamp(day) + pd.Timedelta(days=1)
    ).tz_localize(TIMEZONE)

    duration = (
        end.tz_convert("UTC")
        - start.tz_convert("UTC")
    )

    return int(duration / pd.Timedelta(hours=1))


def calculate_statistic(values, statistic):
    """Calculate one daily statistic."""
    n = len(values)

    if statistic == "mean":
        return values.mean()

    if statistic == "median":
        return values.median()

    if statistic == "min":
        return values.min()

    if statistic == "max":
        return values.max()

    if statistic == "q25":
        return values.quantile(0.25)

    if statistic == "q75":
        return values.quantile(0.75)

    if statistic == "iqr":
        return (
            values.quantile(0.75)
            - values.quantile(0.25)
        )

    if statistic == "std":
        return (
            values.std(ddof=1)
            if n > 1
            else np.nan
        )

    if statistic == "se":
        return (
            values.std(ddof=1) / np.sqrt(n)
            if n > 1
            else np.nan
        )

    if statistic == "sum":
        return values.sum()

    if statistic == "wet_hours":
        return (
            values >= WET_HOUR_THRESHOLD_MM
        ).sum()

    if statistic == "total_mj_m2":
        return (
            values.sum()
            * 3600
            / 1_000_000
        )

    raise ValueError(
        f"Unknown statistic: {statistic}"
    )


def add_daily_statistics(
    records,
    data,
    date_column,
    variable,
    statistics,
):
    """
    Add daily statistics for one variable.

    Individual NaN observations are omitted. Statistics
    are set to NaN when daily coverage is below 75%.
    """
    if variable not in data.columns:
        print(f"Skipping missing variable: {variable}")
        return

    for day, group in data.groupby(date_column):
        records.setdefault(day, {"date": day})

        values = group[variable].dropna()
        n_valid = len(values)

        expected_hours = expected_hours_for_day(day)

        coverage = n_valid / expected_hours

        minimum_required = int(
            np.ceil(
                expected_hours
                * MINIMUM_COVERAGE
            )
        )

        records[day][
            f"{variable}_n_valid"
        ] = n_valid

        records[day][
            f"{variable}_coverage"
        ] = coverage

        for statistic in statistics:
            output_column = (
                f"{variable}_{statistic}"
            )

            if n_valid < minimum_required:
                records[day][output_column] = np.nan
            else:
                records[day][output_column] = (
                    calculate_statistic(
                        values,
                        statistic,
                    )
                )


# ==================================================
# CONVERT HOURLY DATA TO DAILY DATA
# ==================================================

def create_daily_dataframe(hourly):
    """
    Convert the complete hourly dataset into daily features.
    """
    data = hourly.copy()

    data["valid_time"] = pd.to_datetime(
        data["valid_time"],
        utc=True,
    )

    data = (
        data.sort_values("valid_time")
        .reset_index(drop=True)
    )

    # UTC → Berlin local time
    data["local_time"] = (
        data["valid_time"]
        .dt.tz_convert(TIMEZONE)
    )

    # Date for instantaneous measurements
    data["instant_date"] = (
        data["local_time"].dt.date
    )

    # Date for measurements representing the preceding hour
    data["interval_date"] = (
        data["local_time"]
        - pd.Timedelta(nanoseconds=1)
    ).dt.date

    daily_records = {}

    common_statistics = [
        "mean",
        "median",
        "min",
        "max",
        "q25",
        "q75",
        "iqr",
        "std",
        "se",
    ]

    # Temperature
    add_daily_statistics(
        daily_records,
        data,
        "instant_date",
        "t2m_c",
        common_statistics,
    )

    # Dew point
    add_daily_statistics(
        daily_records,
        data,
        "instant_date",
        "d2m_c",
        common_statistics,
    )

    # Relative humidity
    add_daily_statistics(
        daily_records,
        data,
        "instant_date",
        "relative_humidity",
        common_statistics,
    )

    # Surface pressure
    add_daily_statistics(
        daily_records,
        data,
        "instant_date",
        "sp_hpa",
        common_statistics,
    )

    # Wind speed
    add_daily_statistics(
        daily_records,
        data,
        "instant_date",
        "wind_speed_m_s",
        common_statistics,
    )

    # Wind components
    add_daily_statistics(
        daily_records,
        data,
        "instant_date",
        "u10",
        ["mean"],
    )

    add_daily_statistics(
        daily_records,
        data,
        "instant_date",
        "v10",
        ["mean"],
    )

    # Precipitation
    add_daily_statistics(
        daily_records,
        data,
        "interval_date",
        "tp_mm",
        [
            "sum",
            "max",
            "wet_hours",
        ],
    )

    # Solar radiation
    add_daily_statistics(
        daily_records,
        data,
        "interval_date",
        "ssrd_w_m2",
        [
            "mean",
            "max",
            "total_mj_m2",
        ],
    )

    daily_df = pd.DataFrame(
        daily_records.values()
    )

    daily_df["date"] = pd.to_datetime(
        daily_df["date"]
    )

    daily_df = (
        daily_df.sort_values("date")
        .reset_index(drop=True)
    )

    # Daily resultant wind
    if {
        "u10_mean",
        "v10_mean",
    }.issubset(daily_df.columns):

        daily_df[
            "wind_resultant_speed_m_s"
        ] = np.hypot(
            daily_df["u10_mean"],
            daily_df["v10_mean"],
        )

        daily_df[
            "wind_direction_deg"
        ] = (
            180
            + np.degrees(
                np.arctan2(
                    daily_df["u10_mean"],
                    daily_df["v10_mean"],
                )
            )
        ) % 360

    return daily_df


# ==================================================
# COMPLETE FOLDER PROCESSING FUNCTION
# ==================================================

def build_era5_daily_dataframe(
    folder_path="era5_land_berlin",
    start_date=START_DATE,
    end_date=END_DATE,
    output_csv=None,
):
    """
    Read all monthly NetCDF files, combine them at hourly
    resolution, preprocess the variables and return one row
    per calendar day.
    """
    folder = Path(folder_path)

    nc_files = sorted(folder.glob("*.nc"))

    if not nc_files:
        raise FileNotFoundError(
            f"No .nc files found in: "
            f"{folder.resolve()}"
        )

    print(f"Found {len(nc_files)} NetCDF files.")

    monthly_hourly_frames = []

    for file_number, file_path in enumerate(
        nc_files,
        start=1,
    ):
        print(
            f"[{file_number}/{len(nc_files)}] "
            f"Reading {file_path.name}"
        )

        monthly_hourly = load_monthly_hourly(
            file_path
        )

        monthly_hourly_frames.append(
            monthly_hourly
        )

    # Concatenate every month before de-accumulation
    all_hourly = pd.concat(
        monthly_hourly_frames,
        ignore_index=True,
    )

    all_hourly = (
        all_hourly
        .groupby(
            "valid_time",
            as_index=False,
        )[WEATHER_COLUMNS]
        .mean()
        .sort_values("valid_time")
        .reset_index(drop=True)
    )

    print(
        "Combined hourly shape:",
        all_hourly.shape,
    )

    # Unit conversions and derived variables
    all_hourly = preprocess_hourly_data(
        all_hourly
    )

    # Hourly → daily
    daily_df = create_daily_dataframe(
        all_hourly
    )

    # Guarantee one row for every requested date
    complete_date_range = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D",
    )

    daily_df = (
        daily_df
        .set_index("date")
        .reindex(complete_date_range)
        .rename_axis("date")
        .reset_index()
    )

    if output_csv is not None:
        output_path = Path(output_csv)

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        daily_df.to_csv(
            output_path,
            index=False,
        )

        print(f"Saved: {output_path.resolve()}")

    print(
        "Final daily shape:",
        daily_df.shape,
    )

    print(
        "Date range:",
        daily_df["date"].min(),
        "to",
        daily_df["date"].max(),
    )

    return daily_df


# ==================================================
# RUN
# ==================================================

daily_df = build_era5_daily_dataframe(
    folder_path="era5_land_berlin",
    start_date="2015-01-01",
    end_date="2024-12-31",
    output_csv=(
        "era5_land_berlin_daily_2015_2024.csv"
    ),
)

direction_map = {
    0: "N",
    1: "NE",
    2: "E",
    3: "SE",
    4: "S",
    5: "SW",
    6: "W",
    7: "NW",
}

direction_index = (
    ((daily_df["wind_direction_deg"] + 22.5) // 45) % 8
)

daily_df["wind_direction_compass"] = (
    direction_index.map(direction_map)
)

print(
    daily_df[
        ["wind_direction_deg", "wind_direction_compass"]
    ].head(20)
)


print(daily_df.head())
print(daily_df.tail())
print("Number of days:", len(daily_df))
print("Number of columns:", len(daily_df.columns))

daily_df = daily_df.drop(
    columns=daily_df.columns[
        daily_df.columns.str.contains(
            "valid|coverage",
            case=False,
            regex=True,
        )
    ]
)

print(daily_df.columns.tolist())

daily_df.to_csv(
    "era5_land_berlin_daily_2015_2024.csv",
    index=False,
)