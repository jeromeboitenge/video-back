import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User


def create_admin(email_input: str) -> None:
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email_input)).lower()
    except ValidationError as exc:
        raise SystemExit("Enter a valid administrator email address.") from exc

    password = getpass("Administrator password (10-128 characters): ")
    confirmation = getpass("Confirm administrator password: ")
    if not 10 <= len(password) <= 128:
        raise SystemExit("Administrator passwords must be between 10 and 128 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, password_hash=hash_password(password), is_admin=True)
            db.add(user)
        else:
            user.password_hash = hash_password(password)
            user.is_admin = True
        db.commit()
    print(f"Administrator account provisioned for {email}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Frameforge administrator accounts.")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Create or reset and promote an administrator account")
    create.add_argument("email")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email)


if __name__ == "__main__":
    main()
