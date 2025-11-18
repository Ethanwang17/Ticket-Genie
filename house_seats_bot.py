import os
import time
import logging
import asyncio
import discord
from discord.ext import tasks
import requests
import re
from discord.ui import Button, View
import pytz
from datetime import datetime
import random
import html
from supabase_client import SupabaseDB

# environment variables
HOUSESEATS_EMAIL = os.environ.get('HOUSESEATS_EMAIL')
HOUSESEATS_PASSWORD = os.environ.get('HOUSESEATS_PASSWORD')
DISCORD_BOT_TOKEN = os.environ.get('HOUSESEATS_DISCORD_BOT_TOKEN')
DISCORD_CHANNEL_ID = int(os.environ.get('HOUSESEATS_DISCORD_CHANNEL_ID'))

# Set logging level to WARNING to reduce output
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize Discord bot with necessary intents and application commands
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = discord.Bot(intents=intents)

# Add this constant with the other environment variables
PST_TIMEZONE = pytz.timezone('America/Los_Angeles')

# Initialize Supabase DB
db = SupabaseDB()

def get_existing_shows():
	return db.get_houseseats_existing_shows()

def delete_all_current_houseseats_shows():
	db.delete_all_houseseats_current_shows()

def insert_all_current_houseseats_shows(shows):
	db.insert_houseseats_current_shows(shows)

def add_to_houseseats_all_shows(shows):
	db.add_to_houseseats_all_shows(shows)

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

def scrape_and_process():
	# Initialize the database
	initialize_database()

	try:
		# Base URLs
		login_url = 'https://lv.houseseats.com/member/index.bv'
		base_img_url = 'https://lv.houseseats.com/resources/media/'
		base_show_url = 'https://lv.houseseats.com/member/tickets/view/'
		
		# Create a session object to maintain cookies
		session = requests.Session()
		
		# Prepare login data
		login_data = {
			'submit': 'login',
			'lastplace': '',
			'email': HOUSESEATS_EMAIL,
			'password': HOUSESEATS_PASSWORD
		}
		
		headers = {
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
			'Accept': 'application/json, text/plain, */*',
			'Accept-Language': 'en-US,en;q=0.9',
			'Referer': 'https://lv.houseseats.com/',
		}

		# Send POST request to login
		response = session.post(login_url, data=login_data, headers=headers)
		
		if response.status_code != 200:
			raise Exception(f"Login failed with status code: {response.status_code}")

		# Fetch the upcoming shows page
		shows_url = 'https://lv.houseseats.com/member/ajax/upcoming-shows.bv?supersecret=&search=&sortField=&startMonthYear=&endMonthYear=&startDate=&endDate=&start=0'
		shows_response = session.get(shows_url, headers=headers)
		
		# Find all show titles and IDs within h1 tags
		pattern = r'<h1><a href="./tickets/view/\?showid=(\d+)">(.*?)</a></h1>'
		shows = re.findall(pattern, shows_response.text)
		
		# Create dictionary for scraped shows
		scraped_shows_dict = {}
		for show_id, show_name in shows:
			show_name = html.unescape(show_name.strip())
			if show_name and 'See All Dates' not in show_name:
				show_url = f"{base_show_url}?showid={show_id}"
				image_url = f"{base_img_url}{show_id}.jpg"
				
				scraped_shows_dict[show_id] = {
					'name': show_name,
					'url': show_url,
					'image_url': image_url
				}

		# After scraping shows and before checking for new ones
		add_to_houseseats_all_shows(scraped_shows_dict)

		# Get existing shows from the database
		existing_shows = get_existing_shows()

		# Find new shows
		existing_show_ids = set(existing_shows.keys())
		scraped_show_ids = set(scraped_shows_dict.keys())
		new_show_ids = scraped_show_ids - existing_show_ids
		new_shows = {show_id: scraped_shows_dict[show_id] for show_id in new_show_ids}

		# Now erase the database and rewrite it with all the shows just found
		delete_all_current_houseseats_shows()
		insert_all_current_houseseats_shows(scraped_shows_dict)

		# Notify users via DMs if there are new shows
		if new_shows:
			asyncio.run_coroutine_threadsafe(
				notify_users_about_new_shows(new_shows),
				bot.loop
			)

	except Exception as e:
		error_message = f"An error occurred: {e}"
		logger.error(error_message)
		asyncio.run_coroutine_threadsafe(
			send_discord_message(message_text=error_message),
			bot.loop
		)

