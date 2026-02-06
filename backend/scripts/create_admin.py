"""
Script pour créer un utilisateur administrateur initial.
À exécuter une seule fois au démarrage de l'application.
"""
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User


def create_admin_user():
    """Crée un utilisateur administrateur par défaut."""
    db = SessionLocal()
    
    try:
        # Vérifier si un admin existe déjà
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        
        if existing_admin:
            print(f"✅ Un administrateur existe déjà: {existing_admin.username}")
            return
        
        # Créer l'utilisateur admin
        admin = User(
            username="admin",
            email="admin@cockpit-it.local",
            hashed_password=User.hash_password("admin123"),  # À changer après la première connexion !
            full_name="Administrateur",
            is_admin=True,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        
        print("✅ Utilisateur administrateur créé avec succès !")
        print("   Username: admin")
        print("   Password: admin123")
        print("   ⚠️  IMPORTANT: Changez ce mot de passe après la première connexion !")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de l'administrateur: {e}")
        db.rollback()
    
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
