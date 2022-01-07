import boto3


def create_dynamodb_table(table, endpoint_url):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    dynamodb.create_table(
        TableName=table,
        KeySchema=[
            {
                'AttributeName': 'domainName',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'domainName',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )


def delete_dynamodb_table(table, endpoint_url):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    dynamodb.Table(table).delete()
