const fs = require('fs');
const path = require('path');

const UPLOAD_DIR = path.join(__dirname, '..', '..', '..', 'data', 'uploads');

const ensureUploadDir = () => {
    if (!fs.existsSync(UPLOAD_DIR)) {
        fs.mkdirSync(UPLOAD_DIR, { recursive: true });
    }
};

exports.saveFileStream = (file) => {
    return new Promise((resolve, reject) => {
        if (!file || !file.originalname || !file.buffer) {
            return reject(new Error("Arquivo inválido ou não enviado."));
        }

        ensureUploadDir();

        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        const fileName = file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname);
        const filePath = path.join(UPLOAD_DIR, fileName);

        const writeStream = fs.createWriteStream(filePath);

        writeStream.on('finish', () => {
            resolve(filePath);
        });

        writeStream.on('error', (err) => {
            reject(new Error(`Erro ao salvar arquivo via stream: ${err.message}`));
        });

        writeStream.end(file.buffer);
    });
};

exports.deleteFile = (filePath) => {
    return new Promise((resolve) => {
        fs.unlink(filePath, (err) => {
            resolve();
        });
    });
};