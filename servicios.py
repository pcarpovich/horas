# -*- coding: utf-8 -*-
from __future__ import print_function
import datetime
import csv
import os
from collections import defaultdict
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools

# Configuración
TOKEN_PATH = '/home/flaskapp/horas/token.json'
CREDENTIALS_PATH = '/home/flaskapp/horas/it-credentials-2025.json'
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CSV_DIR = "/var/www/html/csv_reports/"
ARCHIVO_SALIDA = os.path.join(CSV_DIR, "servicios.csv")

# Traducción de días
DIAS_ES = {
    'Monday': 'Lunes',
    'Tuesday': 'Martes',
    'Wednesday': 'Miércoles',
    'Thursday': 'Jueves',
    'Friday': 'Viernes',
    'Saturday': 'Sábado',
    'Sunday': 'Domingo'
}

# Orden lógico de los días
ORDEN_DIA = {
    'Lunes': 1, 'Martes': 2, 'Miércoles': 3,
    'Jueves': 4, 'Viernes': 5, 'Sábado': 6, 'Domingo': 7
}

def calcular_rango_30_dias():
    """Devuelve el rango de los últimos 30 días desde el domingo siguiente"""
    hoy = datetime.datetime.today()
    dias_hasta_domingo = (6 - hoy.weekday()) % 7
    domingo_siguiente = hoy + datetime.timedelta(days=dias_hasta_domingo)
    inicio = domingo_siguiente - datetime.timedelta(days=30)
    return inicio, domingo_siguiente

def obtener_eventos(service, fecha_inicio, fecha_fin):
    """Obtiene eventos de todos los calendarios Horarios entre las fechas dadas"""
    tMin = fecha_inicio.isoformat() + "Z"
    tMax = fecha_fin.isoformat() + "Z"
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
                        eventos.append({
                            'operario': operario,
                            'servicio': event['summary'],
                            'fecha': start_dt.date(),
                            'dia': start_dt.strftime("%A"),
                            'hora_inicio': start_dt.strftime("%H:%M"),
                            'hora_fin': end_dt.strftime("%H:%M")
                        })
                    except:
                        continue
    return eventos

def agrupar_por_servicio_y_semana(eventos):
    """Filtra por la última semana completa con al menos un evento por servicio-operario"""
    agrupados = defaultdict(list)

    for evento in eventos:
        clave = (evento['servicio'], evento['operario'])
        agrupados[clave].append(evento)

    resultados_finales = []

    for (servicio, operario), lista_eventos in agrupados.items():
        # Agrupar eventos por semana (Lunes-Domingo)
        semanas = defaultdict(list)
        for ev in lista_eventos:
            lunes = ev['fecha'] - datetime.timedelta(days=ev['fecha'].weekday())
            semanas[lunes].append(ev)

        if semanas:
            ultima_semana = max(semanas.keys())
            for ev in semanas[ultima_semana]:
                resultados_finales.append([
                    ev['operario'],
                    ev['servicio'],
                    DIAS_ES.get(ev['dia'], ev['dia']),
                    ev['hora_inicio'],
                    ev['hora_fin']
                ])
    return resultados_finales

def guardar_csv(eventos, ruta_archivo):
    with open(ruta_archivo, 'w+', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Operario', 'Servicio', 'Día', 'Comienzo', 'Fin'])
        for fila in eventos:
            writer.writerow(fila)

def main():
    # Autenticación
    store = file.Storage(TOKEN_PATH)
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets(CREDENTIALS_PATH, SCOPES)
        creds = tools.run_flow(flow, store)
    service = build('calendar', 'v3', http=creds.authorize(Http()))

    # Calcular rango de fechas
    fecha_inicio, fecha_fin = calcular_rango_30_dias()

    # Obtener eventos
    eventos = obtener_eventos(service, fecha_inicio, fecha_fin)

    # Filtrar última semana útil por servicio
    eventos_filtrados = agrupar_por_servicio_y_semana(eventos)

    # Ordenar por Operario, Servicio, Día, Comienzo
    eventos_ordenados = sorted(eventos_filtrados, key=lambda x: (
        x[0],  # Operario
        x[1],  # Servicio
        ORDEN_DIA.get(x[2], 99),  # Día
        x[3]   # Hora de comienzo
    ))

    # Guardar CSV
    guardar_csv(eventos_ordenados, ARCHIVO_SALIDA)

    # Ajustar permisos
    try:
        os.chown(ARCHIVO_SALIDA, os.getuid(), os.getgid())
        os.chmod(ARCHIVO_SALIDA, 0o644)
        print(f"CSV generado exitosamente en: https://tools.blumas.com.ar/csv_reports/servicios.csv")
    except Exception as e:
        print(f"Advertencia al ajustar permisos: {e}")

if __name__ == '__main__':
    main()
