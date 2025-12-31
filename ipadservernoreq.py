#!/usr/bin/env python3
import http.server
import socketserver
import json
import socket
import base64
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pathlib import Path

PORT = 8000
todos = {}
notes = {}
SMB_SHARE = "/mnt/smb"  # Cambia con il tuo path SMB

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/api/todos':
            self.send_json({'todos': todos})
        elif path == '/api/notes':
            self.send_json({'notes': notes})
        elif path == '/api/smb':
            self.browse_smb()
        elif path == '/':
            self.send_html()
        else:
            self.send_error(404)
    
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = json.loads(self.rfile.read(length)) if length else {}
        path = urlparse(self.path).path
        
        if path == '/api/todos':
            todo_id = str(datetime.now().timestamp())
            todos[todo_id] = {'text': data.get('text', ''), 'done': False, 'created': datetime.now().isoformat()}
            self.send_json({'todos': todos})
        
        elif path.startswith('/api/todos/'):
            action = path.split('/')[-1]
            todo_id = data.get('id')
            
            if action == 'toggle' and todo_id in todos:
                todos[todo_id]['done'] = not todos[todo_id]['done']
            elif action == 'delete' and todo_id in todos:
                del todos[todo_id]
            elif action == 'edit' and todo_id in todos:
                todos[todo_id]['text'] = data.get('text', todos[todo_id]['text'])
            
            self.send_json({'todos': todos})
        
        elif path == '/api/notes':
            note_id = str(datetime.now().timestamp())
            notes[note_id] = {
                'text': data.get('text', ''),
                'image': data.get('image'),
                'created': datetime.now().isoformat(),
                'comments': []
            }
            self.send_json({'notes': notes})
        
        elif path.startswith('/api/notes/'):
            action = path.split('/')[-1]
            note_id = data.get('id')
            
            if action == 'comment' and note_id in notes:
                notes[note_id]['comments'].append({
                    'text': data.get('text', ''),
                    'time': datetime.now().isoformat()
                })
            elif action == 'delete' and note_id in notes:
                del notes[note_id]
            
            self.send_json({'notes': notes})
    
    def browse_smb(self):
        try:
            if os.path.exists(SMB_SHARE):
                files = []
                for f in os.listdir(SMB_SHARE):
                    fpath = os.path.join(SMB_SHARE, f)
                    files.append({
                        'name': f,
                        'is_dir': os.path.isdir(fpath),
                        'size': os.path.getsize(fpath) if not os.path.isdir(fpath) else 0
                    })
                self.send_json({'files': files, 'path': SMB_SHARE})
            else:
                self.send_json({'error': 'SMB share not found. Mount it first!', 'path': SMB_SHARE})
        except Exception as e:
            self.send_json({'error': str(e)})
    
    def send_html(self):
        html = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width">
