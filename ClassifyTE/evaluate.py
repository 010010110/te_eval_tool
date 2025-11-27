import numpy as np
import pandas as pd
import sys
import os
import csv
import time
import argparse
from pathlib import Path  # Usar pathlib para caminhos mais robustos
from sklearn.linear_model import LogisticRegression
import pickle
from HierStack import hierarchy as hie
from HierStack import lcpnb as lcpnb
from HierStack import nllcpn as nllcpn
from HierStack.stackingClassifier import *

# --- INÍCIO DAS MODIFICAÇÕES ---
# Obter o diretório onde este script (evaluate.py) está localizado
SCRIPT_DIR = Path(__file__).parent.resolve()
# Assumir que a raiz do projeto te_eval_tool está dois níveis acima
PROJECT_ROOT = SCRIPT_DIR.parent

# Verificar se a estrutura esperada existe
if not (PROJECT_ROOT / "nodes").exists():
    # Se não encontrar 'nodes', talvez o script esteja na raiz do ClassifyTE clone?
    # Vamos assumir que 'nodes' está no diretório pai do diretório do script.
    PROJECT_ROOT = SCRIPT_DIR.parent # Ajuste se necessário

# --- FIM DAS MODIFICAÇÕES ---

def getSequenceName(feature_dir_path):
    """
    Obtém os nomes das sequências a partir dos arquivos FASTA originais
    usados para gerar as features. Assume uma estrutura específica do kanalyze.
    """
    # Construir caminho absoluto para a pasta input_data do kanalyze
    input_files_dir = feature_dir_path / "kanalyze-2.0.0" / "input_data"
    
    seqIDs = []
    if not input_files_dir.exists():
        print(f"⚠️ Diretório de input do kanalyze não encontrado: {input_files_dir}")
        return seqIDs # Retorna lista vazia se não encontrar

    try:
        files = sorted([f for f in input_files_dir.iterdir() if f.is_file()])
        for file_path in files:
            try:
                with open(file_path, "r") as f:
                    header = f.readline()
                    if header.startswith(">"):
                        # Remove '>' e pega a parte antes do primeiro espaço/tab
                        ID = header[1:].strip().split()[0] 
                        seqIDs.append(ID)
                    else:
                         print(f"⚠️ Arquivo inesperado ou sem cabeçalho FASTA em {file_path}")
            except Exception as e:
                print(f"⚠️ Erro ao ler o arquivo {file_path}: {e}")
                
    except Exception as e:
        print(f"⚠️ Erro ao listar arquivos em {input_files_dir}: {e}")

    return seqIDs

def getLabel(content, predicted_code):
    """Obtém o nome do label a partir do código numérico."""
    # Garante que estamos comparando strings
    predicted_code_str = str(predicted_code) 
    return content.get(predicted_code_str, "").strip("\n") # Usa .get para evitar erro se código não existe

def getCodeLabel(tree_file_path):
    """Carrega o mapeamento codigo -> label do arquivo tree.txt."""
    content = {}
    try:
        with open(tree_file_path, "r") as f:
            for line in f:
                data = line.strip().split(",")
                if len(data) >= 2:
                    code, label = data[0].strip(), data[1].strip()
                    content[code] = label
    except FileNotFoundError:
        print(f"⚠️ Arquivo tree.txt não encontrado em: {tree_file_path}")
    except Exception as e:
        print(f"⚠️ Erro ao ler o arquivo tree.txt: {e}")
    return content

def evaluate_model(test_data, parent_classifiers, algorithm, h):
    """Executa a classificação hierárquica."""
    labels_evaluate = []
    # Seleciona apenas as colunas de features (assumindo que são as primeiras)
    # pow(4,2) + pow(4,3) + pow(4,4) = 16 + 64 + 256 = 336
    num_features = 336 
    if test_data.shape[1] < num_features:
         print(f"⚠️ Aviso: Número de colunas no CSV ({test_data.shape[1]}) é menor que o esperado ({num_features}). Usando todas as colunas disponíveis.")
         num_features = test_data.shape[1]

    feature_data = test_data.iloc[:, 0:num_features].values

    for i in range(len(feature_data)):
        if algorithm == "lcpnb":
            c = lcpnb.lcpnb(h)
        elif algorithm == "nllcpn":
            c = nllcpn.nllcpn(h)
        else:
             print(f"⚠️ Algoritmo desconhecido: {algorithm}. Usando lcpnb como padrão.")
             c = lcpnb.lcpnb(h) # Fallback para lcpnb
             
        try:
             # Garante que os dados são numéricos e no formato correto
             sample = np.array(feature_data[i], dtype=float).reshape(1, -1)
             predicted = c.classify(sample, parent_classifiers)
             labels_evaluate.append(predicted)
        except Exception as e:
             print(f"⚠️ Erro ao classificar amostra {i}: {e}")
             labels_evaluate.append([]) # Adiciona lista vazia em caso de erro

    return labels_evaluate

