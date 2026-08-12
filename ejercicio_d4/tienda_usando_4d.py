#!/usr/bin/env python3
"""
TIENDA COMPLETA — Sistema de Gestión de Tienda en Línea (versión de un solo archivo)
======================================================================================

Este archivo contiene TODO el proyecto que armamos por partes (base de
datos, excepciones, modelos, catálogo, carrito, checkout, pedidos y el menú
de consola), unido en un solo lugar para poder copiarlo y pegarlo de un
jalón en VSCode.

El archivo sigue dividido internamente en las mismas "capas" que antes,
ahora como SECCIONES separadas por comentarios en forma de banner. El orden
importa: cada sección solo puede usar lo que ya se definió en las secciones
anteriores (por ejemplo, la sección de CARRITO usa las excepciones y los
modelos definidos arriba, y el MENÚ DE CONSOLA al final usa todo lo demás).

    SECCIÓN 1: Conexión y esquema de la base de datos (antes: db.py)
    SECCIÓN 2: Excepciones propias de la tienda        (antes: excepciones.py)
    SECCIÓN 3: Estructuras de datos (dataclasses)       (antes: modelos.py)
    SECCIÓN 4: Catálogo e inventario                    (antes: productos.py)
    SECCIÓN 5: Carrito de compras                        (antes: carrito.py)
    SECCIÓN 6: Checkout (confirmar pedido)               (antes: checkout.py)
    SECCIÓN 7: Historial y reportes                      (antes: pedidos.py)
    SECCIÓN 8: Menú de consola (presentación)            (antes: tienda.py)

Cómo ejecutar:
    python3 tienda-completa.py

Nota para quien siga trabajando en este archivo: si el proyecto sigue
creciendo, probablemente convenga volver a separarlo en varios archivos
como estaba antes -- un solo archivo se vuelve incómodo de navegar pasadas
las mil líneas. Por ahora, para el tamaño actual, tenerlo junto es
perfectamente manejable.
"""

# --- Importaciones de la librería estándar de Python (no requieren instalar nada) ---
import os                            # Para construir la ruta del archivo de base de datos.
import sqlite3                       # Motor de base de datos que usa este proyecto.
from datetime import datetime        # Para registrar fechas/horas (carrito, pedidos).
from dataclasses import dataclass, field   # Para las estructuras de datos de la Sección 3.


# ===========================================================================
# SECCIÓN 1 — Conexión y esquema de la base de datos
# ===========================================================================
# Idea de diseño: estas dos funciones son las únicas que conocen el nombre
# del archivo .db y el texto de las sentencias CREATE TABLE. El resto del
# programa recibe una conexión ya abierta y nunca necesita saber cómo se
# creó, lo que facilitaría cambiar de motor de base de datos más adelante.

# Ruta absoluta al archivo tienda.db, en la misma carpeta que este script.
# Se usa una ruta absoluta para que el archivo se cree siempre en el mismo
# lugar, sin importar desde qué carpeta se ejecute el programa.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tienda.db")


def conectar():
    """
    Abre la base de datos SQLite (creándola si todavía no existe) y devuelve
    una conexión lista para usarse, con todas las tablas ya creadas.
    """
    conn = sqlite3.connect(DB_PATH)            # Abre el archivo .db; si no existe, SQLite lo crea vacío automáticamente.
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite trae las llaves foráneas apagadas por defecto; esto las activa.
    crear_tablas(conn)                         # Se asegura de que las tablas existan antes de devolver la conexión.
    return conn                                # El resto del programa usa esta conexión para leer y escribir datos.


def crear_tablas(conn):
    """
    Crea todas las tablas del proyecto si aún no existen.

    Usar "CREATE TABLE IF NOT EXISTS" permite llamar esta función cada vez
    que el programa inicia, sin riesgo de borrar los datos que ya estaban
    guardados de ejecuciones anteriores.
    """

    # --- Tabla "productos": el catálogo de la tienda ---
    # Cada fila representa un producto que se puede comprar.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,     -- identificador único, lo genera SQLite solo
            nombre TEXT NOT NULL UNIQUE,              -- no se permiten dos productos con el mismo nombre
            precio REAL NOT NULL CHECK (precio >= 0), -- el precio nunca puede quedar en negativo
            stock INTEGER NOT NULL CHECK (stock >= 0) -- el stock nunca puede quedar en negativo
        )
    """)  # Ejecuta la sentencia SQL anterior contra la base de datos.

    # --- Tabla "carrito": productos elegidos pero todavía no comprados ---
    # Es una tabla "temporal": se llena mientras el cliente decide qué llevar,
    # y se vacía por completo en cuanto se confirma un checkout.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS carrito (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL REFERENCES productos(id), -- a qué producto corresponde esta línea
            cantidad INTEGER NOT NULL CHECK (cantidad > 0),         -- cuántas unidades quiere el cliente
            precio_unitario REAL NOT NULL,                         -- precio "congelado" al momento de agregarlo
            agregado_en TEXT NOT NULL                              -- fecha/hora en que se agregó (sirve para ordenar)
        )
    """)

    # --- Tabla "pedidos": el encabezado de una compra ya confirmada ---
    # Un pedido nace con estado "pendiente" y en el futuro podría avanzar a
    # "enviado", "entregado", "cancelado", etc.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,                      -- fecha/hora en que se confirmó el pedido
            cliente_nombre TEXT NOT NULL,              -- nombre de quien compra
            direccion_envio TEXT NOT NULL,             -- a dónde se debe enviar
            subtotal REAL NOT NULL,                    -- suma de todas las líneas, sin envío
            costo_envio REAL NOT NULL,                 -- costo de envío aplicado a este pedido
            total REAL NOT NULL,                       -- subtotal + costo_envio
            estado TEXT NOT NULL DEFAULT 'pendiente'   -- ciclo de vida del pedido
        )
    """)

    # --- Tabla "detalle_pedido": las líneas de producto de cada pedido ---
    # Guardamos el nombre y el precio "congelados" en el momento de la compra,
    # para que un pedido antiguo se siga viendo igual aunque después se
    # renombre el producto o le cambien el precio en el catálogo.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detalle_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id),     -- a qué pedido pertenece esta línea
            producto_id INTEGER NOT NULL REFERENCES productos(id),-- qué producto se compró
            producto_nombre TEXT NOT NULL,                         -- nombre del producto al momento de comprar
            cantidad INTEGER NOT NULL,                             -- cuántas unidades se compraron
            precio_unitario REAL NOT NULL,                         -- precio unitario al momento de comprar
            subtotal REAL NOT NULL                                 -- cantidad * precio_unitario, ya calculado
        )
    """)

    conn.commit()  # Guarda los cambios (la creación de las tablas) de forma permanente en el archivo .db.


# ===========================================================================
# SECCIÓN 2 — Excepciones propias de la tienda
# ===========================================================================
# ¿Por qué crear excepciones propias en vez de usar simplemente `print()` o
# `return None` cuando algo falla? Porque así la capa de lógica (catálogo,
# carrito, checkout) puede señalar CADA problema con su propio tipo de
# error, y la capa de presentación (el menú, al final de este archivo)
# decide cómo mostrárselo al usuario sin tener que adivinar qué significó
# un mensaje genérico. Además, "except ErrorTienda" en un solo lugar
# permite atrapar cualquier error de negocio sin enumerar cada uno.

