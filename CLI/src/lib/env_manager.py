import subprocess
import sys
from pathlib import Path
import json
import os
import shutil

class EnvironmentManager:
    def __init__(self):
        base_dir = Path(__file__).parent.parent  # CLI/src/
        self.envs_dir = (base_dir / "model_envs").resolve()
        self.envs_dir.mkdir(exist_ok=True)
        
        self.model_configs = {
            "classifyte": {
                "env_name": "classifyte_env",
                "requirements": [
                    "numpy==1.19.5",
                    "scipy==1.5.4", 
                    "pandas==1.1.5",
                    "scikit-learn==0.24.2",
                    "networkx==2.4"
                ],
                "python_version": "3.9"
            },
            "terl": {
                "env_name": "terl_env",
                "requirements": ["numpy", "tensorflow~=2.16.1", "matplotlib", "scikit-learn", "seaborn"],
                "python_version": "3.9" 
            },
            "yoro": {
                "env_name": "yoro_env",
                "requirements": [
                    "tensorflow==2.8.0", "protobuf==3.20.3", "biopython==1.78",
                    "pandas==1.5.3", "numpy<2.0", "scipy==1.11.1",
                    "matplotlib==3.7.1", "click==8.0.4", "h5py>=3.1.0", "tqdm"
                ],
                "python_version": "3.9"
            },
            "inpactor2": {
                "env_name": "inpactor2_env",
                "requirements": [
                    "tensorflow==2.8.0",
                    "protobuf<4.0",
                    "numpy<2.0",
                    "biopython", 
                    "pandas",
                    "scikit-learn", 
                    "scipy",
                    "seaborn", 
                    "matplotlib", 
                    "focal-loss",
                    "psutil"
                ],
                "python_version": "3.9"
            }
        }
    
    def create_environment(self, model_name):
        if model_name not in self.model_configs:
            raise ValueError(f"Modelo '{model_name}' não configurado")
        
        config = self.model_configs[model_name]
        env_path = self.envs_dir / config["env_name"]
        
        print(f"🔧 Criando ambiente para {model_name}...")
        if env_path.exists():
            shutil.rmtree(env_path)
        
        python_cmd = f"python{config['python_version']}"
        try:
            subprocess.run([python_cmd, "--version"], capture_output=True, check=True)
        except:
            python_cmd = "python3"
        
        subprocess.run([python_cmd, "-m", "venv", str(env_path)], check=True)
        
        pip_path = env_path / "bin" / "pip"
        if not pip_path.exists(): pip_path = env_path / "Scripts" / "pip.exe"
        
        print(f"📚 Instalando dependências...")
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)

        if "requirements_file" in config:
            subprocess.run([str(pip_path), "install", "-r", str(config["requirements_file"])], check=True)
        elif "requirements" in config:
            for req in config["requirements"]:
                print(f"   Instalando {req}...")
                subprocess.run([str(pip_path), "install", req], check=True)
        
        self._save_env_config(env_path, config)
        print(f"✅ Ambiente {model_name} criado em: {env_path}")
        return env_path
    
    def get_python_path(self, model_name):
        config = self.model_configs.get(model_name)
        if not config: raise ValueError(f"Modelo {model_name} desconhecido")
        
        env_path = self.envs_dir / config["env_name"]
        
        if not env_path.exists():
            print(f"⚠️ Ambiente para {model_name} não encontrado. Criando automaticamente...")
            self.create_environment(model_name)
            
        python_path = env_path / "bin" / "python"
        if not python_path.exists(): python_path = env_path / "Scripts" / "python.exe"
        
        return str(python_path.absolute())

    def list_environments(self):
        for model in self.model_configs:
            print(f"📦 {model}")

    def setup_all_environments(self):
        for model in self.model_configs:
            self.create_environment(model)
            
    def clean_environments(self):
        if self.envs_dir.exists():
            shutil.rmtree(self.envs_dir)
            
    def _save_env_config(self, env_path, config):
        config_file = env_path / "env_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

if __name__ == "__main__":
    EnvironmentManager().list_environments()