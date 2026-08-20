# ERA5-Land Downloader and Preprocessor

This project downloads hourly ERA5-Land meteorological data from the Copernicus Climate Data Store (CDS). The raw monthly NetCDF files can be used directly, or optionally converted into a daily CSV containing meteorological summary features.

## Project files

```text
project/
├── config.py
├── cds_credentials.py
├── download_era5.py
├── process_meteo.py
├── requirements.txt
└── .gitignore
```

- `config.py`: years, months, variables, coordinates, paths, and processing settings.
- `cds_credentials.py`: private CDS personal access token.
- `download_era5.py`: downloads raw monthly NetCDF files.
- `process_meteo.py`: optionally converts the raw files into a daily CSV.
- `requirements.txt`: required Python packages.

## 1. Requirements

- Python 3.8 or newer.
- A free [Copernicus Climate Data Store account](https://cds.climate.copernicus.eu/).
- Internet access while downloading data.
- Enough disk space for the selected period and variables.

## 2. Configure Copernicus access

1. Register or sign in to the [Climate Data Store](https://cds.climate.copernicus.eu/).
2. Open the [ERA5-Land hourly dataset](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land).
3. Open its download form and accept the dataset Terms of Use. This must be completed manually before API downloads are allowed.
4. Open the official [CDS API setup page](https://cds.climate.copernicus.eu/how-to-api) while signed in.
5. Copy your personal access token into `cds_credentials.py`:

```python
CDS_API_KEY = "YOUR_PERSONAL_ACCESS_TOKEN"
```

Do not add your token to `config.py`, publish it, or commit it to Git.

## 3. Install the project

Keep all project files in the same directory.

### Windows PowerShell

Open PowerShell and move to the project directory:

```powershell
cd "C:\path\to\your\project"
```

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents activation, the commands can be run without activating the environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe download_era5.py
```

### Linux

```bash
cd /path/to/your/project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### macOS

```bash
cd /path/to/your/project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Configure the download

Edit `config.py` before running the downloader.

### Download one month

This example downloads January 2015:

```python
START_YEAR = 2015
END_YEAR = 2015
DOWNLOAD_MONTHS = [1]

START_DATE = "2015-01-01"
END_DATE = "2015-01-31"
```

### Download several months

This downloads March, April, and May for every selected year:

```python
DOWNLOAD_MONTHS = [3, 4, 5]
```

### Download complete years

This downloads every month from 2015 through 2024:

```python
START_YEAR = 2015
END_YEAR = 2024
DOWNLOAD_MONTHS = list(range(1, 13))

START_DATE = "2015-01-01"
END_DATE = "2024-12-31"
```

`DOWNLOAD_MONTHS` is applied to every year in the configured range. For example, `[1, 2]` downloads January and February for every selected year.

### Change the geographic area

The bounding box uses the order north, west, south, east:

```python
AREA = [52.66, 13.25, 52.40, 13.51]
```

The default coordinates cover the Berlin study area. Replace them with the bounding box of the required location.

### Change paths and filenames

```python
ERA5_DATA_DIR = PROJECT_DIR / "era5_land_berlin"
DAILY_OUTPUT_FILE = PROJECT_DIR / "era5_land_berlin_daily_2015_2024.csv"
DOWNLOAD_FILE_TEMPLATE = "era5_land_berlin_{year}_{month:02d}.nc"
```

Both scripts automatically use the paths defined in `config.py`.

## 5. Download raw ERA5-Land data

### Windows

```powershell
python download_era5.py
```

### Linux and macOS

```bash
python download_era5.py
```

The downloader creates the configured data directory and saves one NetCDF file per month. Existing non-empty files are skipped, so an interrupted multi-year download can be resumed by running the same command again.

If only raw ERA5-Land data is needed, no further command is required.

## 6. Optional preprocessing

To convert the raw hourly NetCDF files into a daily CSV, run:

```bash
python process_meteo.py
```

The processor:

- reads every `.nc` file in `ERA5_DATA_DIR`;
- averages the selected grid cells for each UTC hour;
- converts temperature and dew point from kelvin to degrees Celsius;
- converts precipitation to hourly millimetres;
- converts solar radiation to hourly-average watts per square metre;
- converts surface pressure from pascals to hectopascals;
- calculates wind speed, wind direction, and relative humidity;
- converts timestamps to the configured local timezone;
- calculates the configured daily statistics;
- checks daily data coverage; and
- saves the final daily CSV to `DAILY_OUTPUT_FILE`.

The raw NetCDF files are not changed or deleted during preprocessing.

The processor reads all `.nc` files in the configured folder, regardless of `DOWNLOAD_MONTHS`. Ensure `START_DATE` and `END_DATE` describe the period that should appear in the final CSV.

## 7. Troubleshooting

### Missing or placeholder API key

```text
ValueError: Add your CDS API key to cds_credentials.py before downloading.
```

Replace the placeholder in `cds_credentials.py` with the personal access token shown on the CDS API setup page.

### Authentication, licence, 401, or 403 error

- Confirm that the token is current and copied without additional quotation marks inside its value.
- Confirm that the ERA5-Land dataset Terms of Use have been accepted while signed in.
- Upgrade the API client:

```bash
python -m pip install --upgrade "cdsapi>=0.7.7"
```

### Python package not found

```bash
python -m pip install -r requirements.txt
```

Make sure the command uses the same Python installation or virtual environment used to run the scripts.

### No NetCDF files found

Confirm that `ERA5_DATA_DIR` in `config.py` points to the folder containing the downloaded `.nc` files.

### Large downloads

Multi-year requests may take considerable time and storage. This project submits one request per month, which makes downloads resumable and avoids replacing successfully downloaded files.

## Official resources

- [Climate Data Store](https://cds.climate.copernicus.eu/)
- [Official CDS API setup](https://cds.climate.copernicus.eu/how-to-api)
- [ERA5-Land hourly data](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land)
