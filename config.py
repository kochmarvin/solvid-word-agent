"""
Configuration module for the document editing agent API
"""
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT_GPT5 = os.getenv(
    "AZURE_OPENAI_ENDPOINT_GPT5",
    "https://offic-mhomh003-swedencentral.openai.azure.com/"
)
AZURE_OPENAI_API_KEY_GPT5 = os.getenv(
    "AZURE_OPENAI_API_KEY_GPT5",
    "5Xt61rTN84oi6yyobiEzwlnQS2fUj2fjs1v6kpWxC4IkUajSvyhmJQQJ99BKACfhMk5XJ3w3AAAAACOGE0yI"
)
MODEL_NAME = "gpt-5-mini"
API_VERSION = "2024-08-01-preview"

