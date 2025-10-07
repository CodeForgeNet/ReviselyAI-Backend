# services/cloudinary_storage.py
import os
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


def upload_to_cloudinary(file_path, public_id, folder="pdfs"):
    """
    Upload a file to Cloudinary and return the URL
    """
    if not os.getenv("CLOUDINARY_CLOUD_NAME"):
        return None

    try:
        result = cloudinary.uploader.upload(
            file_path,
            resource_type="raw",
            public_id=public_id,
            folder=folder
        )
        return result['secure_url']
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None


def delete_from_cloudinary(public_id, folder="pdfs"):
    """
    Delete a file from Cloudinary
    """
    if not os.getenv("CLOUDINARY_CLOUD_NAME"):
        return False

    try:
        result = cloudinary.uploader.destroy(
            f"{folder}/{public_id}",
            resource_type="raw"
        )
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
        return False
