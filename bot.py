from datetime import datetime
import threading  # <--- C'est ça qu'il manquait !
import aiohttp
import discord
from discord.ext import commands, tasks
from flask import Flask  # Assure-toi d'avoir 'flask' dans requirements.txt !

# --- 1. Petit serveur web pour Render ---
@app.route("/webhook-twitch", methods=['POST'])
app = Flask("")


@app.route("/")
def home():
  return "Shiro est en ligne !"


def run_web():
  # Render attribue un port via les variables d'environnement, par défaut 8080
  app.run(host="0.0.0.0", port=8080)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

MON_ID_DISCORD = 123456789012345678  # Remplace par ton ID Discord
TWITCH_USERNAME = "limposteur09"

# Liste tampon pour stocker les événements de la nuit
evenements_nuit = []
resume_deja_envoye_ce_matin = False


@bot.event
async def on_ready():
  print(f"Shiro est en ligne en tant que {bot.user}")
  verifier_statut_et_live.start()


# Fonction simulée pour vérifier si tu es en live sur Twitch
async def verifier_si_en_live():
  # TODO: Ici tu pourras brancher la vraie vérification d'API Twitch si tu le souhaites.
  # Pour l'instant, on met False par défaut.
  return False


@tasks.loop(minutes=2)
async def verifier_statut_et_live():
  global resume_deja_envoye_ce_matin
  user = await bot.fetch_user(MON_ID_DISCORD)
  if not user:
    return

  heure_actuelle = datetime.now().hour
  en_live = await verifier_si_en_live()

  # --- GESTION DU STATUT DU BOT ---
  if en_live:
    # PEU IMPORTE L'HEURE : Si tu es en live, le bot reste en ligne / streaming
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Streaming(
            name="TETR.IO sur Twitch",
            url=f"https://twitch.tv/{TWITCH_USERNAME}",
        ),
    )
    # Pendant le live, on remet le compteur de résumé à False pour le lendemain
    resume_deja_envoye_ce_matin = False
  else:
    # Hors live : on respecte les horaires (10h-22h = En ligne, 22h-10h = Veille)
    if 10 <= heure_actuelle < 22:
      await bot.change_presence(status=discord.Status.online)
      # À 10h pile (ou à la première vérification après 10h), on balance le résumé de la nuit s'il y en a un
      if heure_actuelle == 10 and not resume_deja_envoye_ce_matin:
        if len(evenements_nuit) > 0:
          texte_resume = (
              "🌙 **Résumé des événements reçus pendant la nuit :**\n"
              + "\n".join(evenements_nuit)
          )
          await user.send(texte_resume)
          evenements_nuit.clear()  # On vide la liste après l'envoi
        resume_deja_envoye_ce_matin = True
    else:
      await bot.change_presence(status=discord.Status.idle)  # Icône de lune
      # On autorise l'envoi du prochain résumé du matin vu qu'on est la nuit
      resume_deja_envoye_ce_matin = False


# Fonction intelligente qui choisit d'envoyer tout de suite ou de stocker pour le résumé
async def gerer_notification_ou_stockage(titre: str, description: str):
  user = await bot.fetch_user(MON_ID_DISCORD)
  if not user:
    return

  heure_actuelle = datetime.now().hour
  en_live = await verifier_si_en_live()

  # Format du message
  message_complet = f"• **{titre}** : {description}"

  # Si on est en veille (22h à 10h) ET qu'on n'est pas en live : on stocke pour le résumé
  if (not (10 <= heure_actuelle < 22)) and (not en_live):
    evenements_nuit.append(message_complet)
  else:
    # Sinon (en journée ou en plein live de nuit), on envoie direct en MP !
    embed = discord.Embed(
        title=titre, description=description, color=0x9B59B6
    )
    await user.send(embed=embed)


# --- Exemples d'utilisation ---


async def notifier_sub(pseudo: str):
  await gerer_notification_ou_stockage(
      "⭐ Nouveau Sub !", f"**{pseudo}** vient de s'abonner !"
  )


async def notifier_don(pseudo: str, montant: str):
  await gerer_notification_ou_stockage(
      "💸 Don reçu !", f"**{pseudo}** a donné **{montant}** !"
  )
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
