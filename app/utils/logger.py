import logging
import os
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    """Setup logger com formatação consistente"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Criar handler para console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Criar handler para arquivo
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(f"logs/app-{datetime.now().strftime('%Y%m%d')}.log")
        file_handler.setLevel(logging.INFO)
        
        # Formato das mensagens
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Adicionar handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
    
    return logger
