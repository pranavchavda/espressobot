#!/bin/bash

echo "Testing multi-agent status updates..."
echo ""
echo "Expected status sequence:"
echo "1. 🤔 Analyzing your request..."
echo "2. 🔍 Analyzing your request in detail..."
echo "3. 🧐 Determining the best approach..."
echo "4. 🧠 Checking conversation history..."
echo "5. 📝 Creating execution plan..."
echo "6. 🔎 Searching products..."
echo ""
echo "Sending request and listening for events..."
echo ""

curl -N -X POST http://localhost:5173/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Search for espresso machines and show me the top 3",
    "conv_id": null,
    "forceTaskGen": false,
    "image": null
  }' 2>/dev/null | while IFS= read -r line; do
    if [[ $line == event:* ]]; then
        event_name=${line#event: }
        echo -e "\n📩 Event: $event_name"
    elif [[ $line == data:* ]]; then
        data=${line#data: }
        # Try to parse and display status messages
        if echo "$data" | grep -q '"message"'; then
            message=$(echo "$data" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
            if [ ! -z "$message" ]; then
                echo "   📌 Status: $message"
            fi
        fi
        # Show agent names
        if echo "$data" | grep -q '"agent"'; then
            agent=$(echo "$data" | grep -o '"agent":"[^"]*"' | cut -d'"' -f4)
            if [ ! -z "$agent" ]; then
                echo "   👤 Agent: $agent"
            fi
        fi
    fi
done

echo -e "\n✅ Test completed"