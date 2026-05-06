const express = require('express');
const router = express.Router();
const UserService = require('../services/UserService');

router.get('/', async (req, res) => {
  const users = await UserService.getAll();
  res.json(users);
});

router.get('/:id', async (req, res) => {
  const user = await UserService.getById(req.params.id);
  res.json(user);
});

router.post('/', async (req, res) => {
  const user = await UserService.create(req.body);
  res.status(201).json(user);
});

router.delete('/:id', async (req, res) => {
  await UserService.delete(req.params.id);
  res.status(204).send();
});

module.exports = router;
