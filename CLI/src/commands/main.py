import click
import subprocess
import os
import sys
import shutil
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

from lib.metrics_evaluator import TEMetricsEvaluator
from lib.env_manager import EnvironmentManager
from lib.fasta_label_mapper import FASTALabelMapper

# Importação dos Runners
from lib.models.classifyte_runner import ClassifyTERunner
from lib.models.terl_runner import TERLRunner
from lib.models.yoro_runner import YORORunner
from lib.models.inpactor2_runner import Inpactor2Runner

MODEL_RUNNERS = {
    'classifyte': ClassifyTERunner,
    'terl': TERLRunner,
    'yoro': YORORunner,
    'inpactor2': Inpactor2Runner,
}

@click.command()
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
    
    click.echo(f"🔍 Validando {input_file} (formato: {format_type})")
    
    if format_type == 'fasta':
        # Implementação simplificada de validação para manter o foco no run
        try:
            with open(input_file, 'r') as f:
                first_line = f.readline()
                if not first_line.startswith('>'):
                    click.echo("❌ Erro: Arquivo FASTA inválido (não começa com >)")
                    sys.exit(1)
            click.echo("✅ Formato FASTA parece válido (cabeçalho detectado)")
        except Exception as e:
            click.echo(f"❌ Erro ao ler arquivo: {e}")
            sys.exit(1)
    else:
        click.echo("✅ Formato CSV assumido como válido")


@click.command()
@click.option('--model', default='classifyte',
              type=click.Choice(['classifyte', 'terl', 'yoro', 'inpactor2']),
              help='Modelo a ser executado')
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True),
              help='Arquivo FASTA de entrada')
@click.option('--output', 'output_dir', required=True, help='Diretório de saída')
@click.option('--algorithm', default='lcpnb',
              type=click.Choice(['lcpnb', 'nllcpn']),
              help='Algoritmo hierárquico (ClassifyTE)')
@click.option('--model-file', help='Arquivo do modelo (.pkl, DS3 ou diretório da ferramenta)')
@click.option('--node-file', default='node.txt', help='Arquivo de nós hierárquicos')
@click.option('--window', type=int, default=50000, help='Window size (YORO)')
@click.option('--threads', type=int, default=None, help='Threads to use (YORO, optional)')
@click.option('--threshold', type=float, default=0.8, help='Prediction threshold (YORO)')
@click.option('--cycles', type=int, default=1, help='Number of cycles (YORO)')
@click.option('--skip-evaluation', is_flag=True, 
              help='Pular avaliação automática de métricas')
@click.option('--clean', is_flag=True, help='Limpar arquivos temporários após execução')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.option('--auto-label', is_flag=True,
              help='Mapear automaticamente labels do FASTA para avaliação')
@click.pass_context
def run(ctx, model, input_file, output_dir, algorithm, model_file, node_file,
    window, threads, threshold, cycles,
    skip_evaluation, clean, verbose, auto_label):
    """Executar classificação usando ambiente específico do modelo"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    start_time = datetime.now()
    
    if model not in MODEL_RUNNERS:
        click.echo(f"❌ Modelo '{model}' não configurado.")
        sys.exit(1)

    # Configuração de caminhos padrão
    if model == 'terl' and not model_file:
        model_file = './src/models/TERL/Models/DS3'
    elif model == 'classifyte' and not model_file:
        model_file = 'ClassifyTE_combined.pkl'
    elif model == 'yoro' and not model_file:
        model_file = './src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5'
    elif model == 'inpactor2' and not model_file:
        # Caminho padrão para o Inpactor2
        model_file = './src/models/Inpactor2'

    if model == 'classifyte' and model_file:
        from pathlib import Path
        model_path = Path(model_file)
        if model_path.is_absolute() or str(model_file).startswith('/'):
            # Extract just the filename for ClassifyTE
            model_file = model_path.name

    runner_class = MODEL_RUNNERS[model]
    
    try:
        # Verifica se o EnvironmentManager está disponível
        python_path = "python"
        if EnvironmentManager:
            try:
                python_path = EnvironmentManager().get_python_path(model)
            except Exception as e:
                click.echo(f"⚠️ Aviso: Não foi possível obter ambiente para {model}. Usando python do sistema.")
                click.echo(f"   Erro: {e}")

        # Instancia o Runner
        # kwargs permite flexibilidade entre construtores diferentes
        runner_kwargs = {
            'python_path': python_path,
            'input_file': input_file,
            'output_dir': output_dir,
            'model_file': model_file,
            'verbose': verbose,
            'clean_temp': clean,
            'auto_label': auto_label,
            'skip_evaluation': skip_evaluation
        }

        # Adiciona parâmetros específicos se necessário
        if model == 'classifyte':
            runner_kwargs['algorithm'] = algorithm
            runner_kwargs['node_file'] = node_file

        runner = runner_class(**runner_kwargs)
        if model == 'terl':
            runner = runner_class(
                python_path=EnvironmentManager().get_python_path(model),
                input_file=input_file,
                output_dir=output_dir,
                model_file=model_file,
                verbose=verbose,
                skip_evaluation=skip_evaluation
            )
        elif model == 'yoro': 
            runner = runner_class(
                python_path=EnvironmentManager().get_python_path(model),
                input_file=input_file,
                output_dir=output_dir,
                model_file=model_file,
                verbose=verbose,
                skip_evaluation=skip_evaluation,
                clean_temp=clean,
                auto_label=auto_label,
                window=window,
                threads=threads,
                threshold=threshold,
                cycles=cycles
            )
        else:
            runner = runner_class(
                python_path=EnvironmentManager().get_python_path(model),
                input_file=input_file,
                output_dir=output_dir,
                algorithm=algorithm,
                model_file=model_file,
                node_file=node_file,
                verbose=verbose,
                clean_temp=clean,
                auto_label=auto_label,
                skip_evaluation=skip_evaluation
            )
        
        click.echo(f"🔬 Executando {model} com {input_file}")
        click.echo(f"📁 Resultados em: {output_dir}")
        
        success = runner.run()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            click.echo(f"\n✅ Classificação {model} concluída com sucesso!")
            click.echo(f"⏱️  Tempo total: {duration:.1f}s")
        else:
            click.echo(f"❌ Falha na execução do {model}")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Erro crítico: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)