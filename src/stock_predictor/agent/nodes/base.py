import os
import logging
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

def get_llm():
    """
    Initializes and returns the configured LLM based on environment variables.
    Returns None if no API keys are present, triggering the rules-based fallback.
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key.strip():
            logger.info("Initializing OpenAI ChatOpenAI model.")
            return ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=api_key)
            
    elif provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and api_key.strip():
            logger.info("Initializing Gemini ChatGoogleGenerativeAI model.")
            return ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, api_key=api_key)
            
    logger.info("No LLM API keys found or incorrect configuration. Operating in rules-based Fallback Mode.")
    return None
