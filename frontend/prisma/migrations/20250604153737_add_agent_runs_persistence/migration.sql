-- CreateTable
CREATE TABLE "agent_runs" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "conv_id" INTEGER NOT NULL,
    "tasks" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "agent_runs_conv_id_fkey" FOREIGN KEY ("conv_id") REFERENCES "conversations" ("id") ON DELETE NO ACTION ON UPDATE CASCADE
);
