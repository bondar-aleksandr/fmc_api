from dotenv import load_dotenv
import os

load_dotenv()

ASA_CONFIG = 'asa_run.txt'
FMC_LOGIN = os.getenv('login')
FMC_PASSWORD = os.getenv('password')
FMC_HOST = '1.2.3.4'
SERVER = f'https://{FMC_HOST}'
API_AUTH_PATH = "/api/fmc_platform/v1/auth/generatetoken"
AUTH_URL = SERVER + API_AUTH_PATH
LOG_FILE_SIZE = 5*1024*1024
LOGGING_LEVEL = 10 #20-INFO, 10- DEBUG