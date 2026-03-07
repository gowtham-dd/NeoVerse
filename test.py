#!/usr/bin/env python3
"""
Test batch analysis
"""
import asyncio
import json
from modules.ai_analyzer import AIAnalyzer

async def test():
    """Test batch analysis"""
    analyzer = AIAnalyzer()
    
    # Create test messages
    test_messages = [
        {"id": 1, "text": " High quality cocaine available. DM for prices. Discreet shipping worldwide. Bitcoin accepted."},
        {"id": 2, "text": "Looking for party supplies? We have MDMA, ecstasy, and more. Contact @dealer for menu"},
        {"id": 3, "text": "Xanax bars and oxy available. Next day delivery. Cash or crypto."},
        {"id": 4, "text": "Just had a great dinner with friends! #m.d.m.a"},
        {"id": 5, "text": "Anyone know where to find some green in the city?"},
        {"id": 6, "text": "New movie coming out this weekend!"},
        {"id": 7, "text": "Contact me for snow delivery. Pure quality guaranteed."},
        {"id": 8, "text": "Gardening supplies available. DM for info about our special green"},
        {"id": 9, "text": "Check out my new blog about technology!"},
        {"id": 10, "text": " Fire strain available. DM for prices and delivery"}
    ]
    
    print(" Testing batch analysis...")
    print(f"Testing {len(test_messages)} messages")
    
    # Test batch analysis
    results = await analyzer.analyze_messages_batch(test_messages, "test_channel")
    
    print(f"\n Analysis complete!")
    print(f"Results: {len(results)}")
    
    # Show summary
    high_risk = [r for r in results if r['risk_level'] == 'high']
    medium_risk = [r for r in results if r['risk_level'] == 'medium']
    low_risk = [r for r in results if r['risk_level'] == 'low']
    
    print(f"\n Risk Distribution:")
    print(f"  HIGH RISK: {len(high_risk)} messages")
    print(f"  MEDIUM RISK: {len(medium_risk)} messages")
    print(f"  LOW RISK: {len(low_risk)} messages")
    
    # Show high risk examples
    if high_risk:
        print(f"\n🚨 HIGH RISK EXAMPLES:")
        for result in high_risk[:2]:
            print(f"  Message: {result['text'][:60]}...")
            print(f"  Risk: {result['risk_level']} ({result['confidence']*100:.0f}%)")
            print(f"  Indicators: {', '.join(result['indicators'])}")
            print(f"  Action: {result['action']}")
            print()
    
    # Save to file
    with open('batch_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f" Results saved to batch_test_results.json")

if __name__ == "__main__":
    asyncio.run(test())