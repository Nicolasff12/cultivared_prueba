from flask import Flask,flash, render_template, Blueprint, request, redirect, url_for, session
from config import get_connection  # Importamos la conexión a PostgreSQL
from models import ItemPedido, Pedido, Usuarios, db, Producto
from sqlalchemy.orm import joinedload
from collections import defaultdict
from datetime import datetime
from sqlalchemy import func

main = Blueprint('gestor_blueprint', __name__)


@main.route('/')
def gestor():
    if 'logueado' in session and session['logueado']:
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener datos del usuario autenticado
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (session['email'],))
        user = cur.fetchone()
        
        cur.close()
        conn.close()

        if user:
            return render_template('gestor/perfilGestor.html', user=user)
        else:
            
            return """<script> alert("Usuario no encontrado."); window.location.href = "/CULTIVARED/login"; </script>"""
    
    return """<script> alert("Por favor, primero inicie sesión."); window.location.href = "/CULTIVARED/login"; </script>"""


@main.route('/gestion_usuarios')
def gestion_usuarios():
    if 'logueado' in session and session['logueado']:
        rol = request.args.get('rol', 'all')  # Obtener el rol desde la URL

        conn = get_connection()
        cur = conn.cursor()

        if rol == 'all':
            cur.execute('SELECT id, nombre, apellido, genero, email, telefono, rol FROM usuarios')
        else:
            cur.execute('SELECT id, nombre, apellido, genero, email, telefono, rol FROM usuarios WHERE LOWER(rol) = %s', (rol.lower(),))

        users = cur.fetchall()
        cur.close()
        conn.close()

        print("Usuarios obtenidos:", users)  # Verifica en consola qué datos se están trayendo

        return render_template('gestor/gestionUsuarios.html', usuarios=users, selected_role=rol)
    else:
        return redirect(url_for('auth.login'))


def obtener_usuario_por_id(user_id):
    connection = get_connection()  # Asegúrate de tener tu conexión a la DB
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
    usuario = cursor.fetchone()
    connection.close()
    return usuario

