import os
import threading
import sys
import traceback
from flask import Flask
import discord
from discord.ext import tasks, commands
import requests
from datetime import datetime
import pytz

# --- MINI SERVEUR WEB POUR KEEP-ALIVE ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Discord actif 24/7 !"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURATION DU BOT ---
TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_USER_ID = int(os.getenv('MY_DISCORD_ID', '0'))
GF_DISCORD_ID = int(os.getenv('GF_DISCORD_ID', '0'))
VRC_CHANNEL_ID = int(os.getenv('VRC_CHANNEL_ID', '0'))

STREAMERS = ['just1chat', 'katchan', 'mielcrapoulle']
live_status = {s: False for s in STREAMERS}

# File d'attente pour les notifications de nuit
night_notifications = []

intents = discord.Intents.default()
intents.voice_states = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

def get_paris_time():
    """Retourne la date et heure actuelles en France."""
    tz = pytz.timezone('Europe/Paris')
    return datetime.now(tz)

def is_active_hours():
    """Vérifie si l'heure actuelle en France est entre 10h00 et 22h00."""
    now = get_paris_time()
    return 10 <= now.hour < 22

async def send_or_queue_alert(alert_text):
    """Envoie l'alerte immédiatement si 10h-22h, sinon la stocke pour 10h00."""
    now = get_paris_time()
    time_str = now.strftime("%H:%M")
    
    if is_active_hours():
        try:
            user = await bot.fetch_user(DISCORD_USER_ID)
            await user.send(alert_text)
        except Exception as e:
            print(f"Erreur envoi MP : {e}")
    else:
        # Stockage de l'alerte pour le récapitulatif de 10h
        night_notifications.append(f"• [{time_str}] {alert_text}")
        print(f"Alerte nocturne stockée ({time_str})")

# --- GESTIONNAIRE D'ERREURS GLOBAL ---
@bot.event
async def on_error(event, *args, **kwargs):
    error_msg = traceback.format_exc()
    print(f"Erreur détectée : {error_msg}")
    try:
        user = await bot.fetch_user(DISCORD_USER_ID)
        await user.send(f"⚠️ **Erreur détectée sur le bot !**\n```python\n{error_msg[:1800]}\n```")
    except Exception as e:
        print(f"Impossible d'envoyer le MP d'erreur : {e}")

# --- ÉVÉNEMENT : BOT PRÊT ---
@bot.event
async def on_ready():
    print(f"Bot connecté sous le nom : {bot.user}")
    check_twitch.start()
    check_night_recap.start()
    update_bot_status.start() # Démarrage de la boucle de gestion du statut
    
    try:
        user = await bot.fetch_user(DISCORD_USER_ID)
        await user.send("✅ **Le bot est mis à jour !**\n• Gestion automatique du statut (Inactif la nuit).\n• Récapitulatif nocturne à 10h00.")
    except Exception as e:
        print(f"Erreur envoi MP de bienvenue : {e}")

# 1. Alerte Copine en Vocal
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == GF_DISCORD_ID:
        if before.channel is None and after.channel is not None:
            alert = f"⚠️ **Ta copine a rejoint le vocal** `{after.channel.name}` sur le serveur **{after.channel.guild.name}** !"
            await send_or_queue_alert(alert)

# 2. Alerte Soirée VRChat / VR
@bot.event
async def on_message(message):
    if message.channel.id == VRC_CHANNEL_ID:
        content = message.content.lower()
        keywords = ["vr", "vrc", "soirée", "soiree", "event", "20h", "21h"]
        if any(kw in content for kw in keywords):
            alert = f"🥽 **Nouvelle soirée VR/VRChat détectée !**\n{message.jump_url}"
            await send_or_queue_alert(alert)

# 3. Alerte Streamers Twitch
@tasks.loop(minutes=3)
async def check_twitch():
    client_id = os.getenv('TWITCH_CLIENT_ID')
    bearer_token = os.getenv('TWITCH_TOKEN')
    if not client_id or not bearer_token:
        return

    headers = {'Client-ID': client_id, 'Authorization': f'Bearer {bearer_token}'}
    for streamer in STREAMERS:
        try:
            res = requests.get(f'https://api.twitch.tv/helix/streams?user_login={streamer}', headers=headers).json()
            is_live = len(res.get('data', [])) > 0
            if is_live and not live_status[streamer]:
                live_status[streamer] = True
                alert = f"🔴 **{streamer}** est en live sur Twitch !"
                await send_or_queue_alert(alert)
            elif not is_live:
                live_status[streamer] = False
        except Exception as e:
            print(f"Erreur Twitch: {e}")

# 4. Mise à jour automatique du statut du bot selon l'heure
@tasks.loop(minutes=5)
async def update_bot_status():
    if is_active_hours():
        # Entre 10h et 22h -> En ligne (Online)
        await bot.change_presence(status=discord.Status.online)
    else:
        # Entre 22h et 10h -> Inactif (Idle)
        await bot.change_presence(status=discord.Status.idle)

# 5. Tâche de vérification pour le récapitulatif de 10h00
@tasks.loop(minutes=1)
async def check_night_recap():
    now = get_paris_time()
    if now.hour == 10 and now.minute == 0 and night_notifications:
        try:
            user = await bot.fetch_user(DISCORD_USER_ID)
            recap_text = f"☀️ **Récapitulatif des alertes de la nuit ({len(night_notifications)}) :**\n\n"
            recap_text += "\n".join(night_notifications)
            
            await user.send(recap_text)
            night_notifications.clear()
        except Exception as e:
            print(f"Erreur envoi récapitulatif nocturne : {e}")

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.start()
    bot.run(TOKEN)
