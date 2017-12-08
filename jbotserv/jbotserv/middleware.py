from django.http import HttpResponseRedirect
from jbotserv import settings
from re import compile

def LoginRequiredMiddleware(get_response):
    
    # Generate list of urls patterns that are login exempt
    LOGIN_EXEMPT_URL_PATTERNS = [compile(expr) for expr in settings.LOGIN_EXEMPT_URLS]

    def middleware(request):

        # Check if request has user attr, set by AuthenticationMiddleware
	assert hasattr(request, 'user')

        # Check if user is authenticated and return the view if true
        if request.user.is_authenticated():
            return get_response(request)

        # Otherwise, check if the requested URL if login exempt
        path = request.path_info.strip("/")
        if any(m.match(path) for m in LOGIN_EXEMPT_URL_PATTERNS): 
            return get_response(request)

        # Return the LOGIN page on all other cases
        return HttpResponseRedirect(settings.LOGIN_URL)
    
    return middleware
