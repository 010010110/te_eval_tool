import click
import subprocess
import shutil
import pandas as pd
from pathlib import Path
import os

from lib.metrics_evaluator import TEMetricsEvaluator
from lib.fasta_label_mapper import FASTALabelMapper

class YORORunner:

    
    def __init__(self, python_path, model_file, input_file, output_dir, verbose=False, clean_temp=False, auto_label=False, skip_evaluation=False,
                 window=50000, threads=None, threshold=0.8, cycles=1):
        self.python_path = python_path
        self.model_file = model_file
        self.input_file = input_file
        self.output_dir = output_dir
        self.verbose = verbose
        self.clean_temp = clean_temp
        self.auto_label = auto_label
        self.skip_evaluation = skip_evaluation
        # YORO-specific runtime options
        self.window = window
        self.threads = threads
        self.threshold = threshold
        self.cycles = cycles
        
        if self.verbose:
            click.echo(f"🛠️ YORO Runner configurado com modelo: {self.model_file}")

    def run(self):
              
        click.echo("⚙️ Executando YORO...")
        YORO_BASE_DIR = Path(__file__).parent.parent.parent / "models" / "YORO"
        
        input_path = Path(self.input_file).resolve()
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        temp_dir = output_path / "yoro_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        script_path = YORO_BASE_DIR / "pipelineDomain.py"
        if not Path(script_path).exists():
            click.echo(f" Erro: Script 'pipelineDomain.py' nao encontrado em: YORO-master/")
            return False

        model_path = Path(self.model_file).resolve()
        
        if not script_path.exists():
            click.echo(f"❌ Erro: Script 'pipelineDomain.py' nao encontrado em: {script_path.parent}")
            return False
        
        if not model_path.exists():
            click.echo(f"❌ Erro: Modelo YORO nao encontrado em: {model_path}")
            return False

        
        sanitized_fasta_path = temp_dir / "sanitized_input.fasta"
        if self.verbose: click.echo(f"Sanitizando arquivo FASTA para o YORO...")
        
        original_ids = []
        try:
            with open(input_path, 'r') as f_in, open(sanitized_fasta_path, 'w') as f_out:
                for line in f_in:
                    if line.startswith(">"):
                        # Store the full header (without '>')
                        original_header = line.strip()[1:]
                        original_ids.append(original_header)
                        
                        # Sanitize only the first token for YORO compatibility
                        first_token = original_header.split()[0]
                        sanitized_id = first_token.replace('#', '_').replace('|', '_')
                        
                        rest_of_header = line.strip()[1:].partition(' ')[2]
                        if rest_of_header: f_out.write(f">{sanitized_id} {rest_of_header}\n")
                        else: f_out.write(f">{sanitized_id}\n")
                    else:
                        f_out.write(line)
        except Exception as e:
            click.echo(f"Erro ao sanitizar FASTA: {e}")
            return False

        # Use absolute paths for command arguments so the subprocess resolves
        # files correctly even when we change cwd.
        sanitized_fasta_abs = str(sanitized_fasta_path.resolve())
        temp_dir_abs = str(temp_dir.resolve())
        script_path_abs = str(script_path.resolve())

        cmd_classify = [
            self.python_path,
            script_path_abs,
            "-f", sanitized_fasta_abs,
            "-d", temp_dir_abs,
            "-m", str(model_path),
        ]

        # Append YORO-specific flags understood by pipelineDomain.py
        try:
            if self.window is not None:
                cmd_classify.extend(["-w", str(int(self.window))])
        except Exception:
            pass

        if self.threads is not None:
            cmd_classify.extend(["-p", str(int(self.threads))])

        if self.threshold is not None:
            cmd_classify.extend(["-t", str(float(self.threshold))])

        if self.cycles is not None:
            cmd_classify.extend(["-c", str(int(self.cycles))])
        
        if self.verbose: click.echo(f"  Comando: {' '.join(cmd_classify)}")

        test_dir = temp_dir / "test"
        test_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(cmd_classify, capture_output=True, text=True, cwd=temp_dir_abs)
        
        if result.returncode != 0:
            click.echo(f"Erro na classificacao do YORO:")
            if self.verbose:
                click.echo(f"  STDOUT: {result.stdout}")
                click.echo(f"  STDERR: {result.stderr}")
            return False
            
        yoro_output_file = temp_dir / "output.tab"
        if not yoro_output_file.exists():
            click.echo(f"Erro: Arquivo de saida do YORO nao encontrado.")
            return False
            
        click.echo(f"✅ Saida tabular do YORO gerada.")

        # Copiar arquivo nativo do YORO para diretório de saída
        click.echo("📋 Copiando arquivo nativo do YORO...")
        try:
            final_output_file = output_path / "YORO_output.tab"
            shutil.copy2(yoro_output_file, final_output_file)
            click.echo(f"✅ Arquivo YORO_output.tab salvo em: {final_output_file}")
        except Exception as e:
            click.echo(f"❌ Erro ao copiar saida do YORO: {e}")
            return False

        if self.clean_temp:
            click.echo("🧹 Limpando arquivos temporários do YORO...")
            shutil.rmtree(temp_dir)

        return True