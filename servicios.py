# -*- coding: utf-8 -*-
from __future__ import print_function
import datetime
import csv
import os
import shutil
import calendar
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# Rutas y configuración
TOKEN_PATH = '/home/flaskapp/horas/token.json'
CREDENTIALS_PATH = '/home/flaskapp/horas/it-credentials-2025.json'
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CSV_DIR = "/var/www/html/csv_reports/"
ARCHIVO_SALIDA = os.path.join(CSV_DIR, "servicios.csv")

def obtener_eventos_rango(ano, mes, service):
    """Devuelve eventos entre el 1° y último día del mes indicado"""
    tMin = f"{ano}-{str(mes).zfill(2)}-01T00:00:00-00:00"
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    tMax = f"{ano}-{str(mes).zfill(2)}-{ultimo_dia}T23:59:59-00:00"

    eventos = []
    calendar_list = service.calendarList().list().execute()
    for calendar_item in calendar_list.get('items', []):
        if calendar_item['summary'].startswith('Horarios'):
            operario = calendar_item['summary'].partition(' ')[2]
            calid = calendar_item['id']
            events_result = service.events().list(
                calendarId=calid, timeMin=tMin, timeMax=tMax,
                singleEvents=True, orderBy='startTime'
            ).execute()
            for event in events_result.get('items', []):
                if event['summary'] not in ['Trabajo Padre', 'No disponible', 'Birthdays']:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    try:
                        start_dt = datetime.datetime.strptime(start[:16], "%Y-%m-%dT%H:%M")
                        end_dt = datetime.datetime.strptime(end[:16], "%Y-%m-%dT%H:%M")
                        eventos.append([
                            operario,
                            event['summary'],
                            start_dt.strftime("%Y-%m-%d"),
                            start_dt.strftime("%A"),
                            start_dt.strftime("%H:%M"),
                            end_dt.strftime("%H:%M"),
                        ])
                    except:
                        continue
    return eventos

def guardar_csv(eventos, ruta_archivo):
    """Guarda los eventos en un archivo CSV compatible con Excel"""
    with open(ruta_archivo, 'w+', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Operario', 'Servicio', 'Fecha', 'Día', 'Comienzo', 'Fin'])
        for evento in eventos:
            writer.writerow(evento)

def main():
    # Autenticación con Google Calendar
    store = file.Storage(TOKEN_PATH)
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(CREDENTIALS_PATH, SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    # Calcular mes actual y anterior
    hoy = datetime.datetime.today()
    ano_actual, mes_actual = hoy.year, hoy.month
    if mes_actual == 1:
        ano_anterior, mes_anterior = ano_actual - 1, 12
    else:
        ano_anterior, mes_anterior = ano_actual, mes_actual - 1

    # Obtener eventos de ambos meses
    eventos = []
    eventos += obtener_eventos_rango(ano_anterior, mes_anterior, service)
    eventos += obtener_eventos_rango(ano_actual, mes_actual, service)

    # Guardar CSV
    guardar_csv(eventos, ARCHIVO_SALIDA)

    # Ajustar permisos
    try:
        os.chown(ARCHIVO_SALIDA, os.getuid(), os.getgid())
        os.chmod(ARCHIVO_SALIDA, 0o644)
        print(f"CSV generado exitosamente en: https://tools.blumas.com.ar/csv_reports/servicios.csv")
    except Exception as e:
        print(f"Advertencia: no se pudieron ajustar los permisos: {e}")

if __name__ == '__main__':
    main()
