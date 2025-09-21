"""Management command to process daily payouts.

This command finds PayoutRequest objects requested after 17:00 the previous day
and attempts to process them by calling the payment service transfer APIs.
"""

import logging
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.payments.models import PaymentStatus, PayoutRequest
from apps.payments.services import payment_service
from apps.profiles.models import VendorsProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process daily payout requests made after 17:00 the previous day."

    def handle(self, *args, **options):
        now = timezone.now()

        # Determine the cutoff: previous day at 17:00 local timezone
        prev_day = (now - timedelta(days=1)).date()
        cutoff_dt = timezone.make_aware(datetime.combine(prev_day, time(hour=17)))

        self.stdout.write(f"Processing payouts requested after {cutoff_dt.isoformat()}")

        # Select eligible payout requests: created_at >= cutoff, not processed
        # Exclude priority requests — they should be handled separately
        qs = PayoutRequest.objects.filter(
            requested_at__gte=cutoff_dt, processed_at__isnull=True, is_priority=False
        )
        total = qs.count()
        self.stdout.write(f"Found {total} payout(s) to process.")

        for payout in qs:
            try:
                # Find vendor's profile
                vendor_profile = VendorsProfile.objects.filter(
                    user=payout.vendor
                ).first()
                if (
                    not vendor_profile
                    or not vendor_profile.account_number
                    or not vendor_profile.bank_code
                ):
                    raise Exception("Vendor bank details missing")

                # Use existing transfer_recipient if present, otherwise create one
                recipient_code = vendor_profile.transfer_recipient

                if not recipient_code:
                    # create transfer recipient on Paystack
                    # determine recipient name: prefer vendor business name, then user profile first name, then email
                    recipient_name = vendor_profile.business_name or None
                    if not recipient_name:
                        try:
                            recipient_name = payout.vendor.user_profile.first_name
                        except Exception:
                            recipient_name = getattr(payout.vendor, "email", "")
                    resp = payment_service.create_transfer_recipient(
                        name=recipient_name,
                        account_number=vendor_profile.account_number,
                        bank_code=vendor_profile.bank_code or "",
                    )
                    recipient_code = resp.get("data", {}).get("recipient_code")
                    if not recipient_code:
                        raise Exception(f"Failed to create transfer recipient: {resp}")
                    vendor_profile.transfer_recipient = recipient_code
                    vendor_profile.save(update_fields=["transfer_recipient"])

                # initiate transfer (Paystack expects amount in kobo)
                amount_kobo = int(round(float(payout.amount) * 100))

                with db_transaction.atomic():
                    transfer_resp = payment_service.initiate_transfer(
                        recipient=recipient_code,
                        amount=amount_kobo,
                        reason=f"Payout for {payout.vendor.email}",
                    )

                    # Validate transfer response from gateway
                    # Only treat as success if the gateway indicates success.
                    if not transfer_resp or not transfer_resp.get("status"):
                        # include gateway message where available
                        gw_msg = (
                            transfer_resp.get("message")
                            if isinstance(transfer_resp, dict)
                            else None
                        )
                        raise Exception(
                            f"Transfer initiation failed: {gw_msg or transfer_resp}"
                        )

                    # If initiate_transfer returns successfully, mark processed
                    payout.processed_at = timezone.now()
                    payout.status = PaymentStatus.PAID
                    payout.save(update_fields=["processed_at", "status"])
                    self.stdout.write(f"Processed payout {payout.id} - PAID")
            except Exception as e:
                logger.exception(f"Failed processing payout {payout.id}: {e}")
                payout.processed_at = timezone.now()
                payout.status = PaymentStatus.FAILED
                payout.save(update_fields=["processed_at", "status"])
                self.stdout.write(f"Processed payout {payout.id} - FAILED")
