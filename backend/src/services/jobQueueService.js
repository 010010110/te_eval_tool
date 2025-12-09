const path = require('path');
const cliService = require('./cliService');
const mailerService = require('./mailerService');
const fileService = require('./fileService');

const jobQueue = [];
let isProcessing = false;

const executeJob = (job) => {
    const { jobId, command, args, inputFilesForCleanup, outputDir } = job;
    
    cliService.executeBlockingJob(command, args, inputFilesForCleanup)
        .then(async () => {
            console.log(`[QUEUE] Job ${jobId} (${command}) concluído com sucesso.`);

            // Cleanup inputs (temporary uploaded files) - delete regardless of email outcome
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

            // If an email recipient is configured, attempt to send notification and
            // only delete output results after the mail is successfully sent.
            if (args.notificationEmail) {
                try {
                    // Prepare CLI parameters to send in email
                    const cliParams = { ...args };
                    delete cliParams.notificationEmail; // Don't show email in params
                    
                    const mailResult = await mailerService.sendSuccessNotification(args.notificationEmail, command, path.resolve(outputDir), cliParams);
                    if (!mailResult || !mailResult.success) {
                        console.warn(`[MAILER] Email send returned non-success for job ${jobId}. Will not remove outputs.`);
                    } else {
                        console.log(`[MAILER] Success email sent for job ${jobId} (${command}). Proceeding to remove outputs.`);
                        // proceed to delete outputs below
                    }

                    // Safety: only remove output paths that appear to be inside the app data/results
                    // to avoid accidentally deleting unrelated locations.
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
                        } else {
                            console.warn(`[CLEANUP] Skipping removal of output path (unsafe): ${resolved}`);
                        }
                    }
                } catch (emailErr) {
                    console.error(`[MAILER ERROR] Failed to send success notification for job ${jobId}: ${emailErr && emailErr.message}`);
                    // Do not delete outputs if the mail failed — keep for debugging / manual retrieval
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
    
    getQueueStatus() {
        return {
            queueLength: jobQueue.length,
            isProcessing,
        };
    }
}

module.exports = new JobQueueService();