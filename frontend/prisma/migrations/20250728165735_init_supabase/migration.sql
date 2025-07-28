-- CreateTable
CREATE TABLE "alembic_version" (
    "version_num" TEXT NOT NULL,

    CONSTRAINT "alembic_version_pkey" PRIMARY KEY ("version_num")
);

-- CreateTable
CREATE TABLE "conversations" (
    "id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "title" TEXT NOT NULL,
    "topic_title" TEXT,
    "topic_details" TEXT,
    "created_at" TIMESTAMP(3),
    "updated_at" TIMESTAMP(3),
    "filename" TEXT NOT NULL,

    CONSTRAINT "conversations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "embedding_cache" (
    "id" SERIAL NOT NULL,
    "text_hash" TEXT NOT NULL,
    "text_content" TEXT NOT NULL,
    "embedding_data" BYTEA NOT NULL,
    "model_name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3),
    "last_accessed" TIMESTAMP(3),

    CONSTRAINT "embedding_cache_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "messages" (
    "id" SERIAL NOT NULL,
    "conv_id" INTEGER NOT NULL,
    "role" TEXT,
    "content" TEXT NOT NULL,
    "original_content" TEXT,
    "tool_call_id" TEXT,
    "tool_name" TEXT,
    "created_at" TIMESTAMP(3),
    "edited_at" TIMESTAMP(3),

    CONSTRAINT "messages_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_memories" (
    "id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "key" TEXT NOT NULL,
    "value" TEXT NOT NULL,
    "created_at" TIMESTAMP(3),
    "updated_at" TIMESTAMP(3),

    CONSTRAINT "user_memories_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "user_memory_embeddings" (
    "id" SERIAL NOT NULL,
    "user_id" INTEGER NOT NULL,
    "memory_key" TEXT NOT NULL,
    "embedding_cache_id" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3),

    CONSTRAINT "user_memory_embeddings_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" SERIAL NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT,
    "name" TEXT,
    "bio" TEXT,
    "is_whitelisted" BOOLEAN NOT NULL DEFAULT true,
    "is_admin" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3),
    "google_id" TEXT,
    "profile_picture" TEXT,
    "google_access_token" TEXT,
    "google_refresh_token" TEXT,
    "google_token_expiry" TIMESTAMP(3),
    "ga4_property_id" TEXT DEFAULT '325181275',
    "ga4_enabled" BOOLEAN NOT NULL DEFAULT true,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_runs" (
    "id" SERIAL NOT NULL,
    "conv_id" INTEGER NOT NULL,
    "tasks" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "agent_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "conversation_summaries" (
    "id" SERIAL NOT NULL,
    "conv_id" INTEGER NOT NULL,
    "summary" TEXT NOT NULL,
    "start_msg_index" INTEGER NOT NULL,
    "end_msg_index" INTEGER NOT NULL,
    "chunk_number" INTEGER NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "conversation_summaries_pkey" PRIMARY KEY ("id")
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

-- CreateIndex
CREATE UNIQUE INDEX "idx_users_google_id" ON "users"("google_id");

-- CreateIndex
CREATE INDEX "conversation_summaries_conv_id_chunk_number_idx" ON "conversation_summaries"("conv_id", "chunk_number");

-- AddForeignKey
ALTER TABLE "conversations" ADD CONSTRAINT "conversations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "messages" ADD CONSTRAINT "messages_conv_id_fkey" FOREIGN KEY ("conv_id") REFERENCES "conversations"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "user_memories" ADD CONSTRAINT "user_memories_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "user_memory_embeddings" ADD CONSTRAINT "user_memory_embeddings_embedding_cache_id_fkey" FOREIGN KEY ("embedding_cache_id") REFERENCES "embedding_cache"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "user_memory_embeddings" ADD CONSTRAINT "user_memory_embeddings_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "agent_runs" ADD CONSTRAINT "agent_runs_conv_id_fkey" FOREIGN KEY ("conv_id") REFERENCES "conversations"("id") ON DELETE NO ACTION ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "conversation_summaries" ADD CONSTRAINT "conversation_summaries_conv_id_fkey" FOREIGN KEY ("conv_id") REFERENCES "conversations"("id") ON DELETE NO ACTION ON UPDATE CASCADE;
