from __future__ import print_function
import datetime
import sys
import shutil
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import csv
import os

# Configuración
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CSV_DIR = "/var/www/html/csv_reports/"
TOKEN_PATH = '/home/flaskapp/horas/token.json'
CREDENTIALS_PATH = '/home/flaskapp/horas/it-credentials-2025.json'

def obtener_eventos(ano, mes, service):
    tMin = f"{ano}-{str(mes).zfill(2)}-01T00:00:00-00:00"
    if mes == 12:
        tMax = f"{ano+1}-01-01T00:00:00-00:00"
    else:
        tMax = f"{ano}-{str(mes+1).zfill(2)}-01T00:00:00-00:00"

    calendar_list = service.calendarList().list().execute()
    calendars = calendar_list.get('items', [])

    eventos_totales = []

    for calendar in calendars:
        if calendar['summary'].startswith('Horarios'):
            calid = calendar['id']
            events_result = service.events().list(
                calendarId=calid, timeMin=tMin, timeMax=tMax,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])

            for event in events:
                if event['summary'] not in ['Trabajo Padre', 'No disponible', 'Birthdays']:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))

                    try:
                        start_d = datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
                        end_d = datetime.strptime(end[:16], "%Y-%m-%dT%H:%M")
                        delta = end_d - start_d
                        horas_trabajadas = round(delta.total_seconds() / 3600, 2)
                    except:
                        horas_trabajadas = 0.0

                    eventos_totales.append([
                        calendar['summary'].partition(' ')[2],
                        event['summary'],
                        start_d.strftime("%Y-%m-%d"),
                        int(start_d.strftime("%d")),
                        start_d.strftime("%H:%M"),
                        end_d.strftime("%H:%M"),
                        horas_trabajadas
                    ])

    return eventos_totales

def copiar_csv_al_servidor(nombre_archivo):
    destino = os.path.join(CSV_DIR, os.path.basename(nombre_archivo))
    try:
        shutil.copy(nombre_archivo, destino)
        os.chown(destino, os.getuid(), os.getgid())
        os.chmod(destino, 0o644)
        print(f"Archivo disponible en: https://tools.blumas.com.ar/csv_reports/{os.path.basename(nombre_archivo)}")
    except Exception as e:
        print(f"Error copiando {nombre_archivo} al servidor: {e}")

def generar_csv(nombre_archivo, eventos):
    with open(nombre_archivo, 'w+', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Operario', 'Edificio', 'Fecha', 'Dia', 'Comienzo', 'Fin', 'Horas'])
        for evento in eventos:
            writer.writerow(evento)

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

    hoy = datetime.today()
    ano_actual, mes_actual = hoy.year, hoy.month
    if mes_actual == 1:
        ano_anterior, mes_anterior = ano_actual - 1, 12
    else:
        ano_anterior, mes_anterior = ano_actual, mes_actual - 1

    nombre_actual = f"{ano_actual}-{str(mes_actual).zfill(2)}.csv"
    nombre_anterior = f"{ano_anterior}-{str(mes_anterior).zfill(2)}.csv"

    eventos_mes_actual = obtener_eventos(ano_actual, mes_actual, service)
    eventos_mes_anterior = obtener_eventos(ano_anterior, mes_anterior, service)

    generar_csv(nombre_actual, eventos_mes_actual)
    generar_csv(nombre_anterior, eventos_mes_anterior)

    copiar_csv_al_servidor(nombre_actual)
    copiar_csv_al_servidor(nombre_anterior)

    print(f"Archivos generados y publicados en el servidor: {nombre_actual}, {nombre_anterior}")

if __name__ == '__main__':
    main()
