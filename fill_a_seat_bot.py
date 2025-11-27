import requests
import re
import time
import json
import os
import discord
from discord.ext import tasks
import random
from datetime import datetime
import pytz
from discord.ui import Button, View
import logging
import asyncio
from supabase_client import SupabaseDB
from requests.utils import dict_from_cookiejar, cookiejar_from_dict
from fake_useragent import UserAgent

# Replace credentials import with environment variables
USERNAME = os.environ.get('FILLASEAT_USERNAME')
PASSWORD = os.environ.get('FILLASEAT_PASSWORD')
DISCORD_BOT_TOKEN = os.environ.get('FILLASEAT_DISCORD_BOT_TOKEN')
DISCORD_CHANNEL_ID = int(os.environ.get('FILLASEAT_DISCORD_CHANNEL_ID'))
PST_TIMEZONE = pytz.timezone('America/Los_Angeles')

# URLs
LOGIN_PAGE_URL = 'https://www.fillaseatlasvegas.com/login2.php'
LOGIN_ACTION_URL = 'https://www.fillaseatlasvegas.com/login.php'  # Action URL from the form
EVENTS_URL_TEMPLATE = 'https://www.fillaseatlasvegas.com/account/event_json.php?callback=getEventsSelect_cb&_={timestamp}'

# Cookie persistence - use the volume path if it exists (Docker), else local file
if os.path.exists("/app/data"):
    COOKIES_PATH = "/app/data/fillaseat_cookies.json"
else:
    COOKIES_PATH = "fillaseat_cookies.json"

class FillASeatAuthError(Exception):
	pass

# Create a session to persist cookies
session = requests.Session()

def load_session_cookies(session, path=COOKIES_PATH):
	try:
		if os.path.exists(path):
			with open(path, "r") as f:
				data = json.load(f)
			session.cookies = cookiejar_from_dict(data)
			logger.info(f"Loaded FillASeat cookies from {path}")
	except Exception as e:
		logger.warning(f"Failed to load FillASeat cookies: {e}")

def save_session_cookies(session, path=COOKIES_PATH):
	try:
		with open(path, "w") as f:
			json.dump(dict_from_cookiejar(session.cookies), f)
		logger.info(f"Saved FillASeat cookies to {path}")
	except Exception as e:
		logger.warning(f"Failed to save FillASeat cookies: {e}")

# Load cookies if they exist
load_session_cookies(session)

# Initialize FakeUserAgent
ua = UserAgent()

def get_random_headers():
    """Generate random headers for requests."""
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Referer': LOGIN_PAGE_URL
    }

# Initial headers
headers = get_random_headers()

# Add Pushover notification function
def send_pushover_notification(message, title=None, url=None, image_url=None):
    user_key = os.environ.get('PUSHOVER_USER_KEY')
    api_token = os.environ.get('PUSHOVER_API_TOKEN')
    
    if not user_key or not api_token:
        # Silently return if keys aren't set to avoid log spam
        return

    data = {
        "token": api_token,
        "user": user_key,
        "message": message
    }
    
    if title:
        data["title"] = title
    if url:
        data["url"] = url
        
    files = {}
    if image_url:
        try:
            # We must download the image bytes because Pushover requires the file itself,
            # it cannot fetch from a URL on its own.
            img_response = requests.get(image_url, timeout=5)
            if img_response.status_code == 200:
                # ("filename", file_bytes, "mime_type")
                files["attachment"] = ("show_image.jpg", img_response.content, "image/jpeg")
        except Exception as e:
            logger.error(f"Failed to download image for Pushover: {e}")

    try:
        # If files is provided, requests sends a multipart/form-data request
        response = requests.post("https://api.pushover.net/1/messages.json", data=data, files=files if files else None)
        response.raise_for_status()
        logger.info(f"Pushover notification sent: {title}")
    except Exception as e:
        logger.error(f"Failed to send Pushover notification: {e}")

# Initialize Discord bot
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = discord.Bot(intents=intents)

