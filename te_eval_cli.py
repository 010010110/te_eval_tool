import click
import subprocess
import os
import sys
import shutil
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from metrics_evaluator import TEMetricsEvaluator

# Imports condicionais para evitar erros se módulos não existirem
try:
    from env_manager import EnvironmentManager
except ImportError:
    print("⚠️ env_manager.py não encontrado. Alguns recursos podem não funcionar.")
    EnvironmentManager = None

try:
    # CORREÇÃO: O script está na raiz, então importamos de 'src.lib'
    from fasta_label_mapper import FASTALabelMapper 
except ImportError:
    print("⚠️ fasta_label_mapper.py não encontrado. Mapeamento automático não disponível.")
    FASTALabelMapper = None

@click.group()
@click.version_option(version='5.0.1')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def cli(ctx, verbose):
    """
    TE Evaluation Tool v5.0 - Ferramenta padronizada para avaliação de 
    classificadores de elementos transponíveis com métricas completas
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if verbose:
        click.echo("🔧 Modo verboso ativado")

# ==================== COMANDOS DE GERENCIAMENTO DE AMBIENTES ====================

@cli.group('env')
def env_commands():
    """Comandos para gerenciamento de ambientes virtuais"""
    pass

@env_commands.command('setup')
@click.option('--model', type=click.Choice(['classifyte', 'terl', 'all']), default='all', 
              help='Modelo específico ou todos')
def setup_envs(model):
    """Configurar ambientes virtuais para modelos"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    
    if model == 'all':
        click.echo("🚀 Configurando ambientes para todos os modelos...")
        env_manager.setup_all_environments()
    else:
        click.echo(f"🚀 Configurando ambiente para {model}...")
        try:
            env_manager.create_environment(model)
            click.echo(f"✅ Ambiente {model} configurado com sucesso!")
        except Exception as e:
            click.echo(f"❌ Erro: {str(e)}")
            sys.exit(1)

@env_commands.command('list')
def list_envs():
    """Listar ambientes disponíveis"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    env_manager.list_environments()

@env_commands.command('clean')
@click.confirmation_option(prompt='Tem certeza que deseja remover todos os ambientes?')
def clean_envs():
    """Remover todos os ambientes virtuais"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    env_manager.clean_environments()

# ==================== COMANDOS PRINCIPAIS ====================
# (Os comandos 'validate' e outros não modificados estão omitidos por brevidade)
@cli.command()
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True), 
              help='Arquivo FASTA de entrada')
# ... (Resto do comando 'validate' omitido) ...
def validate(ctx, input_file, format_type, detailed, verbose):
    """Validar arquivo de entrada"""
    click.echo(f"🔍 Validando {input_file}...")
    # (A lógica de validação completa é omitida para economizar espaço)
    pass


@cli.command()
@click.option('--model', default='classifyte', 
              type=click.Choice(['classifyte', 'inpactor2', 'terl']), 
              help='Modelo a ser executado')
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True), 
              help='Arquivo FASTA de entrada')
@click.option('--output', 'output_dir', required=True, help='Diretório de saída')
@click.option('--algorithm', default='lcpnb', 
              type=click.Choice(['lcpnb', 'nllcpn']), 
              help='Algoritmo hierárquico (ClassifyTE)')
@click.option('--model-file', default='ClassifyTE_combined.pkl', 
              help='Arquivo do modelo (.pkl) ou diretório (TERL)')
@click.option('--node-file', default='node.txt', help='Arquivo de nós hierárquicos')
@click.option('--skip-evaluation', is_flag=True, 
              help='Pular avaliação automática de métricas')
@click.option('--clean', is_flag=True, help='Limpar arquivos temporários após execução')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.option('--auto-label', is_flag=True, 
              help='Mapear automaticamente labels do FASTA para avaliação')
