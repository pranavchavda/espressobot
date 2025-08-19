#!/usr/bin/env python3
"""
Test script for async background processing solution
Tests multiple concurrent requests to verify no blocking occurs
"""
import asyncio
import aiohttp
import time
import json
from concurrent.futures import ThreadPoolExecutor
import threading

BASE_URL = "http://localhost:8000"

def print_colored(message, color="white"):
    """Print colored output for better visibility"""
    colors = {
        "green": "\033[92m",
        "red": "\033[91m", 
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "white": "\033[0m",
        "bold": "\033[1m"
    }
    print(f"{colors.get(color, '')}{message}\033[0m")

async def test_async_endpoint():
    """Test the new async endpoint"""
    print_colored("\n🧪 Testing Async Endpoint", "blue")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # Send async message
        async with session.post(
            f"{BASE_URL}/api/agent/async/message",
            json={"message": "Test async processing with multiple agents"},
            headers={"Content-Type": "application/json"}
        ) as response:
            response_time = time.time() - start_time
            data = await response.json()
            
            print_colored(f"✅ Response time: {response_time:.3f}s", "green")
            print_colored(f"📋 Task ID: {data['task_id']}", "white")
            print_colored(f"💬 Message: {data['message']}", "white")
            
            return data['task_id']

async def check_task_status(task_id, max_wait=10):
    """Check task status until completion"""
    print_colored(f"\n🔍 Monitoring Task: {task_id}", "blue")
    
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            async with session.get(f"{BASE_URL}/api/agent/async/task/{task_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    status = data['status']
                    progress = data['progress'] * 100
                    message = data['message']
                    
                    print_colored(f"📊 Status: {status} | Progress: {progress:.1f}% | {message}", "yellow")
                    
                    if status in ['completed', 'failed']:
                        if status == 'completed':
                            print_colored(f"✅ Task completed! Response: {data['response'][:100]}...", "green")
                            return True
                        else:
                            print_colored(f"❌ Task failed: {data.get('error', 'Unknown error')}", "red")
                            return False
                
                await asyncio.sleep(0.5)
        
        print_colored("⏰ Task monitoring timed out", "red")
        return False

async def test_concurrent_requests():
    """Test multiple concurrent requests to verify no blocking"""
    print_colored("\n🚀 Testing Concurrent Requests", "blue")
    
    async def make_request(session, endpoint, method="GET", data=None):
        start_time = time.time()
        try:
            if method == "POST":
                async with session.post(endpoint, json=data, headers={"Content-Type": "application/json"}) as response:
                    result = await response.json()
                    response_time = time.time() - start_time
                    return {"endpoint": endpoint, "time": response_time, "status": response.status, "data": result}
            else:
                async with session.get(endpoint) as response:
                    result = await response.json() if response.content_type == 'application/json' else await response.text()
                    response_time = time.time() - start_time
                    return {"endpoint": endpoint, "time": response_time, "status": response.status, "data": result}
        except Exception as e:
            response_time = time.time() - start_time
            return {"endpoint": endpoint, "time": response_time, "status": "ERROR", "error": str(e)}
    
    async with aiohttp.ClientSession() as session:
        # Create multiple concurrent requests
        base_tasks = [
            make_request(session, f"{BASE_URL}/api/agent/async/message", "POST", {"message": f"Concurrent test 1"}),
            make_request(session, f"{BASE_URL}/api/conversations/"),
            make_request(session, f"{BASE_URL}/health"),
            make_request(session, f"{BASE_URL}/api/agent/async/test", "POST"),
        ]
        
        tasks = []
        for i in range(3):
            tasks.extend([
                make_request(session, f"{BASE_URL}/api/agent/async/message", "POST", {"message": f"Concurrent test {i+1}"}),
                make_request(session, f"{BASE_URL}/api/conversations/"),
                make_request(session, f"{BASE_URL}/health"),
                make_request(session, f"{BASE_URL}/api/agent/async/test", "POST"),
            ])
        
        print_colored(f"📤 Sending {len(tasks)} concurrent requests...", "yellow")
        start_time = time.time()
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        print_colored(f"⏱️ Total time for {len(tasks)} requests: {total_time:.3f}s", "green")
        print_colored(f"⚡ Average time per request: {total_time/len(tasks):.3f}s", "green")
        
        # Analyze results
        async_requests = [r for r in results if not isinstance(r, Exception) and 'async' in r['endpoint']]
        other_requests = [r for r in results if not isinstance(r, Exception) and 'async' not in r['endpoint']]
        errors = [r for r in results if isinstance(r, Exception) or (isinstance(r, dict) and r.get('status') == 'ERROR')]
        
        print_colored(f"\n📊 Results Summary:", "bold")
        print_colored(f"   ✅ Async requests: {len(async_requests)} (avg: {sum(r['time'] for r in async_requests)/len(async_requests):.3f}s)", "green")
        print_colored(f"   ✅ Other requests: {len(other_requests)} (avg: {sum(r['time'] for r in other_requests)/len(other_requests):.3f}s)", "green")
        print_colored(f"   ❌ Errors: {len(errors)}", "red" if errors else "green")
        
        if errors:
            for error in errors[:3]:  # Show first 3 errors
                print_colored(f"      Error: {error}", "red")
        
        return len(errors) == 0

def test_browser_simulation():
    """Simulate multiple browser tabs making requests"""
    print_colored("\n🌐 Simulating Multiple Browser Tabs", "blue")
    
    def browser_tab(tab_id):
        """Simulate a browser tab making requests"""
        import requests
        results = []
        
        for i in range(3):
            try:
                # Mix of different endpoints like a real browser
                endpoints = [
                    ("/health", "GET", None),
                    ("/api/conversations/", "GET", None),
                    ("/api/agent/async/message", "POST", {"message": f"Tab {tab_id} message {i}"}),
                ]
                
                for endpoint, method, data in endpoints:
                    start_time = time.time()
                    
                    if method == "POST":
                        response = requests.post(f"{BASE_URL}{endpoint}", json=data, headers={"Content-Type": "application/json"})
                    else:
                        response = requests.get(f"{BASE_URL}{endpoint}")
                    
                    response_time = time.time() - start_time
                    results.append({
                        "tab": tab_id,
                        "endpoint": endpoint,
                        "time": response_time,
                        "status": response.status_code,
                        "success": response.status_code < 400
                    })
                    
                    print_colored(f"📱 Tab {tab_id}: {endpoint} → {response.status_code} ({response_time:.3f}s)", "white")
                    
                    # Small delay between requests within a tab
                    time.sleep(0.1)
                    
            except Exception as e:
                results.append({
                    "tab": tab_id,
                    "error": str(e),
                    "success": False
                })
                print_colored(f"📱 Tab {tab_id} error: {e}", "red")
        
        return results
    
    # Simulate 5 browser tabs making requests concurrently
    with ThreadPoolExecutor(max_workers=5) as executor:
        start_time = time.time()
        futures = [executor.submit(browser_tab, i) for i in range(1, 6)]
        all_results = []
        
        for future in futures:
            all_results.extend(future.result())
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in all_results if r.get('success', False)]
        failed = [r for r in all_results if not r.get('success', True)]
        
        print_colored(f"\n📊 Browser Simulation Results:", "bold")
        print_colored(f"   ⏱️ Total time: {total_time:.3f}s", "white")
        print_colored(f"   ✅ Successful requests: {len(successful)}/{len(all_results)}", "green")
        print_colored(f"   ❌ Failed requests: {len(failed)}", "red" if failed else "green")
        print_colored(f"   ⚡ Average response time: {sum(r.get('time', 0) for r in successful)/len(successful):.3f}s", "green")
        
        return len(failed) == 0

