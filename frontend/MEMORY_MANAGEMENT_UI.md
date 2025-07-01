# Memory Management UI

## Overview
The Memory Management UI provides admin users (specifically pranav@idrinkcoffee.com) with the ability to view, search, edit, and delete memories stored in the EspressoBot system.

## Features

### 1. **Access Control**
- Only visible to users with email `pranav@idrinkcoffee.com`
- Memory button appears in the top navigation bar for admin users
- All API endpoints are protected with admin authorization

### 2. **Memory Operations**
- **View All Memories**: Display all memories with pagination (default 500)
- **Search**: Semantic search using embeddings to find relevant memories
- **Filter by User**: View memories for specific users or all users
- **Edit**: Update memory content (automatically re-generates embeddings)
- **Delete**: Remove individual memories or all memories for a user
- **Statistics**: View total memory count and breakdown by user

### 3. **UI Components**
- **MemoryManagementModal**: Main modal interface
- **Search Bar**: Real-time search with 300ms debounce
- **User Filter**: Dropdown to filter by user ID
- **Memory List**: Scrollable list with inline editing
- **Badges**: Display memory ID, user ID, relevance score

## API Endpoints

All endpoints require authentication and admin authorization:

- `GET /api/memory/all` - Get all memories with optional user filter
- `GET /api/memory/search?q=query` - Search memories semantically
- `GET /api/memory/stats` - Get memory statistics
- `GET /api/memory/users` - Get list of users with memory counts
- `PUT /api/memory/:id` - Update a memory
- `DELETE /api/memory/:id` - Delete a memory
- `DELETE /api/memory/user/:userId` - Delete all memories for a user

## Implementation Details

### Backend
- **Storage**: SQLite database with embeddings
- **Search**: Cosine similarity with OpenAI embeddings
- **Authorization**: Middleware checks for admin email

### Frontend
- **React Components**: Using existing UI component library
- **State Management**: Local React state with hooks
- **Real-time Updates**: Refresh on edit/delete operations

## Usage

1. Login as pranav@idrinkcoffee.com
2. Click the "Memory" button in the top navigation
3. Use the search bar to find specific memories
4. Filter by user if needed
5. Click edit icon to modify memory content
6. Click delete icon to remove memories

## Security
- JWT authentication required
- Admin email verification on every request
- No direct database access from frontend