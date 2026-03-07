"""
Web Dashboard - SIMPLIFIED VIEW-ONLY
"""
from flask import Flask, render_template, jsonify
import json
import asyncio

class Dashboard:
    """Web dashboard for monitoring"""
    
    def __init__(self, monitoring_system):
        self.system = monitoring_system
        self.app = Flask(__name__,
                        template_folder='../templates',
                        static_folder='../static')
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/stats')
        def get_stats():
            """Get system statistics"""
            try:
                with open('analysis_results.json', 'r') as f:
                    data = json.load(f)
            except:
                data = {'total_results': 0, 'high_risk': 0}
            
            return jsonify({
                'channels': len(self.system.monitored_channels),
                'total_alerts': data.get('total_results', 0),
                'high_risk_alerts': data.get('high_risk', 0),
                'system_status': 'active'
            })
        
        @self.app.route('/api/alerts')
        def get_alerts():
            """Get recent alerts"""
            try:
                with open('analysis_results.json', 'r') as f:
                    data = json.load(f)
                alerts = data.get('results', [])
            except:
                alerts = []
            
            return jsonify({'alerts': alerts[-10:]})
        
        @self.app.route('/api/channels')
        def get_channels():
            """Get monitored channels"""
            return jsonify({
                'channels': self.system.monitored_channels,
                'count': len(self.system.monitored_channels)
            })
    
    def run(self, host='0.0.0.0', port=5000):
        """Run the dashboard server"""
        print(f"🌐 Dashboard starting on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=False, use_reloader=False)