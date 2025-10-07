# LagBuy Backend

This repository contains the Django backend for LagBuy — an e-commerce platform with multi-vendor support, vendor dashboards and reporting, payments, and integrations for storage and file exports.

This README gives a fast on-ramp for contributors and maintainers: how to set up a local development environment, run tests, apply migrations, and work with vendor reporting and storage features.

## Table of contents

- Project overview
- Quickstart (development)
- Environment & configuration
- Database migrations
- Running the server
- Running tests
- Development tips
- Project layout
- Contributing
- License

## Project overview

Key features

- Django + Django REST Framework based API
- Multi-vendor product/catalog management
- Orders, payments, coupons, and wallets
- Vendor-scoped reporting endpoints (sales reports, trends, CSV exports)
- S3-backed file export via a storage service wrapper

This repository is intended to be run behind a WSGI/ASGI server in production and used directly via `manage.py` in development.

## Quickstart (development)

These steps assume a Unix-like environment (Linux/macOS). Adjust commands for Windows where required.

1. Clone the repo and change directory

```bash
git clone <repo-url>
cd lagbuy-backend
```

2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Create an `.env` file or set environment variables (see Environment & configuration below)

5. Apply migrations and load any fixtures (if applicable)

```bash
python manage.py migrate
```

6. Run the development server

```bash
python manage.py runserver
```

The API will be available at http://127.0.0.1:8000/ by default.

## Environment & configuration

The project reads configuration from environment variables. Typical variables to set in development:

- `DJANGO_SECRET_KEY` - a secret key for Django
- `DJANGO_DEBUG` - `1` or `0`
- `DATABASE_URL` - optional, if using a non-default database
- AWS / S3 credentials if using S3-backed storage (for CSV exports):
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_STORAGE_BUCKET_NAME`
  - `AWS_REGION`

You can use a local `.env` file with a tool like `python-dotenv` or `direnv` or export variables in your shell for local development.

Secrets and credentials must never be committed to version control.

## Database migrations

When changing models, create migrations and apply them:

```bash
python manage.py makemigrations
python manage.py migrate
```

This repository contains migrations under `apps/*/migrations/` for model changes. When switching branches, always run `migrate` to keep your local DB schema up-to-date.

## Running tests

Run the complete test suite with:

```bash
python manage.py test
```

To run a single test case (useful during debugging):

```bash
python manage.py test apps.vendors.tests.VendorDashboardTest.test_vendor_sales_report -v 2
```

Notes

- The project uses Django and DRF; make sure they are installed in your environment (see `requirements.txt`).
- Tests that touch external services (S3, third-party APIs) may require mocking or local credentials.

## Development tips

- Run the server with `runserver` for local API testing.
- Use Django shell for quick debugging:

```bash
python manage.py shell
```

- If you add model fields used in tests (for example `cost_price` on Product), create migrations and share them with the team.
- Use the included `STORAGE` wrapper for S3 operations to centralize uploads and make tests easier to mock.

## Project layout (high level)

Top-level apps include (not exhaustive):

- `apps/products` — product models, filters, and endpoints
- `apps/orders` — order modelling, order-item handling and serializers
- `apps/vendors` — vendor endpoints, reporting, CSV exports
- `apps/payments` — payment models and services
- `apps/profiles` — user profile and related utilities
- `common/services/storage.py` — storage wrapper for S3 uploads

Refer to the app folders for tests, views, serializers, and models.

## Contributing

Contributions are welcome. Suggested workflow:

1. Create a feature branch from `dev` (or the project's main integration branch):

```bash
git checkout -b feat/your-feature
```

2. Make your changes and add tests
3. Run the test suite locally
4. Commit and push your branch, then open a pull request targeting `dev`

Follow repository coding style, write tests for new behavior, and include migration files for model changes.

## CI / Reviews

Ensure tests pass in CI before merging. If your change includes DB migrations, ensure they run in CI and are compatible with the project's DB backend.

## License

This project’s license information is managed in the repository. Add a LICENSE file or check the root-level license if present.

## Contact

If you need help with setup or tests, open an issue with the failing test output and your environment details (OS, Python version, DB). Include exact commands you ran and any stack traces.

Happy hacking! ⚡
