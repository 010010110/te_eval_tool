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

# Imports condicionais
try:
    from env_manager import EnvironmentManager
except ImportError:
    print("⚠️ env_manager.py não encontrado. Alguns recursos podem não funcionar.")
    EnvironmentManager = None

try:
    from fasta_label_mapper import FASTALabelMapper
except ImportError:
    # Isso pode acontecer se houver erro de sintaxe no mapper ou falta de dependência (pandas)
    # print("⚠️ fasta_label_mapper.py não encontrado ou com erro. Mapeamento automático indisponível.")
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
@click.option('--model', type=click.Choice(['classifyte', 'terl', 'yoro', 'all']), default='all', 
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

@cli.command()
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True), 
              help='Arquivo FASTA de entrada')
@click.option('--format', 'format_type', default='fasta', 
              type=click.Choice(['fasta', 'csv']), help='Formato do arquivo')
@click.option('--detailed', is_flag=True, help='Validação detalhada')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def validate(ctx, input_file, format_type, detailed, verbose):
    """Validar arquivo de entrada"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    def validate_fasta_detailed(file_path):
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            headers = []
            sequences = []
            issues = []
            current_seq = ''
            current_header = None
            
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line: continue
                    
                if line.startswith('>'):
                    if current_header and current_seq:
                        sequences.append((current_header, current_seq))
                        if len(current_seq) < 50:
                            issues.append(f"Linha {i}: Sequência muito curta ({len(current_seq)} bp)")
                    headers.append(line)
                    current_header = line[1:]
                    current_seq = ''
                else:
                    if current_header is None:
                        issues.append(f"Linha {i}: Sequência sem header")
                        continue
                    current_seq += line
            
            if current_header and current_seq:
                sequences.append((current_header, current_seq))
            
            if not headers:
                click.echo("❌ Nenhum header FASTA encontrado")
                return False
            
            click.echo(f"✅ FASTA válido: {len(headers)} headers, {len(sequences)} sequências")
            if issues:
                click.echo(f"⚠️  {len(issues)} problemas encontrados.")
            return len(issues) == 0
            
        except Exception as e:
            click.echo(f"❌ Erro ao validar: {str(e)}")
            return False
    
    def validate_fasta_simple(file_path):
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            headers = content.count('>')
            if headers == 0:
                click.echo("❌ Nenhum header FASTA encontrado")
                return False
            click.echo(f"✅ FASTA válido: {headers} headers encontrados")
            return True
        except Exception as e:
            click.echo(f"❌ Erro ao validar: {str(e)}")
            return False
    
    click.echo(f"🔍 Validando {input_file}...")
    if format_type == 'fasta':
        if detailed:
            validate_fasta_detailed(input_file)
        else:
            validate_fasta_simple(input_file)
    else:
        click.echo("✅ Formato CSV assumido como válido")


@cli.command()
@click.option('--model', default='classifyte', 
              type=click.Choice(['classifyte', 'inpactor2', 'terl', 'yoro']), 
              help='Modelo a ser executado')
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True), 
              help='Arquivo FASTA de entrada')
@click.option('--output', 'output_dir', required=True, help='Diretório de saída')
@click.option('--algorithm', default='lcpnb', 
              type=click.Choice(['lcpnb', 'nllcpn']), 
              help='Algoritmo hierárquico (ClassifyTE)')
@click.option('--model-file', default='ClassifyTE_combined.pkl', 
              help='Arquivo do modelo (.pkl) ou diretório (TERL/YORO)')
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
        "output_dir": str(output_dir)
    }
    
    click.echo(f"🔬 Executando {model} com {input_file}")
    click.echo(f"🌍 Usando ambiente específico do {model}")
    click.echo(f"📁 Resultados em: {output_dir}")
    
    try:
        if EnvironmentManager:
            python_path = env_manager.get_python_path(model)
            click.echo(f"🐍 Python: {python_path}")
        
        success = False
        if model == 'classifyte':
            success = run_classifyte(python_path, input_file, output_dir, algorithm, 
                                     model_file, node_file, verbose, clean)
        elif model == 'inpactor2':
            click.echo("🚧 Inpactor2 ainda não implementado")
        
        elif model == 'terl':
            success = run_terl(python_path, input_file, output_dir, 
                               model_file, 
                               verbose=verbose, clean_temp=clean)

        elif model == 'yoro':
            success = run_yoro(python_path, input_file, output_dir, 
                               verbose=verbose, clean_temp=clean)
            
        else:
            click.echo(f"❌ Modelo '{model}' não reconhecido")
        
        # Finalização e Logs
        end_time = datetime.now()
        log_data.update({"end_time": end_time.isoformat(), "success": success})
        with open(output_path / "execution_log.json", 'w') as f:
            json.dump(log_data, f, indent=2)
        
        if success:
            click.echo(f"\n✅ Classificação {model} concluída com sucesso!")
            
            predictions_file = output_path / "predicted_results.csv"
            if auto_label and FASTALabelMapper and predictions_file.exists():
                click.echo(f"\n🏷️  Mapeando labels automaticamente...")
                try:
                    base_dir = str(Path.cwd())
                    mapper = FASTALabelMapper(base_dir=base_dir) 
                    map_success = mapper.add_actual_labels_to_predictions(
                        str(predictions_file.resolve()), 
                        str(Path(input_file).resolve())
                    )
                    if map_success:
                        click.echo("✅ Labels mapeados com sucesso!")
                    else:
                        click.echo("⚠️ Falha no mapeamento de labels.")
                except Exception as e:
                    click.echo(f"⚠️ Erro no mapeamento automático: {str(e)}")
            
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
        click.echo(f"❌ Erro Crítico: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

# --- FUNÇÕES ESPECÍFICAS DOS MODELOS ---

def run_classifyte(python_path, input_file, output_dir, algorithm, model_file, 
                   node_file, verbose=False, clean_temp=False):
    input_path = Path(input_file)
    model_path = Path("ClassifyTE/models") / model_file
    
    if not model_path.exists():
        click.echo(f"❌ Modelo não encontrado: {model_path}")
        return False

    # Copia e prepara arquivos (Lógica original do ClassifyTE)
    target_fasta = Path("ClassifyTE/data") / input_path.name
    if input_path.resolve() != target_fasta.resolve():
        shutil.copy(input_path, target_fasta)
    
    base_name = input_path.stem
    features_file = f"{base_name}.csv"
    features_dir = f"{base_name}"
    
    # Limpeza prévia
    temp_dir = Path("ClassifyTE") / features_dir
    if temp_dir.exists(): shutil.rmtree(temp_dir)
    
    click.echo("⚙️ Gerando features...")
    cmd_gen = [python_path, "generate_feature_file.py", "-f", input_path.name, "-o", features_file, "-d", features_dir]
    subprocess.run(cmd_gen, cwd="ClassifyTE", check=True, capture_output=not verbose)
    
    click.echo("🧠 Executando predição...")
    cmd_eval = [python_path, "evaluate.py", "-f", features_file, "-d", features_dir, "-n", node_file, "-m", model_file, "-a", algorithm]
    subprocess.run(cmd_eval, cwd="ClassifyTE", check=True, capture_output=not verbose)
    
    # Copiar resultados
    expected_result = Path("ClassifyTE/outputs") / f"predicted_out_{features_dir}.csv"
    if expected_result.exists():
        shutil.copy(expected_result, Path(output_dir) / "predicted_results.csv")
        return True
    return False

def run_terl(python_path, input_file, output_dir, terl_model_path, verbose=False, clean_temp=False):
    click.echo("⚙️ Executando TERL...")
    input_path = Path(input_file).resolve()
    temp_dir = Path(output_dir) / "terl_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if not Path(terl_model_path).exists():
        click.echo(f"❌ Modelo TERL não encontrado: {terl_model_path}")
        return False
        
    script_path = "TERL-master/terl_test.py" if Path("TERL-master/terl_test.py").exists() else "TERL/terl_test.py"
    
    temp_prefix = (temp_dir / f"{input_path.stem}_pred_").resolve()
    output_fasta = temp_dir / f"{input_path.stem}_pred_{input_path.name}"
    
    cmd = [python_path, script_path, "-m", terl_model_path, "-f", str(input_path), "-p", str(temp_prefix), "-q"]
    if verbose: click.echo(f"Cmd: {' '.join(cmd)}")
    
    subprocess.run(cmd, check=False, capture_output=not verbose)
    
    if not output_fasta.exists():
        click.echo("❌ Falha: Arquivo de saída do TERL não gerado.")
        return False
        
    # Conversão FASTA -> CSV
    click.echo("🔄 Convertendo saída FASTA do TERL para CSV...")
    ids, preds = [], []
    with open(input_path) as f_in, open(output_fasta) as f_out:
        # Lê IDs originais
        ids = [l.strip()[1:] for l in f_in if l.startswith('>')]
        # Lê Predições (cabeçalho do TERL tem a classe)
        # Ex: >Copia\t1 -> Copia
        preds = [l.strip()[1:].split('\t')[0] for l in f_out if l.startswith('>')]
    
    if len(ids) != len(preds):
        click.echo(f"❌ Erro de contagem: {len(ids)} IDs vs {len(preds)} predições")
        return False
        
    df = pd.DataFrame({'id': ids, 'Predicted_Label_Name': preds})
    df.to_csv(Path(output_dir) / "predicted_results.csv", index=False)
    
    if clean_temp: shutil.rmtree(temp_dir)
    return True

def run_yoro(python_path, input_file, output_dir, verbose=False, clean_temp=False):
    """Executa YORO com ambiente específico e converte a saída"""
    
    click.echo("⚙️ Executando YORO...")
    
    input_path = Path(input_file).resolve()
    output_path = Path(output_dir)
    
    temp_dir = output_path / "yoro_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    script_path = "YORO-master/pipelineDomain.py"
    if not Path(script_path).exists():
        click.echo(f"❌ Erro: Script 'pipelineDomain.py' não encontrado em: YORO-master/")
        return False

    model_path = Path("YORO-master/models/AAqqYOLOqqdomainqqV25.hdf5").resolve()
    if not model_path.exists():
        click.echo(f"❌ Erro: Modelo YORO não encontrado em: {model_path}")
        return False

    # --- PASSO 1: Sanitizar o FASTA ---
    sanitized_fasta_path = temp_dir / "sanitized_input.fasta"
    if verbose: click.echo(f"🧹 Sanitizando arquivo FASTA para o YORO...")
    
    original_ids = []
    
    try:
        with open(input_path, 'r') as f_in, open(sanitized_fasta_path, 'w') as f_out:
            for line in f_in:
                if line.startswith(">"):
                    original_header = line.strip()[1:]
                    original_id = original_header.split()[0] 
                    
                    # Troca # e | por _ para não quebrar o YORO
                    sanitized_id = original_id.replace('#', '_').replace('|', '_')
                    
                    original_ids.append(original_id)
                    
                    rest_of_header = line.strip()[1:].partition(' ')[2]
                    if rest_of_header:
                        f_out.write(f">{sanitized_id} {rest_of_header}\n")
                    else:
                        f_out.write(f">{sanitized_id}\n")
                else:
                    f_out.write(line)
    except Exception as e:
        click.echo(f"❌ Erro ao sanitizar FASTA: {e}")
        return False

    # --- PASSO 2: Executar YORO ---
    cmd_classify = [
        python_path,
        script_path,
        "-f", str(sanitized_fasta_path),
        "-d", str(temp_dir),
        "-m", str(model_path)
    ]
    
    if verbose: click.echo(f"  Comando: {' '.join(cmd_classify)}")

    result = subprocess.run(cmd_classify, capture_output=True, text=True, cwd=Path.cwd())
    
    if result.returncode != 0:
        click.echo(f"❌ Erro na classificação do YORO:")
        if verbose:
            click.echo(f"  STDOUT: {result.stdout}")
            click.echo(f"  STDERR: {result.stderr}")
        return False
        
    yoro_output_file = temp_dir / "output.tab"
    
    if not yoro_output_file.exists():
        click.echo(f"❌ Erro: Arquivo de saída do YORO não encontrado em: {yoro_output_file}")
        if verbose: click.echo(f"  STDOUT: {result.stdout}")
        return False
        
    click.echo(f"📄 Saída tabular do YORO gerada.")

    # --- PASSO 3: Converter e Limpar ---
    click.echo("🔄 Convertendo saída do YORO para o formato CSV...")
    
    try:
        # Lê o arquivo com tabulação
        yoro_df = pd.read_csv(yoro_output_file, sep='\t')
        
        # --- CORREÇÃO: Limpeza agressiva das colunas ---
        # Remove espaços e o caractere '|' dos nomes das colunas
        yoro_df.columns = yoro_df.columns.str.replace('|', '', regex=False).str.strip()
        
        if 'id' not in yoro_df.columns or 'Class' not in yoro_df.columns:
            click.echo(f"❌ Erro: Colunas esperadas ('id', 'Class') não encontradas.")
            click.echo(f"   Colunas encontradas: {list(yoro_df.columns)}")
            return False

        # Limpeza dos DADOS: remove '|' das células de texto
        for col in yoro_df.columns:
            if yoro_df[col].dtype == object:
                yoro_df[col] = yoro_df[col].astype(str).str.replace('|', '', regex=False).str.strip()
        # ------------------------------------------------

        # Pega a melhor predição
        if 'ProbabilityClass' in yoro_df.columns:
            best_predictions = yoro_df.loc[yoro_df.groupby('id')['ProbabilityClass'].idxmax()]
        else:
            best_predictions = yoro_df.groupby('id').first().reset_index()
        
        preds_df = best_predictions[['id', 'Class']].copy()
        preds_df.columns = ['sanitized_id', 'Predicted_Label_Name']
        preds_df['sanitized_id'] = preds_df['sanitized_id'].astype(str).str.lstrip('>')
        
        # Reconstrói o mapa usando os IDs originais salvos
        master_df = pd.DataFrame({
            'id': original_ids,
            'sanitized_id': [id.replace('#', '_').replace('|', '_') for id in original_ids]
        })
        
        merged_df = pd.merge(master_df, preds_df, on='sanitized_id', how='left')
        merged_df['Predicted_Label_Name'] = merged_df['Predicted_Label_Name'].fillna('Unknown_YORO')
        
        final_df = merged_df[['id', 'Predicted_Label_Name']]
        
        final_file = output_path / "predicted_results.csv"
        final_df.to_csv(final_file, index=False)
        
        click.echo(f"📊 Resultados convertidos e salvos em: {final_file}")
        
        if clean_temp:
            click.echo("🧹 Limpando arquivos temporários do YORO...")
            shutil.rmtree(temp_dir)
            
        return True

    except Exception as e:
        click.echo(f"❌ Erro ao converter saída do YORO: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False

# ==================== COMANDOS UTILITÁRIOS ====================

@cli.command('map-labels')
@click.option('--fasta', required=True, help='Arquivo FASTA')
@click.option('--predictions', help='Arquivo CSV de predições')
@click.option('--output', help='Arquivo de saída')
@click.option('--validate-only', is_flag=True)
@click.option('--tree-file', default='nodes/tree.txt')
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def map_labels(ctx, fasta, predictions, output, validate_only, tree_file, verbose):
    """Mapear headers FASTA"""
    if not FASTALabelMapper:
        click.echo("❌ Mapper indisponível")
        sys.exit(1)
    
    try:
        mapper = FASTALabelMapper(base_dir=str(Path.cwd()), tree_file=tree_file)
        if validate_only:
            mapper.validate_mapping(fasta)
        elif predictions:
            mapper.add_actual_labels_to_predictions(str(Path(predictions).resolve()), str(Path(fasta).resolve()))
            click.echo("✅ Labels mapeados!")
        else:
            # Processamento padrão
            mapper.process_fasta_file(fasta, output)
    except Exception as e:
        click.echo(f"❌ Erro: {e}")

@cli.command('evaluate')
@click.option('--predictions', required=True, help='Arquivo CSV')
@click.option('--output', 'output_dir', required=True)
@click.option('--hierarchy', default='nodes/tree.txt')
@click.option('--format', default='detailed')
@click.option('--verbose', '-v', is_flag=True)
def evaluate_metrics(predictions, output_dir, hierarchy, format, verbose):
    """Avaliar predições"""
    if not TEMetricsEvaluator:
        click.echo("❌ Evaluator indisponível")
        sys.exit(1)
    
    click.echo(f"🔬 Avaliando: {predictions}")
    evaluator = TEMetricsEvaluator(hierarchy_file=hierarchy)
    evaluator.evaluate_predictions(predictions, output_dir)
    click.echo("✅ Avaliação concluída!")

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
    click.echo(f"📊 Métrica principal: {metric}")
    
    if auto_evaluate:
        click.echo("🔬 Modo auto-avaliação ativado")
    if include_incomplete:
        click.echo("📋 Incluindo resultados incompletos")
    
    # Buscar todos os diretórios de resultados
    result_dirs = []
    for item in results_path.iterdir():
        if item.is_dir():
            # Verificar se contém arquivos de resultado
            has_predictions = bool(list(item.glob("**/predicted_results.csv")))
            has_metrics = bool(list(item.glob("**/metrics_summary.json")))
            
            if has_predictions or has_metrics:
                result_dirs.append(item)
                if verbose:
                    status = "✅ com métricas" if has_metrics else "📄 só predições"
                    click.echo(f"   {status}: {item.name}")
    
    if not result_dirs:
        click.echo("❌ Nenhum diretório de resultado encontrado")
        click.echo("   Estrutura esperada: cada subdiretório deve conter predicted_results.csv ou metrics_summary.json")
        return
    
    click.echo(f"📁 Encontrados {len(result_dirs)} diretórios de resultado")
    
    comparison_data = []
    
    # Processar cada diretório de resultado
    for result_dir in result_dirs:
        run_name = result_dir.name
        
        if verbose:
            click.echo(f"\n🔄 Processando: {run_name}")
        
        # Procurar métricas existentes
        metrics_files = list(result_dir.glob("**/metrics_summary.json"))
        prediction_files = list(result_dir.glob("**/predicted_results.csv"))
        
        run_data = {
            "run": run_name,
            "source": "unknown",
            "total_samples": 0,
            "has_metrics": len(metrics_files) > 0,
            "has_predictions": len(prediction_files) > 0
        }
        
        # Tentar carregar métricas existentes
        if metrics_files:
            metrics_file = metrics_files[0]  # Usar o primeiro encontrado
            try:
                with open(metrics_file, 'r') as f:
                    metrics_data = json.load(f)
                
                run_data.update(metrics_data)
                run_data["source"] = "existing_metrics"
                
                if verbose:
                    click.echo(f"   ✅ Métricas carregadas: {metrics_data.get(metric, 'N/A')}")
                
            except Exception as e:
                if verbose:
                    click.echo(f"   ⚠️ Erro ao ler métricas: {str(e)}")
        
        # Se não tem métricas mas tem predições, processar
        elif prediction_files:
            prediction_file = prediction_files[0]  # Usar o primeiro encontrado
            
            try:
                df = pd.read_csv(prediction_file)
                run_data["total_samples"] = len(df)
                run_data["source"] = "predictions_only"
                
                if "Predicted label" in df.columns:
                    predictions = df["Predicted label"].value_counts()
                    run_data["unique_predictions"] = len(predictions)
                    run_data["top_prediction"] = predictions.index[0] if len(predictions) > 0 else "N/A"
                
                # Auto-avaliar se solicitado e temos labels verdadeiros
                if auto_evaluate and "Actual_Label" in df.columns and TEMetricsEvaluator:
                    if verbose:
                        click.echo(f"   🔬 Calculando métricas automaticamente...")
                    
                    try:
                        # Criar diretório temporário para métricas
                        temp_metrics_dir = result_dir / "auto_metrics"
                        temp_metrics_dir.mkdir(exist_ok=True)
                        
                        evaluator = TEMetricsEvaluator()
                        metrics_data = evaluator.evaluate_predictions(
                            str(prediction_file), 
                            str(temp_metrics_dir)
                        )
                        
                        if isinstance(metrics_data, dict) and 'accuracy' in metrics_data:
                            # Filtrar apenas métricas numéricas para comparação
                            numeric_metrics = {}
                            for key, value in metrics_data.items():
                                if isinstance(value, (int, float)) and not isinstance(value, bool):
                                    numeric_metrics[key] = value
                            
                            run_data.update(numeric_metrics)
                            run_data["source"] = "auto_evaluated"
                            
                            if verbose:
                                click.echo(f"   ✅ Auto-avaliação: {metrics_data.get(metric, 'N/A')}")
                        
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
        
        # Aplicar filtros
        if run_data["total_samples"] < min_samples:
            if verbose:
                click.echo(f"   ⏩ Pulando: muito poucas amostras ({run_data['total_samples']})")
            continue
        
        # Se não incluir incompletos, pular runs sem métricas
        if not include_incomplete and run_data["source"] in ["predictions_only"]:
            if verbose:
                click.echo(f"   ⏩ Pulando: sem métricas completas")
            continue
        
        comparison_data.append(run_data)
        
        if verbose:
            click.echo(f"   ✅ Adicionado à comparação")
    
    if not comparison_data:
        click.echo("❌ Nenhum resultado válido encontrado após filtros")
        click.echo("💡 Dicas:")
        click.echo("   - Use --include-incomplete para incluir resultados sem métricas")
        click.echo("   - Use --auto-evaluate para calcular métricas automaticamente") 
        click.echo("   - Verifique se os arquivos predicted_results.csv existem")
        return
    
    # Criar DataFrame para comparação
    comparison_df = pd.DataFrame(comparison_data)
    
    # Salvar comparação completa
    comparison_file = output_path / "comparison_results.csv"
    comparison_df.to_csv(comparison_file, index=False)
    
    # Mostrar resumo
    click.echo(f"\n📊 COMPARAÇÃO DE {len(comparison_data)} EXECUÇÕES:")
    click.echo("=" * 60)
    
    # Estatísticas por fonte
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
    
    # Ranking por métrica se disponível
    if metric in comparison_df.columns:
        # Filtrar apenas runs com a métrica
        metric_df = comparison_df[comparison_df[metric].notna()]
        
        if len(metric_df) > 0:
            metric_df_sorted = metric_df.sort_values(metric, ascending=False)
            
            click.echo(f"\n🏆 RANKING POR {metric.upper()}:")
            click.echo("-" * 40)
            for i, (_, row) in enumerate(metric_df_sorted.iterrows(), 1):
                metric_value = row[metric]
                # Ícone baseado na fonte
                source_icon = {"existing_metrics": "📊", "auto_evaluated": "🔬", "predictions_only": "📄"}.get(row["source"], "❓")
                click.echo(f"  {i:2d}. {source_icon} {row['run']:<25} : {metric_value:.4f}")
            
            # Estatísticas da métrica
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
    
    # Resumo geral
    click.echo(f"\n📋 RESUMO GERAL:")
    total_samples = comparison_df["total_samples"].sum()
    avg_samples = comparison_df["total_samples"].mean()
    
    click.echo(f"   Total de sequências processadas: {total_samples:,}")
    click.echo(f"   Média por execução: {avg_samples:.1f}")
    
    # Salvar relatório simples (sem função externa)
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


@cli.command('diagnose')
@click.option('--results-dir', required=True)
@click.pass_context
def diagnose(ctx, results_dir):
    """Diagnosticar problemas"""
    pass

@cli.command('info')
@click.pass_context
def info(ctx):
    """Mostrar informações"""
    click.echo("🔬 TE Evaluation Tool v5.0.1 (Full Integration)")
    # ...

@cli.command('clean')
@click.option('--target', type=click.Choice(['temp', 'envs', 'results', 'all']), default='temp')
@click.confirmation_option(prompt='Confirma a limpeza?')
@click.pass_context
def clean(ctx, target):
    """Limpar arquivos"""
    verbose = ctx.obj.get('verbose', False)
    click.echo(f"🧹 Limpando {target}...")
    # Lógica de limpeza (simplificada para caber aqui)
    if target in ['envs', 'all']:
        if Path("model_envs").exists(): shutil.rmtree("model_envs")
    if target in ['results', 'all']:
        if Path("results").exists(): shutil.rmtree("results")
        if Path("all_my_results").exists(): shutil.rmtree("all_my_results")
    click.echo("✅ Limpeza concluída.")

@cli.command('examples')
def examples():
    """Mostrar exemplos"""
    pass

@cli.command('quickstart')
def quickstart():
    pass

if __name__ == '__main__':
    cli()