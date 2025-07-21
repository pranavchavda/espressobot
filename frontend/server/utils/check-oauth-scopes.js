/**
 * Check OAuth Scopes Utility
 * Helps determine if a user has authorized all required scopes
 */

import { google } from 'googleapis';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

/**
 * Check if user has authorized the Google Analytics scope
 */
export async function checkAnalyticsScope(userId) {
  try {
    const user = await prisma.users.findUnique({
      where: { id: userId },
      select: { 
        google_access_token: true,
        google_refresh_token: true
      }
    });

    if (!user?.google_access_token) {
      return { hasScope: false, reason: 'No Google authentication' };
    }

    // Create OAuth2 client
    const oauth2Client = new google.auth.OAuth2(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET
    );

    oauth2Client.setCredentials({
      access_token: user.google_access_token,
      refresh_token: user.google_refresh_token
    });

    // Get token info to check scopes
    try {
      const tokenInfo = await oauth2Client.getTokenInfo(user.google_access_token);
      const scopes = tokenInfo.scopes || [];
      
      const hasAnalyticsScope = scopes.includes('https://www.googleapis.com/auth/analytics.readonly');
      
      return {
        hasScope: hasAnalyticsScope,
        scopes: scopes,
        reason: hasAnalyticsScope ? null : 'Analytics scope not authorized'
      };
    } catch (error) {
      // Token might be expired or invalid
      return {
        hasScope: false,
        reason: 'Token validation failed',
        error: error.message
      };
    }
  } catch (error) {
    console.error('Error checking OAuth scopes:', error);
    return {
      hasScope: false,
      reason: 'Error checking scopes',
      error: error.message
    };
  }
}

/**
 * Get re-authorization URL for missing scopes
 */
export function getReauthorizationUrl() {
  const baseUrl = process.env.GOOGLE_CALLBACK_URL?.replace('/callback', '') || '/api/auth/google';
  // Add a parameter to indicate re-authorization
  return `${baseUrl}?reauth=1`;
}