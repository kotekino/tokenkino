import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';

import { connectDB } from './config/database';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import healthRouter from './routes/health';
import mindRouter from './routes/mind';
import transmissionsRouter from './routes/transmissions';
import growthRouter from './routes/growth';
import discoveryRouter from './routes/discovery';

const app = express();
const PORT = process.env.PORT || 4000;

// ─── Security Middleware ────────────────────────────────────────────────────
app.use(helmet());

// CORS_ORIGIN may be a comma-separated list (e.g. the *.azurewebsites.net URL
// AND the custom domain). Requests with no Origin (curl, the brain's push,
// same-origin) are allowed through.
const allowedOrigins = (process.env.CORS_ORIGIN || 'http://localhost:3000')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);
app.use(
  cors({
    origin(origin, cb) {
      if (!origin || allowedOrigins.includes(origin)) return cb(null, true);
      cb(new Error('Not allowed by CORS'));
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key'],
  })
);

// ─── Rate Limiting ──────────────────────────────────────────────────────────
const limiter = rateLimit({
  windowMs: Number(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000, // 15 minutes
  max: Number(process.env.RATE_LIMIT_MAX) || 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { success: false, message: 'Too many requests, please try again later.' },
});
app.use('/api/', limiter);

// ─── Body Parsing ───────────────────────────────────────────────────────────
// Mind snapshots + transmission bodies can be a few KB; allow generous headroom.
app.use(express.json({ limit: process.env.JSON_LIMIT || '128kb' }));
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// ─── Logging ────────────────────────────────────────────────────────────────
if (process.env.NODE_ENV !== 'test') {
  app.use(morgan(process.env.NODE_ENV === 'production' ? 'combined' : 'dev'));
}

// ─── Routes ─────────────────────────────────────────────────────────────────
app.use('/api/health', healthRouter);
app.use('/api/mind', mindRouter);
app.use('/api/transmissions', transmissionsRouter);
app.use('/api/growth', growthRouter);
app.use('/api', discoveryRouter);

// ─── 404 & Error Handlers ───────────────────────────────────────────────────
app.use(notFoundHandler);
app.use(errorHandler);

// ─── Start ───────────────────────────────────────────────────────────────────
const start = () => {
  connectDB(); // non-blocking: connects + retries in the background
  app.listen(PORT, () => {
    console.log(`🚀 Server running on http://localhost:${PORT}`);
    console.log(`📡 Environment: ${process.env.NODE_ENV || 'development'}`);
  });
};

try {
  start();
} catch (err) {
  console.error('Failed to start server:', err);
  process.exit(1);
}

export default app;
