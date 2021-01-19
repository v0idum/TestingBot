import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL = '@RKKimyo'

DATETIME_FORMAT = "%d-%m-%Y %H:%M:%S"