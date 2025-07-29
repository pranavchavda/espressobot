import express from 'express';
import prisma from '../../lib/prisma.js';
import { randomUUID } from 'crypto';

const router = express.Router();

// Get all competitors
router.get('/', async (req, res) => {
  try {
    const { search, status } = req.query;
    
    const where = {};
    
    if (search) {
      where.OR = [
        { name: { contains: search, mode: 'insensitive' } },
        { domain: { contains: search, mode: 'insensitive' } }
      ];
    }
    
    if (status === 'active') {
      where.is_active = true;
    } else if (status === 'inactive') {
      where.is_active = false;
    }
    
    const competitors = await prisma.competitors.findMany({
      where,
      include: {
        _count: {
          select: {
            competitor_products: true,
            scrape_jobs: true
          }
        }
      },
      orderBy: { created_at: 'desc' }
    });
    
    // Transform the data to include counts
    const formattedCompetitors = competitors.map(competitor => ({
      ...competitor,
      total_products: competitor._count.competitor_products,
      total_scrape_jobs: competitor._count.scrape_jobs
    }));
    
    res.json({
      competitors: formattedCompetitors,
      total: competitors.length
    });
  } catch (error) {
    console.error('Error fetching competitors:', error);
    res.status(500).json({ error: 'Failed to fetch competitors' });
  }
});

// Get all competitor products (for manual matching) - MUST come before /:id route
router.get('/products', async (req, res) => {
  try {
    const { limit = 500, search, competitor_id } = req.query;
    
    const where = {};
    
    if (search) {
      where.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { vendor: { contains: search, mode: 'insensitive' } },
        { sku: { contains: search, mode: 'insensitive' } }
      ];
    }
    
    if (competitor_id) {
      where.competitor_id = competitor_id;
    }
    
    const products = await prisma.competitor_products.findMany({
      where,
      include: {
        competitor: {
          select: {
            id: true,
            name: true,
            domain: true
          }
        }
      },
      take: parseInt(limit),
      orderBy: { scraped_at: 'desc' }
    });
    
    res.json({
      products,
      total: products.length
    });
  } catch (error) {
    console.error('Error fetching competitor products:', error);
    res.status(500).json({ error: 'Failed to fetch competitor products' });
  }
});

// Get a single competitor by ID
router.get('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    const competitor = await prisma.competitors.findUnique({
      where: { id },
      include: {
        competitor_products: {
          // No limit - show all competitor products
          orderBy: { scraped_at: 'desc' }
        },
        scrape_jobs: {
          // No limit - show all scrape jobs
          orderBy: { created_at: 'desc' }
        },
        _count: {
          select: {
            competitor_products: true,
            scrape_jobs: true
          }
        }
      }
    });
    
    if (!competitor) {
      return res.status(404).json({ error: 'Competitor not found' });
    }
    
    res.json({
      ...competitor,
      total_products: competitor._count.competitor_products,
      total_scrape_jobs: competitor._count.scrape_jobs
    });
  } catch (error) {
    console.error('Error fetching competitor:', error);
    res.status(500).json({ error: 'Failed to fetch competitor' });
  }
});

// Create a new competitor
router.post('/', async (req, res) => {
  try {
    console.log('Creating competitor with data:', req.body);
    const { 
      name, 
      domain, 
      collections = [], 
      scraping_strategy = 'collections',
      url_patterns = [],
      search_terms = [],
      exclude_patterns = [],
      is_active = true, 
      scrape_schedule,
      rate_limit_ms = 2000 
    } = req.body;
    
    // Validate required fields
    if (!name || !domain) {
      return res.status(400).json({ 
        error: 'Name and domain are required' 
      });
    }
    
    // Check if domain already exists
    const existingCompetitor = await prisma.competitors.findUnique({
      where: { domain }
    });
    
    if (existingCompetitor) {
      return res.status(409).json({ 
        error: 'A competitor with this domain already exists' 
      });
    }
    
    console.log('Creating competitor in database...');
    const competitor = await prisma.competitors.create({
      data: {
        name,
        domain,
        collections,
        scraping_strategy,
        url_patterns,
        search_terms,
        exclude_patterns,
        is_active,
        scrape_schedule,
        rate_limit_ms,
        updated_at: new Date()
      }
    });
    
    console.log('Competitor created successfully:', competitor);
    res.status(201).json(competitor);
  } catch (error) {
    console.error('Error creating competitor:', error);
    res.status(500).json({ error: 'Failed to create competitor' });
  }
});

