# lib/models/terl_runner.py
import click
import subprocess
import os
import shutil
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# Importações dos módulos da pasta 'lib'
from lib.metrics_evaluator import TEMetricsEvaluator
from lib.fasta_label_mapper import FASTALabelMapper

class TERLRunner:
    """Executor para o modelo TERL"""

    def __init__(self, python_path, input_file, output_dir, model_file, verbose=False, skip_evaluation=False):
        self.python_path = python_path
        self.input_file = input_file
        self.output_dir = output_dir
        self.model_file = model_file
        self.verbose = verbose
        self.skip_evaluation = skip_evaluation
        self.mapper = FASTALabelMapper(tree_file="./src/nodes/tree.txt")

    def _parse_terl_output_header(self, header):
        """
        Extrai o ID da sequência e o rótulo da predição do cabeçalho de saída do TERL.
        Exemplo: ">TERL_predicted_ATRAN|1.1_LTR-Retrotransposon/Gypsy"
        """
        if not isinstance(header, str) or not header.startswith('>'):
            return None, None
        
        header = header[1:] # Remove o '>'
        
        # Extrai o ID da sequência e o rótulo da predição
        parts = header.split('/', 1)
        predicted_label = parts[-1].strip() # Limpa espaços em branco
        
        # O TERL_predicted pode ter nomes como "TERL_predicted_seq1_1"
        seq_id_part = parts[0].replace("TERL_predicted_", "").strip()

        # Tenta extrair o ID original
        parsed_header = self.mapper.parse_fasta_header(seq_id_part)
        sequence_id = parsed_header['seq_id'] if parsed_header else seq_id_part

        return sequence_id, predicted_label

    def run(self):
        """Executa a classificação com terl_test.py"""
        
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Verificar se o modelo e o script existem
        if not Path(self.model_file).exists():
            click.echo(f"❌ Modelo não encontrado: {self.model_file}")
            return False
            
        terl_test_script = Path('./src/models/TERL') / "terl_test.py"
        if not terl_test_script.exists():
            click.echo(f"❌ Script de teste do TERL não encontrado: {terl_test_script}")
            return False
            
        click.echo("🧠 Executando predição com TERL...")
        
        # Parâmetros de execução do TERL
        batch_size = 32
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

        click.echo("🔄 Buscando arquivo de saída e convertendo para CSV...")
        
        output_fasta_files = list(Path(os.getcwd()).glob(f"{prefix}{Path(self.input_file).stem}*"))

        if not output_fasta_files:
            click.echo("❌ O arquivo de saída do TERL não foi encontrado.")
            return False

        output_fasta_path = output_fasta_files[0]
        
        predictions = []
        with open(output_fasta_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    sequence_id, predicted_label = self._parse_terl_output_header(line)
                    if sequence_id and predicted_label:
                        predictions.append({
                            "Sequence ID": sequence_id,
                            "Predicted label": predicted_label
                        })

        df = pd.DataFrame(predictions)
        
        output_csv_name = f"predicted{Path(self.input_file).stem}.csv"
        output_csv_path = output_path / output_csv_name
        df.to_csv(output_csv_path, index=False)
        
        click.echo(f"📄 Arquivo de saída CSV salvo em: {output_csv_path}")

        os.remove(output_fasta_path)

        # Exibição da distribuição das predições
        click.echo(f"\n📊 Resultados processados: {len(df)} sequências")
        if "Predicted label" in df.columns:
            predictions_counts = df["Predicted label"].value_counts()
            click.echo("   Distribuição de predições:")
            for pred, count in predictions_counts.head().items():
                click.echo(f"     {pred}: {count}")
            if len(predictions_counts) > 5:
                click.echo(f"     ... e mais {len(predictions_counts) - 5} classes")

        # Geração do arquivo de metadados
        click.echo("\n💾 Gerando arquivo de metadados...")
        
        metadata = {
            "total_sequences": len(df),
            "model": "terl",
            "model_file": self.model_file,
            "input_file": str(Path(self.input_file).name),
            "output_dir": str(output_path),
            "python_environment": self.python_path,
            "timestamp": datetime.now().isoformat()
        }
        
        metadata_file = output_path / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        click.echo(f"📄 Arquivo de metadados salvo em: {metadata_file}")
        
        # Verificação e execução da avaliação
        if not self.skip_evaluation:
            mapper = FASTALabelMapper()
            predictions_df = mapper.add_actual_labels_to_predictions(output_csv_path, self.input_file)
            
            if 'Actual_Label' in predictions_df.columns and predictions_df['Actual_Label'].notna().any():
                click.echo("\n🔬 Avaliando métricas...")
                try:
                    evaluator = TEMetricsEvaluator()
                    metrics = evaluator.evaluate_predictions(output_csv_path, output_path)

                    click.echo("\n📈 MÉTRICAS PRINCIPAIS:")
                    click.echo("=" * 50)
                    click.echo(f"🎯 Acurácia: {metrics.get('accuracy', 0.0):.4f}")
                    click.echo(f"🎯 Precisão (macro): {metrics.get('precision_macro', 0.0):.4f}")
                    click.echo(f"🎯 Recall (macro): {metrics.get('recall_macro', 0.0):.4f}")
                    click.echo(f"🎯 F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}")
                    click.echo(f"🎯 Especificidade: {metrics.get('specificity_macro', 0.0):.4f}")
                    click.echo(f"🎯 Youden's J: {metrics.get('youdens_j', 0.0):.4f}")
                    
                    click.echo("\n✅ Avaliação concluída com sucesso!")
                except Exception as e:
                    click.echo(f"❌ Erro na avaliação: {str(e)}")
                    return False
            else:
                click.echo("\n⚠️ Aviso: Sem labels verdadeiros para avaliação. Use --auto-label ou certifique-se de que o arquivo de entrada está formatado corretamente.")
        
        return True