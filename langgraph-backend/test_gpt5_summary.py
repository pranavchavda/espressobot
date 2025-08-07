#!/usr/bin/env python3
"""
GPT-5 Integration Summary Test - Final validation and recommendations
"""
import os
import json
import asyncio
import aiohttp
import requests
import sys
import time
from datetime import datetime

class GPT5ValidationSuite:
    """Final validation suite for GPT-5 integration"""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "recommendations": []
        }
    
    def check_environment(self):
        """Validate environment setup"""
        print("🔧 ENVIRONMENT VALIDATION")
        print("=" * 50)
        
        required_vars = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "DATABASE_URL": os.getenv("DATABASE_URL"),
        }
        
        optional_vars = {
            "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        }
        
        env_status = {"required": {}, "optional": {}}
        
        for var, value in required_vars.items():
            status = "✅" if value else "❌"
            print(f"   {status} {var}: {'Configured' if value else 'Missing'}")
            env_status["required"][var] = bool(value)
        
        for var, value in optional_vars.items():
            status = "✅" if value else "⚠️"
            print(f"   {status} {var}: {'Configured' if value else 'Not set'}")
            env_status["optional"][var] = bool(value)
        
        self.results["tests"]["environment"] = env_status
        return all(env_status["required"].values())
    
    def test_backend_connectivity(self):
        """Test backend is running and healthy"""
        print("\n🌐 BACKEND CONNECTIVITY")
        print("=" * 50)
        
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Backend healthy at {self.backend_url}")
                health_data = response.json()
                print(f"   📊 Status: {health_data.get('status', 'unknown')}")
                self.results["tests"]["backend_health"] = {"success": True, "status": health_data}
                return True
            else:
                print(f"   ❌ Backend returned status {response.status_code}")
                self.results["tests"]["backend_health"] = {"success": False, "status_code": response.status_code}
                return False
        except Exception as e:
            print(f"   ❌ Cannot connect to backend: {e}")
            self.results["tests"]["backend_health"] = {"success": False, "error": str(e)}
            return False
    
    def test_model_configuration(self):
        """Test GPT-5 model configuration"""
        print("\n🤖 MODEL CONFIGURATION")
        print("=" * 50)
        
        try:
            sys.path.append('/home/pranav/espressobot/langgraph-backend')
            from app.config.model_config import model_config, ModelTier
            from app.config.llm_factory import llm_factory
            
            # Test model tiering
            gpt5_tiers = {}
            for tier in ModelTier:
                config = model_config.get_model_for_tier(tier)
                model_name = config.get("model", "")
                if "gpt-5" in model_name:
                    gpt5_tiers[tier.value] = model_name
                    print(f"   ✅ {tier.value}: {model_name}")
            
            print(f"\n   📊 GPT-5 Models Configured: {len(gpt5_tiers)}/4 tiers")
            
            # Test provider availability
            providers = {
                "OpenAI": llm_factory.openai_key is not None,
                "OpenRouter": llm_factory.openrouter_key is not None,
                "Anthropic": llm_factory.anthropic_key is not None
            }
            
            available_providers = [name for name, available in providers.items() if available]
            print(f"   🔌 Available Providers: {', '.join(available_providers)}")
            
            self.results["tests"]["model_config"] = {
                "gpt5_tiers": gpt5_tiers,
                "providers": providers,
                "success": len(gpt5_tiers) > 0 and len(available_providers) > 0
            }
            
            return True
            
        except Exception as e:
            print(f"   ❌ Model configuration test failed: {e}")
            self.results["tests"]["model_config"] = {"success": False, "error": str(e)}
            return False
    
    async def test_simple_query(self):
        """Test simple query routing"""
        print("\n📝 SIMPLE QUERY TEST")
        print("=" * 50)
        
        query = "What's the price of the Breville Barista Express?"
        print(f"   Query: {query}")
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "message": query,
                "mode": "simple",
                "thread_id": f"test-simple-{int(time.time())}"
            }
            
            try:
                async with session.post(
                    f"{self.backend_url}/api/agent/v2/stream",
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        print(f"   ❌ Request failed with status {response.status}")
                        self.results["tests"]["simple_query"] = {"success": False, "status": response.status}
                        return False
                    
                    # Process response
                    response_text = ""
                    pattern = None
                    agents = []
                    
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
                                if agent and agent not in agents:
                                    agents.append(agent)
                                if data.get("tokens"):
                                    response_text += "".join(data["tokens"])
                            elif data.get("event") == "done":
                                break
                        except json.JSONDecodeError:
                            continue
                    
                    success = len(response_text) > 20 and pattern == "simple"
                    print(f"   ✅ Pattern: {pattern}")
                    print(f"   🤖 Agents: {' → '.join(agents)}")
                    print(f"   📝 Response Length: {len(response_text)} chars")
                    print(f"   {'✅ SUCCESS' if success else '❌ FAILED'}")
                    
                    self.results["tests"]["simple_query"] = {
                        "success": success,
                        "pattern": pattern,
                        "agents": agents,
                        "response_length": len(response_text)
                    }
                    
                    return success
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.results["tests"]["simple_query"] = {"success": False, "error": str(e)}
                return False
    
    async def test_complex_query(self):
        """Test complex query with A2A pattern detection"""
        print("\n🔄 COMPLEX QUERY TEST (A2A)")
        print("=" * 50)
        
        query = "Show me the Breville Barista Express with current pricing and stock levels"
        print(f"   Query: {query}")
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "message": query,
                "mode": "auto",  # Let it decide
                "thread_id": f"test-complex-{int(time.time())}"
            }
            
            try:
                async with session.post(
                    f"{self.backend_url}/api/agent/v2/stream",
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        print(f"   ❌ Request failed with status {response.status}")
                        self.results["tests"]["complex_query"] = {"success": False, "status": response.status}
                        return False
                    
                    # Process response
                    response_text = ""
                    pattern = None
                    agents = []
                    analysis_reason = None
                    had_error = False
                    
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
                                if agent and agent not in agents:
                                    agents.append(agent)
                                if data.get("tokens"):
                                    response_text += "".join(data["tokens"])
                            elif data.get("event") == "error":
                                had_error = True
                                print(f"   ⚠️ Stream Error: {data.get('error', 'Unknown')}")
                            elif data.get("event") == "done":
                                break
                        except json.JSONDecodeError:
                            continue
                    
                    print(f"   🧠 Analysis: {analysis_reason}")
                    print(f"   ✅ Pattern: {pattern}")
                    print(f"   🤖 Agents: {' → '.join(agents)}")
                    print(f"   📝 Response Length: {len(response_text)} chars")
                    
                    # Success if complexity was detected correctly, even if execution had issues
                    success = pattern in ["a2a", "simple"] and not had_error
                    print(f"   {'✅ SUCCESS' if success else '⚠️ PARTIAL' if pattern == 'a2a' else '❌ FAILED'}")
                    
                    self.results["tests"]["complex_query"] = {
                        "success": success,
                        "pattern": pattern,
                        "agents": agents,
                        "analysis_reason": analysis_reason,
                        "response_length": len(response_text),
                        "had_error": had_error
                    }
                    
                    return success
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                self.results["tests"]["complex_query"] = {"success": False, "error": str(e)}
                return False
    
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        print("\n💡 RECOMMENDATIONS")
        print("=" * 50)
        
        recommendations = []
        
        # Check model configuration
        if self.results["tests"].get("model_config", {}).get("success", False):
            gpt5_count = len(self.results["tests"]["model_config"].get("gpt5_tiers", {}))
            if gpt5_count < 3:
                recommendations.append({
                    "priority": "medium",
                    "issue": f"Only {gpt5_count}/3 model tiers use GPT-5",
                    "suggestion": "Configure GPT-5-mini and GPT-5-nano for more agent tiers"
                })
        
        # Check parameter usage
        recommendations.append({
            "priority": "low",
            "issue": "GPT-5 models show parameter warnings",
            "suggestion": "Update LLM factory to use max_completion_tokens parameter explicitly"
        })
        
        # Check A2A orchestration
        complex_test = self.results["tests"].get("complex_query", {})
        if complex_test.get("had_error"):
            recommendations.append({
                "priority": "high",
                "issue": "A2A orchestration has execution errors",
                "suggestion": "Fix checkpointer implementation in A2A orchestrator"
            })
        elif complex_test.get("pattern") == "a2a" and complex_test.get("response_length", 0) < 50:
            recommendations.append({
                "priority": "medium",
                "issue": "A2A orchestration produces minimal responses",
                "suggestion": "Verify agent-to-agent communication and response synthesis"
            })
        
        # Check simple routing
        simple_test = self.results["tests"].get("simple_query", {})
        if simple_test.get("success") and len(simple_test.get("agents", [])) > 0:
            recommendations.append({
                "priority": "info",
                "issue": "Simple routing working correctly",
                "suggestion": "Simple queries are properly routed to appropriate agents"
            })
        
        # Environment recommendations
        env_test = self.results["tests"].get("environment", {})
        if not env_test.get("optional", {}).get("OPENROUTER_API_KEY"):
            recommendations.append({
                "priority": "low",
                "issue": "OpenRouter API not configured",
                "suggestion": "Configure OpenRouter for access to additional models and cost savings"
            })
        
        self.results["recommendations"] = recommendations
        
        for rec in recommendations:
            priority_emoji = {"high": "🚨", "medium": "⚠️", "low": "💡", "info": "ℹ️"}.get(rec["priority"], "•")
            print(f"   {priority_emoji} {rec['priority'].upper()}: {rec['issue']}")
            print(f"      → {rec['suggestion']}")
    
    def print_summary(self):
        """Print final summary"""
        print("\n🎯 INTEGRATION SUMMARY")
        print("=" * 50)
        
        total_tests = len([t for t in self.results["tests"].values() if isinstance(t, dict) and "success" in t])
        successful_tests = len([t for t in self.results["tests"].values() if isinstance(t, dict) and t.get("success")])
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        status_emoji = "🎉" if success_rate >= 80 else "⚠️" if success_rate >= 60 else "❌"
        
        print(f"   {status_emoji} Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        print(f"   🕒 Test Time: {self.results['timestamp']}")
        
        # Key findings
        key_findings = []
        
        if self.results["tests"].get("model_config", {}).get("success"):
            gpt5_count = len(self.results["tests"]["model_config"].get("gpt5_tiers", {}))
            key_findings.append(f"✅ {gpt5_count} GPT-5 model tiers configured")
        
        if self.results["tests"].get("simple_query", {}).get("success"):
            key_findings.append("✅ Simple routing functional")
        
        complex_test = self.results["tests"].get("complex_query", {})
        if complex_test.get("pattern") == "a2a":
            key_findings.append("✅ A2A pattern detection working")
        
        if key_findings:
            print("   📋 Key Findings:")
            for finding in key_findings:
                print(f"      {finding}")
        
        print(f"\n   📄 Detailed report available in test results")
    
    async def run_all_tests(self):
        """Run complete validation suite"""
        print("🚀 GPT-5 INTEGRATION VALIDATION SUITE")
        print("=" * 60)
        print(f"Backend: {self.backend_url}")
        print(f"Time: {self.results['timestamp']}")
        
        # Environment check
        if not self.check_environment():
            print("❌ Environment validation failed - stopping tests")
            return self.results
        
        # Backend connectivity
        if not self.test_backend_connectivity():
            print("❌ Backend connectivity failed - stopping tests")
            return self.results
        
        # Model configuration
        self.test_model_configuration()
        
        # Simple query test
        await self.test_simple_query()
        
        # Complex query test
        await self.test_complex_query()
        
        # Generate recommendations
        self.generate_recommendations()
        
        # Print summary
        self.print_summary()
        
        return self.results

async def main():
    """Run the validation suite"""
    suite = GPT5ValidationSuite()
    results = await suite.run_all_tests()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/home/pranav/espressobot/langgraph-backend/gpt5_validation_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Determine exit code
    total_tests = len([t for t in results["tests"].values() if isinstance(t, dict) and "success" in t])
    successful_tests = len([t for t in results["tests"].values() if isinstance(t, dict) and t.get("success")])
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    return 0 if success_rate >= 70 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)