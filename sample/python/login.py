import boto3
import duckdb

# Set up the logger
import logging

logger = logging.getLogger()


def cognito(path, username, password, **userpoolargs):
    connection = duckdb.connect(path, False)
    if userpoolargs:
        USER_POOL_ID = userpoolargs["USER_POOL_ID"]
        USER_POOL_APP_CLIENT_ID = userpoolargs["USER_POOL_APP_CLIENT_ID"]
        USER_IDENTITY_POOL_ID = userpoolargs["USER_IDENTITY_POOL_ID"]
        USER_BUCKET = userpoolargs["USER_BUCKET"]
        CATALOG = userpoolargs["CATALOG"] if "CATALOG" in userpoolargs else path
        connection.execute(
            f"CREATE CONFIG remote_merge_path AS 's3://{USER_BUCKET}/{CATALOG}';"
        )
        connection.execute(f"CREATE CONFIG user_pool_id AS '{USER_POOL_ID}';")
        connection.execute(
            f"CREATE CONFIG user_pool_client_id AS '{USER_POOL_APP_CLIENT_ID}';"
        )
        connection.execute(
            f"CREATE CONFIG identity_pool_id AS '{USER_IDENTITY_POOL_ID}';"
        )

    configs = connection.execute(
        "select config_name, config_value from vaultdb_configs"
    ).fetchall()
    if not configs:
        raise Exception("Config Data Not found in Database")

    configs = dict(configs)
    user_pool_client_id = configs["user_pool_client_id"]
    user_pool_id = configs["user_pool_id"]
    identity_pool_id = configs["identity_pool_id"]
    region = identity_pool_id.split(":")[0]

    client = boto3.client("cognito-idp", region_name=region)
    # Initiating the Authentication,
    response = client.initiate_auth(
        ClientId=user_pool_client_id,
        AuthFlow="USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )

    # From the JSON response you are accessing the AccessToken
    logger.debug(response)
    # Getting the user details.
    # access_token = response["AuthenticationResult"]["AccessToken"]
    id_token = response["AuthenticationResult"]["IdToken"]

    identity = boto3.client("cognito-identity", region_name=region)
    response = identity.get_id(
        IdentityPoolId=identity_pool_id,
        Logins={f"cognito-idp.{region}.amazonaws.com/{user_pool_id}": id_token},
    )
    logger.debug(response)
    identityId = response["IdentityId"]

    response = identity.get_credentials_for_identity(
        IdentityId=identityId,
        Logins={f"cognito-idp.{region}.amazonaws.com/{user_pool_id}": id_token},
    )

    logger.debug(response)
    aws_cred = response["Credentials"]
    connection.execute(
        f"CREATE OR REPLACE SECRET {username} (TYPE S3, KEY_ID '{aws_cred['AccessKeyId']}', SECRET '{aws_cred['SecretKey']}')"
    )
    # duckdb_secrets = connection.execute("select * from duckdb_secrets();").fetch_df()
    # print(df.head(5))
    return connection


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)  # Very verbose
    connection = cognito (
        "memory",
        "vaultdb",
        "test123",
        USER_POOL_ID="us-east-2_XpU8yRtug",
        USER_POOL_APP_CLIENT_ID="3m036a7r9ic9bv3oq9scgtp04m",
        USER_IDENTITY_POOL_ID="us-east-2:333c9686-af9c-40e7-af91-fc4a47d8b44b",
        USER_BUCKET="dev-public-storage-440955376164",
        CATALOG="memory",
    )
