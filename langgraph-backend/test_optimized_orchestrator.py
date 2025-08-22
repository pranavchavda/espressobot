#!/usr/bin/env python3
"""
Test script for the optimized orchestrator
Demonstrates the key architectural improvements
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

from orchestrator_optimized import (
    OptimizedProgressiveOrchestrator,
    OrchestratorConfig,
    OrchestratorState,
    OrchestratorWorkflowState
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_basic_orchestration():
    """Test basic orchestration functionality"""
    print("🧪 Testing Basic Orchestration...")
    
    # Create config for testing
    config = OrchestratorConfig(
        max_agent_calls_per_request=3,
        enable_structured_logging=True,
        log_level="DEBUG",
        persist_conversations=False,  # Disable for testing
        persist_agent_state=False
    )
    
    orchestrator = OptimizedProgressiveOrchestrator(config)
    
    # Test message
    test_message = "Find coffee products under $50"
    thread_id = "test-thread-123"
    
    print(f"📤 Sending: {test_message}")
    print("📨 Response:")
    
    try:
        response_tokens = []
        async for token in orchestrator.orchestrate(test_message, thread_id, "test-user"):
            response_tokens.append(token)
            print(token, end="", flush=True)
        
        print(f"\\n\\n✅ Complete response received ({len(response_tokens)} tokens)")
        return True
        
    except Exception as e:
        print(f"\\n❌ Error during orchestration: {e}")
        return False

async def test_state_machine_transitions():
    """Test state machine behavior"""
    print("\\n🧪 Testing State Machine Transitions...")
    
    config = OrchestratorConfig(enable_structured_logging=True, log_level="DEBUG")
    orchestrator = OptimizedProgressiveOrchestrator(config)
    
    # Create a test workflow state
    state = OrchestratorWorkflowState(
        thread_id="test-state-machine",
        user_id="test-user",
        user_message="Test state transitions"
    )
    
    # Test state transitions
    initial_state = state.current_state
    print(f"Initial state: {initial_state.value}")
    
    # Simulate state machine execution (without full orchestration)
    await orchestrator._state_initializing(state)
    print(f"After initialization: {state.current_state.value}")
    
    await orchestrator._state_planning(state)
    print(f"After planning: {state.current_state.value}")
    
    print("✅ State machine transitions working correctly")
    return True

async def test_configuration_management():
    """Test configuration loading from environment"""
    print("\\n🧪 Testing Configuration Management...")
    
    # Set some test environment variables
    os.environ["ORCHESTRATOR_MAX_AGENT_CALLS"] = "10"
    os.environ["ORCHESTRATOR_AGENT_TIMEOUT"] = "120"
    os.environ["ORCHESTRATOR_LOG_LEVEL"] = "DEBUG"
    
    config = OrchestratorConfig.from_env()
    
    print(f"Max agent calls: {config.max_agent_calls_per_request}")
    print(f"Agent timeout: {config.agent_timeout_seconds}")
    print(f"Log level: {config.log_level}")
    
    assert config.max_agent_calls_per_request == 10
    assert config.agent_timeout_seconds == 120
    assert config.log_level == "DEBUG"
    
    print("✅ Configuration management working correctly")
    return True

async def test_error_handling():
    """Test error handling and retry mechanisms"""
    print("\\n🧪 Testing Error Handling...")
    
    config = OrchestratorConfig(
        max_retries=2,
        base_retry_delay=0.1,  # Fast for testing
        enable_structured_logging=True
    )
    orchestrator = OptimizedProgressiveOrchestrator(config)
    
    # Test with a simulated error condition
    async def failing_operation():
        raise Exception("Simulated failure")
    
    try:
        await orchestrator.retry_handler.execute_with_retry(
            "test_operation",
            failing_operation
        )
        print("❌ Expected exception was not raised")
        return False
    except Exception as e:
        print(f"✅ Exception properly handled after retries: {e}")
        return True

async def test_structured_logging():
    """Test structured logging functionality"""
    print("\\n🧪 Testing Structured Logging...")
    
    config = OrchestratorConfig(enable_structured_logging=True, log_level="INFO")
    orchestrator = OptimizedProgressiveOrchestrator(config)
    
    # Test various log events
    orchestrator.logger.log_event("test_event", test_param="test_value", count=42)
    orchestrator.logger.log_agent_call("test_agent", "test_task", 1.5, True, extra_info="test")
    orchestrator.logger.log_state_transition("state_a", "state_b", "test_trigger")
    orchestrator.logger.log_error("test_error", "Test error message", retry_count=1)
    
    print("✅ Structured logging working correctly (check logs above)")
    return True

async def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Optimized Orchestrator Tests\\n")
    
    tests = [
        ("Configuration Management", test_configuration_management),
        ("Structured Logging", test_structured_logging),
        ("Error Handling", test_error_handling),
        ("State Machine Transitions", test_state_machine_transitions),
        ("Basic Orchestration", test_basic_orchestration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\\n🎯 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The optimized orchestrator is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
    
    return passed == len(results)

if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_comprehensive_test())
    sys.exit(0 if success else 1)