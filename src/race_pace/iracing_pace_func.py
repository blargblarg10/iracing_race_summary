
from iracingdataapi.client import irDataClient
import os
import shutil
from os.path import join
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import configparser
from statsmodels.nonparametric.smoothers_lowess import lowess
from matplotlib.ticker import FuncFormatter, MultipleLocator
from matplotlib.colors import LinearSegmentedColormap
from concurrent.futures import ThreadPoolExecutor, as_completed

# Global

PKL_DIR = join(os.path.dirname(os.path.abspath(__file__)), "pkl")
GRAPH_DIR = join(os.path.dirname(os.path.abspath(__file__)), "graph")
CRED = join(os.path.dirname(os.path.abspath(__file__)), "credentials.cfg")

# Initialize API CLIENT
class APIClientInitializer:
    def __init__(self, cfg_file):
        self.cfg_file = cfg_file
        self.client = None

    def initialize_api_client(self):
        if not os.path.exists(self.cfg_file):
            self.create_credentials_file()

        print("Loading Credentials")
        config = configparser.ConfigParser()
        config.read(self.cfg_file)
        username = config['credentials']['username']
        password = config['credentials']['password']
        
        print("Establishing connection")
        self.client = self.connect_to_api(username, password)
        return self.client

    def create_credentials_file(self):
        create_file = input(f"Credentials file '{self.cfg_file}' does not exist. Would you like to create it? (y/n): ")
        if create_file.lower() == 'y':
            username = input("Enter email: ")
            password = input("Enter password: ")
            config = configparser.ConfigParser()
            config['credentials'] = {
                'username': username,
                'password': password
            }
            with open(self.cfg_file, 'w') as configfile:
                config.write(configfile)
            print(f"Credentials saved to '{self.cfg_file}'")
        else:
            print("Exiting. Credentials file is required to proceed.")
            exit(1)

    def connect_to_api(self, username, password):
        # Replace this with the actual code to initialize your API client
        return irDataClient(username=username, password=password)

CLIENT = APIClientInitializer(CRED).initialize_api_client()

def test_csv(df, path='./test.csv'):
    df.to_csv(path)


