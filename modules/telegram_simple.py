"""
Simple Telegram API module
"""
import asyncio
import logging
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest

class SimpleTelegramClient:
    """Simplified Telegram client for monitoring"""
    
    def __init__(self, api_id, api_hash, session_name="drug_monitor"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client = None
        self.is_connected = False
    
    async def connect(self):
        """Connect to Telegram"""
        try:
            self.client = TelegramClient(
                self.session_name,
                self.api_id,
                self.api_hash
            )
            
            await self.client.start()
            self.is_connected = True
            logging.info("Telegram API connected successfully")
            return True
        except Exception as e:
            logging.error(f"Telegram connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            logging.info("Telegram API disconnected")
    
    async def get_channel_info(self, channel_username):
        """Get basic channel info"""
        try:
            channel = await self.client.get_entity(channel_username)
            full_channel = await self.client(GetFullChannelRequest(channel))
            
            return {
                'username': channel.username,
                'title': channel.title,
                'id': channel.id,
                'participants_count': getattr(full_channel, 'participants_count', 0),
                'description': getattr(full_channel, 'about', ''),
                'scraped_at': '2024-01-01T00:00:00'  # Placeholder
            }
        except Exception as e:
            logging.warning(f"Could not get channel {channel_username}: {e}")
            return None
    
    async def fetch_messages(self, channel_username, limit=50):
        """Fetch messages from a channel"""
        messages = []
        
        try:
            channel = await self.client.get_entity(channel_username)
            
            async for message in self.client.iter_messages(channel, limit=limit):
                if not message.message:
                    continue
                
                msg_data = {
                    'id': message.id,
                    'date': message.date.isoformat() if hasattr(message.date, 'isoformat') else str(message.date),
                    'text': message.message,
                    'views': getattr(message, 'views', 0),
                    'channel': channel_username
                }
                
                messages.append(msg_data)
            
            logging.info(f"Fetched {len(messages)} messages from {channel_username}")
            return messages
            
        except Exception as e:
            logging.error(f"Error fetching messages from {channel_username}: {e}")
            return []