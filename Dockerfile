# Usa uma imagem Node.js como base para o ambiente de desenvolvimento
FROM node:20-bullseye

# ------------------------------------
# 1. SETUP DE DEPENDÊNCIAS DO SISTEMA
# ------------------------------------

# Instala ferramentas essenciais e Python 3.6 e 3.9 (necessário para ClassifyTE e TERL)
RUN apt-get update && \
    apt-get install -y python3.9 python3.9-venv python3.9-dev \
                    #    python3.6 python3.6-venv python3.6-dev \
                       python3-pip \
                       build-essential default-jdk && \
    apt-get clean

# Cria um link simbólico para 'python3' apontar para a versão que será o CLI wrapper (3.9)
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1

# ------------------------------------
# 2. SETUP DA APLICAÇÃO NODE.JS
# ------------------------------------

WORKDIR /app

# Copia e instala as dependências Node.js
COPY backend/package.json backend/package-lock.json ./backend/
RUN npm install --prefix ./backend

# ------------------------------------
# 3. SETUP DA APLICAÇÃO PYTHON (CLI)
# ------------------------------------

# Copia o código da CLI
COPY CLI/ /app/CLI/

# Instala as dependências do wrapper da CLI no ambiente do sistema (3.9)
RUN pip install --no-cache-dir -r CLI/requirements.txt

# ------------------------------------
# 4. PRÉ-CONFIGURAÇÃO DOS VENVs INTERNOS DA CLI
# ------------------------------------

# Executa o comando de setup para criar os ambientes virtuais internos (terl_env_py36, classifyte_env_py39)
# Isso garante que o EnvironmentManager no Python funcione corretamente.
WORKDIR /app/CLI/
RUN python3 src/main.py env setup --model all

# ------------------------------------
# 5. CONFIGURAÇÃO FINAL
# ------------------------------------

# Retorna para o diretório de execução principal
WORKDIR /app/backend
CMD [ "node", "server.js" ]

# Porta exposta
EXPOSE 3002