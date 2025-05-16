import io
import os
from flask import Flask, flash, render_template, Blueprint, request, redirect, send_file, url_for, session, send_file
from config import get_connection
from models import db, Usuarios, Producto, Transaccion, TransaccionItem


# Definir el Blueprint antes de usarlo
main = Blueprint('admin_blueprint', __name__)

# Definir la ruta de inicio
@main.route('/')
def admin():
    if 'logueado' in session and session['logueado']:
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener datos del usuario autenticado
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (session['email'],))
        user = cur.fetchone()
        
        cur.close()
        conn.close()

        if user:
            return render_template('administrador/administrador.html', user=user)
        else:
            return """<script> alert("Usuario no encontrado."); window.location.href = "/CULTIVARED/login"; </script>"""
    
    return """<script> alert("Por favor, primero inicie sesión."); window.location.href = "/CULTIVARED/login"; </script>"""

# Definir la ruta de perfil
@main.route('/perfil')
def perfil():
    if 'logueado' in session and session['logueado']:
        conn = get_connection()
        cur = conn.cursor()
        
        # Obtener datos del usuario autenticado
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (session['email'],))
        user = cur.fetchone()
        
        cur.close()
        conn.close()

        if user:
            return render_template('administrador/perfil.html', user=user)
        else:
            return """<script> alert("Usuario no encontrado."); window.location.href = "/CULTIVARED/login"; </script>"""
    
    return """<script> alert("Por favor, primero inicie sesión."); window.location.href = "/CULTIVARED/login"; </script>"""

# TRANSACCIONES
# Definir la ruta de transacciones
@main.route('/transacciones')
def transacciones():
    if 'logueado' in session and session['logueado']:
        # Conecta a la BD y obtener el usuario actual
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (session['email'],))
        user = cur.fetchone()
        cur.close()
        conn.close()

        # user al render_template
        return render_template('administrador/transacciones.html', user=user)
    else:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""

# PRODUCTOS
# Definir la ruta de productos
@main.route('/productos')
def productos():
    if 'logueado' in session and session['logueado']:
        conn = get_connection()
        cur = conn.cursor()

        # Obtener el usuario logueado
        cur.execute('SELECT * FROM usuarios WHERE email = %s', (session['email'],))
        user = cur.fetchone()

        # Obtener la lista de productos
        cur.execute('SELECT id, nombre, categoria, cantidad, precio, id_vendedor, imagen FROM productos')
        productos = cur.fetchall()

        cur.close()
        conn.close()
        
        return render_template('administrador/productos.html', user=user, productos=productos)
    else:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""

