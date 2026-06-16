import requests
import webbrowser
import urllib.parse

CLIENT_ID = "rbh1xnq6nyre67hz3q8btq7id6n1r1"
CLIENT_SECRET = "90zk3l5khv8wrua0zaf59vlumwym79"
REDIRECT_URI = "http://localhost"

# Scopes necesarios para el streamer
scopes = [
    "channel:manage:broadcast",
    "channel:edit:commercial",
    "channel:manage:vips",
    "clips:edit",
    "moderator:read:followers",  # Para leer seguidores
    "user:read:follows"          # Alternativa para follows
]

scope_str = " ".join(scopes)
auth_url = f"https://id.twitch.tv/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={urllib.parse.quote(scope_str)}"

print("=" * 60)
print("🔑 GENERAR TOKEN PARA XYOJANSAIDX")
print("=" * 60)
print("\n📱 Abre este enlace en el navegador con la cuenta xyojansaidx:")
print(f"\n{auth_url}\n")
print("📝 Scopes solicitados:")
for scope in scopes:
    print(f"   - {scope}")
print("\n✅ Después de autorizar, copia el código de la URL (después de 'code=')")

auth_code = input("\n📝 Código: ").strip()

print("\n🔄 Generando tokens...")

response = requests.post(
    "https://id.twitch.tv/oauth2/token",
    data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }
)

if response.status_code == 200:
    data = response.json()
    print("\n✅ TOKENS GENERADOS CORRECTAMENTE")
    print("=" * 60)
    print(f"BROADCASTER_TOKEN=oauth:{data['access_token']}")
    print(f"BROADCASTER_REFRESH_TOKEN={data['refresh_token']}")
    print(f"\n⏰ Expira en: {data['expires_in']} segundos ({data['expires_in'] // 60} minutos)")
    
    # Verificar el token
    print("\n🔍 Verificando token...")
    verify_response = requests.get(
        "https://id.twitch.tv/oauth2/validate",
        headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    
    if verify_response.status_code == 200:
        token_data = verify_response.json()
        print(f"✅ Token válido para usuario: {token_data.get('login')}")
        print(f"Scopes: {token_data.get('scopes', [])}")
    else:
        print(f"⚠️ No se pudo verificar el token: {verify_response.status_code}")
    
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)