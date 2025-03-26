#!/bin/bash

# Ejecutar el script Python
/home/flaskapp/horas/venv/bin/python /home/flaskapp/horas/horas-server.py

# Ajustar permisos de los archivos recién generados
chown flaskapp:flaskapp /var/www/html/csv_reports/*.csv
chmod 644 /var/www/html/csv_reports/*.csv

# Log opcional
echo "Ejecución completada: $(date)" >> /home/flaskapp/horas/horas.log
