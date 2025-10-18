"""
AI Processing Module

This module contains AI-powered enhancements for medical coding,
including OpenAI GPT-4o integration for intelligent DRG analysis.
"""

from .openai_drg_analyzer import (
    OpenAIDRGAnalyzer,
    DRGAnalysis,
    get_openai_drg_analyzer,
    analyze_concepts_with_openai
)

__all__ = [
    'OpenAIDRGAnalyzer',
    'DRGAnalysis', 
    'get_openai_drg_analyzer',
    'analyze_concepts_with_openai'
]