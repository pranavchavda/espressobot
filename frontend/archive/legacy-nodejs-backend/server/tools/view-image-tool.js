import { tool } from '@openai/agents';
import { z } from 'zod';

/**
 * Tool for viewing user-attached images
 */
export const viewImageTool = tool({
  name: 'view_image',
  description: 'View the image that the user has attached to their message (This tool is deprecated - images are now automatically visible in your conversation)',
  parameters: z.object({}),
  execute: async () => {
    // This tool is no longer needed since images are passed directly in the message content
    return 'Images are now automatically visible in the conversation. You should be able to see and analyze any images the user has attached without using this tool.';
  }
});