@main.route('/GESTOR/perfil_usuario/<int:user_id>') 
def perfil_usuario(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    rol_usuario = user[6]  # Aquí está el rol: 'vendedor' o 'comprador'
    print("Usuario:", user)

    return render_template('gestor/perfil_usuario.html', user=user, rol_usuario=user[6])


@main.route('/dashboard')
def dashboard():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Total de vendedores y compradores
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM usuarios WHERE LOWER(TRIM(rol)) = 'vendedor') AS total_vendedores,
            (SELECT COUNT(*) FROM usuarios WHERE LOWER(TRIM(rol)) = 'comprador') AS total_compradores;
    """)
    resultado = cur.fetchone()
    print("Resultado conteo roles:", resultado)
    total_vendedores, total_compradores = resultado

    print(f"Vendedores: {total_vendedores}, Compradores: {total_compradores}")  # Debug
    # 🔹 2. Ventas realizadas por cada vendedor
    cur.execute("""
        SELECT u.nombre, COUNT(p.id) AS total_ventas
        FROM usuarios u
        JOIN productos p ON u.id = p.id_vendedor
        GROUP BY u.nombre
        ORDER BY total_ventas DESC;
    """)
    ventas_por_vendedor = cur.fetchall()

    # 🔹 3. Productos más vendidos
    cur.execute("""
        SELECT nombre, cantidad FROM productos ORDER BY cantidad DESC LIMIT 5;
    """)
    productos_mas_vendidos = cur.fetchall()

    # 🔹 4. Total de ingresos generados
    cur.execute("""
        SELECT SUM(precio * cantidad) FROM productos;
    """)
    total_ingresos = cur.fetchone()[0]

    cur.close()
    conn.close()

    return render_template(
        'gestor/dashboard.html', 
        total_vendedores=total_vendedores, 
        total_compradores=total_compradores,
        ventas_por_vendedor=ventas_por_vendedor,
        productos_mas_vendidos=productos_mas_vendidos,
        total_ingresos=total_ingresos
    )


@main.route('/inventario_usuario/<int:user_id>')
def inventario_usuario(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Traer productos registrados por ese usuario
    cur.execute('SELECT * FROM productos WHERE id_vendedor = %s', (user_id,))
    productos = cur.fetchall()

    # Traer info del usuario (opcional)
    cur.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('gestor/inventarioUsuario.html', produ=productos, user=user)



def obtener_historial_pedidos_vendedor(id_vendedor):
    historial = (
        db.session.query(ItemPedido)
        .join(Producto)
        .join(Pedido)
        .join(Usuarios)  # comprador
        .filter(Producto.id_vendedor == id_vendedor)
        .options(
            joinedload(ItemPedido.producto),
            joinedload(ItemPedido.pedido).joinedload(Pedido.usuario)
        )
        .order_by(Pedido.fecha.desc())
        .all()
    )
    return historial

def obtener_resumen_ventas(id_vendedor):
    # Consulta para agrupar por producto y sumar cantidad y total vendido
    resultados = (
        db.session.query(
            Producto.nombre,
            func.sum(ItemPedido.cantidad).label('total_cantidad'),
            func.sum(ItemPedido.precio * ItemPedido.cantidad).label('total_ganancia')
        )
        .join(ItemPedido, Producto.id == ItemPedido.producto_id)
        .filter(Producto.id_vendedor == id_vendedor)
        .group_by(Producto.nombre)
        .all()
    )

    productos_mas_vendidos_nombres = []
    productos_mas_vendidos_cantidades = []
    total_ganancias = 0
    total_productos = 0

    for nombre, cantidad, ganancia in resultados:
        productos_mas_vendidos_nombres.append(nombre)
        productos_mas_vendidos_cantidades.append(cantidad)
        total_ganancias += ganancia
        total_productos += cantidad

    producto_mas_vendido = productos_mas_vendidos_nombres[productos_mas_vendidos_cantidades.index(max(productos_mas_vendidos_cantidades))] if productos_mas_vendidos_cantidades else "Ninguno"

    resumen = {
        'total_ganancias': total_ganancias,
        'total_productos': total_productos,
        'producto_mas_vendido': producto_mas_vendido
    }

    return resumen, productos_mas_vendidos_nombres, productos_mas_vendidos_cantidades



@main.route('/resumen_ventas/<int:user_id>')
def resumen_ventas(user_id):
    if 'id' not in session:
        flash("Por favor, inicia sesión.", "warning")
        return redirect(url_for('autenticacion.login'))
    
    # Obtener usuario (Laura o quien sea)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    user = cur.fetchone()
    
    if not user:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('main.index'))
    
    # Obtener historial de pedidos del vendedor
    historial = obtener_historial_pedidos_vendedor(user_id)
    
    # Calcular resumen
    total_ganancias = sum(item.precio * item.cantidad for item in historial)
    total_productos = sum(item.cantidad for item in historial)
    
    productos_vendidos = {}
    ingresos_por_mes = {}
    for item in historial:
        nombre = item.producto.nombre
        productos_vendidos[nombre] = productos_vendidos.get(nombre, 0) + item.cantidad
        
        mes = item.pedido.fecha.strftime('%B %Y')
        ingresos_por_mes[mes] = ingresos_por_mes.get(mes, 0) + (item.precio * item.cantidad)
    
    producto_mas_vendido = max(productos_vendidos.items(), key=lambda x: x[1])[0] if productos_vendidos else "Ninguno"
    
    resumen = {
        'total_ganancias': total_ganancias,
        'total_productos': total_productos,
        'producto_mas_vendido': producto_mas_vendido
    }
    
    # Ordenar meses cronológicamente (si quieres, ajusta según idioma o formato)
    meses = sorted(ingresos_por_mes.keys(), key=lambda x: datetime.strptime(x, '%B %Y'))
    ingresos_mes_ordenados = [ingresos_por_mes[mes] for mes in meses]
    
    productos_mas_vendidos_nombres = list(productos_vendidos.keys())
    productos_mas_vendidos_cantidades = list(productos_vendidos.values())
    
    cur.close()
    conn.close()
    
    return render_template('gestor/resumenVentas.html',
                        user=user,
                            resumen=resumen,
                            productos_mas_vendidos_nombres=productos_mas_vendidos_nombres,
                            productos_mas_vendidos_cantidades=productos_mas_vendidos_cantidades,
                            meses=meses,
                            ingresos_por_mes=ingresos_por_mes)


@main.route('/historial_pedidos/<int:user_id>')
def historial_pedidos(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Traer info del vendedor
    cur.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    user = cur.fetchone()

    # Traer historial de pedidos de productos de ese vendedor
    cur.execute("""
        SELECT ip.id, ip.cantidad, ip.precio, p.nombre, pe.fecha, u.nombre
        FROM items_pedido ip
        JOIN productos pr ON ip.producto_id = pr.id
        JOIN pedidos pe ON ip.pedido_id = pe.id
        JOIN usuarios u ON pe.id_usuario = u.id
        JOIN productos p ON p.id = ip.producto_id
        WHERE pr.id_vendedor = %s
        ORDER BY pe.fecha DESC
    """, (user_id,))

    historial = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('gestor/historialPedidos.html', historial=historial, user=user)
from collections import defaultdict
from datetime import datetime


def obtener_datos_graficos_ventas(id_vendedor):
    historial = (
        db.session.query(ItemPedido)
        .join(Producto)
        .join(Pedido)
        .filter(Producto.id_vendedor == id_vendedor)
        .all()
    )

    ingresos_por_mes = defaultdict(float)
    productos_vendidos = defaultdict(int)

    for item in historial:
        mes = item.pedido.fecha.strftime('%B %Y') 
        ingresos_por_mes[mes] += float(item.precio) * item.cantidad


        nombre_producto = item.producto.nombre
        productos_vendidos[nombre_producto] += item.cantidad

    # Ordenar los meses cronológicamente
    meses_ordenados = sorted(ingresos_por_mes.keys(), key=lambda x: datetime.strptime(x, '%B %Y'))
    ingresos_ordenados = [ingresos_por_mes[mes] for mes in meses_ordenados]

    nombres_productos = list(productos_vendidos.keys())
    cantidades_productos = list(productos_vendidos.values())

    return meses_ordenados, ingresos_ordenados, nombres_productos, cantidades_productos


@main.route('/grafico_vendedor/<int:user_id>')
def grafico_vendedor(user_id):
    conn = get_connection()
    cur = conn.cursor()

    # Obtener info del usuario
    cur.execute('SELECT id, nombre FROM usuarios WHERE id = %s', (user_id,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    # Obtener resumen
    resumen, productos_mas_vendidos_nombres, productos_mas_vendidos_cantidades = obtener_resumen_ventas(user_id)

    # Obtener datos para gráficas
    meses, ingresos_por_mes, nombres_productos, cantidades_productos = obtener_datos_graficos_ventas(user_id)
   
    return render_template('gestor/graficoVendedor.html',
                           user=user,
                           resumen=resumen,
                           productos_mas_vendidos_nombres=productos_mas_vendidos_nombres,
                           productos_mas_vendidos_cantidades=productos_mas_vendidos_cantidades,
                           meses=meses,
                           ingresos_por_mes=ingresos_por_mes)
