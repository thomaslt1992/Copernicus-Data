from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from config import (
    ACCUMULATION_FIRST_HOUR,
    COMPASS_DIRECTIONS,
    COMPASS_HALF_SECTOR_DEGREES,
    COMPASS_SECTOR_WIDTH_DEGREES,
    DAILY_AGGREGATIONS,
    DAILY_OUTPUT_FILE,
    DATE_FREQUENCY,
    END_DATE,
    ERA5_DATA_DIR,
    FINAL_DROP_COLUMN_PATTERN,
    HOURLY_INTERVAL_HOURS,
    INTERVAL_DATE_EPSILON_NANOSECONDS,
    JOULES_PER_MEGAJOULE,
    KELVIN_OFFSET,
    LOWER_QUANTILE,
    MAGNUS_A,
    MAGNUS_B_CELSIUS,
    MAX_RELATIVE_HUMIDITY,
    METRES_TO_MILLIMETRES,
    MIN_RELATIVE_HUMIDITY,
    MINIMUM_COVERAGE,
    MINIMUM_VARIANCE_SAMPLE_SIZE,
    NETCDF_PATTERN,
    ORIGINAL_COLUMNS_TO_DROP,
    PASCALS_PER_HECTOPASCAL,
    RELATIVE_HUMIDITY_PERCENT_SCALE,
    SAMPLE_STANDARD_DEVIATION_DDOF,
    SECONDS_PER_HOUR,
    START_DATE,
    TIMEZONE,
    UPPER_QUANTILE,
    WEATHER_COLUMNS,
    WET_HOUR_THRESHOLD_MM,
    WIND_DIRECTION_OFFSET_DEGREES,
    WIND_DIRECTION_FULL_CIRCLE_DEGREES,
)


def nc_to_pandas(file_path):
    """Read a NetCDF file and return a pandas DataFrame."""
    with xr.open_dataset(file_path) as dataset:
        return dataset.to_dataframe().reset_index()


