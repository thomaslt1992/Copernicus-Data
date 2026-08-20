from pathlib import Path


# Project paths
PROJECT_DIR = Path(__file__).resolve().parent
ERA5_DATA_DIR = PROJECT_DIR / "era5_land_berlin"
DAILY_OUTPUT_FILE = (
    PROJECT_DIR / "era5_land_berlin_daily_2015_01.csv"
)


# Download period
START_YEAR = 2015
END_YEAR = 2015

# 1 = January, 12 = December
DOWNLOAD_MONTHS = [1]


# Date range used by the optional processing stage
START_DATE = "2015-01-01"
END_DATE = "2015-01-31"


# ERA5-Land download settings
CDS_API_URL = "https://cds.climate.copernicus.eu/api"
CDS_DATASET = "reanalysis-era5-land"

CDS_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "surface_solar_radiation_downwards",
    "surface_pressure",
]

DOWNLOAD_TIMES = [
    f"{hour:02d}:00"
    for hour in range(24)
]

# North, West, South, East
AREA = [
    52.66,
    13.25,
    52.40,
    13.51,
]

DATA_FORMAT = "netcdf"
DOWNLOAD_FORMAT = "unarchived"

DOWNLOAD_FILE_TEMPLATE = (
    "era5_land_berlin_{year}_{month:02d}.nc"
)

MINIMUM_EXISTING_FILE_SIZE_BYTES = 1
MAX_DOWNLOAD_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 30


# Processing settings
TIMEZONE = "Europe/Berlin"
MINIMUM_COVERAGE = 0.75
WET_HOUR_THRESHOLD_MM = 0.1
NETCDF_PATTERN = "*.nc"
DATE_FREQUENCY = "D"

HOURLY_INTERVAL_HOURS = 1
ACCUMULATION_FIRST_HOUR = 1
INTERVAL_DATE_EPSILON_NANOSECONDS = 1


# Original ERA5-Land columns
WEATHER_COLUMNS = [
    "t2m",
    "d2m",
    "u10",
    "v10",
    "tp",
    "ssrd",
    "sp",
]

ORIGINAL_COLUMNS_TO_DROP = [
    "t2m",
    "d2m",
    "tp",
    "ssrd",
    "sp",
    "number",
    "expver",
]


# Unit-conversion constants
KELVIN_OFFSET = 273.15
METRES_TO_MILLIMETRES = 1_000
SECONDS_PER_HOUR = 3_600
PASCALS_PER_HECTOPASCAL = 100
JOULES_PER_MEGAJOULE = 1_000_000


# Magnus approximation constants
MAGNUS_A = 17.625
MAGNUS_B_CELSIUS = 243.04

MIN_RELATIVE_HUMIDITY = 0
MAX_RELATIVE_HUMIDITY = 100
RELATIVE_HUMIDITY_PERCENT_SCALE = 100


# Statistical constants
LOWER_QUANTILE = 0.25
UPPER_QUANTILE = 0.75

SAMPLE_STANDARD_DEVIATION_DDOF = 1
MINIMUM_VARIANCE_SAMPLE_SIZE = 2


# Daily aggregation settings
COMMON_STATISTICS = [
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

DAILY_AGGREGATIONS = {
    "t2m_c": (
        "instant_date",
        COMMON_STATISTICS,
    ),
    "d2m_c": (
        "instant_date",
        COMMON_STATISTICS,
    ),
    "relative_humidity": (
        "instant_date",
        COMMON_STATISTICS,
    ),
    "sp_hpa": (
        "instant_date",
        COMMON_STATISTICS,
    ),
    "wind_speed_m_s": (
        "instant_date",
        COMMON_STATISTICS,
    ),
    "u10": (
        "instant_date",
        ["mean"],
    ),
    "v10": (
        "instant_date",
        ["mean"],
    ),
    "tp_mm": (
        "interval_date",
        ["sum", "max", "wet_hours"],
    ),
    "ssrd_w_m2": (
        "interval_date",
        ["mean", "max", "total_mj_m2"],
    ),
}


# Wind-direction settings
WIND_DIRECTION_OFFSET_DEGREES = 180
WIND_DIRECTION_FULL_CIRCLE_DEGREES = 360

COMPASS_SECTOR_WIDTH_DEGREES = 45
COMPASS_HALF_SECTOR_DEGREES = 22.5

COMPASS_DIRECTIONS = {
    0: "N",
    1: "NE",
    2: "E",
    3: "SE",
    4: "S",
    5: "SW",
    6: "W",
    7: "NW",
}


# Columns removed from the final dataset
FINAL_DROP_COLUMN_PATTERN = r"valid|coverage"