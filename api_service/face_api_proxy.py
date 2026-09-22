import requests
import io
import glob
import os
import logging

import settings_store as ST

API_URL = "http://frec_service:5060"  # See service name in docker-compose.yml


def get_face_encoding(image_bytes):
    files = {'image': ('image.jpg', image_bytes, 'image/jpeg')}
    response = requests.post(f"{API_URL}/get_face_encoding", files=files)
    response.raise_for_status()
    return response.json()["encoding"]


def get_face_encoding_b64(image_b64):
    data = {"image_b64": image_b64}
    response = requests.post(f"{API_URL}/get_face_encoding_b64", json=data)
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
        response = requests.post(f"{API_URL}/get_faces_from_photo", files=files)
        response.raise_for_status()
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
        response = requests.post(f"{API_URL}/is_person_in_photo", files=files, data=data)
        response.raise_for_status()
        return response.json()["match"]


def find_persons_in_photo(group_photo_path, known_faces_data, tolerance=None):
    if tolerance is None:
        tolerance = ST.setting("faces.match_tolerance")
    known_faces, known_names = known_faces_data
    data = {
        "tolerance": tolerance,
        "known_faces": known_faces,
        "known_names": known_names
    }
    with open(group_photo_path, "rb") as group_file:
        files = {"group_photo": ("group.jpg", group_file, "image/jpeg")}
        response = requests.post(f"{API_URL}/find_persons_in_photo", files=files, data={"tolerance": tolerance})
    response.raise_for_status()
    result = response.json()
    return (
        result["names_found"],
        result["names_missing"],
        result["face_count"],
        result["marked_image_b64"]
    )


def write_text_on_image(photo_path, txt, bottom_left):
    with open(photo_path, "rb") as photo:
        files = {"photo": ("photo.jpg", photo, "image/jpeg")}
        data = {
            "text": txt,
            "x": bottom_left[0],
            "y": bottom_left[1]
        }
        response = requests.post(f"{API_URL}/write_text_on_image", files=files, data=data)
        response.raise_for_status()
        return io.BytesIO(response.content)


def mark_person_in_photo(person_photo_path, group_photo_path, tolerance=None):
    if tolerance is None:
        tolerance = ST.setting("faces.match_tolerance")
    with open(person_photo_path, "rb") as person_file, open(group_photo_path, "rb") as group_file:
        files = {
            "person_photo": ("person.jpg", person_file, "image/jpeg"),
            "group_photo": ("group.jpg", group_file, "image/jpeg")
        }
        data = {"tolerance": tolerance}
        response = requests.post(f"{API_URL}/mark_person_in_photo", files=files, data=data)
        response.raise_for_status()
        return io.BytesIO(response.content)
