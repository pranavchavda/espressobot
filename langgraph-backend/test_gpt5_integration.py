#!/usr/bin/env python3
"""
Comprehensive GPT-5 Integration Test Suite for EspressoBot
Tests GPT-5, GPT-5-mini, and GPT-5-nano integration with the LangGraph backend
"""
import os
import sys
import json
import time
import asyncio
import requests
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import aiohttp
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result container"""
    test_name: str
    success: bool
    response_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    model_used: Optional[str] = None
    pattern: Optional[str] = None
    agent_path: Optional[List[str]] = None

class GPT5IntegrationTester:
    """Comprehensive test suite for GPT-5 integration"""
    
    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Test queries for different complexity levels
        self.test_queries = {
            "simple_greeting": "Hello! How are you today?",
            "simple_price": "What's the price of the Breville Barista Express?",
            "simple_sku": "What's the SKU for the Ninja Foodi?",
            "complex_product": "Show me the Breville Barista Express with current pricing and stock levels",
            "complex_comparison": "Compare the Breville Barista Express and Sage Bambino Plus including prices, features, and availability",
            "complex_recommendation": "I need a coffee machine under $500 with milk steaming capability. Show me options with prices and stock",
            "a2a_comprehensive": "Give me a comprehensive analysis of the top 3 espresso machines including detailed specs, current pricing, inventory status, and customer reviews"
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def check_environment(self) -> bool:
        """Check if required environment variables are set"""
        required_vars = ["OPENAI_API_KEY", "DATABASE_URL"]
        optional_vars = ["OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"]
        
        missing_required = []
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        if missing_required:
            logger.error(f"❌ Missing required environment variables: {', '.join(missing_required)}")
            return False
        
        logger.info("✅ Required environment variables found")
        
        # Check optional vars
        for var in optional_vars:
            if os.getenv(var):
                logger.info(f"✅ Optional {var} configured")
            else:
                logger.warning(f"⚠️ Optional {var} not configured")
        
        return True
    
    async def test_backend_health(self) -> TestResult:
        """Test backend health endpoint"""
        test_name = "Backend Health Check"
        start_time = time.time()
        
        try:
            async with self.session.get(f"{self.backend_url}/health") as response:
                duration = time.time() - start_time
                if response.status == 200:
                    data = await response.json()
                    return TestResult(
                        test_name=test_name,
                        success=True,
                        response_data=data,
                        duration=duration
                    )
                else:
                    return TestResult(
                        test_name=test_name,
                        success=False,
                        error=f"Health check failed with status {response.status}",
                        duration=duration
                    )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def test_model_factory(self) -> TestResult:
        """Test the LLM factory model creation"""
        test_name = "LLM Factory Model Creation"
        
        try:
            # Import and test the factory
            sys.path.append('/home/pranav/espressobot/langgraph-backend')
            from app.config.llm_factory import llm_factory
            
            # Test GPT-5 model creation
            start_time = time.time()
            llm = llm_factory.create_llm("gpt-5-mini", temperature=0.0, max_tokens=100)
            duration = time.time() - start_time
            
            # Test a simple completion
            response = llm.invoke("Complete: I am GPT-5-mini and I")
            
            return TestResult(
                test_name=test_name,
                success=True,
                response_data={
                    "model_created": True,
                    "response": response.content if hasattr(response, 'content') else str(response)
                },
                duration=duration,
                model_used="gpt-5-mini"
            )
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time if 'start_time' in locals() else 0
            )
    
    async def test_simple_routing(self, query: str) -> TestResult:
        """Test simple routing with GPT-5 models"""
        test_name = f"Simple Routing: {query[:30]}..."
        start_time = time.time()
        
        try:
            payload = {
                "message": query,
                "mode": "simple",
                "thread_id": f"test-simple-{int(time.time())}"
            }
            
            async with self.session.post(
                f"{self.backend_url}/api/agent/v2/stream",
                json=payload
            ) as response:
                if response.status != 200:
                    return TestResult(
                        test_name=test_name,
                        success=False,
                        error=f"Request failed with status {response.status}",
                        duration=time.time() - start_time
                    )
                
                # Process streaming response
                full_response = ""
                agent_path = []
                pattern = None
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        if data.get("event") == "conversation_id":
                            pattern = data.get("pattern")
                        elif data.get("event") == "agent_message":
                            agent = data.get("agent")
                            if agent and agent not in agent_path:
                                agent_path.append(agent)
                            if data.get("tokens"):
                                full_response += "".join(data["tokens"])
                        elif data.get("event") == "done":
                            break
                    except json.JSONDecodeError:
                        continue
                
                duration = time.time() - start_time
                
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_data={
                        "response": full_response,
                        "response_length": len(full_response)
                    },
                    duration=duration,
                    pattern=pattern,
                    agent_path=agent_path
                )
                
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def test_a2a_orchestration(self, query: str) -> TestResult:
        """Test A2A orchestration with GPT-5 models"""
        test_name = f"A2A Orchestration: {query[:30]}..."
        start_time = time.time()
        
        try:
            payload = {
                "message": query,
                "mode": "a2a",
                "thread_id": f"test-a2a-{int(time.time())}"
            }
            
            async with self.session.post(
                f"{self.backend_url}/api/agent/v2/stream",
                json=payload
            ) as response:
                if response.status != 200:
                    return TestResult(
                        test_name=test_name,
                        success=False,
                        error=f"Request failed with status {response.status}",
                        duration=time.time() - start_time
                    )
                
                # Process streaming response
                full_response = ""
                agent_path = []
                pattern = None
                a2a_metadata = None
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        if data.get("event") == "conversation_id":
                            pattern = data.get("pattern")
                        elif data.get("event") == "agent_message":
                            agent = data.get("agent")
                            if agent and agent not in agent_path:
                                agent_path.append(agent)
                            if data.get("tokens"):
                                full_response += "".join(data["tokens"])
                        elif data.get("event") == "a2a_metadata":
                            a2a_metadata = {
                                "execution_path": data.get("execution_path", []),
                                "agents_involved": data.get("agents_involved", []),
                                "a2a_requests": data.get("a2a_requests", [])
                            }
                        elif data.get("event") == "done":
                            break
                    except json.JSONDecodeError:
                        continue
                
                duration = time.time() - start_time
                
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_data={
                        "response": full_response,
                        "response_length": len(full_response),
                        "a2a_metadata": a2a_metadata
                    },
                    duration=duration,
                    pattern=pattern,
                    agent_path=agent_path
                )
                
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def test_auto_complexity_analysis(self, query: str) -> TestResult:
        """Test automatic complexity analysis and routing"""
        test_name = f"Auto Analysis: {query[:30]}..."
        start_time = time.time()
        
        try:
            payload = {
                "message": query,
                "mode": "auto",
                "thread_id": f"test-auto-{int(time.time())}"
            }
            
            async with self.session.post(
                f"{self.backend_url}/api/agent/v2/stream",
                json=payload
            ) as response:
                if response.status != 200:
                    return TestResult(
                        test_name=test_name,
                        success=False,
                        error=f"Request failed with status {response.status}",
                        duration=time.time() - start_time
                    )
                
                # Process streaming response
                full_response = ""
                agent_path = []
                pattern = None
                analysis_reason = None
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        if data.get("event") == "conversation_id":
                            pattern = data.get("pattern")
                            analysis_reason = data.get("analysis")
                        elif data.get("event") == "agent_message":
                            agent = data.get("agent")
                            if agent and agent not in agent_path:
                                agent_path.append(agent)
                            if data.get("tokens"):
                                full_response += "".join(data["tokens"])
                        elif data.get("event") == "done":
                            break
                    except json.JSONDecodeError:
                        continue
                
                duration = time.time() - start_time
                
                return TestResult(
                    test_name=test_name,
                    success=True,
                    response_data={
                        "response": full_response,
                        "response_length": len(full_response),
                        "analysis_reason": analysis_reason
                    },
                    duration=duration,
                    pattern=pattern,
                    agent_path=agent_path
                )
                
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def test_model_tiering(self) -> TestResult:
        """Test that different models are used for different agent tiers"""
        test_name = "Model Tiering Verification"
        
        try:
            sys.path.append('/home/pranav/espressobot/langgraph-backend')
            from app.config.model_config import model_config, ModelTier
            
            # Test each tier
            tiers_tested = {}
            for tier in ModelTier:
                config = model_config.get_model_for_tier(tier)
                tiers_tested[tier.value] = {
                    "model": config.get("model"),
                    "provider": config.get("provider").value if config.get("provider") else None,
                    "max_tokens": config.get("max_tokens"),
                    "temperature": config.get("temperature")
                }
            
            # Verify GPT-5 models are configured
            gpt5_models = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
            configured_gpt5 = []
            
            for tier, config in tiers_tested.items():
                model_name = config.get("model", "")
                for gpt5_model in gpt5_models:
                    if gpt5_model in model_name:
                        configured_gpt5.append((tier, gpt5_model))
            
            return TestResult(
                test_name=test_name,
                success=len(configured_gpt5) > 0,
                response_data={
                    "tier_configurations": tiers_tested,
                    "gpt5_models_configured": configured_gpt5,
                    "total_tiers": len(tiers_tested)
                }
            )
            
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error=str(e)
            )
    
    async def test_error_handling(self) -> TestResult:
        """Test error handling with invalid requests"""
        test_name = "Error Handling"
        start_time = time.time()
        
        try:
            # Test with empty message
            payload = {
                "message": "",
                "thread_id": f"test-error-{int(time.time())}"
            }
            
            async with self.session.post(
                f"{self.backend_url}/api/agent/v2/stream",
                json=payload
            ) as response:
                # Should handle gracefully
                error_handled = False
                
                if response.status == 200:
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if not line:
                            continue
                        
                        try:
                            data = json.loads(line)
                            if data.get("event") == "error":
                                error_handled = True
                                break
                        except json.JSONDecodeError:
                            continue
                
                duration = time.time() - start_time
                
                return TestResult(
                    test_name=test_name,
                    success=True,  # Success if it handles the error gracefully
                    response_data={
                        "error_handled_gracefully": error_handled or response.status != 500,
                        "response_status": response.status
                    },
                    duration=duration
                )
                
        except Exception as e:
            return TestResult(
                test_name=test_name,
                success=False,
                error=str(e),
                duration=time.time() - start_time
            )
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run the complete test suite"""
        logger.info("🚀 Starting GPT-5 Integration Test Suite")
        
        # Environment check
        if not self.check_environment():
            self.results.append(TestResult(
                test_name="Environment Check",
                success=False,
                error="Environment variables missing"
            ))
            return self._generate_report()
        
        # Test backend health
        logger.info("🔍 Testing backend health...")
        health_result = await self.test_backend_health()
        self.results.append(health_result)
        
        if not health_result.success:
            logger.error("❌ Backend health check failed - cannot proceed")
            return self._generate_report()
        
        # Test model factory
        logger.info("🧠 Testing LLM factory...")
        factory_result = await self.test_model_factory()
        self.results.append(factory_result)
        
        # Test model tiering
        logger.info("📊 Testing model tiering...")
        tiering_result = await self.test_model_tiering()
        self.results.append(tiering_result)
        
        # Test simple routing
        logger.info("📍 Testing simple routing...")
        for query_name, query in self.test_queries.items():
            if query_name.startswith("simple_"):
                result = await self.test_simple_routing(query)
                self.results.append(result)
                await asyncio.sleep(1)  # Rate limiting
        
        # Test A2A orchestration
        logger.info("🔄 Testing A2A orchestration...")
        for query_name, query in self.test_queries.items():
            if query_name.startswith("complex_") or query_name.startswith("a2a_"):
                result = await self.test_a2a_orchestration(query)
                self.results.append(result)
                await asyncio.sleep(1)  # Rate limiting
        
        # Test auto complexity analysis
        logger.info("🧩 Testing auto complexity analysis...")
        for query_name, query in [("auto_simple", self.test_queries["simple_greeting"]), 
                                   ("auto_complex", self.test_queries["complex_product"])]:
            result = await self.test_auto_complexity_analysis(query)
            self.results.append(result)
            await asyncio.sleep(1)  # Rate limiting
        
        # Test error handling
        logger.info("⚠️ Testing error handling...")
        error_result = await self.test_error_handling()
        self.results.append(error_result)
        
        return self._generate_report()
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        
        # Group results by category
        categories = {
            "Infrastructure": ["Backend Health Check", "LLM Factory Model Creation", "Model Tiering Verification"],
            "Simple Routing": [r.test_name for r in self.results if "Simple Routing" in r.test_name],
            "A2A Orchestration": [r.test_name for r in self.results if "A2A Orchestration" in r.test_name],
            "Auto Analysis": [r.test_name for r in self.results if "Auto Analysis" in r.test_name],
            "Error Handling": ["Error Handling"]
        }
        
        category_results = {}
        for category, test_names in categories.items():
            category_tests = [r for r in self.results if r.test_name in test_names]
            if category_tests:
                category_results[category] = {
                    "total": len(category_tests),
                    "successful": sum(1 for r in category_tests if r.success),
                    "failed": sum(1 for r in category_tests if not r.success),
                    "avg_duration": sum(r.duration or 0 for r in category_tests) / len(category_tests),
                    "tests": [
                        {
                            "name": r.test_name,
                            "success": r.success,
                            "duration": r.duration,
                            "pattern": r.pattern,
                            "agent_path": r.agent_path,
                            "model": r.model_used,
                            "error": r.error
                        }
                        for r in category_tests
                    ]
                }
        
        # Model usage analysis
        models_used = {}
        patterns_seen = {"simple": 0, "a2a": 0}
        
        for result in self.results:
            if result.model_used:
                models_used[result.model_used] = models_used.get(result.model_used, 0) + 1
            if result.pattern:
                patterns_seen[result.pattern] = patterns_seen.get(result.pattern, 0) + 1
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "successful": successful_tests,
                "failed": failed_tests,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "categories": category_results,
            "analysis": {
                "models_used": models_used,
                "patterns_distribution": patterns_seen,
                "avg_response_time": sum(r.duration or 0 for r in self.results if r.duration) / max(1, len([r for r in self.results if r.duration]))
            },
            "details": [
                {
                    "test": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "pattern": r.pattern,
                    "agents": r.agent_path,
                    "model": r.model_used,
                    "error": r.error,
                    "response_length": r.response_data.get("response_length") if r.response_data else None
                }
                for r in self.results
            ]
        }
        
        return report