############################################################
# Methods related to the cached Dataframe
############################################################
def clean():
    if os.path.exists(PKL_DIR):
        print(f"Cleaning {PKL_DIR}")
        for filename in os.listdir(PKL_DIR):
            file_path = os.path.join(PKL_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove the file or link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove the subdirectory
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        print(f"Directory {PKL_DIR} does not exist")

def save_dataframe(df, filename):
    if not os.path.exists(PKL_DIR):
        os.mkdir(PKL_DIR)
    else:    
        df.to_pickle(filename)
        print(f"DataFrame saved to {filename}")

def load_dataframe(filename):
    try:
        df = pd.read_pickle(filename)

    except (FileNotFoundError, EOFError):
        print(f"Creating dataframe {filename}")
        df =  pd.DataFrame()

    # Ensure the 'subsession_id' column exists. Only an issue if an empty dataframe is found or created
    if 'subsession_id' not in df.columns:
        df['subsession_id'] = pd.Series(dtype='int')

    return df

############################################################
#   Methods related to the INITIAL gathering and MINOR altering of data directly from the API
#   Minimize how much added columns or restructuring is done from information gathered from the API
#   If refactoring is required. Better to do that in a separate function that calls this parent dataframe 
###########################################################
def series_list():
    return [series["series_name"] for series in CLIENT.series]

def preprocess_lap_data(subsession_id):
    '''
    Preprocessing to add a column to the driver race results. Gives average of 5 best laps if clean and applicable
    '''

    from collections import defaultdict
    import heapq

    laps = CLIENT.result_lap_chart_data(subsession_id=subsession_id)

    # Initialize structures to hold sorted lap times and counts for each customer
    customer_laps = defaultdict(list)
    customer_rating = defaultdict(list)
    customer_clean_laps_count = defaultdict(int)
    customer_total_laps_count = defaultdict(int)

    # Filter, organize laps, and count laps
    for lap in laps:
        cust_id = lap['cust_id']
        customer_total_laps_count[cust_id] += 1

        if not lap['incident'] and lap['lap_number'] > 0 and lap['lap_time'] > 0:
            heapq.heappush(customer_laps[cust_id], lap['lap_time'])
            customer_clean_laps_count[cust_id] += 1

    # Prepare the result
    result = {}
    for cust_id, total_laps in customer_total_laps_count.items():
        lap_times = customer_laps[cust_id]
        clean_laps = customer_clean_laps_count[cust_id]
        
        # If less than 5 clean laps, set average to -1
        if clean_laps < 5:
            average_time = -1
        else:
            # Calculate average of the 5 lowest (best) lap times
            average_time = sum(heapq.nsmallest(5, lap_times)) / 5
        
        result[cust_id]= {
            'avg_time_5': average_time,
            'num_clean_laps': clean_laps,
            'num_total_laps': total_laps
        }

    return result, laps


def merge_summary_and_session(summary, session):
    '''
    Merges Details about lap data from a session with the session results.
    '''
    for driver in session["session_results"][2]["results"]:
        driver_update_keys = summary[driver["cust_id"]]
        driver.update(driver_update_keys)
    return


def correct_race_qual_column(session_dict):
    '''
    For some reason the API for the race session includes the "best qual time" but doesnt properly use it
    That is stored in the qual session under the same name. This code will 
    '''
    # Extract qual and race session results
    qual_results = session_dict["session_results"][1]["results"]
    race_results = session_dict["session_results"][2]["results"]
    
    # Create dictionaries for quick access
    qual_times = {d['cust_id']: d['best_qual_lap_time'] for d in qual_results}
    race_results_by_id = {d['cust_id']: d for d in race_results}

    # Update race session results with qual times
    for cust_id, time in qual_times.items():
        if cust_id in race_results_by_id:
            race_results_by_id[cust_id]['best_qual_lap_time'] = time

    # Assign updated race results back to session dictionary
    session_dict["session_results"][2]["results"] = list(race_results_by_id.values())

    return session_dict


def process_race(session, df):
    subsession_id = session['subsession_id']
    if subsession_id not in df['subsession_id'].values:
        subsession_id = session['subsession_id']
        # Get session data 
        session_results = CLIENT.result(subsession_id=subsession_id, include_licenses=True)

        # Add MINOR revisions to API results by adding all the laps in a session and getting average 5, clean laps, and total laps for each driver
        summary, laps = preprocess_lap_data(subsession_id)
        session_results["race_laps_TSS"] = laps
        merge_summary_and_session(summary, session_results)
        session_results = correct_race_qual_column(session_results)

        return session_results
    else:
        return None


def process_races_with_concurrent(races, df):
    new_data = []
    total_sessions = len(races)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_race, session, df) for session in races]
        
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                new_data.append(result)
            
            print(f'Progress: {len(new_data) / total_sessions * 100:.2f}%', end='\r', flush=True)

    return new_data


def fetch_race_data(series_name, season_year, season_quarter, race_week_num):
    '''
        Primary API method for Races Series Summary Data.
        Gets the subsession of all races in a series, then collects all the data from that subession.
        Returns a Dataframe of that information
    '''    
    # Check if Series name is valid
    races_list = [series['series_name'] for series in CLIENT.series]
    series_id = next((series['series_id'] for series in CLIENT.series if series['series_name'] == series_name), None)
    if series_id is None:
        raise ValueError(f"Series '{series_name}' not found.")

    # Check if a cached dataframe exists. Load it
    df_filename = join(PKL_DIR, f"{season_year}_{season_quarter}_{race_week_num}_{series_name}.pkl")
    df = load_dataframe(df_filename)

    print("Fetching Data")

    # CLIENT API for Session IDs
    races = CLIENT.result_search_series(
        season_year=season_year,
        season_quarter=season_quarter,
        series_id=series_id,
        race_week_num=race_week_num,
        official_only=True,
        event_types=5, #Doesnt matter. Just using this to get session IDs
    )

    new_data = process_races_with_concurrent(races, df)

    if new_data:
        new_data_df = pd.DataFrame(new_data)
        df = pd.concat([df, new_data_df], ignore_index=True)
        save_dataframe(df, df_filename)  # Save updated DataFrame

    return df


