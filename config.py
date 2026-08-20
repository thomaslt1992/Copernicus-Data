from pathlib import Path


# Project paths
PROJECT_DIR = Path(__file__).resolve().parent
ERA5_DATA_DIR = PROJECT_DIR / "era5_land_berlin" #change your folder name 
DAILY_OUTPUT_FILE = PROJECT_DIR / "era5_land_berlin_daily_2015_2024.csv" #change your file name


# Study period
START_YEAR = 2015
END_YEAR = 2024
START_DATE = f"{START_YEAR}-01-01"
END_DATE = f"{END_YEAR}-12-31"


# ERA5-Land download settings
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
DOWNLOAD_TIMES = [f"{hour:02d}:00" for hour in range(24)]

AREA = [52.66, 13.25, 52.40, 13.51]

DATA_FORMAT = "netcdf"
DOWNLOAD_FORMAT = "unarchived"
DOWNLOAD_FILE_TEMPLATE = "era5_land_berlin_{year}_{month:02d}.nc"
MAX_DOWNLOAD_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 30


# Processing settings
TIMEZONE = "Europe/Berlin"
MINIMUM_COVERAGE = 0.75
WET_HOUR_THRESHOLD_MM = 0.1
NETCDF_PATTERN = "*.nc"

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


# Unit conversion constants
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
    "t2m_c": ("instant_date", COMMON_STATISTICS),
    "d2m_c": ("instant_date", COMMON_STATISTICS),
    "relative_humidity": ("instant_date", COMMON_STATISTICS),
    "sp_hpa": ("instant_date", COMMON_STATISTICS),
    "wind_speed_m_s": ("instant_date", COMMON_STATISTICS),
    "u10": ("instant_date", ["mean"]),
    "v10": ("instant_date", ["mean"]),
    "tp_mm": ("interval_date", ["sum", "max", "wet_hours"]),
    "ssrd_w_m2": (
        "interval_date",
        ["mean", "max", "total_mj_m2"],
    ),
}


# Wind-direction settings
WIND_DIRECTION_OFFSET_DEGREES = 180
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


# Columns omitted from the final modelling dataset
FINAL_DROP_COLUMN_PATTERN = r"valid|coverage"
