from __future__ import annotations

from .agents.orchestrator import run_orchestrator_graph
from .config import DEMO_DIR, UPLOAD_DIR
from .extraction import parse_source_payload
from .models import AgentDecision, ProductAttribute, ProductRecord, ReviewAgentPlan


class EvidenceReviewAgent:
    """A bounded, local tool-using controller for human catalog review.

    This compiles and runs the real-time stateful LangGraph pipeline
    configured in backend/app/agents/orchestrator.py.
    """

    def run(self, product: ProductRecord) -> ReviewAgentPlan:
        # Backward-compatible run method
        plan, _, _ = self.run_with_updates(product)
        return plan

    def run_with_updates(
        self, product: ProductRecord, historical_corrections: list[dict] = None
    ) -> tuple[ReviewAgentPlan, list[ProductAttribute], list[AgentDecision]]:
        # Rebuild source document context from stored references
        context = self._rebuild_context(product)

        # Invoke the compiled LangGraph pipeline in real time
        return run_orchestrator_graph(product, context, historical_corrections)

    @staticmethod
    def _rebuild_context(product: ProductRecord) -> str:
        files = {}
        for attr in product.attributes:
            for ev in attr.evidence:
                if ev.source_file and ev.source_file not in {"Manual entry", "Agent Graph Ingestion"}:
                    if ev.source_file not in files:
                        files[ev.source_file] = set()
                    if ev.row is not None:
                        files[ev.source_file].add(ev.row)

        context_parts = []
        for fname, rows_to_keep in files.items():
            is_tabular = fname.lower().endswith((".csv", ".xlsx"))
            for folder in (UPLOAD_DIR, DEMO_DIR):
                path = folder / fname
                if path.exists():
                    try:
                        rows = parse_source_payload(fname, path.read_bytes())
                        for idx, row in enumerate(rows):
                            # If it's a CSV/XLSX, only include the row context if it matches this product's row(s)
                            if is_tabular:
                                if idx in rows_to_keep:
                                    if row.context:
                                        context_parts.append(row.context)
                            else:
                                if row.context:
                                    context_parts.append(row.context)
                    except Exception:
                        pass

        if not context_parts:
            snippets = []
            for attr in product.attributes:
                for ev in attr.evidence:
                    if ev.snippet:
                        snippets.append(ev.snippet)
            return "\n".join(snippets)

        return "\n".join(context_parts)
