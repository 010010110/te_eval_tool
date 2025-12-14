const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const mailerService = require('./mailerService');
const PYTHON_EXECUTABLE = process.env.PYTHON_CLI_EXECUTABLE || 'python3';

const CLI_CWD = path.join(__dirname, '..', '..', '..', 'CLI');

const camelToKebab = (camelCase) => camelCase.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase();

const buildArgs = (command, args) => {
    const cliArgs = [command];

    for (const key of Object.keys(args || {})) {
        const value = args[key];
        const cliOption = `--${camelToKebab(key)}`;
        
        if (key === 'algorithm' && args.model === 'terl') {
            continue; 
        }

        if (typeof value === 'boolean') {
            if (value === true) {
                if (key === 'verbose') {
                    cliArgs.push('-v');
                } else if (key !== 'clean') { 
                    cliArgs.push(cliOption);
                }
            }
        } else if (value !== null && value !== undefined && value !== '') {
            if (key !== 'verbose' && key !== 'notificationEmail') { 
                cliArgs.push(cliOption);
                cliArgs.push(String(value));
            }
        }
    }
    return cliArgs;
};

const executeBlockingJob = (command, args) => {
    return new Promise((resolve, reject) => {
        
        const cliArgs = buildArgs(command, args);
        
        const executionArgs = [
            path.join('src', 'main.py'), 
            ...cliArgs
        ];

        const srcPath = path.join(CLI_CWD, 'src');
        const env = { 
            ...process.env, 
            PYTHONPATH: srcPath
        };

        const cliProcess = spawn(PYTHON_EXECUTABLE, executionArgs, { 
            cwd: CLI_CWD,
            env: env 
        }); 
        
        console.log(`[CLI EXEC] Spawning command: ${PYTHON_EXECUTABLE} ${executionArgs.join(' ')}`);

        let stdout = '';
        let stderr = '';
        
        cliProcess.stdout.on('data', (data) => { stdout += data.toString(); });
        cliProcess.stderr.on('data', (data) => { stderr += data.toString(); });

        cliProcess.on('error', (err) => {
            if (err.code === 'ENOENT') {
                return reject(new Error(`O executável Python ('${PYTHON_EXECUTABLE}') não foi encontrado. Verifique o Docker/variável PYTHON_CLI_EXECUTABLE.`));
            }
            reject(err);
        });

        cliProcess.on('close', (code) => {
            if (code !== 0) {
                const errorMessage = stderr.trim() || `Comando CLI falhou com código de saída ${code}.`;
                return reject(new Error(errorMessage));
            } else {
                return resolve(stdout);
            }
        });
    });
};

class CLIService {
    executeBlockingJob(command, args) {
        return executeBlockingJob(command, args);
    }
}

module.exports = new CLIService();