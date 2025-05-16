from flask import Flask, render_template, Blueprint, request, redirect, url_for, session,flash
from config import get_connection  # Importamos la conexión a PostgreSQL

main = Blueprint('autenticacion_blueprint', __name__)

@main.route('/')
def index():
    return render_template('inicio.html')

@main.route('/Registro')
def registro():
    return render_template('/autenticacion/registro.html')

@main.route('/IniciaSesion')
def iniciar():
    return render_template('/autenticacion/login.html')

@main.route('/formulario', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        ide = request.form['identificacion']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        genero = request.form['genero']
        telefono = request.form['telefono']
        email = request.form['email']
        contrasena1 = request.form['contrasena1']
        contrasena2 = request.form['contrasena2']
        rol = request.form['rol']

        errores = []

        conn = get_connection()
        cur = conn.cursor()

        # Validaciones
        cur.execute('SELECT id FROM usuarios WHERE id = %s', (ide,))
        if cur.fetchone():
            errores.append("La identificación ya está registrada.")

        cur.execute('SELECT email FROM usuarios WHERE email = %s', (email,))
        if cur.fetchone():
            errores.append("El correo electrónico ya está registrado.")

        cur.execute('SELECT telefono FROM usuarios WHERE telefono = %s', (telefono,))
        if cur.fetchone():
            errores.append("El número de celular ya está registrado.")

        if contrasena1 != contrasena2:
            errores.append("Las contraseñas no coinciden.")

        # Mostrar errores si hay
        if errores:
            mensaje = "<ul>"
            for error in errores:
                mensaje += f"<li>{error}</li>"
            mensaje += "</ul>"

            flash(mensaje, "danger")
            cur.close()
            conn.close()
            return redirect('/CULTIVARED/Registro')

        # Insertar el usuario si no hay errores
        cur.execute("""
            INSERT INTO usuarios (id, nombre, apellido, genero, telefono, email, contrasena, rol)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (ide, nombre, apellido, genero, telefono, email, contrasena1, rol))

        conn.commit()
        cur.close()
        conn.close()

        return "<script>alert('Usuario registrado correctamente'); window.location.href = '/CULTIVARED/login';</script>"


    return render_template("inicio.html")


@main.route('/login', methods=['GET', 'POST'])
def log():
    if request.method == 'POST':
        ema = request.form['email']
        contrasena = request.form['contrasena']

        conn = get_connection()
        cur = conn.cursor()

        # Consultar usuario en la base de datos
        cur.execute("SELECT id, email, rol FROM usuarios WHERE email=%s AND contrasena=%s", (ema, contrasena))
        account = cur.fetchone()

        cur.close()
        conn.close()

        # Validar si se encontró un usuario
        if account:
            session['logueado'] = True
            session['id'] = account[0]  # ID del usuario
            session['email'] = account[1]  # Email del usuario
            session['rol'] = account[2]  # Rol del usuario

            if session['rol'] == 'Admin':
                return """<script> alert("Bienvenido a CULTIVARED"); window.location.href = "/ADMINISTRADOR"; </script>"""
            elif session['rol'] == 'Vendedor':
                return """<script> alert("Bienvenido a CULTIVARED"); window.location.href = "/VENDEDOR"; </script>"""
            elif session['rol'] == 'Comprador':
                return """<script> alert("Bienvenido a CULTIVARED"); window.location.href = "/COMPRADOR"; </script>"""
            elif session['rol'] == 'Gestor':
                return """<script> alert("Bienvenido a CULTIVARED"); window.location.href = "/GESTOR"; </script>"""
        else:
            return """<script> alert("Usuario o contraseña incorrecta"); window.location.href = "/CULTIVARED/login"; </script>"""

    return render_template("/autenticacion/login.html")

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('autenticacion_blueprint.index'))
