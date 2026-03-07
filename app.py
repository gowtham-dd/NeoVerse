"""
Nexus AI - Complete Monitoring System with Real Agent Logging
Uses separate telegram_agent.py file
"""
import os
import sys
import json
import sqlite3
import threading
import subprocess
import time
import random
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import logging
from dotenv import load_dotenv

# ==============================================
# LOAD ENVIRONMENT VARIABLES FIRST
# ==============================================
# Load .env file at the very beginning
env_path = Path('.env')
if env_path.exists():
    load_dotenv(override=True)
    print("✅ Loaded environment variables from .env")
else:
    print("⚠️ No .env file found")

# Debug print to verify
print("\n=== Environment Check ===")
print(f"LANGSMITH_API_KEY: {'✅ Set' if os.getenv('LANGSMITH_API_KEY') else '❌ Missing'}")
if os.getenv('LANGSMITH_API_KEY'):
    key = os.getenv('LANGSMITH_API_KEY')
    print(f"  Key starts with: {key[:10]}...")
print("=========================\n")

# ==============================================
# LangSmith Integration
# ==============================================
LANGCHAIN_AVAILABLE = False
langsmith_client = None
LANGSMITH_PROJECT = os.getenv('LANGSMITH_PROJECT', 'illegaltrade')

try:
    from langsmith import Client
    from langsmith.run_helpers import traceable
    from langsmith.evaluation import evaluate
    LANGCHAIN_AVAILABLE = True
    print("✅ LangSmith imported successfully")
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️ LangSmith not installed. Run: pip install langsmith")

# Initialize LangSmith client if available
if LANGCHAIN_AVAILABLE:
    try:
        langsmith_api_key = os.getenv('LANGSMITH_API_KEY')
        
        if langsmith_api_key:
            langsmith_client = Client(
                api_key=langsmith_api_key,
                api_url=os.getenv('LANGSMITH_ENDPOINT', 'https://api.smith.langchain.com')
            )
            print(f"✅ LangSmith client initialized for project: {LANGSMITH_PROJECT}")
            
            # Test the connection with a test run
            try:
                test_run = langsmith_client.create_run(
                    name="startup_test",
                    run_type="chain",
                    inputs={"event": "app_startup", "timestamp": datetime.now().isoformat()},
                    outputs={"status": "initialized"},
                    project_name=LANGSMITH_PROJECT,
                    tags=["startup", "test"]
                )
                print(f"✅ LangSmith test run created")
                print(f"🔗 View at: https://smith.langchain.com/projects/{LANGSMITH_PROJECT}")
            except Exception as e:
                print(f"⚠️ LangSmith test run failed (but client is initialized): {e}")
        else:
            print("⚠️ LANGSMITH_API_KEY not found in environment variables")
            langsmith_client = None
    except Exception as e:
        print(f"⚠️ LangSmith initialization error: {e}")
        langsmith_client = None

def trace_function(name=None):
    """Decorator to trace functions with LangSmith"""
    def decorator(func):
        if langsmith_client and LANGCHAIN_AVAILABLE:
            return traceable(
                name=name or func.__name__,
                client=langsmith_client,
                project_name=LANGSMITH_PROJECT
            )(func)
        return func
    return decorator

# ==============================================
# Initial Setup
# ==============================================
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')

