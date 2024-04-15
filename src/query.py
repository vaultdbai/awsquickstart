# Imports
import os
import logging
import json
import glob
from json import JSONEncoder
import boto3
import duckdb

# Set up the logger
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # Very verbose

application_name = os.environ['application_name'] if "application_name" in os.environ else ""
commitlog_directory = os.environ['commitlog_directory'] if "commitlog_directory" in os.environ else "/tmp"
public_bucket = os.environ['public_bucket'] if "public_bucket" in os.environ else None
data_store = os.environ['data_store'] if "data_store" in os.environ else None

def get_keys():
    from datetime import datetime
    cachepath = f"{commitlog_directory}/jwks{datetime.today().strftime('%Y-%m-%d')}.json"
    if os.path.isfile(cachepath):
        with open(cachepath) as f:
            data = json.load(f)
        local_keys = data['keys']
        logger.debug(f"keys: {local_keys}")
        return local_keys
    else:
        jwks = glob.glob(f"{commitlog_directory}/jwks*.json")
        for jwk in jwks:
            os.remove(jwk)
    
    s3 = boto3.resource('s3')
    obj = s3.meta.client.get_object(Bucket=data_store, Key="jwks.json")
    local_keys = json.loads(obj['Body'].read())
    with open(cachepath, 'w') as f:
        json.dump(local_keys, f)
    logger.debug(f"keys: {local_keys}")
    return local_keys['keys']

keys = get_keys() # Download Public Keys for token verification ahead as we need them for security

def lambda_handler(event, context):
    token = event['token']
    connection = None
    try:
        user_pool_client_id = os.environ['user_pool_client_id'] if "user_pool_client_id" in os.environ else None
        verified_claims = verify_token(token, user_pool_client_id)
        preferred_role = str(verified_claims['cognito:preferred_role']).split(':role/')[-1]        
        logger.debug(f'preferred_role: {preferred_role}')
        if application_name and preferred_role.startswith(application_name):
            preferred_role = preferred_role[len(application_name)+1:]
        if preferred_role.endswith('-AdminRole'):
            preferred_role = preferred_role[:-10]
        logger.debug(f'role: {preferred_role}')
        
        if 'RequestType' in event and event['RequestType'] == 'fetch-catalogues':
            if not os.path.isfile(f"{commitlog_directory}/{application_name}.db"):
                connection = create_sample_database(application_name) # Create Default Database for sample
            catalogues = glob.glob(f"{commitlog_directory}/*.db")
            return {"result":"Success", "data":catalogues}
    
        repo = event['database']
        catalog = event['catalog']
        logger.debug(f'catalog: {catalog}')
        payload = event['payload']
        logger.debug(f'repo: {repo}')
        logger.debug(f'payload: {payload}')

        test_db_path = f"{commitlog_directory}/{catalog}.db"
        if os.path.isfile(test_db_path):
            connection = duckdb.connect(f"{commitlog_directory}/{catalog}.db", True, preferred_role)
            if payload.strip():
                connection.execute(f"PRAGMA enable_data_inheritance;")
                df = connection.execute(payload).fetchdf()
                if "create" in payload.lower() or "alter" in payload.lower():
                    s3 = boto3.resource("s3")
                    s3.meta.client.upload_file(Filename=f"{commitlog_directory}/{catalog}.db", Bucket=public_bucket, Key=f"catalogs/{catalog}.db")
                return {"result":"Success", "data":df.to_json(orient="index")}
            
            return {"result":"Success", "data":{"result":"empty payload. please check your query."}}
        
        elif 'RequestType' in event and event['RequestType'] == 'create-catalog':
            connection = create_sample_database(catalog)
            return {"result":"Success", "data":catalog}
        
        return {"result":"Error", "message":f"Catalog {catalog} does not exist."}
                    
    except Exception as ex:
        logger.error(ex)
        return {"result":"Error", "message":str(ex)}
    finally:
        if connection:
            connection.close()


