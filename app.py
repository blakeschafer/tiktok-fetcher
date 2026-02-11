import logging
import os

from flask import Flask, abort, render_template, request, Response, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from pipeline import run_profile_pipeline
from utils import list_downloads, validate_tiktok_url

# Logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_CONTENT_LENGTH

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[],
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download", methods=["POST"])
@limiter.limit(Config.RATE_LIMIT)
def download():
    data = request.get_json(silent=True)
    if not data:
        return {"error": "Invalid JSON body"}, 400
    url = data.get("url", "")
    error = validate_tiktok_url(url)
    if error:
        return {"error": error}, 400

    def generate():
        for event in run_profile_pipeline(url.strip(), Config):
            yield event.to_sse()

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/downloads")
def browse_downloads():
    profiles = list_downloads(Config.DOWNLOAD_DIR)
    return render_template("results.html", profiles=profiles)


@app.route("/downloads/<path:filepath>")
def serve_file(filepath):
    # Path traversal protection
    base = os.path.realpath(Config.DOWNLOAD_DIR)
    requested = os.path.realpath(os.path.join(Config.DOWNLOAD_DIR, filepath))

    if not requested.startswith(base + os.sep):
        abort(403)

    if not os.path.isfile(requested):
        abort(404)

    directory = os.path.dirname(requested)
    filename = os.path.basename(requested)
    return send_from_directory(directory, filename)


@app.errorhandler(400)
def bad_request(e):
    return {"error": "Bad request"}, 400


@app.errorhandler(403)
def forbidden(e):
    return {"error": "Forbidden"}, 403


@app.errorhandler(404)
def not_found(e):
    return {"error": "Not found"}, 404


@app.errorhandler(429)
def rate_limited(e):
    return {"error": "Rate limit exceeded. Please wait before trying again."}, 429


if __name__ == "__main__":
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.DEBUG)