print("\n" + "="*60)
print("🚀 NEXUS AI - Complete Monitoring System")
print("="*60)

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# ==============================================
# Load Cluster Data from JSON ONLY
# ==============================================
def load_cluster_data():
    """Load drug trafficking cluster data from JSON file"""
    cluster_file = Path('clusters.json')
    
    try:
        if cluster_file.exists():
            with open(cluster_file, 'r', encoding='utf-8') as f:
                clusters = json.load(f)
            print(f"✅ Loaded {len(clusters)} clusters from {cluster_file}")
            return clusters
        else:
            # If file doesn't exist, create an empty array
            with open(cluster_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            print(f"✅ Created empty {cluster_file}")
            return []
    except Exception as e:
        print(f"❌ Error loading cluster data: {e}")
        return []

CLUSTER_DATA = load_cluster_data()

# ==============================================
# Database Manager with LangSmith Tracing
# ==============================================
class DatabaseManager:
    """SQLite database for persistent storage"""
    
    def __init__(self, db_path='nexus_monitoring.db'):
        self.db_path = db_path
        self.init_database()
        self.add_sample_data()
    
    @trace_function(name="db_init")
    def init_database(self):
        """Create database tables with LangSmith support"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
        
        # Check if trace_id column exists in alerts table
            cursor.execute("PRAGMA table_info(alerts)")
            columns = [column[1] for column in cursor.fetchall()]
        
        # Alerts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL,
                channel TEXT,
                risk_level TEXT CHECK(risk_level IN ('high', 'medium', 'low')),
                message TEXT,
                confidence REAL,
                ai_model TEXT,
                processed BOOLEAN DEFAULT 0
            )
        ''')
        
        # Add trace_id and metadata columns if they don't exist
            if 'trace_id' not in columns:
                try:
                    cursor.execute('ALTER TABLE alerts ADD COLUMN trace_id TEXT')
                    print("✅ Added trace_id column to alerts table")
                except Exception as e:
                    print(f"⚠️ Could not add trace_id to alerts: {e}")
        
            if 'metadata' not in columns:
                try:
                    cursor.execute('ALTER TABLE alerts ADD COLUMN metadata TEXT')
                    print("✅ Added metadata column to alerts table")
                except Exception as e:
                    print(f"⚠️ Could not add metadata to alerts: {e}")
        
        # Agent logs table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent_id TEXT,
                log_type TEXT,
                message TEXT,
                details TEXT
            )
        ''')
        
            cursor.execute("PRAGMA table_info(agent_logs)")
            log_columns = [column[1] for column in cursor.fetchall()]
        
            if 'trace_id' not in log_columns:
                try:
                    cursor.execute('ALTER TABLE agent_logs ADD COLUMN trace_id TEXT')
                    print("✅ Added trace_id column to agent_logs table")
                except Exception as e:
                    print(f"⚠️ Could not add trace_id to agent_logs: {e}")
        
        # Agents table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT DEFAULT 'stopped',
                last_started DATETIME,
                last_stopped DATETIME,
                total_alerts INTEGER DEFAULT 0,
                channels_monitored INTEGER DEFAULT 0,
                messages_analyzed INTEGER DEFAULT 0,
                last_activity DATETIME
            )
        ''')
        
        # Check if monitored_channels table exists and has source column
            cursor.execute("PRAGMA table_info(monitored_channels)")
            channel_columns = [column[1] for column in cursor.fetchall()]
        
        # Create or alter monitored_channels table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitored_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_name TEXT,
                added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                last_scanned DATETIME,
                total_messages INTEGER DEFAULT 0,
                total_alerts INTEGER DEFAULT 0,
                last_error TEXT,
                scan_in_progress BOOLEAN DEFAULT 0
            )
        ''')
        
        # Add source column if it doesn't exist
            if 'source' not in channel_columns:
                try:
                    cursor.execute('ALTER TABLE monitored_channels ADD COLUMN source TEXT DEFAULT "telegram"')
                    print("✅ Added source column to monitored_channels table")
                except Exception as e:
                    print(f"⚠️ Could not add source to monitored_channels: {e}")
        
        # Initialize default agents
            default_agents = [
            ('telegram', 'Telegram Monitor', 'stopped', None, None, 0, 0, 0, None),
            ('reddit', 'Reddit Monitor', 'stopped', None, None, 0, 0, 0, None)
        ]
        
            cursor.executemany('''
            INSERT OR IGNORE INTO agents (id, name, status, last_started, last_stopped, total_alerts, channels_monitored, messages_analyzed, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_agents)
        
            conn.commit()
        print("✅ Database initialized with LangSmith support")

    @trace_function(name="db_add_sample_data")
    def add_sample_data(self):
        """Add sample alerts if database is empty"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM alerts")
            if cursor.fetchone()[0] == 0:
                sample_alerts = [
                    (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'telegram', '@darkmarket', 'high', 
                     'Looking for bulk cocaine delivery. Contact @dealer123 for prices.', 95.0, 'Llama3'),
                    (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'reddit', 'r/darknet', 'medium',
                     'Discussion about Bitcoin payments for special deliveries.', 78.0, 'Llama3'),
                ]
                
                cursor.executemany('''
                    INSERT INTO alerts (timestamp, source, channel, risk_level, message, confidence, ai_model)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', sample_alerts)
                
                conn.commit()
                print("✅ Added sample alerts to database")
    
    @trace_function(name="db_add_alert")
    def add_alert(self, source, channel, risk_level, message, confidence, ai_model, trace_id=None, metadata=None):
        """Add new alert with LangSmith trace - with fallback for missing columns"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA table_info(alerts)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'trace_id' in columns and 'metadata' in columns:
                    cursor.execute('''
                        INSERT INTO alerts (source, channel, risk_level, message, confidence, ai_model, trace_id, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (source, channel, risk_level, message, confidence, ai_model, trace_id, 
                         json.dumps(metadata) if metadata else None))
                elif 'trace_id' in columns:
                    cursor.execute('''
                        INSERT INTO alerts (source, channel, risk_level, message, confidence, ai_model, trace_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (source, channel, risk_level, message, confidence, ai_model, trace_id))
                else:
                    cursor.execute('''
                        INSERT INTO alerts (source, channel, risk_level, message, confidence, ai_model)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (source, channel, risk_level, message, confidence, ai_model))
                
                alert_id = cursor.lastrowid
                
                cursor.execute('''
                    UPDATE agents 
                    SET total_alerts = total_alerts + 1,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (source,))
                
                conn.commit()
                
                if langsmith_client and LANGCHAIN_AVAILABLE and trace_id:
                    try:
                        langsmith_client.create_run(
                            name=f"alert_created_{source}",
                            run_type="chain",
                            inputs={
                                "source": source,
                                "channel": channel,
                                "risk_level": risk_level,
                                "message_preview": message[:100],
                                "confidence": confidence
                            },
                            outputs={"alert_id": alert_id},
                            project_name=LANGSMITH_PROJECT,
                            tags=["alert", source, risk_level]
                        )
                    except Exception as e:
                        print(f"⚠️ LangSmith logging error: {e}")
                
                return alert_id
                
        except Exception as e:
            print(f"❌ Error adding alert to database: {e}")
            return None
    
    @trace_function(name="db_add_agent_log")
    def add_agent_log(self, agent_id, log_type, message, details=None, trace_id=None):
        """Add agent activity log with LangSmith trace - with fallback for missing columns"""
        
        colors = {
            'start': '🟢',
            'stop': '🔴',
            'scan': '🔍',
            'alert': '🚨',
            'info': 'ℹ️',
            'error': '❌'
        }
        emoji = colors.get(log_type, '📝')
        print(f"{emoji} [{agent_id.upper()}] {message}")
        if details:
            print(f"   📋 Details: {details}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA table_info(agent_logs)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'trace_id' in columns:
                    cursor.execute('''
                        INSERT INTO agent_logs (agent_id, log_type, message, details, trace_id)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (agent_id, log_type, message, details, trace_id))
                else:
                    cursor.execute('''
                        INSERT INTO agent_logs (agent_id, log_type, message, details)
                        VALUES (?, ?, ?, ?)
                    ''', (agent_id, log_type, message, details))
                
                cursor.execute('''
                    UPDATE agents 
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (agent_id,))
                
                conn.commit()
                
        except Exception as e:
            print(f"⚠️ Could not save log to database: {e}")
    
    def get_agent_logs(self, agent_id=None, limit=20):
        """Get agent activity logs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if agent_id:
                cursor.execute('''
                    SELECT timestamp, agent_id, log_type, message, details
                    FROM agent_logs 
                    WHERE agent_id = ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (agent_id, limit))
            else:
                cursor.execute('''
                    SELECT timestamp, agent_id, log_type, message, details
                    FROM agent_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            return [
                {
                    'timestamp': row[0],
                    'agent_id': row[1],
                    'log_type': row[2],
                    'message': row[3],
                    'details': row[4]
                }
                for row in cursor.fetchall()
            ]
    
    @trace_function(name="db_get_alerts")
    def get_alerts(self, source='all', limit=20, min_confidence=50):
        """Get alerts with optional filtering"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if source == 'all':
                cursor.execute('''
                    SELECT id, timestamp, source, channel, risk_level, message, confidence, ai_model
                    FROM alerts 
                    WHERE confidence >= ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (min_confidence, limit))
            else:
                cursor.execute('''
                    SELECT id, timestamp, source, channel, risk_level, message, confidence, ai_model
                    FROM alerts 
                    WHERE source = ? AND confidence >= ?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (source, min_confidence, limit))
            
            return [
                {
                    'id': row[0],
                    'timestamp': row[1],
                    'source': row[2],
                    'channel': row[3],
                    'risk_level': row[4],
                    'message': row[5],
                    'confidence': row[6],
                    'ai_model': row[7]
                }
                for row in cursor.fetchall()
            ]
    
    @trace_function(name="db_get_stats")
    def get_stats(self):
        """Get system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE confidence >= 50")
            total_alerts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM alerts WHERE risk_level = 'high' AND confidence >= 50")
            high_risk = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(channels_monitored), SUM(messages_analyzed) FROM agents")
            channels, messages = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) FROM monitored_channels WHERE is_active = 1")
            active_channels = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM agent_logs WHERE timestamp > datetime('now', '-5 minutes')")
            recent_activity = cursor.fetchone()[0]
            
            return {
                'total_alerts': total_alerts or 0,
                'high_risk_alerts': high_risk or 0,
                'channels_monitored': active_channels or 0,
                'messages_analyzed': messages or 0,
                'recent_activity': recent_activity or 0
            }
    
    def get_agents(self):
        """Get all agents"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents")
            
            agents = {}
            for row in cursor.fetchall():
                agents[row[0]] = {
                    'name': row[1],
                    'status': row[2],
                    'last_started': row[3],
                    'last_stopped': row[4],
                    'total_alerts': row[5],
                    'channels_monitored': row[6],
                    'messages_analyzed': row[7],
                    'last_activity': row[8]
                }
            return agents
    
    def update_agent_status(self, agent_id, status):
        """Update agent status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if status == 'running':
                cursor.execute('''
                    UPDATE agents 
                    SET status = ?, last_started = CURRENT_TIMESTAMP,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, agent_id))
            else:
                cursor.execute('''
                    UPDATE agents 
                    SET status = ?, last_stopped = CURRENT_TIMESTAMP,
                        last_activity = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, agent_id))
            
            conn.commit()

# ==============================================
# Agent Manager with LangSmith Tracing
# ==============================================
class AgentManager:
    """Manages all monitoring agents - REAL Telegram + Reddit Simulation"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.agents = {}
        self.simulation_agents = {}
        self.telegram_agent_instance = None
        self.telegram_agent_thread = None
        self.setup_logging()
        print("🤖 Agent Manager initialized (Real Telegram + Reddit Simulation)")
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('agent_system.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    @trace_function(name="agent_start")
    def start_agent(self, agent_id):
        """Start an agent - Real Telegram or Simulation for Reddit"""
        if agent_id not in ['telegram', 'reddit']:
            return {'success': False, 'message': 'Invalid agent'}
        
        agents = self.db.get_agents()
        if agents.get(agent_id, {}).get('status') == 'running':
            return {'success': False, 'message': 'Agent already running'}
        
        print(f"\n{'='*60}")
        print(f"🚀 STARTING {agent_id.upper()} AGENT")
        print(f"{'='*60}")
        
        try:
            trace_id = f"start_{agent_id}_{int(time.time())}"
            
            self.db.add_agent_log(agent_id, 'start', f'Starting {agent_id} agent', trace_id=trace_id)
            
            if agent_id == 'telegram':
                result = self._start_real_telegram_agent()
            elif agent_id == 'reddit':
                result = self._start_simulation_agent(agent_id)
            
            if langsmith_client and LANGCHAIN_AVAILABLE:
                try:
                    langsmith_client.create_run(
                        name=f"agent_start_{agent_id}",
                        run_type="chain",
                        inputs={"agent_id": agent_id},
                        outputs=result,
                        project_name=LANGSMITH_PROJECT,
                        tags=["agent_start", agent_id, "success" if result['success'] else "failed"]
                    )
                except Exception as e:
                    print(f"⚠️ LangSmith logging error: {e}")
            
            return result
            
        except Exception as e:
            error_msg = f'Failed to start agent: {str(e)}'
            self.db.add_agent_log(agent_id, 'error', error_msg)
            return {'success': False, 'message': error_msg}
    
    def _start_real_telegram_agent(self):
        """Start the real Telegram agent with proper error handling"""
        try:
            print("🤖 Attempting to start REAL Telegram agent...")
            
            if not os.path.exists('telegram_agent.py'):
                error_msg = "telegram_agent.py not found!"
                print(f"❌ {error_msg}")
                self.db.add_agent_log('telegram', 'error', error_msg, 'Create telegram_agent.py file')
                return {'success': False, 'message': 'Telegram agent file not found'}
            
            try:
                if 'telegram_agent' in sys.modules:
                    del sys.modules['telegram_agent']
                
                from telegram_agent import TelegramMonitorAgent
                print("✅ Telegram agent module imported successfully")
            except ImportError as e:
                error_msg = f"Failed to import telegram_agent: {str(e)}"
                print(f"❌ {error_msg}")
                self.db.add_agent_log('telegram', 'error', error_msg)
                return {'success': False, 'message': f'Import error: {str(e)}'}
            
            self.telegram_agent_instance = TelegramMonitorAgent()
            print("✅ Telegram agent instance created")
            
            self.telegram_agent_thread = threading.Thread(
                target=self._run_telegram_agent,
                daemon=True
            )
            
            self.agents['telegram'] = {
                'thread': self.telegram_agent_thread,
                'running': True,
                'instance': self.telegram_agent_instance,
                'is_simulation': False
            }
            
            self.telegram_agent_thread.start()
            
            time.sleep(3)
            
            if not self.agents['telegram'].get('running', False):
                error_msg = "Agent failed to initialize"
                print(f"❌ {error_msg}")
                self.db.add_agent_log('telegram', 'error', error_msg)
                return {'success': False, 'message': 'Agent failed to initialize'}
            
            self.db.update_agent_status('telegram', 'running')
            
            self.db.add_agent_log('telegram', 'start', 'Real Telegram agent started successfully', 'Using actual Telegram API with Llama3 AI')
            
            return {'success': True, 'message': 'Real Telegram agent started successfully'}
            
        except Exception as e:
            error_msg = f'Failed to start Telegram agent: {str(e)}'
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            self.db.add_agent_log('telegram', 'error', error_msg, str(e))
            
            return {'success': False, 'message': f'Failed to start: {str(e)}'}
    
    @trace_function(name="simulation_start")
    def _start_simulation_agent(self, agent_id):
        """Start simulation agent for Reddit"""
        print(f"🤖 Starting SIMULATION agent for {agent_id}")
    
    # Create simulation thread
        sim_thread = threading.Thread(
        target=self._run_simulation_agent,
        args=(agent_id,),
        daemon=True
        )
    
        self.simulation_agents[agent_id] = {
        'thread': sim_thread,
        'running': True,
        'is_simulation': True
        }
    
        sim_thread.start()
    
    # Update database status
        self.db.update_agent_status(agent_id, 'running')
    
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
            
            # Count active channels for this source
                cursor.execute('''
                SELECT COUNT(*) FROM monitored_channels 
                WHERE source = ? AND is_active = 1
            ''', (agent_id,))
                count = cursor.fetchone()[0]
            
                cursor.execute('''
                UPDATE agents 
                SET channels_monitored = ?
                WHERE id = ?
            ''', (count, agent_id))
                conn.commit()
        except Exception as e:
            print(f"⚠️ Could not update channel count: {e}")
        # Fallback to random number
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE agents 
                SET channels_monitored = ?
                WHERE id = ?
            ''', (random.randint(2, 5), agent_id))
                conn.commit()
    
        self.db.add_agent_log(agent_id, 'start', f'Simulation agent started', 
                        f'Generating realistic simulation data for {agent_id}')
    
        return {'success': True, 'message': f'Simulation agent for {agent_id} started'}
    
    @trace_function(name="simulation_run")
    def _run_simulation_agent(self, agent_id):
        """Run simulation agent to generate realistic data for Reddit"""
        print(f"🎮 Simulation agent {agent_id} running...")
        
        sim_config = {
            'reddit': {
                'platform': 'Reddit',
                'channels': [
                    'r/darknet',
                    'r/drugs',
                    'r/RCsources',
                    'r/researchchemicals',
                    'r/DNMBusts',
                    'r/Opioids',
                    'r/Stims',
                    'r/benzodiazepines'
                ],
                'keywords': ['vendor', 'ship', 'tracking', 'encrypted', 'bitcoin', 'escrow', 
                           'plug', 'connect', 'telegram', 'w/e', 'dd', 'btc', 'pgp'],
                'user_patterns': ['throwaway', 'anon', 'temp', 'burner', 'deleted']
            }
        }
        
        config = sim_config.get(agent_id, {})
        
        try:
            while self.simulation_agents.get(agent_id, {}).get('running', False):
                time.sleep(random.randint(10, 30))
                
                if random.random() < 0.3:
                    self._generate_simulation_alert(agent_id, config)
                
                if random.random() < 0.4:
                    self._generate_simulation_log(agent_id, config)
                
                if random.random() < 0.2:
                    self._update_simulation_stats(agent_id)
                    
        except Exception as e:
            print(f"❌ Simulation agent {agent_id} error: {e}")
    
    @trace_function(name="simulation_alert")
    def _generate_simulation_alert(self, agent_id, config):
        """Generate a realistic simulation alert"""
        alert_templates = [
            f"Potential drug-related content detected: '{{keyword}}' mentioned",
            f"Suspicious user pattern detected: {{user}} appears to be a vendor",
            f"Discussion about illegal substance transactions",
            f"Request for bulk delivery of controlled substances",
            f"Coded language detected suggesting illegal activities",
            f"Bitcoin address shared for payment - potential transaction",
            f"Encrypted message detected - PGP key exchange"
        ]
        
        keyword = random.choice(config.get('keywords', []))
        user = random.choice(config.get('user_patterns', [])) + str(random.randint(100, 999))
        channel = random.choice(config.get('channels', []))
        template = random.choice(alert_templates)
        
        message = template.format(keyword=keyword, user=user)
        
        trace_id = f"sim_alert_{agent_id}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        alert_id = self.db.add_alert(
            source=agent_id,
            channel=channel,
            risk_level=random.choice(['low', 'medium', 'medium', 'high']),
            message=message,
            confidence=random.randint(60, 95),
            ai_model='Llama3-Simulation',
            trace_id=trace_id,
            metadata={
                'simulation': True,
                'keyword': keyword,
                'user': user,
                'template': template,
                'channel': channel
            }
        )
        
        if alert_id:
            self.db.add_agent_log(agent_id, 'alert', f'Simulation alert generated: {message[:50]}...', 
                                f'Alert #{alert_id} in {channel}', trace_id=trace_id)
        
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE agents 
                SET messages_analyzed = messages_analyzed + 1,
                    last_activity = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (agent_id,))
            conn.commit()
    
    def _generate_simulation_log(self, agent_id, config):
        """Generate simulation activity log"""
        log_types = ['scan', 'info', 'monitor']
        log_type = random.choice(log_types)
        
        logs = {
            'scan': [
                f"Scanning {random.choice(config.get('channels', []))} for suspicious content",
                f"Analyzing recent posts in monitored subreddits",
                f"Performing keyword analysis on recent comments",
                f"Checking new submissions in monitored subreddits"
            ],
            'info': [
                f"Monitoring {random.randint(3, 8)} active subreddits",
                f"Processed {random.randint(50, 200)} messages in last hour",
                f"AI model analyzing patterns in user behavior",
                f"Found {random.randint(1, 10)} new potential leads"
            ],
            'monitor': [
                f"New user joined monitored subreddit: {random.choice(config.get('user_patterns', []))}",
                f"Subreddit activity level: {random.choice(['low', 'normal', 'high'])}",
                f"Updated monitoring filters for improved detection",
                f"Detected spike in drug-related terminology"
            ]
        }
        
        message = random.choice(logs.get(log_type, ['Simulation activity']))
        
        self.db.add_agent_log(agent_id, log_type, message)
    
    def _update_simulation_stats(self, agent_id):
        """Update simulation agent statistics"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            increment = random.randint(10, 50)
            cursor.execute('''
                UPDATE agents 
                SET messages_analyzed = messages_analyzed + ?,
                    last_activity = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (increment, agent_id))
            
            conn.commit()
    
    @trace_function(name="telegram_run")
    def _run_telegram_agent(self):
        """Run the actual Telegram agent"""
        try:
            print("🤖 REAL TELEGRAM AGENT STARTING...")
            self.db.add_agent_log('telegram', 'info', 'Real Telegram agent thread starting')
            
            import asyncio
            
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            agent = self.telegram_agent_instance
            
            async def run_agent():
                if await agent.initialize():
                    self.db.add_agent_log('telegram', 'info', 'Telegram agent initialized successfully', 'Connected to Telegram and AI services')
                    await agent.run()
                else:
                    self.db.add_agent_log('telegram', 'error', 'Failed to initialize Telegram agent', 'Check credentials and network connection')
            
            loop.run_until_complete(run_agent())
            
        except Exception as e:
            error_msg = f"Telegram agent error: {str(e)}"
            print(f"❌ {error_msg}")
            self.db.add_agent_log('telegram', 'error', error_msg)
            
            if 'telegram' in self.agents:
                self.agents['telegram']['running'] = False
    
    @trace_function(name="agent_stop")
    def stop_agent(self, agent_id):
        """Stop an agent"""
        print(f"\n{'='*60}")
        print(f"🛑 STOPPING {agent_id.upper()} AGENT")
        print(f"{'='*60}")
        
        if agent_id == 'telegram' and agent_id in self.agents:
            self.agents[agent_id]['running'] = False
            if self.telegram_agent_instance:
                self.telegram_agent_instance.is_running = False
                
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def shutdown():
                        await self.telegram_agent_instance.shutdown()
                    
                    loop.run_until_complete(shutdown())
                except:
                    pass
                
            del self.agents[agent_id]
        
        elif agent_id in self.simulation_agents:
            self.simulation_agents[agent_id]['running'] = False
            del self.simulation_agents[agent_id]
        
        self.db.update_agent_status(agent_id, 'stopped')
        
        self.db.add_agent_log(agent_id, 'stop', 'Agent stopped successfully')
        
        return {'success': True, 'message': f'{agent_id} agent stopped'}
    
    def get_agent_status(self, agent_id):
        """Get detailed agent status"""
        if agent_id == 'telegram' and agent_id in self.agents:
            agent = self.agents[agent_id]
            return {
                'running': agent.get('running', False),
                'is_simulation': False,
                'has_instance': 'instance' in agent,
                'thread_alive': agent.get('thread', None) and agent['thread'].is_alive()
            }
        elif agent_id in self.simulation_agents:
            agent = self.simulation_agents[agent_id]
            return {
                'running': agent.get('running', False),
                'is_simulation': True,
                'thread_alive': agent.get('thread', None) and agent['thread'].is_alive()
            }
        return {'running': False, 'is_simulation': False}
    
    def get_telegram_channels(self):
        """Get channels from real Telegram agent"""
        try:
            if self.telegram_agent_instance:
                channels = self.telegram_agent_instance.monitored_channels
                return {
                    'channels': channels,
                    'count': len(channels),
                    'source': 'live_agent',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT channel_name FROM monitored_channels 
                        WHERE source = 'telegram' AND is_active = 1
                    ''')
                    channels = [row[0] for row in cursor.fetchall()]
                    return {
                        'channels': channels,
                        'count': len(channels),
                        'source': 'database',
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {
                'channels': [],
                'count': 0,
                'source': 'error',
                'error': str(e)
            }
    
    def get_simulation_channels(self, agent_id):
        """Get channels for simulation agents"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT channel_name FROM monitored_channels 
                    WHERE source = ? AND is_active = 1
                ''', (agent_id,))
                channels = [row[0] for row in cursor.fetchall()]
                
                if channels:
                    return {
                        'channels': channels,
                        'count': len(channels),
                        'source': 'database',
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    sim_channels = {
                        'reddit': [
                            'r/darknet',
                            'r/drugs',
                            'r/RCsources',
                            'r/researchchemicals',
                            'r/DNMBusts',
                            'r/Opioids',
                            'r/Stims',
                            'r/benzodiazepines'
                        ]
                    }
                    return {
                        'channels': sim_channels.get(agent_id, []),
                        'count': len(sim_channels.get(agent_id, [])),
                        'source': 'simulation',
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            return {
                'channels': [],
                'count': 0,
                'source': 'error',
                'error': str(e)
            }
    
    @trace_function(name="add_test_alert")
    def add_test_alert(self, agent_id='telegram'):
        """Add a test alert"""
        try:
            if agent_id == 'telegram':
                channels = ['@test_channel', '@monitoring_test', '@ai_analysis_test']
                messages = [
                    "Test alert: Suspected drug trafficking activity detected",
                    "AI analysis indicates high risk content in monitored channel",
                    "Pattern matching found suspicious transaction terms"
                ]
            else:
                channels = ['r/test_monitoring', 'r/simulation_alerts', 'r/drug_testing']
                messages = [
                    "Reddit simulation: Suspicious vendor discussion detected",
                    "Potential sourcing of controlled substances",
                    "Discussion about illegal marketplace activities",
                    "Bitcoin address shared in comments"
                ]
            
            channel = random.choice(channels)
            message = random.choice(messages)
            
            trace_id = f"test_alert_{agent_id}_{int(time.time())}_{random.randint(1000, 9999)}"
            
            alert_id = self.db.add_alert(
                source=agent_id,
                channel=channel,
                risk_level='high',
                message=message,
                confidence=random.randint(85, 95),
                ai_model='Llama3-Test',
                trace_id=trace_id,
                metadata={'test': True, 'channel': channel, 'source': agent_id}
            )
            
            if alert_id:
                self.db.add_agent_log(agent_id, 'alert', 'Test alert generated', 
                                    f'Alert #{alert_id} - {message}', trace_id=trace_id)
                
                with sqlite3.connect(self.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE agents 
                        SET total_alerts = total_alerts + 1,
                            last_activity = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (agent_id,))
                    conn.commit()
                
                return {'success': True, 'alert_id': alert_id, 'message': f'Test alert #{alert_id} added'}
            else:
                return {'success': False, 'message': 'Failed to add test alert to database'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ==============================================
# Initialize System
# ==============================================
db_manager = DatabaseManager()
agent_manager = AgentManager(db_manager)

# ==============================================
# Flask Routes with LangSmith Tracing
# ==============================================

@app.route('/')
@trace_function(name="home_page")
def index():
    """Home page with fallback"""
    try:
        return render_template('index.html')
    except:
        return """
        <html>
            <head><title>Nexus AI</title></head>
            <body style="font-family: Arial; padding: 20px;">
                <h1>🚀 Nexus AI Monitoring System</h1>
                <p>✅ Server is running successfully!</p>
                <ul>
                    <li><a href="/dashboard">📊 Dashboard</a></li>
                    <li><a href="/slang_galley">🌌 Slang Galaxy</a></li>
                    <li><a href="/health">🔧 Health Check</a></li>
                </ul>
                <hr>
                <pre>System Status: Online</pre>
            </body>
        </html>
        """
@app.route('/dashboard')
@trace_function(name="dashboard_page")
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/dashboard.html')
def redirect_dashboard():
    """Redirect from old URL"""
    from flask import redirect
    return redirect('/dashboard')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/agent-info/<agent_id>')
@trace_function(name="api_agent_info")
def get_agent_info(agent_id):
    """Get detailed agent information"""
    agents = db_manager.get_agents()
    agent_data = agents.get(agent_id, {})
    
    live_status = agent_manager.get_agent_status(agent_id)
    
    agent_type = 'real' if agent_id == 'telegram' and not live_status.get('is_simulation', True) else 'simulation'
    
    return jsonify({
        'id': agent_id,
        'name': agent_data.get('name', agent_id),
        'status': agent_data.get('status', 'stopped'),
        'agent_type': agent_type,
        'live_status': live_status,
        'stats': {
            'total_alerts': agent_data.get('total_alerts', 0),
            'channels_monitored': agent_data.get('channels_monitored', 0),
            'messages_analyzed': agent_data.get('messages_analyzed', 0),
            'last_activity': agent_data.get('last_activity'),
            'last_started': agent_data.get('last_started'),
            'last_stopped': agent_data.get('last_stopped')
        }
    })

@app.route('/api/agent-channels/<agent_id>')
@trace_function(name="api_agent_channels")
def get_agent_channels(agent_id):
    """Get channels being monitored by agent"""
    try:
        if agent_id == 'telegram' and agent_manager.telegram_agent_instance:
            channels = agent_manager.telegram_agent_instance.monitored_channels
            return jsonify({
                'channels': channels,
                'count': len(channels),
                'source': 'live_agent',
                'agent_type': 'real'
            })
        
        elif agent_id == 'reddit':
            sim_data = agent_manager.get_simulation_channels(agent_id)
            return jsonify({
                **sim_data,
                'agent_type': 'simulation'
            })
        
        return jsonify({
            'channels': [],
            'count': 0,
            'source': 'none',
            'agent_type': 'unknown'
        })
        
    except Exception as e:
        return jsonify({
            'channels': [],
            'count': 0,
            'source': 'error',
            'error': str(e)
        })
    

@app.route('/api/stats')
@trace_function(name="api_stats")
def get_stats():
    """Get system statistics"""
    stats = db_manager.get_stats()
    agents = db_manager.get_agents()
    
    running_agents = sum(1 for agent in agents.values() if agent['status'] == 'running')
    
    if langsmith_client and LANGCHAIN_AVAILABLE:
        try:
            langsmith_client.create_run(
                name="stats_request",
                run_type="chain",
                inputs={"timestamp": datetime.now().isoformat()},
                outputs=stats,
                project_name=LANGSMITH_PROJECT,
                tags=["stats", "api"]
            )
        except Exception as e:
            print(f"⚠️ LangSmith logging error: {e}")
    
    return jsonify({
        **stats,
        'running_agents': running_agents,
        'system_status': 'active',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/alerts')
@trace_function(name="api_alerts")
def get_alerts():
    """Get alerts with filtering"""
    source = request.args.get('source', 'all')
    limit = int(request.args.get('limit', 50))
    min_confidence = int(request.args.get('min_confidence', 50))
    
    alerts = db_manager.get_alerts(source=source, limit=limit, min_confidence=min_confidence)
    
    if langsmith_client and LANGCHAIN_AVAILABLE and alerts:
        try:
            langsmith_client.create_run(
                name="alerts_request",
                run_type="chain",
                inputs={"source": source, "limit": limit, "min_confidence": min_confidence},
                outputs={"alerts_count": len(alerts)},
                project_name=LANGSMITH_PROJECT,
                tags=["alerts", source, f"count_{len(alerts)}"]
            )
        except Exception as e:
            print(f"⚠️ LangSmith logging error: {e}")
    
    return jsonify({'alerts': alerts})

@app.route('/api/agents')
@trace_function(name="api_agents")
def get_agents():
    """Get all agents"""
    agents_data = db_manager.get_agents()
    
    agents_info = []
    for agent_id, data in agents_data.items():
        agents_info.append({
            'id': agent_id,
            'name': data['name'],
            'status': data['status'],
            'stats': {
                'total_alerts': data['total_alerts'],
                'channels_monitored': data['channels_monitored'],
                'messages_analyzed': data['messages_analyzed'],
                'last_activity': data['last_activity']
            }
        })
    
    return jsonify({'agents': agents_info})

@app.route('/api/agent-logs')
@trace_function(name="api_agent_logs")
def get_agent_logs():
    """Get agent activity logs"""
    agent_id = request.args.get('agent_id')
    limit = int(request.args.get('limit', 50))
    
    logs = db_manager.get_agent_logs(agent_id=agent_id, limit=limit)
    return jsonify({'logs': logs})

@app.route('/api/agents/start', methods=['POST'])
@trace_function(name="api_start_agent")
def start_agent():
    """Start an agent"""
    data = request.json
    agent_id = data.get('agent_id', '').lower()
    
    if not agent_id:
        return jsonify({'success': False, 'message': 'No agent specified'}), 400
    
    result = agent_manager.start_agent(agent_id)
    return jsonify(result)

@app.route('/api/agents/stop', methods=['POST'])
@trace_function(name="api_stop_agent")
def stop_agent():
    """Stop an agent"""
    data = request.json
    agent_id = data.get('agent_id', '').lower()
    
    if not agent_id:
        return jsonify({'success': False, 'message': 'No agent specified'}), 400
    
    result = agent_manager.stop_agent(agent_id)
    return jsonify(result)

@app.route('/api/agents/start-all', methods=['POST'])
@trace_function(name="api_start_all_agents")
def start_all_agents():
    """Start all agents"""
    results = {}
    for agent_id in ['telegram', 'reddit']:
        results[agent_id] = agent_manager.start_agent(agent_id)
    
    all_success = all(result.get('success', False) for result in results.values())
    
    return jsonify({
        'success': all_success,
        'message': 'All agents starting' if all_success else 'Some agents failed to start',
        'results': results
    })

@app.route('/api/agents/stop-all', methods=['POST'])
@trace_function(name="api_stop_all_agents")
def stop_all_agents():
    """Stop all agents"""
    results = {}
    for agent_id in ['telegram', 'reddit']:
        results[agent_id] = agent_manager.stop_agent(agent_id)
    
    return jsonify({
        'success': True,
        'message': 'All agents stopping',
        'results': results
    })

@app.route('/api/test-alert', methods=['POST'])
@trace_function(name="api_test_alert")
def test_alert():
    """Add a test alert"""
    data = request.json
    source = data.get('source', 'telegram')
    
    result = agent_manager.add_test_alert(source)
    return jsonify(result)

@app.route('/health')
@trace_function(name="health_check")
def health_check():
    """Health endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '3.0.0',
        'agents_running': len(agent_manager.agents),
        'langsmith': {
            'enabled': langsmith_client is not None,
            'project': LANGSMITH_PROJECT if langsmith_client else None
        }
    })

@app.route('/alerts')
@trace_function(name="alerts_page")
def alerts():
    return render_template('alert.html')

# ==============================================
# Channel Management Routes
# ==============================================

@app.route('/api/add-channel', methods=['POST'])
@trace_function(name="api_add_channel")
def add_channel():
    """Add a new channel to monitor and scan it immediately"""
    data = request.json
    source = data.get('source', '').lower()
    channel = data.get('channel', '').strip()
    
    if not source or not channel:
        return jsonify({'success': False, 'message': 'Source and channel are required'}), 400
    
    if source not in ['telegram', 'reddit']:
        return jsonify({'success': False, 'message': 'Invalid source. Must be telegram or reddit'}), 400
    
    # Clean channel name
    if source == 'telegram':
        clean_channel = channel.replace('@', '')
        display_channel = f"@{clean_channel}"
        search_term = clean_channel
    else:
        if channel.startswith('r/'):
            clean_channel = channel[2:]
        else:
            clean_channel = channel
        display_channel = f"r/{clean_channel}"
        search_term = clean_channel
    
    try:
        # Database operations
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if source column exists
            cursor.execute("PRAGMA table_info(monitored_channels)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'source' not in columns:
                cursor.execute('ALTER TABLE monitored_channels ADD COLUMN source TEXT DEFAULT "telegram"')
                conn.commit()
                print("✅ Added source column to monitored_channels table")
            
            # Check if channel exists
            cursor.execute('''
                SELECT channel_name, is_active FROM monitored_channels 
                WHERE channel_name = ? AND source = ?
            ''', (display_channel, source))
            
            existing = cursor.fetchone()
            channel_id = None
            
            if existing:
                if existing[1] == 1:
                    message = f'Channel {display_channel} is already being monitored. Scanning now...'
                    cursor.execute('SELECT id FROM monitored_channels WHERE channel_name = ? AND source = ?', 
                                  (display_channel, source))
                    result = cursor.fetchone()
                    channel_id = result[0] if result else None
                else:
                    cursor.execute('''
                        UPDATE monitored_channels 
                        SET is_active = 1, last_error = NULL
                        WHERE channel_name = ? AND source = ?
                    ''', (display_channel, source))
                    conn.commit()
                    message = f'Reactivated {display_channel} for monitoring'
                    cursor.execute('SELECT id FROM monitored_channels WHERE channel_name = ? AND source = ?', 
                                  (display_channel, source))
                    result = cursor.fetchone()
                    channel_id = result[0] if result else None
            else:
                cursor.execute('''
                    INSERT INTO monitored_channels (channel_name, source, is_active, added_date)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                ''', (display_channel, source))
                conn.commit()
                channel_id = cursor.lastrowid
                message = f'Successfully added {display_channel} to monitoring'
            
            # Update agent stats
            cursor.execute('''
                UPDATE agents 
                SET channels_monitored = (
                    SELECT COUNT(*) FROM monitored_channels WHERE is_active = 1 AND source = ?
                )
                WHERE id = ?
            ''', (source, source))
            
            conn.commit()
        
        # Log the addition
        db_manager.add_agent_log(
            source,
            'info',
            f'New channel added: {display_channel}',
            f'Added via dashboard'
        )
        
        # SCAN THE NEW CHANNEL
        scan_result = None
        alerts_created = []
        
        if source == 'telegram' and agent_manager.telegram_agent_instance:
            # Add to agent's monitored channels
            if display_channel not in agent_manager.telegram_agent_instance.monitored_channels:
                agent_manager.telegram_agent_instance.monitored_channels.append(display_channel)
            
            # Trigger immediate scan
            import asyncio
            loop = None
            if hasattr(agent_manager.telegram_agent_instance, 'loop') and agent_manager.telegram_agent_instance.loop:
                loop = agent_manager.telegram_agent_instance.loop
            else:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            async def scan_new_channel():
                try:
                    print(f"\n{'='*60}")
                    print(f"🔍 IMMEDIATE SCAN of new channel: {display_channel}")
                    print(f"{'='*60}")
                    
                    if hasattr(agent_manager.telegram_agent_instance, 'scan_single_channel'):
                        result = await agent_manager.telegram_agent_instance.scan_single_channel(search_term)
                    else:
                        await agent_manager.telegram_agent_instance.scan_channel(search_term)
                        result = {"status": "success", "channel": display_channel}
                    
                    # Get alerts created
                    with sqlite3.connect(db_manager.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT id, message, confidence, risk_level 
                            FROM alerts 
                            WHERE channel = ? 
                            ORDER BY timestamp DESC 
                            LIMIT 10
                        ''', (display_channel,))
                        new_alerts = []
                        for row in cursor.fetchall():
                            new_alerts.append({
                                'id': row[0],
                                'message': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                                'confidence': row[2],
                                'risk_level': row[3]
                            })
                    
                    print(f"\n📊 SCAN RESULTS for {display_channel}:")
                    print(f"   • Messages scanned: {result.get('messages', 0)}")
                    print(f"   • Alerts created: {len(new_alerts)}")
                    for alert in new_alerts:
                        print(f"   🚨 Alert #{alert['id']}: {alert['risk_level'].upper()} - {alert['message']} ({alert['confidence']}%)")
                    
                    return {
                        "status": "success", 
                        "message": f"Scanned {display_channel}",
                        "alerts": new_alerts,
                        "scan_details": result
                    }
                except Exception as e:
                    print(f"❌ Error scanning new channel: {e}")
                    import traceback
                    traceback.print_exc()
                    return {"status": "error", "message": str(e)}
            
            future = asyncio.run_coroutine_threadsafe(scan_new_channel(), loop)
            try:
                scan_result = future.result(timeout=120)
                if scan_result and scan_result.get('status') == 'success':
                    alerts_created = scan_result.get('alerts', [])
            except Exception as e:
                scan_result = {"status": "error", "message": str(e)}
                print(f"❌ Scan timeout or error: {e}")
        
        elif source == 'reddit':
            scan_result = {
                "status": "info", 
                "message": f"Reddit channel {display_channel} added. Will be scanned in next cycle.",
                "alerts": []
            }
        
        # Prepare response
        response_data = {
            'success': True,
            'message': message,
            'channel': display_channel,
            'source': source,
            'channel_id': channel_id,
            'scan_result': scan_result,
            'alerts_created': alerts_created
        }
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ CHANNEL ADDED: {display_channel} ({source})")
        print(f"{'='*60}")
        if scan_result and scan_result.get('status') == 'success':
            print(f"📊 Scan completed: {len(alerts_created)} alerts generated")
        print(f"{'='*60}\n")
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Error adding channel: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error adding channel: {str(e)}'
        }), 500
    
