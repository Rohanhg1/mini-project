import urllib.request

try:
    with urllib.request.urlopen('http://127.0.0.1:8000/') as r:
        data = r.read(1600).decode('utf-8', errors='replace')
        print('STATUS', r.status)
        print(data[:1200])
except Exception as e:
    print('ERROR', e)