# Format time for plots
def format_time(x, pos=None):
    minutes = int(x // 60)
    seconds = x % 60
    return f'{minutes:02d}:{seconds:06.3f}'


def matlib_color(color):
    r, g, b = tuple(int(color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    return (r, g, b)

class TIME_PLOTS:
    def __init__(self, df):
        self.df = df

        self.race_df = self._time_irating_preprocessing()

        self.series_name = df.loc[0, "series_name"]
        self.track_name  = df.loc[0, "track"]["track_name"]

        self.ACCEPT_TYPES = {
                        "Qualify"                  : "best_qual_lap_time",
                        "Average Race Pace"        : "average_lap",
                        "Best 5 Average Race Pace" : "avg_time_5",
                        "Fastest Lap"              : "best_lap_time",
                        }

        self.RATING_TYPES = {
                        "iRating"                  : "oldi_rating",
                        "SOF"                      : "sof",
                } 

    # Prepare data for plotting
    def _time_irating_preprocessing(self):
        # Step 1: Isolate 'subsession_id' and the relevant part of 'session_results'
        
        subsession_ids = self.df['subsession_id']
        sof = self.df['event_strength_of_field']
        nested_data = self.df['session_results'].apply(lambda x: x[2]['results'])

        temp_dfs = []  # Prepare an empty list for collecting DataFrame pieces

        for subsession_id, results, sof in zip(subsession_ids, nested_data, sof):
            temp_df = pd.DataFrame(results)
            temp_df['subsession_id'] = subsession_id
            temp_df['sof'] = sof
            temp_dfs.append(temp_df)

        # Concatenate all DataFrame pieces at once
        return pd.concat(temp_dfs, ignore_index=True)

    #Estimate Lap times
    def plot_box(self, df):
        # Explicitly create a figure and axes
        fig1, ax1 = plt.subplots(figsize=(12, 8))
        df.boxplot(column='best_qual_lap_time', by='old_irating_bin', vert=True, ax=ax1)
        ax1.yaxis.set_major_formatter(FuncFormatter(format_time))
        ax1.set_xlabel('Old iRating Bins')
        ax1.set_ylabel('Best Lap Time (mm:ss.sss)')
        ax1.set_title('Box Plot of Best Lap Time by Old iRating Bins')
        plt.suptitle('')
        plt.xticks(rotation=60)
        plt.show(block=False)  # Or fig1.savefig('boxplot.png') to save instead of showing


    def _estimate_best_lap(self, lowess_result, irating):
        # Find the closest iRating in the LOWESS result and use its corresponding best lap time
        irating_diff = np.abs(lowess_result[:, 0] - irating)
        min_index = np.argmin(irating_diff)
        return lowess_result[min_index, 1]


    def _validate_scatter_type(self, type, rating_type):
        if type in self.ACCEPT_TYPES and rating_type in self.RATING_TYPES:
            return self.ACCEPT_TYPES[type], self.RATING_TYPES[rating_type]
        else:
            print(f"{type} is invalid")
            quit()

    # Main function to orchestrate data fetching, processing, and plotting

    def _time_df_binning(self, df, time_column, rating_colum):
        bin_edges = list(range(0, 10001, 100))
        bin_labels = [f"{bin_edges[i]}-{bin_edges[i+1]-1}" for i in range(len(bin_edges)-1)]
        df = df.copy()
        df.loc[:, 'irating_bin'] = pd.cut(df[rating_colum], bins=bin_edges, labels=bin_labels, include_lowest=True)
        df.loc[:, 'percentile_rank'] = df.groupby('irating_bin', observed=True)[time_column].rank(pct=True)
        return df


    def plot_scatter(self, highlight_driver = [], type = "", rating_type= "iRating", position_mask = None,irating = [2000, 2500, 3000, 3500, 4000]):
        time_column, rating_colum = self._validate_scatter_type(type, rating_type)
        # Converts iracing time to ms and removes anything 
        df = self.race_df.loc[(self.race_df[time_column] >= 0)]

        #Cast column to float to avoid annoying warning
        df = df.astype({f"{time_column}": float})

        if position_mask:
            df = df.loc[(self.race_df['starting_position'] <= position_mask)]
        df.loc[:, time_column] = df.loc[:, time_column]/10000

        # Bin the irating together to apply a color range per bin instead of total time
        df = self._time_df_binning(df, time_column, rating_colum)

        # Colors for gradients
        c = LinearSegmentedColormap.from_list('percentile_cmap', [matlib_color('8bca84'), matlib_color('4169e1'), matlib_color('ff6961')], N=100)
        colors = c(df['percentile_rank'])

        # Scatter Plot
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.scatter(df[rating_colum], df[time_column], c=colors, alpha=0.5)

        # Calculate the y-axis limits based on the fastest time
        fastest_time = df[time_column].min()
        lower_limit = fastest_time * 0.9995  # 0.5% lower than the fastest time
        upper_limit = fastest_time * 1.07   # 7% higher than the fastest time

        # Best fit and Plot Formatting
        lowess_fitted = lowess(df[time_column], df[rating_colum], frac=0.2)    
        ax2.plot(lowess_fitted[:, 0], lowess_fitted[:, 1], '-r', label='LOWESS best fit')
        ax2.yaxis.set_major_formatter(FuncFormatter(format_time))
        ax2.yaxis.set_major_locator(MultipleLocator(0.5))
        ax2.xaxis.set_major_locator(MultipleLocator(500))
        ax2.tick_params(axis='x', rotation=60)
        ax2.set_xlabel('iRating')
        ax2.set_ylabel('Best Lap Time (mm:ss.sss)')
        ax2.set_title(f'{self.series_name} - {self.track_name} : {type} Time vs {rating_type}')
        ax2.set_ylim([lower_limit, upper_limit])  # Apply the calculated y-axis limits
        for ir in irating:
            ax2.axvline(x=ir, color='green', linestyle='--', label=f'Specified iRating ({ir})')    
        ax2.legend()

        # Add plots for specific Drivers
        if highlight_driver is not None:
            for driver in highlight_driver:
                d_name = driver["driver"]
                d_color = driver["color"]
                d_id = driver["cust_id"]
                highlight_df = df[df['cust_id'] == d_id]
                ax2.scatter(highlight_df[rating_colum], highlight_df[time_column], color=d_color, edgecolor='black', alpha=0.75, s=100, label=f'Highlighted (cust_id={d_name})', zorder=3)


        # Info Text Box Stuff
        info_text = [f"Fastest: {format_time(fastest_time)}"]
        info_text.extend([f"3% Goal: {format_time(fastest_time*1.03)}"])
        info_text.extend([f"7% Rule: {format_time(upper_limit)}"])

        estimated_times = [self._estimate_best_lap(lowess_fitted, ir) for ir in irating]
        info_text.extend([f"{ir} Estimate: {format_time(time)}" 
                        for ir, time in zip(irating, estimated_times)])       

        ax2.text(0.05, -0.15, "\n".join(info_text), transform=ax2.transAxes, fontsize=9, 
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # Finally show the plot
        plt.ion()
        plt.tight_layout()
        plt.show()  # Or fig2.savefig('scatterplot.png') to save instead of showing
        
        graph_path = join(GRAPH_DIR,f'{type}.png')
        
        os.makedirs(os.path.dirname(graph_path), exist_ok=True)
        fig2.savefig(graph_path)

        return

DRIVERS = [
    {"driver": "Tyler Somers", "cust_id": 987654,   "color": matlib_color('78081C')},
    {"driver": "Tyler Gefroh", "cust_id": 1014098,  "color": matlib_color('008080')},
    {"driver": "Trent Porter", "cust_id": 879436,   "color": matlib_color('E3BC9A')}
]


def pace_calculator(args):
    print(f"Running with: {args.series_name}, {args.series_year}, {args.season_quarter}, {args.race_week}")

    # Establish connection and retrieve data    
    # for i in CLIENT.series:
    #     print(i["series_name"])
    
    race_df = fetch_race_data(args.series_name, args.series_year, args.season_quarter, args.race_week-1)

    # Preprocess data for time v irating plots
    tp = TIME_PLOTS(race_df)
    
    tp.plot_scatter(highlight_driver=DRIVERS, type="Best 5 Average Race Pace")
    tp.plot_scatter(highlight_driver=DRIVERS, type="Qualify")
    tp.plot_scatter(highlight_driver=DRIVERS, type="Fastest Lap")

    input("Press Enter to close...")


# If you want a standalone example run from within this file
def main():
    class Args:
        def __init__(self, series_name, series_year, season_quarter, race_week):
            self.series_name = series_name
            self.series_year = series_year
            self.season_quarter = season_quarter
            self.race_week = race_week

    default_args = Args("iRacing Porsche Cup By Coach Dave Delta - Fixed", 2024, 3, 2)
    pace_calculator(default_args)


if __name__ == '__main__':
    main()