@click.pass_context
def run(ctx, model, input_file, output_dir, algorithm, model_file, node_file, 
        skip_evaluation, clean, verbose, auto_label):
    """Executar classificação usando ambiente específico do modelo"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    start_time = datetime.now()
    
    if not EnvironmentManager:
        click.echo("⚠️ Ambiente isolado não disponível. Usando Python global.")
        python_path = "python3"
    else:
        env_manager = EnvironmentManager()
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    log_data = {
        "start_time": start_time.isoformat(),
        "model": model,
        "input_file": str(input_file),
        "output_dir": str(output_dir),
        "algorithm": algorithm,
        "model_file": model_file,
        "node_file": node_file
    }
    
    click.echo(f"🔬 Executando {model} com {input_file}")
    click.echo(f"🌍 Usando ambiente específico do {model}")
    click.echo(f"📁 Resultados em: {output_dir}")
    
    try:
        if EnvironmentManager:
            python_path = env_manager.get_python_path(model)
            click.echo(f"🐍 Python: {python_path}")
        
        if model == 'classifyte':
            success = run_classifyte(python_path, input_file, output_dir, algorithm, 
                                     model_file, node_file, verbose, clean)
        elif model == 'inpactor2':
            click.echo("🚧 Inpactor2 ainda não implementado")
            success = False
        
        # --- INÍCIO DA CORREÇÃO (Chamada ao run_terl) ---
        elif model == 'terl':
            # Passa a variável 'model_file' (da opção --model-file)
            # como o 4º argumento posicional (terl_model_path)
            success = run_terl(python_path, input_file, output_dir, 
                               model_file, 
                               verbose=verbose, clean_temp=clean)
        # --- FIM DA CORREÇÃO ---
            
        else:
            click.echo(f"❌ Modelo '{model}' não reconhecido")
            success = False
        
        end_time = datetime.now()
        log_data.update({
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "success": success
        })
        
        log_file = output_path / "execution_log.json"
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        if success:
            click.echo(f"\n✅ Classificação {model} concluída com sucesso!")
            click.echo(f"⏱️  Tempo total: {(end_time - start_time).total_seconds():.1f}s")
            
            predictions_file = output_path / "predicted_results.csv"
            if auto_label and FASTALabelMapper and predictions_file.exists():
                click.echo(f"\n🏷️  Mapeando labels automaticamente...")
                
                # --- INÍCIO DA CORREÇÃO (Chamada ao Mapper) ---
                try:
                    # 1. Instanciar o mapper. Ele encontrará o base_dir e o tree.txt sozinho.
                    # Passa o diretório raiz atual para garantir que ele encontre 'nodes/tree.txt'
                    base_dir = str(Path.cwd())
                    mapper = FASTALabelMapper(base_dir=base_dir) 
                    
                    # 2. Obter caminhos absolutos e passá-los
                    abs_pred_path = predictions_file.resolve()
                    abs_fasta_path = Path(input_file).resolve()
                    
                    map_success = mapper.add_actual_labels_to_predictions(
                        str(abs_pred_path), 
                        str(abs_fasta_path)
                    )
                    
                    if map_success:
                        click.echo("✅ Labels mapeados com sucesso!")
                    else:
                        click.echo("⚠️ Falha no mapeamento de labels. A avaliação pode ficar incompleta.")
                        
                except Exception as e:
                    click.echo(f"⚠️ Erro no mapeamento automático: {str(e)}")
                # --- FIM DA CORREÇÃO ---
            
            if not skip_evaluation and TEMetricsEvaluator and predictions_file.exists():
                click.echo(f"\n🔬 Executando avaliação automática...")
                try:
                    evaluator = TEMetricsEvaluator()
                    evaluator.evaluate_predictions(str(predictions_file), str(output_path))
                    click.echo("✅ Avaliação automática concluída!")
                except Exception as e:
                    click.echo(f"⚠️ Erro na avaliação automática: {str(e)}")
        else:
            click.echo(f"❌ Falha na execução do {model}")
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"❌ Erro: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def run_classifyte(python_path, input_file, output_dir, algorithm, model_file, 
                   node_file, verbose=False, clean_temp=False):
    """Executa ClassifyTE com ambiente específico"""
    
    input_path = Path(input_file)
    output_path = Path(output_dir)
    
    model_path = Path("ClassifyTE/models") / model_file
    if not model_path.exists():
        click.echo(f"❌ Modelo não encontrado: {model_path}")
        return False
    
    nodes_path = Path("ClassifyTE/nodes") / node_file
    if not nodes_path.exists():
        nodes_path = Path("nodes") / node_file
        if not nodes_path.exists():
            click.echo(f"❌ Arquivo de nós não encontrado: {node_file}")
            return False
    
    target_fasta = Path("ClassifyTE/data") / input_path.name
    if input_path.resolve() != target_fasta.resolve():
        shutil.copy(input_path, target_fasta)
        if verbose:
            click.echo(f"📄 FASTA copiado para {target_fasta}")
    
    base_name = input_path.stem
    features_file = f"{base_name}.csv"
    features_dir = f"{base_name}"
    
    temp_files = [
        Path("ClassifyTE") / features_dir,
        Path("ClassifyTE/data") / features_file
    ]
    
    for temp_file in temp_files:
        if temp_file.exists():
            if temp_file.is_dir():
                if verbose:
                    click.echo(f"🧹 Removendo diretório: {temp_file}")
                shutil.rmtree(temp_file)
            else:
                if verbose:
                    click.echo(f"🧹 Removendo arquivo: {temp_file}")
                temp_file.unlink()
    
    click.echo("⚙️ Gerando features...")
    cmd_generate = [
        python_path, "generate_feature_file.py",
        "-f", input_path.name,
        "-o", features_file,
        "-d", features_dir
    ]
    
    if verbose:
        click.echo(f"   Comando: {' '.join(cmd_generate)}")
    
    result = subprocess.run(cmd_generate, cwd="ClassifyTE", capture_output=True, text=True)
    
    if result.returncode != 0:
        click.echo(f"❌ Erro na geração de features:")
        click.echo(f"   STDOUT: {result.stdout}")
        click.echo(f"   STDERR: {result.stderr}")
        return False
    
    click.echo(f"✅ Features geradas: {features_file}")
    
    click.echo("🧠 Executando predição...")
    cmd_evaluate = [
        python_path, "evaluate.py",
        "-f", features_file,
        "-d", features_dir,
        "-n", node_file,
        "-m", model_file,
        "-a", algorithm
    ]
    
    if verbose:
        click.echo(f"   Comando: {' '.join(cmd_evaluate)}")
    
    result = subprocess.run(cmd_evaluate, cwd="ClassifyTE", capture_output=True, text=True)
    
    if result.returncode != 0:
        click.echo(f"❌ Erro na predição:")
        click.echo(f"   STDOUT: {result.stdout}")
        click.echo(f"   STDERR: {result.stderr}")
        return False
    
    if verbose:
        click.echo("✅ Predição executada com sucesso")
    
    expected_result = Path("ClassifyTE/outputs") / f"predicted_out_{features_dir}.csv"
    
    if not expected_result.exists():
        outputs_dir = Path("ClassifyTE/outputs")
        if outputs_dir.exists():
            predicted_files = list(outputs_dir.glob("predicted_*.csv"))
            if predicted_files:
                expected_result = max(predicted_files, key=os.path.getmtime)
                if verbose:
                    click.echo(f"📄 Usando arquivo mais recente: {expected_result}")
            else:
                click.echo("❌ Nenhum arquivo de resultado encontrado")
                return False
        else:
            click.echo("❌ Diretório outputs/ não encontrado")
            return False
    
    final_file = output_path / "predicted_results.csv"
    shutil.copy(expected_result, final_file)
    
    try:
        df = pd.read_csv(final_file)
        click.echo(f"\n📊 Resultados processados: {len(df)} sequências")
        
        if "Predicted label" in df.columns:
            predictions = df["Predicted label"].value_counts()
            click.echo("   Distribuição de predições:")
            for pred, count in predictions.head().items():
                click.echo(f"     {pred}: {count}")
            
            if len(predictions) > 5:
                click.echo(f"     ... e mais {len(predictions) - 5} classes")
        
        metadata = {
            "total_sequences": len(df),
            "model": "classifyte",
            "algorithm": algorithm,
            "model_file": model_file,
            "node_file": node_file,
            "features_generated": True,
            "python_environment": python_path
        }
        
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        if clean_temp:
            click.echo("🧹 Limpando arquivos temporários...")
            for temp_file in temp_files:
                if temp_file.exists():
                    if temp_file.is_dir():
                        shutil.rmtree(temp_file)
                    else:
                        temp_file.unlink()
        
        return True
        
    except Exception as e:
        click.echo(f"⚠️ Erro ao processar resultados: {str(e)}")
        return False

#
# SUBSTITUA A FUNÇÃO 'run_terl' INTEIRA POR ISTO:
#

def run_terl(python_path, input_file, output_dir, terl_model_path, verbose=False, clean_temp=False):
    """Executa TERL com ambiente específico e converte a saída"""

    click.echo("⚙️ Executando TERL...")

    input_path = Path(input_file).resolve()
    output_path = Path(output_dir)

    temp_dir = output_path / "terl_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    model_to_use = terl_model_path

    if not Path(model_to_use).exists():
        click.echo(f"❌ Erro: Modelo TERL não encontrado em: {model_to_use}")
        click.echo(f"   (Você já treinou um modelo? Ex: terl_train.py ... -md {model_to_use})")
        return False

    script_path = "TERL-master/terl_test.py" 
    if not Path(script_path).exists():
        script_path = "TERL/terl_test.py" # Fallback
        if not Path(script_path).exists():
            click.echo(f"❌ Erro: Script 'terl_test.py' não encontrado em: TERL-master/ ou TERL/")
            return False

    # Corrigido: Adiciona o underscore ao prefixo
    temp_prefix = (temp_dir / f"{input_path.stem}_pred_").resolve()
    output_fasta_path = temp_dir / f"{input_path.stem}_pred_{input_path.name}"

    cmd_classify = [
        python_path,
        script_path,
        "-m", model_to_use,
        "-f", str(input_path), 
        "-p", str(temp_prefix), 
        "-q" 
    ]

    if verbose:
        click.echo(f"  Comando: {' '.join(cmd_classify)}")

    result = subprocess.run(cmd_classify, capture_output=True, text=True, cwd=Path.cwd())

    if result.returncode != 0:
        click.echo(f"❌ Erro na classificação do TERL:")
        click.echo(f"  STDOUT: {result.stdout}")
        click.echo(f"  STDERR: {result.stderr}")
        return False

    if not output_fasta_path.exists():
        click.echo(f"❌ Erro: Arquivo de saída do TERL não foi criado em: {output_fasta_path}")
        if verbose:
            click.echo(f"  STDOUT: {result.stdout}")
            click.echo(f"  STDERR: {result.stderr}")
        return False

    click.echo(f"📄 Saída FASTA do TERL gerada.")

    click.echo("🔄 Convertendo saída FASTA do TERL para o formato CSV...")

    # --- INÍCIO DA CORREÇÃO ---
    # Dicionário de classificação do TERL (copiado de terl_test.py)
    classification_map = {
        'Copia': 'Class I\tLTR\tCopia', 'Gypsy': 'Class I\tLTR\tGypsy',
        'Bel-Pao': 'Class I\tLTR\tBel-Pao', 'Retrovirus': 'Class I\tLTR\tRetrovirus',
        'ERV': 'Class I\tLTR\tERV', 'Dirs': 'Class I\tDIRS\tDirs',
        'Ngaro': 'Class I\tDIRS\tNgaro', 'VIPER': 'Class I\tDIRS\tVIPER',
        'Penelope': 'Class I\tPLE\tPenelope', 'R2': 'Class I\tLINE\tR2',
        'RTE': 'Class I\tLINE\tRTE', 'Jockey': 'Class I\tLINE\tJockey',
        'L1': 'Class I\tLINE\tL1', 'I': 'Class I\tLINE\tI',
        'tRNA': 'Class I\tSINE\ttRNA', '7SL': 'Class I\tSINE\t7SL',
        '5S': 'Class I\tSINE\t5S', 'Mariner': 'Class II\tSubclass 1\tTIR\tTc1-Mariner',
        'hAT': 'Class II\tSubclass 1\tTIR\thAT', 'Mutator': 'Class II\tSubclass 1\tTIR\tMutator',
        'Merlin': 'Class II\tSubclass 1\tTIR\tMerlin', 'Transib': 'Class II\tSubclass 1\tTIR\tTransib',
        'P': 'Class II\tSubclass 1\tTIR\tP', 'PiggyBac': 'Class II\tSubclass 1\tTIR\tPiggyBac',
        'PIF-Harbinger': 'Class II\tSubclass 1\tTIR\tPIF-Harbinger', 'CACTA': 'Class II\tSubclass 1\tTIR\tCACTA',
        'Crypton': 'Class II\tSubclass 1\tCrypton\tCrypton', 'Helitron': 'Class II\tSubclass 2\tHelitron\tHelitron',
        'Maverick': 'Class II\tSubclass 2\tMaverick\tMaverick', 'LTR': 'Class I\tLTR',
        'DIRS': 'Class I\tDIRS', 'PLE': 'Class I\tPLE',
        'LINE': 'Class I\tLINE', 'SINE': 'Class I\tSINE',
        'TIR': 'Class II\tSubclass 1\tTIR', 'Subclass 1': 'Class II\tSubclass 1',
        'Subclass 2': 'Class II\tSubclass 2', 'Class I': 'Class I',
        'Class II': 'Class II', 'TRIM': 'TRIM',
        'LARD': 'LARD', 'MITE': 'MITE',
        'SNAC': 'SNAC', 'Random': 'NonTE',

        # Adicionando classes que podem estar faltando do seu dataset de treino
        'Zator': 'Zator', 'Acade': 'Acade', 'Mirage': 'Mirage', 'Chapaev': 'Chapaev',
        'Mu': 'Mu', 't': 't', 'classe': 'classe', 'Helitro': 'Helitro', 'Novosib': 'Novosib',
        'Ginger1': 'Ginger1', 'desconhecido': 'desconhecido', 'Kolobok': 'Kolobok',
        'h': 'h', 'Ginger2': 'Ginger2', 'Crypto': 'Crypto', 'Merli': 'Merli', 'Piggy': 'Piggy',
        'DIR': 'DIR', 'ISL2EU': 'ISL2EU', 'Sol': 'Sol'
    }
    # Criar um mapa reverso (ex: 'Class I\tLTR\tCopia' -> 'Copia')
    reverse_map = {v[0]: k for k, v in classification_map.items()}

    original_ids = []
    predicted_labels = []

    try:
        with open(input_path, 'r') as f_in:
            for line in f_in:
                if line.startswith(">"):
                    original_ids.append(line.strip()[1:]) 

        with open(output_fasta_path, 'r') as f_out:
            for line in f_out:
                if line.startswith(">"):
                    # Cabeçalho do TERL: >[Descrição Longa ou Curta]\t[Contagem]
                    full_description = line.strip()[1:].rsplit('\t', 1)[0]

                    # Tenta converter a descrição longa para curta (ex: 'Class I\tLTR\tCopia' -> 'Copia')
                    # Se já for curta (ex: 'Copia'), o .get() falha
                    # Se falhar, assume que a 'full_description' JÁ É o nome da classe
                    simple_label = reverse_map.get(full_description, full_description)

                    predicted_labels.append(simple_label)

        if len(original_ids) != len(predicted_labels):
            click.echo(f"❌ Erro: Incompatibilidade de contagem de sequências. Entrada: {len(original_ids)}, Saída: {len(predicted_labels)}")
            return False

        df = pd.DataFrame({
            'id': original_ids,
            'Predicted_Label_Name': predicted_labels # Nome da coluna que o evaluator espera
        })

        final_file = output_path / "predicted_results.csv"
        df.to_csv(final_file, index=False)

        click.echo(f"📊 Resultados convertidos e salvos em: {final_file}")

        if clean_temp:
            click.echo("🧹 Limpando arquivos temporários do TERL...")
            shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        click.echo(f"❌ Erro ao converter FASTA do TERL para CSV: {e}")
        return False
# --- FIM DA CORREÇÃO ---


# ==================== COMANDOS DE MAPEAMENTO ====================

@cli.command('map-labels')
@click.option('--fasta', required=True, type=click.Path(exists=True), 
              help='Arquivo FASTA com headers estruturados')
@click.option('--predictions', type=click.Path(exists=True), 
              help='Arquivo CSV de predições para adicionar labels')
@click.option('--output', help='Arquivo de saída (opcional)')
@click.option('--validate-only', is_flag=True, help='Apenas validar mapeamentos')
@click.option('--tree-file', default='nodes/tree.txt', help='Arquivo de hierarquia')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def map_labels(ctx, fasta, predictions, output, validate_only, tree_file, verbose):
    """Mapear headers FASTA para códigos hierárquicos"""
    
    if not FASTALabelMapper:
        click.echo("❌ FASTALabelMapper não disponível")
        sys.exit(1)
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    click.echo(f"🏷️  Mapeando labels de: {fasta}")
    
    try:
        # --- INÍCIO DA CORREÇÃO (Chamada ao Mapper) ---
        base_dir = str(Path.cwd())
        mapper = FASTALabelMapper(base_dir=base_dir, tree_file=tree_file) 
        
        if validate_only:
            mapper.validate_mapping(fasta)
        
        elif predictions:
            click.echo(f"📄 Adicionando labels a: {predictions}")
            
            abs_pred_path = Path(predictions).resolve()
            abs_fasta_path = Path(fasta).resolve()
            
            mapper.add_actual_labels_to_predictions(
                str(abs_pred_path), 
                str(abs_fasta_path)
            )
            
        else:
            output_file = output if output else f"{Path(fasta).stem}_mappings.csv"
            mappings_df = mapper.process_fasta_file(fasta, output_file)
            
            click.echo(f"\n📊 Resumo dos mapeamentos:")
            click.echo(f"   Total: {len(mappings_df)}")
            click.echo(f"   Sucessos: {mappings_df['mapping_success'].sum()}")
            click.echo(f"   Falhas: {(~mappings_df['mapping_success']).sum()}")
        # --- FIM DA CORREÇÃO ---
        
        click.echo("✅ Mapeamento concluído!")
        
    except Exception as e:
        click.echo(f"❌ Erro no mapeamento: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

# ==================== COMANDOS DE AVALIAÇÃO ====================

@cli.command('evaluate')
@click.option('--predictions', required=True, type=click.Path(exists=True), 
              help='Arquivo CSV com predições')
@click.option('--output', 'output_dir', required=True, help='Diretório de saída para métricas')
@click.option('--hierarchy', default='nodes/tree.txt', help='Arquivo de hierarquia')
@click.option('--format', default='detailed', type=click.Choice(['summary', 'detailed', 'json']),
              help='Formato do relatório')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def evaluate_metrics(ctx, predictions, output_dir, hierarchy, format, verbose):
    """Avaliar predições com métricas padronizadas completas"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    if not TEMetricsEvaluator:
        click.echo("❌ TEMetricsEvaluator não disponível")
        sys.exit(1)
    
    click.echo(f"🔬 Avaliando predições: {predictions}")
    click.echo(f"📁 Resultados em: {output_dir}")
    
    try:
        evaluator = TEMetricsEvaluator(hierarchy_file=hierarchy)
        metrics = evaluator.evaluate_predictions(predictions, output_dir)
        
        if isinstance(metrics, dict) and 'accuracy' in metrics:
            
            if format in ['summary', 'detailed']:
                click.echo(f"\n📈 MÉTRICAS PRINCIPAIS:")
                click.echo(f"{'='*50}")
                click.echo(f"🎯 Acurácia: {metrics.get('accuracy', 0.0):.4f}")
                click.echo(f"🎯 Precisão (macro): {metrics.get('precision_macro', 0.0):.4f}")
                click.echo(f"🎯 Recall (macro): {metrics.get('recall_macro', 0.0):.4f}")
                click.echo(f"🎯 F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}")
                click.echo(f"🎯 Especificidade: {metrics.get('specificity_macro', 0.0):.4f}")
                click.echo(f"🎯 Youden's J: {metrics.get('youdens_j', 0.0):.4f}")
            
            if format == 'detailed':
                auroc = metrics.get('auroc_macro')
                if auroc not in ['not_available', None]:
                    click.echo(f"📊 auROC (macro): {auroc:.4f}")
                
                map_score = metrics.get('map_macro')
                if map_score not in ['not_available', None]:
                    click.echo(f"📊 mAP (macro): {map_score:.4f}")
                
                if metrics.get('hierarchical_f1') not in ['not_available', None]:
                    click.echo(f"\n🌳 MÉTRICAS HIERÁRQUICAS:")
                    click.echo(f"   Precisão: {metrics.get('hierarchical_precision', 0.0):.4f}")
                    click.echo(f"   Recall: {metrics.get('hierarchical_recall', 0.0):.4f}")
                    click.echo(f"   F1-Score: {metrics.get('hierarchical_f1', 0.0):.4f}")
                    click.echo(f"   Distância média: {metrics.get('mean_hierarchical_distance', 0.0):.4f}")
                
                click.echo(f"\n📋 INFORMAÇÕES:")
                click.echo(f"   Amostras: {metrics.get('total_samples', 0)}")
                click.echo(f"   Classes verdadeiras: {metrics.get('num_classes', 0)}")
                click.echo(f"   Classes preditas: {metrics.get('num_predicted_classes', 0)}")
            
            if format == 'json':
                summary_metrics = {
                    "accuracy": metrics.get('accuracy', 0.0),
                    "precision_macro": metrics.get('precision_macro', 0.0),
                    "recall_macro": metrics.get('recall_macro', 0.0),
                    "f1_macro": metrics.get('f1_macro', 0.0),
                    "youdens_j": metrics.get('youdens_j', 0.0)
                }
                click.echo(json.dumps(summary_metrics, indent=2))
            
            click.echo(f"\n📄 RELATÓRIOS GERADOS:")
            click.echo(f"   📊 {output_dir}/detailed_metrics.json")
            click.echo(f"   📋 {output_dir}/metrics_summary.json")
            click.echo(f"   📖 {output_dir}/evaluation_report.txt")
            
        else:
            click.echo("📊 Apenas estatísticas descritivas (sem labels verdadeiros)")
        
        click.echo(f"\n✅ Avaliação concluída!")
        
    except Exception as e:
        click.echo(f"❌ Erro na avaliação: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

# ==================== COMANDOS DE COMPARAÇÃO ====================

@cli.command('compare')
@click.option('--results-dir', required=True, type=click.Path(exists=True),
              help='Diretório com múltiplos resultados')
@click.option('--output', default='comparison_results', help='Diretório de saída para comparação')
@click.option('--metric', default='f1_macro', help='Métrica principal para comparação')
@click.option('--auto-evaluate', is_flag=True, 
              help='Calcular métricas automaticamente para arquivos sem avaliação')
@click.option('--include-incomplete', is_flag=True, 
              help='Incluir resultados sem métricas completas')
@click.option('--min-samples', default=1, help='Número mínimo de amostras para incluir')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def compare(ctx, results_dir, output, metric, auto_evaluate, include_incomplete, min_samples, verbose):
    """Comparar múltiplos resultados de classificação com avaliação automática"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    results_path = Path(results_dir)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"🔍 Comparando resultados em: {results_path}")
    
    if auto_evaluate:
        click.echo("🔬 Modo auto-avaliação ativado")
    if include_incomplete:
        click.echo("📋 Incluindo resultados incompletos")
    
    result_dirs = []
    for item in results_path.iterdir():
        if item.is_dir():
            has_predictions = bool(list(item.glob("**/predicted_*.csv")))
            has_metrics = bool(list(item.glob("**/metrics_summary.json")))
            
            if has_predictions or has_metrics:
                result_dirs.append(item)
                if verbose:
                    status = "✅ com métricas" if has_metrics else "📄 só predições"
                    click.echo(f"   {status}: {item.name}")
    
    if not result_dirs:
        click.echo("❌ Nenhum diretório de resultado encontrado")
        click.echo("   Estrutura esperada: cada subdiretório deve conter predicted_*.csv ou metrics_summary.json")
        return
    
    click.echo(f"📁 Encontrados {len(result_dirs)} diretórios de resultado")
    
    comparison_data = []
    
    for result_dir in result_dirs:
        run_name = result_dir.name
        
        if verbose:
            click.echo(f"\n🔄 Processando: {run_name}")
        
        metrics_files = list(result_dir.glob("**/metrics_summary.json"))
        prediction_files = list(result_dir.glob("**/predicted_*.csv"))
        
        run_data = {
            "run": run_name,
            "source": "unknown",
            "total_samples": 0,
            "has_metrics": len(metrics_files) > 0,
            "has_predictions": len(prediction_files) > 0
        }
        
        if metrics_files:
            metrics_file = metrics_files[0] 
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                
                run_data.update(metrics)
                run_data["source"] = "existing_metrics"
                
                if verbose:
                    click.echo(f"   ✅ Métricas carregadas: {metrics.get(metric, 'N/A')}")
                
            except Exception as e:
                if verbose:
                    click.echo(f"   ⚠️ Erro ao ler métricas: {str(e)}")
        
        elif prediction_files:
            prediction_file = prediction_files[0] 
            
            try:
                df = pd.read_csv(prediction_file)
                run_data["total_samples"] = len(df)
                run_data["source"] = "predictions_only"
                
                # Tenta encontrar a coluna de predição
                pred_col = None
                if "Predicted_Label_Name" in df.columns:
                    pred_col = "Predicted_Label_Name"
                elif "Predicted label" in df.columns:
                    pred_col = "Predicted label"

                if pred_col:
                    predictions = df[pred_col].value_counts()
                    run_data["unique_predictions"] = len(predictions)
                    run_data["top_prediction"] = predictions.index[0] if len(predictions) > 0 else "N/A"
                
                if auto_evaluate and "Actual_Label" in df.columns and TEMetricsEvaluator:
                    if verbose:
                        click.echo(f"   🔬 Calculando métricas automaticamente...")
                    
                    try:
                        temp_metrics_dir = result_dir / "auto_metrics"
                        temp_metrics_dir.mkdir(exist_ok=True)
                        
                        evaluator = TEMetricsEvaluator()
                        metrics = evaluator.evaluate_predictions(
                            str(prediction_file), 
                            str(temp_metrics_dir)
                        )
                        
                        if isinstance(metrics, dict) and 'accuracy' in metrics:
                            numeric_metrics = {}
                            for key, value in metrics.items():
                                if isinstance(value, (int, float)) and not isinstance(value, bool):
                                    numeric_metrics[key] = value
                            
                            run_data.update(numeric_metrics)
                            run_data["source"] = "auto_evaluated"
                            
                            if verbose:
                                click.echo(f"   ✅ Auto-avaliação: {metrics.get(metric, 'N/A')}")
                        
                    except Exception as e:
                        if verbose:
                            click.echo(f"   ⚠️ Erro na auto-avaliação: {str(e)}")
                
                elif auto_evaluate and "Actual_Label" not in df.columns:
                    if verbose:
                        click.echo(f"   ⚠️ Sem labels verdadeiros para auto-avaliação")
                
            except Exception as e:
                if verbose:
                    click.echo(f"   ❌ Erro ao processar predições: {str(e)}")
                continue
        
        if run_data["total_samples"] < min_samples:
            if verbose:
                click.echo(f"   ⏩ Pulando: muito poucas amostras ({run_data['total_samples']})")
            continue
        
        if not include_incomplete and run_data["source"] in ["predictions_only"]:
            if verbose:
                click.echo(f"   ⏩ Pulando: sem métricas completas")
            continue
        
        comparison_data.append(run_data)
        
        if verbose:
            click.echo(f"   ✅ Adicionado à comparação")
    
    if not comparison_data:
        click.echo("❌ Nenhum diretório de resultado encontrado")
        click.echo("   Estrutura esperada: cada subdiretório deve conter predicted_*.csv ou metrics_summary.json")
        return
    
    comparison_df = pd.DataFrame(comparison_data)
    
    comparison_file = output_path / "comparison_results.csv"
    comparison_df.to_csv(comparison_file, index=False)
    
    click.echo(f"\n📊 COMPARAÇÃO DE {len(comparison_data)} EXECUÇÕES:")
    click.echo("=" * 60)
    
    source_counts = comparison_df["source"].value_counts()
    click.echo("📋 Por tipo de dados:")
    for source, count in source_counts.items():
        source_labels = {
            "existing_metrics": "Com métricas existentes",
            "auto_evaluated": "Auto-avaliadas",
            "predictions_only": "Apenas predições"
        }
        label = source_labels.get(source, source)
        click.echo(f"   {label}: {count}")
    
    if metric in comparison_df.columns:
        metric_df = comparison_df[comparison_df[metric].notna()]
        
        if len(metric_df) > 0:
            metric_df_sorted = metric_df.sort_values(metric, ascending=False)
            
            click.echo(f"\n🏆 RANKING POR {metric.upper()}:")
            click.echo("-" * 40)
            for i, (_, row) in enumerate(metric_df_sorted.iterrows(), 1):
                metric_value = row[metric]
                source_icon = {"existing_metrics": "📊", "auto_evaluated": "🔬", "predictions_only": "📄"}.get(row["source"], "❓")
                click.echo(f"  {i:2d}. {source_icon} {row['run']:<20} : {metric_value:.4f}")
            
            metric_values = metric_df[metric]
            click.echo(f"\n📈 ESTATÍSTICAS DE {metric.upper()}:")
            click.echo(f"   Média: {metric_values.mean():.4f}")
            click.echo(f"   Mediana: {metric_values.median():.4f}")
            click.echo(f"   Desvio padrão: {metric_values.std():.4f}")
            click.echo(f"   Melhor: {metric_values.max():.4f}")
            click.echo(f"   Pior: {metric_values.min():.4f}")
        
        else:
            click.echo(f"\n⚠️ Nenhum resultado com métrica '{metric}' encontrado")
    
    else:
        click.echo(f"\n⚠️ Métrica '{metric}' não encontrada nos resultados")
        available_metrics = [col for col in comparison_df.columns if comparison_df[col].dtype in ['float64', 'int64']]
        if available_metrics:
            click.echo(f"📊 Métricas disponíveis: {', '.join(available_metrics[:5])}")
    
    click.echo(f"\n📋 RESUMO GERAL:")
    total_samples = comparison_df["total_samples"].sum()
    avg_samples = comparison_df["total_samples"].mean()
    
    click.echo(f"   Total de sequências processadas: {total_samples:,}")
    click.echo(f"   Média por execução: {avg_samples:.1f}")
    
    report_file = output_path / "comparison_report.txt"
    with open(report_file, 'w') as f:
        f.write(f"RELATÓRIO DE COMPARAÇÃO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total de execuções: {len(comparison_data)}\n")
        f.write(f"Métrica principal: {metric}\n\n")
        
        for _, row in comparison_df.iterrows():
            f.write(f"\nExecução: {row['run']}\n")
            f.write(f"Fonte: {row['source']}\n")
            f.write(f"Amostras: {row['total_samples']}\n")
            if metric in row and pd.notna(row[metric]):
                f.write(f"{metric}: {row[metric]:.4f}\n")
    
    click.echo(f"\n💾 ARQUIVOS GERADOS:")
    click.echo(f"   📊 {comparison_file}")
    click.echo(f"   📖 {report_file}")

    runs_without_metrics = len(comparison_df[comparison_df["source"] == "predictions_only"])
    if runs_without_metrics > 0:
        click.echo(f"\n💡 SUGESTÕES:")
        click.echo(f"   • {runs_without_metrics} execuções sem métricas completas")
        click.echo(f"   • Use --auto-evaluate para calcular automaticamente")
        click.echo(f"   • Ou execute 'evaluate' manualmente em cada resultado")

# ==================== COMANDOS UTILITÁRIOS ====================

@cli.command('diagnose')
@click.option('--results-dir', required=True, type=click.Path(exists=True),
              help='Diretório com resultados para diagnosticar')
# ... (Resto do comando 'diagnose' omitido) ...
def diagnose(ctx, results_dir, fix, verbose):
    """Diagnosticar problemas em diretórios de resultados"""
    pass

@cli.command('info')
@click.pass_context
def info(ctx):
    """Mostrar informações sobre a ferramenta e ambiente"""
    # (O conteúdo desta função está omitido por ser longo e correto)
    pass

@cli.command('clean')
@click.option('--target', type=click.Choice(['temp', 'envs', 'results', 'all']), 
              default='temp', help='O que limpar')
# ... (Resto do comando 'clean' omitido) ...
def clean(ctx, target):
    """Limpar arquivos temporários e caches"""
    pass

# ==================== COMANDOS DE HELP E EXEMPLOS ====================

@cli.command('examples')
def examples():
    """Mostrar exemplos de uso da ferramenta"""
    # (O conteúdo desta função está omitido por ser longo e correto)
    pass

@cli.command('quickstart')
@click.option('--input', default='data/default_dataset.fasta', help='Arquivo FASTA para teste')
@click.pass_context
def quickstart(ctx, input):
    """Execução rápida para teste inicial"""
    # (O conteúdo desta função está omitido por ser longo e correto)
    pass

if __name__ == '__main__':
    cli()