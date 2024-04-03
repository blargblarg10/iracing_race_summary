from dataclasses import dataclass
from typing import List, Dict, Optional
from iracingdataapi.client import irDataClient

class RaceData:
    """Class for storing detailed race data for a user."""
    def __init__(self):
        self.name           = ""
        self.car            = ""
        self.track          = ""
        self.date           = ""
        self.q_time         = ""
        self.q_position     = 0
        self.f_position     = ""
        self.fast_lap       = ""
        self.avg_clean_lap  = 0.0
        self.incident_cnt   = 0
        self.laps           = []
        self.per_clean_lap  = 0.0
        self.old_irating    = 0
        self.new_irating    = 0
        self.old_sr         = 0
        self.new_sr         = 0
        self.sof            = 0
        self.subsession_id  = 0

    def get_date(self):
        # Splitting the date and time parts
        date_part, time_part = self.date.split('T')
        year, month, day = date_part.split('-')
        hour, minute = time_part.split(':')[:2]
        
        # Reformatting the date and time
        date_str = f"{month}.{day}.{year}"
        time_str = f"{hour}:{minute}"
        
        return (date_str, time_str)
    
    def get_ir_diff(self):
        return (self.old_irating - self.new_irating)
    
    def get_sr_diff(self):
        return (self.old_sr - self.new_sr)/100


    def fetch_race_data(user_id: int):
        idc = irDataClient(username=IRACING_USERNAME, password=IRACING_PASSWORD)

        # Fetching race data
        most_recent_race = idc.stats_member_recent_races(cust_id=user_id)['races'][0]
        race_id = most_recent_race['subsession_id']
        race_result = idc.result(subsession_id=race_id)

        my_qual = next((r for r in race_result['session_results'][1]['results'] if r['cust_id'] == user_id), None)
        my_race = next((r for r in race_result['session_results'][2]['results'] if r['cust_id'] == user_id), None)

        # Calculate average lap time and percentage of clean laps
        my_laps = [lap for lap in idc.result_lap_chart_data(subsession_id=race_id) if lap['group_id'] == user_id]
        total_lap_time, laps_with_empty_events, lap_list = 0, 0, []

        for lap in my_laps[1:]:
            lap_list.append({'lap_number': lap['lap_number'], 'lap_time': lap['lap_time'], 'lap_events': lap['lap_events']})
            
            if not lap['lap_events']:
                total_lap_time += lap['lap_time']
                laps_with_empty_events += 1
            else:
                print(f"Lap: {lap['lap_number']} - {', '.join(lap['lap_events'])}")

        average_lap_time = total_lap_time / laps_with_empty_events if laps_with_empty_events else None
        percentage_empty_events = (laps_with_empty_events / len(my_laps) * 100) if my_laps else None

        self.name=my_laps[0]['name'],
        self.car=next((r['car_name'] for r in race_result['session_results'][0]['results'] if r['cust_id'] == user_id), 'Unknown'),
        self.track=race_result['track']['track_name'],
        self.date=most_recent_race['session_start_time'],
        self.q_time=my_qual['best_lap_time'] if my_qual else 'N/A',
        self.q_position=most_recent_race['start_position'],
        self.f_position=most_recent_race['finish_position'],
        self.fast_lap=my_race['best_lap_time'] if my_race else 'N/A',
        self.avg_clean_lap=average_lap_time,
        self.incident_cnt=most_recent_race['incidents'],
        self.laps=lap_list,
        self.per_clean_lap=percentage_empty_events,
        self.old_irating=most_recent_race['oldi_rating'],
        self.new_irating=most_recent_race['newi_rating'],
        self.old_sr=most_recent_race['old_sub_level'],
        self.new_sr=most_recent_race['new_sub_level'],
        self.sof=most_recent_race['strength_of_field'],
        self.subsession_id=race_id


if __name__ == "__main__":
    user_id = 987654
    race_data = fetch_race_data(user_id)
    print(race_data)
