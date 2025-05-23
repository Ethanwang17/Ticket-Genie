# Debug imports and startup
import os
import sys
import traceback

print("Starting Ticket Genie bots...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Check environment variables
print("Checking environment variables...")
supabase_url = os.environ.get('SUPABASE_URL')
supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')
print(f"SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'}")
print(f"SUPABASE_SERVICE_KEY: {'SET' if supabase_key else 'NOT SET'}")

try:
	print("Importing modules...")
	import threading
	import time
	
	print("Importing bot modules...")
	import house_seats_bot
	import fill_a_seat_bot
	
	print("All imports successful!")
	
	def run_house_seats_bot():
		try:
			print("Starting HouseSeats bot...")
			house_seats_bot.bot.run(os.environ.get('HOUSESEATS_DISCORD_BOT_TOKEN'))
		except Exception as e:
			print(f"Error in HouseSeats bot: {e}")
			traceback.print_exc()

	def run_fill_a_seat_bot():
		try:
			print("Starting FillASeat bot...")
			fill_a_seat_bot.bot.run(os.environ.get('FILLASEAT_DISCORD_BOT_TOKEN'))
		except Exception as e:
			print(f"Error in FillASeat bot: {e}")
			traceback.print_exc()

	# Start both bots in separate threads
	house_seats_thread = threading.Thread(target=run_house_seats_bot)
	fill_a_seat_thread = threading.Thread(target=run_fill_a_seat_bot)

	house_seats_thread.start()
	fill_a_seat_thread.start()

	print("Both bots started successfully!")
	
	# Keep the main thread alive
	try:
		while True:
			time.sleep(60)
			print("Main thread heartbeat - bots are running...")
	except KeyboardInterrupt:
		print("Shutting down...")

except Exception as e:
	print(f"Fatal error during startup: {e}")
	traceback.print_exc()
	sys.exit(1)