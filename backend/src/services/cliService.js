const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const PYTHON_EXECUTABLE = 'python3'; 

const CLI_CWD = path.join(__dirname, '..', '..', '..', 'CLI');
const CLI_MAIN_SCRIPT_RELATIVE = path.join('src', 'main.py'); 

const camelToKebab = (camelCase) => camelCase.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase();

const cleanupFiles = (filePaths) => { 
    const pathsToClean = Array.isArray(filePaths) ? filePaths : [filePaths].filter(p => p); 

    pathsToClean.forEach(filePath => {
        if (!filePath) return;
        
        fs.stat(filePath, (statErr, stats) => {
            if (statErr) {
                return;
            }

            if (stats.isDirectory()) {
                console.warn(`[ASYNC CLEANUP WARNING] Skipping directory cleanup: '${filePath}'`);
                return;
            }

            fs.unlink(filePath, (err) => {
                if (err) {
                    console.error(`[ASYNC CLEANUP ERROR] Failed to remove input file: ${filePath}`, err);
                } else {
                    console.log(`[ASYNC CLEANUP SUCCESS] Input file removed: ${filePath}`);
                }
            });
        });
    });
}

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
                } else {
                    cliArgs.push(cliOption);
                }
            }
        } else if (value !== null && value !== undefined) {
            if (key !== 'verbose') { 
                cliArgs.push(cliOption);
                cliArgs.push(String(value));
            }
        }
    }
    return cliArgs;
};

const executeDetached = (command, args, options, inputFilesForCleanup) => {
    return new Promise((resolve, reject) => {
        
        const srcPath = path.join(CLI_CWD, 'src');
        const env = { 
            ...process.env, 
            PYTHONPATH: srcPath + path.delimiter + CLI_CWD 
        };

        const spawnOptions = { 
            ...options,
            env: env 
        };

        const cliProcess = spawn(command, args, spawnOptions); 
        console.log(CLI_CWD);
        console.log(`[JOB STARTED] PID: ${cliProcess.pid}. Executando: ${command} ${args.join(' ')}`);

        cliProcess.on('error', (err) => {
            if (err.code === 'ENOENT') {
                reject(new Error(`O executável Python ('${command}') não foi encontrado. Verifique a variável PYTHON_CLI_EXECUTABLE no .env.`));
            } else {
                reject(err);
            }
        });
        
        let stderr = '';
        cliProcess.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        cliProcess.on('close', (code) => {
            if (code !== 0) {
                 console.error(`[JOB FAILED] PID ${cliProcess.pid} falhou com código ${code}. Erro: ${stderr}`);
            } else {
                 console.log(`[JOB SUCCESS] PID ${cliProcess.pid} concluído com sucesso.`);
            }
            cleanupFiles(inputFilesForCleanup); 
        });
        
        resolve({ pid: cliProcess.pid, message: "Processo CLI iniciado com sucesso." });
        
        cliProcess.unref(); 
    });
};


exports.execute = async (command, args) => {
    if (command !== 'run' && command !== 'map-labels') {
        throw new Error(`Comando '${command}' não implementado.`);
    }

    const cliArgs = buildArgs(command, args);
    
    // CORREÇÃO CRÍTICA: Reverte para execução baseada em path (python src/main.py ...)
    const executionArgs = [
        CLI_MAIN_SCRIPT_RELATIVE, 
        ...cliArgs
    ];
    
    // Constrói o array de arquivos de entrada para a limpeza
    const inputFilesForCleanup = [];
    if (args.input) inputFilesForCleanup.push(args.input);
    if (args.fasta) inputFilesForCleanup.push(args.fasta);
    if (args.predictions) inputFilesForCleanup.push(args.predictions);

    try {
        const result = await executeDetached(PYTHON_EXECUTABLE, executionArgs, {
            cwd: CLI_CWD 
        }, inputFilesForCleanup); 
        
        return result;

    } catch (error) {
        const errorMessage = error.message || "Erro desconhecido na execução da CLI.";
        throw new Error(errorMessage);
    }
};