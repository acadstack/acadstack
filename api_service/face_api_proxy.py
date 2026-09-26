import base64
import json
import requests
import io
import glob
import os
import logging

import settings_store as ST
from common import AcadStackException

API_URL = "http://frec_service:5060"  # See service name in docker-compose.yml


def _post(path, **kwargs):
    """POSTs to frec_service with the configured timeout, so a hung call
    cannot block the calling worker indefinitely."""
    timeout = ST.setting("faces.request_timeout_secs")
    try:
        response = requests.post(f"{API_URL}/{path}", timeout=timeout, **kwargs)
    except requests.Timeout as ex:
        raise AcadStackException(
            f"The face-recognition service did not respond within {timeout} "
            f"seconds. Please try again later.") from ex
    response.raise_for_status()
    return response


def _data_url_to_buffer(data_url):
    """Decodes a 'data:image/jpeg;base64,...' URL; None stays None."""
    if not data_url:
        return None
    return io.BytesIO(base64.b64decode(data_url.split(",", 1)[-1]))


def get_face_encoding(image_bytes):
    files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
    response = _post("get_face_encoding", files=files)
    return response.json()["encoding"]


def get_face_encoding_b64(image_b64):
    data = {"image_b64": image_b64}
    response = _post("get_face_encoding_b64", json=data)
    return response.json()["encoding"]


def get_known_faces(images_glob):
    file_paths = glob.glob(images_glob)
    known_faces = []
    known_names = []
    for path in file_paths:
        with open(path, "rb") as f:
            try:
                encoding = get_face_encoding(f.read())
                known_faces.append(encoding)
                known_names.append(os.path.basename(path))
            except Exception as e:
                logging.warning(f"Failed to encode {path}: {e}")
    return known_faces, known_names


def get_faces_from_photo(group_photo_path):
    with open(group_photo_path, "rb") as group_file:
        files = {"image": ("group.jpg", group_file, "image/jpeg")}
        response = _post("get_faces_from_photo", files=files)
        data = response.json()
        return data["encodings"], data["locations"]


def is_person_in_photo(person_photo_path, group_photo_path, tolerance=None):
    if tolerance is None:
        tolerance = ST.setting("faces.match_tolerance")
    with open(person_photo_path, "rb") as person_file, open(group_photo_path, "rb") as group_file:
        files = {
            "person_photo": ("person.jpg", person_file, "image/jpeg"),
            "group_photo": ("group.jpg", group_file, "image/jpeg")
        }
        data = {"tolerance": tolerance}
        response = _post("is_person_in_photo", files=files, data=data)
        return response.json()["found"]


def find_persons_in_photo(group_photo_path, known_faces_data, tolerance=None):
    """Matches stored face encodings against a group photo.

    ``known_faces_data`` is ``(encodings, infos)``: one encoding (a
    sequence of floats) per known person and a matching info object that
    is returned as-is. Returns ``(infos_found, infos_missing, face_count,
    marked_image_data_url)``.
    """
    if tolerance is None:
        tolerance = ST.setting("faces.match_tolerance")
    known_faces, known_infos = known_faces_data
    data = {
        "tolerance": tolerance,
        "known_faces": json.dumps([[float(x) for x in enc] for enc in known_faces]),
        # The service echoes these back; indexes map results to infos.
        "known_names": json.dumps(list(range(len(known_infos)))),
    }
    with open(group_photo_path, "rb") as group_file:
        files = {"group_photo": ("group.jpg", group_file, "image/jpeg")}
        response = _post("find_persons_in_photo", files=files, data=data)
    result = response.json()
    return (
        [known_infos[i] for i in result["found"]],
        [known_infos[i] for i in result["missing"]],
        result["total_faces"],
        result["marked_image"]
    )


def write_text_on_image(photo_path, txt, bottom_left):
    with open(photo_path, "rb") as photo:
        files = {"image": ("photo.jpg", photo, "image/jpeg")}
        data = {
            "text": txt,
            "x": bottom_left[0],
            "y": bottom_left[1]
        }
        response = _post("write_text_on_image", files=files, data=data)
        return _data_url_to_buffer(response.json()["marked_image"])


def mark_person_in_photo(person_photo_path, group_photo_path, tolerance=None):
    if tolerance is None:
        tolerance = ST.setting("faces.match_tolerance")
    with open(person_photo_path, "rb") as person_file, open(group_photo_path, "rb") as group_file:
        files = {
            "person_photo": ("person.jpg", person_file, "image/jpeg"),
            "group_photo": ("group.jpg", group_file, "image/jpeg")
        }
        data = {"tolerance": tolerance}
        response = _post("mark_person_in_photo", files=files, data=data)
        # None when the person is not found in the group photo.
        return _data_url_to_buffer(response.json()["marked_image"])
