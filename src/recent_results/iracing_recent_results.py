from dataclasses import dataclass
from typing import List, Dict, Optional
from iracingdataapi.client import irDataClient
import os
from os.path import join
import configparser
import pandas as pd

# Global
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

class RaceData:
    """Class for storing detailed race data for a user."""
    def __init__(self, user_id):
        self.user_id = user_id
        self.races_data = []
        self.fetch_race_data()

    def _convert_ticks_to_time(self, ticks):
        seconds = ticks / 10000
        minutes = int(seconds // 60)
        seconds = seconds % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        return f"{minutes}:{seconds}.{milliseconds}"

    def print_race_data(self):
        for race in self.races_data:
            print("\nRace Data:")
            for key, value in race.items():
                print(f"{key}: {value}")

    def fetch_race_data(self):
        # Fetch recent races
        recent_races = CLIENT.stats_member_recent_races(cust_id=self.user_id)['races']
        
        if not recent_races:
            print("No recent races found.")
            return

        # Identify the track name of the most recent race
        track_name = recent_races[0]['track']['track_name']

        # Filter all races that have the same track name
        same_track_races = [race for race in recent_races if race['track']['track_name'] == track_name]

        for race in same_track_races:
            race_id = race['subsession_id']
            race_result = CLIENT.result(subsession_id=race_id)

            my_qual = next((r for r in race_result['session_results'][1]['results'] if r['cust_id'] == self.user_id), None)
            my_race = next((r for r in race_result['session_results'][2]['results'] if r['cust_id'] == self.user_id), None)

            my_laps = [lap for lap in CLIENT.result_lap_chart_data(subsession_id=race_id) if lap['group_id'] == self.user_id]
            total_clean_lap_time, laps_with_empty_events, lap_list = 0, 0, []

            for lap in my_laps[1:]:
                lap_list.append({'lap_number': lap['lap_number'], 'lap_time': lap['lap_time'], 'lap_events': lap['lap_events']})
                
                if not lap['lap_events']:
                    total_clean_lap_time += lap['lap_time']
                    laps_with_empty_events += 1
                else:
                    pass
                    # print(f"Lap: {lap['lap_number']} - {', '.join(lap['lap_events'])}")

            average_lap_time = total_clean_lap_time / laps_with_empty_events if laps_with_empty_events else None
            percentage_empty_events = (laps_with_empty_events / len(my_laps) * 100) if my_laps else None

            race_data = {
                'subsession_id': race_id,
                'date': race['session_start_time'],
                'track': race['track']['track_name'],
                'name': my_laps[0]['name'] if my_laps else 'Unknown',
                'car': next((r['car_name'] for r in race_result['session_results'][0]['results'] if r['cust_id'] == self.user_id), 'Unknown'),
                'q_time': my_qual['best_lap_time'] if my_qual else 'N/A',
                'q_position': race['start_position'],
                'f_position': race['finish_position'],
                'fast_lap': my_race['best_lap_time'] if my_race else 'N/A',
                'avg_clean_lap': average_lap_time,
                'incident_cnt': race['incidents'],
                'laps': lap_list,
                'per_clean_lap': percentage_empty_events,
                'old_irating': race['oldi_rating'],
                'new_irating': race['newi_rating'],
                'irating_delta': race['newi_rating'] - race['oldi_rating'],
                'old_sr': race['old_sub_level'] / 100,
                'new_sr': race['new_sub_level'] / 100,
                'sr_delta': (race['new_sub_level'] - race['old_sub_level']) / 100,
                'sof': race['strength_of_field'],
            }

            self.races_data.append(race_data)

    def analyze_race_week(self):
        if not self.races_data:
            print("No race data to analyze.")
            return

        # Sort races by date
        sorted_races = sorted(self.races_data, key=lambda x: x['date'])

        # Compare oldest and newest iRating and Safety Rating
        oldest_irating = sorted_races[0]['old_irating']
        newest_irating = sorted_races[-1]['new_irating']
        irating_diff = newest_irating - oldest_irating

        oldest_sr = sorted_races[0]['old_sr']
        newest_sr = sorted_races[-1]['new_sr']
        sr_diff = round(newest_sr - oldest_sr,2)

        num_races = len(sorted_races)
        
        df = pd.DataFrame(sorted_races)

        df = df['sof'] + df['irating_delta']
        week_skill_ir = df.sum()/num_races

        # Calculate averages
        avg_incidents = round(sum(race['incident_cnt'] for race in sorted_races) / num_races, 2)
        avg_q_time = round(sum(race['q_time'] for race in sorted_races if race['q_time'] != 'N/A') / len([race for race in sorted_races if race['q_time'] != 'N/A']), 2)
        avg_q_position = round(sum(race['q_position'] for race in sorted_races) / num_races, 2)
        avg_sof = round(sum(race['sof'] for race in sorted_races) / num_races, 2)
        avg_f_position = round(sum(race['f_position'] for race in sorted_races) / num_races, 2)


        # Print the results
        print(f"Track: {sorted_races[0]["track"]} - Num Races: {num_races}")
        print(f"Average qualifying time: {self._convert_ticks_to_time(avg_q_time)}")
        print(f"Average qualifying position: {avg_q_position}")
        print(f"Average finishing position: {avg_f_position}")
        print(f"iRating change: {irating_diff}")
        print(f"Safety Rating: {sr_diff}")
        print(f"Average incidents: {avg_incidents}")
        print(f"Average strength of field: {avg_sof}")
        print(f"Week Rating Score: {week_skill_ir}")

if __name__ == "__main__":
    tyler_week = RaceData(987654)
    tyler_week.analyze_race_week()
    trent_week = RaceData(879436)
    trent_week.analyze_race_week()
