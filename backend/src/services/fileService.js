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

/**
 * Delete a filesystem path (file or directory) recursively.
 * Uses fs.promises.rm when available and falls back to recursive rmdir/unlink.
 */
exports.deletePath = async (targetPath) => {
    if (!targetPath) return;

    try {
        const stat = await fs.promises.stat(targetPath);
        if (stat.isDirectory()) {
            // recursive remove
            if (fs.promises.rm) {
                await fs.promises.rm(targetPath, { recursive: true, force: true });
            } else {
                // fallback for older Node: remove files then rmdir
                const files = await fs.promises.readdir(targetPath);
                await Promise.all(files.map(f => exports.deletePath(path.join(targetPath, f))));
                await fs.promises.rmdir(targetPath);
            }
        } else {
            await fs.promises.unlink(targetPath);
        }
    } catch (e) {
        // ignore errors; this is cleanup
    }
};