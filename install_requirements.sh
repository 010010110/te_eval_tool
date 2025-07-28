#!/bin/bash

echo "🔍 Verificando dependências do sistema..."

# Função para verificar e instalar pacotes
check_and_install() {
    if ! dpkg -s "$1" >/dev/null 2>&1; then
        echo "📦 Instalando $1..."
        sudo apt update && sudo apt install -y "$1"
    else
        echo "✅ $1 já está instalado."
    fi
}

# Verifica se Python 3.9 está instalado
if ! python3.9 --version >/dev/null 2>&1; then
    echo "❌ Python 3.9 não encontrado. Instalando..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python3.9 python3.9-venv python3.9-distutils
else
    echo "✅ Python 3.9 encontrado: $(python3.9 --version)"
fi

# Verificar pacotes essenciais
check_and_install build-essential
check_and_install default-jdk
check_and_install git
check_and_install unzip
check_and_install wget

echo "✅ Dependências do sistema verificadas."