# Modify the BlacklistButton class to include show_name
class BlacklistButton(Button):
	def __init__(self, show_id: str, show_name: str, user_id: int):
		super().__init__(
			label="🚫 Blacklist Show",
			style=discord.ButtonStyle.primary,
			custom_id=f"blacklist_{show_id}_{user_id}"  # Unique custom_id
		)
		self.show_id = show_id
		self.show_name = show_name  # Store the show name
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
				db.add_houseseats_user_blacklist(interaction.user.id, self.show_id)
				await interaction.followup.send(
					f"**`{self.show_name}`** has been added to your blacklist.",
					ephemeral=True
				)
			except Exception as e:
				logger.error(f"Error adding show to blacklist: {e}")
				await interaction.followup.send(
					"An error occurred while adding to the blacklist.",
					ephemeral=True
				)

		except Exception as e:
			logger.error(f"Error in BlacklistButton callback: {e}")

active_views = []

async def notify_users_about_new_shows(new_shows):
	logger.debug(f"Notifying users about {len(new_shows)} new shows")

	# Send public notification to the main channel
	for show_id, show_info in new_shows.items():
		embed = discord.Embed(
			title=f"{show_info['name']} (Show ID: {show_id})",
			url=show_info['url'],
			color=discord.Color.red()
		)
		if show_info['image_url']:
			embed.set_image(url=show_info['image_url'])
		
		await send_discord_message(embeds=[embed])
		# Add a short delay to respect rate limits
		await asyncio.sleep(1)

	# Continue with existing DM notification logic...
	users_to_notify = set()
	for guild in bot.guilds:
		async for member in guild.fetch_members(limit=None):
			if not member.bot:
				users_to_notify.add(member)

	# Fetch blacklists
	user_blacklists = db.get_houseseats_user_blacklists_for_shows(list(new_shows.keys()))

	# Iterate over users and send DMs excluding blacklisted shows
	for user in users_to_notify:
		blacklisted_show_ids = user_blacklists.get(user.id, set())
		shows_to_notify = {show_id: info for show_id, info in new_shows.items() if show_id not in blacklisted_show_ids}
		logger.debug(f"User {user.id} will be notified about shows: {list(shows_to_notify.keys())}")
		if shows_to_notify:
			for show_id, show_info in shows_to_notify.items():
				embed = discord.Embed(
					title=f"{show_info['name']} (Show ID: {show_id})",
					url=show_info['url']
				)
				if show_info['image_url']:
					embed.set_image(url=show_info['image_url'])
				
				# Create a view with the blacklist button
				view = View(timeout=3600)  # 1 hour timeout
				blacklist_button = BlacklistButton(show_id, show_info['name'], user.id)  # Pass show_name
				view.add_item(blacklist_button)

				# Keep a reference to the view
				active_views.append(view)
				
				# Optionally, remove the view from active_views after timeout
				async def remove_view_after_timeout(view):
					await asyncio.sleep(view.timeout)
					if view in active_views:
						active_views.remove(view)
				
				asyncio.create_task(remove_view_after_timeout(view))

				# Send the message with the view
				await send_user_dm(user, embed, view)
				await asyncio.sleep(1)

@tasks.loop(minutes=random.randint(2, 3))
async def scraping_task():
	# Get current time in PST
	current_time = datetime.now(PST_TIMEZONE)
	
	# Check if current time is between 6 AM and 5 PM PST
	if 6 <= current_time.hour < 20:
		await asyncio.to_thread(scrape_and_process)
	else:
		logger.debug("Outside of operating hours (8 AM - 5 PM PST). Skipping scrape.")

@scraping_task.before_loop
async def before_scraping_task():
	await bot.wait_until_ready()

