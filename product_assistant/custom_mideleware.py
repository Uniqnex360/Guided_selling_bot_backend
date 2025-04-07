from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status
import jwt
from rest_framework.renderers import JSONRenderer
from datetime import timedelta
from django.http import HttpResponse,JsonResponse
from django.conf import settings


SIMPLE_JWT = {
  'ACCESS_TOKEN_LIFETIME': timedelta(minutes=500),
  'ALGORITHM': 'HS256',
  'SIGNING_KEY': settings.SECRET_KEY,
  'SESSION_COOKIE_DOMAIN' : '192.168.30.148',
  'SESSION_COOKIE_MAX_AGE' : 12000000,
  'AUTH_COOKIE': 'access_token',  # Cookie name. Enables cookies if value is set.
  'AUTH_COOKIE_SECURE': True,    # Whether the auth cookies should be secure (https:// only).
  'AUTH_COOKIE_SAMESITE': 'None',  # Whether to set the flag restricting cookie leaks on cross-site requests. This can be 'Lax', 'Strict', or 'None' to disable the flag.
}





def skip_for_paths():
    """
    decorator for skipping middleware based on path
    """
    def decorator(f):
        def check_if_health(self, request):
            l = ['""',"product","chat",'fetch_ai_content']
            k = request.path.split("/")
            for i in k:
                if i in  l:
                    response = self.get_response(request)
                    return response
            return f(self, request)
        return check_if_health
    return decorator

def createJsonResponse(request, token = None):
    authentication_token = ''
    if token:
        header,payload1,signature = str(token).split(".")
        authentication_token = header+'.'+payload1
    else:
        authentication_token = request.COOKIES.get('authentication_token', "").split(".")[0]
    data_map = dict()
    data_map['data'] = dict()
    response = Response(content_type = 'application/json') 
    response.data = data_map
    response.accepted_renderer = JSONRenderer()
    response.accepted_media_type = "application/json"
    response.renderer_context = {}
    response.data['message'] = 'success'
    response.data['status'] = True
    response.data['authentication_token'] = authentication_token
    response.status_code = 200
    return response







class customMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @skip_for_paths()
    def __call__(self, request):
        response = createJsonResponse(request)
        res = self.get_response(request)
        if isinstance(res, HttpResponse) and not isinstance(res, JsonResponse):
            return res
        if isinstance(res, Response):
            response.data['data'] = res.data
        else:
            response.data['data'] = res
        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = "application/json"
        response.renderer_context = {}
        response.render()
        return response






