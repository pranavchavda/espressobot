import express from 'express';
import competitorsRouter from './competitors.js';
import dashboardRouter from './dashboard.js';
import settingsRouter from './settings.js';
import shopifySyncRouter from './shopify-sync.js';
import shopifySyncSafeRouter from './shopify-sync-safe.js';
import scrapingEngineRouter from './scraping-engine.js';
import productMatchingRouter from './product-matching.js';
import intelligentMatchingRouter from './intelligent-matching.js';
import mapViolationsRouter from './map-violations.js';
import alertsRouter from './alerts.js';
import violationHistoryRouter from './violation-history.js';
import jobStatusRouter from './job-status.js';

const router = express.Router();

// Mount sub-routers
router.use('/competitors', competitorsRouter);
router.use('/dashboard', dashboardRouter);
router.use('/settings', settingsRouter);
router.use('/shopify-sync', shopifySyncRouter);
router.use('/shopify-sync-safe', shopifySyncSafeRouter);
router.use('/scraping', scrapingEngineRouter);
router.use('/product-matching', productMatchingRouter);
router.use('/intelligent-matching', intelligentMatchingRouter);
router.use('/map-violations', mapViolationsRouter);
router.use('/alerts', alertsRouter);
router.use('/violation-history', violationHistoryRouter);
router.use('/job-status', jobStatusRouter);

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'price-monitor',
    timestamp: new Date().toISOString()
  });
});

export default router;