# Add logging configuration
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.info("FillASeat Bot initializing...")

# Initialize Supabase DB
logger.info("Connecting to Supabase database...")
db = SupabaseDB()
logger.info("Supabase database connection established")

def get_sessid(session, headers):
	"""
	Fetch the login page and extract the sessid value.
	"""
	response = session.get(LOGIN_PAGE_URL, headers=headers)
	if response.status_code != 200:
		raise Exception(f"Failed to retrieve login page. Status code: {response.status_code}")
	
	# Use regex to extract the sessid value
	match = re.search(r'name=["\']sessid["\']\s+value=["\']([^"\']+)["\']', response.text)
	if not match:
		raise Exception("Failed to find sessid in the login form.")
	
	sessid = match.group(1)
	logger.info(f"Successfully retrieved sessid: {sessid[:8]}...")
	return sessid

def login(session, headers, sessid, username, password):
	"""
	Submit the login form with the provided credentials and sessid.
	"""
	logger.info("Attempting to login to FillASeat...")
	payload = {
		'sessid': sessid,
		'username': username,
		'password': password,
		'submit': 'Login'
	}
	
	response = session.post(LOGIN_ACTION_URL, data=payload, headers=headers)
	if response.status_code != 200:
		logger.error(f"Login request failed. Status code: {response.status_code}")
		raise Exception(f"Login request failed. Status code: {response.status_code}")
	
	logger.info("Login request completed successfully")
	return response

def is_login_successful(response):
	"""
	Determine if login was successful by checking for indicators in the response.
	"""
	# Example: Check if the response contains a logout link or specific user content
	if "logout.php" in response.text.lower():
		logger.info("FillASeat login successful - logout link found")
		return True
	# Add more checks as needed based on the website's response after login
	logger.warning("FillASeat login may have failed - logout link not found")
	return False

def fetch_events(session, headers):
	"""
	Fetch and parse events from the event_json.php endpoint.
	"""
	timestamp = int(time.time() * 1000)
	events_url = EVENTS_URL_TEMPLATE.format(timestamp=timestamp)
	
	logger.info(f"Fetching FillASeat events...")
	
	response = session.get(events_url, headers=headers)
	
	# Check for auth errors
	if response.status_code in (401, 403):
		raise FillASeatAuthError(f"Authentication failed with status code: {response.status_code}")
	
	if response.status_code != 200:
		raise Exception(f"Failed to retrieve events. Status code: {response.status_code}")
	
	# Check if response looks like a login page instead of JSONP
	if "login.php" in response.text or 'type="password"' in response.text.lower():
		raise FillASeatAuthError("Response looks like a login page.")
	
	match = re.search(r'getEventsSelect_cb\((.*)\)', response.text, re.DOTALL)
	if not match:
		logger.error("Response does not match expected JSONP format.")
		logger.error("----- Response Start -----")
		logger.error(response.text)
		logger.error("----- Response End -----")
		# If we can't parse JSONP but it wasn't a clear login page, 
		# it might still be an auth issue or just a changed format.
		# For now, we'll treat it as a generic exception unless it's clearly auth.
		raise Exception("Failed to parse JSONP response.")
	
	json_data = match.group(1)
	
	try:
		events = json.loads(json_data)
	except json.JSONDecodeError as e:
		raise Exception(f"JSON decoding failed: {e}")
	
	logger.info(f"Successfully fetched {len(events)} FillASeat events")
	
	return events

def delete_all_fillaseat_shows():
	logger.info("Clearing all current FillASeat shows from database")
	db.delete_all_fillaseat_current_shows()
	logger.info("Database cleared successfully")

def insert_fillaseat_shows(shows):
	logger.info(f"Inserting {len(shows)} current FillASeat shows into database")
	db.insert_fillaseat_current_shows(shows)
	logger.info("Shows inserted successfully")

def initialize_database():
	# Tables are created via Supabase dashboard/SQL
	# This function is kept for compatibility but no longer creates tables
	pass

