# -*- coding: utf-8 -*-
import datetime
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# Configuración
TOKEN_PATH = '/home/flaskapp/horas/token.json'
CREDENTIALS_PATH = '/home/flaskapp/horas/it-credentials-2025.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CSV_SALIDA = "/var/www/html/csv_reports/clientes_horas.csv"

def obtener_clientes_mes_actual(service):
    hoy = datetime.datetime.today()
    inicio = datetime.datetime(hoy.year, hoy.month, 1)
    if hoy.month == 12:
        fin = datetime.datetime(hoy.year + 1, 1, 1)
    else:
        fin = datetime.datetime(hoy.year, hoy.month + 1, 1)

    tMin = inicio.isoformat() + "Z"
    tMax = fin.isoformat() + "Z"

    calendar_list = service.calendarList().list().execute()
    clientes = set()

    for calendar in calendar_list.get('items', []):
        if calendar['summary'].startswith('Horarios'):
            calid = calendar['id']
            eventos = service.events().list(
                calendarId=calid, timeMin=tMin, timeMax=tMax,
                singleEvents=True, orderBy='startTime'
            ).execute().get('items', [])

            for evento in eventos:
                resumen = evento.get('summary', '').strip()
                if resumen and resumen not in ['Trabajo Padre', 'No disponible', 'Birthdays']:
                    clientes.add(resumen)

    return sorted(clientes)

def generar_csv_manual(nombre_archivo, clientes):
    os.makedirs(os.path.dirname(nombre_archivo), exist_ok=True)
    with open(nombre_archivo, 'w', newline='', encoding='utf-8-sig') as f:
        f.write("cliente\n")
        for cliente in clientes:
            f.write(cliente.replace('\n', ' ').strip() + "\n")

def main():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    clientes = obtener_clientes_mes_actual(service)
    generar_csv_manual(CSV_SALIDA, clientes)

    try:
        os.chown(CSV_SALIDA, os.getuid(), os.getgid())
        os.chmod(CSV_SALIDA, 0o644)
        print(f"CSV generado exitosamente en: https://tools.blumas.com.ar/csv_reports/clientes_horas.csv")
    except Exception as e:
        print(f"Advertencia al ajustar permisos: {e}")

if __name__ == '__main__':
    main()
