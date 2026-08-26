from datetime import datetime
import os
import threading
import aiohttp
import discord
from discord.ext import commands, tasks
from flask import Flask  # <-- C'est cette ligne qui manquait ou s'est perdue !
import pytz
import requests

# --- 1. CONFIGURATION DU SERVEUR WEB POUR RENDER ---
app = Flask("")


@app.route("/")
def home():
  return "Shiro est en ligne !"


def run_web():
  # Render attribue un port via les variables d'environnement, par défaut 8080
  app.run(host="0.0.0.0", port=8080)


# --- 2. CONFIGURATION DU BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Identifiants et paramètres (à adapter selon tes variables d'environnement ou ID)
MON_ID_DISCORD = (
    123456789012345678  # Remplace par ton ID Discord (ou utilise int(os.getenv('DISCORD_USER_ID', 0)))
)
TWITCH_USERNAME = "limposteur09"
GF_DISCORD_ID = 0  # ID de ta copine si besoin
VRC_CHANNEL_ID = 0  # ID du salon VRChat si besoin

# Listes tampons et dictionnaires de suivi
night_notifications = []
live_status = {}
STREAMERS = ["limposteur09"]


def get_paris_time():
  """Retourne la date et heure actuelles en France."""
  tz = pytz.timezone("Europe/Paris")
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
      user = await bot.fetch_user(MON_ID_DISCORD)
      await user.send(alert_text)
    except Exception as e:
      print(f"Erreur envoi MP : {e}")
  else:
    night_notifications.append(f"• [{time_str}] {alert_text}")
    print(f"Alerte nocturne stockée ({time_str})")


# --- GESTIONNAIRE D'ERREURS GLOBAL ---
@bot.event
async def on_error(event, *args, **kwargs):
  import traceback

  error_msg = traceback.format_exc()
  print(f"Erreur détectée : {error_msg}")
  try:
    user = await bot.fetch_user(MON_ID_DISCORD)
    await user.send(
        f"⚠️ **Erreur détectée sur le bot !**\n```python\n{error_msg[:1800]}\n```"
    )
  except Exception as e:
    print(f"Impossible d'envoyer le MP d'erreur : {e}")


# --- ÉVÉNEMENT : BOT PRÊT ---
@bot.event
async def on_ready():
  print(f"Bot connecté sous le nom : {bot.user}")
  check_twitch.start()
  check_night_recap.start()
  update_bot_status.start()

  try:
    user = await bot.fetch_user(MON_ID_DISCORD)
    await user.send(
        "✅ **Le bot est mis à jour et opérationnel !**\n• Gestion automatique"
        " du statut.\n• Récapitulatif nocturne à 10h00."
    )
  except Exception as e:
    print(f"Erreur envoi MP de bienvenue : {e}")


# --- TÂCHES ET ÉVÉNEMENTS ---


@bot.event
async def on_voice_state_update(member, before, after):
  if member.id == GF_DISCORD_ID:
    if before.channel is None and after.channel is not None:
      alert = f"⚠️ **Ta copine a rejoint le vocal** `{after.channel.name}` sur le serveur **{after.channel.guild.name}** !"
      await send_or_queue_alert(alert)


@bot.event
async def on_message(message):
  if message.channel.id == VRC_CHANNEL_ID:
    content = message.content.lower()
    keywords = ["vr", "vrc", "soirée", "soiree", "event", "20h", "21h"]
    if any(kw in content for kw in keywords):
      alert = f"🥽 **Nouvelle soirée VR/VRChat détectée !**\n{message.jump_url}"
      await send_or_queue_alert(alert)
  await bot.process_commands(message)


@tasks.loop(minutes=3)
async def check_twitch():
  client_id = os.getenv("TWITCH_CLIENT_ID")
  bearer_token = os.getenv("TWITCH_TOKEN")
  if not client_id or not bearer_token:
    return

  headers = {"Client-ID": client_id, "Authorization": f"Bearer {bearer_token}"}
  for streamer in STREAMERS:
    try:
      res = requests.get(
          f"https://api.twitch.tv/helix/streams?user_login={streamer}",
          headers=headers,
      ).json()
      is_live = len(res.get("data", [])) > 0
      if streamer not in live_status:
        live_status[streamer] = False

      if is_live and not live_status[streamer]:
        live_status[streamer] = True
        alert = f"🔴 **{streamer}** est en live sur Twitch !"
        await send_or_queue_alert(alert)
      elif not is_live:
        live_status[streamer] = False
    except Exception as e:
      print(f"Erreur Twitch: {e}")


@tasks.loop(minutes=5)
async def update_bot_status():
  if is_active_hours():
    await bot.change_presence(status=discord.Status.online)
  else:
    await bot.change_presence(status=discord.Status.idle)


@tasks.loop(minutes=1)
async def check_night_recap():
  now = get_paris_time()
  if now.hour == 10 and now.minute == 0 and night_notifications:
    try:
      user = await bot.fetch_user(MON_ID_DISCORD)
      recap_text = f"☀️ **Récapitulatif des alertes de la nuit ({len(night_notifications)}) :**\n\n"
      recap_text += "\n".join(night_notifications)

      await user.send(recap_text)
      night_notifications.clear()
    except Exception as e:
      print(f"Erreur envoi récapitulatif nocturne : {e}")


# --- LANCEMENT FINAL ---
if __name__ == "__main__":
  t = threading.Thread(target=run_web)
  t.start()
  bot.run(os.getenv("TOKEN"))
