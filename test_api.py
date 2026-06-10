import requests
import json

# Login con Pedro
login_url = 'http://localhost:8001/token/'
login_data = {'username': 'Pedro', 'password': 'test123'}

print('Login con Pedro...')
response = requests.post(login_url, json=login_data)
print('Status: ' + str(response.status_code))

if response.status_code == 200:
    tokens = response.json()
    token = tokens.get('access')
    print('Token obtenido')
    
    # GET asignaciones
    headers = {'Authorization': 'Bearer ' + token}
    url = 'http://localhost:8001/api/empleados/me/asignaciones'
    
    resp = requests.get(url, headers=headers)
    print('GET Status: ' + str(resp.status_code))
    
    if resp.status_code == 200:
        data = resp.json()
        print('Asignaciones encontradas: ' + str(len(data)))
        for item in data[:3]:
            inc_id = item['incidente_id']
            inc_tipo = item['incidente_tipo']
            estado = item['estado_tarea']
            print('  - Incidente ' + str(inc_id) + ': ' + str(inc_tipo) + ' (' + estado + ')')
    else:
        print('Error: ' + resp.text)
else:
    print('Error login: ' + response.text)