async def send_discord_message(message_text=None, embeds=None):
	try:
		channel = await bot.fetch_channel(DISCORD_CHANNEL_ID)
		if channel is None:
			logger.error(f"Channel with ID {DISCORD_CHANNEL_ID} not found.")
			return
		if embeds:
			await channel.send(content=message_text, embeds=embeds)
		else:
			await channel.send(content=message_text)
		logger.info("Discord message sent successfully!")
	except Exception as e:
		logger.error(f"Failed to send Discord message. Error: {e}")

async def send_user_dm(user: discord.User, embed: discord.Embed, view: View = None):
	try:
		if view:
			await user.send(embed=embed, view=view)
		else:
			await user.send(embed=embed)
		logger.info(f"Sent DM to user {user.id}")
	except discord.Forbidden:
		logger.warning(f"Cannot send DM to user {user.id}. They might have DMs disabled.")
	except Exception as e:
		logger.error(f"Error sending DM to user {user.id}: {e}")

class BlacklistButton(Button):
	def __init__(self, show_id: str, show_name: str, user_id: int):
		super().__init__(label="Blacklist", style=discord.ButtonStyle.secondary)
		self.show_id = show_id
		self.show_name = show_name
		self.user_id = user_id

	async def callback(self, interaction: discord.Interaction):
		try:
			# Defer the response immediately to prevent timeout
			await interaction.response.defer()
			
			# Check if the user is blacklisting their own message
			if interaction.user.id != self.user_id:
				await interaction.followup.send("You can only blacklist shows for yourself.", ephemeral=True)
				return
			
			try:
				db.add_fillaseat_user_blacklist(interaction.user.id, self.show_id)
				await interaction.followup.send(
					f"**`{self.show_name}`** has been added to your FillASeat blacklist.",
					ephemeral=True
				)
			except Exception as e:
				logger.error(f"Error adding show to FillASeat blacklist: {e}")
				await interaction.followup.send(
					"An error occurred while adding to the blacklist.",
					ephemeral=True
				)
		except Exception as e:
			logger.error(f"Error in BlacklistButton callback: {e}")

def add_to_fillaseat_all_shows(shows):
	logger.info(f"Adding {len(shows)} shows to FillASeat all shows history")
	db.add_to_fillaseat_all_shows(shows)
	logger.info("Shows added to history successfully")

def get_existing_shows():
	return db.get_fillaseat_existing_shows()

async def notify_users_about_new_shows(new_shows):
	if not new_shows:
		logger.info("No new FillASeat shows to notify about")
		return

	logger.info(f"Notifying users about {len(new_shows)} new FillASeat shows")
	# Send notifications to the channel
	for show_id, show_info in new_shows.items():
		embed = discord.Embed(
			title=f"{show_info['name']} (Show ID: {show_id})",
			url=show_info['url'],
			color=discord.Color.red()
		)
		if show_info['image_url']:
			# Validate image URL before setting
			try:
				image_response = session.head(show_info['image_url'], timeout=5)
				if image_response.status_code == 200:
					embed.set_image(url=show_info['image_url'])
				else:
					logger.warning(f"Image not available for show {show_id}: {image_response.status_code}")
			except Exception as e:
				logger.error(f"Error checking image for show {show_id}: {e}")
		
		await send_discord_message(embeds=[embed])

		# Send Pushover notification
		send_pushover_notification(
			message=f"🎟️ {show_info['name']}",
			title="FillASeat Alert",
			url=show_info['url'],
			image_url=show_info.get('image_url')
		)

		logger.info(f"Posted FillASeat show to channel: {show_info['name']}")
		await asyncio.sleep(1)

	# Get users to notify
	logger.info("Gathering users for DM notifications...")
	users_to_notify = set()
	for guild in bot.guilds:
		async for member in guild.fetch_members(limit=None):
			if not member.bot:
				users_to_notify.add(member)

	# Get blacklists and send DMs
	logger.info(f"Found {len(users_to_notify)} users to potentially notify")
	user_blacklists = db.get_fillaseat_user_blacklists_for_shows(list(new_shows.keys()))
	logger.info(f"Retrieved blacklists for {len(user_blacklists)} users")

	for user in users_to_notify:
		blacklisted_show_ids = user_blacklists.get(user.id, set())
		shows_to_notify = {show_id: info for show_id, info in new_shows.items() 
						  if show_id not in blacklisted_show_ids}
		
		for show_id, show_info in shows_to_notify.items():
			embed = discord.Embed(
				title=f"{show_info['name']} (Show ID: {show_id})",
				url=show_info['url']
			)
			if show_info['image_url']:
				embed.set_image(url=show_info['image_url'])
			
			view = View(timeout=3600)
			view.add_item(BlacklistButton(show_id, show_info['name'], user.id))
			
			await send_user_dm(user, embed, view)
			await asyncio.sleep(1)

	logger.info("Completed FillASeat show notifications to all users")

