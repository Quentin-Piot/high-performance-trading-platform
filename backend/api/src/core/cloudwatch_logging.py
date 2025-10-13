"""
Configuration optionnelle pour l'intégration CloudWatch Logs

Ce module fournit une configuration avancée pour envoyer les logs vers AWS CloudWatch.
Il nécessite l'installation de watchtower et boto3.

Installation requise:
    poetry add watchtower boto3

Variables d'environnement requises:
    AWS_REGION: Région AWS (ex: eu-west-1)
    AWS_LOG_GROUP: Nom du groupe de logs CloudWatch
    AWS_LOG_STREAM: Nom du stream de logs (optionnel, par défaut: hostname)
    AWS_ACCESS_KEY_ID: Clé d'accès AWS (ou utiliser IAM roles)
    AWS_SECRET_ACCESS_KEY: Clé secrète AWS (ou utiliser IAM roles)
"""
import logging
import os
from typing import Optional

try:
    from watchtower import CloudWatchLogsHandler
    import boto3
    CLOUDWATCH_AVAILABLE = True
except ImportError:
    CLOUDWATCH_AVAILABLE = False


def setup_cloudwatch_logging(
    log_group: Optional[str] = None,
    log_stream: Optional[str] = None,
    region: Optional[str] = None,
    level: int = logging.INFO
) -> Optional[CloudWatchLogsHandler]:
    """
    Configure CloudWatch logging handler.
    
    Args:
        log_group: CloudWatch log group name
        log_stream: CloudWatch log stream name (defaults to hostname)
        region: AWS region
        level: Logging level
        
    Returns:
        CloudWatchLogsHandler if successful, None otherwise
    """
    if not CLOUDWATCH_AVAILABLE:
        logging.getLogger("cloudwatch").warning(
            "CloudWatch logging not available. Install with: poetry add watchtower boto3"
        )
        return None
    
    # Configuration depuis les variables d'environnement
    log_group = log_group or os.getenv("AWS_LOG_GROUP")
    log_stream = log_stream or os.getenv("AWS_LOG_STREAM")
    region = region or os.getenv("AWS_REGION", "eu-west-1")
    
    if not log_group:
        logging.getLogger("cloudwatch").warning(
            "AWS_LOG_GROUP not configured. CloudWatch logging disabled."
        )
        return None
    
    try:
        # Créer le client CloudWatch Logs
        session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=region
        )
        
        # Configurer le handler CloudWatch
        handler = CloudWatchLogsHandler(
            log_group=log_group,
            stream_name=log_stream,
            boto3_session=session,
            send_interval=5,  # Envoyer les logs toutes les 5 secondes
            max_batch_size=10000,  # Taille maximale du batch
            max_batch_count=100,  # Nombre maximum de messages par batch
            create_log_group=True,  # Créer le groupe s'il n'existe pas
            create_log_stream=True,  # Créer le stream s'il n'existe pas
        )
        
        handler.setLevel(level)
        
        # Format JSON pour CloudWatch (compatible avec notre JSONFormatter)
        from core.logging import JSONFormatter
        handler.setFormatter(JSONFormatter())
        
        logging.getLogger("cloudwatch").info(
            "CloudWatch logging configured",
            extra={
                "log_group": log_group,
                "log_stream": log_stream,
                "region": region
            }
        )
        
        return handler
        
    except Exception as e:
        logging.getLogger("cloudwatch").error(
            "Failed to configure CloudWatch logging",
            extra={"error": str(e)}
        )
        return None


def add_cloudwatch_to_logger(logger_name: str = None) -> bool:
    """
    Ajoute CloudWatch handler à un logger existant.
    
    Args:
        logger_name: Nom du logger (None pour root logger)
        
    Returns:
        True si le handler a été ajouté avec succès
    """
    handler = setup_cloudwatch_logging()
    if not handler:
        return False
    
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    
    return True


def setup_enhanced_logging_with_cloudwatch():
    """
    Configuration complète du logging avec CloudWatch optionnel.
    
    Cette fonction combine la configuration locale existante avec CloudWatch.
    """
    # Configuration locale existante
    from core.logging import setup_logging
    setup_logging()
    
    # Ajout de CloudWatch si configuré
    if os.getenv("ENABLE_CLOUDWATCH_LOGGING", "false").lower() == "true":
        cloudwatch_handler = setup_cloudwatch_logging()
        if cloudwatch_handler:
            # Ajouter CloudWatch à tous les loggers principaux
            root_logger = logging.getLogger()
            root_logger.addHandler(cloudwatch_handler)
            
            # Filtres pour CloudWatch
            from core.logging import RequestIdFilter, SecretsFilter
            cloudwatch_handler.addFilter(RequestIdFilter())
            cloudwatch_handler.addFilter(SecretsFilter())
            
            logging.getLogger("app").info("Enhanced logging with CloudWatch enabled")
        else:
            logging.getLogger("app").warning("CloudWatch logging requested but failed to configure")
    else:
        logging.getLogger("app").info("CloudWatch logging disabled (set ENABLE_CLOUDWATCH_LOGGING=true to enable)")