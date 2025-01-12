import json
import boto3
import os
import uuid
from datetime import datetime, timedelta, timezone



def assignDynamodb():
    try:
        return boto3.resource('dynamodb')
    except Exception as e:
        return " "
   
def assignTable():
    try:
        return dynamodb.Table(os.environ['TASKS_TABLE'])
    except Exception as e:
        return " "
     
dynamodb = assignDynamodb()
table = assignTable()



myHeaders = {
    'Access-Control-Allow-Headers': 'X-Forwarded-For,Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,access-control-allow-origin,access-control-allow-credentials',
    'Access-Control-Allow-Origin': 'http://localhost:4200',
    'Access-Control-Allow-Methods': 'POST, GET, PUT, OPTIONS, DELETE',
    'Access-Control-Allow-Credentials': 'true'
}

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
            "headers": myHeaders,
            "body": json.dumps({
                'message': 'Success',
                'tasks': tasks
            })
        }
    except Exception as e:
        print("error when making the request")
        return {
            "statusCode": 500,
            "headers": myHeaders,
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
            "headers": myHeaders,
            "body": json.dumps({
                'message': 'Success',
                'task': task
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": myHeaders,
            "body": json.dumps({'error': str(e)})
        }


def update_the_task(event, context):

    try:
        # Get task ID from path parameters
        task_id = event['pathParameters']['taskId']
        
        # Get user information from Cognito authorizer
        user_email = event['requestContext']['authorizer']['claims']['email']
        user_groups = event['requestContext']['authorizer']['claims'].get('cognito:groups', [])
        
        # Parse request body
        body = json.loads(event['body'])
        
        # Verify only status and comment are being updated
        allowed_fields = {'status', 'user_comment'}
        update_fields = set(body.keys())
        
        if not update_fields.issubset(allowed_fields):
            return {
                'statusCode': 400,
                'headers': myHeaders,
                'body': json.dumps({
                    'error': 'Only status and user_comment can be updated'
                })
            }
        
        # Get the current task
        task_response = table.get_item(
            Key={'task_id': task_id}
        )
        
        if 'Item' not in task_response:
            return {
                'statusCode': 404,
                'headers': myHeaders,
                'body': json.dumps({'error': 'Task not found'})
            }
            
        current_task = task_response['Item']
        
        # Check if user is authorized (admin or assigned team member)
        if 'Admin' not in user_groups and current_task['responsibility'] != user_email:
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Not authorized to update this task'})
            }
        
        # Prepare update expression
        update_expr = 'SET '
        expr_attrs = {}
        expr_values = {}
        
        if 'status' in body:
            update_expr += '#status = :status, '
            expr_attrs['#status'] = 'status'
            expr_values[':status'] = body['status']
            
        if 'user_comment' in body:
            update_expr += '#comment = :comment, '
            expr_attrs['#comment'] = 'user_comment'
            expr_values[':comment'] = body['user_comment']
            
        # Add last updated timestamp
        update_expr += '#updated_at = :updated_at'
        expr_attrs['#updated_at'] = 'updated_at'
        expr_values[':updated_at'] = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        
        # Update the task
        table.update_item(
            Key={'task_id': task_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attrs,
            ExpressionAttributeValues=expr_values
        )
        
        # If status is changed to 'COMPLETED', notify administrators
        # if body.get('status') == 'COMPLETED':
        #     notify_task_completion(current_task, user_email)
            
        return {
            'statusCode': 200,
            'headers': myHeaders,
            'body': json.dumps({
                'message': 'Task updated successfully',
                'task_id': task_id
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': myHeaders,
            'body': json.dumps({'error': str(e)})
        }


def delete_the_task(event, context):
    try:
            
        task_id = event['pathParameters']['taskId']
        
        # Delete the task
        response = table.delete_item(
            Key={'task_id': task_id},
            ReturnValues='ALL_OLD'  # This will return the deleted item
        )
        
        # Check if the item existed before deletion
        if 'Attributes' not in response:
            return {
                'statusCode': 404,
                'headers': myHeaders,
                'body': json.dumps({'error': 'Task not found'})
            }
            
        return {
            'statusCode': 200,
            'headers': myHeaders,
            'body': json.dumps({
                'message': 'Task deleted successfully',
                'deletedTask': response['Attributes']
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': myHeaders,
            'body': json.dumps({'error': str(e)})
        }

def get_the_task_by_id(event, context):
    try:
        task_id = event['pathParameters']['taskId']
        
        # Get the specific task from DynamoDB
        response = table.get_item(
            Key={'task_id': task_id}
        )
        
        # Check if the task exists
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': myHeaders,
                'body': json.dumps({'error': 'Task not found'})
            }
            
        return {
            'statusCode': 200,
            'headers': myHeaders,
            'body': json.dumps(response['Item'])
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': myHeaders,
            'body': json.dumps({'error': str(e)})
        }


def get_the_user_tasks(event, context):
    print("Event for get user tasks ...")
    print(event)
    print("proceeding to get user tasks...")

    try:
        # Get user ID from path parameters
        user_email = event['pathParameters']['userId']
        
        # Get tasks for specific user
        response = table.scan(
            FilterExpression='responsibility = :user',
            ExpressionAttributeValues={
                ':user': user_email
            }
        )
        
        tasks = response['Items']
        
        # Handle pagination if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                FilterExpression='responsibility = :user',
                ExpressionAttributeValues={
                    ':user': user_email
                }
            )
            tasks.extend(response['Items'])

        return {
            'statusCode': 200,
            'headers': myHeaders,
            'body': json.dumps({
                'tasks': tasks,
                'count': len(tasks),
                'user': user_email
            })
        }
    except KeyError:
        return {
            'statusCode': 400,
            'headers': myHeaders,
            'body': json.dumps({
                'error': 'Missing user ID in path parameters'
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': myHeaders,
            'body': json.dumps({
                'error': str(e)
            })
        }







