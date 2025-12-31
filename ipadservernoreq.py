cat > ipadservernoreq.py << 'EOF'
#!/usr/bin/env python3
"""
iPad Mini 2 Server - ZERO dipendenze
Todo List + System Info
"""

import http.server
import socketserver
import json
import socket
import os
from urllib.parse import urlparse
from datetime import datetime

PORT = 8000
HOST = "0.0.0.0"
todos = {}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/api/todos':
            self.send_json({'todos': todos})
        elif path == '/api/system':
            self.send_system_info()
        elif path == '/':
            self.send_html()
        else:
            self.send_error(404)
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(content_length))
        
        if urlparse(self.path).path == '/api/todos':
            todo_id = str(datetime.now().timestamp())
            todos[todo_id] = {'text': data['text'], 'done': False}
            self.send_json({'todos': todos})
    
    def send_system_info(self):
        try:
            data = {
                'hostname': socket.gethostname(),
                'uptime': os.popen('uptime').read().strip(),
                'disk': os.popen('df -h / | tail -1 | awk "{print $5}"').read().strip()
            }
        except:
            data = {'hostname': 'unknown'}
        self.send_json(data)
    
    def send_html(self):
        html = '''<!DOCTYPE html>
<html>
<head>
<title>iPad Suite</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width">
<style>
body{font-family:-apple-system,sans-serif;margin:20px;background:#f5f5f5;}
.card{background:white;padding:20px;margin:10px 0;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}
input{width:70%;padding:10px;border:1px solid #ddd;border-radius:5px;}
button{padding:10px 20px;background:#007AFF;color:white;border:none;border-radius:5px;cursor:pointer;}
.todo{display:flex;align-items:center;gap:10px;padding:10px;border-bottom:1px solid #eee;}
.todo.done{opacity:0.5;text-decoration:line-through;}
h2{margin-bottom:15px;}
#sys{padding:10px;background:#f0f0f0;border-radius:5px;font-size:14px;}
</style>
</head>
<body>
<div class="card">
<h2>✅ Todo List</h2>
<input id="input" placeholder="Nuovo task">
<button onclick="addTodo()">+</button>
<div id="list"></div>
</div>
<div class="card">
<h2>💻 Server Status</h2>
<div id="sys">Caricamento...</div>
</div>
<script>
async function load(){
const todos=await(await fetch('/api/todos')).json();
document.getElementById('list').innerHTML=Object.entries(todos.todos).map(([id,t])=>
`<div class="todo ${t.done?'done':''}">
<input type="checkbox" ${t.done?'checked':''} onchange="toggle('${id}')">
<span>${t.text}</span>
<button onclick="deleteTodo('${id}')" style="background:#FF3B30;padding:5px 10px;font-size:12px;">✕</button>
</div>`).join('')||'<p style="color:#999;text-align:center;">Nessun task</p>';

const sys=await(await fetch('/api/system')).json();
document.getElementById('sys').innerHTML=`Hostname: ${sys.hostname}<br>Disk: ${sys.disk||'?'}`;
}
async function addTodo(){
const input=document.getElementById('input');
if(!input.value.trim())return;
await fetch('/api/todos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:input.value})});
input.value='';
load();
}
async function deleteTodo(id){
await fetch(`/api/todos/${id}/delete`,{method:'POST'});
load();
}
load();
setInterval(load,5000);
</script>
</body></html>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_json(self, data):
        resp = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(resp)

if __name__ == '__main__':
    print('🚀 iPad Server')
    print(f'📍 http://localhost:{PORT}')
    print(f'🌐 http://{socket.gethostbyname(socket.gethostname())}:{PORT}')
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        httpd.allow_reuse_address = True
        httpd.serve_forever()
EOF
