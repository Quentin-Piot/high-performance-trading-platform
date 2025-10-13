"""
Configuration for the queue system across different environments.

This module provides configuration classes for development, testing, and production
environments, with support for environment variables and validation.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class SQSConfig:
    """SQS-specific configuration"""
    queue_url: str
    region_name: str = "us-east-1"
    dead_letter_queue_url: Optional[str] = None
    visibility_timeout: int = 300  # 5 minutes
    message_retention_period: int = 1209600  # 14 days
    max_receive_count: int = 3
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None  # For LocalStack
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.queue_url:
            raise ValueError("queue_url is required")
        
        if self.visibility_timeout < 0 or self.visibility_timeout > 43200:  # 12 hours max
            raise ValueError("visibility_timeout must be between 0 and 43200 seconds")
        
        if self.message_retention_period < 60 or self.message_retention_period > 1209600:  # 14 days max
            raise ValueError("message_retention_period must be between 60 and 1209600 seconds")


@dataclass
class WorkerConfig:
    """Worker configuration"""
    worker_id: Optional[str] = None
    max_concurrent_jobs: int = 1
    poll_interval: float = 1.0
    health_check_interval: float = 30.0
    shutdown_timeout: int = 300  # 5 minutes
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.max_concurrent_jobs < 1:
            raise ValueError("max_concurrent_jobs must be at least 1")
        
        if self.poll_interval < 0.1:
            raise ValueError("poll_interval must be at least 0.1 seconds")
        
        if self.health_check_interval < 1.0:
            raise ValueError("health_check_interval must be at least 1.0 seconds")


@dataclass
class JobConfig:
    """Job processing configuration"""
    default_timeout_seconds: int = 3600  # 1 hour
    default_max_retries: int = 3
    max_runs_per_job: int = 10000
    min_runs_per_job: int = 1
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.default_timeout_seconds < 60:
            raise ValueError("default_timeout_seconds must be at least 60 seconds")
        
        if self.default_max_retries < 0:
            raise ValueError("default_max_retries must be non-negative")
        
        if self.max_runs_per_job < self.min_runs_per_job:
            raise ValueError("max_runs_per_job must be >= min_runs_per_job")


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    enabled: bool = True
    metrics_retention_hours: int = 24
    health_check_interval: float = 30.0
    performance_window_size: int = 100
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.metrics_retention_hours < 1:
            raise ValueError("metrics_retention_hours must be at least 1")
        
        if self.performance_window_size < 10:
            raise ValueError("performance_window_size must be at least 10")


@dataclass
class QueueSystemConfig:
    """Complete queue system configuration"""
    environment: Environment
    sqs: SQSConfig
    worker: WorkerConfig = field(default_factory=WorkerConfig)
    job: JobConfig = field(default_factory=JobConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    @classmethod
    def from_environment(cls, env: Optional[str] = None) -> 'QueueSystemConfig':
        """
        Create configuration from environment variables.
        
        Args:
            env: Environment name (development, testing, staging, production)
            
        Returns:
            QueueSystemConfig instance
        """
        # Determine environment
        env_name = env or os.getenv("ENVIRONMENT", "development")
        try:
            environment = Environment(env_name.lower())
        except ValueError:
            raise ValueError(f"Invalid environment: {env_name}")
        
        # SQS Configuration
        sqs_config = SQSConfig(
            queue_url=os.getenv("SQS_QUEUE_URL", ""),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            dead_letter_queue_url=os.getenv("SQS_DLQ_URL"),
            visibility_timeout=int(os.getenv("SQS_VISIBILITY_TIMEOUT", "300")),
            message_retention_period=int(os.getenv("SQS_MESSAGE_RETENTION", "1209600")),
            max_receive_count=int(os.getenv("SQS_MAX_RECEIVE_COUNT", "3")),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            endpoint_url=os.getenv("SQS_ENDPOINT_URL")  # For LocalStack
        )
        
        # Worker Configuration
        worker_config = WorkerConfig(
            worker_id=os.getenv("WORKER_ID"),
            max_concurrent_jobs=int(os.getenv("MAX_CONCURRENT_JOBS", "1")),
            poll_interval=float(os.getenv("POLL_INTERVAL", "1.0")),
            health_check_interval=float(os.getenv("HEALTH_CHECK_INTERVAL", "30.0")),
            shutdown_timeout=int(os.getenv("SHUTDOWN_TIMEOUT", "300"))
        )
        
        # Job Configuration
        job_config = JobConfig(
            default_timeout_seconds=int(os.getenv("DEFAULT_JOB_TIMEOUT", "3600")),
            default_max_retries=int(os.getenv("DEFAULT_MAX_RETRIES", "3")),
            max_runs_per_job=int(os.getenv("MAX_RUNS_PER_JOB", "10000")),
            min_runs_per_job=int(os.getenv("MIN_RUNS_PER_JOB", "1"))
        )
        
        # Monitoring Configuration
        monitoring_config = MonitoringConfig(
            enabled=os.getenv("MONITORING_ENABLED", "true").lower() == "true",
            metrics_retention_hours=int(os.getenv("METRICS_RETENTION_HOURS", "24")),
            health_check_interval=float(os.getenv("MONITORING_HEALTH_CHECK_INTERVAL", "30.0")),
            performance_window_size=int(os.getenv("PERFORMANCE_WINDOW_SIZE", "100"))
        )
        
        return cls(
            environment=environment,
            sqs=sqs_config,
            worker=worker_config,
            job=job_config,
            monitoring=monitoring_config
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "environment": self.environment.value,
            "sqs": {
                "queue_url": self.sqs.queue_url,
                "region_name": self.sqs.region_name,
                "dead_letter_queue_url": self.sqs.dead_letter_queue_url,
                "visibility_timeout": self.sqs.visibility_timeout,
                "message_retention_period": self.sqs.message_retention_period,
                "max_receive_count": self.sqs.max_receive_count,
                "endpoint_url": self.sqs.endpoint_url
            },
            "worker": {
                "worker_id": self.worker.worker_id,
                "max_concurrent_jobs": self.worker.max_concurrent_jobs,
                "poll_interval": self.worker.poll_interval,
                "health_check_interval": self.worker.health_check_interval,
                "shutdown_timeout": self.worker.shutdown_timeout
            },
            "job": {
                "default_timeout_seconds": self.job.default_timeout_seconds,
                "default_max_retries": self.job.default_max_retries,
                "max_runs_per_job": self.job.max_runs_per_job,
                "min_runs_per_job": self.job.min_runs_per_job
            },
            "monitoring": {
                "enabled": self.monitoring.enabled,
                "metrics_retention_hours": self.monitoring.metrics_retention_hours,
                "health_check_interval": self.monitoring.health_check_interval,
                "performance_window_size": self.monitoring.performance_window_size
            }
        }
    
    def validate(self) -> None:
        """Validate the complete configuration"""
        # Environment-specific validations
        if self.environment == Environment.PRODUCTION:
            if not self.sqs.aws_access_key_id or not self.sqs.aws_secret_access_key:
                if not os.getenv("AWS_PROFILE") and not os.getenv("AWS_ROLE_ARN"):
                    raise ValueError("Production environment requires AWS credentials or IAM role")
            
            if self.sqs.endpoint_url:
                raise ValueError("Production environment should not use custom SQS endpoint")
        
        elif self.environment == Environment.TESTING:
            # Testing might use LocalStack
            if not self.sqs.endpoint_url and not self.sqs.queue_url.startswith("https://sqs"):
                raise ValueError("Testing environment requires either LocalStack endpoint or real SQS URL")
        
        # General validations
        if not self.sqs.queue_url:
            raise ValueError("SQS queue URL is required")


# Environment-specific configurations
def get_development_config() -> QueueSystemConfig:
    """Get development configuration with LocalStack defaults"""
    return QueueSystemConfig(
        environment=Environment.DEVELOPMENT,
        sqs=SQSConfig(
            queue_url=os.getenv("SQS_QUEUE_URL", "http://localhost:4566/000000000000/monte-carlo-jobs"),
            region_name="us-east-1",
            endpoint_url="http://localhost:4566",  # LocalStack default
            visibility_timeout=60,  # Shorter for development
            max_receive_count=2
        ),
        worker=WorkerConfig(
            max_concurrent_jobs=2,
            poll_interval=0.5,  # More frequent polling for development
            health_check_interval=10.0
        ),
        job=JobConfig(
            default_timeout_seconds=600,  # 10 minutes for development
            max_runs_per_job=1000  # Smaller for development
        )
    )


def get_testing_config() -> QueueSystemConfig:
    """Get testing configuration"""
    return QueueSystemConfig(
        environment=Environment.TESTING,
        sqs=SQSConfig(
            queue_url=os.getenv("SQS_QUEUE_URL", "http://localhost:4566/000000000000/test-monte-carlo-jobs"),
            region_name="us-east-1",
            endpoint_url="http://localhost:4566",  # LocalStack for testing
            visibility_timeout=30,  # Short for testing
            message_retention_period=3600,  # 1 hour for testing
            max_receive_count=1
        ),
        worker=WorkerConfig(
            max_concurrent_jobs=1,
            poll_interval=0.1,  # Fast polling for tests
            health_check_interval=5.0
        ),
        job=JobConfig(
            default_timeout_seconds=300,  # 5 minutes for testing
            default_max_retries=1,
            max_runs_per_job=100  # Small for testing
        ),
        monitoring=MonitoringConfig(
            metrics_retention_hours=1,
            performance_window_size=10
        )
    )


def get_production_config() -> QueueSystemConfig:
    """Get production configuration"""
    config = QueueSystemConfig.from_environment("production")
    
    # Production-specific overrides
    config.worker.max_concurrent_jobs = max(1, config.worker.max_concurrent_jobs)
    config.job.default_timeout_seconds = max(3600, config.job.default_timeout_seconds)
    config.monitoring.enabled = True
    
    return config


def get_config(environment: Optional[str] = None) -> QueueSystemConfig:
    """
    Get configuration for the specified environment.
    
    Args:
        environment: Environment name or None to auto-detect
        
    Returns:
        QueueSystemConfig instance
    """
    env_name = environment or os.getenv("ENVIRONMENT", "development")
    
    if env_name.lower() == "development":
        return get_development_config()
    elif env_name.lower() == "testing":
        return get_testing_config()
    elif env_name.lower() == "production":
        return get_production_config()
    else:
        # Use environment-based configuration for staging or custom environments
        return QueueSystemConfig.from_environment(env_name)