def create_sample_database(catalog_name):
    test_db_path = f"{commitlog_directory}/{catalog_name}.db"
    if os.path.isfile(test_db_path):
        return
    connection = duckdb.connect(test_db_path, False, "vaultdb")
    
    connection.execute(f"CREATE CONFIG remote AS 's3://{data_store}/merged_data';")
    connection.execute(f"CREATE CONFIG remote_merge_path AS 's3://{public_bucket}';")

    connection.execute(f"CREATE CONFIG application_name AS '{application_name}';")
    user_pool_client_id = os.environ['user_pool_client_id'] if "user_pool_client_id" in os.environ else None
    user_pool_id = os.environ['user_pool_id'] if "user_pool_id" in os.environ else None
    identity_pool_id = os.environ['identity_pool_id'] if "identity_pool_id" in os.environ else None
    connection.execute(f"CREATE CONFIG user_pool_id AS '{user_pool_id}';")
    connection.execute(f"CREATE CONFIG user_pool_client_id AS '{user_pool_client_id}';")
    connection.execute(f"CREATE CONFIG identity_pool_id AS '{identity_pool_id}';")

    connection.execute('BEGIN TRANSACTION;')
    if catalog_name==application_name:
        connection.execute('CREATE TABLE tbl_ProductSales (ColID int, Product_Category  varchar(64), Product_Name  varchar(64), TotalSales int)')
        connection.execute('CREATE TABLE another_T (col1 INT, col2 INT, col3 INT, col4 INT, col5 INT, col6 INT, col7 INT, col8 INT)')
        connection.execute("INSERT INTO tbl_ProductSales VALUES (1,'Game','Mobo Game',200),(2,'Game','PKO Game',400),(3,'Fashion','Shirt',500),(4,'Fashion','Shorts',100);")
        connection.execute("INSERT INTO another_T VALUES (1,2,3,4,5,6,7,8), (11,22,33,44,55,66,77,88), (111,222,333,444,555,666,777,888), (1111,2222,3333,4444,5555,6666,7777,8888)")
    else:
        connection.execute('CREATE TABLE demo (col1 INT, col2 INT, col3 INT, col4 INT, col5 INT, col6 INT, col7 INT, col8 INT)')
        connection.execute("INSERT INTO demo VALUES (1,2,3,4,5,6,7,8), (11,22,33,44,55,66,77,88), (111,222,333,444,555,666,777,888), (1111,2222,3333,4444,5555,6666,7777,8888)")
        
    connection.execute('COMMIT;')    
    connection.close()
    
    connection = duckdb.connect(test_db_path, False, "vaultdb")
    configs = connection.execute("select config_name, config_value from vaultdb_configs").fetchall()
    if not configs:
        raise Exception("Config Data Not found in Database")

    connection.execute(f"MERGE DATABASE {catalog_name};")    
    s3 = boto3.resource("s3")
    s3.meta.client.upload_file(Filename=f"{commitlog_directory}/{catalog_name}.db", Bucket=public_bucket, Key=f"catalogs/{catalog_name}.db")
    return connection

def verify_token(token, user_pool_client_id):
    import time
    from jose import jwk, jwt
    from jose.utils import base64url_decode
    # get the kid from the headers prior to verification
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    # search for the kid in the downloaded public keys
    key_index = -1
    valid_keys = keys or get_keys()
    for i in range(len(valid_keys)):
        if kid == valid_keys[i]["kid"]:
            key_index = i
            break
    if key_index == -1:
        raise Exception('Public key not found in jwks.json')
    # construct the public key
    public_key = jwk.construct(keys[key_index])
    # get the last two sections of the token,
    # message and signature (encoded in base64)
    message, encoded_signature = str(token).rsplit('.', 1)
    # decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        raise Exception('Signature verification failed')
    logger.debug('Signature successfully verified')
    # since we passed the verification, we can now safely
    # use the unverified claims
    claims = jwt.get_unverified_claims(token)
    # additionally we can verify the token expiration
    if time.time() > claims['exp']:
        raise Exception('Token is expired')
    # and the Audience  (use claims['client_id'] if verifying an access token)
    if claims['aud'] != user_pool_client_id:
        raise Exception('Token was not issued for this audience')
    # now we can use the claims
    logger.debug(claims)
    return claims

# the following is useful to make this script executable in both
# AWS Lambda and any other local environments
if __name__ == '__main__':
    # for testing locally you can enter the JWT ID Token here
    event = {}
    event['token'] = ''
    event['RequestType'] = 'fetch-catalogues'
    event['database'] = "dev"
    event['catalog'] = "dev"
    event['payload'] = "SELECT * FROM another_T"
    #event['payload'] = "SELECT * FROM vaultdb_configs()"
    #event['payload'] = "SELECT * FROM 's3://dev-data-440955376164/jwks.json'"    
    context = {'identity': {'cognito_identity_id':'', 'cognito_identity_pool_id':''}}
    result = lambda_handler(event, context)
    print(result)
