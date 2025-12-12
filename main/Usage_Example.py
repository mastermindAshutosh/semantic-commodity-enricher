# after pipeline run that created data/output/commodities.ttl (with QUDT loaded)

from src.services.graph_service import GraphService

gs = GraphService("./data/output/commodities.ttl")

# Convert 10 barrels of Brent to cubic meters:
factor = gs.get_conversion_factor("Brent Crude", "Cubic Meter")
if factor:
    print("1 Barrel ->", factor, "Cubic Meter")
    print("10 Barrels ->", 10 * factor, "Cubic Meter")
else:
    print("Conversion factor missing; inspect QUDT triples in graph.")
