"""
Telegram client for connection and operations - FIXED
"""
import logging
from telethon import TelegramClient as TelethonClient
from telethon.tl.functions.channels import JoinChannelRequest
import os

class TelegramMonitorClient:
    """Telegram client wrapper"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
    
    async def connect(self):
        """Connect to Telegram as USER (not bot)"""
        try:
            api_id = int(os.getenv('TELEGRAM_API_ID'))
            api_hash = os.getenv('TELEGRAM_API_HASH')
            phone = os.getenv('TELEGRAM_PHONE')
            
            print(f"🔐 Attempting to connect as user with phone: {phone}")
            
            # Force new session
            session_name = 'user_telegram_session'
            
            self.client = TelethonClient(
                session_name,
                api_id,
                api_hash
            )
            
            # Force user authentication (not bot)
            await self.client.start(phone=phone)
            self.is_connected = True
            
            # Verify we're connected as user
            me = await self.client.get_me()
            if me.bot:
                print("❌ ERROR: Connected as BOT, not USER!")
                print("   Your .env file might have a bot token")
                print("   Delete session files and use phone number only")
                return False
            
            print(f"✅ Connected as USER: {me.first_name} ({me.phone})")
            print(f"✅ User ID: {me.id}")
            return True
            
        except Exception as e:
            print(f"❌ Telegram connection failed: {e}")
            print("\n💡 If you see 'session already had an authorized user':")
            print("   1. Delete all *.session files")
            print("   2. Restart the program")
            print("   3. Enter the verification code when asked")
            return False
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            print("📴 Disconnected from Telegram")
    
    async def join_channel(self, invite_link):
        """Join a channel"""
        try:
            print(f"🔗 Attempting to join: {invite_link}")
            
            # Clean the invite link
            if invite_link.startswith('@'):
                username = invite_link[1:]
                entity = await self.client.get_entity(username)
            elif 't.me/' in invite_link:
                username = invite_link.split('t.me/')[-1]
                if username.startswith('joinchat/'):
                    return {
                        'success': False,
                        'error': 'Private group invite - cannot join via bot'
                    }
                entity = await self.client.get_entity(username)
            else:
                entity = await self.client.get_entity(invite_link)
            
            print(f"📢 Found channel: {entity.title}")
            
            # Try to join
            await self.client(JoinChannelRequest(entity))
            
            return {
                'success': True,
                'channel': entity.username or entity.title,
                'id': entity.id,
                'title': entity.title
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed to join {invite_link}: {error_msg}")
            
            # Provide helpful error messages
            if "USER_NOT_PARTICIPANT" in error_msg:
                error_msg = "Cannot join private channel without invite"
            elif "CHANNEL_PRIVATE" in error_msg:
                error_msg = "Channel is private - needs invite"
            elif "USER_BANNED" in error_msg:
                error_msg = "User is banned from this channel"
            
            return {
                'success': False,
                'error': error_msg,
                'tip': 'Try adding @ before username or use full invite link'
            }
    
    async def fetch_messages(self, channel_username, limit=30):
        """Fetch messages from a channel"""
        try:
            print(f"📥 Fetching messages from: {channel_username}")
            entity = await self.client.get_entity(channel_username)
            messages = []
            
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.text:
                    messages.append({
                        'id': message.id,
                        'date': message.date.isoformat(),
                        'text': message.text,
                        'channel': channel_username
                    })
            
            print(f"✅ Fetched {len(messages)} messages from {channel_username}")
            return messages
            
        except Exception as e:
            print(f"⚠️  Error fetching from {channel_username}: {e}")
            return []
    
    async def get_user_channels(self):
        """Get all channels user is in"""
        try:
            print("📋 Getting user's channels...")
            dialogs = await self.client.get_dialogs(limit=50)
            channels = []
            
            for dialog in dialogs:
                if dialog.is_channel or dialog.is_group:
                    channels.append({
                        'id': dialog.id,
                        'title': dialog.title,
                        'username': getattr(dialog.entity, 'username', ''),
                        'participants': getattr(dialog.entity, 'participants_count', 0)
                    })
            
            print(f"✅ User is in {len(channels)} channels/groups")
            return channels
            
        except Exception as e:
            print(f"❌ Error getting user channels: {e}")
            return []