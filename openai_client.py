"""
OpenAI client initialization
"""
from openai import AzureOpenAI
from config import AZURE_OPENAI_ENDPOINT_GPT5, AZURE_OPENAI_API_KEY_GPT5, API_VERSION

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY_GPT5,
    api_version=API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT_GPT5
)

