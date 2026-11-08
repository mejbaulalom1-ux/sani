import os
from functools import wraps

from flask import (Flask, abort, flash, redirect, render_template_string,
                   request, send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# ============ APNI SETTINGS YAHAN BADLEIN ============
# role "admin"  -> upload, view, download, DELETE
# role "friend" -> upload, view, download (delete NAHI)
# Dosto ke naam aur password badalkar apne hisaab se likhein, aur zaroorat ho to aur jodein.
USERS = {
    "sani":   {"password": "201103",        "role": "admin"},
    "dost1":  {"password": "dost1-password", "role": "friend"},
    "dost2":  {"password": "dost2-password", "role": "friend"},
}
MAX_UPLOAD_MB = 500                     # ek file ki sabse badi size
SITE_NAME = "Sani Storage"              # logo ke saath dikhne wala naam, yahan badal sakte hain
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
AVATAR_DIR = os.path.join(BASE_DIR, "avatars")   # profile photos yahan, files wale list se alag
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AVATAR_DIR, exist_ok=True)

IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
VIDEO_EXT = {"mp4", "webm", "mov", "mkv"}
PREVIEW_EXT = IMAGE_EXT | VIDEO_EXT | {"pdf", "txt", "mp3", "wav"}
AVATAR_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_AVATAR_MB = 5                       # profile photo ki sabse badi size

app = Flask(__name__)
app.secret_key = os.urandom(24)  # server restart par dobara login karna hoga
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Password seedha store nahi hota, uska hash store hota hai
USER_HASHES = {name: generate_password_hash(info["password"]) for name, info in USERS.items()}


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def ext_of(name):
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def unique_name(name):
    base, dot, ext = name.rpartition(".")
    if not dot:
        base, ext = name, ""
    candidate, i = name, 1
    while os.path.exists(os.path.join(UPLOAD_DIR, candidate)):
        candidate = f"{base}_{i}.{ext}" if ext else f"{base}_{i}"
        i += 1
    return candidate


