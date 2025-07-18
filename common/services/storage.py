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
        # Generate a random file name with the same extension
        ext = ""
        if file_name and "." in file_name:
            ext = file_name.split(".")[-1]
        else:
            ext = "jpg"
        random_name = f"{uuid.uuid4().hex}.{ext}"

        # Compress the image using PIL
        try:
            image = Image.open(file_obj)
            buffer = BytesIO()
            # Save as JPEG with quality=75
            image.save(buffer, format="JPEG", quality=75, optimize=True)
            buffer.seek(0)
            content_type = content_type or "image/jpeg"
        except Exception as e:
            logger.error(f"Failed to compress image: {e}")
            return None

        extra_args = {"ContentType": content_type} if content_type else {}
        try:
            self.s3_client.upload_fileobj(
                buffer, self.bucket_name, random_name, ExtraArgs=extra_args
            )
            return self.get_file_url(random_name)
        except ClientError as e:
            logger.error(f"Failed to upload file {random_name} to S3: {e}")
            return None

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
