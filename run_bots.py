# Debug imports and startup
import os
import sys
import traceback
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("Starting Ticket Genie Bot Runner")
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
	import threading
	import time
	
	logger.info("Importing bot modules...")
	import house_seats_bot
	import fill_a_seat_bot
	
	logger.info("All imports successful!")
	
	def run_house_seats_bot():
		thread_logger = logging.getLogger("HouseSeats-Thread")
		try:
			thread_logger.info("Starting HouseSeats bot in dedicated thread...")
			house_seats_bot.bot.run(os.environ.get('HOUSESEATS_DISCORD_BOT_TOKEN'))
		except Exception as e:
			thread_logger.error(f"Critical error in HouseSeats bot: {e}", exc_info=True)

	def run_fill_a_seat_bot():
		thread_logger = logging.getLogger("FillASeat-Thread")
		try:
			thread_logger.info("Starting FillASeat bot in dedicated thread...")
			fill_a_seat_bot.bot.run(os.environ.get('FILLASEAT_DISCORD_BOT_TOKEN'))
		except Exception as e:
			thread_logger.error(f"Critical error in FillASeat bot: {e}", exc_info=True)

	# Start both bots in separate threads
	logger.info("Creating bot threads...")
	house_seats_thread = threading.Thread(target=run_house_seats_bot, name="HouseSeats-Bot")
	fill_a_seat_thread = threading.Thread(target=run_fill_a_seat_bot, name="FillASeat-Bot")

	logger.info("Starting HouseSeats bot thread...")
	house_seats_thread.start()
	
	logger.info("Starting FillASeat bot thread...")
	fill_a_seat_thread.start()

	logger.info("✓ Both bots started successfully!")
	logger.info("Main runner will monitor bot health every 60 seconds...")
	
	# Keep the main thread alive and monitor bot health
	try:
		heartbeat_count = 0
		while True:
			time.sleep(60)
			heartbeat_count += 1
			
			# Check thread health
			houseseats_alive = house_seats_thread.is_alive()
			fillaseat_alive = fill_a_seat_thread.is_alive()
			
			logger.info(f"[Heartbeat #{heartbeat_count}] HouseSeats: {'✓ Running' if houseseats_alive else '✗ STOPPED'}, "
					   f"FillASeat: {'✓ Running' if fillaseat_alive else '✗ STOPPED'}")
			
			# Log warning if any bot has stopped
			if not houseseats_alive:
				logger.error("HouseSeats bot thread has stopped unexpectedly!")
			if not fillaseat_alive:
				logger.error("FillASeat bot thread has stopped unexpectedly!")
			
			# If both bots have stopped, exit
			if not houseseats_alive and not fillaseat_alive:
				logger.error("Both bots have stopped! Exiting...")
				break
				
	except KeyboardInterrupt:
		logger.info("Received shutdown signal (Ctrl+C)...")
		logger.info("Shutting down bot runner...")

except Exception as e:
	logger.critical(f"Fatal error during startup: {e}", exc_info=True)
	logger.critical("Bot runner failed to start - exiting with code 1")
	sys.exit(1)