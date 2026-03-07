"""
Telegram Monitoring Agent - Pure Agent Version
Updated for real integration only with confidence filtering and rate limit handling
"""
import os
import sys
import asyncio
import json
import logging
import sqlite3
from datetime import datetime
import time
import traceback
import random

# Add current directory to path to import modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# ==============================================
# MODULE IMPORT WITH DEBUG PRINTS
# ==============================================
print("\n" + "="*60)
print("🔍 TELEGRAM AGENT - MODULE IMPORT CHECK")
print("="*60)

try:
    print("📦 Attempting to import modules...")
    from modules.channel_discovery import ChannelDiscoverer
    print("  ✅ channel_discovery imported")
    from modules.telegram_client import TelegramMonitorClient    
    print("  ✅ telegram_client imported")
    from modules.ai_analyzer import AIAnalyzer
    print("  ✅ ai_analyzer imported")
    print("✅ All modules imported successfully")
except ImportError as e:
    print(f"❌ Import error: {e}")
    # ... (rest of your import error handling)

# ==============================================
# AGENT CLASS WITH RATE LIMIT HANDLING
# ==============================================
class TelegramMonitorAgent:
    """Pure Telegram monitoring agent - REAL AGENT ONLY with rate limit handling"""
    
    def __init__(self):
        print("\n" + "="*60)
        print("🔧 INITIALIZING TELEGRAM MONITOR AGENT")
        print("="*60)
        
        self.is_running = False
        self.telegram = None
        self.discoverer = None
        self.ai_analyzer = None
        self.monitored_channels = []
        self.analysis_results = []
        self.cycle_count = 0
        self.total_messages_scanned = 0
        self.total_alerts_found = 0
        self.db_path = 'nexus_monitoring.db'
        
        # Rate limit tracking
        self.rate_limit_hits = 0
        self.last_rate_limit_time = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        
        # Minimum confidence threshold
        try:
            self.MIN_CONFIDENCE = int(os.getenv('MIN_ALERT_CONFIDENCE', 50))
        except:
            self.MIN_CONFIDENCE = 50
        
        print(f"🎯 Minimum confidence threshold: {self.MIN_CONFIDENCE}%")
        print(f"📁 Database path: {self.db_path}")
        print(f"📁 Database exists: {os.path.exists(self.db_path)}")
        
        self.setup_logging()
        self.init_database()
        
        print("✅ Agent instance created")
        print("="*60)
    
    def setup_logging(self):
        """Setup logging"""
        print("📝 Setting up logging...")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - TelegramAgent - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('telegram_agent.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        print("✅ Logging setup complete")
    
    def init_database(self):
        """Initialize database tables for channels"""
        print("🗄️ Initializing database tables...")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create monitored channels table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS monitored_channels (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_name TEXT UNIQUE,
                        added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        last_scanned DATETIME,
                        total_messages INTEGER DEFAULT 0,
                        total_alerts INTEGER DEFAULT 0,
                        source TEXT DEFAULT 'telegram'
                    )
                ''')
                print("  ✅ monitored_channels table ready")
                
                # Create alerts table if not exists (for backup)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS telegram_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        channel TEXT,
                        risk_level TEXT,
                        message TEXT,
                        confidence REAL,
                        ai_model TEXT,
                        indicators TEXT,
                        processed BOOLEAN DEFAULT 0
                    )
                ''')
                print("  ✅ telegram_alerts table ready")
                
                conn.commit()
                self.logger.info("✅ Database tables initialized")
                print("✅ Database initialization complete")
        except Exception as e:
            print(f"❌ Database init error: {e}")
            self.logger.error(f"❌ Database init error: {e}")
    
    async def load_channels(self):
        """Load monitored channels from database"""
        print("\n📡 LOADING MONITORED CHANNELS")
        print("-" * 40)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT channel_name FROM monitored_channels WHERE is_active = 1")
                rows = cursor.fetchall()
                self.monitored_channels = [row[0] for row in rows]
                
            print(f"📁 Loaded {len(self.monitored_channels)} channels from database")
            if self.monitored_channels:
                for i, channel in enumerate(self.monitored_channels):
                    print(f"   {i+1}. {channel}")
            else:
                print("   No channels found in database")
            
            # If no channels, add default ones
            if not self.monitored_channels:
                print("➕ Adding default channels...")
                default_channels = ["durov", "telegram", "tginfo", "technews", "cryptoupdates"]
                for channel in default_channels:
                    await self.add_channel(channel)
                print(f"✅ Added {len(default_channels)} default channels")
                    
        except Exception as e:
            print(f"⚠️ Could not load channels: {e}")
            self.logger.error(f"⚠️ Could not load channels: {e}")
            self.monitored_channels = ["durov", "telegram", "tginfo"]  # Fallback
            print(f"📡 Using fallback channels: {self.monitored_channels}")
    
    async def add_channel(self, channel_name):
        """Add a channel to monitor"""
        print(f"   ➕ Adding channel: {channel_name}")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO monitored_channels (channel_name, is_active, source)
                    VALUES (?, 1, 'telegram')
                ''', (channel_name,))
                conn.commit()
                
                if channel_name not in self.monitored_channels:
                    self.monitored_channels.append(channel_name)
                    print(f"   ✅ Added channel: {channel_name}")
                    
                    # Log to agent logs
                    self.add_agent_log('info', f'Added new channel: {channel_name}')
                else:
                    print(f"   ℹ️ Channel already exists: {channel_name}")
                    
        except Exception as e:
            print(f"   ❌ Error adding channel {channel_name}: {e}")
            self.logger.error(f"❌ Error adding channel {channel_name}: {e}")
    
    async def save_channels(self):
        """Save monitored channels (already handled by DB)"""
        pass
    
    async def initialize(self):
        """Initialize the agent"""
        print("\n" + "="*60)
        print("🤖 INITIALIZING REAL TELEGRAM MONITOR AGENT")
        print("="*60)
        
        try:
            print("\n1️⃣ Creating TelegramMonitorClient...")
            self.telegram = TelegramMonitorClient()
            print("   ✅ TelegramMonitorClient created")
            
            print("\n2️⃣ Creating AIAnalyzer...")
            self.ai_analyzer = AIAnalyzer()
            print("   ✅ AIAnalyzer created")
            
            # Check AI model type
            if hasattr(self.ai_analyzer, 'groq_client') and self.ai_analyzer.groq_client:
                print("   🤖 Using Llama3 via Groq for AI analysis")
            else:
                print("   🤖 Using keyword-based analysis (fallback)")
            
            # Connect to Telegram
            print("\n3️⃣ Connecting to Telegram...")
            print("   📞 This may take a few seconds...")
            connect_result = await self.telegram.connect()
            
            if not connect_result:
                logging.error("Failed to connect to Telegram")
                print("❌ Failed to connect to Telegram")
                return False
            
            print("   ✅ Connected to Telegram successfully!")
            
            print("\n4️⃣ Creating ChannelDiscoverer...")
            self.discoverer = ChannelDiscoverer(self.telegram)
            print("   ✅ ChannelDiscoverer created")
            
            # Load monitored channels from database
            print("\n5️⃣ Loading monitored channels...")
            await self.load_channels()
            
            print("\n" + "="*60)
            print("✅ TELEGRAM AGENT INITIALIZED SUCCESSFULLY")
            print("="*60)
            print(f"📊 Will monitor {len(self.monitored_channels)} channels")
            if self.monitored_channels:
                print("📋 Channels:")
                for i, channel in enumerate(self.monitored_channels[:10]):
                    print(f"   {i+1}. {channel}")
                if len(self.monitored_channels) > 10:
                    print(f"   ... and {len(self.monitored_channels) - 10} more")
            print(f"🤖 AI Model: {'Llama3 via Groq' if hasattr(self.ai_analyzer, 'groq_client') and self.ai_analyzer.groq_client else 'Keyword Analysis'}")
            print(f"🎯 Min Confidence: {self.MIN_CONFIDENCE}%")
            print("="*60)
            
            # Update agent status in main database
            self.update_agent_status('running')
            self.add_agent_log('start', 'Telegram agent initialized successfully')
            
            logging.info(f"Agent initialized. Monitoring {len(self.monitored_channels)} channels")
            return True
            
        except Exception as e:
            logging.error(f"Agent initialization failed: {e}")
            print(f"\n❌ Agent initialization failed: {e}")
            print("\n🔍 Detailed error:")
            traceback.print_exc()
            return False
    
    def update_agent_status(self, status):
        """Update agent status in main database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if status == 'running':
                    cursor.execute('''
                        UPDATE agents 
                        SET status = ?, last_started = CURRENT_TIMESTAMP,
                            last_activity = CURRENT_TIMESTAMP,
                            channels_monitored = ?
                        WHERE id = 'telegram'
                    ''', (status, len(self.monitored_channels)))
                    print(f"📊 Agent status updated: RUNNING (monitoring {len(self.monitored_channels)} channels)")
                else:
                    cursor.execute('''
                        UPDATE agents 
                        SET status = ?, last_stopped = CURRENT_TIMESTAMP,
                            last_activity = CURRENT_TIMESTAMP
                        WHERE id = 'telegram'
                    ''', (status,))
                    print(f"📊 Agent status updated: STOPPED")
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error updating agent status: {e}")
            print(f"⚠️ Could not update agent status in DB: {e}")
    
    def add_agent_log(self, log_type, message, details=None):
        """Add log to main database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO agent_logs (agent_id, log_type, message, details)
                    VALUES (?, ?, ?, ?)
                ''', ('telegram', log_type, message, details))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error adding agent log: {e}")
    
    def add_alert_to_db(self, analysis):
        """Add alert to main database - with confidence check"""
        
        # Double-check confidence threshold
        if analysis.get('confidence', 0) < self.MIN_CONFIDENCE:
            print(f"    ⏭️  Not saving alert - confidence too low: {analysis.get('confidence', 0)}% < {self.MIN_CONFIDENCE}%")
            return None
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Add to main alerts table
                cursor.execute('''
                    INSERT INTO alerts (source, channel, risk_level, message, confidence, ai_model)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    'telegram',
                    analysis['channel'],
                    analysis['risk_level'],
                    analysis['summary'][:200],
                    analysis['confidence'],
                    analysis.get('ai_model', 'Llama3')
                ))
                
                alert_id = cursor.lastrowid
                
                # Update agent stats
                cursor.execute('''
                    UPDATE agents 
                    SET total_alerts = total_alerts + 1,
                        messages_analyzed = messages_analyzed + 1,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE id = 'telegram'
                ''')
                
                # Update channel stats
                cursor.execute('''
                    UPDATE monitored_channels 
                    SET total_alerts = total_alerts + 1,
                        last_scanned = CURRENT_TIMESTAMP
                    WHERE channel_name = ?
                ''', (analysis['channel'],))
                
                conn.commit()
                
                # Also save to telegram_alerts for backup
                with sqlite3.connect(self.db_path) as conn2:
                    cursor2 = conn2.cursor()
                    cursor2.execute('''
                        INSERT INTO telegram_alerts (channel, risk_level, message, confidence, ai_model, indicators)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        analysis['channel'],
                        analysis['risk_level'],
                        analysis['text'][:500],
                        analysis['confidence'],
                        analysis.get('ai_model', 'Llama3'),
                        json.dumps(analysis.get('indicators', []))
                    ))
                    conn2.commit()
                
                return alert_id
        except Exception as e:
            self.logger.error(f"Error adding alert to DB: {e}")
            return None
    
    def update_channel_stats(self, channel_name, messages_count):
        """Update channel statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE monitored_channels 
                    SET total_messages = total_messages + ?,
                        last_scanned = CURRENT_TIMESTAMP
                    WHERE channel_name = ?
                ''', (messages_count, channel_name))
                
                # Also update agent messages count
                cursor.execute('''
                    UPDATE agents 
                    SET messages_analyzed = messages_analyzed + ?,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE id = 'telegram'
                ''', (messages_count,))
                
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error updating channel stats: {e}")
    
    async def run(self):
        """Main agent loop - with rate limit handling"""
        self.is_running = True
        
        print("\n" + "="*60)
        print("🚀 REAL TELEGRAM AGENT STARTED - LIVE MONITORING")
        print("="*60)
        logging.info("Telegram agent started - live monitoring")
        
        self.cycle_count = 0
        self.consecutive_errors = 0
        
        try:
            while self.is_running:
                self.cycle_count += 1
                
                print("\n" + "="*60)
                print(f"🔄 MONITORING CYCLE #{self.cycle_count}")
                print("="*60)
                print(f"📡 Active channels: {len(self.monitored_channels)}")
                print(f"📊 Stats: {self.total_messages_scanned} messages scanned, {self.total_alerts_found} alerts found")
                print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 40)
                
                # Show current channels being monitored
                if self.monitored_channels:
                    print("\n📋 Current monitoring list:")
                    for idx, channel in enumerate(self.monitored_channels[:10]):
                        print(f"   📡 {idx+1}. {channel}")
                    if len(self.monitored_channels) > 10:
                        print(f"   ... and {len(self.monitored_channels) - 10} more")
                else:
                    print("⚠️ No channels to monitor!")
                
                # Update channels monitored count in database
                self.update_agent_status('running')
                
                # Scan each channel with rate limit awareness
                channels_to_scan = self.monitored_channels[:15]
                print(f"\n🔍 Scanning {len(channels_to_scan)} channels...")
                
                scan_success = False
                for i, channel in enumerate(channels_to_scan):
                    if not self.is_running:
                        break
                    
                    # Add delay between channels to avoid rate limits
                    if i > 0:
                        delay = random.uniform(2, 5)
                        print(f"   ⏱️  Waiting {delay:.1f}s between scans...")
                        await asyncio.sleep(delay)
                    
                    print(f"\n  [{i+1}/{len(channels_to_scan)}] 🔍 Scanning: {channel}")
                    print(f"  {'-' * 40}")
                    
                    try:
                        await self.scan_channel(channel)
                        self.consecutive_errors = 0
                        scan_success = True
                    except Exception as e:
                        self.consecutive_errors += 1
                        print(f"   ❌ Error scanning {channel}: {e}")
                        
                        # Check if we've had too many consecutive errors
                        if self.consecutive_errors >= self.max_consecutive_errors:
                            print(f"\n⚠️ Too many consecutive errors ({self.consecutive_errors}). Waiting longer...")
                            await asyncio.sleep(30)
                            self.consecutive_errors = 0
                
                # Save results
                await self.save_results()
                
                print("\n" + "="*60)
                print(f"✅ CYCLE #{self.cycle_count} COMPLETE")
                print("="*60)
                print(f"📈 Total scanned: {self.total_messages_scanned} messages")
                print(f"🚨 Total alerts: {self.total_alerts_found}")
                
                # Calculate next scan interval with backoff if needed
                base_interval = 60
                if self.rate_limit_hits > 0:
                    # Exponential backoff
                    backoff = min(2 ** self.rate_limit_hits, 300)  # Max 5 minutes
                    interval = base_interval + backoff
                    print(f"⚠️ Rate limit backoff: +{backoff}s")
                else:
                    interval = base_interval
                
                print(f"⏰ Next cycle in {interval} seconds...")
                print("="*60)
                
                # Log cycle completion
                logging.info(f"Cycle #{self.cycle_count} complete. Total alerts: {self.total_alerts_found}")
                
                # Wait before next cycle (with check for stop)
                for remaining in range(interval, 0, -1):
                    if not self.is_running:
                        break
                    if remaining % 10 == 0:
                        print(f"⏳ {remaining} seconds until next cycle...")
                    await asyncio.sleep(1)
                
                # Reset rate limit counter after successful cycle
                if scan_success:
                    self.rate_limit_hits = max(0, self.rate_limit_hits - 1)
                
        except KeyboardInterrupt:
            print("\n🛑 Agent stopped by user")
            logging.info("Agent stopped by user")
        except Exception as e:
            print(f"\n❌ Agent error: {e}")
            logging.error(f"Agent error: {e}")
            traceback.print_exc()
        finally:
            await self.shutdown()
    
    async def scan_channel(self, channel_name):
        """Scan a channel with rate limit handling"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"    📡 Fetching messages from {channel_name}...")
                
                # Fetch messages with timeout
                messages = await asyncio.wait_for(
                    self.telegram.fetch_messages(channel_name, limit=25),
                    timeout=30
                )
                
                if not messages:
                    print(f"    ℹ️  No messages in {channel_name}")
                    return
                
                self.total_messages_scanned += len(messages)
                print(f"    📄 Found {len(messages)} messages")
                
                # Update channel stats
                self.update_channel_stats(channel_name, len(messages))
                
                # Analyze messages with AI
                print(f"    🤖 Analyzing {len(messages)} messages with AI...")
                analyses = await self.ai_analyzer.analyze_messages_batch(messages, channel_name)
                print(f"    ✅ Analysis complete")
                
                # Process results - FILTER BY CONFIDENCE
                high_risk_count = 0
                medium_risk_count = 0
                skipped_low_confidence = 0
                skipped_no_risk = 0
                
                for idx, analysis in enumerate(analyses):
                    # Skip low confidence alerts (below threshold)
                    if analysis.get('confidence', 0) < self.MIN_CONFIDENCE:
                        skipped_low_confidence += 1
                        continue
                    
                    # Skip if risk level is 'none' or not set
                    if analysis.get('risk_level') == 'none' or not analysis.get('risk_level'):
                        skipped_no_risk += 1
                        continue
                        
                    if analysis['risk_level'] != 'low' and analysis['risk_level'] != 'safe':
                        self.analysis_results.append({
                            **analysis,
                            'timestamp': datetime.now().isoformat(),
                            'agent_cycle': self.cycle_count,
                            'scan_id': f"scan_{self.cycle_count}_{channel_name}"
                        })
                        
                        if analysis['risk_level'] == 'high':
                            high_risk_count += 1
                            self.total_alerts_found += 1
                            print(f"    🚨 HIGH RISK #{high_risk_count}: {analysis['summary'][:100]}")
                            print(f"       Confidence: {analysis['confidence']}%")
                            if 'indicators' in analysis:
                                print(f"       Indicators: {', '.join(analysis['indicators'][:3])}")
                            logging.warning(f"High risk in {channel_name}: {analysis['summary']}")
                            
                            # Add to main database
                            alert_id = self.add_alert_to_db(analysis)
                            if alert_id:
                                print(f"       💾 Alert #{alert_id} saved to database")
                            
                            # Log to agent logs
                            self.add_agent_log(
                                'alert',
                                f'High risk detected in {channel_name}',
                                f'Alert #{alert_id if alert_id else "N/A"} - Confidence: {analysis["confidence"]}%'
                            )
                            
                        elif analysis['risk_level'] == 'medium':
                            medium_risk_count += 1
                            print(f"    ⚠️  Medium risk #{medium_risk_count}: {analysis['summary'][:80]}")
                            logging.info(f"Medium risk in {channel_name}: {analysis['summary']}")
                            
                            # Add to main database
                            alert_id = self.add_alert_to_db(analysis)
                            if alert_id:
                                print(f"       💾 Alert #{alert_id} saved to database")
                            
                            # Log to agent logs
                            self.add_agent_log(
                                'alert',
                                f'Medium risk detected in {channel_name}',
                                f'Alert #{alert_id if alert_id else "N/A"} - Confidence: {analysis["confidence"]}%'
                            )
                
                # Print summary of skipped items
                if skipped_low_confidence > 0:
                    print(f"    ⏭️  Skipped {skipped_low_confidence} low confidence alerts (<{self.MIN_CONFIDENCE}%)")
                if skipped_no_risk > 0:
                    print(f"    ⏭️  Skipped {skipped_no_risk} messages with no risk detected")
                
                if high_risk_count > 0 or medium_risk_count > 0:
                    print(f"    🎯 Summary: {high_risk_count} high, {medium_risk_count} medium risks")
                else:
                    print(f"    ✅ No significant risks detected in {channel_name}")
                
                # Success - break retry loop
                return
                
            except asyncio.TimeoutError:
                print(f"    ⏱️  Timeout fetching messages (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limit errors
                if "flood" in error_str or "too many" in error_str or "rate" in error_str:
                    self.rate_limit_hits += 1
                    wait_time = retry_delay * (2 ** attempt) * 5
                    print(f"    ⚠️  Rate limited! Waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    
                    # Log rate limit event
                    self.add_agent_log('error', f'Rate limit hit for {channel_name}', f'Retry in {wait_time}s')
                    
                else:
                    print(f"    ⚠️  Error scanning {channel_name}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                    else:
                        print(f"    🔍 Error details: {traceback.format_exc()}")
                        logging.error(f"Error scanning {channel_name}: {e}")
    
    async def scan_single_channel(self, channel_name):
        """Scan a single channel immediately (for manual scans)"""
        return await self.scan_channel(channel_name)
    
    async def save_results(self):
        """Save analysis results"""
        try:
            results_file = 'telegram_agent_results.json'
            
            # Get channel stats from database
            channel_stats = []
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT channel_name, total_messages, total_alerts, last_scanned
                        FROM monitored_channels
                        WHERE is_active = 1
                        ORDER BY last_scanned DESC
                        LIMIT 20
                    ''')
                    rows = cursor.fetchall()
                    channel_stats = [
                        {
                            'name': row[0],
                            'messages': row[1],
                            'alerts': row[2],
                            'last_scanned': row[3]
                        }
                        for row in rows
                    ]
            except Exception as e:
                print(f"    ⚠️ Could not get channel stats: {e}")
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'cycle': self.cycle_count,
                'channels_monitored': len(self.monitored_channels),
                'monitored_channels_list': self.monitored_channels[:20],
                'total_messages_scanned': self.total_messages_scanned,
                'total_alerts_found': self.total_alerts_found,
                'min_confidence_threshold': self.MIN_CONFIDENCE,
                'rate_limit_hits': self.rate_limit_hits,
                'last_scan_time': datetime.now().isoformat(),
                'agent_status': 'running' if self.is_running else 'stopped',
                'channel_stats': channel_stats
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"    💾 Saved agent results to {results_file}")
            
        except Exception as e:
            print(f"    ❌ Error saving results: {e}")
            logging.error(f"Error saving results: {e}")
    
    async def shutdown(self):
        """Shutdown the agent"""
        print("\n" + "="*60)
        print("🛑 SHUTTING DOWN TELEGRAM AGENT")
        print("="*60)
        
        self.is_running = False
        
        # Update status in database
        self.update_agent_status('stopped')
        self.add_agent_log('stop', 'Telegram agent stopped')
        
        if self.telegram:
            print("📞 Disconnecting from Telegram...")
            await self.telegram.disconnect()
            print("✅ Disconnected")
        
        print("\n" + "="*60)
        print("👋 TELEGRAM AGENT SHUTDOWN COMPLETE")
        print("="*60)
        print(f"📊 Final stats:")
        print(f"   • Messages scanned: {self.total_messages_scanned}")
        print(f"   • Alerts found: {self.total_alerts_found}")
        print(f"   • Channels monitored: {len(self.monitored_channels)}")
        print(f"   • Rate limit hits: {self.rate_limit_hits}")
        print("="*60)
        logging.info(f"Telegram agent shutdown. Total alerts: {self.total_alerts_found}")


async def main():
    """Agent entry point"""
    print("\n" + "="*60)
    print("🤖 TELEGRAM MONITORING AGENT - STANDALONE MODE")
    print("="*60)
    print("This is a standalone agent. For full features,")
    print("run through the main app.py for web interface.")
    print("="*60 + "\n")
    
    agent = TelegramMonitorAgent()
    
    if not await agent.initialize():
        print("\n❌ Agent initialization failed. Exiting.")
        return
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        print("\n👋 Agent terminated by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
    finally:
        print("\n👋 Agent execution completed")

if __name__ == "__main__":
    # Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Agent terminated by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()