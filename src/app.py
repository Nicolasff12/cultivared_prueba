from flask import Flask
from config import Config
from models import db
from routes import autenticacion, admin, vendedor, comprador, gestor

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)


def page_not_found(error):
    return "<h1>404 - Página no encontrada</h1>", 404

# Registrar los Blueprints
app.register_blueprint(autenticacion.main, url_prefix='/CULTIVARED')
app.register_blueprint(admin.main, url_prefix='/ADMINISTRADOR')
app.register_blueprint(vendedor.main, url_prefix='/VENDEDOR')
app.register_blueprint(comprador.main, url_prefix='/COMPRADOR')
app.register_blueprint(gestor.main, url_prefix='/GESTOR')

app.register_error_handler(404, page_not_found)

if __name__ == '__main__':
    app.run(debug=True)
