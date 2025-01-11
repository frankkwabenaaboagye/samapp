import json
import boto3
import os
import uuid
from datetime import datetime, timedelta, timezone

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TASKS_TABLE'])

def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    # try:
    #     ip = requests.get("http://checkip.amazonaws.com/")
    # except requests.RequestException as e:
    #     # Send some context about this error to Lambda Logs
    #     print(e)

    #     raise e

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
            # "location": ip.text.replace("\n", "")
        }),
    }

def get_the_task(event, context):

    try:
        response = table.scan()
        tasks = response.get('Items', [])
        
        return {
            "statusCode": 200,
            "headers": {
            'Access-Control-Allow-Headers': 'X-Forwarded-For,Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,access-control-allow-origin,access-control-allow-credentials',
            'Access-Control-Allow-Origin': 'http://localhost:4200',
            'Access-Control-Allow-Methods': 'POST, GET, PUT, OPTIONS',
            'Access-Control-Allow-Credentials': 'true'
            },
            "body": json.dumps({
                'message': 'Success',
                'tasks': tasks
            })
        }
    except Exception as e:
        print("error when making the request")
        return {
            "statusCode": 500,
            "headers": {
                'Access-Control-Allow-Headers': 'X-Forwarded-For,Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,access-control-allow-origin,access-control-allow-credentials',
                'Access-Control-Allow-Origin': 'http://localhost:4200',
                'Access-Control-Allow-Methods': 'POST, GET, PUT, OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({'error': str(e)})
        }



def create_the_task(event, context):

    print("Event for the create ...")
    print(event)
    print("proeceeding to perform create task...")

    try:
        body = json.loads(event['body'])
        task_id = str(uuid.uuid4())
        
        task = {
            'task_id': task_id,
            'name': body['name'],
            'description': body['description'],
            'status': 'PENDING',
            'deadline': body['deadline'],
            'responsibility': body['responsibility'],
            'created_at': datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            'user_comment': '',
            'completed_at': ''
        }

        # Store task in DynamoDB
        table.put_item(Item=task)

        return {
            "statusCode": 200,
            "headers": {
                'Access-Control-Allow-Headers': 'X-Forwarded-For,Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,access-control-allow-origin,access-control-allow-credentials',
                'Access-Control-Allow-Origin': 'http://localhost:4200',
                'Access-Control-Allow-Methods': 'POST, GET, PUT, OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            "body": json.dumps({
                'message': 'Success',
                'task': task
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                'Access-Control-Allow-Headers': 'X-Forwarded-For,Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,access-control-allow-origin,access-control-allow-credentials',
                'Access-Control-Allow-Origin': 'http://localhost:4200',
                'Access-Control-Allow-Methods': 'POST, GET, PUT, OPTIONS',
                'Access-Control-Allow-Credentials': 'true'
            },
            "body": json.dumps({'error': str(e)})
        }














    # return {
    #     "statusCode": 200,
    #     "headers": {
    #         'Access-Control-Allow-Headers': 'X-Forwarded-For,Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,access-control-allow-origin,access-control-allow-credentials',
    #         'Access-Control-Allow-Origin': 'http://localhost:4200',
    #         'Access-Control-Allow-Methods': 'POST, GET, PUT, OPTIONS',
    #         'Access-Control-Allow-Credentials': 'true'
    #         },
    #     "body": json.dumps({
    #         "message": "hello tms is working"
    #     }),
    # }