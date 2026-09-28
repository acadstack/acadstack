import base64
import requests
import io
import glob
import json
import os
import logging

API_URL = "http://frec_service:5060"  # See service name in docker-compose.yml

# (connect, read) timeouts in seconds. Matching faces in a group photo is slow.
TIMEOUT = (5, 120)


def _data_url_to_buffer(data_url):
    """Decodes a ``data:image/jpeg;base64,...`` string returned by the service."""
    return io.BytesIO(base64.b64decode(data_url.split(",", 1)[1]))


def get_face_encoding(image_bytes):
    files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
    response = requests.post(f"{API_URL}/get_face_encoding", files=files,
                             timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()["encoding"]


def get_face_encoding_b64(image_b64):
    data = {"image_b64": image_b64}
    response = requests.post(f"{API_URL}/get_face_encoding_b64", json=data,
                             timeout=TIMEOUT)
    response.raise_for_status()
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
        response = requests.post(f"{API_URL}/get_faces_from_photo", files=files,
                                 timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data["encodings"], data["locations"]


def is_person_in_photo(person_photo_path, group_photo_path, tolerance=0.45):
    with open(person_photo_path, "rb") as person_file, open(group_photo_path, "rb") as group_file:
        files = {
            "person_photo": ("person.jpg", person_file, "image/jpeg"),
            "group_photo": ("group.jpg", group_file, "image/jpeg")
        }
        data = {"tolerance": tolerance}
        response = requests.post(f"{API_URL}/is_person_in_photo", files=files, data=data,
                                 timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()["found"]


def find_persons_in_photo(group_photo_path, known_faces_data, tolerance=0.45):
    """Finds which of the known faces are in the group photo.

    Args:
        known_faces_data: ([face encodings], [info for each face]); the info
            items can be any objects, and are returned as they were given.

    Returns:
        (infos found, infos missing, faces in photo, marked photo as a data URL)
    """
    known_faces, known_infos = known_faces_data
    # The service gets each face's index as its name.
    data = {
        "tolerance": tolerance,
        "known_encodings": json.dumps([list(map(float, f)) for f in known_faces]),
        "known_names": json.dumps(list(range(len(known_faces)))),
    }
    with open(group_photo_path, "rb") as group_file:
        files = {"group_photo": ("group.jpg", group_file, "image/jpeg")}
        response = requests.post(f"{API_URL}/find_persons_in_photo", files=files,
                                 data=data, timeout=TIMEOUT)
    response.raise_for_status()
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
        response = requests.post(f"{API_URL}/write_text_on_image", files=files, data=data,
                                 timeout=TIMEOUT)
        response.raise_for_status()
        return _data_url_to_buffer(response.json()["marked_image"])


def mark_person_in_photo(person_photo_path, group_photo_path, tolerance=0.45):
    """Returns the group photo with the person marked, or None when the
    person is not in it."""
    with open(person_photo_path, "rb") as person_file, open(group_photo_path, "rb") as group_file:
        files = {
            "person_photo": ("person.jpg", person_file, "image/jpeg"),
            "group_photo": ("group.jpg", group_file, "image/jpeg")
        }
        data = {"tolerance": tolerance}
        response = requests.post(f"{API_URL}/mark_person_in_photo", files=files, data=data,
                                 timeout=TIMEOUT)
        response.raise_for_status()
        marked = response.json()["marked_image"]
        return _data_url_to_buffer(marked) if marked else None
