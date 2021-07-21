from dotenv import load_dotenv
import os

load_dotenv()

ASA_CONFIG = 'asa_config.txt'
FMC_LOGIN = os.getenv('login')
FMC_PASSWORD = os.getenv('password')
FMC_HOST = '172.18.59.15'
LOG_FILE_SIZE = 5 * 1024 * 1024
LOGGING_LEVEL = 10  # 20-INFO, 10- DEBUG