PAGE = """
{% macro logo(size) -%}
<svg width="{{ size }}" height="{{ size }}" viewBox="0 0 48 48" aria-hidden="true">
  <defs>
    <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#38bdf8"/>
      <stop offset="1" stop-color="#6366f1"/>
    </linearGradient>
  </defs>
  <rect width="48" height="48" rx="12" fill="url(#lg)"/>
  <path d="M12 17a3 3 0 0 1 3-3h6l3 3h9a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H15a3 3 0 0 1-3-3z"
        fill="#ffffff" fill-opacity="0.95"/>
  <path d="M24 31v-8M24 23l-3.5 3.5M24 23l3.5 3.5" stroke="#6366f1" stroke-width="2.4"
        stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>
{%- endmacro %}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ site_name }}</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect width='48' height='48' rx='12' fill='%236366f1'/%3E%3Cpath d='M12 17a3 3 0 0 1 3-3h6l3 3h9a3 3 0 0 1 3 3v12a3 3 0 0 1-3 3H15a3 3 0 0 1-3-3z' fill='white'/%3E%3C/svg%3E">
<style>
  * { box-sizing: border-box; }
  body { font-family: Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; }
  header { display:flex; justify-content:space-between; align-items:center;
           padding:16px 24px; background:#1e293b; }
  header h1 { margin:0; font-size:1.2rem; color:#38bdf8; }
  main { max-width:1000px; margin:0 auto; padding:24px 16px; }
  .box { background:#1e293b; padding:20px; border-radius:12px; margin-bottom:24px; }
  input[type=text], input[type=password] { width:100%; padding:10px; margin:6px 0 14px;
        border-radius:8px; border:1px solid #334155; background:#0f172a; color:#e2e8f0; }
  input[type=file] { margin:8px 0; color:#e2e8f0; }
  button, .btn { background:#38bdf8; color:#0f172a; border:0; padding:8px 14px;
        border-radius:8px; cursor:pointer; font-weight:bold; text-decoration:none;
        display:inline-block; font-size:0.9rem; }
  .danger { background:#f87171; }
  .userbox { display:flex; align-items:center; gap:14px; }
  details.menu { position:relative; }
  details.menu summary { list-style:none; cursor:pointer; display:flex; align-items:center;
                         gap:10px; color:#94a3b8; font-size:0.9rem; }
  details.menu summary::-webkit-details-marker { display:none; }
  .avatar { width:38px; height:38px; border-radius:50%; object-fit:cover; border:2px solid #38bdf8; }
  .avatar.ph { display:flex; align-items:center; justify-content:center; border:0; color:#fff;
               font-weight:bold; background:linear-gradient(135deg,#38bdf8,#6366f1); }
  .menu-box { position:absolute; right:0; top:48px; background:#1e293b; border:1px solid #334155;
              border-radius:10px; padding:12px; min-width:210px; z-index:5; }
  .menu-box form { margin:0; }
  .brand { display:flex; align-items:center; gap:12px; text-decoration:none; }
  .brand-name { font-size:1.25rem; font-weight:bold; color:#f1f5f9; letter-spacing:0.3px; line-height:1.1; }
  .brand-sub { font-size:0.72rem; color:#94a3b8; letter-spacing:1px; text-transform:uppercase; margin-top:3px; }
  .brand-big { text-align:center; margin-bottom:18px; }
  .brand-big svg { filter:drop-shadow(0 6px 14px rgba(99,102,241,0.45)); }
  .brand-big .brand-name { font-size:1.5rem; margin-top:10px; }
  .dropzone { border:2px dashed #475569; border-radius:12px; padding:24px; text-align:center;
              margin-bottom:14px; transition:0.15s; }
  .dropzone.over { border-color:#38bdf8; background:#0f172a; }
  .dz-title { font-weight:bold; }
  .dz-sub { color:#94a3b8; margin:6px 0 10px; font-size:0.9rem; }
  .pick { display:inline-block; background:#334155; color:#e2e8f0; padding:10px 20px;
          border-radius:8px; cursor:pointer; font-weight:bold; }
  .pick:hover { background:#475569; }
  .file-list { color:#94a3b8; font-size:0.85rem; margin-top:14px; line-height:1.6;
               max-height:140px; overflow:auto; word-break:break-all; }
  button:disabled { opacity:0.45; cursor:not-allowed; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:16px; }
  .item { background:#1e293b; border-radius:12px; padding:12px; }
  .thumb { height:140px; display:flex; align-items:center; justify-content:center;
           background:#0f172a; border-radius:8px; overflow:hidden; margin-bottom:8px; }
  .thumb img, .thumb video { max-width:100%; max-height:100%; }
  .name { word-break:break-all; font-size:0.9rem; }
  .meta { color:#94a3b8; font-size:0.8rem; margin:4px 0 10px; }
  .actions { display:flex; gap:6px; flex-wrap:wrap; }
  .actions form { margin:0; }
  .flash { background:#334155; padding:10px 14px; border-radius:8px; margin-bottom:16px; }
  a.link { color:#38bdf8; }
</style>
</head>
<body>
{% if logged_in %}
<header>
  <a class="brand" href="{{ url_for('home') }}">
    {{ logo(40) }}
    <div>
      <div class="brand-name">{{ site_name }}</div>
      <div class="brand-sub">Personal cloud</div>
    </div>
  </a>
  <div class="userbox">
    <details class="menu">
      <summary>
        {% if avatar_url %}<img class="avatar" src="{{ avatar_url }}" alt="">
        {% else %}<span class="avatar ph">{{ username[:1]|upper }}</span>{% endif %}
        <span>{{ username }} ({{ 'Admin' if is_admin else 'Friend' }})</span>
      </summary>
      <div class="menu-box">
        <form method="post" action="{{ url_for('set_avatar') }}" enctype="multipart/form-data">
          <label class="btn" style="display:block;text-align:center;cursor:pointer;">
            {{ 'Photo badlein' if avatar_url else 'Profile photo lagayein' }}
            <input type="file" name="photo" accept="image/png,image/jpeg,image/gif,image/webp"
                   hidden onchange="this.form.submit()">
          </label>
        </form>
        {% if avatar_url %}
        <form method="post" action="{{ url_for('remove_avatar') }}">
          <button class="danger" type="submit" style="width:100%;margin-top:8px;">Photo hatayein</button>
        </form>
        {% endif %}
      </div>
    </details>
    <a class="btn" href="{{ url_for('logout') }}">Logout</a>
  </div>
</header>
{% endif %}
<main>
  {% for m in get_flashed_messages() %}<div class="flash">{{ m }}</div>{% endfor %}

  {% if not logged_in %}
  <div class="box" style="max-width:380px;margin:60px auto;">
    <div class="brand-big">
      {{ logo(64) }}
      <div class="brand-name">{{ site_name }}</div>
      <div class="brand-sub">Personal cloud</div>
    </div>
    <h2 style="margin-top:0;color:#38bdf8;">Login</h2>
    <form method="post">
      <label>Username</label>
      <input type="text" name="username" autocomplete="username" required>
      <label>Password</label>
      <input type="password" name="password" autocomplete="current-password" required>
      <button type="submit">Login</button>
    </form>
  </div>

  {% else %}
  <div class="box">
    <form id="uploadForm" method="post" action="{{ url_for('upload') }}" enctype="multipart/form-data">
      <div id="dropzone" class="dropzone">
        <div class="dz-title">Files yahan kheench kar chhodein</div>
        <div class="dz-sub">ya</div>
        <label for="fileInput" class="pick">Choose files</label>
        <input type="file" id="fileInput" name="files" multiple hidden>
        <div id="fileList" class="file-list">Koi file nahi chuni gayi</div>
      </div>
      <button id="uploadBtn" type="submit" disabled>Upload</button>
    </form>
    <script>
    (function () {
      var input = document.getElementById('fileInput');
      var zone = document.getElementById('dropzone');
      var list = document.getElementById('fileList');
      var btn = document.getElementById('uploadBtn');
      var form = document.getElementById('uploadForm');

      function size(n) {
        if (n < 1024) return n + ' B';
        if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
        if (n < 1073741824) return (n / 1048576).toFixed(1) + ' MB';
        return (n / 1073741824).toFixed(1) + ' GB';
      }

      function refresh() {
        var files = input.files;
        list.textContent = '';
        if (!files.length) {
          list.textContent = 'Koi file nahi chuni gayi';
          btn.disabled = true;
          btn.textContent = 'Upload';
          return;
        }
        for (var i = 0; i < files.length; i++) {
          var row = document.createElement('div');
          row.textContent = files[i].name + ' (' + size(files[i].size) + ')';
          list.appendChild(row);
        }
        btn.disabled = false;
        btn.textContent = 'Upload ' + files.length + (files.length === 1 ? ' file' : ' files');
      }

      input.addEventListener('change', refresh);
      ['dragenter', 'dragover'].forEach(function (ev) {
        zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.add('over'); });
      });
      ['dragleave', 'drop'].forEach(function (ev) {
        zone.addEventListener(ev, function (e) { e.preventDefault(); zone.classList.remove('over'); });
      });
      zone.addEventListener('drop', function (e) {
        if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; refresh(); }
      });
      form.addEventListener('submit', function () {
        btn.disabled = true;
        btn.textContent = 'Uploading... thoda ruko';
      });
    })();
    </script>
  </div>

  {% if files %}
  <div class="grid">
    {% for f in files %}
    <div class="item">
      <div class="thumb">
        {% if f.ext in image_ext %}
          <img src="{{ url_for('raw_file', name=f.name) }}" alt="{{ f.name }}">
        {% elif f.ext in video_ext %}
          <video src="{{ url_for('raw_file', name=f.name) }}" controls preload="metadata"></video>
        {% else %}
          <span>{{ f.ext.upper() or 'FILE' }}</span>
        {% endif %}
      </div>
      <div class="name">{{ f.name }}</div>
      <div class="meta">{{ f.size }}</div>
      <div class="actions">
        {% if f.ext in preview_ext %}
          <a class="btn" href="{{ url_for('view_file', name=f.name) }}">View</a>
        {% endif %}
        <a class="btn" href="{{ url_for('download', name=f.name) }}">Download</a>
        {% if is_admin %}
        <form method="post" action="{{ url_for('delete', name=f.name) }}"
              onsubmit="return confirm('Pakka delete karna hai?');">
          <button class="danger" type="submit">Delete</button>
        </form>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
    <p>Abhi koi file nahi hai. Upar se upload karein.</p>
  {% endif %}
  {% endif %}
</main>
</body>
</html>
"""


