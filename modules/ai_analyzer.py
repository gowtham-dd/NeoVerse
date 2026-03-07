"""
AI Analyzer using Llama3 via Groq - BATCH VERSION with Token Management
"""
import os
import json
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

try:
    from groq import Groq
    from groq import RateLimitError, APIError
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logging.warning("Groq library not installed. AI analysis will be basic.")

class AIAnalyzer:
    """AI analysis for drug content detection - BATCH PROCESSING with token management"""
    
    def __init__(self):
        self.groq_client = None
        self.model = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
        self.max_tokens_per_minute = 6000  # Groq's limit for this model
        self.tokens_used_this_minute = 0
        self.last_reset_time = datetime.now()
        
        if GROQ_AVAILABLE and os.getenv('GROQ_API_KEY'):
            try:
                self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                logging.info(f"✅ Groq client initialized ({self.model})")
            except Exception as e:
                logging.error(f"Failed to initialize Groq: {e}")
                self.groq_client = None
        else:
            logging.warning("⚠️ Using basic keyword analysis (no Groq API)")
        
        # Cache to avoid duplicate analysis
        self.analyzed_cache = {}
        
        # Drug keywords for basic analysis
        self.drug_keywords = [
            'weed', 'marijuana', 'cocaine', 'heroin', 'meth', 'mdma',
            'ecstasy', 'lsd', 'acid', 'shrooms', 'xanax', 'oxy', 'adderall',
            'fentanyl', 'ketamine', 'dmt', 'pharma', 'pill', 'meds',
            'prescription', 'opioid', 'amphetamine', 'benzodiazepine', 'coke',
            'crystal', 'ice', 'tina', 'crank', 'speed', 'molly', 'beans'
        ]
        
        self.transaction_patterns = [
            'dm for', 'contact for', 'for sale', 'price', 'delivery',
            'available now', 'in stock', 'shipping', 'discreet',
            'cash only', 'bitcoin', 'crypto', 'escrow', 'plug', 'connect',
            'telegram', 'w/e', 'dd', 'btc', 'pgp', 'hmu', 'hit me up'
        ]
        
        # Token estimation (rough: 1 token ≈ 4 characters)
        self.CHARS_PER_TOKEN = 4
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a text"""
        return len(text) // self.CHARS_PER_TOKEN
    
    def _check_rate_limit(self, estimated_tokens: int) -> bool:
        """Check if we're within rate limits, reset counter if minute passed"""
        now = datetime.now()
        seconds_passed = (now - self.last_reset_time).total_seconds()
        
        # Reset counter if a minute has passed
        if seconds_passed >= 60:
            self.tokens_used_this_minute = 0
            self.last_reset_time = now
            logging.info(f"🔄 Rate limit counter reset after {seconds_passed:.1f} seconds")
        
        # Check if we have enough tokens
        if self.tokens_used_this_minute + estimated_tokens > self.max_tokens_per_minute:
            return False
        
        return True
    
    async def _wait_for_rate_limit(self, estimated_tokens: int, max_wait: int = 60) -> bool:
        """Wait until rate limit resets or we have enough tokens"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < max_wait:
            if self._check_rate_limit(estimated_tokens):
                return True
            # Wait and check again
            await asyncio.sleep(5)
            # Reset counter if needed (handled in _check_rate_limit)
        
        return False
    
    async def analyze_messages_batch(self, messages: List[Dict], channel: str = "") -> List[Dict]:
        """Analyze multiple messages in one batch with token management"""
        
        if not messages:
            return []
        
        print(f"🤖 Analyzing {len(messages)} messages from {channel}...")
        
        if self.groq_client:
            # Try batch analysis with Llama3
            batch_result = await self._analyze_batch_with_llama3(messages, channel)
            if batch_result:
                return batch_result
        
        # Fallback to individual keyword analysis
        return [self._analyze_with_keywords(msg, channel) for msg in messages]
    
    async def _analyze_batch_with_llama3(self, messages: List[Dict], channel: str) -> Optional[List[Dict]]:
        """Batch analyze messages with Llama3 and token management"""
        try:
            # Prepare batch data with token estimation
            messages_text = []
            total_estimated_tokens = 0
            
            # First, estimate total tokens
            for i, msg in enumerate(messages):
                text = msg.get('text', '')
                if text and len(text) > 10:
                    # Truncate based on token limits
                    max_chars = 200  # About 50 tokens per message
                    truncated_text = text[:max_chars]
                    
                    msg_data = {
                        'id': i,
                        'text': truncated_text
                    }
                    messages_text.append(msg_data)
                    
                    # Estimate tokens for this message + overhead
                    msg_tokens = self._estimate_tokens(truncated_text) + 20  # 20 tokens overhead
                    total_estimated_tokens += msg_tokens
            
            if not messages_text:
                return []
            
            # Add prompt overhead (system prompt + instructions)
            prompt_overhead = 500  # Approximate tokens for prompts
            total_estimated_tokens += prompt_overhead
            
            print(f"   📊 Estimated tokens: {total_estimated_tokens}")
            
            # Check rate limit
            if not self._check_rate_limit(total_estimated_tokens):
                print(f"   ⚠️ Rate limit would be exceeded ({total_estimated_tokens} tokens needed)")
                print(f"   ⏳ Waiting for rate limit reset...")
                
                # Wait for rate limit
                if not await self._wait_for_rate_limit(total_estimated_tokens):
                    print(f"   ❌ Rate limit wait timeout, using keyword analysis")
                    return None
                
                print(f"   ✅ Rate limit reset, proceeding with analysis")
            
            # Create prompt for batch analysis
            prompt = self._create_batch_prompt(messages_text, channel)
            
            # Call Groq API with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    completion = self.groq_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self._get_system_prompt()},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1500,  # Limit response size
                        response_format={"type": "json_object"}
                    )
                    
                    # Update token usage
                    if hasattr(completion, 'usage'):
                        self.tokens_used_this_minute += completion.usage.total_tokens
                        print(f"   💫 Token usage: +{completion.usage.total_tokens} (Total: {self.tokens_used_this_minute}/{self.max_tokens_per_minute})")
                    
                    response = completion.choices[0].message.content
                    
                    # Parse JSON response
                    try:
                        result = json.loads(response)
                        analyses = result.get('analyses', [])
                        
                        # Map analyses back to original messages
                        results = []
                        for i, msg in enumerate(messages[:len(analyses)]):
                            analysis = analyses[i] if i < len(analyses) else {}
                            
                            results.append({
                                'message_id': msg.get('id'),
                                'channel': channel,
                                'text': msg.get('text', '')[:200],
                                'date': msg.get('date', datetime.now().isoformat()),
                                'risk_level': analysis.get('risk_level', 'unknown'),
                                'confidence': float(analysis.get('confidence', 0)),
                                'indicators': analysis.get('indicators', []),
                                'summary': analysis.get('summary', 'No summary'),
                                'action': analysis.get('action', self._get_action(analysis.get('risk_level', 'low'))),
                                'ai_model': f'Llama3-Batch ({self.model})'
                            })
                        
                        print(f"   ✅ Batch analysis complete: {len(results)} messages analyzed")
                        return results
                        
                    except json.JSONDecodeError:
                        print(f"   ⚠️ Failed to parse JSON response (attempt {attempt + 1})")
                        if attempt == max_retries - 1:
                            return None
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        
                except Exception as e:
                    error_str = str(e).lower()
                    
                    if "rate_limit" in error_str or "429" in error_str:
                        wait_time = (2 ** attempt) * 10
                        print(f"   ⚠️ Rate limited, waiting {wait_time} seconds... (attempt {attempt + 1})")
                        await asyncio.sleep(wait_time)
                        
                        # Reset token counter on rate limit
                        self.tokens_used_this_minute = 0
                        self.last_reset_time = datetime.now()
                        
                    elif "413" in error_str or "too large" in error_str:
                        print(f"   ⚠️ Request too large, reducing batch size")
                        # Reduce batch size by half and retry
                        if len(messages) > 5:
                            half = len(messages) // 2
                            print(f"   🔄 Splitting into smaller batches ({half} messages each)")
                            
                            # Split into two batches
                            first_half = messages[:half]
                            second_half = messages[half:]
                            
                            results1 = await self._analyze_batch_with_llama3(first_half, channel)
                            results2 = await self._analyze_batch_with_llama3(second_half, channel)
                            
                            if results1 and results2:
                                return results1 + results2
                        return None
                        
                    else:
                        print(f"   ⚠️ API error: {e}")
                        if attempt == max_retries - 1:
                            return None
                        await asyncio.sleep(2 ** attempt)
            
            return None
                
        except Exception as e:
            print(f"   ❌ Batch analysis error: {e}")
            return None
    
    def _create_batch_prompt(self, messages: List[Dict], channel: str) -> str:
        """Create prompt for batch analysis - optimized for token usage"""
        messages_json = json.dumps(messages, indent=2)
        
        return f"""Analyze these {len(messages)} Telegram messages for drug trafficking.

