import requests

CLIENT_ID = "rbh1xnq6nyre67hz3q8btq7id6n1r1"
BROADCASTER_ID = "472904893"

# Preguntar el token para no hardcodearlo
token = input("🔑 Ingresa tu BROADCASTER_TOKEN (sin oauth:): ").strip()

print("\n🔍 Probando API de follows...")

headers = {
    "Authorization": f"Bearer {token}",
    "Client-Id": CLIENT_ID
}

# Opción 1: Endpoint de seguidores
params = {
    "broadcaster_id": BROADCASTER_ID,
    "first": 20
}

response = requests.get(
    "https://api.twitch.tv/helix/channels/followers",
    headers=headers,
    params=params
)

print(f"\n📡 Endpoint /channels/followers:")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    followers = data.get("data", [])
    print(f"✅ Total seguidores: {len(followers)}")
    for follower in followers[:5]:
        print(f"  - {follower.get('user_name')} (desde: {follower.get('followed_at')})")
else:
    print(f"❌ Error: {response.text}")