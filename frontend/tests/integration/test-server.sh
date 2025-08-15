#!/bin/bash
# Test script to run server and capture logs

echo "Starting server with logging..."
export USE_MULTI_AGENT=true
npm run dev 2>&1 | tee server.log