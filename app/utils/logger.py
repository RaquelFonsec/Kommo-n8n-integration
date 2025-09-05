import logging
import os
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    """Configura logger para o módulo"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Configurar formato
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Nível de log
        log_level = os.getenv("LOG_LEVEL", "INFO")
        logger.setLevel(getattr(logging, log_level.upper()))
    
    return logger
