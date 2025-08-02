import express from 'express';
import { db } from '../../config/database.js';
import { nanoid } from 'nanoid';

const prisma = db;
const router = express.Router();

// Record a job execution
router.post('/record', async (req, res) => {
  try {
    const { job_type, status = 'completed', details = {} } = req.body;
    
    const jobLog = await prisma.job_execution_log.create({
      data: {
        id: nanoid(),
        job_type,
        status,
        details,
        executed_at: new Date(),
        created_at: new Date()
      }
    });
    
    res.json({ 
      message: 'Job execution recorded',
      job_id: jobLog.id 
    });
  } catch (error) {
    console.error('Error recording job execution:', error);
    res.status(500).json({ error: 'Failed to record job execution' });
  }
});

// Get last execution times for each job type
router.get('/last-runs', async (req, res) => {
  try {
    // Get all job types
    const jobTypes = ['shopify_sync', 'competitor_scrape', 'violation_scan', 'cron_job'];
    const lastRunsByType = {};
    
    // Get the most recent execution for each job type
    for (const jobType of jobTypes) {
      const lastRun = await prisma.job_execution_log.findFirst({
        where: { job_type: jobType },
        orderBy: { executed_at: 'desc' }
      });
      
      if (lastRun) {
        lastRunsByType[jobType] = {
          status: lastRun.status,
          executed_at: lastRun.executed_at,
          details: lastRun.details
        };
      }
    }
    
    // Also get counts for today
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const todayExecutions = await prisma.job_execution_log.findMany({
      where: {
        executed_at: { gte: today }
      }
    });
    
    // Count by job type
    const todayCountsByType = {};
    todayExecutions.forEach(execution => {
      if (!todayCountsByType[execution.job_type]) {
        todayCountsByType[execution.job_type] = 0;
      }
      todayCountsByType[execution.job_type]++;
    });
    
    // Add today's counts to response
    Object.keys(todayCountsByType).forEach(jobType => {
      if (lastRunsByType[jobType]) {
        lastRunsByType[jobType].runs_today = todayCountsByType[jobType];
      }
    });
    
    res.json(lastRunsByType);
  } catch (error) {
    console.error('Error fetching last runs:', error);
    res.status(500).json({ error: 'Failed to fetch last runs' });
  }
});

// Get job history for a specific type
router.get('/history/:jobType', async (req, res) => {
  try {
    const { jobType } = req.params;
    const { limit = 50 } = req.query;
    
    const history = await prisma.job_execution_log.findMany({
      where: { job_type: jobType },
      orderBy: { executed_at: 'desc' },
      take: parseInt(limit)
    });
    
    res.json(history);
  } catch (error) {
    console.error('Error fetching job history:', error);
    res.status(500).json({ error: 'Failed to fetch job history' });
  }
});

export default router;