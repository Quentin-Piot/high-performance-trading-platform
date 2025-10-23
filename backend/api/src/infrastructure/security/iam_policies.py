"""
IAM Policy definitions for least-privilege access to AWS services.
This module provides IAM policy templates for different components of the system,
following the principle of least privilege for security best practices.
"""
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class IAMPolicy:
    """IAM Policy representation"""
    version: str = "2012-10-17"
    statements: list[dict[str, Any]] = None
    def __post_init__(self):
        if self.statements is None:
            self.statements = []
    def to_json(self) -> str:
        """Convert policy to JSON string"""
        return json.dumps(
            {"Version": self.version, "Statement": self.statements}, indent=2
        )
    def to_dict(self) -> dict[str, Any]:
        """Convert policy to dictionary"""
        return {"Version": self.version, "Statement": self.statements}
class IAMPolicyBuilder:
    """Builder for creating IAM policies with least-privilege principles"""
    @staticmethod
    def monte_carlo_worker_policy(
        sqs_queue_arn: str,
        s3_bucket_arn: str,
        cloudwatch_log_group_arn: str | None = None,
    ) -> IAMPolicy:
        """
        Create IAM policy for Monte Carlo workers with minimal required permissions.
        Args:
            sqs_queue_arn: ARN of the SQS queue for job processing
            s3_bucket_arn: ARN of the S3 bucket for artifact storage
            cloudwatch_log_group_arn: Optional CloudWatch log group ARN
        Returns:
            IAMPolicy with least-privilege permissions
        """
        statements = [
            {
                "Sid": "SQSJobProcessing",
                "Effect": "Allow",
                "Action": [
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:ChangeMessageVisibility",
                    "sqs:GetQueueAttributes",
                ],
                "Resource": sqs_queue_arn,
            },
            {
                "Sid": "S3ArtifactStorage",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:GetObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                ],
                "Resource": [s3_bucket_arn, f"{s3_bucket_arn}/monte-carlo-artifacts/*"],
                "Condition": {"StringLike": {"s3:prefix": ["monte-carlo-artifacts/*"]}},
            },
            {
                "Sid": "S3LifecycleManagement",
                "Effect": "Allow",
                "Action": [
                    "s3:PutLifecycleConfiguration",
                    "s3:GetLifecycleConfiguration",
                ],
                "Resource": s3_bucket_arn,
            },
        ]
        if cloudwatch_log_group_arn:
            statements.append(
                {
                    "Sid": "CloudWatchLogging",
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams",
                    ],
                    "Resource": f"{cloudwatch_log_group_arn}:*",
                }
            )
        return IAMPolicy(statements=statements)
    @staticmethod
    def api_server_policy(
        sqs_queue_arn: str,
        s3_bucket_arn: str,
        cloudwatch_log_group_arn: str | None = None,
    ) -> IAMPolicy:
        """
        Create IAM policy for API servers with minimal required permissions.
        Args:
            sqs_queue_arn: ARN of the SQS queue for job submission
            s3_bucket_arn: ARN of the S3 bucket for artifact access
            cloudwatch_log_group_arn: Optional CloudWatch log group ARN
        Returns:
            IAMPolicy with least-privilege permissions
        """
        statements = [
            {
                "Sid": "SQSJobSubmission",
                "Effect": "Allow",
                "Action": [
                    "sqs:SendMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                ],
                "Resource": sqs_queue_arn,
            },
            {
                "Sid": "S3ArtifactAccess",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket", "s3:GetObjectVersion"],
                "Resource": [s3_bucket_arn, f"{s3_bucket_arn}/monte-carlo-artifacts/*"],
                "Condition": {"StringLike": {"s3:prefix": ["monte-carlo-artifacts/*"]}},
            },
        ]
        if cloudwatch_log_group_arn:
            statements.append(
                {
                    "Sid": "CloudWatchLogging",
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams",
                    ],
                    "Resource": f"{cloudwatch_log_group_arn}:*",
                }
            )
        return IAMPolicy(statements=statements)
    @staticmethod
    def monitoring_policy(
        cloudwatch_namespace: str = "TradingPlatform/MonteCarloJobs",
    ) -> IAMPolicy:
        """
        Create IAM policy for monitoring and metrics collection.
        Args:
            cloudwatch_namespace: CloudWatch metrics namespace
        Returns:
            IAMPolicy with monitoring permissions
        """
        statements = [
            {
                "Sid": "CloudWatchMetrics",
                "Effect": "Allow",
                "Action": [
                    "cloudwatch:PutMetricData",
                    "cloudwatch:GetMetricStatistics",
                    "cloudwatch:ListMetrics",
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {"cloudwatch:namespace": cloudwatch_namespace}
                },
            },
            {
                "Sid": "CloudWatchAlarms",
                "Effect": "Allow",
                "Action": ["cloudwatch:DescribeAlarms", "cloudwatch:PutMetricAlarm"],
                "Resource": "*",
            },
        ]
        return IAMPolicy(statements=statements)
def generate_terraform_policies(
    sqs_queue_arn: str, s3_bucket_arn: str, cloudwatch_log_group_arn: str | None = None
) -> dict[str, str]:
    """
    Generate Terraform-compatible IAM policy documents.
    Args:
        sqs_queue_arn: SQS queue ARN
        s3_bucket_arn: S3 bucket ARN
        cloudwatch_log_group_arn: Optional CloudWatch log group ARN
    Returns:
        Dictionary of policy names to JSON policy documents
    """
    builder = IAMPolicyBuilder()
    return {
        "monte_carlo_worker_policy": builder.monte_carlo_worker_policy(
            sqs_queue_arn, s3_bucket_arn, cloudwatch_log_group_arn
        ).to_json(),
        "api_server_policy": builder.api_server_policy(
            sqs_queue_arn, s3_bucket_arn, cloudwatch_log_group_arn
        ).to_json(),
        "monitoring_policy": builder.monitoring_policy().to_json(),
    }
def validate_policy_permissions(policy: IAMPolicy, required_actions: list[str]) -> bool:
    """
    Validate that a policy contains all required actions.
    Args:
        policy: IAM policy to validate
        required_actions: List of required actions
    Returns:
        True if all required actions are present
    """
    policy_actions = set()
    for statement in policy.statements:
        if statement.get("Effect") == "Allow":
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            policy_actions.update(actions)
    return all(action in policy_actions for action in required_actions)
