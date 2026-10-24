import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(model=os.getenv("GROQ_MODEL"), temperature=0)
response = llm.invoke("In one sentence, what is a loan-to-value ratio?")
print(response.content)