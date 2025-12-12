# main.py
import os
import sys
import ssl

# --- 1. FORCE SSL BYPASS FOR ALL LIBRARIES (URLLIB + REQUESTS) ---
# This disables verification for SPARQLWrapper
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# This disables verification for HuggingFace / Requests
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

# ⚠️ MONKEY PATCH REQUESTS TO IGNORE VERIFY=TRUE
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

old_merge_environment_settings = requests.Session.merge_environment_settings

def merge_environment_settings(self, url, proxies, stream, verify, cert):
    # Always overwrite 'verify' to False, no matter what the library asks for
    return old_merge_environment_settings(self, url, proxies, stream, False, cert)

requests.Session.merge_environment_settings = merge_environment_settings
# -----------------------------------------------------------------

from tqdm import tqdm
# Ensure we can find the src module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import TARGET_COMMODITIES
from src.extractors import DataExtractor
from src.graph_builder import KnowledgeGraphBuilder
from src.vector_engine import VectorEngine

def build_embedding_text(name, wikidata, dbpedia_abs, inferred_unit):
    label = wikidata.get("label", {}).get("value", "")
    desc = wikidata.get("desc", {}).get("value", "")
    origin = wikidata.get("originLabel", {}).get("value", "")
    raw_unit = wikidata.get("unitLabel", {}).get("value", "")
    
    enriched = f"""
    Commodity Name: {label}
    Common Name: {name}
    Description: {desc}
    Origin: {origin}
    Wikidata Unit Label: {raw_unit}
    Inferred QUDT Unit: {inferred_unit}

    DBpedia Abstract:
    {dbpedia_abs}

    Category: Energy Commodity
    Semantic Class: {("Oil" if "oil" in label.lower() else
                       "Gas" if "gas" in label.lower() else
                       "Metal" if "gold" in label.lower() else
                       "Unknown")}

    Synonyms:
    {name}, {label}, {label.lower()}, {name.lower()}
    """

    return enriched

def main():
    # Ensure output directory
    os.makedirs("data/output", exist_ok=True)

    print("--- Starting Open-Data Enrichment Pipeline ---")
    
    # Initialize components
    extractor = DataExtractor()
    kg_builder = KnowledgeGraphBuilder()
    
    # This should now download successfully without SSL errors
    print("Initializing Vector Engine (Downloading model if needed)...")
    vector_engine = VectorEngine() 

    for name, qid in tqdm(TARGET_COMMODITIES.items()):
        # 1. Pull Metadata (Wikidata)
        wd_data = extractor.fetch_wikidata_metadata(qid)
        
        if not wd_data:
            print(f"Skipping {name} (No data found)")
            continue

        label = wd_data.get("label", {}).get("value", name)
        desc = wd_data.get("desc", {}).get("value", "")
        unit_label = wd_data.get("unitLabel", {}).get("value", "")
        
        # 2. Pull Context (DBpedia) - Enrichment Step
        abstract = extractor.fetch_dbpedia_abstract(label)
        full_context = f"{desc} {abstract if abstract else ''}"

        # 3. Build Graph
        commodity_data = {
            "qid": qid,
            "label": label,
            "description": desc,
            "unit_label": unit_label
        }
        kg_builder.add_commodity(commodity_data)

        # 4. Build Vector Index
        # Infer QUDT unit attached in graph (optional)
        inferred_unit = unit_label or "Unknown"

        embedding_text = build_embedding_text(
            name=name,
            wikidata=wd_data,
            dbpedia_abs=abstract,
            inferred_unit=inferred_unit
        )

        vector_engine.add_to_index(
            embedding_text,
            metadata={
                "qid": qid,
                "label": label,
                "unit": inferred_unit
            }
        )


    # Save artifacts
    kg_builder.save_graph()
    vector_engine.save_index()
    
    print("\n--- Pipeline Complete ---")
    print("1. Knowledge Graph saved to data/output/commodities.ttl")
    print("2. Vector Index saved to data/output/vector_store.index")

    # --- Quick Verification Demo ---
    print("\n--- Testing Fuzzy Resolution ---")
    test_queries = [
        "Oil from the North Sea", 
        "Texas Light Sweet", 
        "Prices for natural gas delivery"
    ]
    
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        results = vector_engine.search(q, k=1)
        for r in results:
            print(f"Match: {r['metadata']['label']} (Score: {r['score']:.4f})")
            print(f"Canonical ID: {r['metadata']['qid']}")

if __name__ == "__main__":
    main()