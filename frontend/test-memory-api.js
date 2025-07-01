// Test script for memory management API endpoints
import fetch from 'node-fetch';

const BASE_URL = 'http://localhost:5173';

// You'll need to get a valid token by logging in as pranav@idrinkcoffee.com
// For testing, you can use the browser's Network tab to copy the token after logging in
const AUTH_TOKEN = 'YOUR_AUTH_TOKEN_HERE';

async function testMemoryAPI() {
  console.log('Testing Memory Management API...\n');

  const headers = {
    'Authorization': `Bearer ${AUTH_TOKEN}`,
    'Content-Type': 'application/json'
  };

  try {
    // Test 1: Get all memories
    console.log('1. Testing GET /api/memory/all');
    const allMemoriesRes = await fetch(`${BASE_URL}/api/memory/all`, { headers });
    if (allMemoriesRes.ok) {
      const data = await allMemoriesRes.json();
      console.log(`✅ Success: Found ${data.total} total memories`);
      console.log(`   Users with memories: ${data.stats.byUser.length}`);
    } else {
      console.log(`❌ Failed: ${allMemoriesRes.status} ${allMemoriesRes.statusText}`);
    }

    // Test 2: Get memory statistics
    console.log('\n2. Testing GET /api/memory/stats');
    const statsRes = await fetch(`${BASE_URL}/api/memory/stats`, { headers });
    if (statsRes.ok) {
      const stats = await statsRes.json();
      console.log(`✅ Success: Stats retrieved`);
      console.log(`   Total memories: ${stats.total}`);
      stats.byUser.forEach(u => {
        console.log(`   User ${u.user_id}: ${u.count} memories`);
      });
    } else {
      console.log(`❌ Failed: ${statsRes.status} ${statsRes.statusText}`);
    }

    // Test 3: Search memories
    console.log('\n3. Testing GET /api/memory/search');
    const searchRes = await fetch(`${BASE_URL}/api/memory/search?q=coffee`, { headers });
    if (searchRes.ok) {
      const data = await searchRes.json();
      console.log(`✅ Success: Found ${data.count} memories matching "coffee"`);
      if (data.memories.length > 0) {
        console.log(`   First result: "${data.memories[0].memory || data.memories[0].content}"...`);
      }
    } else {
      console.log(`❌ Failed: ${searchRes.status} ${searchRes.statusText}`);
    }

    // Test 4: Get users with memories
    console.log('\n4. Testing GET /api/memory/users');
    const usersRes = await fetch(`${BASE_URL}/api/memory/users`, { headers });
    if (usersRes.ok) {
      const data = await usersRes.json();
      console.log(`✅ Success: Found ${data.users.length} users with memories`);
      data.users.forEach(u => {
        console.log(`   ${u.userId}: ${u.memoryCount} memories`);
      });
    } else {
      console.log(`❌ Failed: ${usersRes.status} ${usersRes.statusText}`);
    }

  } catch (error) {
    console.error('Error testing API:', error);
  }
}

console.log(`
To test the Memory Management API:

1. Start the EspressoBot server (npm run dev)
2. Login as pranav@idrinkcoffee.com
3. Open browser DevTools > Network tab
4. Look for any API request and copy the Authorization header token
5. Replace YOUR_AUTH_TOKEN_HERE with the actual token
6. Run: node test-memory-api.js

Note: The API will return 403 Forbidden if you're not logged in as pranav@idrinkcoffee.com
`);

// Uncomment to run tests:
// testMemoryAPI();