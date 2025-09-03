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
@click.pass_context
def validate(ctx, input_file, format_type, detailed, verbose):
    """Validar arquivo de entrada"""
    
    # Obter verbose do contexto se não especificado
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
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
@click.pass_context
def run(ctx, model, input_file, output_dir, algorithm, model_file, node_file, 
        skip_evaluation, clean, verbose, auto_label):
    """Executar classificação usando ambiente específico do modelo"""
    
    # Obter verbose do contexto se não especificado
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
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
@click.pass_context
def map_labels(ctx, fasta, predictions, output, validate_only, tree_file, verbose):
    """Mapear headers FASTA para códigos hierárquicos"""
    
    if not FASTALabelMapper:
        click.echo("❌ FASTALabelMapper não disponível")
        sys.exit(1)
    
    # Obter verbose do contexto se não especificado
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
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
@click.pass_context
def evaluate_metrics(ctx, predictions, output_dir, hierarchy, format, verbose):
    """Avaliar predições com métricas padronizadas completas"""
    
    # Obter verbose do contexto se não especificado
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
@click.option('--auto-evaluate', is_flag=True, 
              help='Calcular métricas automaticamente para arquivos sem avaliação')
@click.option('--include-incomplete', is_flag=True, 
              help='Incluir resultados sem métricas completas')
@click.option('--min-samples', default=1, help='Número mínimo de amostras para incluir')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def compare(ctx, results_dir, output, metric, auto_evaluate, include_incomplete, min_samples, verbose):
    """Comparar múltiplos resultados de classificação com avaliação automática"""
    
    # Obter verbose do contexto se não especificado
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
    
    # Processar cada diretório de resultado
    for result_dir in result_dirs:
        run_name = result_dir.name
        
        if verbose:
            click.echo(f"\n🔄 Processando: {run_name}")
        
        # Procurar métricas existentes
        metrics_files = list(result_dir.glob("**/metrics_summary.json"))
        prediction_files = list(result_dir.glob("**/predicted_*.csv"))
        
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
                    metrics = json.load(f)
                
                run_data.update(metrics)
                run_data["source"] = "existing_metrics"
                
                if verbose:
                    click.echo(f"   ✅ Métricas carregadas: {metrics.get(metric, 'N/A')}")
                
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
                        metrics = evaluator.evaluate_predictions(
                            str(prediction_file), 
                            str(temp_metrics_dir)
                        )
                        
                        if isinstance(metrics, dict) and 'accuracy' in metrics:
                            # Filtrar apenas métricas numéricas para comparação
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
        click.echo("   - Verifique se os arquivos predicted_*.csv existem")
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
                source_icon = {"existing_metrics": "📊", "auto_evaluated": "🔬", "predictions_only": "📄"}.get(row["source"], "❓")
                click.echo(f"  {i:2d}. {source_icon} {row['run']:<20} : {metric_value:.4f}")
            
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

# ==================== COMANDOS UTILITÁRIOS ====================

@cli.command('diagnose')
@click.option('--results-dir', required=True, type=click.Path(exists=True),
              help='Diretório com resultados para diagnosticar')
