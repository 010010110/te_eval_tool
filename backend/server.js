const express = require('express');
const dotenv = require('dotenv');
const cors = require('cors');
const path = require('path');
const swaggerUi = require('swagger-ui-express');
const YAML = require('yamljs');

dotenv.config({ path: path.join(__dirname, '.env') });

const app = express();
const PORT = process.env.PORT || 3000;
const API_BASE_PATH = '/api/v1';

app.use(cors());

app.use(express.json());

app.use(express.urlencoded({ extended: true }));


const apiRouter = require('./src/routes/index');

app.use(API_BASE_PATH, apiRouter);


try {
    const swaggerSpec = YAML.load(path.join(__dirname, 'src', 'config', 'swagger.yaml'));

    app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));
    console.log(`📑 Swagger UI disponível em: http://localhost:${PORT}/api-docs`);

} catch (error) {
    console.error("❌ ERRO ao carregar o arquivo Swagger:", error.message);
}

app.get('/', (req, res) => {
    res.status(200).json({ 
        status: 'OK', 
        message: 'TE Evaluation Tool API rodando',
        version: 'v5.0.1',
        docs: `/api-docs`
    });
});

app.listen(PORT, () => {
    console.log('----------------------------------------------------');
    console.log(`🚀 Servidor rodando na porta ${PORT}`);
    console.log(`🔗 API Base: http://localhost:${PORT}${API_BASE_PATH}`);
    console.log('----------------------------------------------------');
});