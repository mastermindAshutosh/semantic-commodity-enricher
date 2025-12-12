# src/config.py

"""
Configuration for the enrichment pipeline.
- TARGET_COMMODITIES: seed list of canonical commodities (Wikidata QIDs)
  The pipeline will fetch labels/descriptions and enrich these entities.
  Use QIDs to avoid ambiguity (Wikidata canonical identifiers).
- QUDT_TTL_URL: remote TTL to download QUDT unit ontology (cached locally).
"""

# SPARQL endpoints (Wikidata / DBpedia)
WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
DBPEDIA_ENDPOINT = "https://dbpedia.org/sparql"

# Target Commodities (seed QIDs).
# Purpose: start the enrichment pipeline from these canonical entities.
# Add or remove entries depending on your domain coverage.
TARGET_COMMODITIES = {
    "Brent Crude": "Q1270246",
    "WTI Crude": "Q1049071",
    "Dubai Crude": "Q4037659",
    "Natural Gas": "Q40858",
    "Gold": "Q897",
    "Silver": "Q21409",
    "Coal": "Q24489",
    "Crude Oil (Generic)": "Q22656",
    "LNG (Liquefied Natural Gas)": "Q358333",
    "Iron Ore": "Q191552",
    # Add more QIDs your org needs to canonicalize...
}

# QUDT: where to fetch unit ontology TTL (change to a local file if required)
QUDT_TTL_URL = "https://raw.githubusercontent.com/qudt/qudt-public-repo/refs/heads/main/src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl"
QUDT_CACHE_PATH = "data/cache/qudt-units.ttl"

# Namespaces used by the RDF graph builder / service
NAMESPACES = {
    "EX": "http://example.org/commodity/",
    "QUDT": "http://qudt.org/schema/qudt/",
    "UNIT": "http://qudt.org/vocab/unit/",
    "PROV": "http://www.w3.org/ns/prov#",
}
