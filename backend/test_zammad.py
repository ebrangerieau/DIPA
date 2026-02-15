"""Script de test pour la connexion Zammad"""
import asyncio
from datetime import date, timedelta
from app.services.zammad_service import ZammadService

async def test_zammad():
    zs = ZammadService()
    print(f"API URL: {zs.api_url}")
    print(f"Token: {zs.api_token[:20]}...")
    print(f"Project Tag: {zs.project_tag}")
    print("\n" + "="*50)
    
    # Test 1: Récupération des statistiques
    print("\n📊 Test 1: Statistiques des tickets clos (30 derniers jours)")
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    print(f"Période: {start_date} à {end_date}")
    
    try:
        stats = await zs.get_closed_tickets_stats(
            start_date=start_date,
            end_date=end_date,
            exclude_project_tag=True
        )
        print(f"✅ Nombre de jours avec données: {len(stats)}")
        if stats:
            print("Premiers résultats:")
            for s in stats[:5]:
                print(f"  - {s.date}: {s.count} ticket(s)")
        else:
            print("⚠️  Aucune donnée retournée")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 2: Récupération des tickets projet
    print("\n\n📋 Test 2: Tickets avec tag #Projet")
    try:
        tickets = await zs.get_project_tickets()
        print(f"✅ Nombre de tickets #Projet: {len(tickets)}")
        if tickets:
            print("Premiers tickets:")
            for t in tickets[:3]:
                print(f"  - #{t.id}: {t.title} ({t.state})")
        else:
            print("⚠️  Aucun ticket #Projet trouvé")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    asyncio.run(test_zammad())
