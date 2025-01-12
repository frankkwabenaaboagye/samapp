import json
import boto3
import os


cognito = boto3.client('cognito-idp')
USER_POOL_ID = os.environ['USER_POOL_ID']

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