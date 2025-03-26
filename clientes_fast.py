# -*- coding: utf-8 -*-
import os
import datetime

# Archivos
BASE_DIR = "/var/www/html/csv_reports"
HOY = datetime.datetime.today()
NOMBRE_CSV_ENTRADA = f"{HOY.year}-{str(HOY.month).zfill(2)}.csv"
RUTA_CSV_ENTRADA = os.path.join(BASE_DIR, NOMBRE_CSV_ENTRADA)
RUTA_CSV_SALIDA = os.path.join(BASE_DIR, "clientes_horas.csv")


def obtener_clientes_desde_csv(ruta):
    clientes = set()
    try:
        with open(ruta, "r", encoding="utf-8-sig") as f:
            encabezado = f.readline().strip().split(",")
            idx_edificio = encabezado.index("Edificio")

            for linea in f:
                partes = linea.strip().split(",")
                if len(partes) > idx_edificio:
                    cliente = partes[idx_edificio].strip()
                    if cliente:
                        clientes.add(cliente)
    except Exception as e:
        print(f"Error leyendo {ruta}: {e}")
    return sorted(clientes)


def generar_csv_clientes(ruta_salida, lista_clientes):
    os.makedirs(os.path.dirname(ruta_salida), exist_ok=True)
    with open(ruta_salida, mode='w', newline='', encoding='utf-8-sig') as f:
        f.write("cliente\n")
        for cliente in lista_clientes:
            f.write(cliente.replace('\n', ' ').strip() + "\n")


def main():
    if not os.path.exists(RUTA_CSV_ENTRADA):
        print(f"No se encontró el archivo de entrada: {RUTA_CSV_ENTRADA}")
        return

    clientes = obtener_clientes_desde_csv(RUTA_CSV_ENTRADA)
    generar_csv_clientes(RUTA_CSV_SALIDA, clientes)

    try:
        os.chown(RUTA_CSV_SALIDA, os.getuid(), os.getgid())
        os.chmod(RUTA_CSV_SALIDA, 0o644)
        print(f"Archivo generado correctamente: {RUTA_CSV_SALIDA}")
    except Exception as e:
        print(f"Advertencia al ajustar permisos: {e}")

if __name__ == '__main__':
    main()