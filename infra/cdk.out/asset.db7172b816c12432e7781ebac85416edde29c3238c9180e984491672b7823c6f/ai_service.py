"""
CDSS AI Service — Bedrock RAG & Comprehend Medical
Unified service for clinical AI capabilities.
"""

import json
import logging
from typing import List, Optional

import boto3
from .config import AWS_REGION

logger = logging.getLogger(__name__)


class AIService:
    """Service for RAG retrieval and clinical entity extraction."""

    def __init__(self):
        self._bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
        self._comprehend_medical = boto3.client("comprehendmedical", region_name=AWS_REGION)

    def retrieve_from_knowledge_base(
        self, 
        query: str, 
        kb_id: str, 
        number_of_results: int = 5
    ) -> List[dict]:
        """
        Retrieve relevant clinical protocols or history from Bedrock Knowledge Base.
        """
        try:
            response = self._bedrock_agent_runtime.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={"text": query},
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": number_of_results
                    }
                }
            )
            
            results = []
            for result in response.get("retrievalResults", []):
                results.append({
                    "text": result["content"]["text"],
                    "location": result.get("location", {}),
                    "score": result.get("score", 0)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"KB retrieval failed: {e}")
            return []

    def extract_medical_entities(self, text: str) -> dict:
        """
        Extract medical entities (Medications, Conditions, Tests) using Comprehend Medical.
        """
        try:
            # Unified entity detection (SNOMED, RxNorm, ICD-10)
            response = self._comprehend_medical.detect_entities_v2(Text=text)
            
            entities = {
                "MEDICATION": [],
                "MEDICAL_CONDITION": [],
                "TEST_TREATMENT_PROCEDURE": [],
                "ANATOMY": []
            }
            
            for entity in response.get("Entities", []):
                category = entity.get("Category")
                if category in entities:
                    entities[category].append({
                        "text": entity["Text"],
                        "score": entity["Score"],
                        "traits": [t["Name"] for t in entity.get("Traits", [])]
                    })
            
            return entities
            
        except Exception as e:
            logger.error(f"Comprehend Medical extraction failed: {e}")
            return {}

    def analyze_clinical_text(self, text: str, kb_id: Optional[str] = None) -> dict:
        """
        Perform a full clinical analysis of text:
        1. Extract entities with Comprehend Medical
        2. Retrieve context from Knowledge Base (if kb_id provided)
        """
        analysis = {
            "entities": self.extract_medical_entities(text),
            "kb_context": []
        }
        
        if kb_id:
            analysis["kb_context"] = self.retrieve_from_knowledge_base(text, kb_id)
            
        return analysis
