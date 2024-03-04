from flask import request, jsonify
from functools import wraps

api_keys = {
    'API_KEY_1': 'admin',
    'API_KEY_2': 'user',
}

def authenticate_api_key(api_key):
    return api_key in api_keys

def authroize_role(api_key, required_role):
    return api_keys.get(api_key) == required_role

def api_key_required(required_role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key or not authenticate_api_key(api_key):
                return jsonify({'error': 'Invalid API key'}), 401
            if required_role and not authroize_role(api_key, required_role):
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator