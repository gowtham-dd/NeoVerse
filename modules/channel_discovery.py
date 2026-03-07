"""
Channel discovery - FIXED with proper error handling
"""
import re
import asyncio

class ChannelDiscoverer:
    """Discover drug-related channels"""
    
    def __init__(self, telegram_client):
        self.telegram_client = telegram_client  # Store the client wrapper
        self.client = telegram_client.client  # Store the actual Telethon client
        
        # Drug keywords
        self.drug_keywords = [
            'weed', 'marijuana', 'cocaine', 'heroin', 'mdma',
            'ecstasy', 'xanax', 'oxy', 'adderall', 'fentanyl',
            'buy drugs', 'drugs for sale', 'drug delivery',
            'snow', 'candy', 'bars', 'green', 'fire',
            'work', 'pack', 'gear', 'party supplies'
        ]
        
        # Public channels to start from
        self.seed_channels = [
            "durov",           # Telegram founder (public)
            "telegram",        # Official Telegram (public)
            "tginfo",          # Telegram info
            "telegramtips"     # Telegram tips
        ]
    
    async def discover_channels(self, query=None, limit=10):
        """Discover channels"""
        try:
            print("🎯 Starting channel discovery...")
            
            if not self.client:
                print("❌ No Telegram client available!")
                return []
            
            discovered = []
            
            # Method 1: Search by keywords if query provided
            if query:
                channels = await self._search_by_keyword(query, limit)
                discovered.extend(channels)
            
            # Method 2: Extract from seed channels
            if len(discovered) < limit:
                for seed in self.seed_channels:
                    try:
                        print(f"🔍 Checking seed: @{seed}")
                        channels = await self._extract_from_channel(seed, 20)
                        discovered.extend(channels)
                        
                        # Filter for drug-related names
                        suspicious = []
                        for channel in channels:
                            username = channel.get('username', '').lower()
                            if self._contains_drug_keyword(username):
                                suspicious.append(channel)
                        
                        if suspicious:
                            print(f"✅ Found {len(suspicious)} suspicious channels from {seed}")
                            discovered.extend(suspicious)
                            
                    except Exception as e:
                        print(f"⚠️  Error with seed {seed}: {e}")
                        continue
            
            # Remove duplicates
            unique = {}
            for channel in discovered:
                if channel.get('username'):
                    unique[channel['username']] = channel
            
            result = list(unique.values())[:limit]
            print(f"🎯 Discovery complete: Found {len(result)} unique channels")
            return result
            
        except Exception as e:
            print(f"❌ Discovery error: {e}")
            return []
    
    async def _search_by_keyword(self, keyword, limit=10):
        """Search channels by keyword"""
        try:
            # Try to find channels mentioning the keyword
            print(f"🔎 Searching for: {keyword}")
            
            # We'll use a different approach - check public channels
            public_channels = [
                f"{keyword}_news",
                f"{keyword}_chat",
                f"{keyword}_group",
                f"buy_{keyword}",
                f"{keyword}_sale"
            ]
            
            found = []
            for channel_name in public_channels:
                try:
                    # Try to get the channel
                    entity = await self.client.get_entity(channel_name)
                    found.append({
                        'username': channel_name,
                        'title': getattr(entity, 'title', channel_name),
                        'source': 'keyword_search'
                    })
                except:
                    continue
            
            return found
            
        except Exception as e:
            print(f"⚠️  Search error for {keyword}: {e}")
            return []
    
    async def _extract_from_channel(self, channel_username, message_limit=30):
        """Extract channel mentions from a channel"""
        try:
            if not self.client:
                return []
            
            entity = await self.client.get_entity(channel_username)
            found_channels = []
            
            async for message in self.client.iter_messages(entity, limit=message_limit):
                if message.text:
                    text = message.text
                    
                    # Find @mentions
                    mentions = re.findall(r'@(\w+)', text)
                    for mention in mentions:
                        if len(mention) > 3:  # Filter out short mentions
                            found_channels.append({
                                'username': mention,
                                'source': f"mentioned in @{channel_username}",
                                'message_preview': text[:100]
                            })
                    
                    # Find t.me links
                    links = re.findall(r't\.me/(\w+)', text)
                    for link in links:
                        found_channels.append({
                            'username': link,
                            'source': f"linked in @{channel_username}",
                            'message_preview': text[:100]
                        })
            
            return found_channels
            
        except Exception as e:
            print(f"⚠️  Error extracting from {channel_username}: {e}")
            return []
    
    def _contains_drug_keyword(self, text):
        """Check if text contains drug-related keywords"""
        text_lower = text.lower()
        for keyword in self.drug_keywords:
            if keyword in text_lower:
                return True
        return False
    
    async def analyze_channel(self, channel_username):
        """Analyze channel for drug content"""
        try:
            print(f"🔬 Analyzing: @{channel_username}")
            
            if not self.client:
                return {
                    'username': channel_username,
                    'error': 'No Telegram client',
                    'is_suspicious': False
                }
            
            try:
                entity = await self.client.get_entity(channel_username)
            except Exception as e:
                print(f"❌ Cannot access @{channel_username}: {e}")
                return {
                    'username': channel_username,
                    'error': f'Cannot access channel: {e}',
                    'is_suspicious': False
                }
            
            # Scan messages
            drug_count = 0
            total_messages = 0
            sample_messages = []
            
            try:
                async for message in self.client.iter_messages(entity, limit=50):
                    if not message.text:
                        continue
                    
                    total_messages += 1
                    text = message.text.lower()
                    
                    # Check keywords
                    found_keywords = []
                    for keyword in self.drug_keywords:
                        if keyword in text:
                            found_keywords.append(keyword)
                    
                    if found_keywords:
                        drug_count += 1
                        if len(sample_messages) < 3:
                            sample_messages.append({
                                'text': message.text[:200],
                                'keywords': found_keywords
                            })
                
                # Calculate score
                if total_messages > 0:
                    suspicion_score = (drug_count / total_messages) * 100
                else:
                    suspicion_score = 0
                
                print(f"   📊 Scanned {total_messages} messages, {drug_count} suspicious")
                print(f"   🎯 Suspicion score: {suspicion_score:.1f}%")
                
                return {
                    'username': channel_username,
                    'title': getattr(entity, 'title', channel_username),
                    'total_messages': total_messages,
                    'suspicious_messages': drug_count,
                    'suspicion_score': suspicion_score,
                    'sample_messages': sample_messages,
                    'is_suspicious': suspicion_score > 10,
                    'recommendation': self._get_recommendation(suspicion_score)
                }
                
            except Exception as e:
                print(f"⚠️  Error scanning messages: {e}")
                return {
                    'username': channel_username,
                    'error': f'Error scanning: {e}',
                    'is_suspicious': False
                }
            
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return {
                'username': channel_username,
                'error': str(e),
                'is_suspicious': False
            }
    
    def _get_recommendation(self, score):
        """Get recommendation based on score"""
        if score > 50:
            return "🚨 HIGH RISK - Likely drug trafficking"
        elif score > 20:
            return "⚠️ MEDIUM RISK - Drug-related content"
        elif score > 5:
            return "👀 LOW RISK - Some suspicious content"
        else:
            return "✅ SAFE - Minimal suspicious content"