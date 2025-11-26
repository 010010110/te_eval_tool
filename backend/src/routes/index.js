const express = require('express');
const router = express.Router();

const coreRoutes = require('./coreRoutes');


router.use('/', coreRoutes);

module.exports = router;