@app.route('/api/scan-channel', methods=['POST'])
@trace_function(name="api_scan_channel")
def scan_channel():
    """Manually scan a specific channel"""
    data = request.json
    channel = data.get('channel', '').strip()
    source = data.get('source', 'telegram').lower()
    
    if not channel:
        return jsonify({'success': False, 'message': 'Channel name is required'}), 400
    
    if source == 'telegram':
        clean_channel = channel.replace('@', '')
        display_channel = f"@{clean_channel}"
    else:
        if channel.startswith('r/'):
            clean_channel = channel[2:]
        else:
            clean_channel = channel
        display_channel = f"r/{clean_channel}"
    
    scan_result = None
    alerts_created = []
    
    if source == 'telegram' and agent_manager.telegram_agent_instance:
        import asyncio
        loop = agent_manager.telegram_agent_instance.loop if hasattr(agent_manager.telegram_agent_instance, 'loop') else asyncio.new_event_loop()
        
        async def scan():
            try:
                print(f"\n{'='*60}")
                print(f"🔍 MANUAL SCAN of channel: {display_channel}")
                print(f"{'='*60}")
                
                if hasattr(agent_manager.telegram_agent_instance, 'scan_single_channel'):
                    result = await agent_manager.telegram_agent_instance.scan_single_channel(clean_channel)
                else:
                    await agent_manager.telegram_agent_instance.scan_channel(clean_channel)
                    result = {"status": "success", "channel": display_channel}
                
                with sqlite3.connect(db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT id, message, confidence, risk_level 
                        FROM alerts 
                        WHERE channel = ? 
                        ORDER BY timestamp DESC 
                        LIMIT 10
                    ''', (display_channel,))
                    for row in cursor.fetchall():
                        alerts_created.append({
                            'id': row[0],
                            'message': row[1][:100] + '...' if len(row[1]) > 100 else row[1],
                            'confidence': row[2],
                            'risk_level': row[3]
                        })
                
                print(f"\n📊 SCAN RESULTS:")
                print(f"   • Alerts created: {len(alerts_created)}")
                for alert in alerts_created:
                    print(f"   🚨 Alert #{alert['id']}: {alert['risk_level'].upper()} - {alert['message']} ({alert['confidence']}%)")
                
                return {"status": "success", "alerts": alerts_created}
            except Exception as e:
                print(f"❌ Scan error: {e}")
                return {"status": "error", "message": str(e)}
        
        future = asyncio.run_coroutine_threadsafe(scan(), loop)
        try:
            scan_result = future.result(timeout=120)
        except Exception as e:
            scan_result = {"status": "error", "message": str(e)}
    
    return jsonify({
        'success': scan_result.get('status') == 'success' if scan_result else False,
        'message': scan_result.get('message', 'Scan completed') if scan_result else 'Scan triggered',
        'channel': display_channel,
        'alerts': alerts_created
    })

@app.route('/api/channels')
@trace_function(name="api_get_channels")
def get_channels():
    """Get all monitored channels"""
    source = request.args.get('source', 'all')
    
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            if source == 'all':
                cursor.execute('''
                    SELECT channel_name, source, added_date, total_messages, total_alerts, last_scanned, id
                    FROM monitored_channels 
                    WHERE is_active = 1
                    ORDER BY source, added_date DESC
                ''')
            else:
                cursor.execute('''
                    SELECT channel_name, source, added_date, total_messages, total_alerts, last_scanned, id
                    FROM monitored_channels 
                    WHERE is_active = 1 AND source = ?
                    ORDER BY added_date DESC
                ''', (source,))
            
            channels = []
            for row in cursor.fetchall():
                channels.append({
                    'id': row[6],
                    'name': row[0],
                    'source': row[1],
                    'added_date': row[2],
                    'total_messages': row[3] or 0,
                    'total_alerts': row[4] or 0,
                    'last_scanned': row[5]
                })
            
            return jsonify({
                'success': True,
                'channels': channels,
                'count': len(channels)
            })
            
    except Exception as e:
        print(f"❌ Error getting channels: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting channels: {str(e)}'
        }), 500

@app.route('/api/remove-channel', methods=['POST'])
@trace_function(name="api_remove_channel")
def remove_channel():
    """Remove a channel from monitoring"""
    data = request.json
    channel = data.get('channel', '').strip()
    source = data.get('source', '').lower()
    
    if not channel or not source:
        return jsonify({'success': False, 'message': 'Channel and source are required'}), 400
    
    try:
        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE monitored_channels 
                SET is_active = 0 
                WHERE channel_name = ? AND source = ?
            ''', (channel, source))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': f'Channel {channel} not found'})
            
            conn.commit()
            
            cursor.execute('''
                UPDATE agents 
                SET channels_monitored = (
                    SELECT COUNT(*) FROM monitored_channels WHERE is_active = 1 AND source = ?
                )
                WHERE id = ?
            ''', (source, source))
            
            conn.commit()
        
        db_manager.add_agent_log(
            source,
            'info',
            f'Channel removed: {channel}',
            f'Removed from monitoring'
        )
        
        if source == 'telegram' and agent_manager.telegram_agent_instance:
            if channel in agent_manager.telegram_agent_instance.monitored_channels:
                agent_manager.telegram_agent_instance.monitored_channels.remove(channel)
        
        print(f"\n{'='*60}")
        print(f"🗑️ CHANNEL REMOVED: {channel} ({source})")
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'message': f'Successfully removed {channel} from monitoring'
        })
        
    except Exception as e:
        print(f"❌ Error removing channel: {e}")
        return jsonify({
            'success': False,
            'message': f'Error removing channel: {str(e)}'
        }), 500