@tasks.loop(minutes=random.randint(2, 3))
async def fillaseat_task():
	current_time = datetime.now(PST_TIMEZONE)
	logger.info(f"FillASeat task started at {current_time.strftime('%Y-%m-%d %H:%M:%S PST')}")
	
	# Randomize start/end window slightly each day/run
	# This uses a simple fixed randomness per cycle, effectively jittering the boundary
	# For more robust daily shifts, we'd need state persistence, but this adds noise.
	start_hour = 6
	end_hour = 17
	
	# Only proceed if we are roughly in the window
	if start_hour <= current_time.hour < end_hour:
		# Add a small chance to skip a cycle entirely to simulate a "break"
		if random.random() < 0.02:  # 2% chance to skip (take a break)
			logger.info("Taking a random break (skipping this cycle) to mimic human behavior.")
			return

		logger.info("Within operating hours (6 AM - 5 PM PST), proceeding with scraping")
		
		# Randomly rotate headers occasionally
		if random.random() < 0.05:  # 5% chance per cycle
			global headers
			headers = get_random_headers()
			logger.info("Rotated user agent and headers")

		try:
			login_needed = False
			events = []
			
			# 1. Try to fetch events using existing session
			try:
				# Occasionally visit the dashboard to look human
				if random.random() < 0.1:  # 10% chance
					try:
						logger.info("Performing random dashboard visit to mimic human behavior...")
						session.get("https://www.fillaseatlasvegas.com/account/index.php", headers=headers)
						await asyncio.sleep(random.uniform(1, 3))  # Pause like a human reading
					except Exception as e:
						logger.warning(f"Random dashboard visit failed: {e}")

				events = fetch_events(session, headers)
				logger.info("FillASeat session appears valid; fetched events without logging in")
			except FillASeatAuthError as e:
				logger.warning(f"FillASeat session appears expired or unauthenticated: {e}")
				login_needed = True
			except Exception as e:
				# Other network or parsing errors can also trigger login as a fallback
				logger.error(f"Error fetching FillASeat events: {e}")
				login_needed = True

			# 2. Login if needed
			if login_needed:
				try:
					# Get sessid and login
					sessid = get_sessid(session, headers)
					login_response = login(session, headers, sessid, USERNAME, PASSWORD)
					
					if is_login_successful(login_response):
						logger.info("FillASeat authentication successful, fetching events...")
						save_session_cookies(session)
						# Short random delay after login
						await asyncio.sleep(random.uniform(2, 5))
						events = fetch_events(session, headers)
					else:
						logger.error("FillASeat login failed, skipping this cycle")
						return
				except Exception as e:
					logger.error(f"Login attempt failed: {e}")
					return

			# 3. Process events
			current_shows = {}
			
			for event in events:
				event_id = event.get('e', 'N/A')
				show_name = event.get('s', 'N/A')
				show_url = f"https://www.fillaseatlasvegas.com/account/event_info.php?eid={event_id}"
				image_url = f"https://static.fillaseat.com/images/events/{event_id}_std.jpg"
				
				current_shows[event_id] = {
					'name': show_name,
					'url': show_url,
					'image_url': image_url
				}
			
			# Get existing shows before updating
			existing_shows = get_existing_shows()
			
			# Find new shows
			new_show_ids = set(current_shows.keys()) - set(existing_shows.keys())
			new_shows = {show_id: current_shows[show_id] for show_id in new_show_ids}
			logger.info(f"Found {len(new_shows)} new shows out of {len(current_shows)} total shows")
			
			# Update database
			add_to_fillaseat_all_shows(current_shows)
			delete_all_fillaseat_shows()
			insert_fillaseat_shows(current_shows)
			
			# Notify users about new shows
			if new_shows:
				logger.info("New shows found! Preparing notifications...")
				# Add small delay to allow images to become available
				await asyncio.sleep(5)
				await notify_users_about_new_shows(new_shows)
			else:
				logger.info("No new shows found in this cycle")

		except Exception as e:
			logger.error(f"An error occurred in fillaseat_task: {e}", exc_info=True)
			await send_discord_message(f"Error in FillASeat bot: {e}")

	else:
		logger.info(f"Outside operating hours (current: {current_time.hour}:00 PST), skipping scrape")

	logger.info("FillASeat task cycle completed")

