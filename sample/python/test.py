import duckdb

print(duckdb.__file__)
connection = duckdb.connect(f"/efs/dev.db", True, "vaultdb")
print(connection.execute('SELECT * FROM vaultdb_configs()').fetchdf())
#print(connection.execute('select * from another_T').fetchdf())
connection.execute(f"PRAGMA enable_data_inheritance;")
print(connection.execute('select * from another_T').fetchdf())

#connection = duckdb.connect(f"build/test.db", False, "vaultdb") #, config={'extension_directory':"/workspace/build/debug/extension", 'allow_unsigned_extensions' : 'true', 'autoinstall_known_extensions' : 'true', 'autoload_known_extensions' : 'true'})
#connection.execute("LOAD parquet")
#connection.execute("LOAD httpfs")
#print(connection.execute("SELECT * FROM 'https://raw.githubusercontent.com/duckdb/duckdb-web/main/data/weather.csv'").fetchdf())

connection.execute(f"CREATE CONFIG remote AS 's3://dev-data-440955376164/dev';")
connection.execute(f"CREATE CONFIG remote_merge_path AS 's3://dev-public-storage-440955376164/dev';")

#print(connection.execute("select current_setting('remote'), current_setting('remote_merge_path')").fetchdf())

connection.execute('BEGIN TRANSACTION;')
print(connection.execute('CREATE TABLE tbl_ProductSales (ColID int, Product_Category  varchar(64), Product_Name  varchar(64), TotalSales int)').fetchdf())
print(connection.execute('CREATE TABLE another_T (col1 INT, col2 INT, col3 INT, col4 INT, col5 INT, col6 INT, col7 INT, col8 INT)').fetchdf())
print(connection.execute("INSERT INTO tbl_ProductSales VALUES (1,'Game','Mobo Game',200),(2,'Game','PKO Game',400),(3,'Fashion','Shirt',500),(4,'Fashion','Shorts',100);").fetchdf())
print(connection.execute("INSERT INTO another_T VALUES (1,2,3,4,5,6,7,8), (11,22,33,44,55,66,77,88), (111,222,333,444,555,666,777,888), (1111,2222,3333,4444,5555,6666,7777,8888)").fetchdf())
connection.execute('COMMIT;')

#print(connection.execute('select t.table_name, c.column_name from information_schema.tables t, information_schema.columns c where t.table_name=c.table_name').fetchdf())
#print(connection.execute('select * from another_T').fetchdf())
#connection.execute(f"PRAGMA enable_data_inheritance;")
#print(connection.execute('select * from another_T').fetchdf())
#print(connection.execute('select * from duckdb_settings()').fetchdf())

#print(connection.execute("SELECT * FROM 'https://raw.githubusercontent.com/duckdb/duckdb-web/main/data/weather.csv'").fetchdf())


#print(connection.execute("SELECT * FROM read_parquet('s3://dev-data-440955376164/data.parquet');").fetchdf())

#print(connection.execute('PUSH DATABASE dev;').fetchdf())

#print(connection.execute('MERGE DATABASE dev;').fetchdf())
