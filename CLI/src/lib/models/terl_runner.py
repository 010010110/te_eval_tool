
import click
import subprocess
import os
import shutil
import pandas as pd
import json
from pathlib import Path
from datetime import datetime


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
        self.original_headers = self._load_original_headers()

    def _load_original_headers(self):
        """Carrega os cabeçalhos originais do arquivo de entrada FASTA, na ordem que aparecem."""
        headers = []
        with open(self.input_file, 'r') as f:
            for line in f:
                if line.startswith(">"):
                    # Store the full header (without '>')
                    header_line = line[1:].strip()
                    headers.append(header_line)
        
        return headers

    def _parse_terl_output_header(self, header):
        """
        Extrai o rótulo da predição e o score de confiança do cabeçalho de saída do TERL.
        (Novo formato do terl_test: >LABELS||SCORE COUNT)
        
        Retorna: predicted_label (str), final_confidence_score (float ou None)
        """
        if not isinstance(header, str) or not header.startswith('>'):
            return None, None
        

        content = header[1:].strip()
        

        parts = content.split('||', 1)
        
        if len(parts) != 2:

            return None, None 

        raw_predicted_path_labels = parts[0].strip() # Ex: 'Class I     SINE'
        raw_score_and_count = parts[1].strip()     # Ex: '0.935367   1'


        try:
            raw_score = raw_score_and_count.split()[0] # split() sem argumento lida com múltiplos espaços/tabs
            final_confidence_score = float(raw_score)
        except (ValueError, IndexError):

            final_confidence_score = None
            


        predicted_path_parts = raw_predicted_path_labels.split()
        predicted_label = predicted_path_parts[-1] if predicted_path_parts else None

        if predicted_label is None or final_confidence_score is None:
            return None, None
            
        return predicted_label, final_confidence_score

    def run(self):
        """Executa a classificação com terl_test.py"""
        
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        

        if not Path(self.model_file).exists():
            click.echo(f"❌ Modelo não encontrado: {self.model_file}")
            return False
            
        terl_test_script = Path('./src/models/TERL') / "terl_test.py"
        if not terl_test_script.exists():
            click.echo(f"❌ Script de teste do TERL não encontrado: {terl_test_script}")
            return False
            
        click.echo("🧠 Executando predição com TERL...")
        

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
        

        i = 0 
        
        with open(output_fasta_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):

                    predicted_label, final_confidence_score = self._parse_terl_output_header(line)
                    
                    if predicted_label:

                        original_header = self.original_headers[i] if i < len(self.original_headers) else f"Seq_ID_Unknown_{i}"
                        
                        predictions.append({
                            "Sequence ID": original_header,
                            "Predicted label": predicted_label,
                            "Final_Confidence_Score": final_confidence_score 
                        })
                        i += 1 # Incrementa o contador somente após processar um header
                    else:

                        click.echo(f"   ❌ Erro de parsing no header: '{line}'") 

        df = pd.DataFrame(predictions)
        

        if df.empty:
            df = pd.DataFrame(columns=["Sequence ID", "Predicted label", "Final_Confidence_Score", "Predicted_Code", "Predicted_Path_Codes", "Actual_Code", "Actual_Label"])
            click.echo("   ⚠️ Aviso: O DataFrame de predições está vazio. Verifique o FASTA de saída do TERL.")


        output_csv_name = f"predicted{Path(self.input_file).stem}.csv"
        output_csv_path = output_path / output_csv_name
        

        if not df.empty:
            df['Predicted_Code'] = df['Predicted label'].apply(lambda x: self.mapper.get_code_from_label(x))
            df['Predicted_Path_Codes'] = df['Predicted_Code'].apply(lambda x: x.replace('.', ',') if isinstance(x, str) else None)
            click.echo("   Colunas Predicted_Code/Path_Codes adicionadas por inferência.")


            

            df.to_csv(output_csv_path, index=False)
            
            click.echo("🔄 Inserindo labels de verdade (Actual_Code/Label) via mapeamento...")
            
            # Call mapper and reload the updated CSV
            self.mapper.add_actual_labels_to_predictions(str(output_csv_path), self.input_file, output_csv=str(output_csv_path))
            
            # Reload the updated CSV
            df = pd.read_csv(output_csv_path)
            
            if 'Actual_Label' in df.columns:
                actual_count = df['Actual_Label'].notna().sum()
                click.echo(f"✅ Coluna Actual_Label adicionada com {actual_count} valores preenchidos")
            else:
                click.echo("⚠️ ERRO: Coluna Actual_Label NÃO foi adicionada!")
        
        click.echo(f"📄 Arquivo de saída CSV FINAL salvo em: {output_csv_path}")

        os.remove(output_fasta_path)


        if not self.skip_evaluation and not df.empty and 'Actual_Label' in df.columns:
            click.echo("\n🔬 Avaliando métricas...")
            

            try:
                evaluator = TEMetricsEvaluator()
                metrics = evaluator.evaluate_predictions(output_csv_path, output_path)

                click.echo("\n📈 MÉTRICAS PRINCIPAIS:")
                click.echo("=" * 50)
                click.echo(f"🎯 Acurácia: {metrics.get('accuracy', 0.0):.4f}")
                click.echo(f"🎯 Precisão (macro): {metrics.get('precision_macro', 0.0):.4f}")
                click.echo(f"🎯 F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}")
                
                click.echo("\n✅ Avaliação concluída com sucesso!")
            except Exception as e:
                click.echo(f"❌ Erro na avaliação: {str(e)}")
                return False
        elif not self.skip_evaluation and ('Actual_Label' not in df.columns or df['Actual_Label'].isna().all()):
            click.echo("\n⚠️ Aviso: O arquivo de predição final não contém labels verdadeiros válidos. A avaliação foi pulada.")
        
        return True