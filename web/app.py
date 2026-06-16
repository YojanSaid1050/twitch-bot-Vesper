"""
Servidor EventSub para Twitch
Recibe webhooks de Twitch y los reenvía al bot local
"""

import os
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Configuración desde variables de entorno
BOT_WEBHOOK_URL = os.getenv("BOT_WEBHOOK_URL", "http://localhost:5001/webhook")
TWITCH_SECRET = os.getenv("TWITCH_WEBHOOK_SECRET", "")
PORT = int(os.getenv("PORT", 8080))


def verify_signature(message: str, signature: str) -> bool:
    """
    Verificar firma de Twitch para seguridad
    
    Args:
        message: Mensaje completo (message_id + timestamp + body)
        signature: Firma del header Twitch-Eventsub-Message-Signature
    
    Returns:
        True si la firma es válida
    """
    if not TWITCH_SECRET:
        print("⚠️ TWITCH_WEBHOOK_SECRET no configurado, omitiendo verificación")
        return True
    
    expected = hmac.new(
        TWITCH_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # El formato es sha256=firma
    if signature.startswith('sha256='):
        signature = signature[7:]
    
    return hmac.compare_digest(expected, signature)


@app.route('/webhook/twitch', methods=['POST'])
def twitch_webhook():
    """
    Endpoint principal para webhooks de Twitch
    Recibe eventos y los reenvía al bot local
    """
    try:
        # Obtener headers para verificación
        signature = request.headers.get('Twitch-Eventsub-Message-Signature', '')
        message_id = request.headers.get('Twitch-Eventsub-Message-Id', '')
        timestamp = request.headers.get('Twitch-Eventsub-Message-Timestamp', '')
        message_type = request.headers.get('Twitch-Eventsub-Message-Type', '')
        
        # Obtener body
        body = request.get_data(as_text=True)
        
        # Construir mensaje para verificación
        message = message_id + timestamp + body
        
        # Verificar firma
        if not verify_signature(message, signature):
            print(f"⚠️ Firma inválida para mensaje {message_id}")
            return jsonify({"error": "Invalid signature"}), 401
        
        # Parsear JSON
        data = request.json
        
        # Manejar verificación de webhook (challenge)
        if message_type == 'webhook_callback_verification':
            challenge = data.get('challenge')
            print(f"✅ Verificando webhook con challenge: {challenge}")
            return jsonify({"challenge": challenge}), 200
        
        # Procesar evento
        if message_type == 'notification':
            event_type = data.get('subscription', {}).get('type', 'unknown')
            event_data = data.get('event', {})
            
            print(f"📨 Evento recibido: {event_type} - {datetime.now().isoformat()}")
            
            # Reenviar al bot local
            try:
                response = requests.post(
                    BOT_WEBHOOK_URL,
                    json={
                        'type': event_type,
                        'data': event_data,
                        'timestamp': datetime.now().isoformat()
                    },
                    timeout=3
                )
                
                if response.status_code == 200:
                    print(f"✅ Evento reenviado al bot: {event_type}")
                else:
                    print(f"⚠️ Error reenviando evento: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"⚠️ No se pudo conectar con el bot local: {e}")
                # No fallamos la respuesta a Twitch, el evento ya está procesado
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/webhook/twitch', methods=['GET'])
def twitch_webhook_get():
    """Método GET para verificación inicial"""
    return jsonify({"status": "ready"}), 200


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de salud para Render"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "port": PORT,
        "bot_webhook_url": BOT_WEBHOOK_URL
    }), 200


@app.route('/', methods=['GET'])
def index():
    """Página principal"""
    return jsonify({
        "service": "Twitch EventSub Webhook Receiver",
        "status": "running",
        "port": PORT,
        "endpoints": {
            "webhook": "/webhook/twitch",
            "health": "/health"
        }
    }), 200


if __name__ == '__main__':
    print(f"🚀 Iniciando servidor EventSub en puerto {PORT}")
    print(f"📡 Webhook URL: /webhook/twitch")
    print(f"💚 Health check: /health")
    print(f"🔗 Bot webhook: {BOT_WEBHOOK_URL}")
    app.run(host='0.0.0.0', port=PORT, debug=False)