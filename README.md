# Demo vaultDB AI Modeling platform

This repository contains the demo code to install vaultDB AI and Data platform.

## Setup Environment

A) Create User with Cloud Formation Policy
    1) Create cloud formation User

    awsv2 iam create-user --user-name cloudformation-user
    awsv2 iam create-access-key --user-name cloudformation-user

    2) Attach Policy to User
    awsv2 iam put-user-policy --user-name cloudformation-user --policy-name cloudformation-user-policy --policy-document file://./cloudformation-user-policy.json

    3) Create Profile for use
    
    awsv2 configure --profile cloudformation-user

    Append --profile cloudformation-user to any AWS CLI command to run the command as this user

B) Create Service Role

    1) Create Cloud Formation Service Role

    awsv2 cloudformation create-stack --stack-name vaultdb --template-body file://service-role.yaml --capabilities CAPABILITY_NAMED_IAM
    
## License

All Images and Text copyright VaultDB.ai LLC