def avatar_file(username):
    """Is user ki profile photo ka file naam (agar hai), warna None."""
    safe = secure_filename(username)
    for ext in AVATAR_EXT:
        if os.path.isfile(os.path.join(AVATAR_DIR, f"{safe}.{ext}")):
            return f"{safe}.{ext}"
    return None


def looks_like_image(head):
    """File ke shuru ke bytes dekhkar pakka karta hai ki sach mein photo hai."""
    return (head.startswith(b"\x89PNG\r\n\x1a\n") or head.startswith(b"\xff\xd8\xff")
            or head.startswith(b"GIF8") or (head[:4] == b"RIFF" and head[8:12] == b"WEBP"))


def render(**ctx):
    user = session.get("username")
    fn = avatar_file(user) if user else None
    avatar_url = None
    if fn:
        version = int(os.path.getmtime(os.path.join(AVATAR_DIR, fn)))
        avatar_url = url_for("avatar", username=user, v=version)
    return render_template_string(
        PAGE, image_ext=IMAGE_EXT, video_ext=VIDEO_EXT, preview_ext=PREVIEW_EXT,
        username=user, is_admin=session.get("role") == "admin",
        site_name=SITE_NAME, avatar_url=avatar_url, **ctx
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "")
        pw = request.form.get("password", "")
        if user in USERS and check_password_hash(USER_HASHES[user], pw):
            session.clear()
            session["logged_in"] = True
            session["username"] = user
            session["role"] = USERS[user]["role"]
            return redirect(url_for("home"))
        flash("Username ya password galat hai.")
    return render(logged_in=False)


