"""
Crée (ou réinitialise) un compte administrateur local.

Usage (dans le conteneur backend) :
    docker compose exec backend python scripts/create_admin.py <identifiant> <email>
Le mot de passe est demandé de façon masquée (jamais passé en argument ni affiché).
"""
import argparse
import getpass
import os
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.security import password_policy_error  # noqa: E402
from app.services.user_service import find_by_login  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Créer ou réinitialiser un administrateur local")
    parser.add_argument("username")
    parser.add_argument("email")
    parser.add_argument("--full-name", default="Administrateur")
    args = parser.parse_args()

    password = getpass.getpass("Mot de passe (12 caractères minimum) : ")
    if password != getpass.getpass("Confirmation : "):
        print("❌ Les mots de passe ne correspondent pas.")
        return 1
    error = password_policy_error(password)
    if error:
        print(f"❌ {error}")
        return 1

    init_db()
    db = SessionLocal()
    try:
        user = find_by_login(db, args.username) or find_by_login(db, args.email)
        if user is None:
            user = User(username=args.username, email=args.email.lower(), full_name=args.full_name, auth_provider="local")
            db.add(user)
            action = "créé"
        else:
            action = "mis à jour"
        user.hashed_password = User.hash_password(password)
        user.is_admin = True
        user.is_active = True
        user.must_change_password = False
        user.revoke_sessions()
        db.commit()
        print(f"✅ Administrateur « {user.username} » {action}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
