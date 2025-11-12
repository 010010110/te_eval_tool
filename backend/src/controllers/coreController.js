const cliService = require('../services/cliService');
const fileService = require('../services/fileService');
const path = require('path');

exports.run = async (req, res) => {
    let tempFilePath = null;
    let runOutputDir = null;
    
    try {
        const args = req.body;
        
        if (!req.file) {
            throw new Error("Arquivo FASTA de entrada (fastaFile) é obrigatório.");
        }
        
        tempFilePath = await fileService.saveFileStream(req.file);
        args.input = tempFilePath; 
        
        if (!args.output) {
            const timestamp = Date.now();
            const uniqueDirName = `run_${timestamp}`;
            runOutputDir = path.join('..', 'data', 'results', uniqueDirName);
            args.output = runOutputDir;
        } else {
            runOutputDir = args.output;
        }

        if (!args.modelFile) {
            if (args.model === 'classifyte' || !args.model) {
                args.modelFile = 'ClassifyTE_combined.pkl';
            } 
            else if (args.model === 'terl') {
                args.modelFile = path.join('src', 'models', 'TERL', 'Models', 'DS3');
            }
        } 
        
        else if (args.model === 'terl') {
            const shortNameRegex = /^DS[1-5]$/;
            const prefix = path.join('src', 'models', 'TERL', 'Models');
            
            if (shortNameRegex.test(args.modelFile) && 
                !args.modelFile.startsWith(prefix)) {
                
                args.modelFile = path.join(prefix, args.modelFile);
            }
        }
        args.clean = true;
        args.verbose = true;

        cliService.execute('run', args)
            .then(result => {
                console.log(`[JOB LAUNCHED CONFIRMATION] PID: ${result.pid}, Output: ${runOutputDir}`);
            })
            .catch(error => {
                console.error("ERRO CRÍTICO no lançamento do job assíncrono:", error.message);
            });

        res.status(200).json({ 
            message: "Classificação iniciada com sucesso em background. O processamento dos resultados está em andamento.", 
            output: runOutputDir,
            status: "PROCESSING_ASYNC",
            note: "Os resultados serão salvos no diretório especificado quando a execução for concluída."
        });
        
    } catch (error) {
        if (tempFilePath) {
            await fileService.deleteFile(tempFilePath);
        }
        
        res.status(500).json({ 
            message: "Falha no pré-processamento (upload ou configuração de entrada).", 
            error: error.message 
        });
    }
};

exports.mapLabels = async (req, res) => {
    let fastaFilePath = null;
    let predictionsFilePath = null;
    
    try {
        const args = req.body;
        const files = req.files;

        if (!files || !files.fastaFile || files.fastaFile.length === 0) {
            throw new Error("Arquivo FASTA é obrigatório (campo 'fastaFile').");
        }

        fastaFilePath = await fileService.saveFileStream(files.fastaFile[0]);
        args.fasta = fastaFilePath; 


        if (files.predictionsFile && files.predictionsFile.length > 0) {
            predictionsFilePath = await fileService.saveFileStream(files.predictionsFile[0]);
            args.predictions = predictionsFilePath;
        }

        if (args.validateOnly === 'true' || args.validateOnly === true) {
             delete args.output;
             args.validateOnly = true; 
        } 
        
        else if (!args.output) {
             const defaultOutput = `${path.basename(fastaFilePath, path.extname(fastaFilePath))}_mapped.csv`;
             args.output = path.join('data', 'results', defaultOutput); 
        }

        if (!args.treeFile) {
             args.treeFile = 'src/nodes/tree.txt'; 
        }

        args.verbose = true;

        cliService.execute('map-labels', args)
            .then(result => {
                console.log(`[JOB LAUNCHED CONFIRMATION] Mapeamento concluído com PID: ${result.pid}`);
            })
            .catch(error => {
                console.error("ERRO CRÍTICO no lançamento do job assíncrono (map-labels):", error.message);
            });

        res.status(200).json({ 
            message: "Mapeamento iniciado com sucesso em background. Arquivos temporários serão limpos.",
            outputFile: args.output || "Nenhum arquivo de saída (apenas validação)",
            status: "PROCESSING_ASYNC"
        });
        
    } catch (error) {
        if (fastaFilePath) await fileService.deleteFile(fastaFilePath);
        if (predictionsFilePath) await fileService.deleteFile(predictionsFilePath);
        
        res.status(500).json({ 
            message: "Falha no pré-processamento de mapeamento (upload ou validação).", 
            error: error.message 
        });
    }
};
