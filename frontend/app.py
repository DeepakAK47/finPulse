# frontend/app.py
import streamlit as st
import requests

# Configure the page
st.set_page_config(page_title="FinPulse AI", page_icon="📈", layout="wide")

st.title("📈 FinPulse: AI Financial News Intelligence")
st.markdown("Ask questions about the latest market news, companies, or sectors.")

# Create the input box
query = st.text_input("Enter your query:", placeholder="e.g., HDFC Bank news, RBI policy changes, Banking sector update")

if st.button("Analyze"):
    if query:
        with st.spinner("Analyzing news and extracting intelligence..."):
            try:
                # Call your FastAPI backend
                response = requests.post(
                    "http://127.0.0.1:8000/query",
                    json={"query": query}
                )
                response.raise_for_status()
                data = response.json()
                
                # Display the query classification
                st.success(f"Query Intent Detected: **{data.get('query_type', 'Unknown').capitalize()}**")
                
                results = data.get("results", [])
                
                if not results:
                    st.warning("No relevant news found for this query.")
                else:
                    # Display results in nice cards
                    for article in results:
                        with st.expander(f"📰 {article['title']}", expanded=True):
                            st.write(article['content'])
                            st.markdown(f"**Retrieval Reason:** {article.get('reason', 'N/A')}")
                            
                            # Show the impacted stocks if they exist
                            if article.get('impact'):
                                st.markdown("**Impacted Stocks:**")
                                for stock in article['impact']:
                                    st.info(f"Ticker: **{stock['symbol']}** | Confidence: {stock['confidence']} | Type: {stock['type']}")
                                    
            except requests.exceptions.ConnectionError:
                st.error("Error: Could not connect to the backend. Is Uvicorn running?")
            except Exception as e:
                st.error(f"An error occurred: {e}")