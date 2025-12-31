#!/usr/bin/env python3
import http.server
import socketserver
import json
import socket
from urllib.parse import urlparse
from datetime import datetime

PORT = 8000
todos = {}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/todos':
            self.send_json({'todos': todos})
        elif path == '/':
            self.send_html()
        else:
            self.send_error(404)
    
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(length))
        todo_id = str(datetime.now().timestamp())
        todos[todo_id] = {'text': data['text'], 'done': False}
        self.send_json({'todos': todos})
    
    def send_html(self):
        html = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width"><title>iPad</title><style>body{font-family:-apple-system;margin:20px;background:#f5f5f5}.card{background:white;padding:20px;border-radius:10px}input{width:100%;padding:10px;margin:10px 0}button{background:#007AFF;color:white;border:none;padding:10px;border-radius:5px;cursor:pointer}.todo{padding:10px;border-bottom:1px solid #eee}</style></head><body><div class="card"><h1>Todo</h1><input id="i" placeholder="Task"><button onclick="add()">+</button><div id="list"></div></div><script>async function load(){const r=await fetch('/api/todos');const d=await r.json();document.getElementById('list').innerHTML=Object.entries(d.todos).map(([id,t])=>'<div class="todo">'+t.text+'</div>').join('')}async function add(){await fetch('/api/todos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:document.getElementById('i').value})});document.getElementById('i').value='';load()}load()</script></body></html>'''
        self.send_response(200)
        self.send_header('Content-Type','text/html;charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def send_json(self, data):
        r = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type','application/json')
        self.end_headers()
        self.wfile.write(r)

print(f'Server: http://{socket.gethostbyname(socket.gethostname())}:8000')
with socketserver.TCPServer(('', PORT), Handler) as httpd:
    httpd.allow_reuse_address = True
    httpd.serve_forever()
