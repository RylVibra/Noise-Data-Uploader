import requests
import logging
import ftplib
import json
import toml

config = toml.load("config.toml")
FTP_HOST = config['host']['ftp_url']


def call_data_from_sigicom():
    """Get data from sigicom instrument"""
    requests.get()



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


