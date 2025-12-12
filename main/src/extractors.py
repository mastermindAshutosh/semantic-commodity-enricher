# src/extractors.py
import time
from SPARQLWrapper import SPARQLWrapper, JSON
from .config import WIKIDATA_ENDPOINT, DBPEDIA_ENDPOINT

class DataExtractor:
    def __init__(self):
        self.wd_sparql = SPARQLWrapper(WIKIDATA_ENDPOINT)
        self.db_sparql = SPARQLWrapper(DBPEDIA_ENDPOINT)
        self.wd_sparql.setReturnFormat(JSON)
        self.db_sparql.setReturnFormat(JSON)

    def fetch_wikidata_metadata(self, qid):
        """
        Fetches label, description, unit of measure QID, and origin.
        """
        query = f"""
        SELECT ?label ?desc ?unit ?unitLabel ?originLabel WHERE {{
          wd:{qid} rdfs:label ?label .
          OPTIONAL {{ wd:{qid} schema:description ?desc . }}
          OPTIONAL {{ wd:{qid} wdt:P291 ?origin . }}     # Place of Origin
          OPTIONAL {{ wd:{qid} wdt:P2237 ?unit . }}      # Units used in trade
          FILTER(LANG(?label) = "en")
          FILTER(LANG(?desc) = "en")
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT 1
        """
        self.wd_sparql.setQuery(query)
        try:
            results = self.wd_sparql.query().convert()
            if results["results"]["bindings"]:
                return results["results"]["bindings"][0]
            return None
        except Exception as e:
            print(f"Error fetching Wikidata for {qid}: {e}")
            return None

    def fetch_dbpedia_abstract(self, label):
        """
        Fetches the abstract from DBpedia for richer semantic context.
        """
        # Clean label for DBpedia resource format (Spaces -> Underscores)
        resource = label.replace(" ", "_")
        query = f"""
        SELECT ?abstract WHERE {{
          <http://dbpedia.org/resource/{resource}> dbo:abstract ?abstract .
          FILTER(LANG(?abstract) = "en")
        }} LIMIT 1
        """
        self.db_sparql.setQuery(query)
        try:
            results = self.db_sparql.query().convert()
            if results["results"]["bindings"]:
                return results["results"]["bindings"][0]["abstract"]["value"]
            return None
        except Exception as e:
            # Fallback: simple error handling
            return None