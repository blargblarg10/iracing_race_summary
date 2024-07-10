import os
from os import path as p 
import dropbox
from datetime import datetime
import configparser
import requests

# Read configuration
CFG_FILE = p.join(p.dirname(p.abspath(__file__)), "dropbox.cfg")

config = configparser.ConfigParser()
config.read(CFG_FILE)

# Dropbox access token from config file
ACCESS_TOKEN = config['Dropbox']['ACCESS_TOKEN']
FOLDER_PATH = config['Dropbox']['TELEMETRY_DIR']

def get_most_recent_file(folder_path):
    files = os.listdir(folder_path)
    paths = [p.join(folder_path, basename) for basename in files if p.splitext(basename)[1] == ".ibt"]
    return max(paths, key=p.getctime)

def format_filename(filename):
    # Replace spaces with underscores and convert to lowercase
    return filename.replace(' ', '_').lower()

def upload_to_dropbox(file_path):
    dbx = dropbox.Dropbox(ACCESS_TOKEN)
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
    most_recent_file = get_most_recent_file(FOLDER_PATH)
    dropbox_link = upload_to_dropbox(most_recent_file)
    print(f"Dropbox link for the most recent file: {dropbox_link}")
    print(f"Tinyurl link for the most recent file: {tinyurl(dropbox_link)}")

if __name__ == "__main__":
    main()