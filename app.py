from flask import Flask, request, render_template, send_file, session, after_this_request
import yt_dlp
import os
import shutil
import uuid
import logging
from dotenv import load_dotenv
from urllib.parse import quote as url_quote  # Updated import

# Load environment variables from .env file if running locally
load_dotenv()

app = Flask(__name__)

# Set the secret key from the environment variable
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    
    # Validate input URL
    if not url or not url.startswith("http"):
        return "Invalid URL", 400
    
    # Create a unique directory for the user session
    if 'download_dir' not in session:
        session['download_dir'] = os.path.join('downloads', str(uuid.uuid4()))

    download_dir = session['download_dir']
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)
    
    # Clear any existing files in the user-specific download directory
    for filename in os.listdir(download_dir):
        file_path = os.path.join(download_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return f"An error occurred while deleting file {file_path}: {e}", 500

    try:
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'ffmpeg_location': '/usr/bin/ffmpeg'  # Ensure yt-dlp uses the installed ffmpeg
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Assuming only one file is downloaded, find it in the user-specific download directory
        downloaded_file = max(os.listdir(download_dir), key=lambda f: os.path.getctime(os.path.join(download_dir, f)))
        downloaded_file_path = os.path.join(download_dir, downloaded_file)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(downloaded_file_path)
                if not os.listdir(download_dir):
                    shutil.rmtree(download_dir)
                session.pop('download_dir', None)
            except Exception as error:
                logger.error(f"Error removing downloaded file or directory: {error}")
            return response

        return send_file(downloaded_file_path, as_attachment=True, download_name=downloaded_file)
    except Exception as e:
        logger.error(f"Error during download: {e}")
        return f"An error occurred: {e}", 500

if __name__ == '__main__':
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))