@app.route("/avatar/<username>")
@login_required
def avatar(username):
    fn = avatar_file(username) if username in USERS else None
    if not fn:
        abort(404)
    return send_from_directory(AVATAR_DIR, fn)


@app.route("/profile-pic", methods=["POST"])
@login_required
def set_avatar():
    f = request.files.get("photo")
    if not f or not f.filename:
        flash("Koi photo nahi chuni gayi.")
        return redirect(url_for("home"))

    ext = ext_of(f.filename)
    if ext not in AVATAR_EXT:
        flash("Sirf JPG, PNG, GIF ya WEBP photo chalegi.")
        return redirect(url_for("home"))

    data = f.read(MAX_AVATAR_MB * 1024 * 1024 + 1)
    if len(data) > MAX_AVATAR_MB * 1024 * 1024:
        flash(f"Photo bahut badi hai (limit {MAX_AVATAR_MB} MB).")
        return redirect(url_for("home"))
    if not looks_like_image(data[:12]):
        flash("Ye file sahi photo nahi lag rahi.")
        return redirect(url_for("home"))

    # Sirf apni hi photo badal sakte hain; purani hatakar nayi save hoti hai
    safe = secure_filename(session["username"])
    old = avatar_file(session["username"])
    if old:
        os.remove(os.path.join(AVATAR_DIR, old))
    with open(os.path.join(AVATAR_DIR, f"{safe}.{ext}"), "wb") as out:
        out.write(data)
    flash("Profile photo lag gayi.")
    return redirect(url_for("home"))


