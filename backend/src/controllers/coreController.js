const fileService = require('../services/fileService');
const jobQueueService = require('../services/jobQueueService');
const path = require('path');

const BASE_RESULTS_DIR = '/app/data/results';
const CLI_ROOT_PATH = path.join(__dirname, '..', '..', '..', 'CLI');


const TERL_MODELS_DIR = path.join(CLI_ROOT_PATH, 'src', 'models', 'TERL', 'Models');
const INPACTOR2_DIR = path.join(CLI_ROOT_PATH, 'src', 'models', 'Inpactor2');

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
            runOutputDir = path.join(BASE_RESULTS_DIR, uniqueDirName);
            args.output = runOutputDir;
        } else {
            runOutputDir = args.output;
        }
        
        if (args.model === 'inpactorDB') {
            args.model = 'inpactor2';
        }

        if (!args.modelFile) {
            if (args.model === 'classifyte' || !args.model) {
                args.modelFile = 'ClassifyTE_combined.pkl';
            }
            else if (args.model === 'terl') {
                args.modelFile = path.join(TERL_MODELS_DIR, 'DS3');
            }
            
            else if (args.model === 'inpactor2') {
                args.modelFile = INPACTOR2_DIR;
            }
        } 
        
        else if (args.model === 'terl') {
            const shortNameRegex = /^DS[1-5]$/;
            const prefix = path.join(TERL_MODELS_DIR);
            
            if (shortNameRegex.test(args.modelFile) && 
                !args.modelFile.startsWith(prefix)) {
                
                args.modelFile = path.join(prefix, args.modelFile);
            }
        }
        
        args.clean = true;
        args.verbose = true;
        args.autoLabel = true;
        
        const inputFilesForCleanup = [tempFilePath];
        
        const jobId = jobQueueService.addJob(
            'run', 
            args, 
            inputFilesForCleanup,
            runOutputDir
        );

        res.status(200).json({ 
            message: "Classificação enfileirada com sucesso e será processada sequencialmente.", 
            jobId: jobId,
            status: "QUEUED",
            outputDir: runOutputDir,
            note: "Você receberá uma notificação por e-mail na conclusão."
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
    let outputInfo = "Nenhum";
    
    try {
        const args = req.body;
        const files = req.files;

        const inputFilesForCleanup = [];

        if (!files || !files.fastaFile || files.fastaFile.length === 0) {
            throw new Error("Arquivo FASTA é obrigatório (campo 'fastaFile').");
        }
        fastaFilePath = await fileService.saveFileStream(files.fastaFile[0]);
        args.fasta = fastaFilePath; 
        inputFilesForCleanup.push(fastaFilePath);

        if (files.predictionsFile && files.predictionsFile.length > 0) {
            predictionsFilePath = await fileService.saveFileStream(files.predictionsFile[0]);
            args.predictions = predictionsFilePath;
            inputFilesForCleanup.push(predictionsFilePath);
        }

        const isValidateOnly = (args.validateOnly === 'true' || args.validateOnly === true);

        args.validateOnly = isValidateOnly;
        args.verbose = true;
        
        if (!args.treeFile) {
             args.treeFile = 'src/nodes/tree.txt'; 
        }

        if (isValidateOnly) {
             delete args.output;
             outputInfo = "Apenas Validação - Sem arquivo de saída";
        } 
        else if (!args.output) {
             const defaultOutput = `${path.basename(fastaFilePath, path.extname(fastaFilePath))}_mapped.csv`;
             const outputPath = path.join(BASE_RESULTS_DIR, defaultOutput);
             args.output = outputPath;
             outputInfo = outputPath;
        } else {
             outputInfo = args.output;
        }

        const jobId = jobQueueService.addJob(
            'map-labels', 
            args, 
            inputFilesForCleanup,
            outputInfo
        );

        res.status(200).json({ 
            message: "Mapeamento enfileirado com sucesso e será processado sequencialmente.", 
            jobId: jobId,
            status: "QUEUED",
            outputFile: outputInfo,
            note: "Você receberá uma notificação por e-mail na conclusão."
        });
        
    } catch (error) {
        if (fastaFilePath) await fileService.deleteFile(fastaFilePath);
        if (predictionsFilePath) await fileService.deleteFile(predictionsFilePath);
        
        res.status(500).json({ 
            message: "Falha no pré-processamento (upload ou validação de entrada).", 
            error: error.message 
        });
    }
};

exports.evaluateMetrics = async (req, res) => {
    let predictionsFilePath = null;
    let runOutputDir = null;
    
    try {
        const args = req.body;

        if (!req.file) {
            throw new Error("Arquivo CSV de predições é obrigatório (campo 'predictionsFile').");
        }
        predictionsFilePath = await fileService.saveFileStream(req.file);
        args.predictions = predictionsFilePath; 
        
        const inputFilesForCleanup = [predictionsFilePath];

        if (!args.output) {
            const timestamp = Date.now();
            const uniqueDirName = `evaluation_${timestamp}`;
            runOutputDir = path.join(BASE_RESULTS_DIR, uniqueDirName); 
            args.output = runOutputDir;
        } else {
            runOutputDir = args.output;
        }

        if (!args.hierarchy) {
             args.hierarchy = 'src/nodes/tree.txt'; 
        }

        args.verbose = true;

        const jobId = jobQueueService.addJob(
            'evaluate', 
            args, 
            inputFilesForCleanup,
            runOutputDir
        );

        res.status(200).json({ 
            message: "Avaliação enfileirada com sucesso e será processada sequencialmente.", 
            jobId: jobId,
            status: "QUEUED",
            outputDir: runOutputDir,
            note: "Você receberá uma notificação por e-mail na conclusão."
        });
        
    } catch (error) {
        if (predictionsFilePath) {
            await fileService.deleteFile(predictionsFilePath);
        }
        res.status(500).json({ 
            message: "Falha no pré-processamento (upload ou configuração de entrada).", 
            error: error.message 
        });
    }
};