import sqlite3

# Ruta a la base de datos SQLite
db_path = "c:\\Users\\desib\\Documents\\app_Konta\\db.sqlite3"

# Consulta SQL para calcular dinámicamente los totales de Debe y Haber
query = """
SELECT p.id AS poliza_id, 
       SUM(m.debe) AS total_debe, 
       SUM(m.haber) AS total_haber, 
       pl.id AS plantilla_id, 
       pl.nombre AS plantilla_nombre
FROM core_poliza p
LEFT JOIN core_movimientopoliza m ON p.id = m.poliza_id
LEFT JOIN core_plantillapoliza pl ON p.plantilla_usada_id = pl.id
GROUP BY p.id, pl.id, pl.nombre
HAVING ABS(SUM(m.debe) - SUM(m.haber)) > 0.1
ORDER BY ABS(SUM(m.debe) - SUM(m.haber)) DESC;
"""

def main():
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ejecutar la consulta
    cursor.execute(query)
    results = cursor.fetchall()

    # Mostrar los resultados
    print("Pólizas desbalanceadas y sus plantillas asociadas:")
    for row in results:
        print(f"Póliza ID: {row[0]}, Debe: {row[1]}, Haber: {row[2]}, Plantilla ID: {row[3]}, Plantilla Nombre: {row[4]}")

    # Cerrar la conexión
    conn.close()

if __name__ == "__main__":
    main()