from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import requests
import logging
import ftplib
import json
import toml
import io

#### Config ####
config = toml.load("config.toml")
api_endpoint = config['api_endpoint']

FTP_HOST = config['host']['ftp_url']
username = config['host']['username']

sigicom_api_url = api_endpoint['url']
user_id = api_endpoint['user_id']
user_token = api_endpoint['user_token']
device_id = api_endpoint['device_id'] # Depracted and pull from txt file later

header = {"accept":"application/json"}
#### /Config ####


#### Logging ####
logger_name = "sigicom_noise_uploader"
logger= logging.getLogger(logger_name)
logger.setLevel(logging.INFO)
# Create a formatter and set it for RotatingFileHandler
handler = RotatingFileHandler(logger_name, 
                              maxBytes=1_000_000, 
                              backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
#### /Logging ####


def call_data_from_sigicom(data_url:str):
    """Get data from sigicom instrument"""
    request_url = sigicom_api_url + data_url
    logger.info(f"Requesting data from url: {request_url}")
    return requests.get(
        url=request_url,
        headers=header,
        auth=("user", f"{user_id}:{user_token}"),
        )

def set_data_search(date:str, device_id):
    """Get data url for device"""
    search_url = sigicom_api_url + f"/api/v1/sensor/{device_id}/search"
    logger.debug(f"Requesting search url: {search_url}")
    payload = {"datetime_from": date,
               "data_types": {
                   "transient": False,
                   "interval": True},
                "aggregator": 1,
                "timezone": "America/New_York"}
    return requests.post(
        url=search_url, 
        headers=header,
        auth=("user", f"{user_id}:{user_token}"),
        json=payload,
        )


def connect_ftp(username)->ftplib.FTP:
    """Connect to FTP"""
    logger.info(f"Connecting to {FTP_HOST} with {username}")
    ftp = ftplib.FTP(host=FTP_HOST, user=username, timeout=10)
    return ftp


def upload_file(ftp: ftplib.FTP, file_name: str, data:io.BytesIO)->bool:
    """Function to upload file"""
    result = ftp.storbinary(cmd=f'STOR {file_name}', fp=data)
    logger.info(result)
    return result[:3]=='226'


def main():
    time_offset = datetime.now() - timedelta(hours=2)
    time_offset = time_offset.strftime("%Y-%m-%d %H:%M")
    response = set_data_search(time_offset, device_id)
    # Get data url out of search response and call it.
    search_data = json.loads(response.content.decode("utf-8"))
    response = call_data_from_sigicom(search_data["data_url"])

    # Decode binary to string and load JSON
    data = json.loads(response.content.decode("utf-8"))

    # # Save to a JSON file
    # with open("output.json", "w", encoding="utf-8") as f:
    #     json.dump(data['intervals'], f, indent=4)
    
    # Create a data list to hold all the row values
    # Dynamic headers don't work with FTP endpoint.
    final_list = ["datetime,LAS,L90,L50,L10,LAeq"]
    for item in data['intervals']:
        data_list = []
        data_list.append(item['datetime'])
        data_point = item[f'{device_id}']['intervals'] # will be list of dict
        for value in data_point:
            if 'max' in value.keys():
                num_val = value['max']
            else:
                num_val = value['value']
            data_list.append(str(round(num_val,3)))
        joined_data = ','.join(data_list)
        final_list.append(joined_data)
    csv_string = '\n'.join(final_list)

    # Convert the CSV string to bytes
    csv_bytes = csv_string.encode('utf-8')
    logger.debug(csv_string)
    filename = f"device_data.csv"
    conn = connect_ftp(username=username)
    result = upload_file(conn, filename, io.BytesIO(csv_bytes))
    logger.info(result, "Finished")


if __name__ == "__main__":
    main()