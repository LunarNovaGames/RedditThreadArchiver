"""
Exporters - Output format handlers for Q&A data.
"""

import json
from abc import ABC, abstractmethod
from models import QAPair


class BaseExporter(ABC):
    """Abstract base class for exporters."""
    
    @abstractmethod
    def export(self, qa_pairs: list[QAPair]) -> str:
        """Export Q&A pairs to string format."""
        pass


class MarkdownExporter(BaseExporter):
    """Export Q&A pairs to Markdown format."""
    
    def export(self, qa_pairs: list[QAPair]) -> str:
        """
        Export Q&A pairs to Markdown.
        
        Format:
            Q:
            <question text>
            
            A:
            <answer text>
        """
        lines = []
        
        for qa in qa_pairs:
            # Question
            lines.append("Q:")
            lines.append(qa.question.body)
            lines.append("")
            
            # Answer(s)
            for answer in qa.answers:
                lines.append("A:")
                lines.append(answer.body)
                lines.append("")
            
            lines.append("")  # Extra blank line between Q&A pairs
        
        return "\n".join(lines)


class TextExporter(BaseExporter):
    """Export Q&A pairs to plain text format."""
    
    def export(self, qa_pairs: list[QAPair]) -> str:
        """
        Export Q&A pairs to plain text.
        
        Same format as Markdown but cleaner for reading.
        """
        lines = []
        
        for i, qa in enumerate(qa_pairs, 1):
            lines.append(f"Q:")
            lines.append(qa.question.body)
            lines.append("")
            
            for answer in qa.answers:
                lines.append(f"A:")
                lines.append(answer.body)
                lines.append("")
            
            lines.append("")
        
        return "\n".join(lines)


class JSONExporter(BaseExporter):
    """Export Q&A pairs to JSON format."""
    
    def export(self, qa_pairs: list[QAPair]) -> str:
        """
        Export Q&A pairs to JSON.
        
        Returns a JSON array of Q&A objects.
        """
        data = []
        
        for qa in qa_pairs:
            qa_obj = {
                "question": {
                    "id": qa.question.id,
                    "author": qa.question.author,
                    "body": qa.question.body,
                    "created_utc": qa.question.created_utc,
                    "permalink": qa.question.permalink
                },
                "answers": [
                    {
                        "id": answer.id,
                        "author": answer.author,
                        "body": answer.body,
                        "created_utc": answer.created_utc,
                        "permalink": answer.permalink
                    }
                    for answer in qa.answers
                ]
            }
            data.append(qa_obj)
        
        return json.dumps(data, indent=2, ensure_ascii=False)
