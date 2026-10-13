"""AI Opportunity Intake Assistant — turn healthcare business pain points into scored, responsible AI use cases."""
from .engine import assess, rank_portfolio
from .models import UseCaseInput

__all__ = ["assess", "rank_portfolio", "UseCaseInput"]
__version__ = "0.1.0"