# Definir la ruta de imagen de producto    
@main.route('/imagen_producto/<int:producto_id>')
def imagen_producto(producto_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT imagen FROM productos WHERE id = %s", (producto_id,))
    imagen = cur.fetchone()
    cur.close()
    conn.close()

    if imagen and imagen[0]:
        return send_file(io.BytesIO(imagen[0]), mimetype='image/jpeg')  # Ajusta a 'image/png' si usas PNG
    else:
        return "", 204  # No hay imagen

# Definir la ruta de registrar producto   
@main.route('/productos/registrar', methods=['GET', 'POST'])
def registrar_producto():
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert('No estás logueado.');window.location.href='/CULTIVARED/login';</script>"""
    session.pop('_flashes', None) # Limpiar los mensajes flash previos

    if request.method == 'POST':
        try:
            id_producto = request.form['idProducto']
            nombre = request.form['nombreProducto']
            categoria = request.form['categoria']
            cantidad = request.form['cantidad']
            precio = request.form['precio']
            descripcion = request.form['descripcionProducto']
            id_vendedor = request.form['id_vendedor']  # Captura el ID del vendedor
            imagen_file = request.files.get('imagen')

            # Manejo de la imagen: Si no se sube, mostrar mensaje y evitar error
            if not imagen_file or imagen_file.filename == '':
                flash("Debes subir una imagen del producto.", "error")
                return redirect(url_for('admin_blueprint.registrar_producto'))

            imagen_bytes = imagen_file.read()  # Convertir imagen a bytes

            # Validar que se seleccione un vendedor
            if not id_vendedor:
                flash("Debes seleccionar un vendedor.", "error")
                return redirect(url_for('admin_blueprint.registrar_producto'))

            nuevo_producto = Producto(
                id=id_producto,
                nombre=nombre,
                categoria=categoria,
                cantidad=cantidad,
                precio=precio,
                descripcion=descripcion,
                id_vendedor=id_vendedor,
                imagen=imagen_bytes
            )

            db.session.add(nuevo_producto)
            db.session.commit()

            flash("Producto registrado correctamente.", "success")
            return redirect(url_for('admin_blueprint.productos'))

        except Exception as e:
            flash(f"Error al registrar el producto: {str(e)}", "error")
            return redirect(url_for('admin_blueprint.registrar_producto'))

    # Obtener la lista de vendedores para mostrar en el formulario
    vendedores = Usuarios.query.filter_by(rol="Vendedor").all()

    return render_template('administrador/registrar_producto.html', vendedores=vendedores)

# Definir la ruta de editar producto
@main.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    try:
        producto = Producto.query.get(id)
        if not producto:
            flash("El producto no existe o no se pudo cargar.", "error")
            return redirect(url_for('admin_blueprint.productos'))
        
        if request.method == 'POST':
            producto.nombre = request.form['nombreProducto']
            producto.categoria = request.form['categoria']
            producto.cantidad = request.form['cantidad']
            producto.precio = request.form['precio']
            producto.descripcion = request.form['descripcionProducto']

            imagen_file = request.files.get('imagen')
            if imagen_file and imagen_file.filename != '':
                producto.imagen = imagen_file.read()

            db.session.commit()
            flash("Producto actualizado correctamente.", "success")
            return redirect(url_for('admin_blueprint.productos'))
        
        return render_template('administrador/editar_producto.html', producto=producto)

    except Exception as e:
        flash(f"Error al procesar la solicitud: {str(e)}", "error")
        return redirect(url_for('admin_blueprint.productos'))

# Definir la ruta de eliminar producto
@main.route('/productos/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    producto = Producto.query.get(id)

    if not producto:
        flash("El producto no existe.", "error")
        return redirect(url_for('admin_blueprint.productos'))

    db.session.delete(producto)
    db.session.commit()

    flash("Producto eliminado correctamente.", "success")
    return redirect(url_for('admin_blueprint.productos'))

# GESTORES
# Definir la ruta de gestores
@main.route('/gestores')
def gestores():
    if 'logueado' in session and session['logueado']:
        # Consultar el usuario que inició sesión
        user = Usuarios.query.filter_by(email=session['email']).first()

        # Consultar todos los gestores (sin filtrar por estado activo)
        gestores = Usuarios.query.filter(Usuarios.rol == 'Gestor').all()

        return render_template('administrador/gestores.html', user=user, gestores=gestores)
    else:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""

# Definir la ruta de registrar gestor
@main.route('/gestores/registrar', methods=['GET', 'POST'])
def registrar_gestor():
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""  
    session.pop('_flashes', None) # Limpiar los mensajes flash previos

    # Consultar el usuario que inició sesión
    user = Usuarios.query.filter_by(email=session['email']).first()

    if request.method == 'POST':
        id_usuario = request.form['id']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        genero = request.form['genero']
        email = request.form['email']
        telefono = request.form['telefono']
        rol = request.form['rol']
        contrasena = request.form['contrasena']

        # Verificar si el ID o el correo ya existen
        usuario_existente = Usuarios.query.filter(
            (Usuarios.id == id_usuario) | (Usuarios.email == email)
        ).first()

        if usuario_existente:
            flash("El ID o correo electrónico ya están registrados.", "error")
            return redirect(url_for('admin_blueprint.registrar_gestor'))

        nuevo_gestor = Usuarios(
            id=id_usuario,
            nombre=nombre,
            apellido=apellido,
            genero=genero,
            email=email,
            telefono=telefono,
            rol=rol,
            contrasena=contrasena
        )
        db.session.add(nuevo_gestor)
        db.session.commit()

        flash("Gestor registrado correctamente.", "success")
        return redirect(url_for('admin_blueprint.gestores'))
    gestores = Usuarios.query.filter(Usuarios.rol == 'Gestor').all() # Consultar todos los gestores
    return render_template('administrador/registrar_gestor.html', user=user, gestores=gestores)

# Definir la ruta de editar gestor
@main.route('/gestores/editar/<int:id>', methods=['GET', 'POST'])
def editar_gestor(id):
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert('No estás logueado.'); window.location.href='/CULTIVARED/login';</script>"""

    # Buscar el gestor en la base de datos
    gestor = Usuarios.query.get(id)
    user = Usuarios.query.filter_by(email=session['email']).first()

    if not gestor:
        flash("Gestor no encontrado.", "error")
        return redirect(url_for('admin_blueprint.gestores'))

    if request.method == 'POST':
        # Actualizar los campos del gestor
        gestor.nombre = request.form['nombre']
        gestor.apellido = request.form['apellido']
        gestor.email = request.form['email']
        gestor.telefono = request.form['telefono']
        gestor.rol = request.form['rol']

        db.session.commit()

        flash("Gestor actualizado correctamente.", "success")
        return redirect(url_for('admin_blueprint.gestores'))

    return render_template('administrador/editar_gestor.html', gestor=gestor, user=user)

# Definir la ruta de eliminar gestor
@main.route('/gestores/eliminar/<int:id>', methods=['POST'])
def eliminar_gestor(id):
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert('No estás logueado.'); window.location.href='/CULTIVARED/login';</script>"""

    gestor = Usuarios.query.get(id)
    if not gestor:
        flash("Gestor no encontrado.", "error")
        return redirect(url_for('admin_blueprint.gestores'))

    # Eliminar el gestor de la base de datos
    db.session.delete(gestor)
    db.session.commit()

    flash("Gestor eliminado correctamente.", "success")
    return redirect(url_for('admin_blueprint.gestores'))

# USUARIOS
# Definir la ruta de usuarios
@main.route('/usuarios')
def usuarios():
    if 'logueado' in session and session['logueado']:
        user = Usuarios.query.filter_by(email=session['email']).first()
        usuarios = Usuarios.query.filter(Usuarios.rol.in_(['Vendedor', 'Comprador'])).all()

        return render_template('administrador/usuarios.html', user=user, usuarios=usuarios)
    else:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""
    
# Definir la ruta de registrar usuario
@main.route('/usuarios/registrar', methods=['GET', 'POST'])
def registrar_usuario():
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""
    session.pop('_flashes', None) # Limpiar los mensajes flash previos

    if request.method == 'POST':
        id_usuario = request.form['id']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        genero = request.form['genero']
        email = request.form['email']
        telefono = request.form['telefono']
        contrasena = request.form['contrasena']
        rol = request.form['rol']

        # Verificar si el ID o el correo ya existen
        usuario_existente = Usuarios.query.filter(
            (Usuarios.id == id_usuario) | (Usuarios.email == email)
        ).first()

        if usuario_existente:
            flash("El ID o correo electrónico ya están registrados.", "error")
            return redirect(url_for('admin_blueprint.registrar_usuario'))

        nuevo_usuario = Usuarios(
            id=id_usuario,
            nombre=nombre,
            apellido=apellido,
            genero=genero,
            email=email,
            telefono=telefono,
            contrasena=contrasena,
            rol=rol
        )

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Usuario registrado correctamente.", "success")
        return redirect(url_for('admin_blueprint.usuarios'))
    return render_template('administrador/registrar_usuario.html')

@main.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""

    usuario = Usuarios.query.get(id)
    user = Usuarios.query.filter_by(email=session['email']).first()

    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('admin_blueprint.usuarios'))

    if request.method == 'POST':
        usuario.nombre = request.form['nombre']
        usuario.email = request.form['email']
        usuario.telefono = request.form['telefono']
        usuario.rol = request.form['rol']

        db.session.commit()

        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for('admin_blueprint.usuarios'))

    return render_template('administrador/editar_usuario.html', usuario=usuario, user=user)

# Definir la ruta de eliminar usuario
@main.route('/usuarios/eliminar/<int:id>', methods=['POST'])
def eliminar_usuario(id):
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert('No estás logueado.'); window.location.href='/CULTIVARED/login';</script>"""

    usuario = Usuarios.query.get(id)
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('admin_blueprint.usuarios'))

    db.session.delete(usuario)
    db.session.commit()

    flash("Usuario eliminado correctamente.", "success")
    return redirect(url_for('admin_blueprint.usuarios'))