def main(h, data, algorithm, modelname, feature_dir_path):
    """Função principal de avaliação."""
    # --- CAMINHO DO MODELO CORRIGIDO ---
    model_path = SCRIPT_DIR / "models" / modelname # Relativo ao script evaluate.py
    
    # Verifica se o arquivo do modelo existe ANTES de tentar carregar
    if not model_path.exists():
        print(f"❌ Erro Crítico: Arquivo do modelo não encontrado em: {model_path}")
        print(f"   Verifique se o arquivo '{modelname}' existe na pasta '{SCRIPT_DIR / 'models'}'.")
        # Tenta procurar na pasta do projeto como fallback (caso a estrutura seja diferente)
        fallback_model_path = PROJECT_ROOT / "ClassifyTE" / "models" / modelname
        if fallback_model_path.exists():
             print(f"   Tentando caminho alternativo: {fallback_model_path}")
             model_path = fallback_model_path
        else:
            print(f"   Caminho alternativo também falhou. Saindo.")
            sys.exit(1) # Aborta a execução se o modelo não for encontrado

    print(f"🧠 Carregando modelo de: {model_path}")
    try:
        with open(model_path, 'rb') as fb:
            parent_classifiers = pickle.load(fb)
    except FileNotFoundError:
         # Redundante por causa da verificação anterior, mas seguro
         print(f"❌ Erro Crítico: Arquivo do modelo não encontrado ao tentar abrir: {model_path}")
         sys.exit(1)
    except EOFError:
        print(f"❌ Erro Crítico: Arquivo do modelo ({model_path}) parece estar vazio ou corrompido.")
        print(f"   Verifique o download (git lfs pull) e o tamanho do arquivo.")
        sys.exit(1)
    except Exception as e:
         print(f"❌ Erro Crítico inesperado ao carregar o modelo: {e}")
         sys.exit(1)

    print("--------------------------- Avaliação Iniciada ----------------------------\n")
    # Passar feature_dir_path para a função que precisa dela
    # A função evaluate_model não precisa mais do feature_dir_path
    labels_test = evaluate_model(data, parent_classifiers, algorithm, h) 
    return labels_test

