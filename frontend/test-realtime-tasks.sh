#!/bin/bash

echo "Testing real-time task updates with multi-agent system..."
echo ""
echo "This test will:"
echo "1. Send a request that creates a task plan"
echo "2. Show real-time task updates as agents work"
echo "3. Display task completion status"
echo ""
echo "Sending request..."
echo ""

curl -N -X POST http://localhost:5173/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a task plan to search for the top 3 espresso machines and update their descriptions",
    "conv_id": null,
    "forceTaskGen": false,
    "image": null
  }' 2>/dev/null | while IFS= read -r line; do
    if [[ $line == event:* ]]; then
        event_name=${line#event: }
        if [[ $event_name == "task_update" ]]; then
            echo -e "\n📋 TASK UPDATE:"
        else
            echo -e "\n📩 Event: $event_name"
        fi
    elif [[ $line == data:* ]]; then
        data=${line#data: }
        
        # Parse task updates specially
        if echo "$data" | grep -q '"tasks":\['; then
            # Extract task info
            echo "$data" | jq -r '.tasks[] | "   [\(.status)] \(.id): \(.description)"' 2>/dev/null || echo "   $data"
            
            # Show counts
            if echo "$data" | grep -q '"totalCount"'; then
                total=$(echo "$data" | jq -r '.totalCount' 2>/dev/null)
                completed=$(echo "$data" | jq -r '.completedCount' 2>/dev/null)
                inProgress=$(echo "$data" | jq -r '.inProgressCount' 2>/dev/null)
                echo "   📊 Progress: $completed/$total completed, $inProgress in progress"
            fi
        else
            # Show other event data
            if echo "$data" | grep -q '"message"'; then
                message=$(echo "$data" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
                if [ ! -z "$message" ]; then
                    echo "   📌 $message"
                fi
            fi
            if echo "$data" | grep -q '"agent"'; then
                agent=$(echo "$data" | grep -o '"agent":"[^"]*"' | cut -d'"' -f4)
                if [ ! -z "$agent" ]; then
                    echo "   👤 Agent: $agent"
                fi
            fi
        fi
    fi
done

echo -e "\n✅ Test completed"