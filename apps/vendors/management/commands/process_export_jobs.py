# apps/vendors/management/commands/process_export_jobs.py

from django.core.management.base import BaseCommand
from django.utils import timezone
# from django.db import transaction
from apps.vendors.models import ExportJob
from apps.vendors.utils import create_export_file_for_vendor
from apps.notifications.models import Notification

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process pending vendor export jobs"

    def handle(self, *args, **options):
        # pick a batch of pending jobs
        pending_jobs = ExportJob.objects.filter(
            status=ExportJob.STATUS_PENDING
        ).order_by("created_at")[:10]
        if not pending_jobs:
            self.stdout.write("No pending export jobs")
            return

        for job in pending_jobs:
            try:
                job.status = ExportJob.STATUS_PROCESSING
                job.save(update_fields=["status"])
                # generate and upload file
                path, url = create_export_file_for_vendor(
                    job.user, job.export_format, job.params
                )
                # attach file to job
                job.file_name = path
                job.file_url = url
                job.status = ExportJob.STATUS_COMPLETED
                job.completed_at = timezone.now()
                job.save(update_fields=["file_name", "status", "completed_at", "file_url"])
                # notify user
                Notification.objects.create(
                    user=job.user,
                    title="Export ready",
                    message=f"Your export is ready. Download: {url}",
                    notification_type="export_job",
                )
                self.stdout.write(f"Processed job {job.id}")
            except Exception as e:
                logger.exception("Failed processing export job %s", job.id)
                job.status = ExportJob.STATUS_FAILED
                job.error = str(e)[:2000]
                job.save(update_fields=["status", "error"])
