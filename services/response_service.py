"""Standardized response formatting for API endpoints"""
from flask import jsonify


def success(data):
    """Return standard success response"""
    return jsonify({
        "status": "success",
        "data": data
    }), 200


def error(message, status_code=400):
    """Return standard error response with appropriate HTTP status code"""
    return jsonify({
        "status": "error",
        "message": message,
        "data": None
    }), status_code