# Definir la ruta de editar
@main.route('/editar/<int:user_id>', methods=['GET', 'POST'])
def editar(user_id):
    # Paso 1: Verificar que el usuario esté logueado
    if 'logueado' in session and session['logueado']:
        # Conectar a la base de datos
        conn = get_connection()
        cur = conn.cursor()
        
        if request.method == 'POST':
            # Paso 2: Procesar los datos del formulario
            
            # Extraer los datos enviados desde el formulario
            # 'identificacion' se obtiene pero no se actualiza (el ID es la PK)
            identificacion = request.form.get('id')
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            email = request.form.get('email')
            genero = request.form.get('genero')
            contrasena = request.form.get('contrasena')
            confirmar_contrasena = request.form.get('confirmar_contrasena')
            telefono = request.form.get('telefono')
            
            # Validación de contraseñas
            if contrasena and contrasena != confirmar_contrasena:
                cur.close()
                conn.close()
                return """<script>alert("Las contraseñas no coinciden."); window.history.back();</script>"""
            
            # Actualizar los datos del usuario en la BD (sin tocar el rol)
            cur.execute("""
                UPDATE usuarios
                SET nombre=%s, apellido=%s, email=%s, genero=%s, telefono=%s
                WHERE id=%s
            """, (nombre, apellido, email, genero, telefono, user_id))
            
            # Si se ingresó nueva contraseña, actualizarla (sin encriptar en este ejemplo)
            if contrasena and contrasena.strip():
                cur.execute("UPDATE usuarios SET contrasena=%s WHERE id=%s", (contrasena, user_id))
            
            conn.commit()
            
            # Actualizar el correo
            session['email'] = email
            cur.close()
            conn.close()
            
            return """<script>alert("Datos actualizados correctamente."); window.location.href="/ADMINISTRADOR/perfil";</script>"""
        
        else:  # Método GET: mostrar el formulario con los datos actuales
            cur.execute("SELECT * FROM usuarios WHERE id = %s", (user_id,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user:
                # Renderizar la plantilla editarPerfil.html pasando los datos del usuario
                return render_template('administrador/editarPerfil.html', user=user)
            else:
                return """<script>alert("Usuario no encontrado."); window.location.href="/ADMINISTRADOR/perfil";</script>"""
    else:
        return """<script>alert("No estás logueado."); window.location.href="/CULTIVARED/login";</script>"""
    
# Definir la ruta de generar PDF
import os
from flask import send_file, session
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

@main.route('/generar_pdf', methods=['GET'])
def exportar_reporte_general_pdf():
    if 'logueado' not in session or not session['logueado']:
        return """<script>alert("No estás logueado.");window.location.href="/CULTIVARED/login";</script>"""

    ruta_static_real = os.path.join(os.getcwd(), "static", "reports")
    os.makedirs(ruta_static_real, exist_ok=True)
    ruta_pdf = os.path.join(ruta_static_real, "reporte_general.pdf")

    doc = SimpleDocTemplate(ruta_pdf, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("<b>Reporte General - CULTIVARED</b>", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 20))

    # 📌 Sección de Usuarios
    elements.append(Paragraph("<b>📌 Usuarios</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    usuarios = Usuarios.query.filter(Usuarios.rol.in_(['Vendedor', 'Comprador'])).all()
    data_usuarios = [["ID", "Nombre", "Apellido", "Email"]]
    for usuario in usuarios:
        data_usuarios.append([usuario.id, usuario.nombre, usuario.apellido, usuario.email])

    tabla_usuarios = Table(data_usuarios, colWidths=[50, 100, 100, 200])
    tabla_usuarios.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(tabla_usuarios)
    elements.append(Spacer(1, 20))

    # 📌 Sección de Productos
    elements.append(Paragraph("<b>📌 Productos</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    productos = Producto.query.all()
    data_productos = [["ID", "Nombre", "Precio", "Stock"]]
    for producto in productos:
        data_productos.append([producto.id, producto.nombre, f"${producto.precio}", producto.cantidad])

    tabla_productos = Table(data_productos, colWidths=[50, 150, 100, 80])
    tabla_productos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.green),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(tabla_productos)
    elements.append(Spacer(1, 20))

    # 📌 Sección de Transacciones
    elements.append(Paragraph("<b>📌 Transacciones</b>", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    transacciones = Transaccion.query.all()
    data_transacciones = [["ID", "Usuario", "Total", "Estado"]]
    for transaccion in transacciones:
        data_transacciones.append([transaccion.id, transaccion.id_usuario, f"${transaccion.total}", transaccion.estado])

    tabla_transacciones = Table(data_transacciones, colWidths=[50, 100, 100, 100])
    tabla_transacciones.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(tabla_transacciones)

    # Generar el PDF
    doc.build(elements)

    return send_file(ruta_pdf, as_attachment=True)

# Definir la ruta de estadísticas
from flask import render_template
from sqlalchemy import func

@main.route('/estadisticas', methods=['GET'])
def estadisticas():
    num_usuarios = Usuarios.query.count()
    num_vendedores = Usuarios.query.filter_by(rol="Vendedor").count()
    num_compradores = Usuarios.query.filter_by(rol="Comprador").count()

    productos_mas_vendidos = db.session.query(Producto.nombre, func.count(Producto.id))\
        .group_by(Producto.nombre)\
        .order_by(func.count(Producto.id).desc()).limit(5).all()

    productos_menos_vendidos = db.session.query(Producto.nombre, func.count(Producto.id))\
        .group_by(Producto.nombre)\
        .order_by(func.count(Producto.id).asc()).limit(5).all()

    productos_stock = db.session.query(Producto.nombre, Producto.cantidad).all()

    # Convertir datos a formato correcto
    productos_stock = [{"nombre": p[0], "cantidad": p[1]} for p in productos_stock]

    return render_template('administrador/admin_estadisticas.html', 
                           num_usuarios=num_usuarios, 
                           num_vendedores=num_vendedores,
                           num_compradores=num_compradores,
                           productos_mas_vendidos=[p[0] for p in productos_mas_vendidos],
                           productos_menos_vendidos=[p[0] for p in productos_menos_vendidos],
                           productos_stock=productos_stock)