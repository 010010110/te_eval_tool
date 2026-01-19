const nodemailer = require('nodemailer');
const path = require('path');
const fs = require('fs');

const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST,
    port: process.env.SMTP_PORT,
    secure: process.env.SMTP_PORT == 465,
    auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS,
    },
});

exports.sendSuccessNotification = async (recipientEmail, jobType, outputDir, cliParams = null) => {

    if (!recipientEmail) {
        console.warn(`[MAILER WARNING] Tentativa de enviar e-mail sem endereço de destinatário.`);
        return;
    }

    let attachments = [];
    let fileListHTML = '';
    let metricsFiles = [];
    let otherFiles = [];
    let cliParamsHTML = '';

    try {
        const stats = fs.statSync(outputDir);
        
        if (stats.isDirectory()) {
            const files = fs.readdirSync(outputDir);
            const metricsKeywords = ['metrics', 'evaluation', 'report'];
            
            attachments = files
                .filter(file => {
                    try {
                        return fs.statSync(path.join(outputDir, file)).isFile();
                    } catch (e) {
                        return false;
                    }
                })
                .map(file => {
                    const isMetricsFile = metricsKeywords.some(keyword => 
                        file.toLowerCase().includes(keyword)
                    );
                    
                    if (isMetricsFile) {
                        metricsFiles.push(file);
                    } else {
                        otherFiles.push(file);
                    }
                    
                    return {
                        filename: file,
                        path: path.join(outputDir, file)
                    };
                });
            
            if (metricsFiles.length > 0) {
                fileListHTML += '<strong>📊 Metrics & Reports:</strong><ul>';
                metricsFiles.forEach(file => {
                    fileListHTML += `<li style="color: #2196F3;"><code>${file}</code></li>`;
                });
                fileListHTML += '</ul>';
            }
            
            if (otherFiles.length > 0) {
                fileListHTML += '<strong>📁 Results & Data:</strong><ul>';
                otherFiles.forEach(file => {
                    fileListHTML += `<li><code>${file}</code></li>`;
                });
                fileListHTML += '</ul>';
            }
        } else if (stats.isFile()) {
            const fileName = path.basename(outputDir);
            fileListHTML += `<li><code>${fileName}</code></li>`;
            attachments.push({
                filename: fileName,
                path: outputDir
            });
        }
    } catch (error) {
        console.error(`[MAILER ERROR] Falha ao ler o diretório/arquivo de saída ${outputDir}: ${error.message}`);
        fileListHTML = '<li>Não foi possível listar os arquivos devido a um erro no servidor.</li>';
    }

    // Build CLI parameters section if provided
    if (cliParams && Object.keys(cliParams).length > 0) {
        cliParamsHTML = `
            <div style="margin: 20px 0; padding: 15px; background-color: #f5f5f5; border-left: 4px solid #2196F3; border-radius: 4px;">
                <h4 style="margin-top: 0; color: #333;">⚙️ CLI Parameters Used:</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    ${Object.entries(cliParams)
                        .filter(([key, value]) => value !== undefined && value !== null && value !== '')
                        .map(([key, value]) => `
                    <tr>
                        <td style="padding: 6px; border: 1px solid #ddd; font-weight: bold; background-color: #e8e8e8; color: #555;"><code>${key}</code></td>
                        <td style="padding: 6px; border: 1px solid #ddd;"><code>${value}</code></td>
                    </tr>`).join('')}
                </table>
            </div>`;
    }

    const subject = `✅ Job '${jobType}' Completed Successfully!`;

    const resultsPathDisplay = path.normalize(outputDir).replace(/^(\.\.\/data\/|\/app\/data\/)/, 'results/');

    const attachmentMessage = attachments.length > 0
        ? (metricsFiles.length > 0 
            ? `✅ **${attachments.length} file(s)** attached, including **${metricsFiles.length} metrics/report file(s)**:`
            : `The **${attachments.length}** result files are attached directly to this email:`)
        : `The job was completed, but no files were found to attach in the directory ${resultsPathDisplay}.`;

    const mailOptions = {
        from: process.env.MAIL_FROM || process.env.SMTP_USER,
        to: recipientEmail,
        subject: subject,

        attachments: attachments,

        html: `
            <html>
                <head>
                    <style>
                        /* Estilos básicos para garantir boa visualização */
                        body {
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333333;
                        }
                        .container {
                            max-width: 600px;
                            margin: 0 auto;
                            border: 1px solid #dddddd;
                            border-radius: 8px;
                            overflow: hidden;
                        }
                        .header {
                            background-color: #4CAF50; /* Cor verde para sucesso */
                            color: white;
                            padding: 20px;
                            text-align: center;
                        }
                        .content {
                            padding: 30px;
                        }
                        .attachment-list {
                            list-style: none;
                            padding: 0;
                            margin-top: 15px;
                            border-left: 3px solid #4CAF50;
                        }
                        .attachment-list li {
                            padding: 5px 0 5px 15px;
                            background-color: #f9f9f9;
                            margin-bottom: 5px;
                            border-radius: 3px;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2 style="margin: 0;">✅ Job Completed Successfully!</h2>
                        </div>
                        
                        <div class="content">
                            <h3 style="color: #4CAF50;">TE Evaluation Tool Processing</h3>
                            
                            <p>Your <b>${jobType.toUpperCase()}</b> job has been completed successfully and the results are ready for analysis.</p>
                            
                            ${cliParamsHTML}
                            
                            <p><strong>${attachmentMessage}</strong></p>
                            
                            ${fileListHTML ? `<div style="margin: 20px 0;">${fileListHTML}</div>` : ''}

                            <br>
                            
                            <p>Thank you for using the tool.</p>
                            
                            <small style="color: #999999;">This is an automated notification.</small>
                        </div>
                    </div>
                </body>
                </html>
        `,
    };

    try {
        const info = await transporter.sendMail(mailOptions);
        console.log(`[MAILER SUCCESS] Notificação enviada para ${recipientEmail}. ID: ${info.messageId}`);
        if (attachments.length > 0) {
            console.log(`[MAILER INFO] Arquivos anexados: ${attachments.map(a => a.filename).join(', ')}`);
        }
        return { success: true, info };
    } catch (error) {
        console.error(`[MAILER ERROR] Falha ao enviar e-mail para ${recipientEmail}: ${error.message}`);
        return { success: false, error };
    }
};

