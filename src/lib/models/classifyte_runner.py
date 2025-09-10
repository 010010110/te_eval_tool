import click
import subprocess
import shutil
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

# Importações dos módulos da pasta 'lib'
from lib.env_manager import EnvironmentManager
from lib.metrics_evaluator import TEMetricsEvaluator
from lib.fasta_label_mapper import FASTALabelMapper

class ClassifyTERunner:
    """Executor para o modelo ClassifyTE"""
    
    def __init__(self, python_path, input_file, output_dir, algorithm, model_file, node_file, verbose=False, clean_temp=False, auto_label=False, skip_evaluation=False):
        self.python_path = python_path
        self.input_file = input_file
        self.output_dir = output_dir
        self.algorithm = algorithm
        self.model_file = model_file
        self.node_file = node_file
        self.verbose = verbose
        self.clean_temp = clean_temp
        self.auto_label = auto_label
        self.skip_evaluation = skip_evaluation

    def run(self):
        """Executa a classificação, processa a saída e avalia"""
        
        input_path = Path(self.input_file)
        output_path = Path(self.output_dir)
        
        # Corrigido: Cria o diretório de saída antes de qualquer operação de arquivo
        output_path.mkdir(parents=True, exist_ok=True)

        # Verificar se modelo existe
        model_path = Path("./src/models/ClassifyTE/models") / self.model_file
        if not model_path.exists():
            click.echo(f"❌ Modelo não encontrado: {model_path}")
            return False
        
        # Verificar se arquivo de nós existe
        nodes_path = Path("./src/models/ClassifyTE/nodes") / self.node_file
        if not nodes_path.exists():
            nodes_path = Path("nodes") / self.node_file
            if not nodes_path.exists():
                click.echo(f"❌ Arquivo de nós não encontrado: {self.node_file}")
                return False
        
        # Copiar FASTA para ClassifyTE/data
        target_fasta = Path("./src/models/ClassifyTE/data") / input_path.name
        if input_path.resolve() != target_fasta.resolve():
            shutil.copy(input_path, target_fasta)
            if self.verbose:
                click.echo(f"📄 FASTA copiado para {target_fasta}")
        
        base_name = input_path.stem
        features_file = f"{base_name}.csv"
        features_dir = f"{base_name}"
        
        # Limpar arquivos temporários existentes
        temp_files = [
            Path("./src/models/ClassifyTE") / features_dir,
            Path("./src/models/ClassifyTE/data") / features_file
        ]
        
        for temp_file in temp_files:
            if temp_file.exists():
                if temp_file.is_dir():
                    if self.verbose:
                        click.echo(f"🧹 Removendo diretório: {temp_file}")
                    shutil.rmtree(temp_file)
                else:
                    if self.verbose:
                        click.echo(f"🧹 Removendo arquivo: {temp_file}")
                    temp_file.unlink()
        
        # Passo 1: Gerar features
        click.echo("⚙️ Gerando features...")
        cmd_generate = [
            self.python_path, "generate_feature_file.py",
            "-f", input_path.name,
            "-o", features_file,
            "-d", features_dir
        ]
        
        if self.verbose:
            click.echo(f"   Comando: {' '.join(cmd_generate)}")
        
        result = subprocess.run(cmd_generate, cwd="./src/models/ClassifyTE", capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"❌ Erro na geração de features:")
            click.echo(f"   STDOUT: {result.stdout}")
            click.echo(f"   STDERR: {result.stderr}")
            return False
        click.echo(f"✅ Features geradas: {features_file}")
        
        # Passo 2: Executar predição
        click.echo("🧠 Executando predição...")
        cmd_evaluate = [
            self.python_path, "evaluate.py",
            "-f", features_file,
            "-d", features_dir,
            "-n", self.node_file,
            "-m", self.model_file,
            "-a", self.algorithm
        ]
        
        if self.verbose:
            click.echo(f"   Comando: {' '.join(cmd_evaluate)}")
        
        result = subprocess.run(cmd_evaluate, cwd="./src/models/ClassifyTE", capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"❌ Erro na predição:")
            click.echo(f"   STDOUT: {result.stdout}")
            click.echo(f"   STDERR: {result.stderr}")
            return False
        
        if self.verbose:
            click.echo("✅ Predição executada com sucesso")
        
        # Passo 3: Localizar e copiar resultados
        expected_result = Path("./src/models/ClassifyTE/outputs") / f"predicted_out_{features_dir}.csv"
        if not expected_result.exists():
            outputs_dir = Path("./src/models/ClassifyTE/outputs")
            if outputs_dir.exists():
                predicted_files = list(outputs_dir.glob("predicted_*.csv"))
                if predicted_files:
                    expected_result = max(predicted_files, key=os.path.getmtime)
                else:
                    click.echo("❌ Nenhum arquivo de resultado encontrado")
                    return False
            else:
                click.echo("❌ Diretório outputs/ não encontrado")
                return False
        
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
            
            metadata = {
                "total_sequences": len(df),
                "model": "./src/models/ClassifyTE",
                "algorithm": self.algorithm,
                "model_file": self.model_file,
                "node_file": self.node_file,
                "features_generated": True,
                "python_environment": self.python_path
            }
            
            metadata_file = output_path / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            if self.clean_temp:
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