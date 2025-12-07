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

exports.sendSuccessNotification = async (recipientEmail, jobType, outputDir) => {

    if (!recipientEmail) {
        console.warn(`[MAILER WARNING] Tentativa de enviar e-mail sem endereço de destinatário.`);
        return;
    }

    let attachments = [];
    let fileListHTML = '';
    let metricsFiles = [];
    let otherFiles = [];

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

    const subject = `✅ Job '${jobType}' Concluído com Sucesso!`;

    const resultsPathDisplay = path.normalize(outputDir).replace(/^(\.\.\/data\/|\/app\/data\/)/, 'results/');

    const attachmentMessage = attachments.length > 0
        ? (metricsFiles.length > 0 
            ? `✅ **${attachments.length} arquivo(s)** anexado(s), incluindo **${metricsFiles.length} arquivo(s) de métricas/relatórios**:`
            : `Os **${attachments.length}** arquivos de resultado estão anexados diretamente a este e-mail:`)
        : `O job foi concluído, mas nenhum arquivo foi encontrado para anexar no diretório ${resultsPathDisplay}.`;

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
                            <h2 style="margin: 0;">✅ Job Concluído com Sucesso!</h2>
                        </div>
                        
                        <div class="content">
                            <h3 style="color: #4CAF50;">Processamento da TE Evaluation Tool</h3>
                            
                            <p>O seu job de <b>${jobType.toUpperCase()}</b> foi concluído com sucesso e os resultados estão prontos para análise.</p>
                            
                            <p><strong>${attachmentMessage}</strong></p>
                            
                            ${fileListHTML ? `<div style="margin: 20px 0;">${fileListHTML}</div>` : ''}

                            <br>
                            
                            <p>Obrigado por usar a ferramenta.</p>
                            
                            <small style="color: #999999;">Esta é uma notificação automática.</small>
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

    const subject = `❌ FALHA Crítica no Job '${jobType}'!`;

    const mailOptions = {
        from: process.env.MAIL_FROM || process.env.SMTP_USER,
        to: recipientEmail,
        subject: subject,
        html: `
            <html>
                <body>
                    <h2>Processamento da TE Evaluation Tool Falhou</h2>
                    <p>O seu job de <b>${jobType.toUpperCase()}</b> não pôde ser concluído devido a um erro.</p>
                    
                    <p><b>Detalhes do Erro (Traceback da CLI):</b></p>
                    
                    <pre style="background-color: #ffe0e0; border: 1px solid #ff0000; padding: 15px; border-radius: 5px; font-size: 0.85em; overflow-x: auto;">
                        ${errorMessage}
                    </pre>
                    
                    <p>Por favor, revise o erro acima e tente novamente.</p>
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