class ErrorTienda(Exception):
    """Clase base: todas las excepciones propias de la tienda heredan de aquí."""
    # No necesita código propio: su único propósito es servir como "categoría"
    # común para que el resto de excepciones puedan agruparse bajo un solo except.


class ProductoNoExisteError(ErrorTienda):
    """Se lanza cuando se referencia un producto que no existe en el catálogo."""

    def __init__(self, producto_id: int):
        self.producto_id = producto_id   # Guarda el ID que causó el error, útil para depurar después.
        super().__init__(f"El producto con ID {producto_id} no existe.")


class StockInsuficienteError(ErrorTienda):
    """Se lanza cuando se pide más cantidad de un producto de la que hay disponible."""

    def __init__(self, producto_nombre: str, disponible: int, solicitado: int):
        self.producto_nombre = producto_nombre   # Nombre del producto afectado.
        self.disponible = disponible             # Cuánto stock hay realmente.
        self.solicitado = solicitado             # Cuánto se intentó pedir/comprar.
        super().__init__(
            f"Stock insuficiente de '{producto_nombre}': "
            f"disponible {disponible}, solicitado {solicitado}."
        )


class ItemNoEnCarritoError(ErrorTienda):
    """Se lanza al intentar quitar o actualizar un producto que no está en el carrito."""

    def __init__(self, producto_id: int):
        self.producto_id = producto_id
        super().__init__(f"El producto con ID {producto_id} no está en el carrito.")


class CarritoVacioError(ErrorTienda):
    """Se lanza al intentar hacer checkout con el carrito vacío."""

    def __init__(self):
        super().__init__("El carrito está vacío, no se puede procesar el checkout.")


class DatosClienteInvalidosError(ErrorTienda):
    """Se lanza cuando faltan datos obligatorios del cliente en el checkout."""
    # Reutiliza el constructor de Exception tal cual (el mensaje se pasa donde se lanza,
    # por ejemplo: raise DatosClienteInvalidosError("falta el nombre")).


class NombreDuplicadoError(ErrorTienda):
    """Se lanza al intentar crear un producto con un nombre que ya existe."""

    def __init__(self, nombre: str):
        self.nombre = nombre
        super().__init__(f"Ya existe un producto llamado '{nombre}'.")


# ===========================================================================
# SECCIÓN 3 — Estructuras de datos (dataclasses)
# ===========================================================================
# En vez de pasar tuplas sueltas como (1, "Camisa", 3, 15.0) entre funciones
# -- donde es fácil confundir el orden de los campos --, se usan dataclasses.
# Una dataclass es una clase de Python pensada solo para guardar datos: se
# declaran sus campos con nombre y tipo, y Python genera automáticamente el
# constructor (__init__) y una forma legible de imprimirla (__repr__).

@dataclass
class Producto:
    """Representa una fila de la tabla 'productos' (el catálogo de la tienda)."""

    id: int             # Identificador único en la base de datos.
    nombre: str          # Nombre visible del producto.
    precio: float         # Precio unitario actual.
    stock: int             # Unidades disponibles actualmente en inventario.


@dataclass
class ItemCarrito:
    """Representa un producto dentro del carrito, con la cantidad elegida."""

    producto_id: int        # ID del producto en la tabla "productos".
    nombre: str              # Nombre del producto (copiado para no tener que consultarlo de nuevo).
    cantidad: int             # Cuántas unidades quiere el cliente.
    precio_unitario: float    # Precio de una sola unidad, congelado al momento de agregarlo al carrito.

    @property
    def subtotal(self) -> float:
        # 'property' permite llamar item.subtotal como si fuera un campo normal,
        # aunque en realidad se calcula cada vez que se pide (nunca queda desactualizado).
        return round(self.cantidad * self.precio_unitario, 2)   # round(...) evita errores de centavos por decimales binarios.


@dataclass
class ResumenCarrito:
    """El contenido completo del carrito, listo para mostrarse o para el checkout."""

    items: list = field(default_factory=list)   # Lista de ItemCarrito. default_factory=list evita compartir la misma lista entre instancias.

    @property
    def total(self) -> float:
        # Suma el subtotal de cada ítem del carrito para obtener el total general.
        return round(sum(item.subtotal for item in self.items), 2)

    @property
    def esta_vacio(self) -> bool:
        # Forma legible de preguntar "¿el carrito no tiene productos?" en el resto del código.
        return len(self.items) == 0


@dataclass
class LineaPedido:
    """Una línea de detalle dentro de un pedido ya confirmado (equivalente a ItemCarrito, pero para un pedido)."""

    producto_id: int
    nombre: str
    cantidad: int
    precio_unitario: float
    subtotal: float   # Aquí SÍ se guarda como campo (no como property), porque en un pedido ya confirmado
                       # queremos que quede fijo en la base de datos, sin depender de un cálculo posterior.


@dataclass
class Recibo:
    """Resultado de un checkout exitoso: todo lo necesario para mostrárselo al cliente."""

    pedido_id: int          # Número de pedido asignado por la base de datos.
    fecha: str               # Fecha y hora en que se confirmó la compra.
    cliente_nombre: str       # Nombre de quien compró.
    direccion_envio: str      # A dónde se enviará el pedido.
    lineas: list              # Lista de LineaPedido con el detalle de productos comprados.
    subtotal: float           # Suma de las líneas, sin envío.
    costo_envio: float        # Costo de envío aplicado.
    total: float               # subtotal + costo_envio.
    estado: str                 # Estado inicial del pedido (por ejemplo, "pendiente").


# ===========================================================================
# SECCIÓN 4 — Catálogo e inventario
# ===========================================================================
# Agrupa todo lo relacionado con la tabla "productos": listar el catálogo,
# buscar, agregar productos nuevos, editar precio/stock y eliminar
# productos. Estas funciones no imprimen nada: reciben una conexión y
# devuelven datos u objetos; quien las llama decide cómo mostrarlos.

def listar_productos(conn: sqlite3.Connection):
    """Devuelve todos los productos del catálogo, ordenados alfabéticamente."""
    filas = conn.execute(
        "SELECT id, nombre, precio, stock FROM productos ORDER BY nombre"
    ).fetchall()   # fetchall trae todas las filas de una sola vez; el catálogo de una tienda pequeña no es tan grande como para preocuparse por paginar aquí.

    # Convierte cada tupla cruda de la base de datos en un objeto Producto,
    # para que el resto del programa trabaje con nombres de campo, no con índices [0], [1], [2]...
    return [Producto(id=pid, nombre=nombre, precio=precio, stock=stock) for pid, nombre, precio, stock in filas]


def buscar_por_nombre(conn: sqlite3.Connection, texto: str):
    """
    Busca productos cuyo nombre contenga 'texto' (sin importar mayúsculas/minúsculas).
    Útil para la búsqueda del catálogo desde el punto de vista de un cliente.
    """
    patron = f"%{texto.strip()}%"   # Los símbolos % le dicen a SQL "cualquier cosa antes/después de este texto".
    filas = conn.execute(
        "SELECT id, nombre, precio, stock FROM productos WHERE nombre LIKE ? COLLATE NOCASE ORDER BY nombre",
        (patron,),   # COLLATE NOCASE hace que la comparación ignore mayúsculas/minúsculas directamente en SQLite.
    ).fetchall()
    return [Producto(id=pid, nombre=nombre, precio=precio, stock=stock) for pid, nombre, precio, stock in filas]


