import json
import boto3
import os
import logging
from datetime import datetime, timedelta, timezone

USER_POOL_ID = os.environ['USER_POOL_ID']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito = boto3.client('cognito-idp')
sfn = boto3.client('stepfunctions')
logs = boto3.client('logs')
sns = boto3.client('sns')

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
            "message": "hello user management is working",
            # "location": ip.text.replace("\n", "")
        }),
    }




def onboard_user(event, context):
    try:
        body = json.loads(event['body'])
        email = body['email']
        name = body['name']
        role = body['role']
        
        # Create user in Cognito
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'name', 'Value': name},
                {'Name': 'custom:role', 'Value': role}
            ],
            DesiredDeliveryMediums=['EMAIL']
        )
        
        # Add user to appropriate group
        group_name = 'Admin' if role.lower() == 'admin' else 'TeamMember'
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=email,
            GroupName=group_name
        )
        
        return {
            "statusCode": 200,
            'body': json.dumps({'message': 'User created successfully'})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({'error': str(e)})
        }
    
def get_the_users(event, context):
    print("starting the get users")
    print("event =>")
    print(event)
    try:
        # List users from Cognito User Pool
        response = cognito.list_users(
            UserPoolId=USER_POOL_ID
        )

        print("response...=>")
        print(response)
        
        # Format the response
        users = []
        for user in response.get('Users', []):
            user_data = {
                'id': user['Username'],
                'name': '',
                'email': '',
                'role': '',
                'status': user['UserStatus']
            }
            
            # Extract attributes
            for attr in user.get('Attributes', []):
                if attr['Name'] == 'email':
                    user_data['email'] = attr['Value']
                elif attr['Name'] == 'name':
                    user_data['name'] = attr['Value']
                elif attr['Name'] == 'custom:role':
                    user_data['role'] = attr['Value']
            
            users.append(user_data)
        
        return {
            "statusCode": 200,
            "headers": myHeaders,
            "body": json.dumps({'users': users})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")  # Add logging for debugging
        return {
            "statusCode": 500,
            "headers": myHeaders,
            "body": json.dumps({
                'error': str(e)
            })
        }
    

def post_confirmation_handler(event, context):
    """
    Handles post confirmation tasks:
    1. Adds user to TeamMember group
    2. Starts subscription workflow
    """
    try:
        # Part 1: Add user to TeamMember group
        user_pool_id = event['userPoolId']
        username = event['userName']
        
        print("Starting part 1: Adding user to TeamMember group")
        # this part has been done remove it
        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName='TeamMember'
        )
        print(f"Successfully added user {username} to TeamMember group")

        # Part 2: Start subscription workflow
        print("Starting part 2: Initiating subscription workflow")
        user_email = event['request']['userAttributes']['email']
        
        # Start the parallel state machine with the email
        response = sfn.start_execution(
            stateMachineArn=os.environ['SUBSCRIPTION_WORKFLOW_ARN'],
            input=json.dumps({
                'email': user_email
            })
        )
        print(f"Successfully started subscription workflow: {response['executionArn']}")
        
        return event
        
    except Exception as e:
        print(f"Error in post confirmation handler: {str(e)}")
        raise e
    

def ensure_log_group_exists(context):
    """Ensures CloudWatch log group exists"""
    log_group_name = f"/aws/lambda/{context.function_name}"
    try:
        try:
            logs.create_log_group(logGroupName=log_group_name)
            logger.info(f"Created log group: {log_group_name}")
            logs.put_retention_policy(
                logGroupName=log_group_name,
                retentionInDays=30
            )
        except logs.exceptions.ResourceAlreadyExistsException:
            logger.info(f"Log group already exists: {log_group_name}")
        except Exception as e:
            logger.error(f"Error creating log group: {str(e)}")
    except Exception as e:
        logger.error(f"Error in ensure_log_group_exists: {str(e)}")

def subscribe_the_user(event, context):
    """
    Handles single topic subscription.
    Expected event format:
    {
        "TopicArn": "arn:aws:sns:region:account:topic",
        "Protocol": "email",
        "Endpoint": "user@example.com"
    }
    """
    print("executing handler...")
    ensure_log_group_exists(context)
    logger.info(f"Processing subscription request: {json.dumps(event)}")
    
    try:
        # Extract parameters from the event
        topic_arn = event['TopicArn']
        protocol = event['Protocol']
        endpoint = event['Endpoint']
        
        logger.info(f"Subscribing {endpoint} to topic {topic_arn}")
        
        # Create the subscription
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=endpoint,
            ReturnSubscriptionArn=True
        )
        
        subscription_arn = response['SubscriptionArn']
        
        # If this is the assignment notification topic, set up filtering
        if topic_arn.endswith('TasksAssignmentNotificationTopic'):
            logger.info("Setting up filter policy for assignment notifications")
            sns.set_subscription_attributes(
                SubscriptionArn=subscription_arn,
                AttributeName='FilterPolicy',
                AttributeValue=json.dumps({
                    'responsibility': [endpoint]  # Filter by assigned user's email
                })
            )
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Successfully created subscription',
                'subscriptionArn': subscription_arn,
                'endpoint': endpoint,
                'topicArn': topic_arn
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise e


   
