# -*- coding: utf-8 -*-
from __future__ import print_function
import datetime
import os
from collections import defaultdict
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Configuración
TOKEN_PATH = '/home/flaskapp/horas/token.json'
CREDENTIALS_PATH = '/home/flaskapp/horas/it-credentials-2025.json'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
PDF_SALIDA = "/var/www/html/csv_reports/servicios.pdf"

# Días en español y orden
DIAS_ES = {
    'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
    'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
}
ORDEN_DIA = {'Lunes': 1, 'Martes': 2, 'Miércoles': 3, 'Jueves': 4, 'Viernes': 5, 'Sábado': 6, 'Domingo': 7}

# Fuente PDF
try:
    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'Arial-Bold.ttf'))
    addMapping('Arial', 0, 0, 'Arial')
    addMapping('Arial', 1, 0, 'Arial-Bold')
    FUENTE = 'Arial'
except:
    FUENTE = 'Helvetica'

def calcular_rango_30_dias():
    hoy = datetime.datetime.today()
    dias_hasta_domingo = (6 - hoy.weekday()) % 7
    domingo_siguiente = hoy + datetime.timedelta(days=dias_hasta_domingo)
    inicio = domingo_siguiente - datetime.timedelta(days=30)
    return inicio, domingo_siguiente

def obtener_eventos(service, fecha_inicio, fecha_fin):
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
                            'dia_en': start_dt.strftime("%A"),
                            'hora_inicio': start_dt.strftime("%H:%M"),
                            'hora_fin': end_dt.strftime("%H:%M")
                        })
                    except:
                        continue
    return eventos

def filtrar_ultima_semana_por_servicio(eventos):
    agrupados = defaultdict(list)
    for ev in eventos:
        clave = (ev['servicio'], ev['operario'])
        agrupados[clave].append(ev)

    final = []
    for (servicio, operario), lista_eventos in agrupados.items():
        semanas = defaultdict(list)
        for ev in lista_eventos:
            lunes = ev['fecha'] - datetime.timedelta(days=ev['fecha'].weekday())
            semanas[lunes].append(ev)
        if semanas:
            ultima_semana = max(semanas.keys())
            for ev in semanas[ultima_semana]:
                final.append([
                    servicio,
                    operario,
                    DIAS_ES.get(ev['dia_en'], ev['dia_en']),
                    ev['hora_inicio'],
                    ev['hora_fin']
                ])
    return final

def generar_pdf(datos, ruta_pdf):
    datos_ordenados = sorted(datos, key=lambda x: (
        x[0], x[1], ORDEN_DIA.get(x[2], 99), x[3]
    ))
    data = [['Servicio', 'Operario', 'Día', 'Comienzo', 'Fin']] + datos_ordenados

    estilo_tabla = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#00897b'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 1), (-1, -1), '#b2dfdb'),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), f'{FUENTE}-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), FUENTE),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ])

    pdf = SimpleDocTemplate(ruta_pdf, pagesize=A4, leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
    tabla = Table(data, repeatRows=1)
    tabla.setStyle(estilo_tabla)
    pdf.build([tabla])

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

    fecha_inicio, fecha_fin = calcular_rango_30_dias()
    eventos = obtener_eventos(service, fecha_inicio, fecha_fin)
    eventos_filtrados = filtrar_ultima_semana_por_servicio(eventos)
    generar_pdf(eventos_filtrados, PDF_SALIDA)

    try:
        os.chown(PDF_SALIDA, os.getuid(), os.getgid())
        os.chmod(PDF_SALIDA, 0o644)
        print(f"PDF generado exitosamente en: https://tools.blumas.com.ar/csv_reports/servicios.pdf")
    except Exception as e:
        print(f"Advertencia al ajustar permisos: {e}")

if __name__ == '__main__':
    main()
