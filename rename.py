# Upload IDDIG.json → Pinecone illegaltrade index using local embeddings

import json
import os
from dotenv import load_dotenv
from datetime import datetime
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# =============================================
# Load Environment Variables
# =============================================
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# =============================================
# Initialize Pinecone
# =============================================
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("illegaltrade")

print("✅ Connected to Pinecone index: illegaltrade")

# =============================================
# Load Dataset
# =============================================
with open("data/IDDIG.json", "r", encoding="utf-8") as f:
    iddig_data = json.load(f)

texts = iddig_data["IDDIG_Extracted_Code"]

print(f"📂 Loaded {len(texts)} IDDIG codes")

# =============================================
# Load Embedding Model (384-dim)
# =============================================
print("⚡ Loading embedding model...")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

print("✅ Model loaded")

# =============================================
# Upload Vectors
# =============================================
vectors = []
batch_size = 100

for i, text in enumerate(texts):

    print(f"🔎 Embedding {i+1}/{len(texts)}")

    embedding = model.encode(text).tolist()

    vectors.append({
        "id": f"iddig_{i:05d}",
        "values": embedding,
        "metadata": {
            "text": text,
            "type": "drug_code",
            "source": "iddig_seed",
            "timestamp": datetime.now().isoformat()
        }
    })

    # Batch Upload
    if (i + 1) % batch_size == 0:

        index.upsert(
            vectors=vectors,
            namespace="iddig_seed"
        )

        print(f"✅ Uploaded batch {(i+1)//batch_size} ({len(vectors)} vectors)")

        vectors = []

# Upload Remaining
if vectors:

    index.upsert(
        vectors=vectors,
        namespace="iddig_seed"
    )

    print(f"✅ Final batch uploaded ({len(vectors)} vectors)")

# =============================================
# Show Pinecone Stats
# =============================================
stats = index.describe_index_stats()

print("\n🎉 Upload Complete!")
print("📊 Pinecone Index Stats:")
print(stats)