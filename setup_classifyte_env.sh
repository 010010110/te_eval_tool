#!/bin/bash

set -e

echo "📁 Criando ambiente virtual em model_envs/classifyte_env..."
python3.9 -m venv model_envs/classifyte_env

echo "🐍 Ativando ambiente..."
source model_envs/classifyte_env/bin/activate

echo "📦 Instalando dependências..."
pip install --upgrade pip
pip install -r ClassifyTE/requirements.txt

echo "🔗 Verificando link simbólico para pasta 'features'..."
if [ ! -d "features" ]; then
    if [ -d "ClassifyTE/features" ]; then
        ln -s ClassifyTE/features features
        echo "✅ Link simbólico 'features' → 'ClassifyTE/features' criado com sucesso."
    else
        echo "❌ Pasta 'ClassifyTE/features' não encontrada. Verifique se ela existe no projeto."
        exit 1
    fi
else
    echo "✅ Pasta ou link 'features' já existe."
fi

echo "✅ Ambiente ClassifyTE configurado com sucesso!"
