# YouTube HLS with GitHub Releases

This project is a video platform that uses your local machine to process videos into HLS format and uploads them to **GitHub Releases** to serve as a free, high-speed CDN.

## Architecture
1. **Frontend**: Flask templates (HTML/CSS/JS) with HLS.js player.
2. **Backend**: Python Flask app running locally.
3. **Storage**: GitHub Releases (for HLS video segments) + Local JSON (for metadata).

## Setup
1. **GitHub Repo**: Ensure you have a repo at `https://github.com/wwwvasanth507-create/ok`.
2. **Token**: Create a GitHub Personal Access Token (Classic) with `repo` scope.
3. **FFmpeg**: Must be installed and in PATH.

## Installation
```bash
pip install -r requirements.txt
```

## Running
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000).

## Uploading a Video
1. Go to `/upload`.
2. Select a video file.
3. Paste your GitHub Token.
4. Click Upload.
   - The backend will convert the video to HLS.
   - It will create a new Rlease `v-{video_id}`.
   - It will upload the playlist and segments.
   - It will rewrite the playlist to use reliable GitHub Release URLs.
   - The video will appear on the homepage once ready!

## Pushing Code to GitHub
Since `git` wasn't found in your path, use the `push_to_github.bat` (if you install git) or upload files manually via the GitHub website.
