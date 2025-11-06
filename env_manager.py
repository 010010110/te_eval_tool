# env_manager.py - Gerenciador de ambientes por modelo
import subprocess
import sys
from pathlib import Path
import json
import os

class EnvironmentManager:
    """Gerencia ambientes virtuais específicos para cada modelo"""
    
    def __init__(self):
        self.envs_dir = Path("model_envs")
        self.envs_dir.mkdir(exist_ok=True)
        
        # Configurações de ambientes por modelo
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
            # # Preparado para futuros modelos
            # "inpactor2": {
            #     "env_name": "inpactor2_env", 
            #     "requirements": [
            #         "tensorflow>=2.8.0",
            #         "numpy>=1.21.0",
            #         "pandas>=1.3.0"
            #     ],
            #     "python_version": "3.8"
            # },
            
            # --- INÍCIO DA CORREÇÃO (TERL) ---
            "terl": {
                "env_name": "terl_env",
                # Otimizado para instalar a partir do requirements.txt do repositório clonado
                "requirements_file": "TERL/requirements.txt",
                "python_version": "3.9" 
            }
            # --- FIM DA CORREÇÃO (TERL) ---
        }
    
    def create_environment(self, model_name):
        """Cria ambiente virtual para modelo específico"""
        
        if model_name not in self.model_configs:
            raise ValueError(f"Modelo '{model_name}' não configurado")
        
        config = self.model_configs[model_name]
        env_path = self.envs_dir / config["env_name"]
        
        print(f"🔧 Criando ambiente para {model_name}...")
        
        # Remover ambiente existente se houver
        if env_path.exists():
            print(f"🧹 Removendo ambiente existente: {env_path}")
            import shutil
            shutil.rmtree(env_path)
        
        # Criar novo ambiente
        python_cmd = f"python{config['python_version']}"
        if not self._check_python_version(python_cmd):
            python_cmd = "python3" # Fallback
        
        print(f"📦 Criando ambiente virtual com {python_cmd}...")
        subprocess.run([python_cmd, "-m", "venv", str(env_path)], check=True)
        
        # Instalar dependências
        pip_path = env_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = env_path / "Scripts" / "pip.exe" # Windows
        
        print(f"📚 Instalando dependências...")

        # --- INÍCIO DA CORREÇÃO (Instalação) ---

        # Caso 1: Instalar de um requirements.txt (para TERL)
        if "requirements_file" in config:
            req_file = Path(config["requirements_file"])
            if not req_file.exists():
                raise FileNotFoundError(f"Arquivo de requirements não encontrado: {req_file}")
            
            print(f"  Instalando de {req_file}...")
            # Atualiza o pip primeiro
            subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True, capture_output=True)
            # Instala do arquivo
            subprocess.run([str(pip_path), "install", "-r", str(req_file)], check=True)

        # Caso 2: Instalar de uma lista (para ClassifyTE)
        elif "requirements" in config:
            for requirement in config["requirements"]:
                print(f"  Instalando {requirement}...")
                subprocess.run([str(pip_path), "install", requirement], check=True)
        
        else:
            print("⚠️ Nenhuma dependência (requirements) ou (requirements_file) definida.")

        # --- FIM DA CORREÇÃO (Instalação) ---
        
        # Salvar configuração do ambiente
        self._save_env_config(env_path, config)
        
        print(f"✅ Ambiente {model_name} criado com sucesso!")
        return env_path
    
    def get_python_path(self, model_name):
        """Retorna caminho do Python do ambiente do modelo"""
        
        if model_name not in self.model_configs:
            # Tenta encontrar pelo nome do env
            for model, config in self.model_configs.items():
                if config['env_name'] == model_name:
                    model_name = model
                    break
            else:
                 raise ValueError(f"Modelo '{model_name}' não configurado")
        
        config = self.model_configs[model_name]
        env_path = self.envs_dir / config["env_name"]
        
        # Verificar se ambiente existe
        if not env_path.exists():
            print(f"⚠️  Ambiente {model_name} não existe. Criando...")
            self.create_environment(model_name)
        
        # Retornar caminho absoluto do Python
        python_path = env_path.resolve() / "bin" / "python"
        if not python_path.exists():
            python_path = env_path.resolve() / "Scripts" / "python.exe" # Windows
        
        if not python_path.exists():
            raise FileNotFoundError(f"Python não encontrado em {env_path}")
        
        return str(python_path)
    
    def list_environments(self):
        """Lista ambientes disponíveis"""
        
        print("\n🌍 AMBIENTES DISPONÍVEIS:")
        print("=" * 40)
        
        for model_name, config in self.model_configs.items():
            env_path = self.envs_dir / config["env_name"]
            status = "✅ Criado" if env_path.exists() else "❌ Não criado"
            
            print(f"\n📦 {model_name.upper()}")
            print(f"  Ambiente: {config['env_name']}")
            print(f"  Python: {config['python_version']}")
            print(f"  Status: {status}")
            
            if env_path.exists():
                # Mostrar versões instaladas
                try:
                    python_path = self.get_python_path(model_name)
                    # --- CORREÇÃO (Lista de pacotes) ---
                    # Lista os pacotes relevantes para este modelo
                    if "requirements_file" in config:
                        # Para TERL, verificamos torch, numpy, pandas
                        pkg_list = "['torch', 'numpy', 'pandas']"
                    else:
                        # Para ClassifyTE
                        pkg_list = "['numpy', 'pandas', 'scikit-learn', 'networkx']"

                    result = subprocess.run([
                        python_path, "-c", 
                        f"import sys; import pkg_resources; print(f'Python: {sys.version.split()[0]}'); [print(f'  {pkg.key}: {pkg.version}') for pkg in pkg_resources.working_set if pkg.key in {pkg_list}]"
                    ], capture_output=True, text=True)
                    # --- FIM DA CORREÇÃO ---
                    
                    if result.returncode == 0:
                        print(f"  Versões:")
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                print(f"    {line}")
                except:
                    print(f"  Versões: Erro ao verificar")
    
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
            import shutil
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


if __name__ == "__main__":
    # Teste rápido
    manager = EnvironmentManager()
    manager.list_environments()