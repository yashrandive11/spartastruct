const express = require('express');
const userRoutes = require('./routes/users');

const app = express();
app.use(express.json());
app.use('/users', userRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});

module.exports = app;