@app.route("/profile-pic/remove", methods=["POST"])
@login_required
def remove_avatar():
    old = avatar_file(session["username"])
    if old:
        os.remove(os.path.join(AVATAR_DIR, old))
    flash("Profile photo hata di gayi.")
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    files = []
    for name in os.listdir(UPLOAD_DIR):
        path = os.path.join(UPLOAD_DIR, name)
        if os.path.isfile(path):
            files.append({
                "name": name,
                "ext": ext_of(name),
                "size": human_size(os.path.getsize(path)),
                "mtime": os.path.getmtime(path),
            })
    files.sort(key=lambda f: f["mtime"], reverse=True)
    return render(logged_in=True, files=files)


@app.route("/upload", methods=["POST"])
@login_required
def upload():
    count = 0
    for f in request.files.getlist("files"):
        if not f or not f.filename:
            continue
        name = secure_filename(f.filename)
        if not name:  # jaise Bangla/Hindi naam jo secure_filename hata deta hai
            name = "file." + ext_of(f.filename) if ext_of(f.filename) else "file"
        f.save(os.path.join(UPLOAD_DIR, unique_name(name)))
        count += 1
    flash(f"{count} file upload ho gayi." if count else "Koi file nahi chuni gayi.")
    return redirect(url_for("home"))


VIEWER = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ name }}</title>
<style>
  body { font-family: Arial, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; }
  .bar { display:flex; gap:10px; align-items:center; padding:12px 16px;
         background:#1e293b; position:sticky; top:0; z-index:1; }
  .btn { background:#38bdf8; color:#0f172a; padding:8px 14px; border-radius:8px;
         text-decoration:none; font-weight:bold; font-size:0.9rem; white-space:nowrap; }
  .title { flex:1; word-break:break-all; font-size:0.9rem; color:#94a3b8; }
  .stage { display:flex; justify-content:center; padding:16px; }
  .stage img, .stage video { max-width:100%; max-height:85vh; }
  .stage iframe { width:100%; height:85vh; border:0; background:#fff; border-radius:8px; }
</style>
</head>
<body>
  <div class="bar">
    <a class="btn" href="{{ url_for('home') }}">&larr; Back to files</a>
    <span class="title">{{ name }}</span>
    <a class="btn" href="{{ url_for('download', name=name) }}">Download</a>
  </div>
  <div class="stage">
    {% if ext in image_ext %}
      <img src="{{ url_for('raw_file', name=name) }}" alt="{{ name }}">
    {% elif ext in video_ext %}
      <video src="{{ url_for('raw_file', name=name) }}" controls autoplay></video>
    {% elif ext in ('mp3', 'wav') %}
      <audio src="{{ url_for('raw_file', name=name) }}" controls autoplay></audio>
    {% else %}
      <iframe src="{{ url_for('raw_file', name=name) }}"></iframe>
    {% endif %}
  </div>
</body>
</html>
"""


@app.route("/raw/<path:name>")
@login_required
def raw_file(name):
    name = secure_filename(name)
    if ext_of(name) not in PREVIEW_EXT:
        return redirect(url_for("download", name=name))
    return send_from_directory(UPLOAD_DIR, name)


@app.route("/view/<path:name>")
@login_required
def view_file(name):
    name = secure_filename(name)
    if ext_of(name) not in PREVIEW_EXT:
        return redirect(url_for("download", name=name))
    if not os.path.isfile(os.path.join(UPLOAD_DIR, name)):
        abort(404)
    return render_template_string(
        VIEWER, name=name, ext=ext_of(name), image_ext=IMAGE_EXT, video_ext=VIDEO_EXT
    )


@app.route("/download/<path:name>")
@login_required
def download(name):
    return send_from_directory(UPLOAD_DIR, secure_filename(name), as_attachment=True)


@app.route("/delete/<path:name>", methods=["POST"])
@login_required
@admin_required
def delete(name):
    path = os.path.join(UPLOAD_DIR, secure_filename(name))
    if not os.path.isfile(path):
        abort(404)
    os.remove(path)
    flash("File delete ho gayi.")
    return redirect(url_for("home"))


@app.errorhandler(413)
def too_large(_):
    flash(f"File bahut badi hai (limit {MAX_UPLOAD_MB} MB).")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=False)
