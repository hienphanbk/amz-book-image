from flask import Flask, redirect
from app.api.routes import api_bp
from app.config import get_config

def create_app():
    app = Flask(__name__)
    config = get_config()
    app.config.from_object(config)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Add a root route that redirects to /api
    @app.route('/')
    def index():
        return redirect('/api')
        
    return app
