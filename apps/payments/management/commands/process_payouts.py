"""Management command to process daily payouts.

This command finds PayoutRequest objects requested after 17:00 the previous day
and attempts to process them by calling the payment service transfer APIs.
"""

import logging
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.payments.models import PaymentStatus, PayoutRequest
from apps.payments.services import payment_service
from apps.profiles.models import VendorsProfile
from apps.vendors.models import VendorWallet

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

        # Automatic wallet-driven payouts (efficient implementation)
        MIN_PAYOUT = Decimal(str(getattr(settings, "DAILY_PAYOUT_MIN", 1000.00)))
        MAX_PAYOUT = Decimal(str(getattr(settings, "DAILY_PAYOUT_MAX", 100000.00)))

        self.stdout.write(
            f"Processing automatic wallet-driven payouts for wallets with balance >= {MIN_PAYOUT}"
        )

        # First, find vendor ids with eligible balances
        vendor_ids = list(
            VendorWallet.objects.filter(balance__gte=MIN_PAYOUT).values_list(
                "vendor_id", flat=True
            )
        )
        if not vendor_ids:
            self.stdout.write("No wallets eligible for automatic payouts.")
        else:
            # Bulk fetch vendor profiles and build a mapping to avoid N+1 queries
            profiles = VendorsProfile.objects.filter(user_id__in=vendor_ids).values(
                "user_id",
                "account_number",
                "bank_code",
                "transfer_recipient",
                "business_name",
            )
            profile_map = {p["user_id"]: p for p in profiles}

            # Iterate wallets using an iterator to minimize memory and DB hit
            wallets_qs = (
                VendorWallet.objects.filter(balance__gte=MIN_PAYOUT)
                .select_related("vendor")
                .iterator()
            )

            processed = 0
            for wallet in wallets_qs:
                vendor = wallet.vendor
                vp = profile_map.get(vendor.id)
                if not vp or not vp.get("account_number") or not vp.get("bank_code"):
                    logger.debug(
                        f"Skipping vendor {vendor.id}: missing/invalid profile"
                    )
                    continue

                # Determine payout amount and skip if below MIN after cap
                amount_to_pay = min(wallet.balance, MAX_PAYOUT)
                if amount_to_pay < MIN_PAYOUT:
                    continue

                reserved_amount = Decimal("0")
                payout = None
                try:
                    # Reserve funds atomically: lock the wallet row, ensure sufficient balance, create payout, debit
                    with db_transaction.atomic():
                        locked_wallet = VendorWallet.objects.select_for_update().get(
                            pk=wallet.pk
                        )
                        if locked_wallet.balance < amount_to_pay:
                            # balance changed since selection; skip
                            logger.info(f"Wallet {wallet.id} balance changed; skipping")
                            continue
                        payout = PayoutRequest.objects.create(
                            amount=amount_to_pay,
                            currency=locked_wallet.currency,
                            vendor=vendor,
                            status=PaymentStatus.PENDING,
                            is_priority=False,
                        )
                        # debit reserves the funds
                        locked_wallet.debit(amount_to_pay)
                        reserved_amount = amount_to_pay

                    # Ensure transfer_recipient exists; use profile_map to update if needed
                    recipient_code = vp.get("transfer_recipient")
                    if not recipient_code:
                        recipient_name = vp.get("business_name") or None
                        if not recipient_name:
                            try:
                                recipient_name = vendor.user_profile.first_name
                            except Exception:
                                recipient_name = getattr(vendor, "email", "")
                        resp = payment_service.create_transfer_recipient(
                            name=recipient_name,
                            account_number=vp.get("account_number"),
                            bank_code=vp.get("bank_code") or "",
                        )
                        recipient_code = resp.get("data", {}).get("recipient_code")
                        if not recipient_code:
                            raise Exception(
                                f"Failed to create transfer recipient: {resp}"
                            )
                        # persist transfer_recipient to DB to avoid future API calls
                        VendorsProfile.objects.filter(user_id=vendor.id).update(
                            transfer_recipient=recipient_code
                        )
                        # update cached profile_map
                        profile_map[vendor.id]["transfer_recipient"] = recipient_code

                    # Initiate transfer (amount in kobo)
                    amount_kobo = int(round(float(amount_to_pay) * 100))
                    transfer_resp = payment_service.initiate_transfer(
                        recipient=recipient_code,
                        amount=amount_kobo,
                        reason=f"Automatic payout for {vendor.email}",
                    )

                    if not transfer_resp or not transfer_resp.get("status"):
                        gw_msg = (
                            transfer_resp.get("message")
                            if isinstance(transfer_resp, dict)
                            else None
                        )
                        raise Exception(
                            f"Transfer initiation failed: {gw_msg or transfer_resp}"
                        )

                    # Mark processed
                    payout.processed_at = timezone.now()
                    payout.status = PaymentStatus.PAID
                    payout.save(update_fields=["processed_at", "status"])
                    processed += 1
                except Exception as e:
                    logger.exception(
                        f"Failed auto-processing payout for wallet {wallet.id}: {e}"
                    )
                    # Failure cleanup: mark payout failed and re-credit reserved amount if any
                    try:
                        if payout is not None:
                            payout.processed_at = timezone.now()
                            payout.status = PaymentStatus.FAILED
                            payout.save(update_fields=["processed_at", "status"])
                        if reserved_amount > 0:
                            # re-credit atomically
                            with db_transaction.atomic():
                                Wallet = VendorWallet.objects.select_for_update().get(
                                    pk=wallet.pk
                                )
                                Wallet.credit(reserved_amount)
                    except Exception:
                        logger.exception("Error during failure cleanup for auto-payout")
            self.stdout.write(f"Auto-processed {processed} payouts.")
