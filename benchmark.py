# benchmark.py
import time
from src.agents.deduplication import deduplicate_news
from src.agents.entity_extraction import extract_entities
from src.agents.impact_analysis import analyze_impact

def run_benchmarks():
    print("🚀 Running FinPulse Benchmarks...\n")
    
    # 1. Test Deduplication Accuracy
    print("--- Testing Deduplication ---")
    # We use the known duplicate pair from our mock data
    art_A = {"title": "RBI raises repo rate by 25bps to 6.75%, citing inflation concerns", "content": "The Reserve Bank of India (RBI) has increased the repo rate by 25 basis points to 6.75%.", "source": "Reuters", "article_id": "test-1"}
    art_B = {"title": "Central bank hikes interest rates in surprise move", "content": "In a bid to control rising prices, the RBI raised its key lending rate by 25 basis points to 6.75%.", "source": "CNBC", "article_id": "test-2"}
    
    # Process first article to put it in ChromaDB
    deduplicate_news(art_A)
    
    # Process second article (Should be caught as duplicate)
    start_time = time.time()
    res_B = deduplicate_news(art_B)
    dedup_time = time.time() - start_time
    
    if res_B['is_duplicate']:
        print(f"✅ SUCCESS: Semantic duplicate detected in {dedup_time:.2f} seconds.")
    else:
        print("❌ FAILED: Duplicate not detected.")

    # 2. Test Entity Extraction & Latency
    print("\n--- Testing Entity Extraction ---")
    start_time = time.time()
    extracted = extract_entities(art_A)
    extraction_time = time.time() - start_time
    
    print(f"Extracted Regulators: {extracted.get('regulators')}")
    print(f"Extraction Latency: {extraction_time:.2f} seconds")
    
    # 3. Test Impact Mapping
    print("\n--- Testing Impact Mapping ---")
    analyzed = analyze_impact(extracted)
    print(f"Mapped Stocks: {analyzed.get('impacted_stocks')}")
    
    print("\n✅ Benchmarks Complete.")

if __name__ == "__main__":
    run_benchmarks()