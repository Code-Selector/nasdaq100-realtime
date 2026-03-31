#!/usr/bin/env python3
import os, sys
for k in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)

from flask import Flask, send_from_directory
from flask_cors import CORS
from app.config import SERVER_PORT, FRONT_DIR, FETCH_INTERVAL
from app.database import init_pool
from app.dao.stock_dao import init_tables
from app.api.stock_api import stock_bp
from app.task import scheduler


def create_app() -> Flask:
    app = Flask(__name__, static_folder=FRONT_DIR, static_url_path="")
    CORS(app)
    app.register_blueprint(stock_bp)

    @app.route("/")
    def index():
        return send_from_directory(FRONT_DIR, "index.html")

    return app


def main():
    init_pool()
    init_tables()
    scheduler.restore_from_db()
    scheduler.start()
    app = create_app()
    print(f"\n  Nasdaq100 Realtime @ http://localhost:{SERVER_PORT}  (interval {FETCH_INTERVAL}s)\n")
    app.run(host="0.0.0.0", port=SERVER_PORT, debug=False)


if __name__ == "__main__":
    main()
