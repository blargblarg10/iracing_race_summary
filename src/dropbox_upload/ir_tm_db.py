import os
from os import path as p 
import dropbox
from datetime import datetime
import configparser
import requests

# Read configuration
CFG_FILE = p.join(p.dirname(p.abspath(__file__)), "dropbox.cfg")

# Check if config file exists, if not create a template
if not p.exists(CFG_FILE):
    print(f"Configuration file {CFG_FILE} not found, creating a template...")
    config = configparser.ConfigParser()
    config['Dropbox'] = {
        'ACCESS_TOKEN': 'YOUR_DROPBOX_ACCESS_TOKEN_HERE',
        'TELEMETRY_DIR': 'PATH_TO_TELEMETRY_DIRECTORY'
    }
    
    with open(CFG_FILE, 'w') as configfile:
        config.write(configfile)
    
    print(f"Please edit {CFG_FILE} and add your Dropbox access token and telemetry directory path.")
    exit(1)

# Load configuration
config = configparser.ConfigParser()
config.read(CFG_FILE)

# Dropbox access token from config file
ACCESS_TOKEN = config['Dropbox']['ACCESS_TOKEN']
FOLDER_PATH = config['Dropbox']['TELEMETRY_DIR']

def get_most_recent_file(folder_path):
    """Find the most recent .ibt file in the specified folder."""
    if not p.exists(folder_path):
        raise FileNotFoundError(f"Telemetry directory not found: {folder_path}")
    
    files = os.listdir(folder_path)
    ibt_files = [p.join(folder_path, basename) for basename in files if p.splitext(basename)[1].lower() == ".ibt"]
    
    if not ibt_files:
        raise FileNotFoundError(f"No .ibt files found in {folder_path}")
    
    return max(ibt_files, key=p.getctime)

def format_filename(filename):
    """Format the filename for Dropbox: replace spaces with underscores and convert to lowercase."""
    base_name = p.basename(filename)
    formatted = base_name.replace(' ', '_').lower()
    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = p.splitext(formatted)
    return f"{name}_{timestamp}{ext}"

def upload_to_dropbox(file_path):
    """Upload a file to Dropbox and return a shared link."""
    try:
        dbx = dropbox.Dropbox(ACCESS_TOKEN)
        
        # Test the connection
        dbx.users_get_current_account()
        print("Connected to Dropbox successfully")
        
        with open(file_path, 'rb') as file:
            original_file_name = p.basename(file_path)
            formatted_file_name = format_filename(original_file_name)
            dropbox_path = f'/{formatted_file_name}'
            
            # Upload file
            print(f"Uploading {original_file_name} to Dropbox as {formatted_file_name}...")
            dbx.files_upload(file.read(), dropbox_path)
            
            # Create a shared link
            shared_link = dbx.sharing_create_shared_link(dropbox_path)
            print("Upload successful!")
            return shared_link.url
            
    except dropbox.exceptions.AuthError:
        print("ERROR: Invalid Dropbox access token")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def tinyurl(url):
    """Create a shortened URL using TinyURL service."""
    TINY_URL = 'http://tinyurl.com/api-create.php?url='
    try:
        response = requests.get(TINY_URL + url)
        response.raise_for_status()  # Raise an exception if request failed
        short_url = response.text
        return short_url
    except Exception as e:
        print(f"Error creating TinyURL: {e}")
        return url  # Return original URL if shortening fails

def main():
    try:
        print(f"Looking for the most recent .ibt file in {FOLDER_PATH}...")
        most_recent_file = get_most_recent_file(FOLDER_PATH)
        print(f"Found file: {p.basename(most_recent_file)}")
        
        dropbox_link = upload_to_dropbox(most_recent_file)
        
        if dropbox_link:
            print(f"Dropbox link: {dropbox_link}")
            
            tiny_url = tinyurl(dropbox_link)
            print(f"TinyURL link: {tiny_url}")
            
            # Return the TinyURL for easy copying
            return tiny_url
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    main()