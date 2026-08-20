import calendar
import time

import cdsapi

from cds_credentials import CDS_API_KEY
from config import (
    AREA,
    CDS_API_URL,
    CDS_DATASET,
    CDS_VARIABLES,
    DATA_FORMAT,
    DOWNLOAD_FILE_TEMPLATE,
    DOWNLOAD_FORMAT,
    DOWNLOAD_MONTHS,
    DOWNLOAD_TIMES,
    END_YEAR,
    ERA5_DATA_DIR,
    MAX_DOWNLOAD_ATTEMPTS,
    MINIMUM_EXISTING_FILE_SIZE_BYTES,
    RETRY_WAIT_SECONDS,
    START_YEAR,
)


def create_cds_client():
    """Create an authenticated Climate Data Store client."""
    if not CDS_API_KEY or CDS_API_KEY == "PASTE_YOUR_CDS_API_KEY_HERE":
        raise ValueError(
            "Add your CDS API key to cds_credentials.py before downloading."
        )

    return cdsapi.Client(url=CDS_API_URL, key=CDS_API_KEY)


def build_request(year, month):
    """Build the CDS request for one calendar month."""
    number_of_days = calendar.monthrange(year, month)[1]
    days = [f"{day:02d}" for day in range(1, number_of_days + 1)]

    return {
        "variable": CDS_VARIABLES,
        "year": str(year),
        "month": f"{month:02d}",
        "day": days,
        "time": DOWNLOAD_TIMES,
        "area": AREA,
        "data_format": DATA_FORMAT,
        "download_format": DOWNLOAD_FORMAT,
    }


def download_era5_land():
    """Download raw monthly NetCDF files without processing them."""
    ERA5_DATA_DIR.mkdir(parents=True, exist_ok=True)
    client = create_cds_client()

    for year in range(START_YEAR, END_YEAR + 1):
        for month in DOWNLOAD_MONTHS:
            filename = ERA5_DATA_DIR / DOWNLOAD_FILE_TEMPLATE.format(
                year=year,
                month=month,
            )

            if (
                filename.exists()
                and filename.stat().st_size >= MINIMUM_EXISTING_FILE_SIZE_BYTES
            ):
                print(f"Already exists: {filename}")
                continue

            request = build_request(year, month)
            print(f"\nDownloading {year}-{month:02d}...")

            for attempt in range(1, MAX_DOWNLOAD_ATTEMPTS + 1):
                try:
                    client.retrieve(CDS_DATASET, request, str(filename))
                    print(f"Saved raw file: {filename}")
                    break
                except Exception as error:
                    print(
                        f"Attempt {attempt}/{MAX_DOWNLOAD_ATTEMPTS} failed "
                        f"for {year}-{month:02d}: {error}"
                    )

                    if attempt == MAX_DOWNLOAD_ATTEMPTS:
                        print(
                            f"Skipping {year}-{month:02d}. "
                            "Run the script again later."
                        )
                    else:
                        time.sleep(RETRY_WAIT_SECONDS)


if __name__ == "__main__":
    download_era5_land()