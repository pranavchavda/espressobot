-- CreateTable
CREATE TABLE "alembic_version" (
    "version_num" TEXT NOT NULL PRIMARY KEY
);

-- CreateTable
CREATE TABLE "conversations" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    "filename" TEXT NOT NULL,
    CONSTRAINT "conversations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);

-- CreateTable
CREATE TABLE "embedding_cache" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "text_hash" TEXT NOT NULL,
    "text_content" TEXT NOT NULL,
    "embedding_data" BLOB NOT NULL,
    "model_name" TEXT NOT NULL,
    "created_at" DATETIME,
    "last_accessed" DATETIME
);

-- CreateTable
CREATE TABLE "messages" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "conv_id" INTEGER NOT NULL,
    "role" TEXT,
    "content" TEXT NOT NULL,
    "tool_call_id" TEXT,
    "tool_name" TEXT,
    "created_at" DATETIME,
    CONSTRAINT "messages_conv_id_fkey" FOREIGN KEY ("conv_id") REFERENCES "conversations" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);

-- CreateTable
CREATE TABLE "user_memories" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" INTEGER NOT NULL,
    "key" TEXT NOT NULL,
    "value" TEXT NOT NULL,
    "created_at" DATETIME,
    "updated_at" DATETIME,
    CONSTRAINT "user_memories_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);

-- CreateTable
CREATE TABLE "user_memory_embeddings" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_id" INTEGER NOT NULL,
    "memory_key" TEXT NOT NULL,
    "embedding_cache_id" INTEGER NOT NULL,
    "created_at" DATETIME,
    CONSTRAINT "user_memory_embeddings_embedding_cache_id_fkey" FOREIGN KEY ("embedding_cache_id") REFERENCES "embedding_cache" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT "user_memory_embeddings_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);

-- CreateTable
CREATE TABLE "users" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "name" TEXT,
    "bio" TEXT,
    "is_whitelisted" BOOLEAN NOT NULL,
    "created_at" DATETIME
);

-- CreateIndex
CREATE UNIQUE INDEX "conversations_filename_key" ON "conversations"("filename");

-- CreateIndex
CREATE UNIQUE INDEX "ix_embedding_cache_text_hash" ON "embedding_cache"("text_hash");

-- CreateIndex
CREATE UNIQUE INDEX "unique_user_memory_key" ON "user_memories"("user_id", "key");

-- CreateIndex
CREATE UNIQUE INDEX "unique_user_memory_embedding" ON "user_memory_embeddings"("user_id", "memory_key");

-- CreateIndex
CREATE UNIQUE INDEX "ix_users_email" ON "users"("email");
