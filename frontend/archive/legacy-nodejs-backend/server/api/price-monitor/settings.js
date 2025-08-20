import express from 'express';
import { db } from '../../config/database.js';

const prisma = db;

const router = express.Router();

// Get monitored brands
router.get('/monitored-brands', async (req, res) => {
  try {
    const brands = await prisma.monitored_brands.findMany({
      include: {
        _count: {
          select: {
            idc_products: true
          }
        }
      },
      orderBy: { brand_name: 'asc' }
    });
    
    res.json({ brands });
  } catch (error) {
    console.error('Error fetching monitored brands:', error);
    res.status(500).json({ error: 'Failed to fetch monitored brands' });
  }
});

// Create monitored brand
router.post('/monitored-brands', async (req, res) => {
  try {
    const { brand_name, is_active = true } = req.body;
    
    if (!brand_name) {
      return res.status(400).json({ error: 'Brand name is required' });
    }
    
    // Check if brand already exists
    const existingBrand = await prisma.monitored_brands.findUnique({
      where: { brand_name }
    });
    
    if (existingBrand) {
      return res.status(409).json({ error: 'Brand already exists' });
    }
    
    const brand = await prisma.monitored_brands.create({
      data: { 
        brand_name, 
        is_active,
        updated_at: new Date()
      }
    });
    
    res.status(201).json(brand);
  } catch (error) {
    console.error('Error creating monitored brand:', error);
    res.status(500).json({ error: 'Failed to create monitored brand' });
  }
});

// Toggle monitored brand status
router.put('/monitored-brands/:id/toggle', async (req, res) => {
  try {
    const { id } = req.params;
    const { is_active } = req.body;
    
    const brand = await prisma.monitored_brands.findUnique({
      where: { id }
    });
    
    if (!brand) {
      return res.status(404).json({ error: 'Brand not found' });
    }
    
    const updatedBrand = await prisma.monitored_brands.update({
      where: { id },
      data: { is_active }
    });
    
    res.json(updatedBrand);
  } catch (error) {
    console.error('Error toggling brand status:', error);
    res.status(500).json({ error: 'Failed to toggle brand status' });
  }
});

// Delete monitored brand
router.delete('/monitored-brands/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const brand = await prisma.monitored_brands.findUnique({
      where: { id }
    });
    
    if (!brand) {
      return res.status(404).json({ error: 'Brand not found' });
    }
    
    await prisma.monitored_brands.delete({
      where: { id }
    });
    
    res.json({ message: 'Brand deleted successfully' });
  } catch (error) {
    console.error('Error deleting brand:', error);
    res.status(500).json({ error: 'Failed to delete brand' });
  }
});

// Get monitored collections
router.get('/monitored-collections', async (req, res) => {
  try {
    const collections = await prisma.monitored_collections.findMany({
      orderBy: { collection_name: 'asc' }
    });
    
    res.json({ collections });
  } catch (error) {
    console.error('Error fetching monitored collections:', error);
    res.status(500).json({ error: 'Failed to fetch monitored collections' });
  }
});

// Create monitored collection
router.post('/monitored-collections', async (req, res) => {
  try {
    const { collection_name, is_active = true } = req.body;
    
    if (!collection_name) {
      return res.status(400).json({ error: 'Collection name is required' });
    }
    
    // Check if collection already exists
    const existingCollection = await prisma.monitored_collections.findUnique({
      where: { collection_name }
    });
    
    if (existingCollection) {
      return res.status(409).json({ error: 'Collection already exists' });
    }
    
    const collection = await prisma.monitored_collections.create({
      data: { 
        collection_name, 
        is_active,
        updated_at: new Date()
      }
    });
    
    res.status(201).json(collection);
  } catch (error) {
    console.error('Error creating monitored collection:', error);
    res.status(500).json({ error: 'Failed to create monitored collection' });
  }
});

// Toggle monitored collection status
router.post('/monitored-collections/:id/toggle', async (req, res) => {
  try {
    const { id } = req.params;
    
    const collection = await prisma.monitored_collections.findUnique({
      where: { id }
    });
    
    if (!collection) {
      return res.status(404).json({ error: 'Collection not found' });
    }
    
    const updatedCollection = await prisma.monitored_collections.update({
      where: { id },
      data: { is_active: !collection.is_active }
    });
    
    res.json(updatedCollection);
  } catch (error) {
    console.error('Error toggling collection status:', error);
    res.status(500).json({ error: 'Failed to toggle collection status' });
  }
});

// Delete monitored collection
router.delete('/monitored-collections/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const collection = await prisma.monitored_collections.findUnique({
      where: { id }
    });
    
    if (!collection) {
      return res.status(404).json({ error: 'Collection not found' });
    }
    
    await prisma.monitored_collections.delete({
      where: { id }
    });
    
    res.json({ message: 'Collection deleted successfully' });
  } catch (error) {
    console.error('Error deleting collection:', error);
    res.status(500).json({ error: 'Failed to delete collection' });
  }
});

// System settings (stored in a simple key-value format using a settings table or JSON config)
// For now, we'll use a simple in-memory config with database fallback

const DEFAULT_SETTINGS = {
  confidence_threshold: 0.7,
  scraping_interval: 24,
  alert_thresholds: {
    map_violation: 0.05,
    price_change: 0.10
  },
  rate_limits: {
    requests_per_minute: 30,
    delay_between_requests: 2000
  }
};

// Get system settings
router.get('/system', async (req, res) => {
  try {
    // TODO: In a real implementation, you might want to store these in a settings table
    // For now, return default settings
    res.json(DEFAULT_SETTINGS);
  } catch (error) {
    console.error('Error fetching system settings:', error);
    res.status(500).json({ error: 'Failed to fetch system settings' });
  }
});

// Update system settings
router.post('/system', async (req, res) => {
  try {
    const {
      confidence_threshold,
      scraping_interval,
      alert_thresholds,
      rate_limits
    } = req.body;
    
    // Validate settings
    if (confidence_threshold && (confidence_threshold < 0.1 || confidence_threshold > 1)) {
      return res.status(400).json({ 
        error: 'Confidence threshold must be between 0.1 and 1' 
      });
    }
    
    if (scraping_interval && scraping_interval < 1) {
      return res.status(400).json({ 
        error: 'Scraping interval must be at least 1 hour' 
      });
    }
    
    // TODO: In a real implementation, save these to a settings table
    // For now, just return the updated settings
    const updatedSettings = {
      ...DEFAULT_SETTINGS,
      ...(confidence_threshold && { confidence_threshold }),
      ...(scraping_interval && { scraping_interval }),
      ...(alert_thresholds && { alert_thresholds: { ...DEFAULT_SETTINGS.alert_thresholds, ...alert_thresholds } }),
      ...(rate_limits && { rate_limits: { ...DEFAULT_SETTINGS.rate_limits, ...rate_limits } })
    };
    
    res.json({
      message: 'Settings updated successfully',
      settings: updatedSettings
    });
  } catch (error) {
    console.error('Error updating system settings:', error);
    res.status(500).json({ error: 'Failed to update system settings' });
  }
});

export default router;