#!/usr/bin/env python3
"""TTS Reader — Cloud version for Render deployment."""

import http.server, json, os, asyncio, hashlib, tempfile

CACHE_DIR = os.path.join(tempfile.gettempdir(), "tts_cache")
PORT = int(os.environ.get("PORT", 10000))

VOICES = {
    "urdu-female":   "ur-PK-UzmaNeural",
    "urdu-male":     "ur-PK-AsadNeural",
    "english-female": "en-GB-SoniaNeural",
    "english-male":   "en-GB-RyanNeural",
}

HTML = r"""<!DOCTYPE html>
<html lang="ur" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TTS Reader</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0a0a0a; color: #e0e0e0;
    min-height: 100vh; -webkit-tap-highlight-color: transparent; }

  .container { max-width: 800px; margin: 0 auto; padding: 16px; }

  h1 { text-align: center; font-size: 1.4rem; margin: 12px 0 4px; color: #ff5252; }
  .subtitle { text-align: center; color: #777; font-size: 0.8rem; margin-bottom: 16px; }

  .controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: center;
    background: #111; border-radius: 12px; padding: 12px 14px; margin-bottom: 14px; border: 1px solid #3a1a1a; }
  .controls label { font-size: 0.75rem; color: #aaa; }
  .controls select, .controls input[type=range] { background: #1a1a1a; color: #fff; border: 1px solid #3a1a1a;
    border-radius: 6px; padding: 5px 8px; font-size: 0.85rem; }
  .controls select { cursor: pointer; }
  .speed-group { display: flex; align-items: center; gap: 6px; }
  .speed-val { font-size: 0.85rem; color: #ff5252; min-width: 38px; text-align: center; font-weight: 600; }

  .auto-toggle { display: flex; align-items: center; gap: 6px; }
  .auto-toggle label { font-size: 0.75rem; color: #aaa; cursor: pointer; }
  .toggle-btn { background: #1a1a1a; border: 1px solid #3a1a1a; color: #666; padding: 5px 12px;
    border-radius: 6px; cursor: pointer; font-size: 0.8rem; font-weight: 600; transition: all 0.15s; }
  .toggle-btn.on { background: #3a1111; border-color: #e53935; color: #ff5252; }

  .input-area { margin-bottom: 14px; }
  .tab-bar { display: flex; gap: 0; }
  .tab { padding: 7px 16px; background: #111; border: 1px solid #1a1a1a; cursor: pointer;
    font-size: 0.8rem; color: #888; border-bottom: none; border-radius: 8px 8px 0 0; }
  .tab.active { background: #181818; color: #fff; border-color: #3a1a1a; }
  .input-box { background: #181818; border: 1px solid #3a1a1a; border-radius: 0 8px 8px 8px; padding: 12px; }
  textarea { width: 100%; height: 100px; background: #111; color: #e0e0e0; border: 1px solid #2a1515;
    border-radius: 8px; padding: 10px; font-size: 1rem; resize: vertical; font-family: inherit; direction: auto; }
  textarea:focus { border-color: #5a2a2a; outline: none; }
  textarea::placeholder { color: #555; }
  .file-upload { display: flex; align-items: center; gap: 12px; }
  .file-upload input[type=file] { display: none; }
  .upload-btn { background: #e53935; color: #fff; border: none; padding: 8px 18px; border-radius: 8px;
    cursor: pointer; font-weight: 600; font-size: 0.85rem; }
  .upload-btn:hover { background: #ff5252; }
  .file-name { color: #888; font-size: 0.85rem; }

  .load-btn { display: block; margin: 10px auto 0; background: #e53935; color: #fff; border: none;
    padding: 10px 32px; border-radius: 8px; cursor: pointer; font-weight: 700; font-size: 0.95rem; }
  .load-btn:hover { background: #ff5252; }
  .load-btn:disabled { background: #222; color: #555; cursor: not-allowed; }

  .lines-area { margin-top: 6px; }
  .line-row { display: flex; align-items: flex-start; gap: 8px; padding: 10px 12px; margin: 2px 0;
    border-radius: 8px; cursor: pointer; transition: background 0.15s, border-color 0.15s;
    border: 1px solid #1a1a1a; }
  .line-row:hover { background: #1a1010; border-color: #5a2a2a; }
  .line-row.playing { background: #2a1111; border-color: #e53935; }
  .line-row.loading { background: #1a1508; border-color: #5a4a1a; }
  .line-num { min-width: 28px; text-align: right; color: #555; font-size: 0.75rem; padding-top: 3px;
    user-select: none; }
  .line-text { flex: 1; font-size: 1rem; line-height: 1.7; direction: auto; color: #ddd; }
  .line-row:hover .line-text { color: #fff; }
  .line-row.playing .line-text { color: #ff5252; font-weight: 500; }

  .play-icon { font-size: 0.85rem; padding-top: 3px; min-width: 18px; color: #555; }
  .line-row:hover .play-icon { color: #ff5252; }
  .line-row.playing .play-icon { color: #ff5252; }

  .empty-state { text-align: center; color: #555; padding: 50px 20px; font-size: 0.9rem; }

  .stop-btn { display: none; margin: 10px auto; background: #e53935; color: #fff; border: none;
    padding: 8px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.85rem;
    border: 1px solid #ff5252; }
  .stop-btn.visible { display: block; }
  .stop-btn:hover { background: #ff5252; }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #0a0a0a; }
  ::-webkit-scrollbar-thumb { background: #3a1a1a; border-radius: 3px; }
  input[type=range] { accent-color: #e53935; }

  @media (max-width: 600px) {
    .container { padding: 10px; }
    h1 { font-size: 1.2rem; }
    .controls { gap: 6px; padding: 10px; }
    textarea { height: 80px; font-size: 0.95rem; }
    .line-text { font-size: 0.95rem; }
  }
</style>
</head>
<body>
<div class="container">
  <h1>TTS Reader</h1>
  <p class="subtitle">Tap any line to hear it read aloud</p>

  <div class="controls">
    <div>
      <label>Language</label><br>
      <select id="lang">
        <option value="urdu">اردو Urdu</option>
        <option value="english">English</option>
      </select>
    </div>
    <div>
      <label>Voice</label><br>
      <select id="voice">
        <option value="female">Female</option>
        <option value="male">Male</option>
      </select>
    </div>
    <div class="speed-group">
      <div>
        <label>Speed</label><br>
        <input type="range" id="speed" min="0.5" max="3" step="0.25" value="1">
      </div>
      <span class="speed-val" id="speedVal">1x</span>
    </div>
    <div class="auto-toggle">
      <label>Auto</label><br>
      <button class="toggle-btn" id="autoBtn">OFF</button>
    </div>
  </div>

  <div class="input-area">
    <div class="tab-bar">
      <div class="tab active" data-tab="paste">Paste Text</div>
      <div class="tab" data-tab="file">Upload File</div>
    </div>
    <div class="input-box">
      <div id="tab-paste">
        <textarea id="textInput" placeholder="Paste Urdu or English text here..."></textarea>
      </div>
      <div id="tab-file" style="display:none">
        <div class="file-upload">
          <label class="upload-btn" for="fileInput">Choose PDF / MD / TXT</label>
          <input type="file" id="fileInput" accept=".pdf,.md,.txt,.text">
          <span class="file-name" id="fileName">No file selected</span>
        </div>
      </div>
    </div>
    <button class="load-btn" id="loadBtn">Load Text</button>
  </div>

  <button class="stop-btn" id="stopBtn">Stop</button>

  <div class="lines-area" id="linesArea">
    <div class="empty-state">Paste some text and tap Load to get started</div>
  </div>
</div>

<script>
let lines = [];
let currentAudio = null;
let isPlaying = false;
let playId = 0;
let autoContinue = false;

const autoBtn = document.getElementById('autoBtn');
autoBtn.addEventListener('click', () => {
  autoContinue = !autoContinue;
  autoBtn.textContent = autoContinue ? 'ON' : 'OFF';
  autoBtn.classList.toggle('on', autoContinue);
});

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-paste').style.display = tab.dataset.tab === 'paste' ? '' : 'none';
    document.getElementById('tab-file').style.display = tab.dataset.tab === 'file' ? '' : 'none';
  });
});

document.getElementById('fileInput').addEventListener('change', e => {
  document.getElementById('fileName').textContent = e.target.files[0]?.name || 'No file selected';
});

const speedSlider = document.getElementById('speed');
const speedVal = document.getElementById('speedVal');
speedSlider.addEventListener('input', () => { speedVal.textContent = speedSlider.value + 'x'; });

document.getElementById('loadBtn').addEventListener('click', async () => {
  const btn = document.getElementById('loadBtn');
  btn.disabled = true; btn.textContent = 'Loading...';
  const activeTab = document.querySelector('.tab.active').dataset.tab;
  let text = '';
  if (activeTab === 'paste') {
    text = document.getElementById('textInput').value;
  } else {
    const file = document.getElementById('fileInput').files[0];
    if (!file) { btn.disabled = false; btn.textContent = 'Load Text'; return; }
    if (file.name.endsWith('.pdf')) {
      const fd = new FormData(); fd.append('file', file);
      const r = await fetch('/api/extract-pdf', { method: 'POST', body: fd });
      text = (await r.json()).text || '';
    } else { text = await file.text(); }
  }
  lines = text.split('\n').map((l,i) => ({num:i+1, text:l.trim()})).filter(l => l.text.length > 0);
  renderLines();
  btn.disabled = false; btn.textContent = 'Load Text';
});

function renderLines() {
  const area = document.getElementById('linesArea');
  if (!lines.length) { area.innerHTML = '<div class="empty-state">No text found</div>'; return; }
  area.innerHTML = lines.map((l,i) => `
    <div class="line-row" data-idx="${i}">
      <span class="play-icon">▶</span>
      <span class="line-num">${i+1}</span>
      <span class="line-text">${escHtml(l.text)}</span>
    </div>`).join('');
  area.querySelectorAll('.line-row').forEach(row => {
    row.addEventListener('click', e => {
      e.preventDefault();
      const idx = parseInt(row.dataset.idx);
      stopPlayback();
      if (autoContinue) { const ids=[]; for(let i=idx;i<lines.length;i++) ids.push(i); playLines(ids); }
      else { playLines([idx]); }
    });
    row.addEventListener('contextmenu', e => {
      e.preventDefault();
      const idx = parseInt(row.dataset.idx);
      stopPlayback();
      const ids=[]; for(let i=idx;i<lines.length;i++) ids.push(i); playLines(ids);
    });
  });
}

function escHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

async function playLines(indices) {
  const myId = ++playId;
  isPlaying = true;
  document.getElementById('stopBtn').classList.add('visible');
  for (const idx of indices) {
    if (!isPlaying || playId !== myId) break;
    const row = document.querySelector(`.line-row[data-idx="${idx}"]`);
    document.querySelectorAll('.line-row').forEach(r => r.classList.remove('playing','loading'));
    if (row) { row.classList.add('loading'); row.scrollIntoView({behavior:'smooth',block:'center'}); }
    const voiceKey = document.getElementById('lang').value + '-' + document.getElementById('voice').value;
    try {
      const resp = await fetch('/api/tts', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({text:lines[idx].text, voice:voiceKey, speed:parseFloat(speedSlider.value)})
      });
      if (!isPlaying || playId !== myId) break;
      if (!resp.ok) continue;
      const url = URL.createObjectURL(await resp.blob());
      if (row) { row.classList.remove('loading'); row.classList.add('playing'); }
      await new Promise((res,rej) => {
        currentAudio = new Audio(url);
        currentAudio.onended = res; currentAudio.onerror = rej;
        currentAudio.play().catch(rej);
      });
      URL.revokeObjectURL(url);
      if (row) row.classList.remove('playing');
    } catch(e) {
      if (row) row.classList.remove('playing','loading');
      if (!isPlaying || playId !== myId) break;
    }
  }
  if (playId === myId) {
    isPlaying = false;
    document.getElementById('stopBtn').classList.remove('visible');
    document.querySelectorAll('.line-row').forEach(r => r.classList.remove('playing','loading'));
  }
}

function stopPlayback() {
  isPlaying = false; playId++;
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  document.getElementById('stopBtn').classList.remove('visible');
  document.querySelectorAll('.line-row').forEach(r => r.classList.remove('playing','loading'));
}

document.getElementById('stopBtn').addEventListener('click', stopPlayback);
document.addEventListener('keydown', e => { if (e.key === 'Escape') stopPlayback(); });
</script>
</body>
</html>"""


