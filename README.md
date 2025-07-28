# 🧬 TE Evaluation Tool

Ferramenta de linha de comando para avaliação de modelos de classificação de Elementos Transponíveis (TEs), como o **ClassifyTE**. Permite ao usuário rodar facilmente modelos existentes com seus próprios arquivos `.fasta` e obter métricas padronizadas.

---
#### 🧪 Modelos suportados
- [ClassifyTE](https://github.com/manisa/ClassifyTE)

#### 📋 Pré-Requisitos
- Linux (Ubuntu recomendado)

- Python 3.9

- Java JDK

#### 👨‍🔬 Criação e pesquisa

Desenvolvido para facilitar a avaliação de modelos de classificação de elementos transponíveis com diferentes datasets, especialmente no contexto de pesquisa científica.

--- 

## 📦 Funcionalidades

- Execução automatizada do pipeline do **ClassifyTE**
- Suporte a arquivos `.fasta` personalizados
- Avaliação com métricas padrão (Acurácia, Precisão, F1-score, etc.)
- Script para instalar pré-requisitos
- Script de instalação para preparar o ambiente do zero

---

## 🚀 Começando

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/te_eval_tool.git
cd te_eval_tool
```

### 2. Instale os requisitos do sistema
> Etapa opicional caso ja tenha instalado os requisitos   listados

Execute o script abaixo para verificar e instalar dependências do sistema:
```bash
chmod +x install_requirements.sh
./install_requirements.sh
```
> Requisitos: Ubuntu/Debian com apt e permissões de sudo

## ⚙️ Usando a ferramenta

### 1. Escolha seu .fasta
Você pode usar o dataset padrão ou fornecer o seu próprio arquivo:

- ✅ Opção 1: Use o dataset padrão incluído (default_dataset.fasta)

- ✅ Opção 2: Forneça seu próprio .fasta com --input (o arquivo será automaticamente copiado para a estrutura esperada)

### 2. Execute o modelo ClassifyTE

```bash
python main.py \
  --model classifyte \
  --input /caminho/para/seu_arquivo.fasta \
  --outputs ./outputss/nome_da_execucao/
```
Exemplo:
```bash 
python main.py \
  --model classifyte \
  --input data/my_sequences.fasta \
  --outputs ./outputss/teste_classifyte/
```
### 3. Resultados
Os arquivos de saída são salvos no diretório `--outputs`, incluindo:

`metrics.json`: métricas da classificação

`predicted_result.csv`: previsões do modelo


### 📂 Estrutura de Pastas
```bash
te_eval_tool/
├── ClassifyTE/            # Código do modelo ClassifyTE
├── evaluation/            # Cálculo de métricas
├── model_envs/            # Ambientes virtuais isolados por modelo
├── outputss/               # Resultados das execuções
├── data/                  # Base de dados do usuário
├── main.py                # Ponto de entrada da ferramenta
├── install_requirements.sh
└── README.md
```

📄 Licença
MIT License
