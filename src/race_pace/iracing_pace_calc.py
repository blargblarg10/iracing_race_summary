import sys
import datetime
import argparse
from iracing_pace_func import pace_calculator, clean, series_list
from math import ceil

# Constants
DEFAULT_START_DATE = datetime.date(2023, 12, 12)  # The start of 2024 Season 1
DEFAULT_SERIES_NAME = "iRacing Porsche Cup By Coach Dave Delta - Fixed"
CURRENT_YEAR = datetime.datetime.now().year

def calculate_quarter_and_week(start_date):
    current_date = datetime.date.today()
    days_since_start = (current_date - start_date).days
    weeks_since_start = days_since_start / 7
    quarter = int((weeks_since_start // 13) % 4) + 1 # For Some reason this is base 1 while weeks is base 0
    week = ceil(weeks_since_start % 13)  # Plus 1 to go from zero-based to one-based
    return quarter, week

def validate_args(parser):
    # Parse arguments
    args = parser.parse_args()

    # Argument validation: Check that at most one argument is true
    default_true_count = sum([bool(args.pcup), bool(args.fl), bool(args.f4)])
    if default_true_count > 1:
        parser.error('Only one of --pcup, --fl, or --f4 can be specified at a time.')

    if default_true_count == 0 and args.series_name is None:
        parser.error('No Series Name given')

    return args

def main():
    # Argument parser setup
    parser = argparse.ArgumentParser(description="iRacing Race Pace CLI")
    parser.add_argument('-s', '--series_name', type=str, default=DEFAULT_SERIES_NAME, help='Name of the series')
    parser.add_argument('-y', '--series_year', type=int, default=CURRENT_YEAR, help='Year of the series')
    parser.add_argument('-q', '--season_quarter', type=int, help='Quarter of the season (1-4)')
    parser.add_argument('-w', '--race_week', type=int, help='Week of the race (1-13)')
    parser.add_argument('-c', '--clean', type=bool, help='Clean PKL Dir')
    parser.add_argument('-sl', '--series_list', action='store_true', help='Prints list of iRacing Series')
    parser.add_argument('-f', '--fixed', action='store_true', help='Indicate if the series is fixed')


    # Add arguments
    parser.add_argument('-pcup', '--pcup', action='store_true', help='Short Hand to run the current week of Porsche Cup')
    parser.add_argument('-fl', '--fl', action='store_true', help='Short Hand to run the current week of Formula Lights')
    parser.add_argument('-f4', '--f4', action='store_true', help='Short Hand to run the current week of Formula 4')

    args = validate_args(parser)

    if args.series_list:
        print("\n".join(series_list()))
        return 0

    if args.clean:
        clean()
        return 0
    
    if args.season_quarter is None or args.race_week is None:
        quarter, week = calculate_quarter_and_week(DEFAULT_START_DATE)
        args.season_quarter = args.season_quarter or quarter
        args.race_week = args.race_week or week

    # Your code here
    if args.pcup:
        args.series_name = "iRacing Porsche Cup By Coach Dave Delta"
    elif args.fl:
        args.series_name = "Formula C - Super Formula Lights"
    elif args.f4:
        args.series_name = "FIA Formula 4 Challenge"

    # Append " - Fixed" to the series name if the --fixed argument is provided
    if args.fixed:
        args.series_name += " - Fixed"

    # Run function with parsed arguments
    pace_calculator(args)

if __name__ == '__main__':
    main()
