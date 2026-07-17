"""Create (or update) a recruiter login. Usage:

    python manage.py create_recruiter --username jane --password secret \
        --email jane@example.com
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update a recruiter user account."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument(
            "--staff",
            action="store_true",
            help="Also grant Django admin (staff) access.",
        )

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username=options["username"],
            defaults={"email": options["email"]},
        )
        user.email = options["email"] or user.email
        user.set_password(options["password"])
        if options["staff"]:
            user.is_staff = True
        user.save()

        verb = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} recruiter '{user.username}'.")
        )
