
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


from lib.models.classifyte_runner import ClassifyTERunner
from lib.models.terl_runner import TERLRunner
from lib.models.yoro_runner import YORORunner


MODEL_RUNNERS = {
    'classifyte': ClassifyTERunner,
    'terl': TERLRunner,
    'yoro': YORORunner,
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
    
    def validate_fasta_detailed(file_path):

        pass
    
    def validate_fasta_simple(file_path):

        pass
    
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



@click.command()
@click.option('--model', default='classifyte', 
              type=click.Choice(['classifyte', 'terl', 'yoro']),
              help='Modelo a ser executado')
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True), 
              help='Arquivo FASTA de entrada')
@click.option('--output', 'output_dir', required=True, help='Diretório de saída')
@click.option('--algorithm', default='lcpnb', 
              type=click.Choice(['lcpnb', 'nllcpn']), 
              help='Algoritmo hierárquico (ClassifyTE)')
@click.option('--model-file', help='Arquivo do modelo (.pkl ou DS3)')
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
    
    if model not in MODEL_RUNNERS:
        click.echo(f"❌ Modelo '{model}' não configurado.")
        sys.exit(1)

    if model == 'terl' and not model_file:
        model_file = './src/models/TERL/Models/DS3'
    elif model == 'classifyte' and not model_file:
        model_file = 'ClassifyTE_combined.pkl'
    elif model == 'yoro' and not model_file:
        model_file = './src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5'

    runner_class = MODEL_RUNNERS[model]
    
    try:
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
                auto_label=auto_label
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
        click.echo(f"❌ Erro: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)