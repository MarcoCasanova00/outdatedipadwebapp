#!/usr/bin/env python3
"""
iPad Mini 2 - Simple Web Server
Todo List + RSS Feed
Runs on Void Linux
"""

import http.server
import socketserver
import json
import socket
import feedparser
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 8000
HOST = "0.0.0.0"
BASE_DIR = Path(__file__).parent

# RSS Feeds
RSS_FEEDS = [
    "https://news.ycombinator.com/rss",
    "https://feeds.arstechnica.com/arstechnica/index",
]

# In-memory storage
todos = {}


class WebHandler(http.server.SimpleHTTPRequestHandler):
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        # API: Get todos
        if path == "/api/todos":
            self.json_response({"todos": todos})
            return
        
        # API: Get RSS
        if path == "/api/rss":
            self.get_rss()
            return
        
        # Root: Serve HTML
        if path == "/" or path == "/index.html":
            self.serve_html()
            return
        
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        data = json.loads(body) if body else {}
        
        # Add todo
        if path == "/api/todos/add":
            todo_id = str(datetime.now().timestamp())
            todos[todo_id] = {"text": data.get("text"), "done": False}
            self.json_response({"id": todo_id, "todos": todos})
            return
        
        # Toggle todo
        if path.startswith("/api/todos/toggle/"):
            todo_id = path.split("/")[-1]
            if todo_id in todos:
                todos[todo_id]["done"] = not todos[todo_id]["done"]
            self.json_response({"todos": todos})
            return
        
        # Delete todo
        if path.startswith("/api/todos/delete/"):
            todo_id = path.split("/")[-1]
            if todo_id in todos:
                del todos[todo_id]
            self.json_response({"todos": todos})
            return
        
        self.send_error(404)

    def get_rss(self):
        try:
            feeds = []
            for url in RSS_FEEDS:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:  # Top 3 per feed
                    feeds.append({
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "source": feed.feed.get("title", ""),
                    })
            self.json_response({"feeds": feeds})
        except Exception as e:
            self.json_response({"error": str(e)})

    def serve_html(self):
        html = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iPad Suite</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #fafafa; color: #212121; height: 100%; }
        body { display: flex; flex-direction: column; padding: 16px; gap: 16px; overflow-y: auto; }
        header { font-size: 28px; font-weight: 600; padding-bottom: 8px; border-bottom: 1px solid #e0e0e0; }
        .card { background: #fff; border-radius: 12px; padding: 16px; border: 1px solid #e0e0e0; }
        .card h2 { font-size: 18px; margin-bottom: 12px; }
        input { width: 100%; padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 8px; font-size: 14px; }
        button { padding: 10px 16px; background: #2196F3; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; }
        button:active { background: #1976D2; }
        .todo-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: #f5f5f5; border-radius: 8px; margin-bottom: 8px; }
        .todo-item input[type="checkbox"] { width: 20px; height: 20px; cursor: pointer; }
        .todo-item.done label { text-decoration: line-through; opacity: 0.6; }
        .todo-item label { flex: 1; cursor: pointer; }
        .todo-item .del { background: #f44336; padding: 4px 8px; font-size: 12px; }
        .feed-item { padding: 12px; border-left: 4px solid #2196F3; margin-bottom: 12px; }
        .feed-item strong { display: block; margin-bottom: 4px; }
        .feed-item small { color: #757575; display: block; }
        .feed-item a { color: #2196F3; text-decoration: none; }
        @media (prefers-color-scheme: dark) {
            html, body { background: #121212; color: #fff; }
            .card { background: #1e1e1e; border-color: #333; }
            input { background: #1e1e1e; color: #fff; border-color: #333; }
            .todo-item { background: #333; }
            .feed-item { border-left-color: #64B5F6; }
        }
    </style>
</head>
<body>
    <header>📱 Suite</header>
    
    <div class="card">
        <h2>✅ Todo List</h2>
        <div style="display: flex; gap: 8px;">
            <input id="todoInput" placeholder="Nuovo task...">
            <button onclick="addTodo()">Add</button>
        </div>
        <div id="todoList"></div>
    </div>
    
    <div class="card">
        <h2>📰 RSS Feeds</h2>
        <div id="feedList" style="font-size: 13px;">Caricamento...</div>
    </div>

    <script>
        async function loadTodos() {
            const res = await fetch('/api/todos');
            const data = await res.json();
            const list = document.getElementById('todoList');
            
            if (Object.keys(data.todos).length === 0) {
                list.innerHTML = '<p style="color: #999; text-align: center;">Nessun task</p>';
                return;
            }
            
            list.innerHTML = Object.entries(data.todos)
                .map(([id, todo]) => `
                    <div class="todo-item ${todo.done ? 'done' : ''}">
                        <input type="checkbox" ${todo.done ? 'checked' : ''} onchange="toggleTodo('${id}')">
                        <label for="todo-${id}">${todo.text}</label>
                        <button class="del" onclick="deleteTodo('${id}')">✕</button>
                    </div>
                `)
                .join('');
        }
        
        async function addTodo() {
            const input = document.getElementById('todoInput');
            if (!input.value.trim()) return;
            
            await fetch('/api/todos/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({text: input.value})
            });
            
            input.value = '';
            loadTodos();
        }
        
        async function toggleTodo(id) {
            await fetch(`/api/todos/toggle/${id}`, {method: 'POST'});
            loadTodos();
        }
        
        async function deleteTodo(id) {
            await fetch(`/api/todos/delete/${id}`, {method: 'POST'});
            loadTodos();
        }
        
        async function loadFeeds() {
            try {
                const res = await fetch('/api/rss');
                const data = await res.json();
                const list = document.getElementById('feedList');
                
                if (data.error) {
                    list.innerHTML = `<p style="color: #f44336;">Errore: ${data.error}</p>`;
                    return;
                }
                
                list.innerHTML = data.feeds
                    .map(f => `
                        <div class="feed-item">
                            <strong>${f.title}</strong>
                            <small>${f.source}</small>
                            <a href="${f.link}" target="_blank">Leggi →</a>
                        </div>
                    `)
                    .join('');
            } catch (e) {
                document.getElementById('feedList').innerHTML = '<p style="color: #f44336;">Errore caricamento feed</p>';
            }
        }
        
        loadTodos();
        loadFeeds();
        setInterval(loadFeeds, 300000);  // Refresh ogni 5 minuti
    </script>
</body>
</html>"""
        
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())

    def json_response(self, data):
        response = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        print(f"[{self.client_address[0]}] {format % args}")


def main():
    print(f"\n🚀 iPad Web Server")
    print(f"📍 http://{HOST}:{PORT}")
    print(f"🌐 Accedi: http://{socket.gethostbyname(socket.gethostname())}:{PORT}")
    print(f"⚠️  Ctrl+C per fermare\n")
    
    with socketserver.TCPServer(("", PORT), WebHandler) as httpd:
        httpd.allow_reuse_address = True
        httpd.serve_forever()


if __name__ == "__main__":
    main()
