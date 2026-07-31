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
    
    try:
        user = await bot.fetch_user(DISCORD_USER_ID)
        await user.send("✅ **Le bot est démarré et mis à jour !**\n• Mots-clés VR/VRC élargis.\n• Récapitulatif nocturne activé pour 10h00.")
    except Exception as e:
        print(f"Erreur envoi MP de bienvenue : {e}")

# 1. Alerte Copine en Vocal
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == GF_DISCORD_ID:
        if before.channel is None and after.channel is not None:
            alert = f"⚠️ **Ta copine a rejoint le vocal** `{after.channel.name}` sur le serveur **{after.channel.guild.name}** !"
            await send_or_queue_alert(alert)

# 2. Alerte Soirée VRChat
@bot.event
async def on_message(message):
    if message.channel.id == VRC_CHANNEL_ID:
        content = message.content.lower()
        # Extension des mots-clés (vr, vrc, soirée, event, 20h, 21h)
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

# 4. Tâche de vérification pour le récapitulatif de 10h00
@tasks.loop(minutes=1)
async def check_night_recap():
    now = get_paris_time()
    # Déclenchement à 10h00 pile si des alertes ont été accumulées
    if now.hour == 10 and now.minute == 0 and night_notifications:
        try:
            user = await bot.fetch_user(DISCORD_USER_ID)
            recap_text = f"☀️ **Récapitulatif des alertes de la nuit ({len(night_notifications)}) :**\n\n"
            recap_text += "\n".join(night_notifications)
            
            await user.send(recap_text)
            night_notifications.clear() # Vider la liste après envoi
        except Exception as e:
            print(f"Erreur envoi récapitulatif nocturne : {e}")

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.start()
    bot.run(TOKEN)bot = commands.Bot(command_prefix="!", intents=intents)

def is_active_hours():
    """Vérifie si l'heure actuelle en France est entre 10h00 et 22h00."""
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    return 10 <= now.hour < 22

# --- GESTIONNAIRE D'ERREURS GLOBAL ---
@bot.event
async def on_error(event, *args, **kwargs):
    """Envoie un MP si une erreur imprévue survient dans un événement."""
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
    
    # Message MP au démarrage / fin de configuration
    try:
        user = await bot.fetch_user(DISCORD_USER_ID)
        await user.send("✅ **Le bot est démarré et entièrement configuré !** Prêt à surveiller les vocals, VRChat et Twitch.")
    except Exception as e:
        print(f"Erreur envoi MP de bienvenu : {e}")

# 1. Alerte Copine en Vocal
@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == GF_DISCORD_ID and is_active_hours():
        if before.channel is None and after.channel is not None:
            user = await bot.fetch_user(DISCORD_USER_ID)
            await user.send(f"⚠️ **Ta copine a rejoint le vocal** `{after.channel.name}` sur le serveur **{after.channel.guild.name}** !")

# 2. Alerte Soirée VRChat
@bot.event
async def on_message(message):
    if message.channel.id == VRC_CHANNEL_ID and is_active_hours():
        content = message.content.lower()
        if any(kw in content for kw in ["soirée", "event", "vrc", "20h", "21h"]):
            user = await bot.fetch_user(DISCORD_USER_ID)
            await user.send(f"🥽 **Nouvelle soirée VRChat détectée !**\n{message.jump_url}")

# 3. Alerte Streamers Twitch (en MP)
@tasks.loop(minutes=3)
async def check_twitch():
    if not is_active_hours():
        return
        
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
                user = await bot.fetch_user(DISCORD_USER_ID)
                await user.send(f"🔴 **{streamer}** est en live sur Twitch !")
            elif not is_live:
                live_status[streamer] = False
        except Exception as e:
            print(f"Erreur Twitch: {e}")

if __name__ == "__main__":
    t = threading.Thread(target=run_web)
    t.start()
    bot.run(TOKEN)
