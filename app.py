import requests
import logging
import ftplib
import json
import toml

config = toml.load("config.toml")
api_endpoint = config['api_endpoint']

FTP_HOST = config['host']['ftp_url']

sigicom_api_url = api_endpoint['url']
user_id = api_endpoint['user_id']
user_token = api_endpoint['user_token']
device_id = api_endpoint['device_id']
data_id = api_endpoint['data_id']



header = {"accept":"application/json"}

def call_data_from_sigicom():
    """Get data from sigicom instrument"""
    search_url = sigicom_api_url + f"/{device_id}/search/{data_id}/data"
    # search_url = sigicom_api_url
    print(search_url)
    
    # payload = {"datetime_from": "2025-06-03"}
    return requests.get(
        url=search_url, 
        headers=header,
        auth=("user", f"{user_id}:{user_token}"),
        # json=payload,
        )


def connect_ftp(username)->ftplib.FTP:
    """Connect to FTP"""
    logging.info(f"Connecting to {FTP_HOST} with {username}")
    ftp = ftplib.FTP(host=FTP_HOST, user=username, timeout=10)
    return ftp


def upload_file(ftp: ftplib.FTP, file_name: str, json_data)->bool:
    """Function to upload file"""
    result = ftp.storbinary(f'STOR {file_name}', json_data)
    print(result)
    return result[:3]=='226'


def main():
    response = call_data_from_sigicom()
    print(response.headers)
    print(response.content)
    
    # Decode binary to string and load JSON
    data = json.loads(response.content.decode("utf-8"))

    # Save to a JSON file
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    main()