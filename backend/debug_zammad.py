"""Script de debug simple"""
import asyncio
import json
from app.services.zammad_service import ZammadService

async def debug_simple():
    zs = ZammadService()
    
    print("Test 1: /api/v1/tickets (liste simple)")
    try:
        data = await zs._make_request("/api/v1/tickets?limit=1")
        print(f"Type: {type(data)}")
        if isinstance(data, list):
            print(f"Liste de {len(data)} éléments")
            if data:
                print("Exemple:", json.dumps(data[0], indent=2)[:200])
        elif isinstance(data, dict):
            print(f"Dict keys: {list(data.keys())}")
    except Exception as e:
        print(f"Erreur: {e}")

    print("\nTest 2: /api/v1/tickets/search (recherche vide)")
    try:
        data = await zs._make_request("/api/v1/tickets/search?query=state:closed&limit=1")
        print(f"Type: {type(data)}")
        if isinstance(data, list):
             print(f"Liste de {len(data)} éléments")
        elif isinstance(data, dict):
             print(f"Dict keys: {list(data.keys())}")
    except Exception as e:
        print(f"Erreur: {e}")

if __name__ == "__main__":
    asyncio.run(debug_simple())
