import click
import subprocess
import shutil
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

# Tenta importar módulos auxiliares
try:
    from fasta_label_mapper import FASTALabelMapper
except ImportError:
    FASTALabelMapper = None

try:
    from metrics_evaluator import TEMetricsEvaluator
except ImportError:
    TEMetricsEvaluator = None

class ClassifyTERunner:
    """Executor dedicado para o modelo ClassifyTE"""
    
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
        """Executa o pipeline completo do ClassifyTE"""
        
        input_path = Path(self.input_file)
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Verificações
        model_path = Path("ClassifyTE/models") / self.model_file
        if not model_path.exists():
            click.echo(f"❌ Modelo não encontrado: {model_path}")
            return False
        
        nodes_path = Path("ClassifyTE/nodes") / self.node_file
        if not nodes_path.exists():
            nodes_path = Path("nodes") / self.node_file
            if not nodes_path.exists():
                click.echo(f"❌ Arquivo de nós não encontrado: {self.node_file}")
                return False
        
        # Preparação dos arquivos
        target_fasta = Path("ClassifyTE/data") / input_path.name
        if input_path.resolve() != target_fasta.resolve():
            shutil.copy(input_path, target_fasta)
            if self.verbose: click.echo(f"📄 FASTA copiado para {target_fasta}")
        
        base_name = input_path.stem
        features_file = f"{base_name}.csv"
        features_dir = f"{base_name}"
        
        temp_files = [
            Path("ClassifyTE") / features_dir,
            Path("ClassifyTE/data") / features_file
        ]
        
        # Limpeza prévia
        for temp_file in temp_files:
            if temp_file.exists():
                if temp_file.is_dir(): shutil.rmtree(temp_file)
                else: temp_file.unlink()
        
        # Passo 1: Gerar Features
        click.echo("⚙️ Gerando features...")
        cmd_gen = [
            self.python_path, "generate_feature_file.py",
            "-f", input_path.name,
            "-o", features_file,
            "-d", features_dir
        ]
        if self.verbose: click.echo(f"   Comando: {' '.join(cmd_gen)}")
        
        result = subprocess.run(cmd_gen, cwd="ClassifyTE", capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"❌ Erro na geração de features:\n{result.stderr}")
            return False
        
        click.echo(f"✅ Features geradas: {features_file}")
        
        # Passo 2: Predição
        click.echo("🧠 Executando predição...")
        cmd_eval = [
            self.python_path, "evaluate.py",
            "-f", features_file,
            "-d", features_dir,
            "-n", self.node_file,
            "-m", self.model_file,
            "-a", self.algorithm
        ]
        if self.verbose: click.echo(f"   Comando: {' '.join(cmd_eval)}")
        
        result = subprocess.run(cmd_eval, cwd="ClassifyTE", capture_output=True, text=True)
        if result.returncode != 0:
            click.echo(f"❌ Erro na predição:\n{result.stderr}")
            return False
        
        if self.verbose: click.echo("✅ Predição executada com sucesso")
        
        # Passo 3: Processar Resultados
        expected_result = Path("ClassifyTE/outputs") / f"predicted_out_{features_dir}.csv"
        if not expected_result.exists():
            # Tenta achar o mais recente como fallback
            outputs_dir = Path("ClassifyTE/outputs")
            if outputs_dir.exists():
                predicted_files = list(outputs_dir.glob("predicted_*.csv"))
                if predicted_files:
                    expected_result = max(predicted_files, key=os.path.getmtime)
                else:
                    click.echo("❌ Nenhum arquivo de resultado encontrado")
                    return False
            else:
                return False
        
        # Padronização do CSV
        final_file = output_path / "predicted_results.csv"
        try:
            df = pd.read_csv(expected_result)
            rename_map = {
                'ID': 'Sequence ID', 'id': 'Sequence ID',
                'Predicted': 'Predicted label', 'Classification': 'Predicted label',
                'Probability': 'Final_Confidence_Score', 'Prob': 'Final_Confidence_Score'
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            
            if 'Final_Confidence_Score' not in df.columns: 
                df['Final_Confidence_Score'] = 1.0
            
            if 'Sequence ID' not in df.columns and 'id' in df.columns:
                 df = df.rename(columns={'id': 'Sequence ID'})

            df.to_csv(final_file, index=False)
            click.echo(f"\n📊 Resultados processados: {len(df)} sequências")
            
            # Metadados
            metadata = {
                "total_sequences": len(df),
                "model": "classifyte",
                "algorithm": self.algorithm,
                "model_file": self.model_file
            }
            with open(output_path / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
        except Exception as e:
            click.echo(f"⚠️ Erro ao padronizar CSV: {e}")
            shutil.copy(expected_result, final_file)

        # Passo 4: Auto Label e Avaliação
        if self.auto_label and FASTALabelMapper:
            click.echo(f"\n🏷️  Mapeando labels automaticamente...")
            try:
                mapper = FASTALabelMapper(base_dir=str(Path.cwd())) 
                map_success = mapper.add_actual_labels_to_predictions(
                    str(final_file.resolve()), 
                    str(Path(self.input_file).resolve())
                )
                if map_success: click.echo("✅ Labels mapeados com sucesso!")
            except Exception as e:
                click.echo(f"⚠️ Erro no mapeamento: {str(e)}")
        
        if not self.skip_evaluation and TEMetricsEvaluator and final_file.exists():
            click.echo(f"\n🔬 Executando avaliação automática...")
            try:
                evaluator = TEMetricsEvaluator()
                evaluator.evaluate_predictions(str(final_file), str(output_path))
                click.echo("✅ Avaliação automática concluída!")
            except Exception as e:
                click.echo(f"⚠️ Erro na avaliação: {str(e)}")

        if self.clean_temp:
            click.echo("🧹 Limpando arquivos temporários...")
            for temp_file in temp_files:
                if temp_file.exists():
                    if temp_file.is_dir(): shutil.rmtree(temp_file)
                    else: temp_file.unlink()
        
        return True
