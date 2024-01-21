import os

SSM_PARAMETERS_PATH = os.environ["SSM_PARAMETERS_PATH"]
API_URL = "https://api.daraz.com.bd/rest"
APP_KEY = os.environ["APP_KEY"]
APP_SECRET = os.environ["APP_SECRET"]
APP_CODE_SSM_PATH = f"{SSM_PARAMETERS_PATH}/app/code"
APP_TOKENS_SSM_PATH = f"{SSM_PARAMETERS_PATH}/app/oauth"