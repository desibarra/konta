import sqlite3

# Ruta a la base de datos SQLite
db_path = "c:\\Users\\desib\\Documents\\app_Konta\\db.sqlite3"

# Consulta SQL para obtener las cuentas configuradas en la plantilla "Egreso - Gasto General"
query = """
SELECT pl.id AS plantilla_id, 
       pl.nombre AS plantilla_nombre, 
       cf.codigo AS cuenta_flujo, 
       cp.codigo AS cuenta_provision, 
       ci.codigo AS cuenta_impuesto
FROM core_plantillapoliza pl
LEFT JOIN core_cuentacontable cf ON pl.cuenta_flujo_id = cf.id
LEFT JOIN core_cuentacontable cp ON pl.cuenta_provision_id = cp.id
LEFT JOIN core_cuentacontable ci ON pl.cuenta_impuesto_id = ci.id
WHERE pl.id = 9;
"""

def main():
    # Conectar a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ejecutar la consulta
    cursor.execute(query)
    results = cursor.fetchall()

    # Mostrar los resultados
    print("Cuentas configuradas en la plantilla 'Egreso - Gasto General':")
    for row in results:
        print(f"Plantilla ID: {row[0]}, Nombre: {row[1]}, Cuenta Flujo: {row[2]}, Cuenta Provisión: {row[3]}, Cuenta Impuesto: {row[4]}")

    # Cerrar la conexión
    conn.close()

if __name__ == "__main__":
    main()