import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm():
    """Returns the Groq model every agent uses. temperature=0 means consistent, non-creative answers."""
    return ChatGroq(model=os.getenv("GROQ_MODEL"), temperature=0)