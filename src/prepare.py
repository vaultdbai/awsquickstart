import os

# This file is used to install all required extensions for vaultdb
if __name__ == '__main__':
    import duckdb
    connection = duckdb.connect()
    connection.execute("INSTALL parquet")
    connection.execute("LOAD parquet")
    connection.execute("INSTALL httpfs")
    connection.execute("LOAD httpfs")