def obtener_producto(conn: sqlite3.Connection, producto_id: int):
    """Devuelve un Producto por su ID, o None si no existe."""
    fila = conn.execute(
        "SELECT id, nombre, precio, stock FROM productos WHERE id = ?",
        (producto_id,),
    ).fetchone()
    if fila is None:
        return None   # Se devuelve None (en vez de lanzar una excepción) porque aquí "no existe" es una respuesta válida, no un error.
    pid, nombre, precio, stock = fila
    return Producto(id=pid, nombre=nombre, precio=precio, stock=stock)


def agregar_producto(conn: sqlite3.Connection, nombre: str, precio: float, stock: int) -> int:
    """
    Agrega un producto nuevo al catálogo y devuelve el ID que se le asignó.

    Lanza:
        ValueError: si el nombre está vacío, o si precio/stock son negativos.
        NombreDuplicadoError: si ya existe un producto con ese nombre.
    """
    nombre = nombre.strip()   # Quita espacios sobrantes antes de validar y guardar.
    if not nombre:
        raise ValueError("El nombre del producto no puede estar vacío.")
    if precio < 0:
        raise ValueError("El precio no puede ser negativo.")
    if stock < 0:
        raise ValueError("El stock no puede ser negativo.")

    existente = conn.execute(
        "SELECT id FROM productos WHERE nombre = ? COLLATE NOCASE", (nombre,)
    ).fetchone()   # Revisa duplicados ignorando mayúsculas/minúsculas ("Camisa" y "camisa" cuentan como el mismo nombre).
    if existente:
        raise NombreDuplicadoError(nombre)

    cursor = conn.execute(
        "INSERT INTO productos (nombre, precio, stock) VALUES (?, ?, ?)",
        (nombre, precio, stock),
    )
    conn.commit()
    return cursor.lastrowid   # Devuelve el ID recién generado, útil para confirmarle al usuario "producto #7 creado".


def editar_producto(conn: sqlite3.Connection, producto_id: int, precio: float = None, stock: int = None) -> None:
    """
    Actualiza el precio y/o el stock de un producto existente.

    Los parámetros `precio` y `stock` son opcionales (valor None = "no cambiar
    este campo"), para poder actualizar solo uno de los dos sin tener que
    volver a mandar el valor que ya tenía.

    Lanza:
        ProductoNoExisteError: si el producto no existe.
        ValueError: si se manda un precio o stock negativo.
    """
    producto = obtener_producto(conn, producto_id)
    if producto is None:
        raise ProductoNoExisteError(producto_id)

    precio_final = producto.precio if precio is None else precio   # Si no se especifica precio nuevo, se conserva el actual.
    stock_final = producto.stock if stock is None else stock

    if precio_final < 0:
        raise ValueError("El precio no puede ser negativo.")
    if stock_final < 0:
        raise ValueError("El stock no puede ser negativo.")

    conn.execute(
        "UPDATE productos SET precio = ?, stock = ? WHERE id = ?",
        (precio_final, stock_final, producto_id),
    )
    conn.commit()


def eliminar_producto(conn: sqlite3.Connection, producto_id: int) -> None:
    """
    Elimina un producto del catálogo.

    Lanza:
        ProductoNoExisteError: si el producto no existe.
    """
    producto = obtener_producto(conn, producto_id)
    if producto is None:
        raise ProductoNoExisteError(producto_id)

    conn.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()


# ===========================================================================
# SECCIÓN 5 — Carrito de compras
# ===========================================================================
# Estas funciones validan reglas de negocio (que el producto exista, que
# haya stock suficiente, que la cantidad tenga sentido) y usan la base de
# datos como almacenamiento del carrito. A propósito NO imprimen nada ni le
# preguntan nada al usuario -- eso es responsabilidad del menú, al final de
# este archivo.

def _obtener_producto_crudo(conn: sqlite3.Connection, producto_id: int):
    """
    Función 'privada' (el guion bajo al inicio es una convención de Python
    para decir "esto es un detalle interno"). Devuelve (id, nombre, precio,
    stock) como tupla cruda -- se usa aquí en vez de obtener_producto() para
    evitar armar un objeto Producto completo solo para leer un par de campos.
    """
    return conn.execute(
        "SELECT id, nombre, precio, stock FROM productos WHERE id = ?",  # El "?" evita inyección SQL: nunca se concatena el valor directamente en el texto.
        (producto_id,),   # SQLite exige que los parámetros vayan en una tupla, incluso si es un solo valor.
    ).fetchone()   # fetchone() devuelve una sola fila (o None si no hay ninguna), ideal cuando se busca por ID único.


def _obtener_fila_carrito(conn: sqlite3.Connection, producto_id: int):
    """Devuelve (id, cantidad) de la fila del carrito para ese producto, o None si no está en el carrito."""
    return conn.execute(
        "SELECT id, cantidad FROM carrito WHERE producto_id = ?",
        (producto_id,),
    ).fetchone()


def agregar_al_carrito(conn: sqlite3.Connection, producto_id: int, cantidad: int = 1) -> None:
    """
    Agrega 'cantidad' unidades de un producto al carrito.

    Si el producto YA estaba en el carrito, ACUMULA la cantidad nueva sobre
    la que ya había, en vez de crear una fila duplicada. Por ejemplo: si ya
    hay 2 unidades de "Camisa" en el carrito y se vuelve a agregar 1, el
    carrito queda con 3 unidades de "Camisa" en una sola fila (no con dos
    filas separadas de 2 y 1).

    Lanza:
        ValueError: si `cantidad` no es un entero positivo.
        ProductoNoExisteError: si el producto no existe en el catálogo.
        StockInsuficienteError: si no hay stock suficiente para la cantidad total.
    """
    if cantidad <= 0:
        # Validación de entrada: nunca debería llegar aquí una cantidad de 0 o negativa,
        # así que se lanza un error inmediatamente en vez de dejar que ensucie el carrito.
        raise ValueError("La cantidad a agregar debe ser mayor a cero.")

    producto = _obtener_producto_crudo(conn, producto_id)   # Busca el producto una sola vez y reutiliza el resultado.
    if producto is None:
        raise ProductoNoExisteError(producto_id)       # Si no existe, no tiene sentido seguir: se corta aquí.
    _, nombre, precio, stock = producto                 # Desempaqueta la tupla; el "_" descarta el id (ya lo tenemos en producto_id).

    fila_carrito = _obtener_fila_carrito(conn, producto_id)             # ¿Ya había algo de este producto en el carrito?
    cantidad_previa = fila_carrito[1] if fila_carrito else 0            # Si no había fila, la cantidad previa es 0.
    cantidad_final = cantidad_previa + cantidad                          # La cantidad total que quedaría después de agregar.

    if cantidad_final > stock:
        # Se valida contra el TOTAL que quedaría en el carrito, no solo contra la cantidad nueva,
        # para no permitir que dos "agregar" pequeños terminen superando el stock real.
        raise StockInsuficienteError(nombre, disponible=stock, solicitado=cantidad_final)

    if fila_carrito:
        # Ya existía una fila para este producto: se actualiza la cantidad en el mismo registro.
        conn.execute(
            "UPDATE carrito SET cantidad = ? WHERE id = ?",
            (cantidad_final, fila_carrito[0]),   # fila_carrito[0] es el id de esa fila del carrito.
        )
    else:
        # No existía: se inserta una fila nueva, guardando el precio actual como "precio congelado".
        conn.execute(
            "INSERT INTO carrito (producto_id, cantidad, precio_unitario, agregado_en) "
            "VALUES (?, ?, ?, ?)",
            (producto_id, cantidad, precio, datetime.now().isoformat()),  # isoformat() da un texto ordenable como "2026-08-12T18:00:00".
        )
    conn.commit()   # Guarda el cambio de forma permanente; sin este commit, el cambio se perdería al cerrar la conexión.


