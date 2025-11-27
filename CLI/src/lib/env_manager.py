
import subprocess
import sys
from pathlib import Path
import json
import os
import shutil

class EnvironmentManager:
    """Gerencia ambientes virtuais específicos para cada modelo"""
    
    def __init__(self):
        self.envs_dir = Path("/app/CLI/src/model_envs")
        self.envs_dir.mkdir(exist_ok=True)
        

        self.model_configs = {
            "classifyte": {
                "env_name": "classifyte_env",
                "requirements": [
                    "networkx>=2.4,<3.0",
                    "numpy>=1.19.0,<1.25.0", 
                    "pandas>=1.0.0,<1.6.0",
                    "scikit-learn>=0.23.0,<0.25.0",
                    "scipy>=1.5.0,<1.8.0"
                ],
                "python_version": "3.9"
            },
            "terl": {
                "env_name": "terl_env",
                "requirements": [
                    "numpy",
                    "tensorflow~=2.16.1",
                    "matplotlib",
                    "scikit-learn",
                    "seaborn"
                ],
                "python_version": "3.9"
            },
            "yoro": {
                "env_name": "yoro_env",
                "requirements": [
                    "tensorflow==2.8.0", 
                    "protobuf==3.20.3",
                    "biopython==1.78",
                    "pandas==1.5.3",
                    "numpy<2.0",
                    "scipy==1.11.1",
                    "matplotlib==3.7.1",
                    "click==8.0.4",
                    "h5py>=3.1.0", 
                    "tqdm"
                ],
                "python_version": "3.9"
            }
        }
    
    def create_environment(self, model_name):
        """Cria ambiente virtual para modelo específico"""
        
        if model_name not in self.model_configs:
            raise ValueError(f"Modelo '{model_name}' não configurado")
        
        config = self.model_configs[model_name]
        env_path = self.envs_dir / config["env_name"]
        
        print(f"🔧 Criando ambiente para {model_name}...")
        

        if env_path.exists():
            print(f"🧹 Removendo ambiente existente: {env_path}")
            shutil.rmtree(env_path)
        

        python_cmd = f"python{config['python_version']}"
        if not self._check_python_version(python_cmd):
            python_cmd = "python3"  # Fallback
        
        print(f"📦 Criando ambiente virtual com {python_cmd}...")
        subprocess.run([python_cmd, "-m", "venv", str(env_path)], check=True)
        

        pip_path = env_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = env_path / "Scripts" / "pip.exe"  # Windows
        
        print(f"📚 Instalando dependências...")
        for requirement in config["requirements"]:
            print(f"   Instalando {requirement}...")
            subprocess.run([str(pip_path), "install", requirement], check=True)
        

        self._save_env_config(env_path, config)
        
        print(f"✅ Ambiente {model_name} criado com sucesso!")
        return env_path
    
    def get_python_path(self, model_name):
        """Retorna caminho do Python do ambiente do modelo"""
        
        if model_name not in self.model_configs:
            raise ValueError(f"Modelo '{model_name}' não configurado")
        
        config = self.model_configs[model_name]

        env_path = self.envs_dir / config["env_name"]
        

        if not env_path.exists():
            print(f"⚠️  Ambiente {model_name} não existe. Criando...")
            self.create_environment(model_name)
        

        unix_python_path = env_path / "bin" / "python"
        windows_python_path = env_path / "Scripts" / "python.exe"

        python_path = unix_python_path
        



        try:
            absolute_path_for_debug = unix_python_path.resolve()
            print(f"============================================================")
            print(f"🔍 DEBUG: Caminho Absoluto (resolved): {absolute_path_for_debug}")
            print(f"============================================================")
        except Exception as e:

            absolute_path_for_debug = f"[Caminho não resolvido: {unix_python_path}]"

        
        if not python_path.exists():
            python_path = windows_python_path
        

        if not python_path.exists():

            raise FileNotFoundError(f"Python não encontrado. Caminho ABSOLUTO esperado: {absolute_path_for_debug}")
        
        return str(python_path)
    
    def list_environments(self):
        """Lista ambientes disponíveis"""
        
        print("\n🌍 AMBIENTES DISPONÍVEIS:")
        print("=" * 40)
        
        for model_name, config in self.model_configs.items():
            env_path = self.envs_dir / config["env_name"]
            status = "✅ Criado" if env_path.exists() else "❌ Não criado"
            
            print(f"\n📦 {model_name.upper()}")
            print(f"   Ambiente: {config['env_name']}")
            print(f"   Python: {config['python_version']}")
            print(f"   Status: {status}")
            
            if env_path.exists():

                try:
                    python_path = self.get_python_path(model_name)
                    result = subprocess.run([
                        python_path, "-c", 
                        "import sys; import pkg_resources; print(f'Python: {sys.version.split()[0]}'); [print(f'{pkg.key}: {pkg.version}') for pkg in pkg_resources.working_set if pkg.key in ['numpy', 'pandas', 'scikit-learn', 'networkx', 'tensorflow', 'matplotlib', 'seaborn']]"
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"   Versões:")
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                print(f"     {line}")
                except:
                    print(f"   Versões: Erro ao verificar")
    
    def setup_all_environments(self):
        """Cria todos os ambientes configurados"""
        
        print("🚀 Configurando todos os ambientes...")
        
        for model_name in self.model_configs.keys():
            try:
                self.create_environment(model_name)
            except Exception as e:
                print(f"❌ Erro ao criar ambiente {model_name}: {str(e)}")
        
        print("\n✅ Setup de ambientes concluído!")
        self.list_environments()
    
    def clean_environments(self):
        """Remove todos os ambientes"""
        
        print("🧹 Removendo todos os ambientes...")
        
        if self.envs_dir.exists():
            shutil.rmtree(self.envs_dir)
        
        print("✅ Ambientes removidos!")
    
    def _check_python_version(self, python_cmd):
        """Verifica se versão específica do Python existe"""
        try:
            subprocess.run([python_cmd, "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _save_env_config(self, env_path, config):
        """Salva configuração do ambiente"""
        config_file = env_path / "env_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def verify_environment(self, model_name):
        """Verifica se o ambiente virtual do modelo está funcional e com dependências principais instaladas"""
        
        if model_name not in self.model_configs:
            print(f"Modelo '{model_name}' não configurado para verificação.")
            return False
            
        try:
            python_path = self.get_python_path(model_name)
             
            command = [
                python_path, 
                "-c", 
                "import sys; import numpy; import pandas; import tensorflow; print('Verification OK')"
            ]
            
            # Executa o comando
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=15  
            )

            if "Verification OK" in result.stdout:
                return True
            
            return False
                
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Erro de verificação no ambiente {model_name.upper()}.")
            print("   Falha ao importar dependências principais (e.g., numpy, tensorflow).")
            if e.stderr:
                 print(f"   Detalhes do erro: {e.stderr.strip().splitlines()[-1]}")
            return False
        except Exception as e:
            print(f"\n❌ Erro de verificação inesperado para {model_name.upper()}: {str(e)}")
            return False

if __name__ == "__main__":

    manager = EnvironmentManager()
    manager.list_environments()