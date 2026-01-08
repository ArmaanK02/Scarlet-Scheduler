import os

class Config:
    """
    Centralized configuration management.
    """
    # File Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_FILE_PATH = os.path.join(BASE_DIR, 'rutgers_scheduler_data.json')
    
    # Scheduling Parameters
    MAX_SCHEDULES = 50
    SEMESTER_CODE = "92025"
    CAMPUS_CODE = "NB"
    LEVEL_CODE = "U,G"

    # AI Configuration
    # List of keys for fallback support
    GEMINI_API_KEYS = [
        os.environ.get("GEMINI_API_KEY_1", "AIzaSyDEA479CZRhovLzdfx1XfQvdcrIrUixJ9o"),
        os.environ.get("GEMINI_API_KEY_2", "AIzaSyCklokl5pn_F401zA1tQVVRLn0sWAc3w1s")
    ]

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'production':
        return ProductionConfig
    return DevelopmentConfig