def quitar_del_carrito(conn: sqlite3.Connection, producto_id: int) -> None:
    """
    Elimina por completo un producto del carrito, sin importar cuántas
    unidades tuviera.

    Lanza:
        ItemNoEnCarritoError: si el producto no está en el carrito.
    """
    fila_carrito = _obtener_fila_carrito(conn, producto_id)   # Verifica primero que exista, para dar un error claro si no.
    if fila_carrito is None:
        raise ItemNoEnCarritoError(producto_id)

    conn.execute("DELETE FROM carrito WHERE producto_id = ?", (producto_id,))   # Borra la fila correspondiente.
    conn.commit()   # Hace permanente la eliminación.


def actualizar_cantidad(conn: sqlite3.Connection, producto_id: int, nueva_cantidad: int) -> None:
    """
    Cambia la cantidad de un producto ya presente en el carrito a un valor
    EXACTO (a diferencia de `agregar_al_carrito`, que SUMA). Útil para un
    flujo de "editar carrito" donde el cliente escribe directamente cuántas
    unidades quiere en total.

    Si `nueva_cantidad` es 0, el producto se elimina del carrito.

    Lanza:
        ValueError: si `nueva_cantidad` es negativa.
        ItemNoEnCarritoError: si el producto no está en el carrito.
        ProductoNoExisteError: si el producto ya no existe en el catálogo.
        StockInsuficienteError: si `nueva_cantidad` excede el stock disponible.
    """
    if nueva_cantidad < 0:
        raise ValueError("La cantidad no puede ser negativa.")

    fila_carrito = _obtener_fila_carrito(conn, producto_id)
    if fila_carrito is None:
        raise ItemNoEnCarritoError(producto_id)

    if nueva_cantidad == 0:
        # Fijar la cantidad en 0 es, en la práctica, lo mismo que quitar el producto.
        # Se reutiliza la función existente en vez de duplicar el DELETE aquí.
        quitar_del_carrito(conn, producto_id)
        return   # 'return' sin valor: esta función no devuelve nada, solo se sale para no seguir ejecutando el resto.

    producto = _obtener_producto_crudo(conn, producto_id)
    if producto is None:
        raise ProductoNoExisteError(producto_id)
    _, nombre, _, stock = producto   # Aquí no necesitamos el precio, por eso también se descarta con "_".

    if nueva_cantidad > stock:
        raise StockInsuficienteError(nombre, disponible=stock, solicitado=nueva_cantidad)

    conn.execute(
        "UPDATE carrito SET cantidad = ? WHERE id = ?",
        (nueva_cantidad, fila_carrito[0]),
    )
    conn.commit()


def vaciar_carrito(conn: sqlite3.Connection) -> None:
    """Elimina todos los productos del carrito (por ejemplo, si el cliente cancela la compra)."""
    conn.execute("DELETE FROM carrito")   # Sin condición WHERE: borra todas las filas de la tabla carrito.
    conn.commit()


def ver_carrito(conn: sqlite3.Connection) -> ResumenCarrito:
    """
    Devuelve el contenido actual del carrito, con subtotales por línea y el
    total general, listo para mostrarse o para pasar al checkout.
    """
    # Se usa un solo JOIN para traer, en una sola consulta, tanto los datos del
    # carrito (cantidad, precio congelado) como el nombre actual del producto,
    # en vez de hacer una consulta separada por cada fila del carrito.
    filas = conn.execute(
        """SELECT p.id, p.nombre, c.cantidad, c.precio_unitario
           FROM carrito c
           JOIN productos p ON p.id = c.producto_id
           ORDER BY c.agregado_en"""    # Se ordena por fecha de agregado, para que el carrito se vea en el mismo orden en que se armó.
    ).fetchall()   # fetchall() trae todas las filas de una vez como una lista.

    # 'list comprehension': por cada fila (pid, nombre, cantidad, precio) crea un ItemCarrito.
    # Es equivalente a un bucle for que hace .append(...) en cada vuelta, pero más compacto.
    items = [
        ItemCarrito(producto_id=pid, nombre=nombre, cantidad=cantidad, precio_unitario=precio)
        for pid, nombre, cantidad, precio in filas
    ]
    return ResumenCarrito(items=items)   # Empaqueta la lista de ítems en la estructura que espera el resto del programa.


# ===========================================================================
# SECCIÓN 6 — Checkout (confirmar pedido)
# ===========================================================================
# Al confirmar el checkout, en este orden:
#     1. Se validan los datos del cliente (nombre y dirección).
#     2. Se valida que el carrito no esté vacío.
#     3. Se vuelve a revisar el stock de cada producto -- puede haber cambiado
#        desde que se agregó al carrito.
#     4. Se crea el pedido y sus líneas de detalle.
#     5. Se descuenta del inventario el stock vendido.
#     6. Se vacía el carrito.
#
# Nota sobre rendimiento: los pasos 3, 4 y 5 tocan varios productos a la vez
# (uno por cada línea del carrito). En vez de hacer una consulta a la base
# de datos POR CADA producto dentro de un bucle -- lo cual sería lento si el
# carrito tuviera muchos productos distintos, porque cada consulta implica
# un viaje de ida y vuelta a la base de datos --, se usa una sola consulta
# para revisar el stock de todos a la vez, y `executemany` para insertar o
# actualizar todas las filas de una sola vez.

ESTADO_INICIAL_PEDIDO = "pendiente"   # Constante: así, si el estado inicial cambia algún día, se edita en un solo lugar.


