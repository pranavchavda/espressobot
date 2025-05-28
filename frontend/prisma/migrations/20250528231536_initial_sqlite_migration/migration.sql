-- CreateTable
CREATE TABLE "User" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "name" TEXT,
    "bio" TEXT,
    "is_whitelisted" BOOLEAN NOT NULL DEFAULT false,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "Conversation" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL,
    "filename" TEXT NOT NULL,
    CONSTRAINT "Conversation_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Message" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "conv_id" INTEGER NOT NULL,
    "role" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "tool_call_id" TEXT,
    "tool_name" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Message_conv_id_fkey" FOREIGN KEY ("conv_id") REFERENCES "Conversation" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "UserMemory" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" INTEGER NOT NULL,
    "key" TEXT NOT NULL,
    "value" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL,
    CONSTRAINT "UserMemory_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "EmbeddingCache" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "text_hash" TEXT NOT NULL,
    "text_content" TEXT NOT NULL,
    "embedding_data" BLOB NOT NULL,
    "model_name" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_accessed" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "UserMemoryEmbedding" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" INTEGER NOT NULL,
    "memory_key" TEXT NOT NULL,
    "embedding_cache_id" INTEGER NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "UserMemoryEmbedding_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "UserMemoryEmbedding_embedding_cache_id_fkey" FOREIGN KEY ("embedding_cache_id") REFERENCES "EmbeddingCache" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- CreateIndex
CREATE INDEX "User_email_idx" ON "User"("email");

-- CreateIndex
CREATE UNIQUE INDEX "Conversation_filename_key" ON "Conversation"("filename");

-- CreateIndex
CREATE INDEX "Conversation_user_id_idx" ON "Conversation"("user_id");

-- CreateIndex
CREATE INDEX "Message_conv_id_idx" ON "Message"("conv_id");

-- CreateIndex
CREATE INDEX "UserMemory_user_id_idx" ON "UserMemory"("user_id");

-- CreateIndex
CREATE UNIQUE INDEX "UserMemory_user_id_key_key" ON "UserMemory"("user_id", "key");

-- CreateIndex
CREATE UNIQUE INDEX "EmbeddingCache_text_hash_key" ON "EmbeddingCache"("text_hash");

-- CreateIndex
CREATE INDEX "EmbeddingCache_text_hash_idx" ON "EmbeddingCache"("text_hash");

-- CreateIndex
CREATE INDEX "UserMemoryEmbedding_user_id_idx" ON "UserMemoryEmbedding"("user_id");

-- CreateIndex
CREATE INDEX "UserMemoryEmbedding_embedding_cache_id_idx" ON "UserMemoryEmbedding"("embedding_cache_id");

-- CreateIndex
CREATE UNIQUE INDEX "UserMemoryEmbedding_user_id_memory_key_key" ON "UserMemoryEmbedding"("user_id", "memory_key");
