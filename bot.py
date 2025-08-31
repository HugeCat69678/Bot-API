import os
import asyncio
import aiohttp
from discord.ext import commands
from discord import Embed
from flask import Flask
from threading import Thread

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
FORTNITE_API_KEY = os.getenv("FORTNITE_API_KEY")

# Fortnite usernames to track
TRACKED_USERS = ["Huge_CatWasTaken", "Dov1duzass"]

# Cache to avoid duplicate announcements
last_matches = {}

# Start Discord bot
bot = commands.Bot(command_prefix="!", intents=None)

async def fetch_match_data(session, username):
    url = f"https://fortniteapi.io/v1/stats?username={username}"
    headers = {"Authorization": FORTNITE_API_KEY}
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            return None
        return await resp.json()

async def check_wins():
    await bot.wait_until_ready()
    async with aiohttp.ClientSession() as session:
        while not bot.is_closed():
            winners = []
            game_info = {}

            for user in TRACKED_USERS:
                data = await fetch_match_data(session, user)
                if not data or "account" not in data:
                    continue

                last_match = data["account"].get("lastBattlePass");
                if not last_match:
                    continue

                match_id = last_match.get("id")
                is_win = last_match.get("result") == "victory"
                mode = last_match.get("mode")
                party_size = last_match.get("partySize")

                if is_win and last_matches.get(user) != match_id:
                    winners.append(user)
                    game_info[user] = (mode, party_size, match_id)
                    last_matches[user] = match_id

            # If any wins detected
            if winners:
                embed = Embed(title="Fortnite Victory!", color=0x00ff00)
                if len(winners) == 1:
                    user = winners[0]
                    mode, party_size, match_id = game_info[user]
                    embed.add_field(name="Winner", value=user, inline=False)
                    embed.add_field(name="Mode", value=mode, inline=True)
                    embed.add_field(name="Party Size", value=str(party_size), inline=True)
                else:
                    embed.add_field(name="Winners", value=", ".join(winners), inline=False)
                    mode, party_size, _ = game_info[winners[0]]
                    embed.add_field(name="Mode", value=mode, inline=True)
                    embed.add_field(name="Party Size", value=str(party_size), inline=True)

                async with session.post(WEBHOOK_URL, json={"embeds": [embed.to_dict()]}) as resp:
                    if resp.status != 204:
                        print("Failed to send webhook", resp.status)

            await asyncio.sleep(60)

# Flask server for UptimeRobot
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# Start background loop
bot.loop.create_task(check_wins())

# Run bot
bot.run(DISCORD_TOKEN)
