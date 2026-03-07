let riskChart;

async function loadData() {
    try {
        // Load stats
        const statsResponse = await fetch('/api/stats');
        const stats = await statsResponse.json();
        
        document.getElementById('channelCount').textContent = stats.total_channels || '0';
        document.getElementById('messageCount').textContent = stats.messages_analyzed || '0';
        document.getElementById('highRiskCount').textContent = stats.high_risk_messages || '0';
        
        // Check for alerts
        if (stats.high_risk_messages > 0) {
            document.getElementById('alertBanner').style.display = 'block';
            document.getElementById('alertText').textContent = 
                `Found ${stats.high_risk_messages} high-risk messages`;
        }
        
        // Load messages
        const messagesResponse = await fetch('/api/messages');
        const messagesData = await messagesResponse.json();
        displayMessages(messagesData.messages || []);
        
        // Update chart
        updateChart(messagesData.messages || []);
        
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

function displayMessages(messages) {
    const container = document.getElementById('messagesList');
    
    if (!messages || messages.length === 0) {
        container.innerHTML = '<div class="loading">No messages found</div>';
        return;
    }
    
    let html = '';
    
    // Sort by risk (high first)
    messages.sort((a, b) => {
        const riskOrder = {high: 3, medium: 2, low: 1};
        return (riskOrder[b.metadata?.risk_level] || 0) - (riskOrder[a.metadata?.risk_level] || 0);
    });
    
    messages.slice(0, 20).forEach(msg => {
        const riskLevel = msg.metadata?.risk_level || 'low';
        const confidence = parseFloat(msg.metadata?.confidence || 0) * 100;
        
        html += `
            <div class="message-item ${riskLevel}-risk">
                <div class="message-channel">
                    ${msg.channel || 'Unknown'}
                    <span class="risk-badge risk-${riskLevel}">
                        ${riskLevel.toUpperCase()} (${confidence.toFixed(0)}%)
                    </span>
                </div>
                <div class="message-text">${escapeHtml(msg.text || '')}</div>
                <div class="message-meta">
                    <span>${msg.metadata?.analyzed_at ? new Date(msg.metadata.analyzed_at).toLocaleString() : ''}</span>
                    <span>Action: ${msg.metadata?.recommended_action || 'none'}</span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function updateChart(messages) {
    const ctx = document.getElementById('riskChart').getContext('2d');
    
    // Count messages by risk level
    const counts = {high: 0, medium: 0, low: 0};
    messages.forEach(msg => {
        const risk = msg.metadata?.risk_level || 'low';
        counts[risk] = (counts[risk] || 0) + 1;
    });
    
    if (riskChart) {
        riskChart.destroy();
    }
    
    riskChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High Risk', 'Medium Risk', 'Low Risk'],
            datasets: [{
                data: [counts.high, counts.medium, counts.low],
                backgroundColor: [
                    '#ff4444',
                    '#ffbb33',
                    '#00C851'
                ],
                borderWidth: 2,
                borderColor: '#1a1a2e'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e0e0e0',
                        font: {
                            size: 14
                        }
                    }
                },
                title: {
                    display: true,
                    text: 'Risk Distribution',
                    color: '#e0e0e0',
                    font: {
                        size: 16
                    }
                }
            }
        }
    });
}

async function searchMessages() {
    const query = document.getElementById('searchInput').value;
    if (!query.trim()) return;
    
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        displayMessages(data.results || []);
    } catch (error) {
        console.error('Search failed:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-refresh every 30 seconds
setInterval(loadData, 30000);

// Initial load
document.addEventListener('DOMContentLoaded', loadData);