from typing import Dict, Any
import os
import base64

# Assuming a simple Flask app for the web interface
from flask import Flask, request, jsonify, render_template_string

class MobileDocumentCapture:
    """Provides a web-based interface for mobile document capture."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.upload_dir = self.config.get("mobile_upload_dir", "/tmp/mobile_uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
        self.app = Flask(__name__)
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/upload", methods=["GET", "POST"])
        def upload_file():
            if request.method == "POST":
                if "file" not in request.files:
                    return jsonify({"status": "error", "message": "No file part"}), 400
                file = request.files["file"]
                if file.filename == "":
                    return jsonify({"status": "error", "message": "No selected file"}), 400
                if file:
                    filename = os.path.join(self.upload_dir, file.filename)
                    file.save(filename)
                    # Here you would trigger the main workflow to process this document
                    # For now, just acknowledge the upload
                    return jsonify({"status": "success", "message": f"File {file.filename} uploaded successfully.", "path": filename}), 200
            
            # Simple HTML form for GET request
            return render_template_string("""
                <!doctype html>
                <title>Upload new File</title>
                <h1>Upload new File</h1>
                <form method=post enctype=multipart/form-data>
                  <input type=file name=file>
                  <input type=submit value=Upload>
                </form>
            """)

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        """Runs the Flask web server for mobile capture."""
        print(f"Mobile capture interface running on http://{host}:{port}/upload")
        self.app.run(host=host, port=port)


