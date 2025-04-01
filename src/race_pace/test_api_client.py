import os
import sys
import configparser
from iracing_api_client import IracingAPIClient

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Path to your credentials configuration file
CRED_FILE = os.path.join(current_dir, "credentials.cfg")

def test_api_client():
    """
    Test the enhanced API client by connecting and fetching various data types.
    """
    # Load credentials
    if not os.path.exists(CRED_FILE):
        username = input("Enter your iRacing email: ")
        password = input("Enter your iRacing password: ")
        
        # Create credentials file
        config = configparser.ConfigParser()
        config['credentials'] = {
            'username': username,
            'password': password
        }
        with open(CRED_FILE, 'w') as configfile:
            config.write(configfile)
        print(f"Credentials saved to '{CRED_FILE}'")
    else:
        config = configparser.ConfigParser()
        config.read(CRED_FILE)
        username = config['credentials']['username']
        password = config['credentials']['password']

    # Initialize API client
    print("Initializing API client...")
    client = IracingAPIClient(username, password)
    
    # Test fetching series data
    print("\n1. Fetching series data...")
    series_data = client.series()
    if series_data:
        print(f"Found {len(series_data)} series")
        # Print the first few series as examples
        print("Example series:")
        for s in series_data[:5]:
            print(f"  - {s}")
    else:
        print("Failed to fetch series data")
    
    # Test fetching car classes
    print("\n2. Fetching car classes...")
    car_classes = client.get_carclasses()
    if car_classes:
        print(f"Found {len(car_classes)} car classes")
        # Print a few car classes as examples
        print("Example car classes:")
        for cc in car_classes[:3]:
            print(f"  - {cc.get('name', 'Unknown')} (ID: {cc.get('car_class_id', 'Unknown')})")
    else:
        print("Failed to fetch car classes")
    
    # Test fetching license information
    print("\n3. Fetching license information...")
    licenses = client.lookup_licenses()
    if licenses:
        print(f"Found {len(licenses)} license types")
        # Print a few licenses as examples
        print("Example licenses:")
        for lic in licenses[:5]:
            print(f"  - {lic.get('license_group', 'Unknown')}: {lic.get('group_name', 'Unknown')}")
    else:
        print("Failed to fetch license information")
    
    # Test fetching recent races
    print("\n4. Fetching recent races...")
    # You can replace this with a real customer ID if desired
    cust_id = 120570  
    recent_races = client.stats_member_recent_races(cust_id)
    if recent_races and 'races' in recent_races:
        print(f"Found {len(recent_races['races'])} recent races")
        if recent_races['races']:
            # Print the first race as an example
            race = recent_races['races'][0]
            print(f"Example race: {race.get('track', {}).get('track_name', 'Unknown')} on {race.get('session_start_time', 'Unknown')}")
            print(f"  Series: {race.get('series_name', 'Unknown')}")
            print(f"  Position: {race.get('finish_position', 'Unknown')}/{race.get('field_size', 'Unknown')}")
            print(f"  iRating change: {race.get('newi_rating', 0) - race.get('oldi_rating', 0)}")
    else:
        print("Failed to fetch recent races")
    
    # Test series seasons
    print("\n5. Fetching series seasons...")
    seasons = client.series_seasons(include_series=True)
    if seasons:
        print(f"Found {len(seasons)} series seasons")
        # Print a few seasons as examples
        print("Example seasons:")
        count = 0
        for season in seasons:
            if count >= 3:
                break
            if 'series_name' in season:
                print(f"  - {season.get('series_name', 'Unknown')}: Season {season.get('season_id', 'Unknown')}")
                count += 1
    else:
        print("Failed to fetch series seasons")

if __name__ == "__main__":
    test_api_client()