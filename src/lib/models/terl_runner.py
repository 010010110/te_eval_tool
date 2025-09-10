# lib/models/terl_runner.py
import click
import subprocess
import os
import shutil
import pandas as pd
from pathlib import Path
from datetime import datetime

class TERLRunner:
    """Executor para o modelo TERL"""

    def __init__(self, python_path, input_file, output_dir, model_file, verbose=False):
        self.python_path = python_path
        self.input_file = input_file
        self.output_dir = output_dir
        self.model_file = model_file
        self.verbose = verbose
    
    def run(self):
        """Executa a classificação com terl_test.py"""
        
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Verificar se o modelo e o script existem
        if not Path(self.model_file).exists():
            click.echo(f"❌ Modelo não encontrado: {self.model_file}")
            return False
            
        terl_test_script = Path('./src/models/TERL') / "terl_test.py" # Usando o novo parâmetro
        if not terl_test_script.exists():
            click.echo(f"❌ Script de teste do TERL não encontrado: {terl_test_script}")
            return False
            
        click.echo("🧠 Executando predição com TERL...")
        
        # Parâmetros de execução do TERL
        batch_size = 32 # Valor padrão
        prefix = "TERL_predicted"
        
        cmd = [
            self.python_path,
            str(terl_test_script),
            "-m", self.model_file,
            "-f", self.input_file,
            "-b", str(batch_size),
            "-p", prefix
        ]

        if not self.verbose:
            cmd.append("-q")

        if self.verbose:
            click.echo(f"   Comando: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            click.echo(f"❌ Erro na execução do TERL:")
            click.echo(f"   STDOUT: {result.stdout}")
            click.echo(f"   STDERR: {result.stderr}")
            return False
            
        click.echo("✅ Predição executada com sucesso")

        output_fasta_name = f"{prefix}_{Path(self.input_file).name}"
        output_fasta_path = Path(output_fasta_name)

        if not output_fasta_path.exists():
            click.echo("❌ O arquivo de saída do TERL não foi encontrado.")
            return False

        shutil.move(output_fasta_path, output_path / output_fasta_name)
        click.echo(f"📄 Arquivo de saída FASTA salvo em: {output_path / output_fasta_name}")
        
        return True