from dotenv import load_dotenv
import os

load_dotenv()
print("AI_API_KEY exists:", bool(os.getenv('AI_API_KEY')))
print("AI_PROVIDER:", os.getenv('AI_PROVIDER'))
print("AI_MODEL:", os.getenv('AI_MODEL'))

