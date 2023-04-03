# vaultDB AI Modeling platform

This repository contains the demo code to install vaultDB AI and Data platform.

## Setup Environment

### Create Service Role

#### Create Cloud Formation Service Role

    awsv2 cloudformation create-stack --stack-name vaultdb-service-role --template-body file://service-role.yaml --capabilities CAPABILITY_NAMED_IAM

##### Update Service Role

    awsv2 cloudformation update-stack --stack-name vaultdb-service-role --template-body file://service-role.yaml --capabilities CAPABILITY_NAMED_IAM
    
### Deploy 

#### Deploy VaultDB

    awsv2 cloudformation create-stack --stack-name [APPLICATIONNAME] --role-arn [ROLE-ARN-FROM-STEP-ABOVE] --template-url file://vaultdb.yaml --parameters AdminEmail=[ADMIN-EMAIL-ADDRESS],ExistingVpcID=[VPC-ID-IF-YOU-HAVE-ONE-ELSE-SEND-EMPTY],CidrBlock=[VPC-CIDR-BLOCK],PrivateSubnetCIDR=[10.0.20.0/24],BucketName=vaultdb-hosted-content --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND

    Values you can use:-- 
        APPLICATIONNAME
            Pick a Uniquename for your installation and append test/dev/uat/prod etc to diffrentiate between different environments.
        ROLE-ARN-FROM-STEP-ABOVE
            Use role ARN from the output of step above where you created service role
        ADMIN-EMAIL-ADDRESS
            this email will receive the user passwords and instructions on how to start using VAULTDB ai platform.
        VPC-ID-IF-YOU-HAVE-ONE-ELSE-SEND-EMPTY
            Provide the VPC ID if you have one and wants to use that otherwise remove the parameter all together or provide empty value
        VPC-CIDR-BLOCK
            10.0.0.0/16

##### Example

awsv2 cloudformation create-stack `
--stack-name dev `
--role-arn "arn:aws:cloudformation:us-east-1:457538873532:stack/vaultdb-service-role/cb3757f0-d24d-11ed-9703-0ab9ea6915a5" 
--template-url file://vaultdb.yaml `
--parameters AdminEmail=vaultdb@outlook.com,CidrBlock=10.0.0.0/16,PrivateSubnetCIDR=10.0.20.0/24,BucketName=vaultdb-hosted-content `
--capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND

## License

All Images and Text copyright VaultDB.ai LLC