CHANNEL: {channel}
MESSAGES: {messages_json}

For EACH message, return:
- risk_level: "high"/"medium"/"low"/"safe"
- confidence: 0.0-1.0
- indicators: list of found terms
- summary: 10 words max

Return ONLY JSON:
{{"analyses": [{{"risk_level":"high","confidence":0.9,"indicators":["cocaine"],"summary":"Drug sale detected"}}]}}"""
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for drug detection - optimized"""
        return """You detect drug trafficking in Telegram messages.

KEY INDICATORS:
1. Drug names: cocaine, heroin, meth, MDMA, weed, xanax, fentanyl
2. Coded terms: snow, candy, bars, gear, work
3. Transaction: "for sale", "dm me", "price", "delivery"
4. Payment: bitcoin, cash, crypto
5. Safety: discreet, secure

CLASSIFY:
- HIGH: Drug names + transaction terms
- MEDIUM: Drug names OR transaction terms
- LOW: Suspicious but unclear
- SAFE: No indicators

Be accurate. False positive > missing real trafficking."""
    
    def _analyze_with_keywords(self, message: Dict, channel: str) -> Dict:
        """Basic keyword analysis for a single message"""
        text = message.get('text', '').lower()
        
        # Check for keywords
        found_drugs = [kw for kw in self.drug_keywords if kw in text]
        found_patterns = [p for p in self.transaction_patterns if p in text]
        
        # Check for payment methods
        payment_terms = ['bitcoin', 'crypto', 'cash', 'paypal', 'venmo', 'btc']
        found_payments = [p for p in payment_terms if p in text]
        
        # Calculate risk score
        risk_score = (
            len(found_drugs) * 3 +
            len(found_patterns) * 2 +
            len(found_payments) * 1
        )
        
        # Determine risk level and confidence
        if risk_score >= 5:
            risk_level = 'high'
            confidence = 0.8
        elif risk_score >= 2:
            risk_level = 'medium'
            confidence = 0.6
        elif risk_score >= 1:
            risk_level = 'low'
            confidence = 0.3
        else:
            risk_level = 'safe'
            confidence = 0.1
        
        # Create indicators list
        indicators = []
        if found_drugs:
            indicators.append(f"drugs: {', '.join(found_drugs[:3])}")
        if found_patterns:
            indicators.append(f"transactions: {', '.join(found_patterns[:3])}")
        if found_payments:
            indicators.append(f"payments: {', '.join(found_payments[:3])}")
        
        # Create summary
        if risk_level == 'high':
            summary = f"🚨 High risk: {len(found_drugs)} drug terms, {len(found_patterns)} transaction patterns"
        elif risk_level == 'medium':
            summary = f"⚠️ Medium risk: {len(found_drugs)} drug terms, {len(found_patterns)} transaction patterns"
        elif risk_level == 'low':
            summary = f"👀 Low risk: Suspicious indicators found"
        else:
            summary = f"✅ Safe: No drug indicators"
        
        return {
            'message_id': message.get('id'),
            'channel': channel,
            'text': message.get('text', '')[:200],
            'date': message.get('date', datetime.now().isoformat()),
            'risk_level': risk_level,
            'confidence': confidence,
            'indicators': indicators,
            'summary': summary,
            'action': self._get_action(risk_level),
            'ai_model': 'Keyword Analysis'
        }
    
    def _get_action(self, risk_level: str) -> str:
        """Get recommended action"""
        actions = {
            'high': '🚨 IMMEDIATE REVIEW - High probability of drug trafficking',
            'medium': '⚠️ MONITOR CLOSELY - Suspicious activity detected',
            'low': '👀 KEEP WATCH - Some suspicious indicators',
            'safe': '✅ ROUTINE MONITORING - No significant risk'
        }
        return actions.get(risk_level, 'No action required')
    
    async def analyze_single_message(self, text: str, channel: str = "") -> Dict:
        """Analyze single message (for API)"""
        message = {'text': text, 'id': 'single', 'date': datetime.now().isoformat()}
        results = await self.analyze_messages_batch([message], channel)
        return results[0] if results else self._analyze_with_keywords(message, channel)