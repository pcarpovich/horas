from flask import Flask, jsonify, send_from_directory
import os
import subprocess

app = Flask(__name__)

CSV_PATH = "/var/www/html/csv_reports/"

@app.route('/')
def home():
    return "Tools App - Blumas"

@app.route('/ejecutar-horas', methods=['GET', 'POST'])
def ejecutar_horas():
    try:
        # Cambiar directorio antes de ejecutar el script
        os.chdir("/home/flaskapp/horas")
        subprocess.run(["sudo", "-u", "flaskapp", "venv/bin/python", "horas-server.py"])
        return jsonify({"message": "Script ejecutado correctamente"})
    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500

@app.route('/descargar-csv/<yyyymm>', methods=['GET'])
def descargar_csv(yyyymm):
    # Convertir YYYYMM en YYYY-MM
    archivo = f"{yyyymm[:4]}-{yyyymm[4:]}.csv"

    if os.path.exists(os.path.join(CSV_PATH, archivo)):
        return send_from_directory(CSV_PATH, archivo, as_attachment=True)
    return jsonify({"message": "Archivo no encontrado"}), 404


@app.route('/listar-archivos', methods=['GET'])
def listar_archivos():
    archivos = sorted(os.listdir(CSV_PATH), reverse=True)[:10]
    return jsonify({"archivos": archivos})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
