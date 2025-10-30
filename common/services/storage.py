import logging
import uuid
import warnings
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from PIL import Image

logger = logging.getLogger(__name__)


class StorageService:
    """
    Amazon S3 file storage service for uploading, retrieving URLs, and deleting files.
    Checks for required AWS environment variables on initialization and warns if any are missing.
    """

    def __init__(self, bucket_name=None):
        """Initializes the S3 client and bucket name using Django settings or provided bucket_name."""

        # Retrieve AWS credentials and configuration
        aws_access_key_id = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        aws_secret_access_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        aws_region = getattr(settings, "AWS_S3_REGION_NAME", None)
        bucket = bucket_name or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)

        # Check for missing configuration and warn
        missing = []
        if not aws_access_key_id:
            missing.append("AWS_ACCESS_KEY_ID")
        if not aws_secret_access_key:
            missing.append("AWS_SECRET_ACCESS_KEY")
        if not aws_region:
            missing.append("AWS_S3_REGION_NAME")
        if not bucket:
            missing.append("AWS_STORAGE_BUCKET_NAME")
        if missing:
            warnings.warn(f"Missing AWS S3 configuration: {', '.join(missing)}")

        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.bucket_name = bucket

    def upload_file(self, file_obj, file_name=None, content_type=None):
        """
        Compresses and uploads an image file to S3 with a random name to prevent clashes.
        If file_name is provided, it uses the same extension; otherwise, defaults to .jpg.
        """
        # Generate a random file name and pick an appropriate extension/format
        try:
            image = Image.open(file_obj)
        except Exception as e:
            logger.error(f"Failed to open image: {e}")
            raise e
        
        buffer = BytesIO()

        # Determine original image format and choose a safe target format
        original_format = (image.format or "JPEG").upper()
        # Prefer preserving these formats; otherwise fall back to JPEG
        supported_formats = {"JPEG", "JPG", "PNG", "WEBP", "GIF", "BMP", "TIFF"}
        target_format = (
            original_format if original_format in supported_formats else "JPEG"
        )

        # Handle alpha channel if converting to a format that doesn't support it (e.g., JPEG)
        try:
            if target_format in {"JPEG", "JPG"}:
                if image.mode in ("RGBA", "LA") or (
                    image.mode == "P" and "transparency" in image.info
                ):
                    # Flatten transparency onto white background
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    background.paste(
                        image.convert("RGBA"), mask=image.convert("RGBA").split()[-1]
                    )
                    save_image = background
                else:
                    save_image = image.convert("RGB")
                save_image.save(buffer, format="JPEG", quality=75, optimize=True)
                chosen_ext = "jpg"
                content_type = content_type or "image/jpeg"
            elif target_format == "PNG":
                save_image = (
                    image.convert("RGBA")
                    if image.mode in ("RGBA", "LA", "P")
                    else image.convert("RGB")
                )
                save_image.save(buffer, format="PNG", optimize=True)
                chosen_ext = "png"
                content_type = content_type or "image/png"
            elif target_format == "WEBP":
                save_image = (
                    image.convert("RGBA")
                    if image.mode in ("RGBA", "LA", "P")
                    else image.convert("RGB")
                )
                save_image.save(buffer, format="WEBP", quality=75, method=6)
                chosen_ext = "webp"
                content_type = content_type or "image/webp"
            elif target_format == "GIF":
                # For GIFs, if animated, keep only the first frame to avoid complexity
                try:
                    image.seek(0)
                except Exception:
                    pass
                frame = image.convert("RGBA")
                frame.save(buffer, format="GIF")
                chosen_ext = "gif"
                content_type = content_type or "image/gif"
            else:
                # BMP, TIFF or unknown supported formats - save using original format where possible
                save_format = target_format
                try:
                    image.save(buffer, format=save_format)
                except Exception:
                    # fallback to JPEG
                    image.convert("RGB").save(
                        buffer, format="JPEG", quality=75, optimize=True
                    )
                    save_format = "JPEG"
                chosen_ext = save_format.lower()
                content_type = content_type or f"image/{chosen_ext}"
        except Exception as e:
            logger.error(f"Failed to process and save image: {e}")
            raise e

        buffer.seek(0)

        # Build a random filename using the chosen extension
        random_name = f"{uuid.uuid4().hex}.{chosen_ext}"

        extra_args = {"ContentType": content_type} if content_type else {}
        try:
            self.s3_client.upload_fileobj(
                buffer, self.bucket_name, random_name, ExtraArgs=extra_args
            )
            return self.get_file_url(random_name)
        except ClientError as e:
            logger.error(f"Failed to upload file {random_name} to S3: {e}")
            raise e

    def get_file_url(self, file_name):
        """Returns the public S3 URL for a given file name."""
        return f"https://{self.bucket_name}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{file_name}"

    def delete_file(self, file_name):
        """Deletes a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_name)
            return True
        except ClientError:
            logger.error(f"Failed to delete file {file_name} from S3")
            return False


# Module-level singleton StorageService instance used across the project.
try:
    STORAGE = StorageService()
except Exception as e:
    # Initialization may fail if environment is not configured (e.g. in local tests).
    logger.warning(f"Failed to initialize StorageService singleton: {e}")
    STORAGE = None

__all__ = ["StorageService", "STORAGE"]
