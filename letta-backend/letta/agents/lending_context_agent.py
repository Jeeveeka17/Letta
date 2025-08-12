import os
import json
import numpy as np
from typing import Dict, List, Optional, Any
import anthropic
from ..db_demo import GraphVectorDB
from .base_agent import BaseAgent
from ..embeddings import get_embedding

class LendingContextAgent(BaseAgent):
    def __init__(self, anthropic_api_key: str):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.db = GraphVectorDB()
        self.setup_knowledge_base()

    def setup_knowledge_base(self):
        """Initialize the knowledge base with context documents"""
        # Create schema
        self.db.create_schema()

        # Load and embed context files
        context_files = {
            "ekyc": "context/eKYC.txt",
            "lending": "context/lending_rules.txt",
            "pan": "context/PANNSDL.txt"
        }

        # Store documents and create relationships
        doc_ids = {}
        for category, filepath in context_files.items():
            with open(filepath, 'r') as f:
                content = f.read()
                # Get embedding for the content
                vector = get_embedding(content)
                # Add to databases
                doc_id = self.db.add_document(
                    content=content,
                    category=category,
                    vector=vector
                )
                doc_ids[category] = doc_id

        # Create relationships between related documents
        self.db.create_relationship(
            doc_ids["ekyc"], 
            doc_ids["pan"], 
            "REQUIRES"
        )
        self.db.create_relationship(
            doc_ids["lending"], 
            doc_ids["ekyc"], 
            "REQUIRES"
        )

    def process_query(self, query: str) -> str:
        """Process a user query using context-aware responses"""
        # Get query embedding
        query_vector = get_embedding(query)
        
        # Search for relevant context
        similar_docs = self.db.search_similar(query_vector)
        
        # Build context from similar documents
        context = "\n\n".join([
            f"Category: {doc.properties['category']}\n{doc.properties['content']}"
            for doc in similar_docs
        ])

        # Create message with context
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a lending assistant with expertise in eKYC verification, "
                    "PAN verification, and lending rules. Use the following context "
                    "to provide accurate responses:\n\n" + context
                )
            },
            {
                "role": "user",
                "content": query
            }
        ]

        # Get response from Claude
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=messages
        )

        return response.content[0].text

    def verify_pan(self, pan: str, name: str) -> Dict[str, Any]:
        """Verify PAN details using context rules"""
        # Get PAN verification context
        query_vector = get_embedding("PAN verification process")
        similar_docs = self.db.search_similar(query_vector)
        pan_doc = next(
            (doc for doc in similar_docs 
             if doc.properties['category'] == 'pan'),
            None
        )

        if not pan_doc:
            return {"error": "PAN verification context not found"}

        # Validate PAN format
        if not self._validate_pan_format(pan):
            return {
                "status": "INVALID",
                "message": "Invalid PAN format"
            }

        # Apply business rules from context
        if pan.startswith('ZZZ'):
            return {
                "status": "ERROR",
                "message": "API error occurred"
            }

        if pan[-1].isdigit() and int(pan[-1]) % 2 == 0:
            status = "Active"
        else:
            status = "Inactive"

        return {
            "status": status,
            "aadhaar_linked": True,
            "pan_masked": "XXXX" + pan[-5:],
            "name": name
        }

    def verify_ekyc(self, aadhaar: str, consent: bool) -> Dict[str, Any]:
        """Verify eKYC details using context rules"""
        if not consent:
            return {
                "status": "FAILED",
                "message": "Identity verification consent is mandatory"
            }

        if not aadhaar.isdigit() or len(aadhaar) != 12:
            return {
                "status": "FAILED",
                "message": "Invalid Aadhaar format"
            }

        return {
            "status": "IN_PROGRESS",
            "reference_number": "REF" + aadhaar[-6:],
            "message": "OTP sent to registered mobile"
        }

    def check_loan_eligibility(
        self, 
        loan_type: str, 
        credit_score: int,
        income: float
    ) -> Dict[str, Any]:
        """Check loan eligibility using context rules"""
        # Get lending rules context
        query_vector = get_embedding("loan eligibility criteria")
        similar_docs = self.db.search_similar(query_vector)
        lending_doc = next(
            (doc for doc in similar_docs 
             if doc.properties['category'] == 'lending'),
            None
        )

        if not lending_doc:
            return {"error": "Lending rules context not found"}

        eligibility = {
            "eligible": False,
            "reasons": []
        }

        if loan_type == "personal":
            if credit_score < 680:
                eligibility["reasons"].append(
                    "Credit score below minimum requirement of 680"
                )
            if income < 30000:
                eligibility["reasons"].append(
                    "Income below minimum requirement of $30,000/year"
                )
            eligibility["eligible"] = len(eligibility["reasons"]) == 0

        elif loan_type == "business":
            if credit_score < 700:
                eligibility["reasons"].append(
                    "Credit score below minimum requirement of 700"
                )
            # Add other business loan criteria checks

        elif loan_type == "mortgage":
            if credit_score < 720:
                eligibility["reasons"].append(
                    "Credit score below minimum requirement of 720"
                )
            # Add other mortgage criteria checks

        return eligibility

    def _validate_pan_format(self, pan: str) -> bool:
        """Validate PAN format based on context rules"""
        if len(pan) != 10:
            return False
        
        # First 3 characters: alphabets
        if not pan[:3].isalpha():
            return False
            
        # 4th character: "P"
        if pan[3] != "P":
            return False
            
        # 5th character: alphabet
        if not pan[4].isalpha():
            return False
            
        # Next 4 characters: digits
        if not pan[5:9].isdigit():
            return False
            
        # Last character: alphabet
        if not pan[9].isalpha():
            return False
            
        return True

    def close(self):
        """Clean up resources"""
        self.db.close()
