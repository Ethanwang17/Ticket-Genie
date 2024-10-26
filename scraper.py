import os
import time
import logging
import asyncio
import psycopg2
from telegram import Bot
from telegram.constants import ParseMode
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Use environment variables
HOUSESEATS_EMAIL = os.environ.get('HOUSESEATS_EMAIL')
HOUSESEATS_PASSWORD = os.environ.get('HOUSESEATS_PASSWORD')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')  # Your user ID or chat ID
DATABASE_URL = os.environ.get('DATABASE_URL')

def main():
    # Set up Chrome options for Heroku
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run Chrome in headless mode
    chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    chrome_options.binary_location = os.environ.get('GOOGLE_CHROME_BIN', '/app/.apt/usr/bin/google-chrome')

    # Initialize the headless webdriver
    service = Service(executable_path=os.environ.get('CHROMEDRIVER_PATH', '/app/.chromedriver/bin/chromedriver'))
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Set logging level to WARNING to reduce output
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger(__name__)

    def get_db_connection():
        return psycopg2.connect(DATABASE_URL)

    def create_shows_table():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS shows (
                id TEXT PRIMARY KEY,
                name TEXT
            )
        ''')
        conn.commit()
        cur.close()
        conn.close()

    def get_existing_shows():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name FROM shows')
        existing_shows = {row[0]: row[1] for row in cur.fetchall()}
        cur.close()
        conn.close()
        return existing_shows

    def delete_all_shows():
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM shows')
        conn.commit()
        cur.close()
        conn.close()

    def insert_all_shows(shows):
        conn = get_db_connection()
        cur = conn.cursor()
        for show_id, show_name in shows:
            try:
                cur.execute('INSERT INTO shows (id, name) VALUES (%s, %s)', (show_id, show_name))
            except Exception as e:
                logger.error(f"Error inserting show {show_id}: {e}")
        conn.commit()
        cur.close()
        conn.close()

    def initialize_database():
        create_shows_table()

    async def send_telegram_message(message_text):
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        try:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)
            logger.info("Telegram message sent successfully!")
        except Exception as e:
            logger.error(f"Failed to send Telegram message. Error: {e}")

    # Initialize the database
    initialize_database()

    try:
        # Navigate to the login page
        driver.get("https://lv.houseseats.com/login")

        # Wait for the email input field to be visible
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "emailAddress"))
        )

        # Enter your login credentials
        email_field.send_keys(HOUSESEATS_EMAIL)
        password_field = driver.find_element(By.ID, "password")
        password_field.send_keys(HOUSESEATS_PASSWORD)

        # Submit the form
        submit_button = driver.find_element(By.XPATH, "//button[contains(@class, 'btn-orange')]")
        submit_button.click()

        # Wait for the page to load
        time.sleep(5)

        # Get the page source and parse it with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Find the div with id "event-info"
        event_info_div = soup.find('div', id='event-info')

        if event_info_div:
            # Find all panels representing shows
            panels = event_info_div.find_all('div', class_='panel panel-default')

            # Initialize an empty dictionary to store scraped shows
            scraped_shows_dict = {}

            logger.debug(f"Found {len(panels)} show panels")

            for panel in panels:
                heading = panel.find('div', class_='panel-heading')
                if not heading:
                    continue  # Skip if no heading found

                link = heading.find('a', href=lambda href: href and href.startswith('./tickets/view/'))
                if not link:
                    continue  # Skip if no valid link found

                show_name = link.text.strip()
                show_id = link['href'].split('=')[-1]

                # Skip empty show names
                if not show_name or show_name == "[...]":
                    continue

                # Add to dictionary without overwriting existing entries with empty names
                if show_id not in scraped_shows_dict or scraped_shows_dict[show_id] == "[...]":
                    scraped_shows_dict[show_id] = show_name

            # Convert dictionary to list of tuples
            scraped_shows = list(scraped_shows_dict.items())

            # Get existing shows from the database
            existing_shows = get_existing_shows()  # returns dict {id: name}

            # Find new shows
            existing_show_ids = set(existing_shows.keys())
            scraped_show_ids = set(scraped_shows_dict.keys())

            new_show_ids = scraped_show_ids - existing_show_ids

            new_shows = [(show_id, scraped_shows_dict[show_id]) for show_id in new_show_ids]

            logger.debug(f"Identified {len(new_shows)} new shows")

            # Now erase the database and rewrite it with all the shows just found
            delete_all_shows()
            insert_all_shows(scraped_shows)

            # Only send a message if there are new shows
            if new_shows:
                # Prepare the message content
                message_text = "New shows found:\n"
                for show_id, show_name in new_shows:
                    message_text += f"- {show_name}\n"

                # Send the Telegram message
                asyncio.run(send_telegram_message(message_text))

        else:
            warning_message = "Warning: Could not find the event-info div. The page structure might have changed."
            logger.warning(warning_message)
            asyncio.run(send_telegram_message(warning_message))

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        asyncio.run(send_telegram_message(f"An error occurred: {e}"))

    finally:
        # Don't forget to close the browser when you're done
        driver.quit()

    print("Scraping complete!")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(120)  # Sleep for 2 minutes