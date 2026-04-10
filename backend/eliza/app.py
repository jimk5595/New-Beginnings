from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from routes.eliza_task import eliza_task_bp
from routes.eliza_scene import eliza_scene_bp

load_dotenv()

def create_app():
    """
    Application factory function that initializes the Flask app
    and registers the eliza_task and eliza_scene blueprints.
    """
    app = Flask(__name__)
    CORS(app)

    # Configuration for production stability
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-fallback')

    # Register blueprints with the /eliza prefix.
    app.register_blueprint(eliza_task_bp, url_prefix='/eliza')
    app.register_blueprint(eliza_scene_bp, url_prefix='/eliza')

    @app.route('/health')
    def health_check():
        return {"status": "operational", "service": "eliza"}, 200

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)