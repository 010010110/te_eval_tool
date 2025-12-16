import click
import subprocess
import shutil
import pandas as pd
from pathlib import Path
import os
import sys
import re


try:
    from lib.metrics_evaluator import TEMetricsEvaluator
    from lib.fasta_label_mapper import FASTALabelMapper
except ImportError:
    TEMetricsEvaluator = None
    FASTALabelMapper = None

class Inpactor2Runner:
    
    def __init__(self, python_path, model_file, input_file, output_dir, verbose=False, clean_temp=False, auto_label=False, skip_evaluation=False, 
                 threads=None, cycles=1, max_len=15000, min_len=1000, annotate='no', tg_ca='no', tsd='no', curated='yes', **kwargs):
        self.python_path = python_path
        self.model_file = model_file
        self.input_file = input_file
        self.output_dir = output_dir
        self.verbose = verbose
        self.clean_temp = clean_temp
        self.auto_label = auto_label
        self.skip_evaluation = skip_evaluation
        self.threads = threads if threads else 4
        self.cycles = cycles
        self.max_len = max_len
        self.min_len = min_len
        self.annotate = annotate
        self.tg_ca = tg_ca
        self.tsd = tsd
        self.curated = curated
        
        if self.verbose:
            click.echo(f"🛠️ Inpactor2 Runner inicializado (Modo Não-Invasivo).")

    def run(self):
        click.echo("⚙️ Preparando execução do Inpactor2...")
        
      
        TOOL_DIR = Path(self.model_file).resolve()
        REAL_SCRIPT_PATH = TOOL_DIR / "Inpactor2.py"
        
       
        WRAPPER_PATH = Path(__file__).parent / "inpactor_wrapper.py"
        
        
        BASE_SRC_DIR = Path(__file__).parents[2]
        TREE_FILE_PATH = BASE_SRC_DIR / 'nodes' / 'tree.txt'
        
        input_path = Path(self.input_file).resolve()
        output_path = Path(self.output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        temp_dir = output_path / "inpactor2_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if not REAL_SCRIPT_PATH.exists():
            click.echo(f"❌ Erro: Script original não encontrado em: {REAL_SCRIPT_PATH}")
            return False
            
        if not WRAPPER_PATH.exists():
            click.echo(f"❌ Erro: Wrapper não encontrado em: {WRAPPER_PATH}")
            return False

        
        sanitized_fasta_path = temp_dir / "input_sanitized.fasta"
        if self.verbose: click.echo(f"🧹 Sanitizando headers e limpando nucleotídeos...")
        
        original_ids_map = {}
        try:
            with open(input_path, 'r') as f_in, open(sanitized_fasta_path, 'w') as f_out:
                for line in f_in:
                    line = line.strip()
                    if not line: continue
                    if line.startswith(">"):
                        original_header = line[1:]
                        original_id = original_header.split()[0]
                        sanitized_id = original_id.replace('|', '_').replace('#', '_').replace(':', '_')
                        original_ids_map[sanitized_id] = original_id
                        f_out.write(f">{sanitized_id}\n")
                    else:
                        clean_seq = re.sub(r'[^ACGTN]', 'N', line.upper())
                        f_out.write(clean_seq + "\n")
        except Exception as e:
            click.echo(f"❌ Erro ao sanitizar FASTA: {str(e)}")
            return False

        
        cmd = [
            self.python_path,
            str(WRAPPER_PATH),
            str(REAL_SCRIPT_PATH),
            "-f", str(sanitized_fasta_path),
            "-o", str(temp_dir),
            "-t", str(self.threads),
            "-C", str(self.cycles),
            "-m", str(self.max_len),
            "-n", str(self.min_len),
            "-a", self.annotate,
            "-i", self.tg_ca,
            "-d", self.tsd,
            "-c", self.curated
        ]
        
        if self.verbose:
            cmd.append("-V")
            cmd.append("yes")

        if self.verbose: 
            click.echo(f"💻 Comando Wrapper: {' '.join(cmd)}")
            click.echo(f"📂 CWD: {TOOL_DIR}")

       
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=str(TOOL_DIR) 
            )
            
            # Sempre mostrar stdout/stderr para debug
            if result.stdout:
                click.echo("=== STDOUT do Inpactor2 ===")
                click.echo(result.stdout)
                click.echo("===========================")
            
            if result.stderr:
                click.echo("=== STDERR do Inpactor2 ===")
                click.echo(result.stderr)
                click.echo("===========================")
            
            if result.returncode != 0:
                click.echo(f"❌ Erro na execução do Inpactor2 (Exit Code: {result.returncode})")
                return False
                
            if self.verbose:
                click.echo("✅ Execução finalizada com sucesso.")

        except Exception as e:
            click.echo(f"❌ Falha ao iniciar subprocesso: {str(e)}")
            return False

       
        # Copiar os arquivos originais do Inpactor2 para o diretório de saída final
        click.echo(f"📦 Copiando arquivos de saída do Inpactor2...")
        
        # Principais arquivos de saída do Inpactor2
        inpactor2_outputs = [
            "Inpactor2_library.fasta",
            "Inpactor2_predictions.tab"
        ]
        
        # Arquivos opcionais (RepeatMasker, se annotate=yes)
        optional_outputs = [
            "Inpactor2_anno_summary.txt",
        ]
        
        copied_files = []
        for filename in inpactor2_outputs:
            src = temp_dir / filename
            dest = output_path / filename
            if src.exists():
                shutil.copy2(src, dest)
                file_size = src.stat().st_size
                click.echo(f"   ✅ {filename} copiado ({file_size} bytes)")
                copied_files.append(filename)
            else:
                click.echo(f"   ⚠️ {filename} não encontrado (pode indicar que nenhum elemento foi detectado)")
        
        # Copiar arquivos opcionais se existirem
        for filename in optional_outputs:
            src = temp_dir / filename
            dest = output_path / filename
            if src.exists():
                shutil.copy2(src, dest)
                click.echo(f"   ✅ {filename} copiado (anotação opcional)")
                copied_files.append(filename)
        
        # Copiar arquivos do RepeatMasker se existirem (quando annotate=yes)
        for maskfile in temp_dir.glob("*.masked"):
            dest = output_path / maskfile.name
            shutil.copy2(maskfile, dest)
            click.echo(f"   ✅ {maskfile.name} copiado (RepeatMasker)")
            copied_files.append(maskfile.name)
        
        for gfffile in temp_dir.glob("*.gff"):
            dest = output_path / gfffile.name
            shutil.copy2(gfffile, dest)
            click.echo(f"   ✅ {gfffile.name} copiado (RepeatMasker)")
            copied_files.append(gfffile.name)
        
        if not copied_files:
            click.echo("⚠️ Aviso: Nenhum arquivo de saída foi copiado.")
            if "There is no LTR retrotransposons" in result.stdout:
                click.echo("   Motivo: Inpactor2 não encontrou LTR-retrotransposons válidos na sequência.")
            elif "Number of LTR-retrotransposons detected: 0" in result.stdout:
                click.echo("   Motivo: LTR_FINDER não detectou elementos com estrutura completa [LTR]-[internal]-[LTR].")
            else:
                click.echo("   Motivo: Verifique os logs acima para detalhes.")
        else:
            click.echo(f"✅ {len(copied_files)} arquivo(s) copiado(s) para: {output_path}")
        
        # NÃO gerar CSV, NÃO mapear labels, NÃO calcular métricas
        # O Inpactor2 já gerou seus próprios arquivos de saída que serão enviados por email

        if self.clean_temp:
            click.echo("🧹 Limpando arquivos temporários...")
            shutil.rmtree(temp_dir)

        return True