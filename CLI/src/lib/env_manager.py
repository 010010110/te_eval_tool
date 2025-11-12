# lib/env_manager.py - Gerenciador de ambientes por modelo
import subprocess
import sys
from pathlib import Path
import json
import os
import shutil

class EnvironmentManager:
    """Gerencia ambientes virtuais específicos para cada modelo"""
    
    def __init__(self):
        self.envs_dir = Path("./src/model_envs")
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
            }
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
            shutil.rmtree(env_path)
        
        # Criar novo ambiente
        python_cmd = f"python{config['python_version']}"
        if not self._check_python_version(python_cmd):
            python_cmd = "python3"  # Fallback
        
        print(f"📦 Criando ambiente virtual com {python_cmd}...")
        subprocess.run([python_cmd, "-m", "venv", str(env_path)], check=True)
        
        # Instalar dependências (lógica unificada para todos os modelos)
        pip_path = env_path / "bin" / "pip"
        if not pip_path.exists():
            pip_path = env_path / "Scripts" / "pip.exe"  # Windows
        
        print(f"📚 Instalando dependências...")
        for requirement in config["requirements"]:
            print(f"   Instalando {requirement}...")
            subprocess.run([str(pip_path), "install", requirement], check=True)
        
        # Salvar configuração do ambiente
        self._save_env_config(env_path, config)
        
        print(f"✅ Ambiente {model_name} criado com sucesso!")
        return env_path
    
    def get_python_path(self, model_name):
        """Retorna caminho do Python do ambiente do modelo"""
        
        if model_name not in self.model_configs:
            raise ValueError(f"Modelo '{model_name}' não configurado")
        
        config = self.model_configs[model_name]
        # self.envs_dir é Path("./src/model_envs")
        env_path = self.envs_dir / config["env_name"]
        
        # Verificar se ambiente existe
        if not env_path.exists():
            print(f"⚠️  Ambiente {model_name} não existe. Criando...")
            self.create_environment(model_name)
        
        # Definir caminhos
        unix_python_path = env_path / "bin" / "python"
        windows_python_path = env_path / "Scripts" / "python.exe"

        python_path = unix_python_path
        
        # =========================================================
        # 🔍 INSERÇÃO DO LOG DE DEBUG E RESOLUÇÃO DO CAMINHO ABSOLUTO
        # Tentamos resolver o caminho para ver onde ele aponta no FS do Docker
        try:
            absolute_path_for_debug = unix_python_path.resolve()
            print(f"============================================================")
            print(f"🔍 DEBUG: Caminho Absoluto (resolved): {absolute_path_for_debug}")
            print(f"============================================================")
        except Exception as e:
            # Em alguns casos, resolve() falha se o caminho não existir
            absolute_path_for_debug = f"[Caminho não resolvido: {unix_python_path}]"
        # =========================================================
        
        if not python_path.exists():
            python_path = windows_python_path
        
        # Verifica se o executável Python existe
        if not python_path.exists():
            # CRÍTICO: Relata o caminho absoluto (se resolvido) para o erro
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
                # Mostrar versões instaladas
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


if __name__ == "__main__":
    # Teste rápido
    manager = EnvironmentManager()
    manager.list_environments()