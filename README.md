# iRacing Tools

This repository contains a collection of tools for analyzing iRacing data, especially focused on race pace analysis, recent results tracking, and telemetry file sharing.

## Overview

The main tools in this repository include:

1. **Race Pace Calculator** - Analyzes race data to show pace vs. iRating correlations
2. **Recent Results Analyzer** - Tracks and analyzes your recent race results at a specific track
3. **Telemetry Uploader** - Quickly uploads telemetry files to Dropbox for sharing

## Installation

### Prerequisites

- Python 3.7 or newer
- Required packages (see `python_requirements.txt`)

### Setup

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd iracing-tools
   ```

2. Set up the environment:
   ```bash
   source setup_env.bsh
   ```
   This script will create a conda environment, install dependencies, and set up aliases.

3. Add your credentials:
   - When you first run any of the tools, you'll be prompted to enter your iRacing credentials
   - For the Dropbox uploader, you'll need to add a Dropbox API token to `src/dropbox_upload/dropbox.cfg`

## Usage

### Race Pace Calculator

The `iracing_pace_calc.py` script calculates and visualizes race pace data for different iRacing series.

```bash
# Using aliases (after running setup_env.bsh)
calc_pcup     # Porsche Cup
calc_pcup -f  # Porsche Cup Fixed
calc_fl       # Formula Lights
calc_f4       # Formula 4

# Or run directly with custom options
python src/race_pace/iracing_pace_calc.py --series_name "Formula C - Super Formula Lights" --series_year 2024 --season_quarter 2 --race_week 3
```

### Options

- `-s, --series_name`: Name of the series
- `-y, --series_year`: Year of the series (default: current year)
- `-q, --season_quarter`: Quarter of the season (1-4)
- `-w, --race_week`: Week of the race (1-13)
- `-c, --clean`: Clean the cached data directory
- `-sl, --series_list`: Print list of available iRacing series
- `-f, --fixed`: Indicate if the series is fixed
- `-pcup, --pcup`: Shorthand for Porsche Cup
- `-fl, --fl`: Shorthand for Formula Lights
- `-f4, --f4`: Shorthand for Formula 4

### Outputs

The script generates several graphs in the `src/race_pace/graph/` directory:
- Best 5 Average Race Pace
- Qualifying times
- Fastest Lap times

All graphs show the correlation between lap times and iRating.

### Recent Results Analyzer

The `iracing_recent_results.py` script analyzes your recent race results at the same track.

```bash
python src/recent_results/iracing_recent_results.py
```

You'll need to edit the script to set your customer ID at the bottom.

### Telemetry Uploader

The `ir_tm_db.py` script uploads the most recent telemetry file to Dropbox and creates a shareable link.

```bash
python src/dropbox_upload/ir_tm_db.py
```

## Configuration

### Credentials

Credentials are stored in `credentials.cfg` files in each tool's directory. If the file doesn't exist, you'll be prompted to create it when you run the tool.

### Dropbox Upload

For the Dropbox uploader, you'll need to:
1. Create a Dropbox app in the [Dropbox Developer Console](https://www.dropbox.com/developers/apps)
2. Generate an access token
3. Create a `dropbox.cfg` file in the `src/dropbox_upload/` directory with:
   ```
   [Dropbox]
   ACCESS_TOKEN = your_access_token
   TELEMETRY_DIR = path_to_telemetry_directory
   ```

## API Implementation

This project uses direct API calls to iRacing's new API endpoints. The custom client implementation handles authentication, request caching, and data formatting.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.