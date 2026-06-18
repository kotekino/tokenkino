import { Router, Request, Response, NextFunction } from 'express';
import { ContactMessage } from '../models/ContactMessage';
import { createError } from '../middleware/errorHandler';

const router = Router();

// POST /api/contact - Submit contact form
router.post('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { name, email, message } = req.body;

    if (!name || !email || !message) {
      return next(createError('Name, email and message are required', 400));
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return next(createError('Invalid email address', 400));
    }

    if (message.trim().length < 10) {
      return next(createError('Message must be at least 10 characters', 400));
    }

    const contact = await ContactMessage.create({ name, email, message });

    res.status(201).json({
      success: true,
      message: 'Your message has been received. We will get back to you soon.',
      data: { id: contact._id },
    });
  } catch (error) {
    next(error);
  }
});

// GET /api/contact - List messages (protected in production - add auth middleware)
router.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const messages = await ContactMessage.find()
      .sort({ createdAt: -1 })
      .limit(50)
      .select('-__v');

    res.json({ success: true, data: messages, count: messages.length });
  } catch (error) {
    next(error);
  }
});

export default router;
