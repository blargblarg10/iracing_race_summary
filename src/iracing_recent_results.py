from dataclasses import dataclass
from typing import List, Dict, Optional
from iracingdataapi.client import irDataClient

# Assuming environment variables are used for credentials
IRACING_USERNAME = "tssomersasu@gmail.com"
IRACING_PASSWORD = "Phxfire1557"

@dataclass
class RaceData:
    """Class for storing detailed race data for a user."""
    name: str
    car: str
    track: str
    date: str
    q_time: str
    q_position: int
    f_position: str
    fast_lap: str
    avg_clean_lap: Optional[float]
    incident_cnt: int
    laps: List[Dict[int, any]]
    per_clean_lap: Optional[float]
    old_irating: int
    new_irating: int
    old_sr: int
    new_sr: int
    sof: int
    subsession_id: int

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


def fetch_race_data(user_id: int) -> RaceData:
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

    return RaceData(
        name=my_laps[0]['name'],
        car=next((r['car_name'] for r in race_result['session_results'][0]['results'] if r['cust_id'] == user_id), 'Unknown'),
        track=race_result['track']['track_name'],
        date=most_recent_race['session_start_time'],
        q_time=my_qual['best_lap_time'] if my_qual else 'N/A',
        q_position=most_recent_race['start_position'],
        f_position=most_recent_race['finish_position'],
        fast_lap=my_race['best_lap_time'] if my_race else 'N/A',
        avg_clean_lap=average_lap_time,
        incident_cnt=most_recent_race['incidents'],
        laps=lap_list,
        per_clean_lap=percentage_empty_events,
        old_irating=most_recent_race['oldi_rating'],
        new_irating=most_recent_race['newi_rating'],
        old_sr=most_recent_race['old_sub_level'],
        new_sr=most_recent_race['new_sub_level'],
        sof=most_recent_race['strength_of_field'],
        subsession_id=race_id
    )

if __name__ == "__main__":
    user_id = 987654
    race_data = fetch_race_data(user_id)
    print(race_data)
