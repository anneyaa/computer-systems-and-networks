import os
import shutil
from flask import Flask, request, jsonify, send_from_directory, abort, Response
from datetime import datetime, timezone

app = Flask(__name__)

STORAGE_BASE_DIR = os.path.abspath("storage_data")

os.makedirs(STORAGE_BASE_DIR, exist_ok=True)


def get_full_path(path: str) -> str:
    safe_path = path.lstrip("/")

    full_path = os.path.realpath(os.path.join(STORAGE_BASE_DIR, safe_path))
    base = os.path.realpath(STORAGE_BASE_DIR)

    if not full_path.startswith(base + os.sep):
        raise ValueError("Invalid path")

    return full_path


@app.route('/', defaults={'filepath': ''}, methods=['GET'])
@app.route('/<path:filepath>', methods=['GET'])
def get_file_or_list(filepath):
    full_path = get_full_path(filepath)

    if not os.path.exists(full_path):
        return jsonify({"error": "Resource not found"}), 404

    if os.path.isdir(full_path):
        items = os.listdir(full_path)
        return jsonify({
            "directory": filepath if filepath else "/",
            "content": items
        }), 200

    return send_from_directory(
        os.path.dirname(full_path),
        os.path.basename(full_path)
    )


@app.route('/<path:filepath>', methods=['PUT'])
def upload_or_copy_file(filepath):
    target_path = get_full_path(filepath)

    copy_from = request.headers.get('X-Copy-From')

    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    if copy_from:
        source_path = get_full_path(copy_from)

        if not os.path.exists(source_path):
            return jsonify({"error": "Source not found"}), 404

        # если уже существует — это overwrite
        status_code = 200 if os.path.exists(target_path) else 201

        if os.path.isdir(source_path):
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.copytree(source_path, target_path)
        else:
            shutil.copy2(source_path, target_path)

        return jsonify({"message": "Copied successfully"}), status_code

    file_exists = os.path.exists(target_path)

    with open(target_path, 'wb') as f:
        f.write(request.data)

    return jsonify({
        "message": "File updated" if file_exists else "File created"
    }), 200 if file_exists else 201


@app.route('/<path:filepath>', methods=['HEAD'])
def get_file_info(filepath):
    full_path = get_full_path(filepath)

    if not os.path.exists(full_path) or os.path.isdir(full_path):
        abort(404)

    stat = os.stat(full_path)

    response = Response()
    response.headers['Content-Length'] = str(stat.st_size)

    last_mod = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    response.headers['Last-Modified'] = last_mod.strftime(
        '%a, %d %b %Y %H:%M:%S GMT'
    )

    return response


@app.route('/<path:filepath>', methods=['DELETE'])
def delete_item(filepath):
    full_path = get_full_path(filepath)

    if not os.path.exists(full_path):
        return jsonify({"error": "Not found"}), 404

    if os.path.isdir(full_path):
        shutil.rmtree(full_path)
    else:
        os.remove(full_path)

    return '', 204


if __name__ == '__main__':
    print(f"Storage running at: {STORAGE_BASE_DIR}")
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    app.run(host='0.0.0.0', port=5555, debug=True)