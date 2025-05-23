import os
from supabase import create_client, Client
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class SupabaseDB:
    def __init__(self):
        print("Initializing SupabaseDB...")
        
        # Get Supabase credentials from environment variables
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_KEY')  # Use service key for backend operations
        
        print(f"SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'}")
        print(f"SUPABASE_SERVICE_KEY: {'SET' if supabase_key else 'NOT SET'}")
        
        if not supabase_url or not supabase_key:
            error_msg = "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set"
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        try:
            print("Creating Supabase client...")
            self.client: Client = create_client(supabase_url, supabase_key)
            print("Supabase client created successfully!")
        except Exception as e:
            print(f"ERROR creating Supabase client: {e}")
            raise
    
    def create_tables(self):
        """Create all necessary tables for both bots"""
        # This will be handled via Supabase dashboard/SQL editor
        # We'll define the schema there
        pass
    
    # HouseSeats operations
    def get_houseseats_existing_shows(self) -> Dict[str, Dict]:
        """Get existing HouseSeats shows"""
        try:
            response = self.client.table('houseseats_current_shows').select('*').execute()
            return {row['id']: {'name': row['name'], 'url': row['url'], 'image_url': row['image_url']} 
                   for row in response.data}
        except Exception as e:
            logger.error(f"Error fetching existing HouseSeats shows: {e}")
            return {}
    
    def delete_all_houseseats_current_shows(self):
        """Delete all current HouseSeats shows"""
        try:
            response = self.client.table('houseseats_current_shows').delete().neq('id', '').execute()
            logger.info("Deleted all current HouseSeats shows")
        except Exception as e:
            logger.error(f"Error deleting current HouseSeats shows: {e}")
    
    def insert_houseseats_current_shows(self, shows: Dict[str, Dict]):
        """Insert current HouseSeats shows"""
        try:
            data = [
                {
                    'id': show_id,
                    'name': show_info['name'],
                    'url': show_info['url'],
                    'image_url': show_info['image_url']
                }
                for show_id, show_info in shows.items()
            ]
            if data:
                response = self.client.table('houseseats_current_shows').insert(data).execute()
                logger.info(f"Inserted {len(data)} HouseSeats current shows")
        except Exception as e:
            logger.error(f"Error inserting HouseSeats current shows: {e}")
    
    def add_to_houseseats_all_shows(self, shows: Dict[str, Dict]):
        """Add shows to HouseSeats all shows table (with upsert)"""
        try:
            data = [
                {
                    'id': show_id,
                    'name': show_info['name'],
                    'url': show_info['url'],
                    'image_url': show_info['image_url']
                }
                for show_id, show_info in shows.items()
            ]
            if data:
                response = self.client.table('houseseats_all_shows').upsert(data, on_conflict='id').execute()
                logger.info(f"Upserted {len(data)} HouseSeats all shows")
        except Exception as e:
            logger.error(f"Error upserting HouseSeats all shows: {e}")
    
    def add_houseseats_user_blacklist(self, user_id: int, show_id: str):
        """Add a show to user's HouseSeats blacklist"""
        try:
            data = {'user_id': user_id, 'show_id': show_id}
            response = self.client.table('houseseats_user_blacklists').upsert(data, on_conflict='user_id,show_id').execute()
            logger.info(f"Added show {show_id} to user {user_id} HouseSeats blacklist")
        except Exception as e:
            logger.error(f"Error adding to HouseSeats blacklist: {e}")
    
    def remove_houseseats_user_blacklist(self, user_id: int, show_id: str):
        """Remove a show from user's HouseSeats blacklist"""
        try:
            response = self.client.table('houseseats_user_blacklists').delete().eq('user_id', user_id).eq('show_id', show_id).execute()
            logger.info(f"Removed show {show_id} from user {user_id} HouseSeats blacklist")
        except Exception as e:
            logger.error(f"Error removing from HouseSeats blacklist: {e}")
    
    def get_houseseats_user_blacklists(self, user_id: int) -> List[str]:
        """Get user's HouseSeats blacklisted shows"""
        try:
            response = self.client.table('houseseats_user_blacklists').select('show_id').eq('user_id', user_id).execute()
            return [row['show_id'] for row in response.data]
        except Exception as e:
            logger.error(f"Error fetching HouseSeats user blacklists: {e}")
            return []
    
    def get_houseseats_user_blacklists_for_shows(self, show_ids: List[str]) -> Dict[int, set]:
        """Get all user blacklists for specific show IDs"""
        try:
            response = self.client.table('houseseats_user_blacklists').select('user_id, show_id').in_('show_id', show_ids).execute()
            user_blacklists = {}
            for row in response.data:
                user_id = row['user_id']
                show_id = row['show_id']
                if user_id not in user_blacklists:
                    user_blacklists[user_id] = set()
                user_blacklists[user_id].add(show_id)
            return user_blacklists
        except Exception as e:
            logger.error(f"Error fetching HouseSeats user blacklists for shows: {e}")
            return {}
    
    def get_houseseats_all_shows_name(self, show_id: str) -> Optional[str]:
        """Get show name by ID from HouseSeats all shows"""
        try:
            response = self.client.table('houseseats_all_shows').select('name').eq('id', show_id).execute()
            if response.data:
                return response.data[0]['name']
            return None
        except Exception as e:
            logger.error(f"Error fetching HouseSeats show name: {e}")
            return None
    
    def get_houseseats_current_shows_name(self, show_id: str) -> Optional[str]:
        """Get show name by ID from HouseSeats current shows"""
        try:
            response = self.client.table('houseseats_current_shows').select('name').eq('id', show_id).execute()
            if response.data:
                return response.data[0]['name']
            return None
        except Exception as e:
            logger.error(f"Error fetching HouseSeats current show name: {e}")
            return None
    
    def get_houseseats_user_blacklists_names(self, user_id: int) -> List[str]:
        """Get names of user's blacklisted HouseSeats shows"""
        try:
            response = self.client.table('houseseats_user_blacklists').select('houseseats_all_shows(name)').eq('user_id', user_id).execute()
            return [f"• **`{row['houseseats_all_shows']['name']}`**" for row in response.data if row['houseseats_all_shows']]
        except Exception as e:
            logger.error(f"Error fetching HouseSeats user blacklist names: {e}")
            # Fallback method
            try:
                blacklist_response = self.client.table('houseseats_user_blacklists').select('show_id').eq('user_id', user_id).execute()
                show_ids = [row['show_id'] for row in blacklist_response.data]
                if show_ids:
                    shows_response = self.client.table('houseseats_all_shows').select('name').in_('id', show_ids).execute()
                    return [f"• **`{row['name']}`**" for row in shows_response.data]
                return []
            except Exception as e2:
                logger.error(f"Error in fallback method: {e2}")
                return []
    
    def get_houseseats_current_shows(self) -> List[Dict]:
        """Get all HouseSeats current shows"""
        try:
            response = self.client.table('houseseats_current_shows').select('*').order('name').execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching HouseSeats current shows: {e}")
            return []
    
    def get_houseseats_all_shows(self) -> List[Dict]:
        """Get all HouseSeats shows ever seen"""
        try:
            response = self.client.table('houseseats_all_shows').select('*').order('first_seen_date', desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching HouseSeats all shows: {e}")
            return []
    
    # FillASeat operations
    def get_fillaseat_existing_shows(self) -> Dict[str, Dict]:
        """Get existing FillASeat shows"""
        try:
            response = self.client.table('fillaseat_current_shows').select('*').execute()
            return {row['id']: {'name': row['name'], 'url': row['url'], 'image_url': row['image_url']} 
                   for row in response.data}
        except Exception as e:
            logger.error(f"Error fetching existing FillASeat shows: {e}")
            return {}
    
    def delete_all_fillaseat_current_shows(self):
        """Delete all current FillASeat shows"""
        try:
            response = self.client.table('fillaseat_current_shows').delete().neq('id', '').execute()
            logger.info("Deleted all current FillASeat shows")
        except Exception as e:
            logger.error(f"Error deleting current FillASeat shows: {e}")
    
    def insert_fillaseat_current_shows(self, shows: Dict[str, Dict]):
        """Insert current FillASeat shows"""
        try:
            data = [
                {
                    'id': show_id,
                    'name': show_info['name'],
                    'url': show_info['url'],
                    'image_url': show_info['image_url']
                }
                for show_id, show_info in shows.items()
            ]
            if data:
                response = self.client.table('fillaseat_current_shows').insert(data).execute()
                logger.info(f"Inserted {len(data)} FillASeat current shows")
        except Exception as e:
            logger.error(f"Error inserting FillASeat current shows: {e}")
    
    def add_to_fillaseat_all_shows(self, shows: Dict[str, Dict]):
        """Add shows to FillASeat all shows table (with upsert)"""
        try:
            data = [
                {
                    'id': show_id,
                    'name': show_info['name'],
                    'url': show_info['url'],
                    'image_url': show_info['image_url']
                }
                for show_id, show_info in shows.items()
            ]
            if data:
                response = self.client.table('fillaseat_all_shows').upsert(data, on_conflict='id').execute()
                logger.info(f"Upserted {len(data)} FillASeat all shows")
        except Exception as e:
            logger.error(f"Error upserting FillASeat all shows: {e}")
    
    def add_fillaseat_user_blacklist(self, user_id: int, show_id: str):
        """Add a show to user's FillASeat blacklist"""
        try:
            data = {'user_id': user_id, 'show_id': show_id}
            response = self.client.table('fillaseat_user_blacklists').upsert(data, on_conflict='user_id,show_id').execute()
            logger.info(f"Added show {show_id} to user {user_id} FillASeat blacklist")
        except Exception as e:
            logger.error(f"Error adding to FillASeat blacklist: {e}")
    
    def remove_fillaseat_user_blacklist(self, user_id: int, show_id: str):
        """Remove a show from user's FillASeat blacklist"""
        try:
            response = self.client.table('fillaseat_user_blacklists').delete().eq('user_id', user_id).eq('show_id', show_id).execute()
            logger.info(f"Removed show {show_id} from user {user_id} FillASeat blacklist")
        except Exception as e:
            logger.error(f"Error removing from FillASeat blacklist: {e}")
    
    def get_fillaseat_user_blacklists(self, user_id: int) -> List[str]:
        """Get user's FillASeat blacklisted shows"""
        try:
            response = self.client.table('fillaseat_user_blacklists').select('show_id').eq('user_id', user_id).execute()
            return [row['show_id'] for row in response.data]
        except Exception as e:
            logger.error(f"Error fetching FillASeat user blacklists: {e}")
            return []
    
    def get_fillaseat_user_blacklists_for_shows(self, show_ids: List[str]) -> Dict[int, set]:
        """Get all user blacklists for specific show IDs"""
        try:
            response = self.client.table('fillaseat_user_blacklists').select('user_id, show_id').in_('show_id', show_ids).execute()
            user_blacklists = {}
            for row in response.data:
                user_id = row['user_id']
                show_id = row['show_id']
                if user_id not in user_blacklists:
                    user_blacklists[user_id] = set()
                user_blacklists[user_id].add(show_id)
            return user_blacklists
        except Exception as e:
            logger.error(f"Error fetching FillASeat user blacklists for shows: {e}")
            return {}
    
    def get_fillaseat_all_shows_name(self, show_id: str) -> Optional[str]:
        """Get show name by ID from FillASeat all shows"""
        try:
            response = self.client.table('fillaseat_all_shows').select('name').eq('id', show_id).execute()
            if response.data:
                return response.data[0]['name']
            return None
        except Exception as e:
            logger.error(f"Error fetching FillASeat show name: {e}")
            return None
    
    def get_fillaseat_current_shows_name(self, show_id: str) -> Optional[str]:
        """Get show name by ID from FillASeat current shows"""
        try:
            response = self.client.table('fillaseat_current_shows').select('name').eq('id', show_id).execute()
            if response.data:
                return response.data[0]['name']
            return None
        except Exception as e:
            logger.error(f"Error fetching FillASeat current show name: {e}")
            return None
    
    def get_fillaseat_user_blacklists_names(self, user_id: int) -> List[str]:
        """Get names of user's blacklisted FillASeat shows"""
        try:
            response = self.client.table('fillaseat_user_blacklists').select('fillaseat_all_shows(name)').eq('user_id', user_id).execute()
            return [f"• **`{row['fillaseat_all_shows']['name']}`**" for row in response.data if row['fillaseat_all_shows']]
        except Exception as e:
            logger.error(f"Error fetching FillASeat user blacklist names: {e}")
            # Fallback method
            try:
                blacklist_response = self.client.table('fillaseat_user_blacklists').select('show_id').eq('user_id', user_id).execute()
                show_ids = [row['show_id'] for row in blacklist_response.data]
                if show_ids:
                    shows_response = self.client.table('fillaseat_all_shows').select('name').in_('id', show_ids).execute()
                    return [f"• **`{row['name']}`**" for row in shows_response.data]
                return []
            except Exception as e2:
                logger.error(f"Error in fallback method: {e2}")
                return []
    
    def get_fillaseat_current_shows(self) -> List[Dict]:
        """Get all FillASeat current shows"""
        try:
            response = self.client.table('fillaseat_current_shows').select('*').order('name').execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching FillASeat current shows: {e}")
            return []
    
    def get_fillaseat_all_shows(self) -> List[Dict]:
        """Get all FillASeat shows ever seen"""
        try:
            response = self.client.table('fillaseat_all_shows').select('*').order('first_seen_date', desc=True).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching FillASeat all shows: {e}")
            return [] 