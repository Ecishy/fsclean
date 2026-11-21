"""fsclean — tidy messy folders by moving loose files into category folders."""

from .core import CATEGORIES, Move, apply_moves, format_bytes, parse_rules, plan_moves

__version__ = "0.1.0"

__all__ = ["CATEGORIES", "Move", "apply_moves", "format_bytes", "parse_rules", "plan_moves"]
