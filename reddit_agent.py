"""
Reddit Agent for Drug Content Monitoring
Uses PRAW for Reddit API, Sentence Transformers for embeddings, and Llama3 for classification
"""

import os
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Third-party imports
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    logging.warning("PRAW library not installed. Install with: pip install praw")

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("SentenceTransformers not installed. Install with: pip install sentence-transformers")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logging.warning("Groq library not installed. Install with: pip install groq")


class RedditAgent:
    """Reddit Agent for monitoring drug-related content"""
    
    def __init__(self):
        self.reddit_client = None
        self.embedding_model = None
        self.groq_client = None
        self.is_authenticated = False
        
        # Drug-related search terms and hashtags
        self.drug_search_terms = [
            '#cocaine', '#heroin', '#weed', '#marijuana', '#meth', '#mdma',
            '#ecstasy', '#lsd', '#xanax', '#oxy', '#fentanyl', '#drugs',
            '#pharma', '#opioids', '#psychedelics', '#dealers', '#vendors'
        ]
        
        # Drug-related keywords for similarity matching
        self.drug_keywords = [
            'cocaine', 'heroin', 'weed', 'marijuana', 'cannabis', 'meth',
            'methamphetamine', 'mdma', 'ecstasy', 'lsd', 'acid', 'shrooms',
            'mushrooms', 'xanax', 'alprazolam', 'oxy', 'oxycodone', 'fentanyl',
            'adderall', 'ketamine', 'dmt', 'pharma', 'pill', 'opioid',
            'amphetamine', 'benzodiazepine', 'tramadol', 'codeine', 'morphine'
        ]
        
        # Transaction/selling patterns
        self.transaction_patterns = [
            'for sale', 'selling', 'price', 'cost', '$$', 'shipping',
            'delivery', 'available', 'in stock', 'dm', 'pm', 'contact',
            'message me', 'secure', 'discreet', 'escrow', 'bitcoin',
            'crypto', 'payment', 'cash', 'venmo', 'paypal'
        ]
        
        # Initialize components
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Reddit, embedding model, and Groq clients"""
        
        # Initialize Reddit client
        if PRAW_AVAILABLE:
            try:
                self.reddit_client = praw.Reddit(
                    client_id=os.getenv('REDDIT_CLIENT_ID', ''),
                    client_secret=os.getenv('REDDIT_CLIENT_SECRET', ''),
                    user_agent=os.getenv('REDDIT_USER_AGENT', 'DrugMonitoringAgent/1.0'),
                    username=os.getenv('REDDIT_USERNAME', ''),
                    password=os.getenv('REDDIT_PASSWORD', '')
                )
                print("✅ Reddit client initialized")
            except Exception as e:
                print(f"❌ Failed to initialize Reddit client: {e}")
                self.reddit_client = None
        else:
            print("⚠️  PRAW not available. Install with: pip install praw")
        
        # Initialize Sentence Transformer model
        if TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✅ Sentence Transformer model loaded")
            except Exception as e:
                print(f"❌ Failed to load embedding model: {e}")
                self.embedding_model = None
        else:
            print("⚠️  SentenceTransformers not available. Install with: pip install sentence-transformers")
        
        # Initialize Groq client for Llama3
        if GROQ_AVAILABLE and os.getenv('GROQ_API_KEY'):
            try:
                self.groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
                print("✅ Groq client initialized for Llama3")
            except Exception as e:
                print(f"❌ Failed to initialize Groq client: {e}")
                self.groq_client = None
        else:
            print("⚠️  Groq API key not found or library not installed")
    
    async def authenticate(self):
        """Authenticate with Reddit"""
        if not self.reddit_client:
            print("❌ Reddit client not initialized")
            return False
        
        try:
            # Test authentication
            user = self.reddit_client.user.me()
            print(f"✅ Authenticated as Reddit user: {user.name}")
            self.is_authenticated = True
            return True
        except Exception as e:
            print(f"❌ Reddit authentication failed: {e}")
            print("\n💡 Please check your Reddit credentials in .env file:")
            print("   REDDIT_CLIENT_ID=your_client_id")
            print("   REDDIT_CLIENT_SECRET=your_client_secret")
            print("   REDDIT_USERNAME=your_username")
            print("   REDDIT_PASSWORD=your_password")
            print("   REDDIT_USER_AGENT=your_app_name/1.0")
            return False
    
    async def search_drug_content(self, limit_posts=10, limit_comments=10):
        """
        Search for drug-related content on Reddit
        Returns list of posts with analyzed content
        """
        if not self.is_authenticated:
            print("❌ Not authenticated. Please authenticate first.")
            return []
        
        print(f"\n🔍 Searching for drug-related content on Reddit...")
        print(f"   Posts to fetch: {limit_posts}")
        print(f"   Comments per post: {limit_comments}")
        
        all_posts_data = []
        
        try:
            # Search in multiple drug-related subreddits
            subreddits = ['drugs', 'DarkNetMarkets', 'psychedelics', 'trees', 'opiates']
            
            for subreddit_name in subreddits:
                print(f"\n📋 Checking r/{subreddit_name}...")
                
                try:
                    subreddit = self.reddit_client.subreddit(subreddit_name)
                    
                    # Get new posts
                    for post in subreddit.new(limit=limit_posts):
                        post_data = await self._analyze_post(post, limit_comments)
                        if post_data:
                            all_posts_data.append(post_data)
                            
                            # Print progress
                            print(f"   ✓ Analyzed: {post.title[:60]}...")
                
                except Exception as e:
                    print(f"   ⚠️  Error accessing r/{subreddit_name}: {e}")
                    continue
            
            # Also search by keywords
            print(f"\n🔎 Searching by drug keywords...")
            for keyword in self.drug_keywords[:5]:  # Limit to 5 keywords to avoid rate limits
                try:
                    search_results = self.reddit_client.subreddit('all').search(
                        keyword, 
                        limit=5,  # 5 posts per keyword
                        sort='new'
                    )
                    
                    for post in search_results:
                        # Avoid duplicates
                        if not any(p['post_id'] == post.id for p in all_posts_data):
                            post_data = await self._analyze_post(post, limit_comments)
                            if post_data:
                                all_posts_data.append(post_data)
                                print(f"   ✓ Found via '{keyword}': {post.title[:50]}...")
                
                except Exception as e:
                    print(f"   ⚠️  Error searching for '{keyword}': {e}")
                    continue
            
            print(f"\n✅ Total posts analyzed: {len(all_posts_data)}")
            return all_posts_data
            
        except Exception as e:
            print(f"❌ Error during Reddit search: {e}")
            return []
    
    async def _analyze_post(self, post, limit_comments=10):
        """Analyze a single Reddit post"""
        try:
            # Extract post content
            post_content = f"{post.title}\n\n{post.selftext}"
            
            # Get top comments
            comments = []
            post.comments.replace_more(limit=0)  # Remove "load more comments"
            
            for i, comment in enumerate(post.comments[:limit_comments]):
                if hasattr(comment, 'body'):
                    comments.append(comment.body)
                    if i >= limit_comments - 1:
                        break
            
            # Combine all text for analysis
            all_text = [post_content] + comments
            
            # Calculate embeddings and similarity
            similarity_scores = await self._calculate_similarity(all_text)
            
            # Prepare data for AI analysis
            post_data = {
                'post_id': post.id,
                'subreddit': str(post.subreddit),
                'title': post.title,
                'author': str(post.author),
                'created_utc': post.created_utc,
                'score': post.score,
                'num_comments': post.num_comments,
                'url': post.url,
                'post_content': post_content[:1000],  # Limit length
                'comments': comments[:5],  # Keep only first 5 comments for display
                'all_comments_count': len(comments),
                'similarity_scores': similarity_scores,
                'avg_similarity': np.mean(similarity_scores) if similarity_scores else 0,
                'has_high_similarity': any(score > 0.7 for score in similarity_scores) if similarity_scores else False
            }
            
            return post_data
            
        except Exception as e:
            print(f"⚠️  Error analyzing post {post.id}: {e}")
            return None
    
    async def _calculate_similarity(self, texts: List[str]) -> List[float]:
        """Calculate cosine similarity between texts and drug keywords"""
        if not self.embedding_model or not texts:
            return []
        
        try:
            # Create embeddings for input texts
            text_embeddings = self.embedding_model.encode(texts)
            
            # Create embeddings for drug keywords
            keyword_embeddings = self.embedding_model.encode(self.drug_keywords)
            
            # Calculate cosine similarity
            similarity_matrix = cosine_similarity(text_embeddings, keyword_embeddings)
            
            # Get maximum similarity for each text
            max_similarities = np.max(similarity_matrix, axis=1)
            
            return max_similarities.tolist()
            
        except Exception as e:
            print(f"⚠️  Error in similarity calculation: {e}")
            return []
    
    async def analyze_with_llama3(self, post_data: Dict) -> Dict:
        """Analyze post data using Llama3 via Groq"""
        if not self.groq_client:
            print("⚠️  Groq client not available. Skipping AI analysis.")
            return {
                'risk_level': 'unknown',
                'confidence': 0.0,
                'indicators': [],
                'summary': 'AI analysis unavailable',
                'action': 'Check Groq API configuration'
            }
        
        try:
            # Prepare prompt for Llama3
            prompt = self._create_llama3_prompt(post_data)
            
            # Call Groq API
            completion = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system", 
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            response = completion.choices[0].message.content
            
            # Parse JSON response
            try:
                result = json.loads(response)
                return result
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    'risk_level': 'medium',
                    'confidence': 0.5,
                    'indicators': ['AI analysis completed'],
                    'summary': 'Content analyzed with AI',
                    'action': 'Review manually'
                }
                
        except Exception as e:
            print(f"⚠️  Error in Llama3 analysis: {e}")
            return {
                'risk_level': 'error',
                'confidence': 0.0,
                'indicators': ['Analysis failed'],
                'summary': f'Analysis error: {str(e)}',
                'action': 'Check AI service'
            }
    
    def _create_llama3_prompt(self, post_data: Dict) -> str:
        """Create prompt for Llama3 analysis"""
        
        # Format comments for prompt
        comments_text = "\n".join([
            f"Comment {i+1}: {comment[:200]}..."
            for i, comment in enumerate(post_data.get('comments', [])[:3])
        ])
        
        prompt = f"""
        Analyze this Reddit post for drug trafficking or drug-related activity:
        
        SUBREDDIT: r/{post_data.get('subreddit', 'unknown')}
        TITLE: {post_data.get('title', 'No title')}
        AUTHOR: {post_data.get('author', 'Unknown')}
        POST CONTENT: {post_data.get('post_content', 'No content')[:500]}
        
        COMMENTS:
        {comments_text}
        
        SIMILARITY ANALYSIS:
        - Average similarity to drug keywords: {post_data.get('avg_similarity', 0):.2f}
        - Has high similarity: {post_data.get('has_high_similarity', False)}
        
        Analyze for:
        1. Direct drug mentions or coded language
        2. Transaction/selling indicators
        3. Sourcing or vendor discussions
        4. Payment method discussions
        5. Safety/discretion discussions
        
        Return a JSON object with this exact structure:
        {{
            "risk_level": "high", "medium", "low", or "safe",
            "confidence": 0.0 to 1.0,
            "indicators": ["list", "of", "found", "indicators"],
            "summary": "Brief summary (20 words max)",
            "action": "Recommended action"
        }}
        
        Be conservative. False positives are better than missing real drug trafficking.
        """
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """System prompt for drug detection"""
        return """You are an expert drug trafficking detection system specializing in Reddit content analysis. 
        
        You analyze Reddit posts and comments for signs of drug-related activity including:
        
        1. DIRECT DRUG MENTIONS: cocaine, heroin, meth, MDMA, weed, marijuana, opioids, etc.
        2. CODED LANGUAGE: "snow", "candy", "bars", "green", "fire", "work", "pack", "gear", "clear"
        3. TRANSACTION INDICATORS: "for sale", "selling", "price", "$$", "shipping", "delivery"
        4. SOURCING: "looking for", "need connect", "reliable vendor", "trusted source"
        5. PAYMENT: "bitcoin", "crypto", "cashapp", "venmo", "paypal", "escrow"
        6. SAFETY: "discreet", "secure", "stealth", "no tracking"
        
        Risk Classification:
        - HIGH: Direct drug names + transaction terms OR sourcing requests + payment methods
        - MEDIUM: Drug mentions OR transaction discussions without clear intent
        - LOW: Casual drug discussions without commercial intent
        - SAFE: No drug-related indicators
        
        Focus on commercial intent and potential harm."""
    
    async def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        print("\n" + "="*60)
        print("🚀 REDDIT AGENT STARTING MONITORING CYCLE")
        print("="*60)
        
        # Step 1: Authenticate
        print("\n1️⃣ AUTHENTICATION")
        auth_success = await self.authenticate()
        if not auth_success:
            print("❌ Authentication failed. Exiting.")
            return
        
        # Step 2: Search for content
        print("\n2️⃣ CONTENT SEARCH")
        posts_data = await self.search_drug_content(limit_posts=10, limit_comments=10)
        
        if not posts_data:
            print("ℹ️  No posts found or analyzed.")
            return
        
        # Step 3: Analyze with AI
        print("\n3️⃣ AI ANALYSIS WITH LLAMA3")
        print("-" * 40)
        
        high_risk_count = 0
        medium_risk_count = 0
        
        for i, post_data in enumerate(posts_data):
            print(f"\n📊 POST {i+1}/{len(posts_data)}")
            print(f"   Subreddit: r/{post_data['subreddit']}")
            print(f"   Title: {post_data['title'][:80]}...")
            print(f"   Similarity Score: {post_data['avg_similarity']:.2f}")
            
            # Only analyze posts with significant similarity or manually review all
            if post_data['avg_similarity'] > 0.3 or post_data['has_high_similarity']:
                print("   🤖 Sending to Llama3 for analysis...")
                
                ai_result = await self.analyze_with_llama3(post_data)
                
                # Update post data with AI results
                post_data['ai_analysis'] = ai_result
                
                # Print results
                risk_level = ai_result.get('risk_level', 'unknown')
                confidence = ai_result.get('confidence', 0)
                summary = ai_result.get('summary', 'No summary')
                
                risk_color = {
                    'high': '🔴',
                    'medium': '🟡', 
                    'low': '🟢',
                    'safe': '⚪'
                }.get(risk_level, '⚫')
                
                print(f"   {risk_color} Risk: {risk_level.upper()}")
                print(f"   📈 Confidence: {confidence:.2f}")
                print(f"   📝 Summary: {summary}")
                
                if risk_level == 'high':
                    high_risk_count += 1
                    print(f"   🚨 HIGH RISK DETECTED!")
                    print(f"   Action: {ai_result.get('action', 'No action specified')}")
                elif risk_level == 'medium':
                    medium_risk_count += 1
                
                # Print indicators if any
                indicators = ai_result.get('indicators', [])
                if indicators:
                    print(f"   🔍 Indicators: {', '.join(indicators[:3])}")
            
            else:
                print("   ⚪ Low similarity, skipping AI analysis")
        
        # Step 4: Summary
        print("\n" + "="*60)
        print("📋 MONITORING CYCLE COMPLETE")
        print("="*60)
        print(f"📊 Posts analyzed: {len(posts_data)}")
        print(f"🔴 High risk posts: {high_risk_count}")
        print(f"🟡 Medium risk posts: {medium_risk_count}")
        print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Save results to file
        await self._save_results(posts_data)
        
        return posts_data
    
    async def _save_results(self, posts_data):
        """Save analysis results to JSON file"""
        try:
            results = {
                'timestamp': datetime.now().isoformat(),
                'total_posts': len(posts_data),
                'high_risk_count': sum(1 for p in posts_data 
                                     if p.get('ai_analysis', {}).get('risk_level') == 'high'),
                'medium_risk_count': sum(1 for p in posts_data 
                                       if p.get('ai_analysis', {}).get('risk_level') == 'medium'),
                'posts': posts_data
            }
            
            filename = f"reddit_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)
            
            print(f"💾 Results saved to: {filename}")
            
        except Exception as e:
            print(f"⚠️  Error saving results: {e}")


async def main():
    """Main function to run the Reddit agent"""
    print("🚀 Initializing Reddit Drug Monitoring Agent...")
    
    # Create agent instance
    agent = RedditAgent()
    
    # Run monitoring cycle
    await agent.run_monitoring_cycle()


if __name__ == "__main__":
    # Run the agent
    asyncio.run(main())