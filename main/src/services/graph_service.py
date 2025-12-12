# src/services/graph_service.py

import logging
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDFS, XSD

log = logging.getLogger(__name__)

QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")

class GraphService:
    def __init__(self, ttl_path):
        self.g = Graph()
        self.g.parse(ttl_path, format="turtle")
        self.QUDT = QUDT
        self.UNIT = UNIT

    def find_unit_uri_by_label(self, label):
        """
        Try to find a unit URI by rdfs:label match (case-insensitive).
        """
        q = """
        SELECT ?unit WHERE {
            ?unit rdfs:label ?label .
            FILTER(lcase(str(?label)) = lcase(str("%s")) )
        } LIMIT 1
        """ % label.replace('"', '\\"')
        res = list(self.g.query(q))
        if res:
            return res[0][0]
        return None

    def get_unit_multiplier(self, unit_uri):
        """
        Return the conversionMultiplier literal for a unit URI if present (float).
        Assumes conversionMultiplier is to a canonical base (e.g., cubic meter).
        """
        unit_ref = URIRef(unit_uri)
        for _, _, val in self.g.triples((unit_ref, self.QUDT.conversionMultiplier, None)):
            try:
                return float(val.toPython())
            except Exception:
                pass
        return None

    def get_commodity_unit(self, commodity_label):
        """
        Resolve commodity node by label and return the associated unit URI (qudt:unit).
        """
        q = """
        SELECT ?unit WHERE {
            ?c rdfs:label "%s" .
            ?c <http://qudt.org/schema/qudt/unit> ?unit .
        } LIMIT 1
        """ % commodity_label.replace('"', '\\"')
        res = list(self.g.query(q))
        if res:
            return res[0][0]
        return None

    def get_conversion_factor(self, commodity_label_or_unit, target_unit_label_or_uri):
        """
        Two modes:
        - If commodity_label_or_unit is a commodity label known in graph, use its associated unit.
        - Otherwise, if it's a unit URI/label, treat it as the source unit.
        Returns multiplier to convert 1 * source_unit -> target_unit (float), or None.
        """
        # Resolve source unit
        source_unit_uri = None

        # 1) if commodity exists with that label, use its unit
        source_unit_uri = self.get_commodity_unit(commodity_label_or_unit)

        # 2) else try interpret as unit label
        if not source_unit_uri:
            source_unit_uri = self.find_unit_uri_by_label(commodity_label_or_unit)

        # 3) if still not found and input looks like a URI, use it
        if not source_unit_uri and isinstance(commodity_label_or_unit, str) and commodity_label_or_unit.startswith("http"):
            source_unit_uri = URIRef(commodity_label_or_unit)

        if not source_unit_uri:
            log.warning("Source unit not found for input: %s", commodity_label_or_unit)
            return None

        # Resolve target unit
        target_unit_uri = None
        if isinstance(target_unit_label_or_uri, str) and target_unit_label_or_uri.startswith("http"):
            target_unit_uri = URIRef(target_unit_label_or_uri)
        else:
            target_unit_uri = self.find_unit_uri_by_label(target_unit_label_or_uri)

        if not target_unit_uri:
            log.warning("Target unit not found for input: %s", target_unit_label_or_uri)
            return None

        # Get conversion multipliers (assumed to be to same canonical base, e.g., cubic meter)
        src_mul = self.get_unit_multiplier(source_unit_uri)
        tgt_mul = self.get_unit_multiplier(target_unit_uri)

        if src_mul is None or tgt_mul is None:
            log.warning("Missing multiplier: src=%s (%s), tgt=%s (%s)", source_unit_uri, src_mul, target_unit_uri, tgt_mul)
            # if one is missing, we cannot compute exact ratio reliably; return None
            return None

        # conversion factor from source_unit -> target_unit = src_mul / tgt_mul
        # Eg: if src_mul=0.1589873 (bbl->m3) and tgt_mul=1 (m3->m3), factor=0.1589873
        conversion = src_mul / tgt_mul
        return float(conversion)
