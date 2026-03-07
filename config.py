"""
Configuration settings
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """System configuration"""
    
    # Telegram API
    TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE: str = os.getenv("TELEGRAM_PHONE", "")
    
    # Groq API for Llama3
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    
    # Search keywords for channel discovery
    SEARCH_KEYWORDS: List[str] = field(default_factory=lambda: [
        'weed', 'marijuana', 'cocaine', 'heroin', 'mdma', 'ecstasy',
        'xanax', 'oxy', 'adderall', 'fentanyl', 'ketamine',
        'buy drugs', 'drugs for sale', 'drug delivery',
        'pharma', 'meds', 'prescription'
    ])
    
    # Monitoring settings
    SCAN_INTERVAL_MINUTES: int = 5
    MESSAGES_PER_CHANNEL: int = 100
    AUTO_DISCOVERY_ENABLED: bool = True
    AUTO_JOIN_ENABLED: bool = True
    
    # File paths
    CHANNELS_FILE: str = "channels.json"
    RESULTS_FILE: str = "analysis_results.json"