import os
import time
import uuid
import threading
import requests
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-123'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['HLS_FOLDER'] = os.path.join('static', 'hls')
# Allow huge files for local processing
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  

# CONFIGURATION
# Set these!
GITHUB_USER = "wwwvasanth507-create"
GITHUB_REPO = "ok" # from user url
REPO_FULL = f"{GITHUB_USER}/{GITHUB_REPO}"
# TOKEN can be set via env var or passed in request
ENV_GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

DB_PATH = 'db.json'

def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

# Ensure dirs
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['HLS_FOLDER'], exist_ok=True)
os.makedirs('static/thumbnails', exist_ok=True)

def upload_file_to_release(upload_url_base, file_path, name, token):
    with open(file_path, 'rb') as f:
        data = f.read()
    
    headers = {
        'Authorization': f'token {token}',
        'Content-Type': 'application/octet-stream',
        'Accept': 'application/vnd.github.v3+json'
    }
    # upload_url_base is typically: https://uploads.github.com/repos/:owner/:repo/releases/:id/assets{?name,label}
    # We strip the template part
    url = upload_url_base.split('{')[0]
    
    params = {'name': name}
    resp = requests.post(url, headers=headers, params=params, data=data)
    if resp.status_code != 201:
        print(f"Failed to upload {name}: {resp.status_code} {resp.text}")
        return False
    return True

def process_video_task(video_id, input_path, token):
    try:
        print(f"[{video_id}] Starting processing...")
        # 1. Prepare local folders
        vid_hls_dir = os.path.join(app.config['HLS_FOLDER'], video_id)
        os.makedirs(vid_hls_dir, exist_ok=True)
        playlist_path = os.path.join(vid_hls_dir, 'playlist.m3u8')
        thumb_path = os.path.join('static', 'thumbnails', f"{video_id}.jpg")
        
        # 2. Thumbnail
        os.system(f'ffmpeg -i "{input_path}" -ss 00:00:01 -vframes 1 "{thumb_path}" -y')
        
        # 3. HLS Conversion
        # Use 4-second segments for better web reliability
        cmd = f'ffmpeg -i "{input_path}" -c:v h264 -c:a aac -hls_time 4 -hls_list_size 0 -f hls "{playlist_path}"'
        print(f"[{video_id}] Running ffmpeg...")
        os.system(cmd)
        
        if not os.path.exists(playlist_path):
            print(f"[{video_id}] FFmpeg failed.")
            return

        # 4. GitHub Release Logic
        if not token:
            print(f"[{video_id}] No token provided, skipping upload.")
            # Local fallback not implemented in this branch to force GitHub usage as requested
            return

        print(f"[{video_id}] Creating GitHub Release...")
        tag_name = f"v-{video_id}"
        create_url = f"https://api.github.com/repos/{REPO_FULL}/releases"
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        payload = {
            "tag_name": tag_name,
            "name": f"Video {video_id}",
            "body": "Running...",
            "draft": False,
            "prerelease": False
        }
        
        resp = requests.post(create_url, json=payload, headers=headers)
        if resp.status_code != 201:
            print(f"[{video_id}] Create Release Failed: {resp.text}")
            return
            
        release_data = resp.json()
        upload_url = release_data['upload_url']
        
        # 5. Rewrite Playlist for Remote URLs
        # Read the generated playlist
        with open(playlist_path, 'r') as f:
            lines = f.readlines()
            
        new_lines = []
        base_download_url = f"https://github.com/{REPO_FULL}/releases/download/{tag_name}/"
        
        for line in lines:
            if line.strip().endswith('.ts'):
                # It's a segment file
                segment_name = line.strip()
                # Use the remote URL
                new_lines.append(base_download_url + segment_name + '\n')
            else:
                new_lines.append(line)
                
        # Save rewritten playlist
        with open(playlist_path, 'w') as f:
            f.writelines(new_lines)
            
        # 6. Upload Assets
        # Upload playlist
        print(f"[{video_id}] Uploading playlist...")
        upload_file_to_release(upload_url, playlist_path, 'playlist.m3u8', token)
        
        # Upload segments
        for f in os.listdir(vid_hls_dir):
            if f.endswith('.ts'):
                print(f"[{video_id}] Uploading segment {f}...")
                upload_file_to_release(upload_url, os.path.join(vid_hls_dir, f), f, token)
        
        # 7. Update DB
        db = load_db()
        for v in db:
            if v['id'] == video_id:
                v['status'] = 'ready'
                v['hls_url'] = base_download_url + 'playlist.m3u8'
                break
        save_db(db)
        
        print(f"[{video_id}] DONE! Available at {base_download_url}playlist.m3u8")

    except Exception as e:
        print(f"[{video_id}] Error: {e}")

@app.route('/')
def index():
    videos = load_db()
    return render_template('index.html', videos=videos)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('video')
        title = request.form.get('title')
        # User defined token or env token
        token = request.form.get('token') or ENV_GITHUB_TOKEN
        
        if file and title:
            vid_id = str(uuid.uuid4())[:8]
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            
            # Init DB entry
            db = load_db()
            db.append({
                'id': vid_id,
                'title': title,
                'status': 'processing',
                'views': 0,
                'uploaded_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'hls_url': '' # Will be filled after processing
            })
            save_db(db)
            
            # Start Thread
            if token:
                t = threading.Thread(target=process_video_task, args=(vid_id, save_path, token))
                t.start()
                flash('Video uploading to GitHub... check back in a few minutes!')
            else:
                flash('No GitHub Token provided! Video cannot be processed to releases.')
                
            return redirect(url_for('index'))
            
    return render_template('upload.html')

@app.route('/watch/<vid_id>')
def watch(vid_id):
    db = load_db()
    video = next((v for v in db if v['id'] == vid_id), None)
    return render_template('watch.html', video=video)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
