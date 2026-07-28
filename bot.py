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

intents = discord.Intents.default()
intents.voice_states = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
