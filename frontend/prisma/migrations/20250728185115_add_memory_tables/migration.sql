-- CreateTable
CREATE TABLE "memories" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "content" TEXT NOT NULL,
    "embedding" BYTEA,
    "metadata" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "memories_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "tool_result_cache" (
    "id" TEXT NOT NULL,
    "tool_name" TEXT NOT NULL,
    "input_hash" TEXT NOT NULL,
    "result" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_accessed" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "tool_result_cache_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "memories_user_id_idx" ON "memories"("user_id");

-- CreateIndex
CREATE INDEX "memories_created_at_idx" ON "memories"("created_at");

-- CreateIndex
CREATE UNIQUE INDEX "tool_result_cache_input_hash_key" ON "tool_result_cache"("input_hash");

-- CreateIndex
CREATE INDEX "tool_result_cache_tool_name_idx" ON "tool_result_cache"("tool_name");

-- CreateIndex
CREATE INDEX "tool_result_cache_created_at_idx" ON "tool_result_cache"("created_at");
