# app/api.py

from quart import Quart, request, jsonify
from app import service
import base64
import json
import logging

import numpy as np
from app.logging_config import setup_logging
setup_logging()  # <- call it before anything else

app = Quart(__name__)

@app.errorhandler(Exception)
async def handle_exception(e):
    # Log full stack trace
    logging.error("Unhandled exception occurred", exc_info=e)

    # Return a JSON response to the client
    return {
        "error": "Internal Server Error",
        "message": str(e)
    }, 500


@app.route("/health", methods=["GET"])
async def health_check():
    logging.debug("Health check called.")
    return jsonify({"status": "ok"})


@app.route("/get_face_encoding", methods=["POST"])
async def get_face_encoding():
    file = (await request.files).get("image")
    encoding = service.get_face_encoding(file.read())
    return jsonify({"encoding": encoding.tolist()})


@app.route("/get_face_encoding_b64", methods=["POST"])
async def get_face_encoding_b64():
    data = await request.get_json()
    image_b64 = data.get("image_b64")
    encoding = service.get_face_encoding_b64(image_b64)
    return jsonify({"encoding": encoding.tolist()})


@app.route("/get_known_faces", methods=["POST"])
async def get_known_faces():
    files = (await request.files).getlist("images")
    known_faces = []
    known_names = []
    for file in files:
        enc = service.get_face_encoding(file.read())
        known_faces.append(enc.tolist())
        known_names.append(file.filename)
    return jsonify({
        "encodings": known_faces,
        "names": known_names
    })


@app.route("/get_faces_from_photo", methods=["POST"])
async def get_faces_from_photo():
    file = (await request.files).get("image")
    encodings, locations, _ = service.get_faces_from_photo(file.read())
    encodings = [e.tolist() for e in encodings]
    return jsonify({
        "encodings": encodings,
        "locations": locations
    })


@app.route("/is_person_in_photo", methods=["POST"])
async def is_person_in_photo():
    files = await request.files
    person_photo = files["person_photo"].read()
    group_photo = files["group_photo"].read()
    tolerance = float((await request.form).get("tolerance", 0.45))
    result = service.is_person_in_photo_bytes(person_photo, group_photo, tolerance)
    return jsonify({"found": result})


@app.route("/mark_person_in_photo", methods=["POST"])
async def mark_person_in_photo():
    files = await request.files
    person_photo = files["person_photo"].read()
    group_photo = files["group_photo"].read()
    tolerance = float((await request.form).get("tolerance", 0.45))
    result = service.mark_person_in_photo_bytes(person_photo, group_photo, tolerance)
    if result is None:
        return jsonify({"marked_image": None, "message": "Person not found"})
    b64_img = base64.b64encode(result.getvalue()).decode()
    return jsonify({"marked_image": f"data:image/jpeg;base64,{b64_img}"})


@app.route("/write_text_on_image", methods=["POST"])
async def write_text_on_image():
    files = await request.files
    form = await request.form
    image = files["image"].read()
    text = form.get("text", "Test")
    x = int(form.get("x", 10))
    y = int(form.get("y", 10))
    result = service.write_text_on_image_bytes(image, text, (x, y))
    b64_img = base64.b64encode(result.getvalue()).decode()
    return jsonify({"marked_image": f"data:image/jpeg;base64,{b64_img}"})


@app.route("/find_persons_in_photo", methods=["POST"])
async def find_faces():
    try:
        form = await request.form
        files = await request.files

        group_photo = files.get("group_photo")
        tolerance = float(form.get("tolerance", 0.45))

        if "known_faces" in form:
            # Stored encodings sent as JSON, with matching opaque names.
            known_faces = [np.array(e) for e in json.loads(form["known_faces"])]
            known_names = json.loads(form.get("known_names", "[]"))
            if len(known_names) != len(known_faces):
                return jsonify({"error": "known_names must match known_faces "
                                         "one-to-one."}), 400
        else:
            # One uploaded image per known face, named by its file name.
            known_faces = []
            known_names = []
            for file in files.getlist("known_faces"):
                known_faces.append(service.get_face_encoding(file.read()))
                known_names.append(file.filename)

        group_photo_bytes = group_photo.read()
        result = service.find_persons_in_photo(
            group_photo_bytes,
            (known_faces, known_names),
            tolerance=tolerance
        )

        names_found, names_missing, total_faces, marked_image = result

        return jsonify({
            "found": names_found,
            "missing": names_missing,
            "total_faces": total_faces,
            "marked_image": marked_image
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
