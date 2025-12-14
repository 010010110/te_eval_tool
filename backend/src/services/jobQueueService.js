const path = require('path');
const cliService = require('./cliService');
const mailerService = require('./mailerService');
const fileService = require('./fileService');

const jobQueue = [];
let isProcessing = false;

const executeJob = (job) => {
    const { jobId, command, args, inputFilesForCleanup, outputDir } = job;
    
    cliService.executeBlockingJob(command, args)
        .then(async () => {
            console.log(`[QUEUE] Job ${jobId} (${command}) concluído com sucesso.`);

            if (Array.isArray(inputFilesForCleanup) && inputFilesForCleanup.length > 0) {
                for (const p of inputFilesForCleanup) {
                    try {
                        await fileService.deletePath(p);
                        console.log(`[CLEANUP] Removed temporary input: ${p}`);
                    } catch (err) {
                        console.warn(`[CLEANUP] Failed to remove temporary input ${p}: ${err && err.message}`);
                    }
                }
            }

            if (args.notificationEmail) {
                try {
                    const cliParams = { ...args };
                    delete cliParams.notificationEmail; 
                    
                    const mailResult = await mailerService.sendSuccessNotification(args.notificationEmail, command, path.resolve(outputDir), cliParams);
                    
                    if (mailResult && mailResult.success && outputDir) {
                        const resolved = path.resolve(outputDir);
                        const safePrefixes = [path.resolve('/app/data'), path.resolve('./data'), path.resolve(process.cwd(), 'data')];
                        const isSafe = safePrefixes.some(prefix => resolved.startsWith(prefix));

                        if (isSafe) {
                            try {
                                await fileService.deletePath(resolved);
                                console.log(`[CLEANUP] Removed output path: ${resolved}`);
                            } catch (err) {
                                console.warn(`[CLEANUP] Failed to remove output ${resolved}: ${err && err.message}`);
                            }
                        }
                    }
                } catch (emailErr) {
                    console.error(`[MAILER ERROR] Failed to send success notification for job ${jobId}: ${emailErr && emailErr.message}`);
                }
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
}

module.exports = new JobQueueService();