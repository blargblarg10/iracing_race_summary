import os
from os import path as p 
import dropbox
from datetime import datetime
import configparser
import requests
from requests.auth import HTTPBasicAuth 

# Read configuration
CFG_FILE = p.join(p.dirname(p.abspath(__file__)), "dropbox.cfg")

config = configparser.ConfigParser()
config.read(CFG_FILE)

# Dropbox app key, secret, and authorization code from config file
APP_KEY = config['Dropbox']['APP_KEY']
APP_SECRET = config['Dropbox']['APP_SECRET']
REFRESH_TOKEN = config['Dropbox']['REFRESH_TOKEN']
FOLDER_PATH = config['Dropbox']['TELEMETRY_DIR']

def get_new_access_token():
    try:
        response = requests.post('https://api.dropboxapi.com/oauth2/token',
                                 data={
                                     'refresh_token': REFRESH_TOKEN,
                                     'grant_type': 'refresh_token',
                                     'client_id': APP_KEY,
                                     'client_secret': APP_SECRET
                                 })
        response.raise_for_status()
        print("-- Got Access to Drop Box --")
        return response.json()['access_token']
    except Exception as e:
        print(f"Error refreshing access token: {e}")
        return None

def get_most_recent_file(folder_path):
    files = os.listdir(folder_path)
    paths = [p.join(folder_path, basename) for basename in files if p.splitext(basename)[1] == ".ibt"]
    return max(paths, key=p.getctime)

def format_filename(filename):
    return filename.replace(' ', '_').lower()

def upload_to_dropbox(file_path, access_token):
    dbx = dropbox.Dropbox(access_token)
    with open(file_path, 'rb') as file:
        original_file_name = os.path.basename(file_path)
        formatted_file_name = format_filename(original_file_name)
        dropbox_path = f'/{formatted_file_name}'
        dbx.files_upload(file.read(), dropbox_path)
    
    shared_link = dbx.sharing_create_shared_link(dropbox_path)
    return shared_link.url

def tinyurl(url):
    TINY_URL = 'http://tinyurl.com/api-create.php?url='
    response = requests.get(TINY_URL+url)
    short_url = response.text
    return short_url

def main():
    access_token = get_new_access_token()
    print("-- Got Access to Drop Box --")
    if not access_token:
        print("Failed to obtain access token.")
        return

    most_recent_file = get_most_recent_file(FOLDER_PATH)
    dropbox_link = upload_to_dropbox(most_recent_file, access_token)
    print(f"Dropbox link for the most recent file: {dropbox_link}")
    print(f"Tinyurl link for the most recent file: {tinyurl(dropbox_link)}")

if __name__ == "__main__":
    main()