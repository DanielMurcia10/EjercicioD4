#!/usr/bin/env python3
"""
Programa de Gestión de Tienda
=============================

Sistema de consola para administrar una tienda: inventario de productos,
registro de ventas (carrito) y reportes básicos. Los datos se guardan en
una base de datos SQLite (tienda.db) que se crea automáticamente en la
misma carpeta que este script, así que la información persiste entre
ejecuciones.

Cómo ejecutar:
    python3 tienda.py

Requisitos: solo Python 3 (sqlite3 viene incluido en la librería estándar).
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tienda.db")


# ---------------------------------------------------------------------------
# Capa de base de datos
# ---------------------------------------------------------------------------

def conectar():
    """Abre una conexión a la base de datos y asegura que las tablas existan."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    crear_tablas(conn)
    return conn


def crear_tablas(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            precio REAL NOT NULL CHECK (precio >= 0),
            stock INTEGER NOT NULL CHECK (stock >= 0)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            total REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detalle_venta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL REFERENCES ventas(id),
            producto_id INTEGER NOT NULL REFERENCES productos(id),
            producto_nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            subtotal REAL NOT NULL
        )
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Utilidades de entrada
# ---------------------------------------------------------------------------

def pedir_texto(mensaje):
    while True:
        valor = input(mensaje).strip()
        if valor:
            return valor
        print("  → Este campo no puede estar vacío.")


def pedir_float(mensaje, minimo=0):
    while True:
        valor = input(mensaje).strip().replace(",", ".")
        try:
            numero = float(valor)
            if numero < minimo:
                print(f"  → El valor debe ser mayor o igual a {minimo}.")
                continue
            return numero
        except ValueError:
            print("  → Ingresa un número válido.")


def pedir_entero(mensaje, minimo=0):
    while True:
        valor = input(mensaje).strip()
        try:
            numero = int(valor)
            if numero < minimo:
                print(f"  → El valor debe ser mayor o igual a {minimo}.")
                continue
            return numero
        except ValueError:
            print("  → Ingresa un número entero válido.")


def confirmar(mensaje):
    return input(mensaje).strip().lower() in ("s", "si", "sí", "y", "yes")


def formatear_dinero(valor):
    return f"${valor:,.2f}"


def pausar():
    input("\nPresiona Enter para continuar...")


# ---------------------------------------------------------------------------
# Inventario de productos
# ---------------------------------------------------------------------------

def agregar_producto(conn):
    print("\n--- Agregar nuevo producto ---")
    nombre = pedir_texto("Nombre del producto: ")
    existente = conn.execute(
        "SELECT id FROM productos WHERE nombre = ?", (nombre,)
    ).fetchone()
    if existente:
        print(f"  → Ya existe un producto llamado '{nombre}'. Usa la opción de editar stock/precio.")
        return
    precio = pedir_float("Precio unitario: ")
    stock = pedir_entero("Cantidad en stock: ")
    conn.execute(
        "INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)",
        (nombre, precio, stock),
    )
    conn.commit()
    print(f"  ✔ Producto '{nombre}' agregado correctamente.")


def listar_productos(conn, mostrar_encabezado=True):
    productos = conn.execute(
        "SELECT id, nombre, precio, stock FROM productos ORDER BY nombre"
    ).fetchall()
    if mostrar_encabezado:
        print("\n--- Inventario de productos ---")
    if not productos:
        print("  (No hay productos registrados todavía)")
        return productos

    print(f"{'ID':<4}{'Producto':<25}{'Precio':<15}{'Stock':<10}")
    print("-" * 54)
    for pid, nombre, precio, stock in productos:
        alerta = "  ⚠ bajo stock" if stock <= 5 else ""
        print(f"{pid:<4}{nombre:<25}{formatear_dinero(precio):<15}{stock:<10}{alerta}")
    return productos


def buscar_producto_por_id(conn, producto_id):
    return conn.execute(
        "SELECT id, nombre, precio, stock FROM productos WHERE id = ?",
        (producto_id,),
    ).fetchone()


