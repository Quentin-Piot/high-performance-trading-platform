#!/usr/bin/env python3
"""
Debug script to test AWS credentials configuration
"""
import sys
import os
sys.path.insert(0, 'src')

from config import get_testing_config
from infrastructure.security import CredentialManager

def main():
    print("=== Debug AWS Credentials ===")
    
    # Get testing config
    config = get_testing_config()
    print(f"Config environment: {config.environment}")
    print(f"SQS config: {config.sqs}")
    print(f"AWS credentials: {config.sqs.aws_credentials}")
    
    if config.sqs.aws_credentials:
        print(f"Credentials valid: {config.sqs.aws_credentials.is_valid()}")
        print(f"Masked data: {config.sqs.aws_credentials.mask_sensitive_data()}")
        
        # Test validation
        is_valid = CredentialManager.validate_credentials(config.sqs.aws_credentials)
        print(f"Validation result: {is_valid}")
    else:
        print("No AWS credentials found in config")

if __name__ == "__main__":
    main()