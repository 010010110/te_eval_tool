const path = require('path');
const cliService = require('./cliService');
const mailerService = require('./mailerService');

const jobQueue = [];
let isProcessing = false;

const executeJob = (job) => {
    const { jobId, command, args, inputFilesForCleanup, outputDir } = job;
    
    cliService.executeBlockingJob(command, args, inputFilesForCleanup)
        .then(() => {
            console.log(`[QUEUE] Job ${jobId} (${command}) concluído com sucesso.`);
            if (args.notificationEmail) {
                mailerService.sendSuccessNotification(args.notificationEmail, command, path.resolve(outputDir));
            }
        })
        .catch((error) => {
            console.error(`[QUEUE ERROR] Job ${jobId} (${command}) falhou: ${error.message}`);
            if (args.notificationEmail) {
                mailerService.sendFailureNotification(args.notificationEmail, command, error.message);
            }
        })
        .finally(() => {
            isProcessing = false;
            processQueue();
        });
};


const processQueue = () => {
    if (isProcessing || jobQueue.length === 0) {
        return;
    }

    isProcessing = true;
    const job = jobQueue.shift();
    
    console.log(`[QUEUE] Iniciando processamento do Job ${job.jobId} (${job.command}). Jobs na fila: ${jobQueue.length}`);
    executeJob(job);
};


class JobQueueService {
    
    addJob(command, args, inputFilesForCleanup, outputDir) {
        const jobId = `JOB-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
        
        const job = {
            jobId,
            command,
            args,
            inputFilesForCleanup,
            outputDir,
            submittedAt: new Date(),
        };
        
        jobQueue.push(job);
        
        setTimeout(processQueue, 0); 
        
        return jobId;
    }
    
    getQueueStatus() {
        return {
            queueLength: jobQueue.length,
            isProcessing,
        };
    }
}

module.exports = new JobQueueService();