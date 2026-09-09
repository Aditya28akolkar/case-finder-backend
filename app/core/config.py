from dotenv import load_dotenv
import os

load_dotenv()


PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")