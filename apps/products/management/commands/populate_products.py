from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.products.models import Category, Product, ProductImage
from apps.userAuth.models import CustomUser, Role

SAMPLE_CATEGORIES = [
    "Electronics",
    "Fashion",
    "Home",
    "Beauty",
    "Sports",
]


class Command(BaseCommand):
    help = "Populate the database with sample products for vendors"

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-vendor",
            type=int,
            default=5,
            help="Number of products to create per vendor (default 5)",
        )
        parser.add_argument(
            "--vendors",
            nargs="*",
            help="Optional list of vendor emails to populate. If omitted, all vendors are used.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="If set, do not save changes to the database; just report what would be done",
        )

    def handle(self, *args, **options):
        per_vendor = options.get("per_vendor") or 5
        vendor_emails = options.get("vendors") or []
        dry_run = options.get("dry_run")

        # find vendor role; create if it doesn't exist
        vendor_role, created_role = Role.objects.get_or_create(name="vendor")
        if created_role:
            self.stdout.write(
                self.style.WARNING("Role 'vendor' did not exist and was created.")
            )

        if vendor_emails:
            vendors = CustomUser.objects.filter(
                email__in=vendor_emails, roles=vendor_role
            )
        else:
            vendors = CustomUser.objects.filter(roles=vendor_role)

        if not vendors.exists():
            self.stdout.write(self.style.WARNING("No vendors found to populate."))
            return

        created = 0
        now = timezone.now()
        for vendor in vendors:
            for i in range(per_vendor):
                cat_name = SAMPLE_CATEGORIES[i % len(SAMPLE_CATEGORIES)]
                cat, _ = Category.objects.get_or_create(name=cat_name)
                name = f"Sample {cat_name} Product {i+1}"
                description = f"Auto-generated sample product for vendor {vendor.email}"
                price = 1000 + (i * 250)
                if dry_run:
                    self.stdout.write(
                        f"Would create product '{name}' for vendor {vendor.email}"
                    )
                    created += 1
                    continue
                p = Product.objects.create(
                    name=name,
                    description=description,
                    price=price,
                    verified=True,
                    stock_quantity=100,
                    seller=vendor,
                )
                p.categories.add(cat)
                # optionally create a placeholder image record
                ProductImage.objects.create(
                    product=p, image_url="https://example.com/placeholder.jpg"
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Populated {created} products."))
