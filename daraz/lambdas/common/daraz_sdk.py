"""
Daraz Open Platform SDK for Python
"""

from typing import Any
from aws_lambda_powertools.utilities import parameters
import boto3
from aws_lambda_powertools import Logger
import requests
import time
import hmac
import hashlib
import socket
import platform
from aws_lambda_powertools import Logger

logger = Logger()
logger.append_keys(component="daraz_sdk")

P_SDK_VERSION = "daraz-py-sdk-ct-20240120"

P_APPKEY = "app_key"
P_ACCESS_TOKEN = "access_token"
P_TIMESTAMP = "timestamp"
P_SIGN = "sign"
P_SIGN_METHOD = "sign_method"
P_PARTNER_ID = "partner_id"
P_DEBUG = "debug"

P_CODE = 'code'
P_TYPE = 'type'
P_MESSAGE = 'message'
P_REQUEST_ID = 'request_id'

P_LOG_LEVEL_DEBUG = "DEBUG"
P_LOG_LEVEL_INFO = "INFO"
P_LOG_LEVEL_ERROR = "ERROR"


def sign(secret,api, parameters):
    sort_dict = sorted(parameters)
    
    parameters_str = "%s%s" % (api,
        str().join('%s%s' % (key, parameters[key]) for key in sort_dict))

    h = hmac.new(secret.encode(encoding="utf-8"), parameters_str.encode(encoding="utf-8"), digestmod=hashlib.sha256)

    return h.hexdigest().upper()


def mixStr(pstr):
    if(isinstance(pstr, str)):
        return pstr
    elif (isinstance(pstr, bytes)):
        return pstr.decode('utf-8')
    else:
        return str(pstr)

def logApiError(appkey, sdkVersion, requestUrl, code, message):
    localIp = socket.gethostbyname(socket.gethostname())
    platformType = platform.platform()
    logger.error({
        "appkey": appkey,
        "sdkVersion": sdkVersion,
        "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "localIp": localIp,
        "platformType": platformType,
        "requestUrl": requestUrl,
        "code": code,
        "message": message
    })

class DarazRequest(object):
    def __init__(self,api_pame,http_method = 'POST'):
        self._api_params = {}
        self._file_params = {}
        self._api_pame = api_pame
        self._http_method = http_method

    def add_api_param(self,key,value):
        self._api_params[key] = value

    def add_file_param(self,key,value):
        self._file_params[key] = value


class DarazResponse(object):
    def __init__(self):
        self.type = None
        self.code = None
        self.message = None
        self.request_id = None
        self.body = None
    
    def __str__(self, *args, **kwargs):
        sb = "type=" + mixStr(self.type) +\
            " code=" + mixStr(self.code) +\
            " message=" + mixStr(self.message) +\
            " requestId=" + mixStr(self.request_id)
        return sb

class DarazClient(object):
    
    log_level = P_LOG_LEVEL_ERROR
    def __init__(self, server_url,app_key,app_secret,timeout=30):
        self._server_url = server_url
        self._app_key = app_key
        self._app_secret = app_secret
        self._timeout = timeout
    
    def execute(self, request,access_token = None):

        sys_parameters = {
            P_APPKEY: self._app_key,
            P_SIGN_METHOD: "sha256",
            P_TIMESTAMP: str(int(round(time.time()))) + '000',
            P_PARTNER_ID: P_SDK_VERSION
        }

        if(self.log_level == P_LOG_LEVEL_DEBUG):
            sys_parameters[P_DEBUG] = 'true'

        if(access_token):
            sys_parameters[P_ACCESS_TOKEN] = access_token

        application_parameter = request._api_params

        sign_parameter = sys_parameters.copy()
        sign_parameter.update(application_parameter)

        sign_parameter[P_SIGN] = sign(self._app_secret,request._api_pame,sign_parameter)

        api_url = "%s%s" % (self._server_url,request._api_pame)

        full_url = api_url + "?"
        for key in sign_parameter:
            full_url += key + "=" + str(sign_parameter[key]) + "&"
        full_url = full_url[0:-1]

        try:
            if(request._http_method == 'POST' or len(request._file_params) != 0) :
                r = requests.post(api_url,sign_parameter,files=request._file_params, timeout=self._timeout)
            else:
                r = requests.get(api_url,sign_parameter, timeout=self._timeout)
        except Exception as err:
            logApiError(self._app_key, P_SDK_VERSION, full_url, "HTTP_ERROR", str(err))
            raise err

        response = DarazResponse()

        jsonobj = r.json()

        if P_CODE in jsonobj:
            response.code = jsonobj[P_CODE]
        if P_TYPE in jsonobj:
            response.type = jsonobj[P_TYPE]
        if P_MESSAGE in jsonobj:
            response.message = jsonobj[P_MESSAGE]
        if P_REQUEST_ID in jsonobj:
            response.request_id = jsonobj[P_REQUEST_ID]

        if response.code is not None and response.code != "0":
            logApiError(self._app_key, P_SDK_VERSION, full_url, response.code, response.message)
        else:
            if(self.log_level == P_LOG_LEVEL_DEBUG or self.log_level == P_LOG_LEVEL_INFO):
                logApiError(self._app_key, P_SDK_VERSION, full_url, "", "")

        response.body = jsonobj

        logger.debug(response)

        return response

class DarazOAuthTokens:
    def __init__(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token

    @classmethod
    def from_ssm(cls, path: str):
        """Retrieve tokens from SSM"""

        # Retrieve tokens from AWS SSM
        tokens = parameters.get_parameters(path, decrypt=True, max_age=60)
        logger.debug(tokens)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        return cls(access_token, refresh_token)
    
    @classmethod
    def from_code(cls, code: str, client: DarazClient):
        """Generate tokens from code"""

        request = DarazRequest('/auth/token/create')
        request.add_api_param('code', code)
        response = client.execute(request)
        logger.debug(response)
        body: Any = response.body

        access_token = body["access_token"]
        refresh_token = body["refresh_token"]

        return cls(access_token, refresh_token)
    
    @classmethod
    def from_refresh_token(cls, refresh_token: str, client: DarazClient):
        """Generate tokens from refresh token"""

        request = DarazRequest('/auth/token/refresh')
        request.add_api_param('refresh_token', refresh_token)
        response = client.execute(request)
        logger.debug(response)
        body: Any = response.body

        access_token = body["access_token"]
        refresh_token = body["refresh_token"]

        return cls(access_token, refresh_token)
    
    @classmethod
    def from_refresh_token_in_ssm(cls, path: str, client: DarazClient):
        """Generate tokens from refresh token in SSM"""

        # Retrieve refresh token from AWS SSM
        refresh_token = parameters.get_parameter(f"{path}/refresh_token", decrypt=True)

        return cls.from_refresh_token(refresh_token, client)
    
    def put_in_ssm(self, path: str):
        """Store tokens in SSM"""

        # TODO: can't use powertools https://github.com/aws-powertools/powertools-lambda-python/issues/3040
        ssm = boto3.client("ssm")

        # Store access token in AWS SSM
        ssm.put_parameter(
            Name=f"{path}/access_token",
            Description="Daraz oauth access token",
            Value=self.access_token,
            Type="SecureString",
            Overwrite=True,
        )

        # Store refresh token in AWS SSM
        ssm.put_parameter(
            Name=f"{path}/refresh_token",
            Description="Daraz oauth refresh token",
            Value=self.refresh_token,
            Type="SecureString",
            Overwrite=True,
        )

    def to_dict(self):
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }