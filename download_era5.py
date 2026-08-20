from pathlib import Path
import calendar
import time

import cdsapi


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

START_YEAR = 2015
END_YEAR = 2024

OUTPUT_DIR = Path("era5_land_berlin")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATASET = "reanalysis-era5-land"

VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "surface_solar_radiation_downwards",
    "surface_pressure",
]

TIMES = [f"{hour:02d}:00" for hour in range(24)]

# Order: North, West, South, East
AREA = [
    52.66,
    13.25,
    52.40,
    13.51,
]


# --------------------------------------------------
# DOWNLOAD
# --------------------------------------------------

client = cdsapi.Client()

for year in range(START_YEAR, END_YEAR + 1):
    for month in range(1, 13):

        filename = OUTPUT_DIR / (
            f"era5_land_berlin_{year}_{month:02d}.nc"
        )

        if filename.exists() and filename.stat().st_size > 0:
            print(f"Already exists: {filename}")
            continue

        number_of_days = calendar.monthrange(year, month)[1]
        days = [
            f"{day:02d}"
            for day in range(1, number_of_days + 1)
        ]

        request = {
            "variable": VARIABLES,
            "year": str(year),
            "month": f"{month:02d}",
            "day": days,
            "time": TIMES,
            "area": AREA,
            "data_format": "netcdf",
            "download_format": "unarchived",
        }

        print(f"\nDownloading {year}-{month:02d}...")

        for attempt in range(1, 4):
            try:
                client.retrieve(
                    DATASET,
                    request,
                    str(filename),
                )

                print(f"Saved: {filename}")
                break

            except Exception as error:
                print(
                    f"Attempt {attempt}/3 failed for "
                    f"{year}-{month:02d}: {error}"
                )

                if attempt == 3:
                    print(
                        f"Skipping {year}-{month:02d}. "
                        "Run the script again later."
                    )
                else:
                    time.sleep(30)