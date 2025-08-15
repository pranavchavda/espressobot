import { PrismaClient } from '@prisma/client';

/**
 * Centralized Prisma client configuration with PostgreSQL optimizations
 * Fixes connection pool exhaustion and timeout issues
 */

let prisma;
let connectionAttempts = 0;
const MAX_CONNECTION_ATTEMPTS = 3;

export function getPrismaClient() {
  if (!prisma && connectionAttempts < MAX_CONNECTION_ATTEMPTS) {
    connectionAttempts++;
    console.log(`[Database] Prisma client initialization attempt ${connectionAttempts}/${MAX_CONNECTION_ATTEMPTS}`);
    
    try {
      // Build enhanced DATABASE_URL with connection pool parameters
      const baseUrl = process.env.DATABASE_URL;
      if (!baseUrl) {
        throw new Error('DATABASE_URL environment variable is required');
      }
      
      const enhancedUrl = baseUrl.includes('?') 
        ? `${baseUrl}&connection_limit=10&pool_timeout=60&connect_timeout=30&idle_timeout=600&max_idle_time=300`
        : `${baseUrl}?connection_limit=10&pool_timeout=60&connect_timeout=30&idle_timeout=600&max_idle_time=300`;

      prisma = new PrismaClient({
        log: ['error', 'warn'],
        datasources: {
          db: {
            url: enhancedUrl
          }
        }
      });

      // Handle process exit for cleanup
      process.on('beforeExit', async () => {
        console.log('[Database] Process exiting, disconnecting Prisma client...');
        await prisma?.$disconnect();
      });

      console.log('[Database] Prisma client initialized with PostgreSQL optimizations');
    } catch (error) {
      console.error(`[Database] Failed to create Prisma client (attempt ${connectionAttempts}):`, error.message);
      prisma = null;
      
      if (connectionAttempts >= MAX_CONNECTION_ATTEMPTS) {
        throw new Error(`Failed to initialize Prisma client after ${MAX_CONNECTION_ATTEMPTS} attempts`);
      }
    }
  }

  return prisma;
}

/**
 * Ensure database connection is established
 */
export async function ensureConnection() {
  const client = getPrismaClient();
  try {
    await client.$connect();
    console.log('[Database] Connection established successfully');
    return true;
  } catch (error) {
    console.error('[Database] Failed to establish connection:', error.message);
    return false;
  }
}

// Create singleton instance
export const db = getPrismaClient();

/**
 * Connection health monitoring
 */
let connectionMonitor = null;

export function startConnectionHealthMonitor() {
  if (connectionMonitor) return; // Already running
  
  console.log('[Database] Starting connection health monitor...');
  
  connectionMonitor = setInterval(async () => {
    try {
      const client = getPrismaClient();
      await client.$queryRaw`SELECT 1`;
      // Connection is healthy - no need to log success
    } catch (error) {
      console.error('[Database] Health check failed:', error.message);
      
      // More aggressive reconnection for "Closed" errors
      if (error.message.includes('Closed') || error.message.includes('kind: Closed')) {
        console.log('[Database] Detected closed connection, forcing full reconnection...');
        
        try {
          // Force complete disconnection
          await prisma?.$disconnect();
          prisma = null; // Force recreation of client
          
          // Wait longer for remote connection cleanup
          await new Promise(resolve => setTimeout(resolve, 3000));
          
          // Recreate client and connect
          const client = getPrismaClient();
          await client.$connect();
          console.log('[Database] Full reconnection successful');
        } catch (reconnectError) {
          console.error('[Database] Full reconnection failed:', reconnectError.message);
        }
      } else {
        // Standard reconnection for other errors
        try {
          const client = getPrismaClient();
          await client.$disconnect();
          await new Promise(resolve => setTimeout(resolve, 1000));
          await client.$connect();
          console.log('[Database] Standard reconnection successful');
        } catch (reconnectError) {
          console.error('[Database] Standard reconnection failed:', reconnectError.message);
        }
      }
    }
  }, 20000); // Check every 20 seconds (more frequent)
}

export function stopConnectionHealthMonitor() {
  if (connectionMonitor) {
    clearInterval(connectionMonitor);
    connectionMonitor = null;
    console.log('[Database] Connection health monitor stopped');
  }
}

// Export for backward compatibility
export default db;

/**
 * Gracefully disconnect from database
 */
export async function disconnectDatabase() {
  if (prisma) {
    await prisma.$disconnect();
    prisma = null;
    console.log('[Database] Disconnected from PostgreSQL');
  }
}

/**
 * Test database connection with retry logic
 */
export async function testConnection(retries = 3) {
  const client = getPrismaClient();
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      await client.$queryRaw`SELECT 1`;
      console.log('[Database] Connection test successful');
      return true;
    } catch (error) {
      console.error(`[Database] Connection test failed (attempt ${attempt}/${retries}):`, error.message);
      
      if (attempt < retries) {
        const delay = attempt * 1000; // Exponential backoff
        console.log(`[Database] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }
  
  console.error('[Database] All connection attempts failed');
  return false;
}

/**
 * Handle connection errors and retry
 */
export async function withRetry(operation, retries = 3) {
  const client = getPrismaClient();
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      // Ensure connection is established before operation
      if (!client) {
        throw new Error('Prisma client not available');
      }
      
      // Force connection establishment
      await client.$connect();
      
      // Verify connection with a simple query
      await client.$queryRaw`SELECT 1`;
      
      return await operation(client);
    } catch (error) {
      console.error(`[Database] Operation failed (attempt ${attempt}/${retries}):`, error.message);
      
      // Check if it's a connection error
      const isConnectionError = 
        error.message.includes('Connection') ||
        error.message.includes('timeout') ||
        error.message.includes('ECONNRESET') ||
        error.message.includes('ECONNREFUSED') ||
        error.message.includes('Engine is not yet connected') ||
        error.message.includes('Closed') ||  // Add Closed connection error
        error.message.includes('kind: Closed') ||  // Specific PostgreSQL closed error
        error.code === 'P1001' || // Connection error
        error.code === 'P1008' || // Connection timeout
        error.code === 'P1017';   // Server closed connection
      
      if (isConnectionError && attempt < retries) {
        const delay = attempt * 2000; // Exponential backoff
        console.log(`[Database] Connection error, retrying in ${delay}ms...`);
        
        // Handle "Closed" errors with full client recreation
        if (error.message.includes('Closed') || error.message.includes('kind: Closed')) {
          console.log('[Database] Closed connection detected, recreating client...');
          try {
            await client.$disconnect();
            prisma = null; // Force recreation
            await new Promise(resolve => setTimeout(resolve, 2000));
            // getPrismaClient() will create a new client
            const newClient = getPrismaClient();
            await newClient.$connect();
          } catch (connectError) {
            console.warn('[Database] Full reconnection attempt failed:', connectError.message);
          }
        } else {
          // Standard reconnection for other errors
          try {
            await client.$disconnect();
            await new Promise(resolve => setTimeout(resolve, 1000));
            await client.$connect();
          } catch (connectError) {
            console.warn('[Database] Standard reconnection attempt failed:', connectError.message);
          }
        }
        
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      throw error;
    }
  }
}