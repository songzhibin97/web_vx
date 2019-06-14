from flask import Flask
from web_vx.views.login import vx_demo


def get_app():
    app = Flask(__name__)
    app.secret_key = 'bin'
    app.register_blueprint(vx_demo)
    return app