@fillaseat_task.before_loop
async def before_fillaseat_task():
	logger.info("Waiting for FillASeat bot to be ready...")
	await bot.wait_until_ready()
	logger.info("FillASeat bot is ready, initializing database...")
	initialize_database()  # Initialize the database before starting the task
	logger.info("FillASeat database initialized, starting periodic task...")

# Add your slash commands here
@bot.slash_command(name="fillaseat_blacklist_add", description="Add a show to your FillASeat blacklist")
async def fillaseat_blacklist_add(ctx, show_id: str = discord.Option(description="Show ID to blacklist")):
	user_id = ctx.author.id
	try:
		show_name = db.get_fillaseat_all_shows_name(show_id)
		if show_name:
			db.add_fillaseat_user_blacklist(user_id, show_id)
			await ctx.respond(f"**`{show_name}`** has been added to your FillASeat blacklist.", ephemeral=True)
		else:
			await ctx.respond("Show ID not found in the FillASeat shows list. Please check the ID and try again.", ephemeral=True)
	except Exception as e:
		logger.error(f"Error adding show to FillASeat blacklist: {e}")
		await ctx.respond("An error occurred while adding to the FillASeat blacklist.", ephemeral=True)

@bot.slash_command(name="fillaseat_blacklist_remove", description="Remove a show from your FillASeat blacklist")
async def fillaseat_blacklist_remove(ctx, show_id: str = discord.Option(description="Show ID to remove from blacklist")):
	user_id = ctx.author.id
	try:
		show_name = db.get_fillaseat_current_shows_name(show_id)
		if show_name:
			db.remove_fillaseat_user_blacklist(user_id, show_id)
			await ctx.respond(f"**`{show_name}`** has been removed from your FillASeat blacklist.", ephemeral=True)
		else:
			await ctx.respond("Show ID not found. Please check the ID and try again.", ephemeral=True)
	except Exception as e:
		logger.error(f"Error removing show from FillASeat blacklist: {e}")
		await ctx.respond("An error occurred while removing from the FillASeat blacklist.", ephemeral=True)

@bot.slash_command(name="fillaseat_blacklist_list", description="List all shows in your FillASeat blacklist")
async def fillaseat_blacklist_list(ctx):
	user_id = ctx.author.id
	try:
		show_names = db.get_fillaseat_user_blacklists_names(user_id)
		if show_names:
			await ctx.respond("Your FillASeat blacklisted shows:\n" + "\n".join(show_names), ephemeral=True)
		else:
			await ctx.respond("Your FillASeat blacklist is empty.", ephemeral=True)
	except Exception as e:
		logger.error(f"Error fetching FillASeat blacklist: {e}")
		await ctx.respond("An error occurred while fetching your FillASeat blacklist.", ephemeral=True)

