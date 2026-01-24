from flask import Flask
from flask_cors import CORS
from routes.eliza_task import eliza_task_bp
from routes.eliza_scene import eliza_scene_bp

def create_app():
    """
    Application factory function that initializes the Flask app
    and registers the eliza_task and eliza_scene blueprints.
    """
    app = Flask(__name__)
    CORS(app)

    # Register blueprints with the /eliza prefix.
    app.register_blueprint(eliza_task_bp, url_prefix='/eliza')
    app.register_blueprint(eliza_scene_bp, url_prefix='/eliza')

    return app