def _revalidar_stock(conn: sqlite3.Connection, resumen: ResumenCarrito) -> None:
    """
    Verifica que el stock actual siga alcanzando para cada ítem del carrito.

    Optimización: en vez de un bucle que hace una consulta SELECT por cada
    producto (el problema conocido como "N+1 consultas"), se hace UNA sola
    consulta que trae el stock de TODOS los productos del carrito de una
    vez, usando "WHERE id IN (...)". Luego la comparación se hace en
    memoria con un diccionario, que es prácticamente instantánea.
    """
    if not resumen.items:
        return   # Carrito vacío: no hay nada que revalidar (este caso ya se filtra antes, pero es una guarda extra segura).

    # Lista de todos los IDs de producto presentes en el carrito.
    ids_productos = [item.producto_id for item in resumen.items]

    # Genera dinámicamente "?,?,?" con un signo de interrogación por cada ID,
    # que es la forma correcta y segura de armar un IN (...) con parámetros en sqlite3.
    placeholders = ",".join("?" for _ in ids_productos)

    # UNA sola consulta a la base de datos para traer el stock de todos los productos del carrito.
    filas = conn.execute(
        f"SELECT id, stock FROM productos WHERE id IN ({placeholders})",
        ids_productos,
    ).fetchall()

    # Convierte la lista de filas [(id, stock), ...] en un diccionario {id: stock, ...}
    # para poder consultar el stock de un producto en tiempo constante (sin recorrer la lista).
    stock_por_producto = {producto_id: stock for producto_id, stock in filas}

    for item in resumen.items:
        # Este bucle YA NO toca la base de datos en cada vuelta: solo lee del diccionario en memoria.
        stock_actual = stock_por_producto.get(item.producto_id, 0)   # 0 si el producto ya no existe en el catálogo.
        if stock_actual < item.cantidad:
            raise StockInsuficienteError(item.nombre, disponible=stock_actual, solicitado=item.cantidad)