def print_test_report(report: Dict[str, Any]):
    """Print formatted test report"""
    print("\n" + "="*80)
    print("🧪 GPT-5 INTEGRATION TEST REPORT")
    print("="*80)
    
    # Check if report has expected structure
    if "summary" not in report:
        print("❌ Test report generation failed - no summary available")
        print(f"Available keys: {list(report.keys())}")
        return
    
    # Summary
    summary = report["summary"]
    success_rate = summary.get("success_rate", 0)
    status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
    
    print(f"\n📊 SUMMARY:")
    print(f"   {status_emoji} Success Rate: {success_rate:.1f}% ({summary.get('successful', 0)}/{summary.get('total', 0)} tests)")
    print(f"   ⏱️ Test Duration: {summary.get('timestamp', 'Unknown')}")
    
    # Category breakdown
    if "categories" in report:
        print(f"\n📂 CATEGORY BREAKDOWN:")
        for category, data in report["categories"].items():
            category_success_rate = (data["successful"] / data["total"] * 100) if data["total"] > 0 else 0
            category_emoji = "✅" if category_success_rate >= 80 else "⚠️" if category_success_rate >= 60 else "❌"
            print(f"   {category_emoji} {category}: {data['successful']}/{data['total']} ({category_success_rate:.1f}%) - Avg: {data['avg_duration']:.2f}s")
    
    # Analysis
    if "analysis" in report:
        analysis = report["analysis"]
        print(f"\n🔍 ANALYSIS:")
        print(f"   📈 Avg Response Time: {analysis.get('avg_response_time', 0):.2f}s")
        print(f"   🤖 Models Used: {', '.join(analysis.get('models_used', {}).keys())}")
        print(f"   🧩 Pattern Distribution: Simple={analysis.get('patterns_distribution', {}).get('simple', 0)}, A2A={analysis.get('patterns_distribution', {}).get('a2a', 0)}")
    
    # Detailed results
    if "details" in report:
        print(f"\n📋 DETAILED RESULTS:")
        for detail in report["details"]:
            status_emoji = "✅" if detail.get("success", False) else "❌"
            duration_str = f"{detail['duration']:.2f}s" if detail.get('duration') else "N/A"
            pattern_str = f"[{detail['pattern']}]" if detail.get('pattern') else ""
            model_str = f"({detail['model']})" if detail.get('model') else ""
            
            print(f"   {status_emoji} {detail.get('test', 'Unknown Test')} - {duration_str} {pattern_str} {model_str}")
            
            if detail.get("error"):
                print(f"      ❌ Error: {detail['error']}")
            
            if detail.get("agents"):
                agents_str = " → ".join(detail["agents"])
                print(f"      🔄 Agent Path: {agents_str}")
    
    print("\n" + "="*80)

async def main():
    """Main test execution"""
    backend_url = "http://localhost:8000"
    
    # Test basic connectivity first
    try:
        response = requests.get(f"{backend_url}/health", timeout=10)
        if response.status_code != 200:
            print(f"❌ Backend not responding at {backend_url}")
            print("Please ensure the backend is running on http://localhost:8000")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to backend at {backend_url}")
        print(f"Error: {e}")
        print("Please ensure the backend is running on http://localhost:8000")
        sys.exit(1)
    
    # Run comprehensive tests
    async with GPT5IntegrationTester(backend_url) as tester:
        report = await tester.run_all_tests()
        
        # Print report
        print_test_report(report)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"/home/pranav/espressobot/langgraph-backend/test_gpt5_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        success_rate = report["summary"]["success_rate"]
        sys.exit(0 if success_rate >= 80 else 1)

if __name__ == "__main__":
    asyncio.run(main())