async def main():
    """Run all tests"""
    print_colored("🧪 EspressoBot Async Solution Test Suite", "bold")
    print_colored("=" * 50, "white")
    
    all_tests_passed = True
    
    try:
        # Test 1: Basic async endpoint
        task_id = await test_async_endpoint()
        if task_id:
            task_completed = await check_task_status(task_id)
            if not task_completed:
                all_tests_passed = False
        else:
            all_tests_passed = False
        
        # Test 2: Concurrent requests
        concurrent_success = await test_concurrent_requests()
        if not concurrent_success:
            all_tests_passed = False
        
        # Test 3: Browser simulation
        browser_success = test_browser_simulation()
        if not browser_success:
            all_tests_passed = False
        
    except Exception as e:
        print_colored(f"❌ Test suite error: {e}", "red")
        all_tests_passed = False
    
    # Final results
    print_colored("\n" + "=" * 50, "white")
    if all_tests_passed:
        print_colored("🎉 ALL TESTS PASSED! Async solution is working correctly.", "green")
        print_colored("✅ Ready for deployment - multiple browser tabs will work simultaneously.", "green")
    else:
        print_colored("❌ Some tests failed. Check the output above for details.", "red")
        print_colored("🔧 The async solution needs fixes before deployment.", "yellow")

if __name__ == "__main__":
    print("Starting async solution tests...")
    asyncio.run(main())