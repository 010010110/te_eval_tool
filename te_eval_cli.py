# te_eval_cli.py - Versão 5 - CLI otimizado com gerenciamento de ambientes
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
    from fasta_label_mapper import FASTALabelMapper
except ImportError:
    print("⚠️ fasta_label_mapper.py não encontrado. Mapeamento automático não disponível.")
    FASTALabelMapper = None

@click.group()
@click.version_option(version='5.0.0')
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
@click.option('--model', type=click.Choice(['classifyte', 'all']), default='all', 
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
def validate(input_file, format_type, detailed, verbose):
    """Validar arquivo de entrada"""
    
    verbose = verbose
    
    def validate_fasta_detailed(file_path):
        """Validação detalhada de FASTA"""
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
                if not line:
                    continue
                    
                if line.startswith('>'):
                    # Salvar sequência anterior se existe
                    if current_header and current_seq:
                        sequences.append((current_header, current_seq))
                        if len(current_seq) < 50:
                            issues.append(f"Linha {i}: Sequência muito curta ({len(current_seq)} bp)")
                    
                    headers.append(line)
                    current_header = line[1:]  # Remove '>'
                    current_seq = ''
                    
                    # Verificar formato do header
                    if '|' in current_header:
                        parts = current_header.split('|')
                        if verbose:
                            click.echo(f"   Header: {parts}")
                else:
                    # Linha de sequência
                    if current_header is None:
                        issues.append(f"Linha {i}: Sequência sem header")
                        continue
                    
                    # Verificar caracteres válidos
                    valid_chars = set('ACGTNacgtn-.')
                    invalid_chars = set(line) - valid_chars
                    if invalid_chars:
                        issues.append(f"Linha {i}: Caracteres inválidos: {invalid_chars}")
                    
                    current_seq += line
            
            # Processar última sequência
            if current_header and current_seq:
                sequences.append((current_header, current_seq))
                if len(current_seq) < 50:
                    issues.append(f"Última sequência muito curta ({len(current_seq)} bp)")
            
            # Resultados
            if not headers:
                click.echo("❌ Nenhum header FASTA encontrado")
                return False
            
            if not sequences:
                click.echo("❌ Nenhuma sequência encontrada")
                return False
            
            click.echo(f"✅ FASTA válido:")
            click.echo(f"   📊 {len(headers)} headers")
            click.echo(f"   📊 {len(sequences)} sequências")
            
            if sequences:
                seq_lengths = [len(seq) for _, seq in sequences]
                click.echo(f"   📏 Tamanho médio: {sum(seq_lengths)/len(seq_lengths):.1f} bp")
                click.echo(f"   📏 Menor: {min(seq_lengths)} bp, Maior: {max(seq_lengths)} bp")
            
            # Mostrar problemas encontrados
            if issues:
                click.echo(f"\n⚠️  {len(issues)} problemas encontrados:")
                for issue in issues[:5]:  # Mostrar apenas 5 primeiros
                    click.echo(f"   {issue}")
                if len(issues) > 5:
                    click.echo(f"   ... e mais {len(issues) - 5} problemas")
            
            return len(issues) == 0
            
        except Exception as e:
            click.echo(f"❌ Erro ao validar: {str(e)}")
            return False
    
    def validate_fasta_simple(file_path):
        """Validação simples de FASTA"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            headers = sum(1 for line in lines if line.strip().startswith('>'))
            sequences = sum(1 for line in lines if line.strip() and not line.strip().startswith('>'))
            
            if headers == 0:
                click.echo("❌ Nenhum header FASTA encontrado")
                return False
            
            if sequences == 0:
                click.echo("❌ Nenhuma sequência encontrada")
                return False
            
            click.echo(f"✅ FASTA válido: {headers} headers, {sequences} linhas de sequência")
            return True
        
        except Exception as e:
            click.echo(f"❌ Erro ao validar: {str(e)}")
            return False
    
    # Executar validação
    click.echo(f"🔍 Validando {input_file} (formato: {format_type})")
    
    if format_type == 'fasta':
        if detailed:
            is_valid = validate_fasta_detailed(input_file)
        else:
            is_valid = validate_fasta_simple(input_file)
    else:
        click.echo("✅ Formato CSV assumido como válido")
        is_valid = True
    
    if not is_valid:
        sys.exit(1)

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
              help='Arquivo do modelo (.pkl)')
@click.option('--node-file', default='node.txt', help='Arquivo de nós hierárquicos')
@click.option('--skip-evaluation', is_flag=True, 
              help='Pular avaliação automática de métricas')
@click.option('--clean', is_flag=True, help='Limpar arquivos temporários após execução')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.option('--auto-label', is_flag=True, 
              help='Mapear automaticamente labels do FASTA para avaliação')
def run(model, input_file, output_dir, algorithm, model_file, node_file, 
        skip_evaluation, clean, verbose, auto_label):
    """Executar classificação usando ambiente específico do modelo"""
    
    verbose = verbose
    start_time = datetime.now()
    
    # Verificar se EnvironmentManager está disponível
    if not EnvironmentManager:
        click.echo("⚠️ Ambiente isolado não disponível. Usando Python global.")
        python_path = "python3"
    else:
        env_manager = EnvironmentManager()
    
    # Criar diretório de saída
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Log inicial
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
        # Obter Python do ambiente específico
        if EnvironmentManager:
            python_path = env_manager.get_python_path(model)
            click.echo(f"🐍 Python: {python_path}")
        
        # Executar modelo específico
        if model == 'classifyte':
            success = run_classifyte(python_path, input_file, output_dir, algorithm, 
                                   model_file, node_file, verbose, clean)
        elif model == 'inpactor2':
            click.echo("🚧 Inpactor2 ainda não implementado")
            success = False
        elif model == 'terl':
            click.echo("🚧 TERL ainda não implementado") 
            success = False
        else:
            click.echo(f"❌ Modelo '{model}' não reconhecido")
            success = False
        
        # Log final
        end_time = datetime.now()
        log_data.update({
            "end_time": end_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "success": success
        })
        
        # Salvar log de execução
        log_file = output_path / "execution_log.json"
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        if success:
            click.echo(f"\n✅ Classificação {model} concluída com sucesso!")
            click.echo(f"⏱️  Tempo total: {(end_time - start_time).total_seconds():.1f}s")
            
            # Mapeamento automático de labels se solicitado
            predictions_file = output_path / "predicted_results.csv"
            if auto_label and FASTALabelMapper and predictions_file.exists():
                click.echo(f"\n🏷️  Mapeando labels automaticamente...")
                try:
                    mapper = FASTALabelMapper()
                    mapper.add_actual_labels_to_predictions(
                        str(predictions_file), 
                        input_file, 
                        str(predictions_file)
                    )
                    click.echo("✅ Labels mapeados com sucesso!")
                except Exception as e:
                    click.echo(f"⚠️ Erro no mapeamento automático: {str(e)}")
            
            # Avaliação automática se não foi pulada
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
    
    # Verificar se modelo existe
    model_path = Path("ClassifyTE/models") / model_file
    if not model_path.exists():
        click.echo(f"❌ Modelo não encontrado: {model_path}")
        return False
    
    # Verificar se arquivo de nós existe
    nodes_path = Path("ClassifyTE/nodes") / node_file
    if not nodes_path.exists():
        nodes_path = Path("nodes") / node_file
        if not nodes_path.exists():
            click.echo(f"❌ Arquivo de nós não encontrado: {node_file}")
            return False
    
    # Copiar FASTA para ClassifyTE/data
    target_fasta = Path("ClassifyTE/data") / input_path.name
    if input_path.resolve() != target_fasta.resolve():
        shutil.copy(input_path, target_fasta)
        if verbose:
            click.echo(f"📄 FASTA copiado para {target_fasta}")
    
    # Preparar nomes de arquivos
    base_name = input_path.stem
    features_file = f"{base_name}.csv"
    features_dir = f"{base_name}"
    
    # Limpar arquivos temporários existentes
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
    
    # Passo 1: Gerar features
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
    
    # Passo 2: Executar predição
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
    
    # Passo 3: Localizar e copiar resultados
    expected_result = Path("ClassifyTE/outputs") / f"predicted_out_{features_dir}.csv"
    
    if not expected_result.exists():
        # Procurar arquivo mais recente
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
    
    # Copiar resultado final
    final_file = output_path / "predicted_results.csv"
    shutil.copy(expected_result, final_file)
    
    # Passo 4: Processar e mostrar resultados
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
        
        # Salvar metadados básicos
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
        
        # Limpeza de arquivos temporários se solicitada
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
def map_labels(fasta, predictions, output, validate_only, tree_file, verbose):
    """Mapear headers FASTA para códigos hierárquicos"""
    
    if not FASTALabelMapper:
        click.echo("❌ FASTALabelMapper não disponível")
        sys.exit(1)
    
    click.echo(f"🏷️  Mapeando labels de: {fasta}")
    
    try:
        mapper = FASTALabelMapper(tree_file=tree_file)
        
        if validate_only:
            # Apenas validar mapeamentos
            mapper.validate_mapping(fasta)
        
        elif predictions:
            # Adicionar labels a arquivo de predições
            click.echo(f"📄 Adicionando labels a: {predictions}")
            mapper.add_actual_labels_to_predictions(predictions, fasta, output)
            
        else:
            # Processar FASTA e gerar CSV de mapeamentos
            output_file = output if output else f"{Path(fasta).stem}_mappings.csv"
            mappings_df = mapper.process_fasta_file(fasta, output_file)
            
            click.echo(f"\n📊 Resumo dos mapeamentos:")
            click.echo(f"   Total: {len(mappings_df)}")
            click.echo(f"   Sucessos: {mappings_df['mapping_success'].sum()}")
            click.echo(f"   Falhas: {(~mappings_df['mapping_success']).sum()}")
        
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
def evaluate_metrics(predictions, output_dir, hierarchy, format, verbose):
    """Avaliar predições com métricas padronizadas completas"""
    
    verbose = verbose
    
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
                # Métricas avançadas
                auroc = metrics.get('auroc_macro')
                if auroc not in ['not_available', None]:
                    click.echo(f"📊 auROC (macro): {auroc:.4f}")
                
                map_score = metrics.get('map_macro')
                if map_score not in ['not_available', None]:
                    click.echo(f"📊 mAP (macro): {map_score:.4f}")
                
                # Métricas hierárquicas
                if metrics.get('hierarchical_f1') not in ['not_available', None]:
                    click.echo(f"\n🌳 MÉTRICAS HIERÁRQUICAS:")
                    click.echo(f"   Precisão: {metrics.get('hierarchical_precision', 0.0):.4f}")
                    click.echo(f"   Recall: {metrics.get('hierarchical_recall', 0.0):.4f}")
                    click.echo(f"   F1-Score: {metrics.get('hierarchical_f1', 0.0):.4f}")
                    click.echo(f"   Distância média: {metrics.get('mean_hierarchical_distance', 0.0):.4f}")
                
                # Informações gerais
                click.echo(f"\n📋 INFORMAÇÕES:")
                click.echo(f"   Amostras: {metrics.get('total_samples', 0)}")
                click.echo(f"   Classes verdadeiras: {metrics.get('num_classes', 0)}")
                click.echo(f"   Classes preditas: {metrics.get('num_predicted_classes', 0)}")
            
            if format == 'json':
                # Imprimir JSON das métricas principais
                summary_metrics = {
                    "accuracy": metrics.get('accuracy', 0.0),
                    "precision_macro": metrics.get('precision_macro', 0.0),
                    "recall_macro": metrics.get('recall_macro', 0.0),
                    "f1_macro": metrics.get('f1_macro', 0.0),
                    "youdens_j": metrics.get('youdens_j', 0.0)
                }
                click.echo(json.dumps(summary_metrics, indent=2))
            
            # Arquivos gerados
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
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
def compare(results_dir, output, metric, verbose):
    """Comparar múltiplos resultados de classificação"""
    
    verbose = ctx.obj.get('verbose', False)
    results_path = Path(results_dir)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"🔍 Comparando resultados em: {results_path}")
    
    # Procurar arquivos de métricas
    metrics_files = list(results_path.glob("**/metrics_summary.json"))
    prediction_files = list(results_path.glob("**/predicted_results.csv"))
    
    if not metrics_files and not prediction_files:
        click.echo("❌ Nenhum arquivo de resultado encontrado")
        return
    
    comparison_data = []
    
    # Processar arquivos de métricas
    for metrics_file in metrics_files:
        run_name = metrics_file.parent.name
        
        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
            
            data = {"run": run_name, "source": "metrics"}
            data.update(metrics)
            comparison_data.append(data)
            
            if verbose:
                click.echo(f"   📊 {run_name}: {metrics.get(metric, 'N/A')}")
                
        except Exception as e:
            click.echo(f"   ❌ Erro ao ler {metrics_file}: {str(e)}")
    
    # Processar arquivos de predição sem métricas
    for pred_file in prediction_files:
        run_name = pred_file.parent.name
        
        # Verificar se já foi processado via metrics
        if any(item['run'] == run_name for item in comparison_data):
            continue
        
        try:
            df = pd.read_csv(pred_file)
            
            data = {
                "run": run_name,
                "source": "predictions",
                "total_samples": len(df)
            }
            
            if "Predicted label" in df.columns:
                predictions = df["Predicted label"].value_counts()
                data["unique_predictions"] = len(predictions)
                data["top_prediction"] = predictions.index[0] if len(predictions) > 0 else "N/A"
            
            comparison_data.append(data)
            
        except Exception as e:
            click.echo(f"   ❌ Erro ao ler {pred_file}: {str(e)}")
    
    if comparison_data:
        # Criar DataFrame para comparação
        comparison_df = pd.DataFrame(comparison_data)
        
        # Salvar comparação
        comparison_file = output_path / "comparison_results.csv"
        comparison_df.to_csv(comparison_file, index=False)
        
        # Mostrar resumo
        click.echo(f"\n📊 COMPARAÇÃO DE {len(comparison_data)} EXECUÇÕES:")
        click.echo("=" * 60)
        
        # Ordenar por métrica se disponível
        if metric in comparison_df.columns:
            comparison_df_sorted = comparison_df.sort_values(metric, ascending=False)
            click.echo(f"Ranking por {metric}:")
            for i, (_, row) in enumerate(comparison_df_sorted.iterrows(), 1):
                metric_value = row.get(metric, 'N/A')
                click.echo(f"  {i}. {row['run']}: {metric_value}")
        else:
            for _, row in comparison_df.iterrows():
                click.echo(f"  - {row['run']}: {row.get('total_samples', 'N/A')} sequências")
        
        # Estatísticas gerais
        if metric in comparison_df.columns:
            metric_values = comparison_df[metric].dropna()
            if len(metric_values) > 0:
                click.echo(f"\nEstatísticas de {metric}:")
                click.echo(f"  Média: {metric_values.mean():.4f}")
                click.echo(f"  Desvio padrão: {metric_values.std():.4f}")
                click.echo(f"  Melhor: {metric_values.max():.4f}")
                click.echo(f"  Pior: {metric_values.min():.4f}")
        
        # Gerar relatório detalhado
        report_file = output_path / "comparison_report.txt"
        with open(report_file, 'w') as f:
            f.write("RELATÓRIO DE COMPARAÇÃO - TE EVALUATION TOOL\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total de execuções: {len(comparison_data)}\n")
            f.write(f"Métrica principal: {metric}\n\n")
            
            f.write("RESULTADOS DETALHADOS:\n")
            f.write("-" * 30 + "\n")
            for _, row in comparison_df.iterrows():
                f.write(f"\nExecução: {row['run']}\n")
                for col, val in row.items():
                    if col != 'run':
                        f.write(f"  {col}: {val}\n")
        
        click.echo(f"\n💾 Comparação salva:")
        click.echo(f"   📊 {comparison_file}")
        click.echo(f"   📖 {report_file}")
        
    else:
        click.echo("❌ Nenhum dado válido encontrado para comparação")

# ==================== COMANDOS UTILITÁRIOS ====================

@cli.command('info')
@click.pass_context
def info(ctx):
    """Mostrar informações sobre a ferramenta e ambiente"""
    
    click.echo("🔬 TE Evaluation Tool v5.0")
    click.echo("=" * 40)
    
    # Informações do sistema
    click.echo(f"🐍 Python: {sys.version.split()[0]}")
    click.echo(f"📁 Diretório atual: {os.getcwd()}")
    
    # Verificar disponibilidade de módulos
    modules_status = {
        "EnvironmentManager": EnvironmentManager is not None,
        "TEMetricsEvaluator": TEMetricsEvaluator is not None,
        "pandas": True,  # Já importado
        "click": True    # Já importado
    }
    
    click.echo(f"\n📦 Módulos disponíveis:")
    for module, available in modules_status.items():
        status = "✅" if available else "❌"
        click.echo(f"   {status} {module}")
    
    # Verificar estrutura do projeto
    important_paths = [
        "ClassifyTE/",
        "ClassifyTE/generate_feature_file.py",
        "ClassifyTE/evaluate.py",
        "ClassifyTE/models/",
        "nodes/tree.txt",
        "nodes/node.txt"
    ]
    
    click.echo(f"\n📁 Estrutura do projeto:")
    for path in important_paths:
        exists = Path(path).exists()
        status = "✅" if exists else "❌"
        click.echo(f"   {status} {path}")
    
    # Verificar modelos disponíveis
    models_dir = Path("ClassifyTE/models")
    if models_dir.exists():
        model_files = list(models_dir.glob("*.pkl"))
        click.echo(f"\n🤖 Modelos encontrados ({len(model_files)}):")
        for model_file in model_files:
            click.echo(f"   📄 {model_file.name}")
    
    # Verificar ambientes virtuais
    if EnvironmentManager:
        envs_dir = Path("model_envs")
        if envs_dir.exists():
            env_dirs = [d for d in envs_dir.iterdir() if d.is_dir()]
            click.echo(f"\n🌍 Ambientes virtuais ({len(env_dirs)}):")
            for env_dir in env_dirs:
                python_path = env_dir / "bin" / "python"
                status = "✅" if python_path.exists() else "❌"
                click.echo(f"   {status} {env_dir.name}")

@cli.command('clean')
@click.option('--target', type=click.Choice(['temp', 'envs', 'results', 'all']), 
              default='temp', help='O que limpar')
@click.confirmation_option(prompt='Confirma a limpeza?')
@click.pass_context
def clean(ctx, target):
    """Limpar arquivos temporários e caches"""
    
    verbose = ctx.obj.get('verbose', False)
    
    cleaned_items = []
    
    if target in ['temp', 'all']:
        # Limpar arquivos temporários do ClassifyTE
        temp_patterns = [
            "ClassifyTE/features_*",
            "ClassifyTE/data/*.csv",
            "ClassifyTE/outputs/predicted_*"
        ]
        
        for pattern in temp_patterns:
            for temp_file in Path(".").glob(pattern):
                try:
                    if temp_file.is_dir():
                        shutil.rmtree(temp_file)
                    else:
                        temp_file.unlink()
                    cleaned_items.append(str(temp_file))
                    if verbose:
                        click.echo(f"🧹 Removido: {temp_file}")
                except Exception as e:
                    click.echo(f"⚠️ Erro ao remover {temp_file}: {str(e)}")
    
    if target in ['envs', 'all']:
        # Limpar ambientes virtuais
        envs_dir = Path("model_envs")
        if envs_dir.exists():
            try:
                shutil.rmtree(envs_dir)
                cleaned_items.append("model_envs/")
                if verbose:
                    click.echo("🧹 Ambientes virtuais removidos")
            except Exception as e:
                click.echo(f"⚠️ Erro ao remover ambientes: {str(e)}")
    
    if target in ['results', 'all']:
        # Limpar resultados antigos (cuidado!)
        results_dir = Path("results")
        if results_dir.exists():
            try:
                shutil.rmtree(results_dir)
                cleaned_items.append("results/")
                if verbose:
                    click.echo("🧹 Resultados removidos")
            except Exception as e:
                click.echo(f"⚠️ Erro ao remover resultados: {str(e)}")
    
    if cleaned_items:
        click.echo(f"✅ Limpeza concluída: {len(cleaned_items)} itens removidos")
    else:
        click.echo("✅ Nada para limpar")

# ==================== COMANDOS DE HELP E EXEMPLOS ====================

@cli.command('examples')
def examples():
    """Mostrar exemplos de uso da ferramenta"""
    
    click.echo("🚀 EXEMPLOS DE USO - TE Evaluation Tool v5.0")
    click.echo("=" * 50)
    
    examples = [
        {
            "title": "Setup inicial",
            "commands": [
                "python3 te_eval_cli.py env setup",
                "python3 te_eval_cli.py info"
            ]
        },
        {
            "title": "Validação de arquivos",
            "commands": [
                "python3 te_eval_cli.py validate --input data/default_dataset.fasta",
                "python3 te_eval_cli.py validate --input data/default_dataset.fasta --detailed"
            ]
        },
        {
            "title": "Classificação básica",
            "commands": [
                "python3 te_eval_cli.py run --model classifyte --input data/default_dataset.fasta --output results/basic",
                "python3 te_eval_cli.py run --model classifyte --input data/default_dataset.fasta --output results/advanced --algorithm nllcpn --clean"
            ]
        },
        {
            "title": "Avaliação de métricas",
            "commands": [
                "python3 te_eval_cli.py evaluate --predictions results/basic/predicted_results.csv --output results/metrics",
                "python3 te_eval_cli.py evaluate --predictions results/basic/predicted_results.csv --output results/metrics --format json"
            ]
        },
        {
            "title": "Comparação de resultados",
            "commands": [
                "python3 te_eval_cli.py compare --results-dir results/ --output comparison",
                "python3 te_eval_cli.py compare --results-dir results/ --metric accuracy"
            ]
        },
        {
            "title": "Manutenção",
            "commands": [
                "python3 te_eval_cli.py clean --target temp",
                "python3 te_eval_cli.py env clean"
            ]
        }
    ]
    
    for example in examples:
        click.echo(f"\n📋 {example['title']}:")
        click.echo("-" * 30)
        for cmd in example['commands']:
            click.echo(f"  {cmd}")

@cli.command('quickstart')
@click.option('--input', default='data/default_dataset.fasta', help='Arquivo FASTA para teste')
def quickstart(input):
    """Execução rápida para teste inicial"""
    
    click.echo("🚀 QUICKSTART - TE Evaluation Tool")
    click.echo("=" * 40)
    
    # Verificar se arquivo existe
    if not Path(input).exists():
        click.echo(f"❌ Arquivo não encontrado: {input}")
        click.echo("   Certifique-se de ter um arquivo FASTA válido")
        return
    
    # Executar pipeline completo
    steps = [
        f"python3 te_eval_cli.py validate --input {input}",
        f"python3 te_eval_cli.py run --model classifyte --input {input} --output quickstart_results",
        "python3 te_eval_cli.py evaluate --predictions quickstart_results/predicted_results.csv --output quickstart_results/metrics"
    ]
    
    click.echo("Executando pipeline completo:")
    for i, step in enumerate(steps, 1):
        click.echo(f"\n{i}. {step}")
        
        # Simular execução (na prática, você executaria os comandos)
        click.echo(f"   ⏳ Executando...")
        
        # Aqui você poderia chamar as funções diretamente ou usar subprocess
        # Por simplicidade, apenas mostramos os comandos
    
    click.echo(f"\n✅ Pipeline quickstart definido!")
    click.echo(f"📁 Resultados serão salvos em: quickstart_results/")
    click.echo(f"\nPara executar manualmente, rode os comandos acima em sequência.")

if __name__ == '__main__':
    cli()