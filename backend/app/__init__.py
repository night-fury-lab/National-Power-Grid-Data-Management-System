from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
ma = Marshmallow()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Initialize extensions with app
    db.init_app(app)
    ma.init_app(app)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    with app.app_context():
        # Import routes here (inside app context)
        from app.routes import dashboard
        from app.routes import plants
        from app.routes import analytics
        from app.routes import regions
        from app.routes import alerts
        from app.routes import health
        from app.routes import db_admin
        
        # Register blueprints
        try:
            app.register_blueprint(dashboard.bp, url_prefix='/api/dashboard')
            print("✅ Dashboard routes registered")
        except Exception as e:
            print(f"⚠️ Error loading dashboard routes: {e}")
        
        try:
            app.register_blueprint(plants.bp, url_prefix='/api/plants')
            print("✅ Plants routes registered")
        except Exception as e:
            print(f"⚠️ Error loading plants routes: {e}")
        
        try:
            app.register_blueprint(analytics.bp, url_prefix='/api/analytics')
            print("✅ Analytics routes registered")
        except Exception as e:
            print(f"⚠️ Error loading analytics routes: {e}")
        
        try:
            app.register_blueprint(regions.bp, url_prefix='/api/regions')
            print("✅ Regions routes registered")
        except Exception as e:
            print(f"⚠️ Error loading regions routes: {e}")
        
        try:
            app.register_blueprint(alerts.bp, url_prefix='/api/alerts')
            print("✅ Alerts routes registered")
        except Exception as e:
            print(f"⚠️ Error loading alerts routes: {e}")
        try:
            app.register_blueprint(health.bp, url_prefix='/api/health')
            print("✅ Health routes registered")
        except Exception as e:
            print(f"⚠️ Error loading health routes: {e}")
        try:
            app.register_blueprint(db_admin.bp, url_prefix='/api/admin')
            print("✅ DB admin routes registered")
        except Exception as e:
            print(f"⚠️ Error loading db_admin routes: {e}")
    
    return app
