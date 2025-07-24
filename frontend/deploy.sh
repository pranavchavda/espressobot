#!/bin/bash

# EspressoBot Production Deployment Script

set -e  # Exit on any error

echo "🚀 Starting EspressoBot production deployment..."

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Run this script from the frontend directory."
    exit 1
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production not found. Copy .env.production.example and configure it."
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pnpm install --prod

# Run database migrations (if using Prisma)
if [ -f "prisma/schema.prisma" ]; then
    echo "🗄️ Running database migrations..."
    pnpm prisma migrate deploy
    pnpm prisma generate
fi

# Build the frontend
echo "🏗️ Building frontend..."
pnpm run build:prod

# Create required directories
mkdir -p logs
mkdir -p data/plans

# Set permissions
chmod +x server-production.js

# Check if PM2 is available
if command -v pm2 &> /dev/null; then
    echo "🔄 Using PM2 for process management..."
    
    # Stop existing process if running
    pm2 stop espressobot 2>/dev/null || true
    pm2 delete espressobot 2>/dev/null || true
    
    # Start with PM2
    pm2 start server-production.js --name espressobot --env production
    pm2 save
    
    echo "✅ EspressoBot deployed successfully with PM2!"
    echo "📊 View logs: pm2 logs espressobot"
    echo "🔄 Restart: pm2 restart espressobot"
    echo "⏹️ Stop: pm2 stop espressobot"
    
else
    echo "⚠️ PM2 not found. Starting with node..."
    echo "🔧 For production, install PM2: npm install -g pm2"
    
    # Start with node (development mode)
    NODE_ENV=production node server-production.js &
    echo $! > espressobot.pid
    
    echo "✅ EspressoBot started successfully!"
    echo "📝 Process ID saved to espressobot.pid"
    echo "⏹️ Stop: kill \$(cat espressobot.pid)"
fi

echo ""
echo "🌐 Application should be running on port 3000"
echo "🏥 Health check: curl http://localhost:3000/health"
echo "📋 Configure nginx to proxy requests to localhost:3000"