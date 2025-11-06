import os
import random
from pathlib import Path
from Bio import SeqIO
import sys
import shutil

# Importa o mapper que já corrigimos e refatoramos
try:
    from fasta_label_mapper import FASTALabelMapper
except ImportError:
    print("❌ Erro: Não foi possível encontrar 'fasta_label_mapper.py'.")
    print("   Certifique-se que este script ('preparar_dataset.py') está na mesma pasta que 'fasta_label_mapper.py'.")
    sys.exit(1)

# --- Configuração ---
ARQUIVO_DE_ENTRADA = 'data/subset_db.fasta'
PASTA_RAIZ_SAIDA = 'Dataset' # Onde o TERL espera os dados
TAXA_TREINO = 0.8 # 80% treino, 20% teste
# --------------------

print("Iniciando preparação de dados para o TERL...")

# 1. Inicializar o mapper
try:
    # Ele usará o 'nodes/tree.txt' e 'mapper_config.json' da pasta raiz
    mapper = FASTALabelMapper(base_dir=str(Path.cwd()))
    if not mapper.hierarchy_map:
        print("❌ Erro: hierarchy_map (tree.txt) não foi carregado. Saindo.")
        sys.exit(1)
except Exception as e:
    print(f"❌ Erro ao inicializar o FASTALabelMapper: {e}")
    print("   Certifique-se que 'fasta_label_mapper.py', 'mapper_config.json' e 'nodes/tree.txt' estão na pasta raiz.")
    sys.exit(1)

print(f"Lendo e classificando sequências de '{ARQUIVO_DE_ENTRADA}'...")

sequencias_por_classe = {}
comprimento_maximo = 0 # O TERL precisa disso

try:
    for record in SeqIO.parse(ARQUIVO_DE_ENTRADA, "fasta"):
        # Recria o cabeçalho exatamente como o mapper espera
        header = ">" + record.description 
        
        # Usa a mesma lógica de inferência 100% correta do mapper
        parsed = mapper.parse_fasta_header(header)
        hierarchical_code = mapper.map_to_hierarchical_code(parsed)
        nome_da_classe = mapper.hierarchy_map.get(str(hierarchical_code), 'Unknown') if hierarchical_code else 'Unknown'

        # Não vamos treinar o modelo com sequências "Unknown"
        if nome_da_classe == 'Unknown':
            continue
            
        # Adiciona à lista da classe
        if nome_da_classe not in sequencias_por_classe:
            sequencias_por_classe[nome_da_classe] = []
        sequencias_por_classe[nome_da_classe].append(record)
        
        # Encontra o comprimento máximo
        if len(record.seq) > comprimento_maximo:
            comprimento_maximo = len(record.seq)

except FileNotFoundError:
    print(f"ERRO: Arquivo '{ARQUIVO_DE_ENTRADA}' não encontrado.")
    sys.exit(1)
except Exception as e:
    print(f"ERRO inesperado ao ler o FASTA: {e}")
    sys.exit(1)

print("\nSeparação por classe (Real) concluída. Classes encontradas:")
total_seqs = 0
for classe, seqs in sequencias_por_classe.items():
    print(f"- {classe}: {len(seqs)} sequências")
    total_seqs += len(seqs)
    
if not sequencias_por_classe:
    print("❌ ERRO: Nenhuma classe foi mapeada. Verifique seu fasta_label_mapper.py e mapper_config.json.")
    sys.exit(1)
    
print(f"\nTotal de sequências para treinar/testar: {total_seqs}")
print(f"Comprimento máximo encontrado: {comprimento_maximo} bases.")
print("Dividindo em treino/teste...")

train_path = os.path.join(PASTA_RAIZ_SAIDA, 'Train')
test_path = os.path.join(PASTA_RAIZ_SAIDA, 'Test')

# Limpa pastas antigas
if os.path.exists(PASTA_RAIZ_SAIDA):
    shutil.rmtree(PASTA_RAIZ_SAIDA)
os.makedirs(train_path, exist_ok=True)
os.makedirs(test_path, exist_ok=True)


dados_treino = {}
dados_teste = {}

for nome_da_classe, lista_de_sequencias in sequencias_por_classe.items():
    random.shuffle(lista_de_sequencias)
    ponto_de_corte = int(len(lista_de_sequencias) * TAXA_TREINO)
    
    dados_treino[nome_da_classe] = lista_de_sequencias[:ponto_de_corte]
    dados_teste[nome_da_classe] = lista_de_sequencias[ponto_de_corte:]

def salvar_arquivos_processados(caminho_pasta, dados_para_salvar):
    """Salva os arquivos FASTA no formato que o TERL espera."""
    
    classes_salvas = set()
    for nome_da_classe, lista_de_sequencias in dados_para_salvar.items():
        # O TERL não lida bem com '/' no nome do arquivo
        nome_arquivo_seguro = nome_da_classe.replace('/', '_').replace('?', 'desconhecido')
        caminho_arquivo_saida = os.path.join(caminho_pasta, f"{nome_arquivo_seguro}.fa")
        
        sequencias_processadas = []
        
        for record in lista_de_sequencias:
            # O TERL precisa de padding/truncamento
            seq_original = record.seq
            seq_nova = str(seq_original).upper()
            
            if len(seq_nova) < comprimento_maximo:
                seq_nova = seq_nova + 'N' * (comprimento_maximo - len(seq_nova))
            elif len(seq_nova) > comprimento_maximo:
                seq_nova = seq_nova[:comprimento_maximo]
            
            # Recria o record com a sequência modificada
            record.seq = type(seq_original)(seq_nova)
            sequencias_processadas.append(record)
        
        if sequencias_processadas: # Só salva se houver sequências
            SeqIO.write(sequencias_processadas, caminho_arquivo_saida, "fasta")
            print(f" -> Arquivo '{caminho_arquivo_saida}' salvo com {len(sequencias_processadas)} sequências.")
            classes_salvas.add(nome_da_classe)
            
    return classes_salvas
        
print("\nProcessando e salvando arquivos de TREINO...")
classes_treino = salvar_arquivos_processados(train_path, dados_treino)

print("\nProcessando e salvando arquivos de TESTE...")
classes_teste = salvar_arquivos_processados(test_path, dados_teste)

# Criar arquivos vazios para classes que não caíram no split (requisito do TERL)
print("\nSincronizando arquivos (o TERL precisa que os nomes dos arquivos batam)...")
todas_classes = classes_treino.union(classes_teste)
for nome_da_classe in todas_classes:
    nome_arquivo_seguro = nome_da_classe.replace('/', '_').replace('?', 'desconhecido')
    
    caminho_teste = os.path.join(test_path, f"{nome_arquivo_seguro}.fa")
    if not os.path.exists(caminho_teste):
        SeqIO.write([], caminho_teste, "fasta") # Cria arquivo vazio
        print(f" -> Arquivo de teste vazio criado: {caminho_teste}")
        
    caminho_treino = os.path.join(train_path, f"{nome_arquivo_seguro}.fa")
    if not os.path.exists(caminho_treino):
        SeqIO.write([], caminho_treino, "fasta") # Cria arquivo vazio
        print(f" -> Arquivo de treino vazio criado: {caminho_treino}")


print("\nProcessamento concluído com sucesso!")
print(f"Seus dados de treino e teste estão prontos dentro da pasta '{PASTA_RAIZ_SAIDA}'.")
