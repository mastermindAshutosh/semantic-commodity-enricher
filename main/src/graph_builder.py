# src/graph_builder.py

import logging
import os
import time
from datetime import datetime
from rdflib import Graph, Literal, RDF, URIRef, Namespace
from rdflib.namespace import PROV, RDFS, XSD, OWL
from .config import NAMESPACES, QUDT_TTL_URL, QUDT_CACHE_PATH
from .qudt_rules import infer_unit, get_multiplier  # optional fallback mapping

log = logging.getLogger(__name__)

class KnowledgeGraphBuilder:
    def __init__(self):
        self.g = Graph()
        # Namespaces
        self.EX = Namespace(NAMESPACES["EX"])
        self.QUDT = Namespace(NAMESPACES["QUDT"])
        self.UNIT = Namespace(NAMESPACES["UNIT"])
        self.g.bind("ex", self.EX)
        self.g.bind("qudt", self.QUDT)
        self.g.bind("unit", self.UNIT)
        self.g.bind("prov", PROV)

        self.activity_id = URIRef(f"{self.EX}activity/{datetime.utcnow().isoformat()}")
        self.g.add((self.activity_id, RDF.type, PROV.Activity))

        # Load QUDT ontology into graph (cached)
        self._ensure_qudt_loaded()

    def _download_qudt(self, url, local_path, retries=3, backoff=2):
        import requests
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as fh:
                    fh.write(resp.content)
                log.info("Downloaded QUDT TTL to %s", local_path)
                return local_path
            except Exception as e:
                log.warning("QUDT download attempt %d failed: %s", attempt, e)
                time.sleep(backoff * attempt)
        raise RuntimeError("Failed to download QUDT TTL after retries")

    def _ensure_qudt_loaded(self):
        # Try local cache first
        if os.path.exists(QUDT_CACHE_PATH):
            try:
                self.g.parse(QUDT_CACHE_PATH, format="turtle")
                log.info("Loaded QUDT from cache: %s", QUDT_CACHE_PATH)
                return
            except Exception as e:
                log.warning("Failed to parse cached QUDT TTL: %s (will re-download)", e)

        # If remote URL provided, try to download and cache
        if QUDT_TTL_URL and QUDT_TTL_URL.startswith("http"):
            try:
                local = self._download_qudt(QUDT_TTL_URL, QUDT_CACHE_PATH)
                self.g.parse(local, format="turtle")
                log.info("Loaded QUDT from downloaded TTL")
                return
            except Exception as e:
                log.error("Failed to download/parse QUDT TTL: %s. QUDT triples will be missing.", e)

        # If no TTL available, we still proceed — qudt triples may be added via qudt_rules fallbacks.
        log.warning("QUDT ontology not loaded. Conversion triples may be incomplete.")

    def add_commodity(self, data):
        qid = data['qid']
        uri = self.EX[qid]
        self.g.add((uri, RDF.type, self.EX.Commodity))
        self.g.add((uri, RDFS.label, Literal(data.get("label", ""))))
        self.g.add((uri, RDFS.comment, Literal(data.get("description", ""))))
        self.g.add((uri, OWL.sameAs, URIRef(f"http://www.wikidata.org/entity/{qid}")))

        # Prefer explicit unit from Wikidata if available (data['unit_uri'] optional).
        unit_uri = data.get("unit_uri")
        if unit_uri:
            try:
                self.g.add((uri, self.QUDT.unit, URIRef(unit_uri)))
            except Exception:
                log.exception("Invalid unit URI for %s: %s", qid, unit_uri)

        # Otherwise infer from text and map to QUDT unit URI
        else:
            text_context = (data.get("label", "") + " " + data.get("description", "")).lower()
            inferred_code = infer_unit(text_context)  # e.g., "BBL"
            if inferred_code:
                unit_uri = str(self.UNIT[inferred_code])  # http://qudt.org/vocab/unit/BBL
                self.g.add((uri, self.QUDT.unit, URIRef(unit_uri)))
                log.info("Inferred unit %s for %s", inferred_code, qid)

                # If QUDT ontology loaded and provides conversionMultiplier, it's already present in graph.
                # Otherwise, attach fallback multiplier via qudt_rules.get_multiplier
                multiplier = None
                # check if multiplier triple exists in graph
                unit_ref = URIRef(unit_uri)
                mult_triples = list(self.g.triples((unit_ref, self.QUDT.conversionMultiplier, None)))
                if mult_triples:
                    log.info("Found conversionMultiplier in QUDT for %s", unit_uri)
                else:
                    # fallback: add a literal multiplier if qudt_rules has it
                    fallback = get_multiplier(inferred_code)
                    if fallback:
                        self.g.add((unit_ref, self.QUDT.conversionMultiplier, Literal(fallback, datatype=XSD.float)))
                        log.info("Added fallback conversionMultiplier for %s", inferred_code)

        # Provenance
        self.g.add((uri, PROV.wasGeneratedBy, self.activity_id))

    def save_graph(self, filepath="data/output/commodities.ttl"):
        self.g.serialize(destination=filepath, format="turtle")
        log.info("Graph saved to %s", filepath)