@bot.slash_command(name="fillaseat_all_shows", description="List all FillASeat shows ever seen")
async def fillaseat_all_shows(ctx):
	try:
		all_shows = db.get_fillaseat_all_shows()
		if not all_shows:
			await ctx.respond("No shows found in the database.", ephemeral=True)
			return

		# Create embeds (Discord has a limit of 25 fields per embed)
		embeds = []
		current_embed = discord.Embed(title="All FillASeat Shows History", color=discord.Color.blue())
		field_count = 0
		
		for show in all_shows:
			if field_count == 25:  # Start a new embed when we hit the limit
				embeds.append(current_embed)
				current_embed = discord.Embed(title="All FillASeat Shows History (Continued)", color=discord.Color.blue())
				field_count = 0
			
			current_embed.add_field(
				name=f"{show['name']} (ID: {show['id']})",
				value="\u200b",  # Zero-width space as value
				inline=True
			)
			field_count += 1

		# Add the last embed if it has any fields
		if field_count > 0:
			embeds.append(current_embed)

		# Send all embeds
		for embed in embeds:
			await ctx.respond(embed=embed, ephemeral=True)
	except Exception as e:
		logger.error(f"Error fetching all FillASeat shows: {e}")
		await ctx.respond("An error occurred while fetching the shows.", ephemeral=True)

@bot.slash_command(name="fillaseat_current_shows", description="List currently available FillASeat shows")
async def fillaseat_current_shows(ctx):
	try:
		current_shows = db.get_fillaseat_current_shows()
		if not current_shows:
			await ctx.respond("No current shows available.", ephemeral=True)
			return

		# Create embeds (Discord has a limit of 25 fields per embed)
		embeds = []
		current_embed = discord.Embed(title="Currently Available FillASeat Shows", color=discord.Color.green())
		field_count = 0
		
		for show in current_shows:
			if field_count == 25:  # Start a new embed when we hit the limit
				embeds.append(current_embed)
				current_embed = discord.Embed(title="Currently Available FillASeat Shows (Continued)", color=discord.Color.green())
				field_count = 0
			
			# Add thumbnail if image exists and is accessible
			if show['image_url'] and field_count == 0:  # Only check first show in each embed
				try:
					image_response = session.head(show['image_url'], timeout=5)
					if image_response.status_code == 200:
						current_embed.set_thumbnail(url=show['image_url'])
				except Exception as e:
					logger.error(f"Error checking image for show {show['id']}: {e}")
			
			current_embed.add_field(
				name=f"{show['name']} (ID: {show['id']})",
				value="\u200b",  # Zero-width space as value
				inline=True
			)
			field_count += 1

		# Add the last embed if it has any fields
		if field_count > 0:
			embeds.append(current_embed)

		# Send all embeds
		for embed in embeds:
			await ctx.respond(embed=embed, ephemeral=True)
	except Exception as e:
		logger.error(f"Error fetching current FillASeat shows: {e}")
		await ctx.respond("An error occurred while fetching the shows.", ephemeral=True)

# Bot event handlers
@bot.event
async def on_ready():
	logger.info(f"FillASeat Bot logged in as {bot.user} (ID: {bot.user.id})")
	logger.info(f"Bot is connected to {len(bot.guilds)} guild(s)")
	for guild in bot.guilds:
		logger.info(f"  - {guild.name} (ID: {guild.id}) - {guild.member_count} members")
	
	if not fillaseat_task.is_running():
		logger.info("Starting FillASeat periodic task...")
		fillaseat_task.start()

@bot.event
async def on_connect():
	logger.info("FillASeat Bot connected to Discord")

@bot.event
async def on_disconnect():
	logger.warning("FillASeat Bot disconnected from Discord")

@bot.event
async def on_resumed():
	logger.info("FillASeat Bot resumed connection to Discord")

# Start the task and run the bot
# logger.info("Starting FillASeat periodic task...")
# fillaseat_task.start()
if __name__ == "__main__":
	logger.info("Starting FillASeat Discord bot...")
	bot.run(DISCORD_BOT_TOKEN)