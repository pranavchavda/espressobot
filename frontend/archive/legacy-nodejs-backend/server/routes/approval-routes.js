import express from 'express';
import { approveOperation, rejectOperation } from '../tools/approval-tool.js';

const router = express.Router();

/**
 * Approve an operation
 */
router.post('/api/agent/approve', async (req, res) => {
  try {
    const { approval_id } = req.body;
    
    if (!approval_id) {
      return res.status(400).json({ 
        success: false, 
        message: 'Approval ID is required' 
      });
    }
    
    const result = approveOperation(approval_id);
    
    if (result) {
      res.json({ 
        success: true, 
        message: 'Operation approved',
        approval_id 
      });
    } else {
      res.status(404).json({ 
        success: false, 
        message: 'Approval not found or already processed' 
      });
    }
  } catch (error) {
    console.error('Error approving operation:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Internal server error' 
    });
  }
});

/**
 * Reject an operation
 */
router.post('/api/agent/reject', async (req, res) => {
  try {
    const { approval_id } = req.body;
    
    if (!approval_id) {
      return res.status(400).json({ 
        success: false, 
        message: 'Approval ID is required' 
      });
    }
    
    const result = rejectOperation(approval_id);
    
    if (result) {
      res.json({ 
        success: true, 
        message: 'Operation rejected',
        approval_id 
      });
    } else {
      res.status(404).json({ 
        success: false, 
        message: 'Approval not found or already processed' 
      });
    }
  } catch (error) {
    console.error('Error rejecting operation:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Internal server error' 
    });
  }
});

export default router;