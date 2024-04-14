import requests
import duckdb

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
    downloaded_filename = download_file(url, "/tmp/dev.db")
    
    connection = duckdb.login.cognito("vaultdb","test123", "/tmp/dev.db")
    
    df = connection.execute("SELECT * FROM vaultdb_configs()").fetchdf()
    print(df.head())
    
