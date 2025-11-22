import urllib.request
urls = ['http://127.0.0.1:8000/', 'http://127.0.0.1:8000/seating/', 'http://127.0.0.1:8000/timetable/start/']
for u in urls:
    try:
        with urllib.request.urlopen(u) as r:
            data = r.read(1200).decode('utf-8', errors='replace')
            print('URL:', u, 'STATUS', r.status)
            print(data[:400].replace('\n',' '))
            print('---\n')
    except Exception as e:
        print('URL:', u, 'ERROR', e)
