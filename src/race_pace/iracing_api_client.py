import requests
import json
import hashlib
import base64
import time
from urllib.parse import urljoin
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

class IracingAPIClient:
    """
    A client for interacting with the new iRacing API.
    This replaces the deprecated iracingdataapi package.
    """
    
    BASE_URL = 'https://members-ng.iracing.com/'
    
    def __init__(self, username=None, password=None, silent=False):
        self.session = requests.Session()
        self.auth_token = None
        self.cache = {}
        self.authenticated = False
        self.silent = silent
        self.username = username
        
        if username and password:
            self.encoded_password = self._hash_password(password, username)
            self.login(username, self.encoded_password)
    
    def _hash_password(self, password, username):
        """
        Hash the password according to iRacing's new authentication method.
        1. Convert the username to lowercase
        2. Concatenate password and lowercase username
        3. Create SHA256 hash
        4. Encode in Base64
        """
        username = username.lower()
        concat = password + username
        hash_obj = hashlib.sha256(concat.encode())
        hashed_pw = base64.b64encode(hash_obj.digest()).decode()
        return hashed_pw
    
    def login(self, username, password_hash=None):
        """
        Log in to the iRacing API using the provided credentials.
        
        Args:
            username (str): iRacing email/username
            password_hash (str): Pre-hashed password (if None, assumes password is already hashed)
        """
        auth_url = urljoin(self.BASE_URL, 'auth')
        headers = {"Content-Type": "application/json"}
        
        try:
            # Use either the provided hash or the already encoded password
            hashed_password = password_hash or self.encoded_password
            
            payload = {
                'email': username,
                'password': hashed_password
            }
            
            response = self.session.post(auth_url, headers=headers, json=payload, timeout=10.0)
            
            # Handle rate limiting
            if response.status_code == 429:
                ratelimit_reset = response.headers.get('x-ratelimit-reset')
                if ratelimit_reset:
                    reset_datetime = datetime.fromtimestamp(int(ratelimit_reset))
                    delta = reset_datetime - datetime.now() + timedelta(milliseconds=500)
                    if not self.silent:
                        print(f"Rate limited, waiting {delta.total_seconds()} seconds")
                    if delta.total_seconds() > 0:
                        time.sleep(delta.total_seconds())
                    return self.login(username, password_hash)
                    
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('authcode'):
                    self.authenticated = True
                    if not self.silent:
                        print("Authentication successful")
                    return "Logged in"
                else:
                    print(f"Authentication failed: {response.status_code} - {response.text}")
                    return None
            else:
                print(f"Authentication failed: {response.status_code} - {response.text}")
                return None
        except requests.Timeout:
            print("Login request timed out")
            return None
        except Exception as e:
            print(f"Error during authentication: {e}")
            return None
    
    def _build_url(self, endpoint):
        """
        Build a full URL for the given endpoint.
        
        Args:
            endpoint (str): The API endpoint
            
        Returns:
            str: The full URL
        """
        return urljoin(self.BASE_URL, endpoint)
    
    def _get_resource_or_link(self, url, params=None):
        """
        Get a resource or follow a link.
        
        Args:
            url (str): The URL to request
            params (dict): Query parameters
            
        Returns:
            tuple: (response data, is_link flag)
        """
        if not self.authenticated:
            self.login(self.username, self.encoded_password)
            return self._get_resource_or_link(url, params)
            
        try:
            response = self.session.get(url, params=params)
            
            # Handle authentication timeout
            if response.status_code == 401 and self.authenticated:
                self.authenticated = False
                return self._get_resource_or_link(url, params)
                
            # Handle rate limiting
            if response.status_code == 429:
                ratelimit_reset = response.headers.get('x-ratelimit-reset')
                if ratelimit_reset:
                    reset_datetime = datetime.fromtimestamp(int(ratelimit_reset))
                    delta = reset_datetime - datetime.now() + timedelta(milliseconds=500)
                    if not self.silent:
                        print(f"Rate limited, waiting {delta.total_seconds()} seconds")
                    if delta.total_seconds() > 0:
                        time.sleep(delta.total_seconds())
                    return self._get_resource_or_link(url, params)
            
            if response.status_code != 200:
                print(f"Request failed: {response.status_code} - {response.text}")
                return None, False
                
            data = response.json()
            if not isinstance(data, list) and 'link' in data:
                return data.get('link'), True
            else:
                return data, False
                
        except Exception as e:
            print(f"Error making request: {e}")
            return None, False
    
    def _make_request(self, endpoint, params=None):
        """
        Make a request to the iRacing API.
        
        Args:
            endpoint (str): The API endpoint to request
            params (dict, optional): Query parameters
            
        Returns:
            Any: The JSON response or None on failure
        """
        url = self._build_url(endpoint)
        
        resource, is_link = self._get_resource_or_link(url, params)
        
        if resource is None:
            return None
            
        if is_link:
            try:
                response = self.session.get(resource)
                
                if response.status_code == 401 and self.authenticated:
                    self.authenticated = False
                    self.login(self.username, self.encoded_password)
                    return self._make_request(endpoint, params)
                    
                if response.status_code == 429:
                    print("Rate limited, waiting")
                    ratelimit_reset = response.headers.get('x-ratelimit-reset')
                    if ratelimit_reset:
                        reset_datetime = datetime.fromtimestamp(int(ratelimit_reset))
                        delta = reset_datetime - datetime.now()
                        if delta.total_seconds() > 0:
                            time.sleep(delta.total_seconds())
                    return self._make_request(endpoint, params)
                    
                if response.status_code != 200:
                    print(f"Failed to follow link: {response.status_code} - {response.text}")
                    return None
                    
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    return response.json()
                else:
                    print(f"Unsupported content type: {content_type}")
                    return None
                    
            except Exception as e:
                print(f"Error following link: {e}")
                return None
        else:
            return resource
    
    def _get_chunks(self, chunks):
        """
        Get all data chunks when a response is split into multiple files.
        
        Args:
            chunks (dict): Chunk information from API response
            
        Returns:
            list: Aggregated data from all chunks
        """
        if not isinstance(chunks, dict):
            # If there are no chunks, return an empty list for compatibility
            return []
            
        base_url = chunks.get('base_download_url')
        urls = [base_url + x for x in chunks.get('chunk_file_names')]
        
        list_of_chunks = []
        for url in urls:
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    list_of_chunks.append(response.json())
                else:
                    print(f"Failed to get chunk: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error getting chunk: {e}")
                
        # Flatten the list of chunks
        output = [item for sublist in list_of_chunks for item in sublist]
        return output
    
    # Core API Methods
    
    def series(self):
        """
        Get all available series from iRacing.
        
        Returns:
            list: A list of series names.
        """
        # Check cache first
        if 'series' in self.cache:
            return self.cache['series']
        
        data = self._make_request('data/series/stats_series')
        if data:
            # Extract just the series names
            self.cache['series'] = [series['series_name'] for series in data]
            return self.cache['series']
        return []
    
    def result(self, subsession_id, include_licenses=False):
        """
        Get detailed results for a specific subsession.
        
        Args:
            subsession_id (int): The ID of the subsession.
            include_licenses (bool, optional): Whether to include license information.
            
        Returns:
            dict: The subsession results.
        """
        cache_key = f'result_{subsession_id}_{include_licenses}'
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        params = {
            'subsession_id': subsession_id,
            'include_licenses': include_licenses
        }
        
        result = self._make_request('data/results/get', params)
        if result:
            self.cache[cache_key] = result
            return result
        return None
    
    def result_lap_chart_data(self, subsession_id, simsession_number=0):
        """
        Get lap chart data for a specific subsession.
        
        Args:
            subsession_id (int): The ID of the subsession.
            simsession_number (int, optional): The simulation session number (0 for race).
            
        Returns:
            list: Lap data for all drivers in the session.
        """
        cache_key = f'lap_chart_{subsession_id}_{simsession_number}'
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        params = {
            'subsession_id': subsession_id,
            'simsession_number': simsession_number
        }
        
        data = self._make_request('data/results/lap_chart_data', params)
        if data and 'lap_data' in data:
            self.cache[cache_key] = data['lap_data']
            return data['lap_data']
        elif data and 'chunk_info' in data:
            # Handle chunked data
            lap_data = self._get_chunks(data['chunk_info'])
            self.cache[cache_key] = lap_data
            return lap_data
        return []
    
    def result_lap_data(self, subsession_id, simsession_number=0, cust_id=None, team_id=None):
        """
        Get lap data for a specific driver in a subsession.
        
        Args:
            subsession_id (int): The ID of the subsession.
            simsession_number (int): The simulation session number (0 for race).
            cust_id (int, optional): The customer ID. Required for single-driver events.
            team_id (int, optional): The team ID. Required for team events.
            
        Returns:
            list: Lap data for the specified driver/team.
        """
        if not cust_id and not team_id:
            raise ValueError("Please supply either a cust_id or a team_id")
            
        cache_key = f'lap_data_{subsession_id}_{simsession_number}_{cust_id}_{team_id}'
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        params = {
            'subsession_id': subsession_id,
            'simsession_number': simsession_number
        }
        if cust_id:
            params['cust_id'] = cust_id
        if team_id:
            params['team_id'] = team_id
            
        data = self._make_request('data/results/lap_data', params)
        
        if data and 'chunk_info' in data:
            lap_data = self._get_chunks(data['chunk_info'])
            self.cache[cache_key] = lap_data
            return lap_data
        return []
    
    def result_event_log(self, subsession_id, simsession_number=0):
        """
        Get the event log for a specific subsession.
        
        Args:
            subsession_id (int): The ID of the subsession.
            simsession_number (int): The simulation session number (0 for race).
            
        Returns:
            list: Event log data.
        """
        cache_key = f'event_log_{subsession_id}_{simsession_number}'
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        params = {
            'subsession_id': subsession_id,
            'simsession_number': simsession_number
        }
        
        data = self._make_request('data/results/event_log', params)
        
        if data and 'chunk_info' in data:
            event_log = self._get_chunks(data['chunk_info'])
            self.cache[cache_key] = event_log
            return event_log
        return []
    
    def stats_member_recent_races(self, cust_id=None):
        """
        Get recent races for a specific customer.
        
        Args:
            cust_id (int, optional): The customer ID. If not provided, returns data for the authenticated user.
            
        Returns:
            dict: Recent race data for the customer.
        """
        cache_key = f'recent_races_{cust_id}'
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        params = {}
        if cust_id:
            params['cust_id'] = cust_id
        
        data = self._make_request('data/stats/member_recent_races', params)
        if data:
            self.cache[cache_key] = data
            return data
        return {'races': []}
    
    def result_search_series(self, season_year=None, season_quarter=None, series_id=None, 
                             race_week_num=None, official_only=True, event_types=5,
                             start_range_begin=None, start_range_end=None,
                             finish_range_begin=None, finish_range_end=None,
                             cust_id=None, category_ids=None):
        """
        Search for race results by series and season.
        
        Args:
            season_year (int): The year of the season.
            season_quarter (int): The quarter of the season (1-4).
            series_id (int): The ID of the series.
            race_week_num (int): The week number in the season.
            official_only (bool): Whether to include only official races.
            event_types (int/list): The type(s) of events to include (5 for races).
            start_range_begin (str): ISO-8601 UTC time - Start time lower bound.
            start_range_end (str): ISO-8601 UTC time - Start time upper bound.
            finish_range_begin (str): ISO-8601 UTC time - Finish time lower bound.
            finish_range_end (str): ISO-8601 UTC time - Finish time upper bound.
            cust_id (int): Filter by customer ID.
            category_ids (list): Filter by category IDs.
            
        Returns:
            list: A list of race results matching the criteria.
        """
        if not ((season_year and season_quarter) or start_range_begin or finish_range_begin):
            raise ValueError("Please supply Season Year and Season Quarter or a date range")
            
        cache_key = f'races_{season_year}_{season_quarter}_{series_id}_{race_week_num}_{official_only}_{event_types}'
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        params = {}
        if season_year:
            params['season_year'] = season_year
        if season_quarter:
            params['season_quarter'] = season_quarter
        if series_id:
            params['series_id'] = series_id
        if race_week_num is not None:
            params['race_week_num'] = race_week_num
        if official_only is not None:
            params['official_only'] = official_only
        if event_types:
            params['event_types'] = event_types
        if start_range_begin:
            params['start_range_begin'] = start_range_begin
        if start_range_end:
            params['start_range_end'] = start_range_end
        if finish_range_begin:
            params['finish_range_begin'] = finish_range_begin
        if finish_range_end:
            params['finish_range_end'] = finish_range_end
        if cust_id:
            params['cust_id'] = cust_id
        if category_ids:
            params['category_ids'] = category_ids
        
        data = self._make_request('data/results/search_series', params)
        if data and 'data' in data and 'chunk_info' in data['data']:
            sessions = self._get_chunks(data['data']['chunk_info'])
            self.cache[cache_key] = sessions
            return sessions
        elif data and 'sessions' in data:
            self.cache[cache_key] = data['sessions']
            return data['sessions']
        return []
    
    # Additional methods from original client
    
    def get_cars(self):
        """
        Get information about all available cars.
        
        Returns:
            list: Car information.
        """
        return self._make_request('data/car/get')
    
    def get_tracks(self):
        """
        Get information about all available tracks.
        
        Returns:
            list: Track information.
        """
        return self._make_request('data/track/get')
    
    def get_carclasses(self):
        """
        Get information about car classes.
        
        Returns:
            list: Car class information.
        """
        return self._make_request('data/carclass/get')
    
    def constants_divisions(self):
        """
        Get information about iRacing divisions.
        
        Returns:
            list: Division information.
        """
        return self._make_request('data/constants/divisions')
    
    def member_profile(self, cust_id=None):
        """
        Get the member profile for a customer.
        
        Args:
            cust_id (int, optional): The customer ID. If not provided, returns data for the authenticated user.
            
        Returns:
            dict: Member profile data.
        """
        params = {}
        if cust_id:
            params['cust_id'] = cust_id
        return self._make_request('data/member/profile', params)
    
    def stats_member_career(self, cust_id=None):
        """
        Get the career statistics for a member.
        
        Args:
            cust_id (int, optional): The customer ID. If not provided, returns data for the authenticated user.
            
        Returns:
            dict: Career statistics.
        """
        params = {}
        if cust_id:
            params['cust_id'] = cust_id
        return self._make_request('data/stats/member_career', params)
    
    def series_seasons(self, include_series=False):
        """
        Get information about all series seasons.
        
        Args:
            include_series (bool): Whether to include series information.
            
        Returns:
            list: Series season information.
        """
        params = {'include_series': include_series}
        return self._make_request('data/series/seasons', params)
    
    def get_series_assets(self):
        """
        Get assets for all series.
        
        Returns:
            dict: Series assets.
        """
        return self._make_request('data/series/assets')
    
    def result_season_results(self, season_id, event_type=None, race_week_num=None):
        """
        Get results for a specific season.
        
        Args:
            season_id (int): The season ID.
            event_type (int, optional): The event type (2=practice, 3=qualify, 4=time trial, 5=race).
            race_week_num (int, optional): The race week number.
            
        Returns:
            dict: Season results.
        """
        params = {'season_id': season_id}
        if event_type:
            params['event_type'] = event_type
        if race_week_num is not None:
            params['race_week_num'] = race_week_num
        return self._make_request('data/results/season_results', params)
    
    def lookup_licenses(self):
        """
        Get information about iRacing licenses.
        
        Returns:
            list: License information.
        """
        return self._make_request('data/lookup/licenses')