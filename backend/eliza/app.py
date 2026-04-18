from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
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

    @app.route('/api/weather/live', methods=['GET'])
    def get_live_weather():
        try:
            # Production integration using OpenWeatherMap One Call API for comprehensive data
            api_key = os.environ.get('WEATHER_API_KEY')
            # Using specific city coordinates to ensure valid response, defaulting to central coordinates if location not specified
            lat, lon = "38.8951", "-77.0364" 
            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return jsonify(response.json()), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch live weather data", "details": str(e)}), 502

    @app.route('/api/hazards/live', methods=['GET'])
    def get_live_hazards():
        try:
            # Production endpoint for USGS earthquake/hazard feed
            url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return jsonify(response.json()), 200
        except Exception as e:
            return jsonify({"error": "Failed to fetch live hazard data", "details": str(e)}), 502

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)