// Update a competitor
router.put('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { 
      name, 
      domain, 
      collections, 
      scraping_strategy,
      url_patterns,
      search_terms,
      exclude_patterns,
      is_active, 
      scrape_schedule,
      rate_limit_ms 
    } = req.body;
    
    // Check if competitor exists
    const existingCompetitor = await prisma.competitors.findUnique({
      where: { id }
    });
    
    if (!existingCompetitor) {
      return res.status(404).json({ error: 'Competitor not found' });
    }
    
    // If domain is being changed, check if new domain already exists
    if (domain && domain !== existingCompetitor.domain) {
      const domainExists = await prisma.competitors.findUnique({
        where: { domain }
      });
      
      if (domainExists) {
        return res.status(409).json({ 
          error: 'A competitor with this domain already exists' 
        });
      }
    }
    
    const updatedCompetitor = await prisma.competitors.update({
      where: { id },
      data: {
        name,
        domain,
        collections,
        scraping_strategy,
        url_patterns,
        search_terms,
        exclude_patterns,
        is_active,
        scrape_schedule,
        rate_limit_ms
      }
    });
    
    res.json(updatedCompetitor);
  } catch (error) {
    console.error('Error updating competitor:', error);
    res.status(500).json({ error: 'Failed to update competitor' });
  }
});

// Delete a competitor
router.delete('/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    // Check if competitor exists
    const existingCompetitor = await prisma.competitors.findUnique({
      where: { id }
    });
    
    if (!existingCompetitor) {
      return res.status(404).json({ error: 'Competitor not found' });
    }
    
    // Delete competitor (this will cascade delete related records)
    await prisma.competitors.delete({
      where: { id }
    });
    
    res.json({ message: 'Competitor deleted successfully' });
  } catch (error) {
    console.error('Error deleting competitor:', error);
    res.status(500).json({ error: 'Failed to delete competitor' });
  }
});

// Toggle competitor active status
router.post('/:id/toggle', async (req, res) => {
  try {
    const { id } = req.params;
    
    const competitor = await prisma.competitors.findUnique({
      where: { id }
    });
    
    if (!competitor) {
      return res.status(404).json({ error: 'Competitor not found' });
    }
    
    const updatedCompetitor = await prisma.competitors.update({
      where: { id },
      data: { is_active: !competitor.is_active }
    });
    
    res.json(updatedCompetitor);
  } catch (error) {
    console.error('Error toggling competitor status:', error);
    res.status(500).json({ error: 'Failed to toggle competitor status' });
  }
});

// Start scraping for a specific competitor
router.post('/:id/scrape', async (req, res) => {
  try {
    const { id } = req.params;
    const { collections } = req.body;
    
    const competitor = await prisma.competitors.findUnique({
      where: { id }
    });
    
    if (!competitor) {
      return res.status(404).json({ error: 'Competitor not found' });
    }
    
    if (!competitor.is_active) {
      return res.status(400).json({ error: 'Competitor is not active' });
    }
    
    // Create a scrape job
    const scrapeJob = await prisma.scrape_jobs.create({
      data: {
        id: randomUUID(),
        competitor_id: id,
        collections: collections || competitor.collections,
        status: 'pending',
        updated_at: new Date()
      }
    });
    
    // TODO: Trigger actual scraping process here
    // This would typically be handled by a background job queue
    
    res.json({
      message: 'Scraping job queued successfully',
      job: scrapeJob
    });
  } catch (error) {
    console.error('Error starting scrape job:', error);
    res.status(500).json({ error: 'Failed to start scraping' });
  }
});

// Get scrape jobs for a competitor
router.get('/:id/scrape-jobs', async (req, res) => {
  try {
    const { id } = req.params;
    const { limit = 20, status } = req.query;
    
    const where = { competitor_id: id };
    if (status) {
      where.status = status;
    }
    
    const scrapeJobs = await prisma.scrape_jobs.findMany({
      where,
      take: parseInt(limit),
      orderBy: { created_at: 'desc' }
    });
    
    res.json({ scrape_jobs: scrapeJobs });
  } catch (error) {
    console.error('Error fetching scrape jobs:', error);
    res.status(500).json({ error: 'Failed to fetch scrape jobs' });
  }
});

export default router;