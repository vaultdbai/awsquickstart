import requests
import duckdb
import os

def download_file(url, filename=None):
  """Downloads a file from a URL and saves it locally.

  Args:
    url: The URL of the file to download.
    filename: The filename to save the downloaded file as. If not specified,
      the filename will be extracted from the URL.
  """
  response = requests.get(url, stream=True)
  response.raise_for_status()
  
  if filename is None:
    filename = url.split("/")[-1]

  if os.path.isfile(filename):
    os.remove(filename)  

  if os.path.isfile(filename+".wal"):
    os.remove(filename+".wal")  

  with open(filename, "wb") as f:
    for chunk in response.iter_content(1024):
      if chunk:  # filter out keep-alive new chunks
        f.write(chunk)

  return filename

# Set up the logger
import logging

logger = logging.getLogger()

if __name__ == "__main__":    
    logger.setLevel(logging.DEBUG)  # Very verbose
    url = "http://dev-public-storage-440955376164.s3-website.us-east-2.amazonaws.com/catalogs/dev.db"
    downloaded_filename = download_file(url)
    
    connection = duckdb.login.cognito("vaultdb","test123", downloaded_filename or "dev.db")
    
    #print(connection.execute("SELECT * FROM another_T").fetchdf())
    #connection.execute(f"PRAGMA enable_data_inheritance;")
    #print(connection.execute("SELECT * FROM another_T").fetchdf())

    #connection.execute('BEGIN TRANSACTION;')
    #connection.execute('CREATE TABLE demo (col1 INT, col2 INT, col3 INT, col4 INT, col5 INT, col6 INT, col7 INT, col8 INT)')
    #connection.execute("INSERT INTO demo VALUES (1,2,3,4,5,6,7,8), (11,22,33,44,55,66,77,88), (111,222,333,444,555,666,777,888), (1111,2222,3333,4444,5555,6666,7777,8888)")
    print(connection.execute('PUSH DATABASE dev;').fetchdf())
    #print(connection.execute('MERGE DATABASE dev;').fetchdf())
    