def editar_producto(conn):
    print("\n--- Editar producto ---")
    productos = listar_productos(conn, mostrar_encabezado=False)
    if not productos:
        return
    pid = pedir_entero("\nID del producto a editar: ", minimo=1)
    producto = buscar_producto_por_id(conn, pid)
    if not producto:
        print("  → No existe un producto con ese ID.")
        return

    _, nombre_actual, precio_actual, stock_actual = producto
    print(f"Editando '{nombre_actual}' (precio actual: {formatear_dinero(precio_actual)}, stock actual: {stock_actual})")
    print("Deja el campo vacío para mantener el valor actual.")

    nuevo_precio = input(f"Nuevo precio [{precio_actual}]: ").strip().replace(",", ".")
    nuevo_stock = input(f"Nuevo stock [{stock_actual}]: ").strip()

    precio_final = precio_actual
    stock_final = stock_actual

    if nuevo_precio:
        try:
            precio_final = float(nuevo_precio)
        except ValueError:
            print("  → Precio inválido, se mantiene el valor anterior.")

    if nuevo_stock:
        try:
            stock_final = int(nuevo_stock)
        except ValueError:
            print("  → Stock inválido, se mantiene el valor anterior.")

    conn.execute(
        "UPDATE productos SET precio = ?, stock = ? WHERE id = ?",
        (precio_final, stock_final, pid),
    )
    conn.commit()
    print("  ✔ Producto actualizado.")


def eliminar_producto(conn):
    print("\n--- Eliminar producto ---")
    productos = listar_productos(conn, mostrar_encabezado=False)
    if not productos:
        return
    pid = pedir_entero("\nID del producto a eliminar: ", minimo=1)
    producto = buscar_producto_por_id(conn, pid)
    if not producto:
        print("  → No existe un producto con ese ID.")
        return
    if confirmar(f"¿Seguro que deseas eliminar '{producto[1]}'? (s/n): "):
        conn.execute("DELETE FROM productos WHERE id = ?", (pid,))
        conn.commit()
        print("  ✔ Producto eliminado.")
    else:
        print("  Operación cancelada.")


# ---------------------------------------------------------------------------
# Ventas (carrito de compra)
# ---------------------------------------------------------------------------

