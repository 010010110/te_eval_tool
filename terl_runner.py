import click
import subprocess
import shutil
import pandas as pd
from pathlib import Path
import os

try:
    from fasta_label_mapper import FASTALabelMapper
except ImportError:
    FASTALabelMapper = None

try:
    from metrics_evaluator import TEMetricsEvaluator
except ImportError:
    TEMetricsEvaluator = None

class TERLRunner:
    """Executor dedicado para o modelo TERL"""
    
    def __init__(self, python_path, input_file, output_dir, model_file, verbose=False, clean_temp=False, auto_label=False, skip_evaluation=False):
        self.python_path = python_path
        self.input_file = input_file
        self.output_dir = output_dir
        self.model_file = model_file
        self.verbose = verbose
        self.clean_temp = clean_temp
        self.auto_label = auto_label
        self.skip_evaluation = skip_evaluation

    def run(self):
        """Executa o pipeline completo do TERL"""
        
        click.echo("⚙️ Executando TERL...")
        
        input_path = Path(self.input_file).resolve()
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        temp_dir = output_path / "terl_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        if not Path(self.model_file).exists():
            click.echo(f"❌ Erro: Modelo TERL não encontrado em: {self.model_file}")
            return False
            
        script_path = "TERL-master/terl_test.py" 
        if not Path(script_path).exists():
            script_path = "TERL/terl_test.py"
            if not Path(script_path).exists():
                click.echo(f"❌ Erro: Script 'terl_test.py' não encontrado.")
                return False

        temp_prefix = (temp_dir / f"{input_path.stem}_pred_").resolve()
        output_fasta_path = temp_dir / f"{input_path.stem}_pred_{input_path.name}"
        
        cmd_classify = [
            self.python_path,
            script_path,
            "-m", self.model_file,
            "-f", str(input_path), 
            "-p", str(temp_prefix), 
            "-q" 
        ]
        
        if self.verbose: click.echo(f"   Comando: {' '.join(cmd_classify)}")

        result = subprocess.run(cmd_classify, capture_output=True, text=True, cwd=Path.cwd())
        
        if result.returncode != 0:
            click.echo(f"❌ Erro na classificação do TERL:\n{result.stderr}")
            return False
            
        if not output_fasta_path.exists():
            click.echo(f"❌ Erro: Arquivo de saída do TERL não foi criado.")
            return False
            
        click.echo(f"📄 Saída FASTA do TERL gerada.")
        click.echo("🔄 Convertendo saída FASTA do TERL para CSV...")
        
        try:
            original_ids = []
            predicted_labels = []
            
            with open(input_path, 'r') as f_in:
                for line in f_in:
                    if line.startswith(">"):
                        original_ids.append(line.strip()[1:]) 
            
            with open(output_fasta_path, 'r') as f_out:
                for line in f_out:
                    if line.startswith(">"):
                        # O TERL test corrigido escreve >Classe\tContador
                        full_description = line.strip()[1:].rsplit('\t', 1)[0]
                        predicted_labels.append(full_description)

            if len(original_ids) != len(predicted_labels):
                click.echo(f"❌ Erro: Incompatibilidade de contagem. Entrada: {len(original_ids)}, Saída: {len(predicted_labels)}")
                return False

            # Padronização
            df = pd.DataFrame({
                'Sequence ID': original_ids,
                'Predicted label': predicted_labels,
                'Final_Confidence_Score': 1.0 # TERL não exporta score no fasta padrão
            })
            
            final_file = output_path / "predicted_results.csv"
            df.to_csv(final_file, index=False)
            
            click.echo(f"📊 Resultados convertidos e salvos em: {final_file}")

        except Exception as e:
            click.echo(f"❌ Erro na conversão TERL: {e}")
            return False

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
            click.echo("🧹 Limpando arquivos temporários do TERL...")
            shutil.rmtree(temp_dir)
            
        return True