exports.sendFailureNotification = async (recipientEmail, jobType, errorMessage) => {

    if (!recipientEmail) {
        console.warn(`[MAILER WARNING] Tentativa de enviar e-mail de falha sem endereço de destinatário.`);
        return;
    }

    const subject = `❌ CRITICAL FAILURE in Job '${jobType}'!`;

    const mailOptions = {
        from: process.env.MAIL_FROM || process.env.SMTP_USER,
        to: recipientEmail,
        subject: subject,
        html: `
            <html>
                <body>
                    <h2>TE Evaluation Tool Processing Failed</h2>
                    <p>Your <b>${jobType.toUpperCase()}</b> job could not be completed due to an error.</p>
                    
                    <p><b>Error Details (CLI Traceback):</b></p>
                    
                    <pre style="background-color: #ffe0e0; border: 1px solid #ff0000; padding: 15px; border-radius: 5px; font-size: 0.85em; overflow-x: auto;">
                        ${errorMessage}
                    </pre>
                    
                    <p>Please review the error above and try again.</p>
                </body>
            </html>
        `,
    };

    try {
        const info = await transporter.sendMail(mailOptions);
        console.log(`[MAILER FAILURE SENT] Notificação de falha enviada para ${recipientEmail}. ID: ${info.messageId}`);
    } catch (error) {
        console.error(`[MAILER ERROR] Falha ao enviar e-mail de falha para ${recipientEmail}: ${error.message}`);
    }
};