import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { authenticateToken } from './auth.js';

const prisma = new PrismaClient();
const router = Router();

/**
 * @swagger
 * /api/tasks/{taskId}/status:
 *   patch:
 *     summary: Update the status of a task
 *     description: Allows a sub-agent to update the status of a specific task (e.g., from 'in_progress' to 'completed').
 *     tags: [Tasks]
 *     security:
 *       - bearerAuth: []
 *     parameters:
 *       - in: path
 *         name: taskId
 *         required: true
 *         schema:
 *           type: string
 *         description: The ID of the task to update.
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               status:
 *                 type: string
 *                 description: The new status for the task.
 *                 example: 'completed'
 *     responses:
 *       200:
 *         description: Task status updated successfully.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Task'
 *       400:
 *         description: Bad request, status is required.
 *       404:
 *         description: Task not found.
 *       500:
 *         description: Internal server error.
 */
router.patch('/:taskId/status', authenticateToken, async (req, res) => {
  const { taskId } = req.params;
  const { status } = req.body;

  if (!status) {
    return res.status(400).json({ error: 'Status is required' });
  }

  try {
    const updatedTask = await prisma.task.update({
      where: { id: taskId },
      data: { status },
    });
    res.json(updatedTask);
  } catch (error) {
    // Prisma's P2025 code indicates that the record was not found
    if (error.code === 'P2025') {
      return res.status(404).json({ error: 'Task not found' });
    }
    console.error('Error updating task status:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

export default router;