import urllib.request, urllib.parse
import http.cookiejar
import re
import sys

url = 'http://localhost:8000/admin/login/'
req = urllib.request.Request(url)
resp = urllib.request.urlopen(req)
html = resp.read().decode('utf-8')
csrf_match = re.search(r'name=\"csrfmiddlewaretoken\" value=\"([^\"]+)\"', html)
if csrf_match:
    csrf = csrf_match.group(1)
    print('CSRF:', csrf)
else:
    print('CSRF not found')
    sys.exit(1)
