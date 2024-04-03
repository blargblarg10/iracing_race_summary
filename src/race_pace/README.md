# iRacing Race Summary

## Overview
The `iracing_pace_calc.py` script is the main entry point for calculating race pace data in the iRacing platform. This script fetches, processes, and visualizes race data for various racing series. It is designed to be run from the command line with a variety of arguments to customize the output.

## Script Usage
The script can be executed with the following command:
```bash
python src/race_pace/iracing_pace_calc.py [options]
```

### Arguments
- `-s, --series_name` (type: `str`, default: `iRacing Porsche Cup By Coach Dave Delta - Fixed`)
  - The name of the series.
- `-y, --series_year` (type: `int`, default: current year)
  - The year of the series.
- `-q, --season_quarter` (type: `int`)
  - The quarter of the season (1-4). If empty, current week will be used
- `-w, --race_week` (type: `int`)
  - The week of the race (1-13). If empty, cuirrent week will be used.
- `-c, --clean` (type: `bool`)
  - If set, cleans the pickle directory.
- `-sl, --series_list` (action: `store_true`)
  - Prints the list of available iRacing series.
- `-f, --fixed` (action: `store_true`)
  - Indicates if the series is fixed.
- `-pcup, --pcup` (action: `store_true`)
  - Runs the current week of Porsche Cup.
- `-fl, --fl` (action: `store_true`)
  - Runs the current week of Formula Lights.
- `-f4, --f4` (action: `store_true`)
  - Runs the current week of Formula 4.

### Example Usage
1. **Calculate Race Pace for Porsche Cup**
   ```bash
   python src/race_pace/iracing_pace_calc.py --pcup
   ```

2. **Calculate Race Pace for a Custom Series**
   ```bash
   python src/race_pace/iracing_pace_calc.py --series_name "Custom Series" --series_year 2023 --season_quarter 1 --race_week 5
   ```

### Output
The script generates several outputs:
- **Plots:** Saves scatter plots a race pace data in the `src/race_pace/graph/` directory for average of best 5 laps, qualifying time, and fastest lap.

### Aliases
For convenience, the following aliases are provided:
- `calc_pcup` - Runs Race Pace Calculator on Porsche Cup.
- `calc_pcup -f` - Runs Race Pace Calculator on Porsche Cup - Fixed.
- `calc_fl` - Runs Race Pace Calculator on Formula Lights.
- `calc_fl -f` - Runs Race Pace Calculator on Formula Lights - Fixed.
- `calc_f4` - Runs Race Pace Calculator on Formula 4.
- `calc_f4 -f` - Runs Race Pace Calculator on Formula 4 - Fixed.

To use these aliases, ensure they are defined in your shell environment by sourcing the setup script:
```bash
source setup_env.bsh
```

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.
