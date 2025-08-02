import express from 'express';
import competitorsRouter from './competitors.js';
import dashboardRouter from './dashboard.js';
import settingsRouter from './settings.js';
import shopifySyncRouter from './shopify-sync.js';
import scrapingEngineRouter from './scraping-engine.js';
import productMatchingRouter from './product-matching.js';
import intelligentMatchingRouter from './intelligent-matching.js';
import mapViolationsRouter from './map-violations.js';
import alertsRouter from './alerts.js';

const router = express.Router();

// Mount sub-routers
router.use('/competitors', competitorsRouter);
router.use('/dashboard', dashboardRouter);
router.use('/settings', settingsRouter);
router.use('/shopify-sync', shopifySyncRouter);
router.use('/scraping', scrapingEngineRouter);
router.use('/product-matching', productMatchingRouter);
router.use('/intelligent-matching', intelligentMatchingRouter);
router.use('/map-violations', mapViolationsRouter);
router.use('/alerts', alertsRouter);

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'price-monitor',
    timestamp: new Date().toISOString()
  });
});

export default router;