# ==============================================
# LangSmith Analytics Endpoint
# ==============================================

@app.route('/api/test-langsmith')
@trace_function(name="test_langsmith")
def test_langsmith():
    """Test LangSmith connection"""
    if not langsmith_client:
        return jsonify({
            'status': 'error',
            'message': 'LangSmith not configured',
            'project': LANGSMITH_PROJECT
        })
    
    try:
        run_id = f"test_{int(time.time())}"
        run = langsmith_client.create_run(
            name="api_test_connection",
            run_type="chain",
            inputs={"test": True, "timestamp": datetime.now().isoformat()},
            outputs={"status": "success", "message": "LangSmith is working!"},
            project_name=LANGSMITH_PROJECT,
            tags=["test", "api"]
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Test run created successfully',
            'project': LANGSMITH_PROJECT,
            'run_id': str(run.id) if run else run_id,
            'dashboard_url': f'https://smith.langchain.com/projects/{LANGSMITH_PROJECT}'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'project': LANGSMITH_PROJECT
        })

@app.route('/api/langsmith/runs')
@trace_function(name="api_langsmith_runs")
def get_langsmith_runs():
    """Get recent LangSmith runs"""
    if not langsmith_client or not LANGCHAIN_AVAILABLE:
        return jsonify({'error': 'LangSmith not configured'}), 404
    
    try:
        limit = int(request.args.get('limit', 20))
        project = LANGSMITH_PROJECT
        
        runs = langsmith_client.list_runs(
            project_name=project,
            limit=limit
        )
        
        return jsonify({
            'runs': [{
                'id': run.id,
                'name': run.name,
                'start_time': run.start_time.isoformat() if run.start_time else None,
                'end_time': run.end_time.isoformat() if run.end_time else None,
                'status': run.status,
                'error': run.error
            } for run in runs]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==============================================
# Slang Galaxy Routes - Using JSON Data
# ==============================================

@app.route('/slang_galaxy')
@trace_function(name="slang_galaxy_page")
def slang_galaxy():
    """Slang galaxy visualization page"""
    return render_template('slang_galaxy.html')

@app.route('/api/slang-stats')
@trace_function(name="api_slang_stats")
def get_slang_stats():
    """Get slang cluster statistics from JSON data"""
    
    # Handle empty clusters.json
    if not CLUSTER_DATA:
        return jsonify({
            'established_clusters': 0,
            'emerging_patterns': 0,
            'new_detections': 0,
            'clusters': []
        })
    
    established = len([c for c in CLUSTER_DATA if c.get('type') == 'established'])
    emerging = len([c for c in CLUSTER_DATA if c.get('type') == 'emerging'])
    new = len([c for c in CLUSTER_DATA if c.get('type') == 'new'])
    
    return jsonify({
        'established_clusters': established,
        'emerging_patterns': emerging,
        'new_detections': new,
        'clusters': CLUSTER_DATA
    })

@app.route('/api/slang-cluster/<int:cluster_id>')
@trace_function(name="api_slang_cluster")
def get_slang_cluster(cluster_id):
    """Get detailed information about a specific cluster from JSON data"""
    
    cluster = next((c for c in CLUSTER_DATA if c.get('id') == cluster_id), None)
    
    if cluster:
        return jsonify(cluster)
    else:
        return jsonify({'error': 'Cluster not found'}), 404

@app.route('/api/slang/confirm/<int:cluster_id>', methods=['POST'])
@trace_function(name="api_slang_confirm")
def confirm_slang(cluster_id):
    """Confirm a new slang cluster"""
    data = request.json
    cluster_name = data.get('name', f'Cluster {cluster_id}')
    
    cluster = next((c for c in CLUSTER_DATA if c.get('id') == cluster_id), None)
    
    if cluster:
        db_manager.add_agent_log(
            'system', 
            'info', 
            f'✅ New slang cluster confirmed: {cluster_name}',
            f'Cluster #{cluster_id} moved from {cluster.get("type", "unknown")} to established patterns'
        )
    
    return jsonify({
        'success': True,
        'message': f'Slang cluster "{cluster_name}" confirmed and added to established patterns',
        'cluster_id': cluster_id
    })

@app.route('/api/slang/deny/<int:cluster_id>', methods=['POST'])
@trace_function(name="api_slang_deny")
def deny_slang(cluster_id):
    """Deny a new slang cluster"""
    data = request.json
    cluster_name = data.get('name', f'Cluster {cluster_id}')
    
    cluster = next((c for c in CLUSTER_DATA if c.get('id') == cluster_id), None)
    
    if cluster:
        db_manager.add_agent_log(
            'system', 
            'info', 
            f'❌ New slang cluster rejected: {cluster_name}',
            f'Cluster #{cluster_id} marked as false positive'
        )
    
    return jsonify({
        'success': True,
        'message': f'Slang cluster "{cluster_name}" rejected and will be ignored',
        'cluster_id': cluster_id
    })

@app.route('/api/slang/search', methods=['POST'])
@trace_function(name="api_slang_search")
def search_slang():
    """Search for similar slang patterns"""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    results = []
    
    for cluster in CLUSTER_DATA:
        matches = []
        if query.lower() in [k.lower() for k in cluster.get('keywords', [])]:
            matches.append('keyword match')
        
        for msg in cluster.get('messages', []):
            if query.lower() in msg.get('text', '').lower():
                matches.append('message match')
                break
        
        if matches:
            results.append({
                'cluster_id': cluster.get('id'),
                'name': cluster.get('name'),
                'type': cluster.get('type'),
                'confidence': cluster.get('confidence', 0.5),
                'matches': matches
            })
    
    return jsonify({
        'query': query,
        'results': results[:5]
    })

# ==============================================
# Main Execution
# ==============================================
# if __name__ == '__main__':
#     os.makedirs('templates', exist_ok=True)
#     os.makedirs('static/css', exist_ok=True)
    
#     print("\n📋 System Status:")
#     print("-" * 50)
    
#     try:
#         stats = db_manager.get_stats()
#         print(f"✅ Database: nexus_monitoring.db")
#         print(f"📊 Total alerts: {stats['total_alerts']}")
#         print(f"📈 High risk alerts: {stats['high_risk_alerts']}")
#     except Exception as e:
#         print(f"❌ Database error: {e}")
    
#     print("\n📁 Files Check:")
#     print("-" * 50)
    
#     if os.path.exists('telegram_agent.py'):
#         print("✅ telegram_agent.py exists")
#     else:
#         print("⚠️ telegram_agent.py will be created when needed")
    
#     cluster_file = Path('clusters.json')
#     if cluster_file.exists():
#         print(f"✅ clusters.json loaded with {len(CLUSTER_DATA)} clusters")
#     else:
#         print(f"⚠️ clusters.json not found - created empty file")
    
#     if os.path.exists('modules'):
#         print("✅ modules/ directory exists")
#         if os.path.exists('modules/telegram_client.py'):
#             print("✅ modules/telegram_client.py exists")
#         if os.path.exists('modules/ai_analyzer.py'):
#             print("✅ modules/ai_analyzer.py exists")
    
#     if langsmith_client:
#         print(f"✅ LangSmith: Enabled (Project: {LANGSMITH_PROJECT})")
#         print(f"🔗 Dashboard: https://smith.langchain.com/projects/{LANGSMITH_PROJECT}")
#     else:
#         print("⚠️ LangSmith: Disabled (Set LANGSMITH_API_KEY in .env to enable)")
    
#     print("\n" + "="*60)
#     print("🌐 Web Interface: http://localhost:5000")
#     print("📊 Dashboard: http://localhost:5000/dashboard")
#     print("🤖 Available Agents:")
#     print("   • Telegram: ✅ REAL MONITORING (AI-powered)")
#     print("   • Reddit: ⚠️ Simulation mode")
#     print("📝 Logging: Console + Database + File + LangSmith")
#     print("💾 Data Storage: SQLite (persistent)")
#     print("📊 Cluster Data: clusters.json (modular)")
#     print("="*60)

#     print("\n✅ System ready for REAL Telegram monitoring!")
#     print("📢 REAL AGENT ACTIVITY WILL BE DISPLAYED HERE:")
#     print("-" * 60 + "\n")
    
#     try:
#         app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
#     except KeyboardInterrupt:
#         print("\n👋 Shutting down all agents...")
#         for agent_id in ['telegram', 'reddit']:
#             agent_manager.stop_agent(agent_id)
#         print("✅ System shutdown complete")

# ==============================================
# For local development only
# ==============================================
if __name__ == '__main__':
    # This only runs when you execute python app.py directly
    # Gunicorn ignores this block
    print("\n⚠️ Running in development mode - use Gunicorn for production")
    print("To run with Gunicorn: gunicorn app:app\n")
    
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    
    print("\n📋 System Status:")
    print("-" * 50)
    
    try:
        stats = db_manager.get_stats()
        print(f"✅ Database: nexus_monitoring.db")
        print(f"📊 Total alerts: {stats['total_alerts']}")
        print(f"📈 High risk alerts: {stats['high_risk_alerts']}")
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    print("\n📁 Files Check:")
    print("-" * 50)
    
    if os.path.exists('telegram_agent.py'):
        print("✅ telegram_agent.py exists")
    else:
        print("⚠️ telegram_agent.py will be created when needed")
    
    cluster_file = Path('clusters.json')
    if cluster_file.exists():
        print(f"✅ clusters.json loaded with {len(CLUSTER_DATA)} clusters")
    else:
        print(f"⚠️ clusters.json not found - created empty file")
    
    if os.path.exists('modules'):
        print("✅ modules/ directory exists")
        if os.path.exists('modules/telegram_client.py'):
            print("✅ modules/telegram_client.py exists")
        if os.path.exists('modules/ai_analyzer.py'):
            print("✅ modules/ai_analyzer.py exists")
    
    if langsmith_client:
        print(f"✅ LangSmith: Enabled (Project: {LANGSMITH_PROJECT})")
        print(f"🔗 Dashboard: https://smith.langchain.com/projects/{LANGSMITH_PROJECT}")
    else:
        print("⚠️ LangSmith: Disabled (Set LANGSMITH_API_KEY in .env to enable)")
    
    print("\n" + "="*60)
    print("🌐 Web Interface: http://localhost:5000")
    print("📊 Dashboard: http://localhost:5000/dashboard")
    print("🤖 Available Agents:")
    print("   • Telegram: ✅ REAL MONITORING (AI-powered)")
    print("   • Reddit: ⚠️ Simulation mode")
    print("📝 Logging: Console + Database + File + LangSmith")
    print("💾 Data Storage: SQLite (persistent)")
    print("📊 Cluster Data: clusters.json (modular)")
    print("="*60)

    print("\n✅ System ready for REAL Telegram monitoring!")
    print("📢 REAL AGENT ACTIVITY WILL BE DISPLAYED HERE:")
    print("-" * 60 + "\n")
    
    # Start Flask development server (for local testing only)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)