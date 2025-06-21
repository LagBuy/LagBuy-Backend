import os

from django.core.management.base import BaseCommand

from apps.products.models import ProductImage
from common.services.storage import StorageService


class Command(BaseCommand):
    help = "Remove orphaned images from S3 that are not referenced by any ProductImage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List orphaned images without deleting them.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        storage = StorageService()
        bucket = storage.bucket_name
        s3_client = storage.s3_client

        # Collect all S3 keys referenced in ProductImage
        referenced_keys = set()
        for img in ProductImage.objects.all():
            url = img.image_url

            # Extract the S3 key from the URL
            if url and bucket in url:
                key = url.split(f"{bucket}/")[-1]
                referenced_keys.add(key)

        # List all objects in the S3 bucket
        paginator = s3_client.get_paginator("list_objects_v2")
        orphaned = []
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key not in referenced_keys:
                    orphaned.append(key)

        if not orphaned:
            self.stdout.write(self.style.SUCCESS("No orphaned images found."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run: The following orphaned images would be deleted:"
                )
            )
            for key in orphaned:
                self.stdout.write(f"  {key}")
            self.stdout.write(
                self.style.SUCCESS(f"Total orphaned images: {len(orphaned)}")
            )
        else:
            for key in orphaned:
                s3_client.delete_object(Bucket=bucket, Key=key)
                self.stdout.write(self.style.SUCCESS(f"Deleted orphaned image: {key}"))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleanup complete. {len(orphaned)} orphaned images deleted."
                )
            )
