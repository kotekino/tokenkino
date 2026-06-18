import { Router, Request, Response, NextFunction } from 'express';
import { CookieConsent } from '../models/CookieConsent';
import { createError } from '../middleware/errorHandler';

const router = Router();

// POST /api/cookie-consent - Record or update consent
router.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { sessionId, analytics, marketing } = req.body;

    if (!sessionId) {
      return next(createError('sessionId is required', 400));
    }

    const ipAddress = (req.headers['x-forwarded-for'] as string)?.split(',')[0] || req.ip;
    const userAgent = req.headers['user-agent'];

    const consent = await CookieConsent.findOneAndUpdate(
      { sessionId },
      {
        sessionId,
        necessary: true,
        analytics: Boolean(analytics),
        marketing: Boolean(marketing),
        ipAddress,
        userAgent,
      },
      { upsert: true, new: true, setDefaultsOnInsert: true }
    );

    res.status(200).json({
      success: true,
      message: 'Consent recorded',
      data: {
        sessionId: consent.sessionId,
        necessary: consent.necessary,
        analytics: consent.analytics,
        marketing: consent.marketing,
        consentedAt: consent.consentedAt,
      },
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/cookie-consent/:sessionId - Retrieve consent for session
router.get('/:sessionId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { sessionId } = req.params;
    const consent = await CookieConsent.findOne({ sessionId }).select('-ipAddress -__v');

    if (!consent) {
      return res.status(404).json({ success: false, message: 'No consent record found' });
    }

    res.json({ success: true, data: consent });
  } catch (error) {
    next(error);
  }
});

export default router;
