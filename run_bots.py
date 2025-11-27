# Debug imports and startup
import os
import sys
import logging
import asyncio
from datetime import datetime

# Setup logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("Starting Ticket Genie Bot Runner (Asyncio Version)")
logger.info("=" * 50)
logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Check environment variables
logger.info("Checking environment variables...")
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
fillaseat_token = os.environ.get('FILLASEAT_DISCORD_BOT_TOKEN')
houseseats_token = os.environ.get('HOUSESEATS_DISCORD_BOT_TOKEN')

logger.info(f"SUPABASE_URL: {'✓ SET' if supabase_url else '✗ NOT SET'}")
logger.info(f"SUPABASE_SERVICE_KEY: {'✓ SET' if supabase_key else '✗ NOT SET'}")
logger.info(f"FILLASEAT_DISCORD_BOT_TOKEN: {'✓ SET' if fillaseat_token else '✗ NOT SET'}")
logger.info(f"HOUSESEATS_DISCORD_BOT_TOKEN: {'✓ SET' if houseseats_token else '✗ NOT SET'}")

try:
	logger.info("Importing required modules...")
	
	# Fix for macOS asyncio loop issues if running locally
	if sys.platform == 'darwin':
		try:
			asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
		except Exception:
			pass
	
	logger.info("Importing bot modules...")
	import house_seats_bot
	import fill_a_seat_bot
	
	logger.info("All imports successful!")
	
	async def main():
		if not fillaseat_token or not houseseats_token:
			logger.critical("Bot tokens are missing! Exiting.")
			return

		logger.info("Starting bots...")

		# Create tasks for both bots
		# We use bot.start() instead of bot.run() because bot.run() is blocking and creates its own loop handling
		# running multiple bots in the same process requires sharing the asyncio loop
		tasks = [
			house_seats_bot.bot.start(houseseats_token),
			fill_a_seat_bot.bot.start(fillaseat_token)
		]

		try:
			await asyncio.gather(*tasks)
		except Exception as e:
			logger.error(f"Error running bots: {e}", exc_info=True)

	if __name__ == "__main__":
		try:
			asyncio.run(main())
		except KeyboardInterrupt:
			logger.info("Received shutdown signal (Ctrl+C). Exiting...")
		except Exception as e:
			logger.critical(f"Fatal error during startup: {e}", exc_info=True)
			logger.critical("Bot runner failed to start - exiting with code 1")
			sys.exit(1)

except Exception as e:
	logger.critical(f"Fatal error during import or setup: {e}", exc_info=True)
	sys.exit(1)
