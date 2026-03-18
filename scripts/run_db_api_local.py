from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import sys
from pathlib import Path

# Add backend to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "backend/api/rest"))

import database_crud
import dashboard_handler
import ai_handler

class LocalDBHandler(BaseHTTPRequestHandler):
    def _handle_request(self):
        length = int(self.headers.get('content-length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else None
        
        path = self.path.split('?')[0]
        # Normalize: remove /api/v1 if present
        clean_path = path.replace('/api/v1', '')
        if not clean_path.startswith('/'): clean_path = '/' + clean_path
        
        resource = clean_path
        path_params = {}
        
        # Resource Mapping Logic
        parts = [p for p in clean_path.split('/') if p]
        if parts:
            base_resource = parts[0]
            if base_resource in ['patients', 'doctors', 'appointments', 'medications', 'surgeries', 'inventory', 'schedule', 'resources']:
                if len(parts) > 1:
                    resource = f'/{base_resource}/{{id}}'
                    path_params = {'id': parts[1]}
                else:
                    resource = f'/{base_resource}'
            elif base_resource == 'dashboard':
                resource = '/dashboard'
            elif base_resource == 'agent':
                resource = '/agent'
            elif base_resource == 'consultations':
                if len(parts) > 1 and parts[1] == 'start':
                    resource = '/consultations/start'
                else:
                    resource = '/consultations'
        
        event = {
            'httpMethod': self.command,
            'resource': resource,
            'path': path,
            'pathParameters': path_params,
            'queryStringParameters': dict(qc.split('=') for qc in self.path.split('?')[1].split('&') if '=' in qc) if '?' in self.path else {},
            'body': body,
            'headers': dict(self.headers)
        }
        
        # Routing to specific handlers
        if resource == '/dashboard':
            response = dashboard_handler.lambda_handler(event, None)
        elif resource == '/agent':
            response = ai_handler.lambda_handler(event, None)
        else:
            response = database_crud.lambda_handler(event, None)
        
        self.send_response(response['statusCode'])
        
        # Headers
        final_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
        
        if 'headers' in response:
            for k, v in response['headers'].items():
                low_k = k.lower()
                if low_k not in [h.lower() for h in final_headers.keys()]:
                    final_headers[k] = v
                elif low_k == "content-type":
                    final_headers["Content-Type"] = v

        for k, v in final_headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(response['body'].encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self): self._handle_request()
    def do_POST(self): self._handle_request()
    def do_PUT(self): self._handle_request()
    def do_DELETE(self): self._handle_request()

def main():
    # Set env vars for local DB
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_NAME'] = 'cdssdb'
    os.environ['DB_USER'] = 'postgres'
    os.environ['DB_PASS'] = 'password'
    os.environ['DB_PORT'] = '5433'
    
    port = 8080
    print(f"Starting Local CDSS API at http://localhost:{port}")
    httpd = HTTPServer(('', port), LocalDBHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
