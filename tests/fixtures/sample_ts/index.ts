import express from 'express';
import { UserService } from './services/UserService';

const app = express();
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.listen(3000);
export default app;
