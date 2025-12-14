FROM node:20-bullseye

# 1. Instalar dependências do sistema
# Removemos 'git' da lista obrigatória pois vamos copiar o LTR_Finder localmente,
# mas mantemos mafft e prodigal essenciais para Inpactor2.
RUN apt-get update && \
    apt-get install -y python3.9 python3.9-venv python3.9-dev \
                       python3-pip \
                       build-essential default-jdk \
                       mafft prodigal && \
    apt-get clean

# 2. Configurar Python 3.9 como padrão
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# --- BLOCO DE INSTALAÇÃO DO LTR_FINDER (VIA CÓPIA LOCAL) ---
# Copia a pasta do seu computador para a pasta temporária do Docker
COPY LTR_Finder /tmp/LTR_Finder

# Compila e instala
WORKDIR /tmp/LTR_Finder/source
# make clean garante que não usamos binários velhos do host
RUN make clean && \
    make && \
    cp ltr_finder /usr/local/bin/ && \
    chmod +x /usr/local/bin/ltr_finder && \
    cd / && \
    rm -rf /tmp/LTR_Finder
# -----------------------------------------------------------

WORKDIR /app

# 3. Instalar Dependências do Backend (Node.js)
COPY backend/package.json backend/package-lock.json ./backend/
RUN npm install --prefix ./backend

# 4. Instalar Dependências da CLI (Python)
COPY CLI/ /app/CLI/
RUN pip install --no-cache-dir -r CLI/requirements.txt

# 5. Configurar Ambientes dos Modelos
WORKDIR /app/CLI/
RUN python3 src/main.py env setup --model all

# 6. Iniciar o Servidor
WORKDIR /app/backend
CMD [ "node", "server.js" ]

EXPOSE 3002