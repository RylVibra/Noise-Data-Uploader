from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import requests
import logging
import ftplib
import json
import toml
import time
import sys
import io


#### Logging ####
logger_name = "sigicom_noise_uploader.log"
logger= logging.getLogger(logger_name)
logger.setLevel(logging.DEBUG)
# Create a formatter and set it for RotatingFileHandler
handler = RotatingFileHandler(logger_name, 
                              maxBytes=1_000_000, 
                              backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
#### /Logging ####
    

#### Config ####
# def load_config(path='config.toml')
try:
    config = toml.load("asdf.toml")
    FTP_HOST = config['host']['ftp_url']
    username = config['host']['username']

    api_endpoint = config['api_endpoint']
    sigicom_api_url = api_endpoint['url']
    user_id = api_endpoint['user_id']
    user_token = api_endpoint['user_token']
    device_id = api_endpoint['device_id'] # TODO: Deprecate it and pull from txt file later
    
    header = {"accept":"application/json"}
except (TypeError, FileNotFoundError, toml.TomlDecodeError) as e:
    logger.error(e)
    sys.exit(1)
#### /Config ####


def call_data_from_sigicom(data_url:str):
    """Get data from sigicom instrument"""
    request_url = sigicom_api_url + data_url
    logger.info(f"Requesting data from url: {request_url}")
    return requests.get(
        url=request_url,
        headers=header,
        auth=("user", f"{user_id}:{user_token}"),
        )

def set_data_search(date_start:datetime, date_end:datetime, device_id):
    """Get data url for device"""
    pattern = "%Y-%m-%d %H:%M"
    search_url = sigicom_api_url + f"/api/v1/sensor/{device_id}/search"
    logger.debug(f"Requesting search url: {search_url}")
    payload = {"datetime_from": date_start.strftime(pattern),
               "datetime_to":date_end.strftime(pattern),
               "data_types": {
                   "transient": False,
                   "interval": True},
                "aggregator": 1,
                "timezone": "America/New_York"}
    logger.debug(payload)
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
    # start_date = datetime(2025,6,11)
    # now = datetime.now()
    # while start_date < now:
    #     end_date = start_date + timedelta(days=5)
    end_date = datetime.now().replace(second=0,microsecond=0)
    start_date = end_date - timedelta(hours=2)
    response = set_data_search(start_date, end_date, device_id)
    # Get data url out of search response and call it.
    search_data = json.loads(response.content.decode("utf-8"))
    response = call_data_from_sigicom(search_data["data_url"])
    # Decode binary to string and load JSON
    if response.content:
        data = json.loads(response.content.decode("utf-8"))
        with open("output.json", 'w') as file:
            json.dump(data, file, indent=4)
        # Create a data list to hold all the row values
        # Dynamic headers don't work with FTP endpoint.
        final_list = ["datetime,LAS,L90,L50,L10,LAeq"]
        if len(data['intervals'])>2:
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
            logger.info(f"{result}Finished")
            # time.sleep(10)

    
    
if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        # Optional: log the error
        logger.error(e)
        sys.exit(1)