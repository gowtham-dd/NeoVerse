// ==============================================
// Alert Center Configuration Data
// ==============================================

window.ALERT_CONFIG = {
    // Available sources (removed Facebook)
    sources: ['telegram', 'reddit'],
    
    // Risk levels
    riskLevels: ['high', 'medium', 'low'],
    
    // Channel data by source
    channels: {
        telegram: [
            '@darkmarket', 
            '@drugtalk', 
            '@pharma_connect', 
            '@underground', 
            '@private_channel',
            '@blackmarket',
            '@cryptotalk',
            '@darkweb_updates'
        ],
        reddit: [
            'r/darknet', 
            'r/drugs', 
            'r/RCsources', 
            'r/researchchemicals', 
            'r/DNMBusts',
            'r/Opioids',
            'r/Stims',
            'r/benzodiazepines'
        ]
    },
    
    // Sample messages for testing
    messages: [
        'Looking for bulk cocaine delivery. Contact @dealer123 for prices.',
        'Xanax bars available, shipping worldwide. Discreet packaging.',
        'Discussion about Bitcoin payments for special deliveries.',
        'Pure MDMA crystals, wholesale prices. Telegram: @crystal_king',
        'New batch of white heroin, 90% purity. Sample available.',
        'Looking for connects in Mumbai. Need quality powder.',
        'Fentanyl patches for sale, pharmaceutical grade.',
        'Weed delivery service now operating in your area.',
        'Need help finding LSD sheets in bulk.',
        'Oxycodone 30mg, genuine Pharma. Bulk discount.',
        'Encrypted chat: PGP key in bio for secure comms.',
        'Escrow available for large orders. BTC only.',
        'New vendor on the scene, cheap prices for first 10 customers.',
        'Telegram channel with daily updates on product availability.',
        'Darknet market links and mirror sites working.'
    ],
    
    // Sample statistics
    sampleStats: {
        totalAlerts: 132,
        highRiskAlerts: 21,
        mediumRiskAlerts: 58,
        lowRiskAlerts: 53
    }
};

// ==============================================
// Blockchain Evidence Data
// ==============================================

window.EVIDENCE_DATA = {
    1: {
        hash: '0x7d8f3a2b1c9e5f4a8d3c2b1a9f8e7d6c5b4a3f2e1d',
        timestamp: '2024-03-10 14:23:45',
        verified: true,
        blockNumber: 18456321,
        transactionId: '0x3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b'
    },
    2: {
        hash: '0x3e4a5f6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f',
        timestamp: '2024-03-09 22:15:30',
        verified: true,
        blockNumber: 18455892,
        transactionId: '0x8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e'
    },
    3: {
        hash: '0xa1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0',
        timestamp: '2024-03-08 19:42:15',
        verified: true,
        blockNumber: 18455423,
        transactionId: '0x1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b'
    },
    4: {
        hash: '0x9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9',
        timestamp: '2024-03-07 11:30:22',
        verified: true,
        blockNumber: 18454987,
        transactionId: '0x0f1e2d3c4b5a6f7e8d9c0b1a2f3e4d5c6b7a8f9e'
    },
    5: {
        hash: '0x8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b',
        timestamp: '2024-03-06 16:20:45',
        verified: true,
        blockNumber: 18454532,
        transactionId: '0x2f3e4d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0f1e'
    },
    6: {
        hash: '0x5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e',
        timestamp: '2024-03-05 23:15:10',
        verified: true,
        blockNumber: 18454098,
        transactionId: '0x6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d'
    },
    7: {
        hash: '0x2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d',
        timestamp: '2024-03-04 20:08:33',
        verified: true,
        blockNumber: 18453654,
        transactionId: '0x9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f'
    },
    8: {
        hash: '0x4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b',
        timestamp: '2024-03-03 14:50:27',
        verified: true,
        blockNumber: 18453210,
        transactionId: '0xb0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9'
    },
    9: {
        hash: '0x3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a',
        timestamp: '2024-03-02 09:15:42',
        verified: true,
        blockNumber: 18452786,
        transactionId: '0xd2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1'
    },
    10: {
        hash: '0x6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e7d',
        timestamp: '2024-03-01 22:30:18',
        verified: true,
        blockNumber: 18452342,
        transactionId: '0xe4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3'
    }
};

// ==============================================
// Evidence Generator Function
// ==============================================

window.generateEvidenceHash = function(alertId, timestamp) {
    const baseString = `${alertId}-${timestamp}-nexusai-blockchain`;
    let hash = '0x';
    for (let i = 0; i < 32; i++) {
        hash += Math.floor(Math.random() * 16).toString(16);
    }
    return hash;
};