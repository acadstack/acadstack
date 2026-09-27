import os
import requests

# --- Configuration ---
API_URL = "http://localhost:5000/find_persons_in_photo"
KNOWN_FACES_DIR = "./known"
GROUP_PHOTO_PATH = "./group/group.jpeg"
TOLERANCE = 0.45


def main():
    # Load known face images
    known_files = []
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            filepath = os.path.join(KNOWN_FACES_DIR, filename)
            known_files.append(("known_faces", (filename, open(filepath, "rb"), "image/jpeg")))

    if not known_files:
        print("No known face images found.")
        return
    
    print(f"Found {len(known_files)} known faces.")

    # Load group photo
    if not os.path.exists(GROUP_PHOTO_PATH):
        print("Group photo not found.")
        return

    with open(GROUP_PHOTO_PATH, "rb") as group_photo:
        group_data = {
            "group_photo": ("group.jpeg", group_photo, "image/jpeg"),
            "tolerance": str(TOLERANCE)
        }

        # Prepare multipart form-data
        multipart_data = {
            "tolerance": str(TOLERANCE)
        }

        # Send the request
        response = requests.post(
            API_URL,
            files=known_files + [("group_photo", group_data["group_photo"])],
            data=multipart_data
        )

    # Handle the response
    if response.status_code == 200:
        result = response.json()
        print("\n--- RESULTS ---")
        print("✅ Faces Found   :", result.get("found"))
        print("❌ Faces Missing :", result.get("missing"))
        print("📸 Total Faces   :", result.get("total_faces"))

        marked_image = result.get("marked_image")
        if marked_image:
            with open("marked_group.jpeg", "wb") as f:
                header, encoded = marked_image.split(",", 1)
                f.write(base64.b64decode(encoded))
                print("🖼️  Marked image saved to 'marked_group.jpeg'")
    else:
        print("Error:", response.status_code, response.text)


if __name__ == "__main__":
    import base64
    main()
