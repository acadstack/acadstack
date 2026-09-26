"""A module for performing face recognition tasks in photos.

This module makes use of the https://github.com/ageitgey/face_recognition
library for all face recognition tasks.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import base64
import glob
import io
import os
import logging

import cv2
import face_recognition as fr
import numpy as np


def get_face_encoding(image_bytes):
    f = io.BytesIO(image_bytes)
    image = fr.load_image_file(f)
    fenc = fr.face_encodings(image, num_jitters=15, model="large")
    if len(fenc) != 1:
        raise Exception("Expected 1 face, found {0}".format(len(fenc)))
    return fenc[0]


def get_face_encoding_b64(image_b64):
    img_data = base64.b64decode(image_b64)
    return get_face_encoding(img_data)


def get_known_faces(images_glob):
    """This function reads all the image files found with the input glob
    and then extracts face encodings for each photo. Each image file is
    expected to hold only one face.

    Arguments:
        images_glob {str} -- glob pattern for the input images.

    Returns:
        A tuple whose first item is the list of face encodings, and
        the second item is the list of corresponding names of faces.
        The name of the image file is taken as the face name.
    """
    file_paths = glob.glob(images_glob)
    known_faces = []
    known_names = []
    for f in file_paths:
        image = fr.load_image_file(f)
        fenc = fr.face_encodings(image, num_jitters=15, model="large")
        if fenc:
            known_faces.append(fenc[0])
            known_names.append(os.path.basename(f))
    return known_faces, known_names


def get_faces_from_photo(photo_bytes):
    """Returns the face encodings and locations of the faces for all
    the faces which are detected in the input photo.

    Arguments:
        photo_bytes {str} -- Group photo bytes.

    Returns:
        A tuple whose first item is the list of face encodings and
        second item is the list of locations of those faces in the photo.
    """
    image = fr.load_image_file(io.BytesIO(photo_bytes))
    face_loc = fr.face_locations(image)
    face_enc = fr.face_encodings(image, num_jitters=5, model="large", known_face_locations=face_loc)
    return face_enc, face_loc


def find_persons_in_photo(group_photo_bytes, known_faces_data, tolerance=0.45):
    """Finds all those faces from a set of known faces which
    are present in a given group photo.

    Arguments:
        group_photo_bytes {bytes} -- Content of the group photo.
        known_faces_data {str} -- glob pattern for known faces images, OR
        the tuple: ([Face encodings], [Face info])

    Keyword Arguments:
        tolerance {float} -- How much distance between faces to consider
        it a match. Lower is more strict (default: {0.45})

    Returns:
        Tuple: (names_found, names_missing, grp_faces_count) --
        names_found -- Names of known faces which are present in group photo.
        names_missing -- Names of known faces not present in group photo.
        grp_faces_count -- No. of faces present in the group photo.
    """
    if isinstance(known_faces_data, str):
        logging.debug(f"Loading known faces data from path: {known_faces_data}")
        kn_faces, kn_names = get_known_faces(known_faces_data)
    else:
        kn_faces, kn_names = known_faces_data

    grp_faces, face_loc = get_faces_from_photo(group_photo_bytes)
    names_found = []
    names_missing = []
    face_locs_found = []

    if grp_faces:
        for idx, kf in enumerate(kn_faces):
            matches = fr.compare_faces(grp_faces, kf, tolerance=tolerance)
            face_distances = fr.face_distance(grp_faces, kf)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                names_found.append(kn_names[idx])
                face_locs_found.append(face_loc[best_match_index])
            else:
                names_missing.append(kn_names[idx])
    else:
        logging.debug("No faces found in group photo")

    return (names_found, names_missing, len(grp_faces),
            mark_faces(_load_bgr_image(group_photo_bytes), face_locs_found))


def _load_bgr_image(image_bytes):
    """Decodes image bytes into the BGR array OpenCV draws on and encodes."""
    return cv2.cvtColor(fr.load_image_file(io.BytesIO(image_bytes)),
                        cv2.COLOR_RGB2BGR)


def mark_faces(image, face_loc, as_buff=False):
    """Draws a numbered box around each face location on a BGR image.
    Returns a JPEG data URL, or a BytesIO of the JPEG if ``as_buff``."""
    for idx, (top, right, bottom, left) in enumerate(face_loc):
        cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 2)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(image, str(idx), (left - 15, bottom + 30), font, 1.0, (0, 0, 255), 2)
    return _encode_image(image, as_buff=as_buff)


def is_person_in_photo_bytes(person_photo_bytes, group_photo_bytes, tolerance=0.45):
    """Checks if the given person (face) is present in a group photo.

    Arguments:
        person_photo_bytes {bytes} -- Contents of person't photo to check for.
        There should be only one face present in this photo.
        group_photo_bytes {bytes} -- Contents of the group photo.

    Keyword Arguments:
        tolerance {float} -- How much distance between faces to consider
        it a match. Lower is more strict (default: {0.45})

    Returns:
        True if found, else False
    """
    grp_faces, _ = get_faces_from_photo(group_photo_bytes)
    
    # Pick the first face found in person's photo
    face = get_faces_from_photo(person_photo_bytes)[0][0]
    matches = fr.compare_faces(grp_faces, face, tolerance=tolerance)
    return True in matches


def mark_person_in_photo_bytes(person_photo, group_photo, tolerance=0.45):
    """Marks the given person (face) if present in a group photo.

    Arguments:
        person_photo {bytes} -- Content of the person't photo to check for.
        There should be only one face present in this photo.
        group_photo {bytes} -- Content of the group photo.

    Keyword Arguments:
        tolerance {float} -- How much distance between faces to consider
        it a match. Lower is more strict (default: {0.45})

    Returns:
        If successful then returns the image with person marked.
    """
    grp_faces, face_loc = get_faces_from_photo(group_photo)
    faces, flocs = get_faces_from_photo(person_photo)
    matches = fr.compare_faces(grp_faces, faces[0], tolerance=tolerance)
    face_distances = fr.face_distance(grp_faces, faces[0])
    bmi = np.argmin(face_distances)
    if matches[bmi]:
        return mark_faces(_load_bgr_image(group_photo),
                          face_loc[bmi:bmi+1], as_buff=True)
    else:
        return None


def write_text_on_image_bytes(image_bytes, txt, bottom_left):
    image = _load_bgr_image(image_bytes)
    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(image, txt, bottom_left, font, 1.0, (0, 0, 255), 2)
    return _encode_image(image, as_buff=True)


def _encode_image(image, as_buff=False):
    is_success, im_buf_arr = cv2.imencode(".jpg", image)
    if is_success:
        if as_buff:
            return io.BytesIO(im_buf_arr)
        else:
            byte_im = im_buf_arr.tobytes()
            img_data = "data:image/jpeg;base64," + base64.b64encode(byte_im).decode()
            return img_data
    else:
        raise ValueError("Failed to encode image.")