# Start the task when the bot is ready
scraping_task.start()

@bot.slash_command(name="blacklist_add", description="Add a show to your blacklist")
async def blacklist_add(ctx, show_id: str = discord.Option(description="Show ID to blacklist")):
	user_id = ctx.author.id
	try:
		# CHANGE: Fetch the show name from the all_shows table instead of shows
		show_name = db.get_houseseats_all_shows_name(show_id)
		if show_name:
			db.add_houseseats_user_blacklist(user_id, show_id)
			await ctx.respond(f"**`{show_name}`** has been added to your blacklist.", ephemeral=True)
		else:
			# CHANGE: Updated error message to specify all_shows
			await ctx.respond("Show ID not found in the all shows list. Please check the ID and try again.", ephemeral=True)
	except Exception as e:
		logger.error(f"Error adding show to blacklist: {e}")
		await ctx.respond("An error occurred while adding to the blacklist.", ephemeral=True)

@bot.slash_command(name="blacklist_remove", description="Remove a show from your blacklist")
async def blacklist_remove(ctx, show_id: str = discord.Option(description="Show ID to remove from blacklist")):
	user_id = ctx.author.id
	try:
		# Fetch the show name from the database
		show_name = db.get_houseseats_current_shows_name(show_id)
		if show_name:
			db.remove_houseseats_user_blacklist(user_id, show_id)
			await ctx.respond(f"**`{show_name}`** has been removed from your blacklist.", ephemeral=True)
		else:
			await ctx.respond("Show ID not found. Please check the ID and try again.", ephemeral=True)
	except Exception as e:
		logger.error(f"Error removing show from blacklist: {e}")
		await ctx.respond("An error occurred while removing from the blacklist.", ephemeral=True)

@bot.slash_command(name="blacklist_list", description="List all shows in your blacklist")
async def blacklist_list(ctx):
	user_id = ctx.author.id
	try:
		# Fetch show names based on show_ids from all shows table
		show_names = db.get_houseseats_user_blacklists_names(user_id)
		if show_names:
			await ctx.respond("Your blacklisted shows:\n" + "\n".join(show_names), ephemeral=True)
		else:
			await ctx.respond("Your blacklist is empty.", ephemeral=True)
	except Exception as e:
		logger.error(f"Error fetching blacklist: {e}")
		await ctx.respond("An error occurred while fetching your blacklist.", ephemeral=True)

@bot.slash_command(name="houseseats_all_shows", description="List all shows ever seen")
async def houseseats_all_shows(ctx):
	try:
		shows = db.get_houseseats_all_shows()
		
		if not shows:
			await ctx.respond("No shows found in the database.", ephemeral=True)
			return

		# Create embeds (Discord has a limit of 25 fields per embed)
		embeds = []
		current_embed = discord.Embed(title="All Shows History", color=discord.Color.blue())
		field_count = 0
		
		for show in shows:
			if field_count == 25:  # Start a new embed when we hit the limit
				embeds.append(current_embed)
				current_embed = discord.Embed(title="All Shows History (Continued)", color=discord.Color.blue())
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
		logger.error(f"Error fetching all shows: {e}")
		await ctx.respond("An error occurred while fetching the shows.", ephemeral=True)

@bot.slash_command(name="current_shows", description="List currently available shows")
async def current_shows(ctx):
	try:
		shows = db.get_houseseats_current_shows()
		
		if not shows:
			await ctx.respond("No current shows available.", ephemeral=True)
			return

		# Create embeds (Discord has a limit of 25 fields per embed)
		embeds = []
		current_embed = discord.Embed(title="Currently Available Shows", color=discord.Color.green())
		field_count = 0
		
		for show in shows:
			if field_count == 25:  # Start a new embed when we hit the limit
				embeds.append(current_embed)
				current_embed = discord.Embed(title="Currently Available Shows (Continued)", color=discord.Color.green())
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
		logger.error(f"Error fetching current shows: {e}")
		await ctx.respond("An error occurred while fetching the shows.", ephemeral=True)

# Run the bot
bot.run(DISCORD_BOT_TOKEN)