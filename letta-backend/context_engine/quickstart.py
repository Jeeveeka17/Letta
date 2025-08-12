"""
Quick Start Guide for Context Engine
"""
import asyncio
from enhanced_context_engine import EnhancedContextEngine
from schema import ContentType, DomainType, LayerType

async def demonstrate_capabilities():
    # Initialize the engine - no need to pass anthropic_api_key, it will use the one from .env
    engine = EnhancedContextEngine(base_dir="context")
    
    # Process all content
    print("Processing content...")
    await engine.process_directory()
    
    # Example 1: Basic Context Query
    print("\n1. Basic Query for Loan Verification:")
    results = await engine.query_context(
        query="How do we verify loan applications?",
        k=2
    )
    for result in results:
        print(f"\nFound in: {result.metadata.file_path}")
        print(f"Summary: {result.metadata.summary}")
    
    # Example 2: Code-Specific Query
    print("\n2. Finding Code Implementation:")
    code_results = await engine.query_context(
        query="loan verification implementation",
        filter_criteria={
            "content_type": ContentType.CODE,
            "layer": LayerType.SERVICE
        }
    )
    for result in code_results:
        print(f"\nCode from: {result.metadata.file_path}")
        if result.code_snippet:
            print("Relevant code snippet:")
            print(result.code_snippet)
    
    # Example 3: Documentation Query
    print("\n3. Finding Documentation:")
    doc_results = await engine.query_context(
        query="credit score requirements",
        filter_criteria={
            "content_type": ContentType.DOCUMENTATION
        }
    )
    for result in doc_results:
        print(f"\nFound in: {result.metadata.file_path}")
        print(f"Summary: {result.metadata.summary}")
    
    # Example 4: Exploring Relationships
    print("\n4. Exploring Related Capabilities:")
    graph = engine.get_capability_graph("loan_verification")
    print("\nRelated concepts:")
    for node in graph["nodes"]:
        print(f"- {node['id']} ({node['type']})")

if __name__ == "__main__":
    asyncio.run(demonstrate_capabilities())