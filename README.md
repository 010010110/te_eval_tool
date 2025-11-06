# 🧬 TE Evaluation Tool v1.0

Ferramenta padronizada para avaliação de modelos de classificação de Elementos Transponíveis (TEs) com métricas completas e mapeamento automático de labels.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)]()

## 📋 Índice

- [Sobre](#-sobre)
- [Funcionalidades](#-funcionalidades)
- [Instalação](#-instalação)
- [Uso Rápido](#-uso-rápido)
- [Comandos Principais](#-comandos-principais)
- [Métricas Disponíveis](#-métricas-disponíveis)
- [Formatos de Dados](#-formatos-de-dados)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Exemplos Avançados](#-exemplos-avançados)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

## 🎯 Sobre

O **TE Evaluation Tool** foi desenvolvido como parte de uma pesquisa de mestrado em Computação Aplicada para padronizar a avaliação de modelos de Inteligência Artificial aplicados à classificação de elementos transponíveis.

### 📊 Problema Resolvido

A literatura científica mostra uma **falta de padronização** na avaliação de modelos de classificação de TEs:
- Diferentes estudos usam métricas distintas
- Bases de dados variadas dificultam comparações
- Ausência de validação hierárquica específica para TEs
- Dificuldade na reprodutibilidade dos resultados

### 🎯 Solução

Esta ferramenta oferece:
- **Pipeline padronizado** para avaliação de modelos
- **Métricas hierárquicas** específicas para classificação de TEs
- **Mapeamento automático** de headers FASTA para códigos hierárquicos
- **Ambientes isolados** para cada modelo (evita conflitos de dependências)
- **Relatórios acadêmicos** prontos para publicação

## ✨ Funcionalidades

### 🤖 Modelos Suportados
- ✅ **ClassifyTE** - Stacking-based hierarchical classifier
- 🚧 **Inpactor2** - Deep learning for LTR retrotransposons (em desenvolvimento)
- 🚧 **TERL** - CNN-based classification (em desenvolvimento)

### 📈 Métricas Implementadas

**Métricas Padrão:**
- Acurácia, Precisão, Recall, F1-Score (macro/micro/weighted)
- Matriz de confusão
- Especificidade
- Youden's J Statistic

**Métricas Avançadas:**
- Area Under ROC Curve (auROC)
- Mean Average Precision (mAP)

**Métricas Hierárquicas:**
- Precisão hierárquica
- Recall hierárquico
- F1-Score hierárquico
- Distância hierárquica média
- Erro induzido pela árvore

### 🏷️ Mapeamento Automático

Suporta múltiplos formatos de headers FASTA:
```
>5S|ClassI|SINE|5S                    # Formato estruturado
>AACOPIA1_I|ClassI|LTR|Copia         # Formato padrão
>hAT-9_XT|ClassII|TIR|hAT            # Formato completo
>ATRAN                               # Nome simples (inferência automática)
```

## 🚀 Instalação

### Pré-requisitos
- Python 3.9+
- Java JDK (para ClassifyTE)
- Git

### Setup Automático

```bash
# 1. Clone o repositório
git clone https://github.com/010010110/te_eval_tool.git
cd te-eval-tool

# 2. Configure ambientes virtuais
python3 te_eval_cli.py env setup

# 3. Verifique a instalação
python3 te_eval_cli.py info
```

### Setup Manual

```bash
# 1. Instalar dependências do sistema (Ubuntu/Debian)
sudo apt update
sudo apt install python3-pip python3-venv default-jdk

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependências Python
pip install pandas scikit-learn numpy click

# 4. Verificar ClassifyTE
ls ClassifyTE/  # Deve conter generate_feature_file.py, evaluate.py, etc.
```

## ⚡ Uso Rápido

### Teste Inicial
```bash
# Pipeline completo com dataset padrão
python3 te_eval_cli.py quickstart
```

### Classificação Completa
```bash
# Executar ClassifyTE + mapeamento automático + métricas
python3 te_eval_cli.py run \
  --model classifyte \
  --input data/default_dataset.fasta \
  --output results/my_analysis \
  --auto-label \
  --verbose
```

### Validar Arquivo
```bash
# Verificar se FASTA é válido
python3 te_eval_cli.py validate \
  --input data/my_sequences.fasta \
  --detailed
```

## 🛠️ Comandos Principais

### Gerenciamento de Ambientes
```bash
# Configurar ambientes para todos os modelos
python3 te_eval_cli.py env setup

# Listar ambientes disponíveis
python3 te_eval_cli.py env list

# Limpar ambientes
python3 te_eval_cli.py env clean
```

### Execução de Modelos
```bash
# Classificação básica
python3 te_eval_cli.py run \
  --model classifyte \
  --input data/sequences.fasta \
  --output results/classification

# Com algoritmo específico
python3 te_eval_cli.py run \
  --model classifyte \
  --input data/sequences.fasta \
  --output results/nllcpn_test \
  --algorithm nllcpn

# Sem avaliação automática
python3 te_eval_cli.py run \
  --model classifyte \
  --input data/sequences.fasta \
  --output results/classify_only \
  --skip-evaluation
```

### Mapeamento de Labels
```bash
# Validar mapeamento de headers
python3 te_eval_cli.py map-labels \
  --fasta data/sequences.fasta \
  --validate-only

# Adicionar labels a predições existentes
python3 te_eval_cli.py map-labels \
  --fasta data/sequences.fasta \
  --predictions results/predictions.csv

# Gerar arquivo de mapeamentos
python3 te_eval_cli.py map-labels \
  --fasta data/sequences.fasta \
  --output mappings.csv
```

### Avaliação de Métricas
```bash
# Avaliação completa
python3 te_eval_cli.py evaluate \
  --predictions results/predicted_results.csv \
  --output results/metrics

# Diferentes formatos de saída
python3 te_eval_cli.py evaluate \
  --predictions results/predicted_results.csv \
  --output results/metrics \
  --format json

# Com arquivo de hierarquia customizado
python3 te_eval_cli.py evaluate \
  --predictions results/predicted_results.csv \
  --output results/metrics \
  --hierarchy custom_tree.txt
```

### Comparação de Resultados
```bash
# Comparar múltiplas execuções
python3 te_eval_cli.py compare \
  --results-dir results/ \
  --output comparison_report

# Comparar por métrica específica
python3 te_eval_cli.py compare \
  --results-dir results/ \
  --metric accuracy
```

### Utilitários
```bash
# Ver informações do sistema
python3 te_eval_cli.py info

# Exemplos de uso
python3 te_eval_cli.py examples

# Limpeza de arquivos temporários
python3 te_eval_cli.py clean --target temp

# Ajuda completa
python3 te_eval_cli.py --help
```

## 📊 Métricas Disponíveis

### Arquivo `metrics_summary.json`
```json
{
  "accuracy": 0.8567,
  "precision_macro": 0.8423,
  "recall_macro": 0.8567,
  "f1_macro": 0.8492,
  "specificity_macro": 0.9640,
  "youdens_j": 0.8207,
  "hierarchical_f1": 0.8756,
  "total_samples": 100,
  "num_classes": 8
}
```

### Relatório Detalhado (`evaluation_report.txt`)
```
RELATÓRIO DE AVALIAÇÃO - ELEMENTOS TRANSPONÍVEIS
==================================================

RESUMO EXECUTIVO:
Total de sequências: 100
Acurácia geral: 0.8567
F1-Score (macro): 0.8492
F1-Score hierárquico: 0.8756
Youden's J Statistic: 0.8207

MÉTRICAS PADRÃO:
Acurácia: 0.8567
Precisão (macro): 0.8423
[...]

MÉTRICAS HIERÁRQUICAS:
Precisão hierárquica: 0.8890
Recall hierárquico: 0.8634
F1-Score hierárquico: 0.8756
[...]
```

## 📁 Formatos de Dados

### Arquivo FASTA de Entrada
```
>5S|ClassI|SINE|5S
ATCGATCGATCGATCGATCGATCGATCGATCGATCG
>AACOPIA1_I|ClassI|LTR|Copia
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT
>hAT-9_XT|ClassII|TIR|hAT
TTAATTAATTAATTAATTAATTAATTAATTAATTA
```

### Arquivo de Hierarquia (`nodes/tree.txt`)
```
1,Retrotransposon
2,DNA transposon
1.1,LTR
1.1.1,Copia
1.1.2,gypsy
1.5,SINE
1.5.3,5S
2.1.1,TIRS
2.1.1.2,hAT
```

### Saída de Predições
```csv
Sequence ID,Predicted label,Actual_Label,Actual_Code
5S,5S,5S,1.5.3
AACOPIA1_I,Copia,Copia,1.1.1
hAT-9_XT,hAT,hAT,2.1.1.2
```

## 🏗️ Estrutura do Projeto

```
te_eval_tool/
├── 📄 te_eval_cli.py              # Interface principal
├── 📄 env_manager.py              # Gerenciador de ambientes
├── 📄 fasta_label_mapper.py       # Mapeamento automático
├── 📄 metrics_evaluator.py        # Cálculo de métricas
├── 📁 ClassifyTE/                 # Código do ClassifyTE
│   ├── generate_feature_file.py
│   ├── evaluate.py
│   ├── HierStack/
│   └── models/
├── 📁 data/                       # Datasets
│   ├── default_dataset.fasta
│   └── demo_features.fasta
├── 📁 nodes/                      # Arquivos de hierarquia
│   ├── tree.txt
│   ├── node.txt
│   └── node_*.txt
├── 📁 model_envs/                 # Ambientes virtuais isolados
├── 📁 results/                    # Resultados de execuções
└── 📄 README.md                   # Este arquivo
```

## 🔬 Exemplos Avançados

### Análise Comparativa de Algoritmos
```bash
# Executar com diferentes algoritmos
python3 te_eval_cli.py run \
  --model classifyte \
  --input data/benchmark.fasta \
  --output results/lcpnb_analysis \
  --algorithm lcpnb \
  --auto-label

python3 te_eval_cli.py run \
  --model classifyte \
  --input data/benchmark.fasta \
  --output results/nllcpn_analysis \
  --algorithm nllcpn \
  --auto-label

# Comparar resultados
python3 te_eval_cli.py compare \
  --results-dir results/ \
  --metric f1_macro \
  --output algorithm_comparison
```

### Validação de Dataset Customizado
```bash
# 1. Validar formato
python3 te_eval_cli.py validate \
  --input data/custom_dataset.fasta \
  --detailed

# 2. Testar mapeamento
python3 te_eval_cli.py map-labels \
  --fasta data/custom_dataset.fasta \
  --validate-only

# 3. Executar análise completa
python3 te_eval_cli.py run \
  --model classifyte \
  --input data/custom_dataset.fasta \
  --output results/custom_analysis \
  --auto-label \
  --tree-file custom_hierarchy.txt
```

### Avaliação de Modelos Externos
```bash
# Para predições de modelos externos (formato CSV)
python3 te_eval_cli.py map-labels \
  --fasta data/original_sequences.fasta \
  --predictions external_predictions.csv

python3 te_eval_cli.py evaluate \
  --predictions external_predictions.csv \
  --output external_evaluation \
  --format detailed
```

## 🔧 Personalização

### Adicionando Novos Modelos

1. **Implementar interface base:**
```python
# models/novo_modelo.py
from models.base_model import TEModel

class NovoModelo(TEModel):
    def setup_environment(self):
        # Configuração do ambiente
        pass
    
    def preprocess(self, input_path, output_dir):
        # Pré-processamento específico
        pass
    
    # ... outros métodos
```

2. **Configurar ambiente:**
```python
# env_manager.py
"novo_modelo": {
    "env_name": "novo_modelo_env",
    "requirements": ["tensorflow>=2.8.0"],
    "python_version": "3.9"
}
```

3. **Registrar no CLI:**
```python
# te_eval_cli.py
@click.option('--model', type=click.Choice(['classifyte', 'novo_modelo']))
```

### Customizando Métricas

Edite `metrics_evaluator.py` para adicionar novas métricas:
```python
def calculate_custom_metric(self, y_true, y_pred):
    # Sua métrica customizada
    return custom_score
```

## 📚 Contexto Acadêmico

Esta ferramenta foi desenvolvida como parte da dissertação:

**"Proposta de pipeline padronizada para testes de modelos baseados em inteligência artificial para a classificação de elementos transponíveis"**

- **Autor:** Gabriel Carneiro de Arruda.
- **Orientador:** Alceu de Souza Britto Jr.
- **Coorientador:** Adriano Ferassa.
- **Programa:** Mestrado em Computação Aplicada - UEPG
- **Ano:** 2025

### 📖 Publicações Relacionadas

A metodologia e resultados desta ferramenta contribuem para:
- Padronização de avaliação em bioinformática
- Reprodutibilidade em pesquisa de IA aplicada à genômica
- Benchmarking de modelos de classificação hierárquica

## 🤝 Contribuição

Contribuições são bem-vindas! Para contribuir:

1. **Fork** o projeto
2. **Crie** uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. **Commit** suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. **Push** para a branch (`git push origin feature/nova-feature`)
5. **Abra** um Pull Request

### 🐛 Reportando Bugs

Use as [Issues do GitHub](https://github.com/010010110/te_eval_tool/issues) para:
- Reportar bugs
- Solicitar novas funcionalidades
- Discutir melhorias

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

<p align="center">
  Desenvolvido com 💙 para a comunidade científica<br>
  <sub>TE Evaluation Tool v1.0 - 2025</sub>
</p>