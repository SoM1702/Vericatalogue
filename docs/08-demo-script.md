# Demo Script (3 Minutes)

## Opening (30 seconds)
"AI can easily extract catalog data. But industrial commerce cannot trust AI without proof. If a valve's pressure rating is hallucinated, it could cause catastrophic failure. VeriCatalog Proof makes every product attribute auditable before it reaches a PIM. It acts as a trust layer between unstructured supplier data and your structured catalog."

## Action 1: Enrich Product (1 minute)
"Let's look at a common scenario. A distributor receives a messy supplier catalog containing incomplete product information. I'll upload this PDF for an industrial ball valve."
*(Uploads PDF)*
"VeriCatalog Proof extracts the attributes and normalizes the units. Notice that '25.4 mm' was automatically standardized to '1 inch' based on our PIM requirements."

## Action 2: Evidence & Review Workbench (1 minute)
"Because trust is paramount, every field has lineage. If I click on the 'Pressure Rating' field, the Evidence Workbench opens. It shows me exactly where this value came from in the source document—page 2, and the exact text snippet."
"Here we see a flagged issue: the system detected a conflict. Our historical data says 400 WOG, but the new PDF says 600 WOG. I run the bounded Evidence Review Agent. It performs four local, inspect-only checks, records its audit trail, and ranks this conflict for my review. It cannot edit or approve anything; I inspect the evidence and make the final decision. Once resolved, I export a trusted, PIM-ready record."

## Action 3: Catalog Health (30 seconds)
"Finally, this isn't just for single items. On the Catalog Health page, we can see this workflow operating across a clearly labelled synthetic batch of 50+ products. It calculates completeness, highlights conflicts and missing required fields, and prioritizes the exact items requiring review. Those metrics describe this processed batch; we do not claim an unmeasured real-world accuracy or time saving."