<title>iPad Suite</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,sans-serif;background:#f5f5f5;padding:10px}
.tabs{display:flex;gap:5px;margin-bottom:10px;border-bottom:2px solid #ddd}
.tab-btn{padding:10px 15px;background:none;border:none;cursor:pointer;font-weight:500;color:#999}
.tab-btn.active{color:#007AFF;border-bottom:3px solid #007AFF;margin-bottom:-2px}
.card{background:white;padding:15px;border-radius:10px;margin-bottom:10px}
input,textarea{width:100%;padding:10px;border:1px solid #ddd;border-radius:5px;margin-bottom:10px;font-family:inherit}
textarea{min-height:80px;resize:vertical}
button{background:#007AFF;color:white;border:none;padding:10px 15px;border-radius:5px;cursor:pointer;font-weight:500}
button:active{background:#005A9C}
.todo-item,.note-item{padding:10px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:start}
.todo-item.done{opacity:0.5;text-decoration:line-through}
.todo-text{flex:1}
.todo-actions{display:flex;gap:5px}
.todo-actions button{padding:5px 10px;font-size:12px}
.note-item{flex-direction:column}
.note-img{max-width:100%;max-height:200px;border-radius:5px;margin-top:10px}
.comment{background:#f9f9f9;padding:8px;border-radius:5px;margin-top:8px;font-size:12px}
.file-item{padding:10px;border:1px solid #ddd;border-radius:5px;margin-bottom:5px;display:flex;justify-content:space-between}
#content>div{display:none}
#content>div.active{display:block}
.hidden{display:none}
</style>
</head>
<body>
<div class="tabs">
<button class="tab-btn active" onclick="switchTab('todos')">✅ Todo</button>
<button class="tab-btn" onclick="switchTab('notes')">📝 Notes</button>
<button class="tab-btn" onclick="switchTab('smb')">📁 SMB</button>
</div>

<div id="content">

<!-- TODO -->
<div id="todos" class="active">
<div class="card">
<h2>Todo List</h2>
<input id="todoInput" placeholder="Nuovo task">
<button onclick="addTodo()">+ Add</button>
<div id="todoList"></div>
</div>
</div>

<!-- NOTES -->
<div id="notes">
<div class="card">
<h2>Create Note</h2>
<textarea id="noteText" placeholder="Testo"></textarea>
<input type="file" id="noteImage" accept="image/*" onchange="previewImage()">
<img id="preview" style="max-width:100%;margin:10px 0" class="hidden">
<button onclick="addNote()">+ Save Note</button>
<div id="notesList"></div>
</div>
</div>

<!-- SMB -->
<div id="smb">
<div class="card">
<h2>SMB Share Browser</h2>
<p style="font-size:12px;color:#666;margin-bottom:10px">Path: <span id="smbPath">/mnt/smb</span></p>
<button onclick="browseSMB()">🔄 Refresh</button>
<div id="fileList"></div>
</div>
</div>

</div>

<script>
function switchTab(tab){
  document.querySelectorAll('#content>div').forEach(d=>d.classList.remove('active'));
  document.getElementById(tab).classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  event.target.classList.add('active');
}

async function addTodo(){
  const input=document.getElementById('todoInput');
  if(!input.value.trim())return;
  await fetch('/api/todos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:input.value})});
  input.value='';
  loadTodos();
}

async function toggleTodo(id){
  await fetch('/api/todos/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  loadTodos();
}

async function editTodo(id){
  const newText=prompt('Edit:');
  if(!newText)return;
  await fetch('/api/todos/edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,text:newText})});
  loadTodos();
}

async function deleteTodo(id){
  await fetch('/api/todos/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  loadTodos();
}

async function loadTodos(){
  const r=await fetch('/api/todos');
  const d=await r.json();
  const list=document.getElementById('todoList');
  if(!Object.keys(d.todos).length){list.innerHTML='<p style="text-align:center;color:#999">No tasks</p>';return}
  list.innerHTML=Object.entries(d.todos).map(([id,t])=>`
    <div class="todo-item ${t.done?'done':''}">
      <div class="todo-text">
        <input type="checkbox" ${t.done?'checked':''} onchange="toggleTodo('${id}')"> ${t.text}
      </div>
      <div class="todo-actions">
        <button onclick="editTodo('${id}')">✏️</button>
        <button onclick="deleteTodo('${id}')">✕</button>
      </div>
    </div>
  `).join('');
}

function previewImage(){
  const file=document.getElementById('noteImage').files[0];
  if(!file)return;
  const reader=new FileReader();
  reader.onload=e=>{document.getElementById('preview').src=e.target.result;document.getElementById('preview').classList.remove('hidden')};
  reader.readAsDataURL(file);
}

async function addNote(){
  const text=document.getElementById('noteText').value;
  const image=document.getElementById('preview').src||null;
  if(!text.trim())return;
  await fetch('/api/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,image})});
  document.getElementById('noteText').value='';
  document.getElementById('noteImage').value='';
  document.getElementById('preview').classList.add('hidden');
  loadNotes();
}

async function addComment(id){
  const text=prompt('Comment:');
  if(!text)return;
  await fetch('/api/notes/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,text})});
  loadNotes();
}

async function deleteNote(id){
  await fetch('/api/notes/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  loadNotes();
}

async function loadNotes(){
  const r=await fetch('/api/notes');
  const d=await r.json();
  const list=document.getElementById('notesList');
  if(!Object.keys(d.notes).length){list.innerHTML='<p style="text-align:center;color:#999">No notes</p>';return}
  list.innerHTML=Object.entries(d.notes).map(([id,n])=>`
    <div class="note-item">
      <strong>${n.text}</strong>
      ${n.image?`<img src="${n.image}" class="note-img">':''}
      <small style="color:#999;margin-top:5px">${new Date(n.created).toLocaleString()}</small>
      <div style="margin-top:10px">
        ${n.comments.map(c=>`<div class="comment">${c.text} <small>${new Date(c.time).toLocaleTimeString()}</small></div>`).join('')}
        <button onclick="addComment('${id}')" style="font-size:12px;padding:5px 10px;margin-top:5px">💬 Comment</button>
      </div>
      <button onclick="deleteNote('${id}')" style="background:#f44336;margin-top:10px;font-size:12px">Delete</button>
    </div>
  `).join('');
}

async function browseSMB(){
  const r=await fetch('/api/smb');
  const d=await r.json();
  const list=document.getElementById('fileList');
  if(d.error){list.innerHTML=`<p style="color:red">${d.error}</p>`;return}
  list.innerHTML=d.files.map(f=>`
    <div class="file-item">
      <span>${f.is_dir?'📁':'📄'} ${f.name}</span>
      ${!f.is_dir?`<small>${(f.size/1024).toFixed(1)}KB</small>`:''}
    </div>
  `).join('');
}

loadTodos();
loadNotes();
browseSMB();
</script>
</body>
</html>'''
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

print('🚀 iPad Suite running on port 8000')
with socketserver.TCPServer(('', PORT), Handler) as httpd:
    httpd.allow_reuse_address = True
    httpd.serve_forever()
