#!/usr/bin/env python
"""
Direct test of LangSmith tracing with traceable decorator
"""
import os
import asyncio
from langchain_openai import ChatOpenAI
from langsmith.run_helpers import traceable

# Set environment variables
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "espressobot"

@traceable(name="test_orchestrator_flow", run_type="chain")
async def test_orchestrator_flow(message: str):
    """Simulates orchestrator flow with tracing"""
    
    # Step 1: Routing decision
    routing_result = await make_routing_decision(message)
    print(f"  Routing: {routing_result}")
    
    # Step 2: Process with agent
    if routing_result == "math":
        response = await process_with_math_agent(message)
    else:
        response = await process_with_general_agent(message)
    
    return response

@traceable(name="routing_decision", run_type="llm")
async def make_routing_decision(message: str):
    """Simulates routing decision"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = f"""Classify this message:
    Message: {message}
    
    Return 'math' if it's a math question, otherwise 'general'.
    Just return the single word."""
    
    response = await llm.ainvoke(prompt)
    return response.content.strip().lower()

@traceable(name="math_agent", run_type="chain")
async def process_with_math_agent(message: str):
    """Simulates math agent processing"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = await llm.ainvoke(f"Answer this math question: {message}")
    return response.content

@traceable(name="general_agent", run_type="chain")
async def process_with_general_agent(message: str):
    """Simulates general agent processing"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    response = await llm.ainvoke(f"Respond to: {message}")
    return response.content

async def main():
    print("\n" + "="*60)
    print("Testing LangSmith Tracing with @traceable decorators")
    print("="*60)
    
    # Test 1: Math question
    print("\n📝 Test 1: Math question")
    result = await test_orchestrator_flow("What is 15 + 27?")
    print(f"  Response: {result}")
    
    # Test 2: General question
    print("\n📝 Test 2: General question")
    result = await test_orchestrator_flow("What's the weather like?")
    print(f"  Response: {result}")
    
    print("\n" + "="*60)
    print("✅ Tests completed!")
    print("\n📊 View traces at:")
    print("https://smith.langchain.com/o/336cb8ba-b6ab-42fa-85a4-9c079014f4ce/projects/p/espressobot/runs")
    print("\nYou should see:")
    print("- test_orchestrator_flow (parent trace)")
    print("  - routing_decision (child trace)")
    print("  - math_agent OR general_agent (child trace)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())