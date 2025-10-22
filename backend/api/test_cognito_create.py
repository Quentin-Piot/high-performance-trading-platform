import os
import sys

sys.path.append('src')

# Set environment variables directly
os.environ['COGNITO_CLIENT_ID'] = 'hcl2tpol6rk94cu1u0cg9o4f4'
os.environ['COGNITO_USER_POOL_ID'] = 'eu-west-3_pb05WIUdA'
os.environ['COGNITO_REGION'] = 'eu-west-3'

print("Environment variables set directly:")
print(f"  COGNITO_CLIENT_ID: '{os.getenv('COGNITO_CLIENT_ID')}'")
print(f"  COGNITO_USER_POOL_ID: '{os.getenv('COGNITO_USER_POOL_ID')}'")
print(f"  COGNITO_REGION: '{os.getenv('COGNITO_REGION')}'")

from core.cognito import CognitoService
from core.config import get_settings

# Test the settings loading
settings = get_settings()
print("\nSettings loaded:")
print(f"  ENV: {settings.env}")
print(f"  COGNITO_REGION: {settings.cognito_region}")
print(f"  COGNITO_USER_POOL_ID: {settings.cognito_user_pool_id}")
print(f"  COGNITO_CLIENT_ID: '{settings.cognito_client_id}'")
print(f"  AWS_ENDPOINT_URL: {settings.aws_endpoint_url}")

# Test the create_user function
cognito_service = CognitoService()
print("\nCognito service:")
print(f"  Client configured: {cognito_service.cognito_client is not None}")
print(f"  User pool ID: {cognito_service.user_pool_id}")
print(f"  Client ID: '{cognito_service.client_id}'")
print(f"  Region: {cognito_service.region}")

try:
    result = cognito_service.create_user("test-debug@example.com", "TempPass123!")
    print(f"Create user result: {result}")
except Exception as e:
    print(f"Error creating user: {e}")
    import traceback
    traceback.print_exc()