def speed_to_rate(speed):
    pct = round((speed - 1.0) * 100)
    return f"{pct:+d}%"


def cache_path(text, voice, speed):
    os.makedirs(CACHE_DIR, exist_ok=True)
    h = hashlib.md5(f"{text}|{voice}|{speed}".encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"tts_{h}.mp3")


def generate_tts(text, voice_key, speed):
    import edge_tts
    voice = VOICES.get(voice_key, VOICES["urdu-female"])
    rate = speed_to_rate(speed)
    mp3 = cache_path(text, voice, rate)
    if not os.path.exists(mp3):
        async def _gen():
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(mp3)
        asyncio.run(_gen())
    return mp3


def extract_pdf_text(data):
    import fitz
    doc = fitz.open(stream=data, filetype="pdf")
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/tts":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            text = body.get("text", "")
            voice_key = body.get("voice", "urdu-female")
            speed = body.get("speed", 1.0)
            try:
                mp3 = generate_tts(text, voice_key, speed)
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(mp3, "rb") as f:
                    self.wfile.write(f.read())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == "/api/extract-pdf":
            content_type = self.headers.get("Content-Type", "")
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            boundary = content_type.split("boundary=")[1].encode() if "boundary=" in content_type else b""
            parts = raw.split(b"--" + boundary)
            pdf_data = None
            for part in parts:
                if b"filename=" in part:
                    idx = part.find(b"\r\n\r\n")
                    if idx != -1:
                        pdf_data = part[idx + 4:]
                        if pdf_data.endswith(b"\r\n"):
                            pdf_data = pdf_data[:-2]
            text = ""
            if pdf_data:
                try:
                    text = extract_pdf_text(pdf_data)
                except Exception as e:
                    text = f"Error: {e}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"text": text}).encode())
        else:
            self.send_error(404)


if __name__ == "__main__":
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"TTS Reader running on port {PORT}")
    server.serve_forever()