def registrar_venta(conn):
    print("\n--- Nueva venta ---")
    productos = listar_productos(conn, mostrar_encabezado=False)
    if not productos:
        print("  → No hay productos para vender. Agrega productos primero.")
        return

    carrito = []  # lista de dicts: producto_id, nombre, cantidad, precio_unitario
    while True:
        pid = pedir_entero("\nID del producto a vender (0 para terminar): ", minimo=0)
        if pid == 0:
            break

        producto = buscar_producto_por_id(conn, pid)
        if not producto:
            print("  → No existe un producto con ese ID.")
            continue

        _, nombre, precio, stock_disponible = producto

        # Considerar lo que ya está en el carrito para no exceder el stock real
        ya_en_carrito = sum(item["cantidad"] for item in carrito if item["producto_id"] == pid)
        disponible_real = stock_disponible - ya_en_carrito

        if disponible_real <= 0:
            print(f"  → No hay más stock disponible de '{nombre}'.")
            continue

        cantidad = pedir_entero(
            f"Cantidad de '{nombre}' (disponible: {disponible_real}): ", minimo=1
        )
        if cantidad > disponible_real:
            print(f"  → Solo hay {disponible_real} unidades disponibles.")
            continue

        carrito.append({
            "producto_id": pid,
            "nombre": nombre,
            "cantidad": cantidad,
            "precio_unitario": precio,
        })
        print(f"  ✔ Agregado: {cantidad} x {nombre} = {formatear_dinero(cantidad * precio)}")

    if not carrito:
        print("\n  Venta cancelada: el carrito está vacío.")
        return

    print("\n--- Resumen de la venta ---")
    total = 0
    for item in carrito:
        subtotal = item["cantidad"] * item["precio_unitario"]
        total += subtotal
        print(f"  {item['cantidad']} x {item['nombre']} = {formatear_dinero(subtotal)}")
    print(f"\n  TOTAL: {formatear_dinero(total)}")

    if not confirmar("\n¿Confirmar venta? (s/n): "):
        print("  Venta cancelada.")
        return

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.execute(
        "INSERT INTO ventas (fecha, total) VALUES (?, ?)", (fecha, total)
    )
    venta_id = cursor.lastrowid

    for item in carrito:
        subtotal = item["cantidad"] * item["precio_unitario"]
        conn.execute(
            """INSERT INTO detalle_venta
               (venta_id, producto_id, producto_nombre, cantidad, precio_unitario, subtotal)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (venta_id, item["producto_id"], item["nombre"], item["cantidad"],
             item["precio_unitario"], subtotal),
        )
        conn.execute(
            "UPDATE productos SET stock = stock - ? WHERE id = ?",
            (item["cantidad"], item["producto_id"]),
        )

    conn.commit()
    print(f"\n  ✔ Venta #{venta_id} registrada con éxito. Total: {formatear_dinero(total)}")


def historial_ventas(conn):
    print("\n--- Historial de ventas ---")
    ventas = conn.execute(
        "SELECT id, fecha, total FROM ventas ORDER BY id DESC"
    ).fetchall()
    if not ventas:
        print("  (No se han registrado ventas todavía)")
        return

    for vid, fecha, total in ventas:
        print(f"\nVenta #{vid} — {fecha} — Total: {formatear_dinero(total)}")
        detalles = conn.execute(
            "SELECT producto_nombre, cantidad, precio_unitario, subtotal FROM detalle_venta WHERE venta_id = ?",
            (vid,),
        ).fetchall()
        for nombre, cantidad, precio_unitario, subtotal in detalles:
            print(f"    - {cantidad} x {nombre} @ {formatear_dinero(precio_unitario)} = {formatear_dinero(subtotal)}")


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------

def reporte_general(conn):
    print("\n--- Reporte general ---")
    total_ventas, num_ventas = conn.execute(
        "SELECT COALESCE(SUM(total), 0), COUNT(*) FROM ventas"
    ).fetchone()
    print(f"  Número de ventas realizadas: {num_ventas}")
    print(f"  Ingresos totales: {formatear_dinero(total_ventas)}")

    valor_inventario = conn.execute(
        "SELECT COALESCE(SUM(precio * stock), 0) FROM productos"
    ).fetchone()[0]
    print(f"  Valor total del inventario actual: {formatear_dinero(valor_inventario)}")

    print("\n  Productos más vendidos:")
    top = conn.execute("""
        SELECT producto_nombre, SUM(cantidad) AS total_vendido
        FROM detalle_venta
        GROUP BY producto_nombre
        ORDER BY total_vendido DESC
        LIMIT 5
    """).fetchall()
    if not top:
        print("    (Aún no hay ventas registradas)")
    else:
        for nombre, cantidad in top:
            print(f"    - {nombre}: {cantidad} unidades vendidas")

    print("\n  Productos con bajo stock (5 o menos):")
    bajo_stock = conn.execute(
        "SELECT nombre, stock FROM productos WHERE stock <= 5 ORDER BY stock"
    ).fetchall()
    if not bajo_stock:
        print("    (Ningún producto con bajo stock)")
    else:
        for nombre, stock in bajo_stock:
            print(f"    - {nombre}: {stock} unidades")


# ---------------------------------------------------------------------------
# Menú principal
# ---------------------------------------------------------------------------

MENU = """
==============================
   SISTEMA DE GESTIÓN - TIENDA
==============================
1. Ver inventario
2. Agregar producto
3. Editar producto (precio/stock)
4. Eliminar producto
5. Registrar venta
6. Ver historial de ventas
7. Reporte general
0. Salir
==============================
"""


def main():
    conn = conectar()
    print("Bienvenido al sistema de gestión de tienda.")
    print(f"Base de datos: {DB_PATH}")

    acciones = {
        "1": lambda: listar_productos(conn),
        "2": lambda: agregar_producto(conn),
        "3": lambda: editar_producto(conn),
        "4": lambda: eliminar_producto(conn),
        "5": lambda: registrar_venta(conn),
        "6": lambda: historial_ventas(conn),
        "7": lambda: reporte_general(conn),
    }

    try:
        while True:
            print(MENU)
            opcion = input("Elige una opción: ").strip()

            if opcion == "0":
                print("\n¡Gracias por usar el sistema! Hasta pronto.")
                break

            accion = acciones.get(opcion)
            if accion:
                try:
                    accion()
                except sqlite3.Error as e:
                    print(f"  → Error de base de datos: {e}")
                pausar()
            else:
                print("  → Opción inválida, intenta de nuevo.")
    except KeyboardInterrupt:
        print("\n\nPrograma interrumpido. ¡Hasta pronto!")
    finally:
        conn.close()


if __name__ == "__main__":
    main()