from flask import Blueprint, jsonify
from app.utils.database import DatabaseHelper

bp = Blueprint('health', __name__)


@bp.route('/', methods=['GET'])
def health_check():
    """Health check endpoint. Returns app and DB status."""
    try:
        db_ok = False
        try:
            db_ok = DatabaseHelper.test_connection()
        except Exception:
            db_ok = False

        return jsonify({'success': True, 'status': 'ok', 'db': bool(db_ok)}), 200
    except Exception as e:
        return jsonify({'success': False, 'status': 'error', 'error': str(e)}), 500