if __name__ == '__main__':
    # Usar argparse para melhor manuseio de argumentos
    parser = argparse.ArgumentParser(description="Executa a predição ClassifyTE em um arquivo de features.")
    parser.add_argument("-f", "--filename", required=True, help="Nome do arquivo CSV de features (gerado por generate_feature_file.py)")
    parser.add_argument("-d", "--featuredir", required=True, help="Diretório onde as features foram geradas (contém a estrutura kanalyze)")
    parser.add_argument("-n", "--node_file", default="node.txt", help="Nome do arquivo de nós da hierarquia (dentro da pasta nodes)")
    parser.add_argument("-m", "--modelname", required=True, help="Nome do arquivo do modelo .pkl (dentro da pasta models)")
    parser.add_argument("-a", "--algorithm", default='lcpnb', choices=['lcpnb', 'nllcpn'], help="Algoritmo de classificação hierárquica (lcpnb ou nllcpn)")
    parser.add_argument("-o", "--outputdir", default="outputs", help="Diretório para salvar os resultados")

    args = parser.parse_args()

    # --- CAMINHOS CONSTRUÍDOS DE FORMA ROBUSTA ---
    # Caminho absoluto para o arquivo de features CSV
    # Assume que o nome do arquivo é passado corretamente pelo chamador (te_eval_cli.py)
    # Vamos construir o caminho a partir do diretório de execução atual
    dataset_path = Path.cwd() / args.filename 
    if not dataset_path.exists():
         # Se não encontrar relativo ao CWD, tenta relativo ao diretório de features
         feature_dir_path_abs = Path(args.featuredir).resolve() # Garante caminho absoluto
         dataset_path_alt = feature_dir_path_abs / args.filename
         if dataset_path_alt.exists():
              dataset_path = dataset_path_alt
         else:
              print(f"❌ Erro Crítico: Arquivo de features CSV não encontrado em {dataset_path} ou {dataset_path_alt}")
              sys.exit(1)

    # Caminho absoluto para o arquivo de nós
    node_path = PROJECT_ROOT / "nodes" / args.node_file
    if not node_path.exists():
         print(f"❌ Erro Crítico: Arquivo de nós não encontrado em {node_path}")
         sys.exit(1)

    # Caminho absoluto para o arquivo tree.txt
    tree_path = PROJECT_ROOT / "nodes" / "tree.txt"
    if not tree_path.exists():
         print(f"❌ Erro Crítico: Arquivo tree.txt não encontrado em {tree_path}")
         # Não abortar, mas o mapeamento de labels ficará vazio
         
    # Caminho absoluto para o diretório de features (para getSequenceName)
    feature_dir_path_abs = Path(args.featuredir).resolve() # Garante caminho absoluto
    if not feature_dir_path_abs.exists():
         print(f"❌ Erro Crítico: Diretório de features não encontrado: {feature_dir_path_abs}")
         sys.exit(1)

    # Caminho absoluto para o diretório de saída
    output_path_abs = Path(args.outputdir).resolve()
    output_path_abs.mkdir(parents=True, exist_ok=True) # Cria o diretório se não existir

    print(f"📂 Usando arquivo de features: {dataset_path}")
    print(f"🌳 Usando arquivo de nós: {node_path}")
    print(f"🌲 Usando arquivo tree: {tree_path}")
    print(f"⚙️ Usando diretório de features: {feature_dir_path_abs}")
    print(f"📄 Usando diretório de saída: {output_path_abs}")

    # Carregar nomes das sequências ANTES de carregar dados (mais eficiente)
    seq_names = getSequenceName(feature_dir_path_abs) 
    if not seq_names:
         print(f"❌ Erro Crítico: Nenhum nome de sequência encontrado. Verifique a estrutura em {feature_dir_path_abs / 'kanalyze-2.0.0' / 'input_data'}")
         sys.exit(1)

    # Carregar hierarquia
    h = hie.hierarchy(str(node_path)) # HierStack pode esperar string

    start_time = time.time()

    # Carregar dados do CSV
    try:
        data = pd.read_csv(dataset_path, low_memory=False)
        # Verificar se o número de linhas corresponde ao número de sequências
        if len(data) != len(seq_names):
             print(f"⚠️ Aviso: Número de sequências no CSV ({len(data)}) não bate com o número de arquivos FASTA ({len(seq_names)}). Os resultados podem estar desalinhados.")
    except FileNotFoundError:
         print(f"❌ Erro Crítico: Arquivo de features CSV não encontrado ao tentar ler: {dataset_path}")
         sys.exit(1)
    except Exception as e:
         print(f"❌ Erro Crítico ao ler o arquivo CSV de features: {e}")
         sys.exit(1)

    # Carregar mapeamento codigo -> label
    content = getCodeLabel(tree_path)

    # Executar a predição principal
    hier_label = main(h, data, args.algorithm, args.modelname, feature_dir_path_abs) # Passa feature_dir_path_abs

    # --- NOMES DE ARQUIVOS DE SAÍDA CORRIGIDOS ---
    # Usar o nome base do arquivo de features para nomear a saída
    base_feature_name = dataset_path.stem 
    outputs_filename = output_path_abs / f"predicted_{base_feature_name}.csv"
    outputs_txt = output_path_abs / f"predicted_{base_feature_name}_details.txt"

    print(f"💾 Salvando resultados em {output_path_abs}...")

    # --- ESCRITA DOS RESULTADOS ---
    try:
        with open(outputs_filename, 'w', newline='') as f_csv, \
             open(outputs_txt, 'w') as f_txt:

            csv_writer = csv.writer(f_csv)
            csv_writer.writerow(["Sequence ID", "Predicted_Label_Code", "Predicted_Label_Name"]) # Cabeçalho CSV
            f_txt.write("Prediction Results\n")
            f_txt.write("=" * 80 + "\n\n")

            # Garantir que temos o mesmo número de predições e nomes
            num_results = min(len(hier_label), len(seq_names))
            if len(hier_label) != len(seq_names):
                print(f"⚠️ Aviso: Número de predições ({len(hier_label)}) diferente do número de sequências ({len(seq_names)}). Salvando {num_results} resultados.")

            for count in range(num_results):
                k = hier_label[count]
                seq_id = seq_names[count] # Usar o ID já extraído corretamente

                predicted_label_code = k[-1] if k else ""
                predicted_label_name = getLabel(content, predicted_label_code)

                f_txt.write(f"Sequence ID: {seq_id}\n")
                f_txt.write("Prediction Path:\n")
                
                path_str = []
                for i in k:
                    label = getLabel(content, i)
                    f_txt.write(f"  Level {i} : {label}\n")
                    path_str.append(label if label else str(i))
                
                f_txt.write(f"Final Predicted Code: {predicted_label_code}\n")
                f_txt.write(f"Final Predicted Label: {predicted_label_name}\n\n")
                f_txt.write("-" * 80 + "\n\n")

                # Escrever no CSV
                csv_writer.writerow([seq_id, predicted_label_code, predicted_label_name])
                
                # Opcional: Imprimir no console (pode ser muito verbose)
                # print(f"Prediction for {seq_id}: {' -> '.join(path_str)} (Final: {predicted_label_name})")

    except Exception as e:
         print(f"❌ Erro ao escrever arquivos de saída: {e}")

    elapsed_time = time.time() - start_time
    print(f"\n✅ Predição concluída!")
    print(f"   Resultados salvos em '{outputs_filename}' e '{outputs_txt}'")
    print(f"   Tempo total decorrido: {elapsed_time:.2f} segundos")