def procesar_checkout(
    conn: sqlite3.Connection,
    cliente_nombre: str,
    direccion_envio: str,
    costo_envio: float = 0.0,
) -> Recibo:
    """
    Confirma el carrito actual como un pedido nuevo y descuenta inventario.

    Devuelve un `Recibo` con todo lo necesario para mostrárselo al cliente
    (número de pedido, líneas compradas, totales, estado inicial).

    Lanza:
        DatosClienteInvalidosError: si falta el nombre o la dirección.
        ValueError: si `costo_envio` es negativo.
        CarritoVacioError: si no hay nada que comprar.
        StockInsuficienteError: si algún producto ya no tiene stock suficiente.
    """
    # --- Validaciones de entrada, antes de tocar la base de datos ---
    if not cliente_nombre or not cliente_nombre.strip():
        # "not cliente_nombre" cubre None o cadena vacía; ".strip()" cubre cadenas de solo espacios.
        raise DatosClienteInvalidosError("El nombre del cliente es obligatorio.")
    if not direccion_envio or not direccion_envio.strip():
        raise DatosClienteInvalidosError("La dirección de envío es obligatoria.")
    if costo_envio < 0:
        raise ValueError("El costo de envío no puede ser negativo.")

    resumen = ver_carrito(conn)         # Trae el contenido actual del carrito (una sola consulta con JOIN).
    if resumen.esta_vacio:
        raise CarritoVacioError()        # No tiene sentido seguir si no hay nada que comprar.

    _revalidar_stock(conn, resumen)      # Segunda verificación de stock, ya optimizada (ver función arriba).

    subtotal = resumen.total                          # Suma de todas las líneas, sin envío.
    total = round(subtotal + costo_envio, 2)           # Total final que pagará el cliente.
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # Fecha/hora legible para guardar en el pedido.

    # Inserta el "encabezado" del pedido y recupera el ID que SQLite le asignó automáticamente.
    cursor = conn.execute(
        """INSERT INTO pedidos
               (fecha, cliente_nombre, direccion_envio, subtotal, costo_envio, total, estado)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            fecha,
            cliente_nombre.strip(),      # .strip() quita espacios sobrantes al inicio/final antes de guardar.
            direccion_envio.strip(),
            subtotal,
            costo_envio,
            total,
            ESTADO_INICIAL_PEDIDO,
        ),
    )
    pedido_id = cursor.lastrowid   # 'lastrowid' es el ID autoincremental que acaba de generar el INSERT anterior.

    # --- Preparar en memoria TODAS las filas de detalle y TODAS las actualizaciones de stock ---
    # En vez de ejecutar un INSERT y un UPDATE por cada producto dentro del bucle (dos consultas
    # por producto), se acumulan las tuplas aquí y se envían todas juntas al final con executemany,
    # que es mucho más eficiente cuando el carrito tiene varios productos distintos.
    filas_detalle = []            # Aquí se acumulan las tuplas para la tabla detalle_pedido.
    actualizaciones_stock = []    # Aquí se acumulan las tuplas para descontar stock en productos.
    lineas = []                   # Aquí se acumulan los objetos LineaPedido que irán en el Recibo.

    for item in resumen.items:
        # Cada tupla debe respetar el mismo orden de columnas que el INSERT que se usará más abajo.
        filas_detalle.append((
            pedido_id,
            item.producto_id,
            item.nombre,
            item.cantidad,
            item.precio_unitario,
            item.subtotal,
        ))
        # Cada tupla respeta el orden de "SET stock = stock - ? WHERE id = ?": primero la cantidad, luego el id.
        actualizaciones_stock.append((item.cantidad, item.producto_id))

        # Se construye ya aquí el objeto que se mostrará en el recibo final, para no recorrer la lista dos veces.
        lineas.append(
            LineaPedido(
                producto_id=item.producto_id,
                nombre=item.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                subtotal=item.subtotal,
            )
        )

    # executemany ejecuta la misma sentencia SQL una vez por cada tupla de la lista,
    # pero en un solo viaje "de lote" hacia la base de datos, en vez de N viajes separados.
    conn.executemany(
        """INSERT INTO detalle_pedido
               (pedido_id, producto_id, producto_nombre, cantidad, precio_unitario, subtotal)
           VALUES (?, ?, ?, ?, ?, ?)""",
        filas_detalle,
    )
    conn.executemany(
        "UPDATE productos SET stock = stock - ? WHERE id = ?",
        actualizaciones_stock,
    )

    vaciar_carrito(conn)   # El carrito ya se convirtió en pedido: se limpia para la próxima compra.
    conn.commit()          # Guarda TODOS los cambios de este checkout de forma permanente y a la vez.

    # Devuelve el recibo armado, que la capa de presentación usará para mostrarle
    # el resultado al cliente sin tener que volver a consultar la base de datos.
    return Recibo(
        pedido_id=pedido_id,
        fecha=fecha,
        cliente_nombre=cliente_nombre.strip(),
        direccion_envio=direccion_envio.strip(),
        lineas=lineas,
        subtotal=subtotal,
        costo_envio=costo_envio,
        total=total,
        estado=ESTADO_INICIAL_PEDIDO,
    )


# ===========================================================================
# SECCIÓN 7 — Historial y reportes
# ===========================================================================
# Funciones de solo lectura: no modifican nada, solo consultan las tablas
# "pedidos", "detalle_pedido" y "productos" para armar la información que
# se muestra en el historial y en el reporte general.

UMBRAL_BAJO_STOCK = 5   # Constante: un producto se considera "bajo stock" si tiene esta cantidad o menos.


def listar_pedidos(conn: sqlite3.Connection):
    """
    Devuelve todos los pedidos confirmados, del más reciente al más antiguo,
    cada uno con su lista de líneas de detalle ya armada.
    """
    pedidos_filas = conn.execute(
        "SELECT id, fecha, cliente_nombre, direccion_envio, subtotal, costo_envio, total, estado "
        "FROM pedidos ORDER BY id DESC"    # DESC = del más nuevo al más viejo, que es como normalmente se quiere ver un historial.
    ).fetchall()

    if not pedidos_filas:
        return []   # Ninguna consulta adicional si no hay pedidos: se corta aquí para no hacer trabajo de más.

    # En vez de consultar el detalle pedido por pedido dentro de un bucle (N consultas),
    # se traen TODAS las líneas de detalle de una sola vez con un IN (...), igual que
    # se hizo en la Sección 6 para revalidar stock.
    ids_pedidos = [fila[0] for fila in pedidos_filas]
    placeholders = ",".join("?" for _ in ids_pedidos)
    detalle_filas = conn.execute(
        f"""SELECT pedido_id, producto_id, producto_nombre, cantidad, precio_unitario, subtotal
            FROM detalle_pedido
            WHERE pedido_id IN ({placeholders})
            ORDER BY id""",
        ids_pedidos,
    ).fetchall()

    # Agrupa las líneas de detalle por pedido_id en un diccionario, para poder
    # asignarle a cada pedido sus líneas sin volver a tocar la base de datos.
    lineas_por_pedido = {}
    for pedido_id, producto_id, nombre, cantidad, precio_unitario, subtotal in detalle_filas:
        linea = LineaPedido(
            producto_id=producto_id,
            nombre=nombre,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            subtotal=subtotal,
        )
        # setdefault crea la lista vacía la primera vez que se ve ese pedido_id, y la reutiliza después.
        lineas_por_pedido.setdefault(pedido_id, []).append(linea)

    pedidos_resultado = []
    for pid, fecha, cliente_nombre, direccion_envio, subtotal, costo_envio, total, estado in pedidos_filas:
        pedidos_resultado.append(
            Recibo(
                pedido_id=pid,
                fecha=fecha,
                cliente_nombre=cliente_nombre,
                direccion_envio=direccion_envio,
                lineas=lineas_por_pedido.get(pid, []),   # .get(...) con lista vacía por defecto, por si un pedido no tuviera líneas.
                subtotal=subtotal,
                costo_envio=costo_envio,
                total=total,
                estado=estado,
            )
        )
    return pedidos_resultado


def reporte_general(conn: sqlite3.Connection) -> dict:
    """
    Calcula un pequeño resumen del estado de la tienda: ingresos totales,
    valor del inventario, productos más vendidos y productos con bajo stock.

    Se devuelve un diccionario en vez de una dataclass porque este reporte
    es más flexible/variable que el resto de estructuras (podría crecer con
    más métricas sin necesidad de agregar una clase nueva cada vez).
    """
    # COALESCE(..., 0) evita que SUM() devuelva None cuando todavía no hay ningún pedido.
    total_ingresos, numero_pedidos = conn.execute(
        "SELECT COALESCE(SUM(total), 0), COUNT(*) FROM pedidos"
    ).fetchone()

    valor_inventario = conn.execute(
        "SELECT COALESCE(SUM(precio * stock), 0) FROM productos"
    ).fetchone()[0]

    top_productos = conn.execute("""
        SELECT producto_nombre, SUM(cantidad) AS total_vendido
        FROM detalle_pedido
        GROUP BY producto_nombre
        ORDER BY total_vendido DESC
        LIMIT 5
    """).fetchall()   # Trae directamente solo los 5 más vendidos calculados por SQLite; no hay que ordenar nada en Python.

    bajo_stock = conn.execute(
        "SELECT nombre, stock FROM productos WHERE stock <= ? ORDER BY stock",
        (UMBRAL_BAJO_STOCK,),
    ).fetchall()

    return {
        "numero_pedidos": numero_pedidos,
        "total_ingresos": round(total_ingresos, 2),
        "valor_inventario": round(valor_inventario, 2),
        "top_productos": top_productos,   # lista de tuplas (nombre, cantidad_vendida)
        "bajo_stock": bajo_stock,          # lista de tuplas (nombre, stock)
    }


# ===========================================================================
# SECCIÓN 8 — Menú de consola (presentación)
# ===========================================================================
# Esta es la ÚNICA sección que interactúa con el usuario (imprime texto, lee
# lo que teclea). Todo lo de arriba es lógica de negocio pura: si el día de
# mañana esto se convierte en una página web, solo esta sección se reescribe.

# --- Utilidades de entrada de datos ---
# Existen para no repetir la misma validación (campo vacío, número inválido,
# etc.) en cada punto del menú donde se le pide algo al usuario.

def pedir_texto(mensaje: str) -> str:
    """Pide un texto no vacío, repitiendo la pregunta hasta recibir uno."""
    while True:                              # Bucle controlado: solo se sale con un 'return' cuando el dato es válido.
        valor = input(mensaje).strip()        # .strip() quita espacios sobrantes al inicio/final de lo que el usuario escribió.
        if valor:                              # Una cadena vacía ("") se evalúa como False en Python, así que esto detecta campos vacíos.
            return valor                        # Dato válido: se devuelve y el bucle termina.
        print("  → Este campo no puede estar vacío.")   # Dato inválido: se avisa y el bucle vuelve a preguntar.


def pedir_float(mensaje: str, minimo: float = 0) -> float:
    """Pide un número decimal mayor o igual a 'minimo', repitiendo hasta recibir uno válido."""
    while True:
        valor = input(mensaje).strip().replace(",", ".")   # Acepta tanto "15.5" como "15,5" (coma decimal, común en español).
        try:
            numero = float(valor)               # Intenta convertir el texto a número; si no se puede, lanza ValueError.
            if numero < minimo:
                print(f"  → El valor debe ser mayor o igual a {minimo}.")
                continue                          # 'continue' salta directo a la siguiente vuelta del bucle (vuelve a preguntar).
            return numero
        except ValueError:                       # Se captura específicamente ValueError (no cualquier error) para no ocultar otros bugs.
            print("  → Ingresa un número válido.")


def pedir_entero(mensaje: str, minimo: int = 0) -> int:
    """Pide un número entero mayor o igual a 'minimo', repitiendo hasta recibir uno válido."""
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


def pedir_entero_opcional(mensaje: str, minimo: int = 0):
    """
    Igual que pedir_entero, pero si el usuario deja el campo vacío devuelve
    None en vez de insistir. Se usa en 'editar producto', donde dejar vacío
    significa "no cambiar este valor".
    """
    valor = input(mensaje).strip()
    if not valor:
        return None                              # Campo vacío: el llamador interpretará esto como "sin cambios".
    try:
        numero = int(valor)
        if numero < minimo:
            print("  → Valor inválido, se mantiene el valor anterior.")
            return None
        return numero
    except ValueError:
        print("  → Valor inválido, se mantiene el valor anterior.")
        return None


def pedir_float_opcional(mensaje: str, minimo: float = 0):
    """Versión de pedir_float que acepta dejar el campo vacío (ver pedir_entero_opcional)."""
    valor = input(mensaje).strip().replace(",", ".")
    if not valor:
        return None
    try:
        numero = float(valor)
        if numero < minimo:
            print("  → Valor inválido, se mantiene el valor anterior.")
            return None
        return numero
    except ValueError:
        print("  → Valor inválido, se mantiene el valor anterior.")
        return None


def confirmar(mensaje: str) -> bool:
    """Pregunta sí/no; cualquier variante de "sí" cuenta como afirmativo."""
    return input(mensaje).strip().lower() in ("s", "si", "sí", "y", "yes")


def formatear_dinero(valor: float) -> str:
    """Da formato de moneda a un número, por ejemplo 1234.5 -> '$1,234.50'."""
    return f"${valor:,.2f}"   # ',' agrega separador de miles, '.2f' fuerza siempre 2 decimales.


def pausar() -> None:
    """Espera a que el usuario presione Enter antes de seguir (para poder leer el resultado anterior)."""
    input("\nPresiona Enter para continuar...")


# --- Pantallas: Catálogo y carrito ---

def pantalla_ver_catalogo(conn) -> None:
    """Muestra todos los productos disponibles, con aviso de bajo stock."""
    print("\n--- Catálogo de productos ---")
    lista = listar_productos(conn)   # Lista de objetos Producto (Sección 3).
    if not lista:                     # Lista vacía: no hay nada que mostrar.
        print("  (No hay productos registrados todavía)")
        return

    # Encabezado de la tabla, con ancho fijo por columna para que se alinee visualmente.
    print(f"{'ID':<4}{'Producto':<25}{'Precio':<15}{'Stock':<10}")
    print("-" * 54)
    for producto in lista:                       # Recorre cada Producto y lo imprime como una fila.
        alerta = "  ⚠ bajo stock" if producto.stock <= 5 else ""   # Aviso visual solo si el stock es bajo.
        print(f"{producto.id:<4}{producto.nombre:<25}{formatear_dinero(producto.precio):<15}{producto.stock:<10}{alerta}")


def pantalla_agregar_al_carrito(conn) -> None:
    """Pide un ID de producto y una cantidad, y los agrega al carrito."""
    print("\n--- Agregar producto al carrito ---")
    pantalla_ver_catalogo(conn)                  # Se muestra el catálogo para que el usuario sepa qué IDs existen.

    lista = listar_productos(conn)
    if not lista:
        return   # Ya se mostró el aviso de catálogo vacío arriba; no hay nada más que hacer aquí.

    producto_id = pedir_entero("\nID del producto a agregar: ", minimo=1)
    cantidad = pedir_entero("Cantidad: ", minimo=1)

    # Todas las validaciones de negocio (¿existe?, ¿hay stock?) ocurren DENTRO de
    # agregar_al_carrito; aquí solo hace falta que el menú principal atrape el error si algo falla.
    agregar_al_carrito(conn, producto_id, cantidad)
    print("  ✔ Producto agregado al carrito.")


def _imprimir_resumen_carrito(resumen: ResumenCarrito) -> None:
    """Función auxiliar para imprimir un ResumenCarrito; la reutilizan varias pantallas."""
    if resumen.esta_vacio:
        print("  (El carrito está vacío)")
        return
    for item in resumen.items:                  # Cada 'item' es un ItemCarrito (Sección 3).
        print(f"  [{item.producto_id}] {item.cantidad} x {item.nombre} "
              f"@ {formatear_dinero(item.precio_unitario)} = {formatear_dinero(item.subtotal)}")
    print(f"\n  TOTAL: {formatear_dinero(resumen.total)}")


def pantalla_ver_carrito(conn) -> None:
    """Muestra el contenido actual del carrito."""
    print("\n--- Carrito de compras ---")
    resumen = ver_carrito(conn)
    _imprimir_resumen_carrito(resumen)


def pantalla_quitar_del_carrito(conn) -> None:
    """Pide un ID de producto y lo elimina por completo del carrito."""
    print("\n--- Quitar producto del carrito ---")
    resumen = ver_carrito(conn)
    _imprimir_resumen_carrito(resumen)
    if resumen.esta_vacio:
        return

    producto_id = pedir_entero("\nID del producto a quitar: ", minimo=1)
    quitar_del_carrito(conn, producto_id)
    print("  ✔ Producto eliminado del carrito.")


def pantalla_actualizar_cantidad_carrito(conn) -> None:
    """Pide un ID de producto en el carrito y una cantidad nueva exacta."""
    print("\n--- Actualizar cantidad en el carrito ---")
    resumen = ver_carrito(conn)
    _imprimir_resumen_carrito(resumen)
    if resumen.esta_vacio:
        return

    producto_id = pedir_entero("\nID del producto a actualizar: ", minimo=1)
    nueva_cantidad = pedir_entero("Nueva cantidad (0 para quitarlo): ", minimo=0)
    actualizar_cantidad(conn, producto_id, nueva_cantidad)
    print("  ✔ Carrito actualizado.")


def pantalla_vaciar_carrito(conn) -> None:
    """Vacía el carrito por completo, con confirmación previa."""
    print("\n--- Vaciar carrito ---")
    if confirmar("¿Seguro que deseas vaciar el carrito? (s/n): "):
        vaciar_carrito(conn)
        print("  ✔ Carrito vaciado.")
    else:
        print("  Operación cancelada.")


def pantalla_checkout(conn) -> None:
    """Pide los datos del cliente y confirma el carrito actual como un pedido nuevo."""
    print("\n--- Checkout ---")
    resumen = ver_carrito(conn)
    _imprimir_resumen_carrito(resumen)
    if resumen.esta_vacio:
        return   # procesar_checkout también lo validaría, pero cortar aquí evita pedir datos de más al usuario.

    cliente_nombre = pedir_texto("\nNombre del cliente: ")
    direccion_envio = pedir_texto("Dirección de envío: ")
    costo_envio = pedir_float("Costo de envío (0 si no aplica): ", minimo=0)

    if not confirmar(f"\n¿Confirmar compra por un total aproximado de "
                      f"{formatear_dinero(resumen.total + costo_envio)}? (s/n): "):
        print("  Compra cancelada.")
        return

    recibo = procesar_checkout(conn, cliente_nombre, direccion_envio, costo_envio)
    print(f"\n  ✔ Pedido #{recibo.pedido_id} confirmado. Estado: {recibo.estado}")
    print(f"  Subtotal: {formatear_dinero(recibo.subtotal)}  |  "
          f"Envío: {formatear_dinero(recibo.costo_envio)}  |  Total: {formatear_dinero(recibo.total)}")


# --- Pantallas: Historial y reportes ---

def pantalla_historial_pedidos(conn) -> None:
    """Muestra todos los pedidos confirmados, del más reciente al más antiguo."""
    print("\n--- Historial de pedidos ---")
    lista = listar_pedidos(conn)
    if not lista:
        print("  (No se han confirmado pedidos todavía)")
        return

    for recibo in lista:                          # Cada 'recibo' es un objeto Recibo (Sección 3).
        print(f"\nPedido #{recibo.pedido_id} — {recibo.fecha} — Estado: {recibo.estado}")
        print(f"  Cliente: {recibo.cliente_nombre}  |  Envío a: {recibo.direccion_envio}")
        for linea in recibo.lineas:                # Cada 'linea' es un LineaPedido.
            print(f"    - {linea.cantidad} x {linea.nombre} @ {formatear_dinero(linea.precio_unitario)} "
                  f"= {formatear_dinero(linea.subtotal)}")
        print(f"  Subtotal: {formatear_dinero(recibo.subtotal)}  |  "
              f"Envío: {formatear_dinero(recibo.costo_envio)}  |  Total: {formatear_dinero(recibo.total)}")


def pantalla_reporte_general(conn) -> None:
    """Muestra un resumen general: ingresos, valor de inventario, más vendidos y bajo stock."""
    print("\n--- Reporte general ---")
    reporte = reporte_general(conn)        # Diccionario con todas las métricas ya calculadas (Sección 7).

    print(f"  Número de pedidos confirmados: {reporte['numero_pedidos']}")
    print(f"  Ingresos totales: {formatear_dinero(reporte['total_ingresos'])}")
    print(f"  Valor total del inventario actual: {formatear_dinero(reporte['valor_inventario'])}")

    print("\n  Productos más vendidos:")
    if not reporte["top_productos"]:
        print("    (Aún no hay pedidos confirmados)")
    else:
        for nombre, cantidad in reporte["top_productos"]:
            print(f"    - {nombre}: {cantidad} unidades vendidas")

    print("\n  Productos con bajo stock (5 o menos):")
    if not reporte["bajo_stock"]:
        print("    (Ningún producto con bajo stock)")
    else:
        for nombre, stock in reporte["bajo_stock"]:
            print(f"    - {nombre}: {stock} unidades")


# --- Pantallas: Administración de inventario ---

def pantalla_agregar_producto(conn) -> None:
    """Pide los datos de un producto nuevo y lo agrega al catálogo."""
    print("\n--- Agregar producto nuevo ---")
    nombre = pedir_texto("Nombre del producto: ")
    precio = pedir_float("Precio unitario: ")
    stock = pedir_entero("Cantidad en stock: ")

    nuevo_id = agregar_producto(conn, nombre, precio, stock)
    print(f"  ✔ Producto '{nombre}' agregado con ID {nuevo_id}.")


def pantalla_editar_producto(conn) -> None:
    """Permite cambiar el precio y/o el stock de un producto existente."""
    print("\n--- Editar producto ---")
    pantalla_ver_catalogo(conn)

    producto_id = pedir_entero("\nID del producto a editar: ", minimo=1)
    producto = obtener_producto(conn, producto_id)
    if producto is None:
        print("  → No existe un producto con ese ID.")
        return

    print(f"Editando '{producto.nombre}' "
          f"(precio actual: {formatear_dinero(producto.precio)}, stock actual: {producto.stock})")
    print("Deja el campo vacío para mantener el valor actual.")

    nuevo_precio = pedir_float_opcional(f"Nuevo precio [{producto.precio}]: ")
    nuevo_stock = pedir_entero_opcional(f"Nuevo stock [{producto.stock}]: ")

    editar_producto(conn, producto_id, precio=nuevo_precio, stock=nuevo_stock)
    print("  ✔ Producto actualizado.")


def pantalla_eliminar_producto(conn) -> None:
    """Elimina un producto del catálogo, con confirmación previa."""
    print("\n--- Eliminar producto ---")
    pantalla_ver_catalogo(conn)

    producto_id = pedir_entero("\nID del producto a eliminar: ", minimo=1)
    producto = obtener_producto(conn, producto_id)
    if producto is None:
        print("  → No existe un producto con ese ID.")
        return

    if confirmar(f"¿Seguro que deseas eliminar '{producto.nombre}'? (s/n): "):
        eliminar_producto(conn, producto_id)
        print("  ✔ Producto eliminado.")
    else:
        print("  Operación cancelada.")


# --- Menú principal ---

# Texto del menú, separado en secciones para que el usuario entienda de un
# vistazo qué opciones son de "comprar" y cuáles son de "administrar".
MENU = """
==========================================
   SISTEMA DE TIENDA EN LÍNEA
==========================================
--- Catálogo y compras ---
1. Ver catálogo de productos
2. Agregar producto al carrito
3. Ver carrito de compras
4. Quitar producto del carrito
5. Actualizar cantidad en el carrito
6. Vaciar carrito
7. Confirmar compra (checkout)
--- Historial y reportes ---
8. Ver historial de pedidos
9. Reporte general
--- Administración de inventario ---
10. Agregar producto nuevo
11. Editar producto (precio/stock)
12. Eliminar producto
0. Salir
==========================================
"""


def main() -> None:
    conn = conectar()   # Abre (o crea) la base de datos y asegura que las tablas existan (Sección 1).
    print("Bienvenido al sistema de tienda en línea.")
    print(f"Base de datos: {DB_PATH}")

    # Diccionario que asocia cada opción del menú con la función que debe ejecutar.
    # Usar un diccionario en vez de una cadena larga de "if opcion == '1': ... elif ...
    # opcion == '2': ..." hace que agregar una opción nueva sea una sola línea aquí,
    # sin tocar el resto de la estructura del menú.
    acciones = {
        "1": pantalla_ver_catalogo,
        "2": pantalla_agregar_al_carrito,
        "3": pantalla_ver_carrito,
        "4": pantalla_quitar_del_carrito,
        "5": pantalla_actualizar_cantidad_carrito,
        "6": pantalla_vaciar_carrito,
        "7": pantalla_checkout,
        "8": pantalla_historial_pedidos,
        "9": pantalla_reporte_general,
        "10": pantalla_agregar_producto,
        "11": pantalla_editar_producto,
        "12": pantalla_eliminar_producto,
    }

    try:
        while True:                                   # Bucle principal del programa: se repite hasta que el usuario elige "Salir".
            print(MENU)
            opcion = input("Elige una opción: ").strip()

            if opcion == "0":
                print("\n¡Gracias por usar el sistema! Hasta pronto.")
                break                                   # Rompe el bucle 'while True' y el programa termina limpiamente.

            accion = acciones.get(opcion)               # Busca la función correspondiente a la opción tecleada.
            if accion is None:
                print("  → Opción inválida, intenta de nuevo.")
                continue                                 # Vuelve directo a mostrar el menú, sin pausar.

            try:
                accion(conn)                             # Ejecuta la pantalla elegida, pasándole la conexión abierta.
            except ErrorTienda as error:
                # Cualquier error de negocio (stock insuficiente, carrito vacío, etc.)
                # cae aquí y se muestra de forma amigable, sin detener el programa.
                print(f"  → {error}")
            except ValueError as error:
                # Errores de validación simples (cantidades negativas, etc.).
                print(f"  → {error}")
            except sqlite3.Error as error:
                # Cualquier error inesperado de la base de datos (por ejemplo, una restricción CHECK violada).
                print(f"  → Error de base de datos: {error}")

            pausar()                                     # Da tiempo de leer el resultado antes de volver a mostrar el menú.
    except KeyboardInterrupt:
        # Si el usuario presiona Ctrl+C, se sale del programa de forma ordenada en vez de mostrar un traceback feo.
        print("\n\nPrograma interrumpido. ¡Hasta pronto!")
    finally:
        conn.close()   # 'finally' garantiza que la conexión se cierre siempre, incluso si algo falló arriba.


if __name__ == "__main__":
    # Este bloque evita que main() se ejecute automáticamente si este archivo
    # se importa desde otro script; solo se ejecuta cuando tienda-completa.py se corre directamente.
    main()