@click.option('--fix', is_flag=True, help='Tentar corrigir problemas automaticamente')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def diagnose(ctx, results_dir, fix, verbose):
    """Diagnosticar problemas em diretórios de resultados"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    results_path = Path(results_dir)
    click.echo(f"🔍 Diagnosticando: {results_path}")
    
    issues = []
    fixable_issues = []
    
    # Verificar estrutura de diretórios
    subdirs = [d for d in results_path.iterdir() if d.is_dir()]
    
    click.echo(f"\n📁 ESTRUTURA DE DIRETÓRIOS:")
    click.echo(f"   Encontrados {len(subdirs)} subdiretórios")
    
    for subdir in subdirs:
        click.echo(f"\n📂 {subdir.name}:")
        
        # Verificar arquivos de predição
        prediction_files = list(subdir.glob("**/predicted_*.csv"))
        metrics_files = list(subdir.glob("**/metrics_summary.json"))
        
        click.echo(f"   📄 Arquivos de predição: {len(prediction_files)}")
        click.echo(f"   📊 Arquivos de métricas: {len(metrics_files)}")
        
        if prediction_files:
            pred_file = prediction_files[0]
            click.echo(f"   📍 Predições: {pred_file.relative_to(results_path)}")
            
            # Analisar arquivo de predição
            try:
                df = pd.read_csv(pred_file)
                click.echo(f"   🔢 Linhas: {len(df)}")
                click.echo(f"   📋 Colunas: {list(df.columns)}")
                
                # Verificar colunas importantes
                required_cols = ['Sequence ID', 'Predicted label']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    issue = f"{subdir.name}: Colunas obrigatórias faltando: {missing_cols}"
                    issues.append(issue)
                    click.echo(f"   ❌ {issue}")
                
                # Verificar se tem labels verdadeiros
                has_actual_labels = 'Actual_Label' in df.columns
                actual_label_count = 0
                if has_actual_labels:
                    actual_label_count = df['Actual_Label'].notna().sum()
                
                click.echo(f"   🏷️  Labels verdadeiros: {'Sim' if has_actual_labels else 'Não'}")
                if has_actual_labels:
                    click.echo(f"   📊 Labels válidos: {actual_label_count}/{len(df)}")
                    
                    if actual_label_count == 0:
                        issue = f"{subdir.name}: Labels verdadeiros vazios"
                        issues.append(issue)
                        click.echo(f"   ⚠️  Todos os labels verdadeiros estão vazios")
                    elif actual_label_count < len(df):
                        issue = f"{subdir.name}: Labels verdadeiros parcialmente vazios"
                        issues.append(issue)
                        click.echo(f"   ⚠️  Alguns labels verdadeiros estão vazios")
                
                # Verificar distribuição de predições
                if 'Predicted label' in df.columns:
                    pred_dist = df['Predicted label'].value_counts()
                    click.echo(f"   📈 Predições únicas: {len(pred_dist)}")
                    if len(pred_dist) > 0:
                        click.echo(f"   🔝 Mais comum: {pred_dist.index[0]} ({pred_dist.iloc[0]} vezes)")
                
                # Verificar se precisa de avaliação
                if has_actual_labels and actual_label_count > 0 and not metrics_files:
                    fixable_issue = {
                        'type': 'missing_metrics',
                        'dir': subdir,
                        'pred_file': pred_file,
                        'description': f"{subdir.name}: Tem labels verdadeiros mas sem métricas"
                    }
                    fixable_issues.append(fixable_issue)
                    click.echo(f"   🔧 CORRIGÍVEL: Pode calcular métricas automaticamente")
                
            except Exception as e:
                issue = f"{subdir.name}: Erro ao ler predições: {str(e)}"
                issues.append(issue)
                click.echo(f"   ❌ Erro ao ler arquivo: {str(e)}")
        
        else:
            issue = f"{subdir.name}: Nenhum arquivo de predição encontrado"
            issues.append(issue)
            click.echo(f"   ❌ Nenhum arquivo predicted_*.csv encontrado")
        
        if metrics_files:
            metrics_file = metrics_files[0]
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                click.echo(f"   ✅ Métricas carregadas: {len(metrics)} campos")
                
                # Verificar métricas principais
                key_metrics = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro']
                available_key_metrics = [m for m in key_metrics if m in metrics]
                click.echo(f"   📊 Métricas principais: {len(available_key_metrics)}/{len(key_metrics)}")
                
            except Exception as e:
                issue = f"{subdir.name}: Erro ao ler métricas: {str(e)}"
                issues.append(issue)
                click.echo(f"   ❌ Erro ao ler métricas: {str(e)}")
    
    # Resumo dos problemas
    click.echo(f"\n🔍 RESUMO DO DIAGNÓSTICO:")
    click.echo("=" * 40)
    
    if issues:
        click.echo(f"❌ {len(issues)} problemas encontrados:")
        for i, issue in enumerate(issues, 1):
            click.echo(f"   {i}. {issue}")
    else:
        click.echo("✅ Nenhum problema grave encontrado")
    
    if fixable_issues:
        click.echo(f"\n🔧 {len(fixable_issues)} problemas corrigíveis:")
        for i, issue in enumerate(fixable_issues, 1):
            click.echo(f"   {i}. {issue['description']}")
        
        # Oferecer correção automática
        if fix:
            click.echo(f"\n🛠️  APLICANDO CORREÇÕES:")
            
            for issue in fixable_issues:
                if issue['type'] == 'missing_metrics':
                    click.echo(f"   🔬 Calculando métricas para {issue['dir'].name}...")
                    
                    try:
                        if TEMetricsEvaluator:
                            evaluator = TEMetricsEvaluator()
                            metrics_dir = issue['dir'] / "auto_metrics"
                            metrics_dir.mkdir(exist_ok=True)
                            
                            metrics = evaluator.evaluate_predictions(
                                str(issue['pred_file']), 
                                str(metrics_dir)
                            )
                            
                            if isinstance(metrics, dict) and 'accuracy' in metrics:
                                click.echo(f"   ✅ Métricas calculadas: F1={metrics.get('f1_macro', 0):.3f}")
                            else:
                                click.echo(f"   ⚠️  Métricas calculadas mas incompletas")
                        else:
                            click.echo(f"   ❌ TEMetricsEvaluator não disponível")
                    
                    except Exception as e:
                        click.echo(f"   ❌ Erro ao calcular métricas: {str(e)}")
        
        elif not fix:
            click.echo(f"\n💡 Para corrigir automaticamente, use: --fix")
    
    # Sugestões
    click.echo(f"\n💡 SUGESTÕES:")
    
    dirs_without_metrics = len([d for d in subdirs if not list(d.glob("**/metrics_summary.json"))])
    if dirs_without_metrics > 0:
        click.echo(f"   • {dirs_without_metrics} diretórios sem métricas")
        click.echo(f"   • Execute: te_eval_cli.py evaluate --predictions <arquivo> --output <dir>")
    
    dirs_without_actual_labels = 0
    dirs_with_partial_labels = 0
    
    for subdir in subdirs:
        pred_files = list(subdir.glob("**/predicted_*.csv"))
        if pred_files:
            try:
                df = pd.read_csv(pred_files[0])
                if 'Actual_Label' not in df.columns:
                    dirs_without_actual_labels += 1
                elif df['Actual_Label'].isna().any():
                    dirs_with_partial_labels += 1
            except:
                pass
    
    if dirs_without_actual_labels > 0:
        click.echo(f"   • {dirs_without_actual_labels} diretórios sem labels verdadeiros")
        click.echo(f"   • Execute: te_eval_cli.py map-labels --fasta <arquivo> --predictions <csv>")
    
    if dirs_with_partial_labels > 0:
        click.echo(f"   • {dirs_with_partial_labels} diretórios com labels parciais")
        click.echo(f"   • Verifique o mapeamento automático de labels")
    
    # Comando sugerido para comparação
    if len(subdirs) > 1:
        click.echo(f"\n🔗 PARA COMPARAÇÃO:")
        if dirs_without_metrics == 0:
            click.echo(f"   te_eval_cli.py compare --results-dir {results_path}")
        else:
            click.echo(f"   te_eval_cli.py compare --results-dir {results_path} --auto-evaluate --include-incomplete")
    
    return issues, fixable_issues

@cli.command('info')
@click.pass_context
def info(ctx):
    """Mostrar informações sobre a ferramenta e ambiente"""
    
    click.echo("🔬 TE Evaluation Tool v5.0.1")
    click.echo("=" * 40)
    
    # Informações do sistema
    click.echo(f"🐍 Python: {sys.version.split()[0]}")
    click.echo(f"📁 Diretório atual: {os.getcwd()}")
    
    # Verificar disponibilidade de módulos
    modules_status = {
        "EnvironmentManager": EnvironmentManager is not None,
        "TEMetricsEvaluator": TEMetricsEvaluator is not None,
        "FASTALabelMapper": FASTALabelMapper is not None,
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
    
    click.echo("🚀 EXEMPLOS DE USO - TE Evaluation Tool v5.0.1")
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
@click.pass_context
def quickstart(ctx, input):
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