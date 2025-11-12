const express = require('express');
const router = express.Router();
const multer = require('multer');
const coreController = require('../controllers/coreController');

const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

const mapLabelsUpload = upload.fields([
    { name: 'fastaFile', maxCount: 1 },
    { name: 'predictionsFile', maxCount: 1 }
]);

router.post('/run', upload.single('fastaFile'), coreController.run);
router.post('/map-labels', mapLabelsUpload, coreController.mapLabels);

module.exports = router;