def load_monthly_hourly(file_path):
    """Read one monthly file and spatially average its grid cells."""
    df = nc_to_pandas(file_path)

    if "valid_time" not in df.columns:
        raise ValueError(f"'valid_time' is missing from {file_path}")

    missing_columns = [
        column for column in WEATHER_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing columns in {file_path}: {missing_columns}")

    df["valid_time"] = pd.to_datetime(df["valid_time"], utc=True)

    return (
        df.groupby("valid_time", as_index=False)[WEATHER_COLUMNS]
        .mean()
        .sort_values("valid_time")
        .reset_index(drop=True)
    )


def deaccumulate_era5_land(series, timestamps):
    """Convert cumulative ERA5-Land values into hourly increments."""
    hours = timestamps.dt.hour
    consecutive = timestamps.diff().eq(
        pd.Timedelta(hours=HOURLY_INTERVAL_HOURS)
    )
    hourly = series.diff()
    hourly.loc[hours == ACCUMULATION_FIRST_HOUR] = series.loc[
        hours == ACCUMULATION_FIRST_HOUR
    ]
    hourly.loc[
        ~consecutive & (hours != ACCUMULATION_FIRST_HOUR)
    ] = np.nan
    return hourly.clip(lower=0)


def preprocess_hourly_data(df_hourly):
    """Convert units and create the derived hourly variables."""
    hourly = df_hourly.sort_values("valid_time").reset_index(drop=True).copy()

    hourly["t2m_c"] = hourly["t2m"] - KELVIN_OFFSET
    hourly["d2m_c"] = hourly["d2m"] - KELVIN_OFFSET
    hourly["tp_mm"] = (
        deaccumulate_era5_land(hourly["tp"], hourly["valid_time"])
        * METRES_TO_MILLIMETRES
    )
    hourly["ssrd_w_m2"] = (
        deaccumulate_era5_land(hourly["ssrd"], hourly["valid_time"])
        / SECONDS_PER_HOUR
    )
    hourly["sp_hpa"] = hourly["sp"] / PASCALS_PER_HECTOPASCAL
    hourly["wind_speed_m_s"] = np.hypot(hourly["u10"], hourly["v10"])
    hourly["relative_humidity"] = (
        RELATIVE_HUMIDITY_PERCENT_SCALE
        * np.exp(
            (MAGNUS_A * hourly["d2m_c"])
            / (MAGNUS_B_CELSIUS + hourly["d2m_c"])
        )
        / np.exp(
            (MAGNUS_A * hourly["t2m_c"])
            / (MAGNUS_B_CELSIUS + hourly["t2m_c"])
        )
    ).clip(MIN_RELATIVE_HUMIDITY, MAX_RELATIVE_HUMIDITY)

    return hourly.drop(columns=ORIGINAL_COLUMNS_TO_DROP, errors="ignore")


def expected_hours_for_day(day):
    """Return 23, 24, or 25 hours according to daylight saving time."""
    start = pd.Timestamp(day).tz_localize(TIMEZONE)
    end = (
        pd.Timestamp(day) + pd.Timedelta(days=1)
    ).tz_localize(TIMEZONE)
    duration = end.tz_convert("UTC") - start.tz_convert("UTC")
    return int(duration / pd.Timedelta(hours=HOURLY_INTERVAL_HOURS))


def calculate_statistic(values, statistic):
    """Calculate one configured daily statistic."""
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
        return values.quantile(LOWER_QUANTILE)
    if statistic == "q75":
        return values.quantile(UPPER_QUANTILE)
    if statistic == "iqr":
        return values.quantile(UPPER_QUANTILE) - values.quantile(
            LOWER_QUANTILE
        )
    if statistic == "std":
        return (
            values.std(ddof=SAMPLE_STANDARD_DEVIATION_DDOF)
            if n >= MINIMUM_VARIANCE_SAMPLE_SIZE
            else np.nan
        )
    if statistic == "se":
        return (
            values.std(ddof=SAMPLE_STANDARD_DEVIATION_DDOF) / np.sqrt(n)
            if n >= MINIMUM_VARIANCE_SAMPLE_SIZE
            else np.nan
        )
    if statistic == "sum":
        return values.sum()
    if statistic == "wet_hours":
        return (values >= WET_HOUR_THRESHOLD_MM).sum()
    if statistic == "total_mj_m2":
        return values.sum() * SECONDS_PER_HOUR / JOULES_PER_MEGAJOULE

    raise ValueError(f"Unknown statistic: {statistic}")


def add_daily_statistics(
    records,
    data,
    date_column,
    variable,
    statistics,
):
    """Add configured statistics when daily data coverage is sufficient."""
    if variable not in data.columns:
        print(f"Skipping missing variable: {variable}")
        return

    for day, group in data.groupby(date_column):
        records.setdefault(day, {"date": day})
        values = group[variable].dropna()
        n_valid = len(values)
        expected_hours = expected_hours_for_day(day)
        coverage = n_valid / expected_hours
        minimum_required = int(np.ceil(expected_hours * MINIMUM_COVERAGE))

        records[day][f"{variable}_n_valid"] = n_valid
        records[day][f"{variable}_coverage"] = coverage

        for statistic in statistics:
            output_column = f"{variable}_{statistic}"
            records[day][output_column] = (
                calculate_statistic(values, statistic)
                if n_valid >= minimum_required
                else np.nan
            )


def create_daily_dataframe(hourly):
    """Convert the complete hourly dataset into daily features."""
    data = hourly.copy()
    data["valid_time"] = pd.to_datetime(data["valid_time"], utc=True)
    data = data.sort_values("valid_time").reset_index(drop=True)
    data["local_time"] = data["valid_time"].dt.tz_convert(TIMEZONE)
    data["instant_date"] = data["local_time"].dt.date
    data["interval_date"] = (
        data["local_time"]
        - pd.Timedelta(nanoseconds=INTERVAL_DATE_EPSILON_NANOSECONDS)
    ).dt.date

    daily_records = {}
    for variable, (date_column, statistics) in DAILY_AGGREGATIONS.items():
        add_daily_statistics(
            daily_records,
            data,
            date_column,
            variable,
            statistics,
        )

    daily_df = pd.DataFrame(daily_records.values())
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df = daily_df.sort_values("date").reset_index(drop=True)

    if {"u10_mean", "v10_mean"}.issubset(daily_df.columns):
        daily_df["wind_resultant_speed_m_s"] = np.hypot(
            daily_df["u10_mean"],
            daily_df["v10_mean"],
        )
        daily_df["wind_direction_deg"] = (
            WIND_DIRECTION_OFFSET_DEGREES
            + np.degrees(
                np.arctan2(
                    daily_df["u10_mean"],
                    daily_df["v10_mean"],
                )
            )
        ) % WIND_DIRECTION_FULL_CIRCLE_DEGREES

        direction_index = (
            (
                daily_df["wind_direction_deg"]
                + COMPASS_HALF_SECTOR_DEGREES
            )
            // COMPASS_SECTOR_WIDTH_DEGREES
        ) % len(COMPASS_DIRECTIONS)
        daily_df["wind_direction_compass"] = direction_index.map(
            COMPASS_DIRECTIONS
        )

    return daily_df


def build_era5_daily_dataframe(
    folder_path=ERA5_DATA_DIR,
    start_date=START_DATE,
    end_date=END_DATE,
    output_csv=DAILY_OUTPUT_FILE,
):
    """Read raw NetCDF files and build one modelling row per day."""
    folder = Path(folder_path)
    nc_files = sorted(folder.glob(NETCDF_PATTERN))

    if not nc_files:
        raise FileNotFoundError(f"No NetCDF files found in: {folder.resolve()}")

    print(f"Found {len(nc_files)} raw NetCDF files.")
    monthly_frames = []

    for file_number, file_path in enumerate(nc_files, start=1):
        print(f"[{file_number}/{len(nc_files)}] Reading {file_path.name}")
        monthly_frames.append(load_monthly_hourly(file_path))

    all_hourly = pd.concat(monthly_frames, ignore_index=True)
    all_hourly = (
        all_hourly.groupby("valid_time", as_index=False)[WEATHER_COLUMNS]
        .mean()
        .sort_values("valid_time")
        .reset_index(drop=True)
    )

    daily_df = create_daily_dataframe(preprocess_hourly_data(all_hourly))
    complete_date_range = pd.date_range(
        start=start_date,
        end=end_date,
        freq=DATE_FREQUENCY,
    )
    daily_df = (
        daily_df.set_index("date")
        .reindex(complete_date_range)
        .rename_axis("date")
        .reset_index()
    )

    daily_df = daily_df.drop(
        columns=daily_df.columns[
            daily_df.columns.str.contains(
                FINAL_DROP_COLUMN_PATTERN,
                case=False,
                regex=True,
            )
        ]
    )

    if output_csv is not None:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        daily_df.to_csv(output_path, index=False)
        print(f"Saved processed file: {output_path.resolve()}")

    print(f"Final daily shape: {daily_df.shape}")
    print(f"Date range: {daily_df['date'].min()} to {daily_df['date'].max()}")
    return daily_df


if __name__ == "__main__":
    build_era5_daily_dataframe()