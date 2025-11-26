import click
import sys

try:
    from lib.env_manager import EnvironmentManager
except ImportError:
    print("⚠️ env_manager.py não encontrado. Alguns recursos podem não funcionar.")
    EnvironmentManager = None

@click.group('env')
def env_commands():
    """Comandos para gerenciamento de ambientes virtuais específicos por modelo"""
    pass

@env_commands.command('setup')
@click.option('--model', type=click.Choice(['classifyte', 'terl', 'all']), default='all', 
              help='Modelo específico ou todos (TERL=Python3.6, ClassifyTE=Python3.9)')
def setup_envs(model):
    """
    Configurar ambientes virtuais com versões Python específicas:
    • TERL: Python 3.6 + versões originais 
    • ClassifyTE: Python 3.9 + versões flexíveis
    """
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    
    if model == 'all':
        click.echo("🚀 Configurando TODOS os ambientes com versões específicas...")
        click.echo("   • TERL: Python 3.6 + versões originais")
        click.echo("   • ClassifyTE: Python 3.9 + versões flexíveis")
        click.echo("")
        env_manager.setup_all_environments()
    else:
        python_version = "3.6" if model == "terl" else "3.9"
        version_type = "originais" if model == "terl" else "flexíveis"
        
        click.echo(f"🚀 Configurando ambiente {model.upper()}...")
        click.echo(f"   Python: {python_version}")
        click.echo(f"   Versões: {version_type}")
        click.echo("")
        
        try:
            env_manager.create_environment(model)
            click.echo(f"✅ Ambiente {model} configurado com sucesso!")
            

            click.echo(f"\n🧪 Verificando ambiente {model}...")
            if env_manager.verify_environment(model):
                click.echo(f"✅ Ambiente {model} verificado e funcionando!")
            else:
                click.echo(f"⚠️ Possíveis problemas detectados no {model}")
                click.echo(f"💡 Execute: python src/main.py env verify --model {model}")
                    
        except Exception as e:
            click.echo(f"❌ Erro: {str(e)}")
            

            if model == "terl":
                click.echo("\n💡 DICA PARA TERL:")
                click.echo("   O TERL precisa de Python 3.6")
                click.echo("   Instale com: sudo apt-get install python3.6 python3.6-venv python3.6-dev")
                click.echo("   Ou use pyenv: pyenv install 3.6.15")
            elif model == "classifyte":
                click.echo("\n💡 DICA PARA CLASSIFYTE:")
                click.echo("   O ClassifyTE funciona melhor com Python 3.9")
                click.echo("   Instale com: sudo apt-get install python3.9 python3.9-venv python3.9-dev")
            
            sys.exit(1)

@env_commands.command('list')
def list_envs():
    """Listar ambientes disponíveis com suas versões Python específicas"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    env_manager.list_environments()

@env_commands.command('verify')
@click.option('--model', type=click.Choice(['classifyte', 'terl', 'all']), default='all',
              help='Verificar modelo específico ou todos')
def verify_envs(model):
    """Verificar se ambientes estão funcionando corretamente"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    
    if model == 'all':
        models_to_verify = ['terl', 'classifyte']
    else:
        models_to_verify = [model]
    
    all_good = True
    
    for model_name in models_to_verify:
        try:
            click.echo(f"\n🧪 Verificando {model_name.upper()}...")
            if env_manager.verify_environment(model_name):
                click.echo(f"✅ {model_name.upper()}: OK")
            else:
                click.echo(f"❌ {model_name.upper()}: Problemas detectados")
                all_good = False
        except Exception as e:
            click.echo(f"❌ {model_name.upper()}: Erro - {str(e)}")
            all_good = False
    
    if all_good:
        click.echo(f"\n🎉 Todos os ambientes estão funcionando!")
    else:
        click.echo(f"\n⚠️ Alguns ambientes têm problemas")
        click.echo(f"💡 Tente recriar: python src/main.py env setup --model <modelo>")

@env_commands.command('clean')
@click.confirmation_option(prompt='Tem certeza que deseja remover TODOS os ambientes específicos?')
def clean_envs():
    """Remover todos os ambientes virtuais específicos"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    env_manager.clean_environments()

@env_commands.command('check-python')
def check_python():
    """Verificar quais versões Python estão disponíveis no sistema"""
    
    import subprocess
    
    click.echo("🔍 VERIFICANDO VERSÕES PYTHON DISPONÍVEIS")
    click.echo("=" * 45)
    

    python_versions = [
        ("python3.6", "Para TERL"),
        ("python3.7", "Compatível com TERL"),
        ("python3.8", "Compatível com ambos"), 
        ("python3.9", "Para ClassifyTE"),
        ("python3.10", "Versão moderna"),
        ("python3", "Python 3 padrão"),
        ("python", "Python padrão")
    ]
    
    found_versions = []
    
    for py_cmd, description in python_versions:
        try:
            result = subprocess.run([py_cmd, "--version"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version_info = result.stdout.strip()
                found_versions.append((py_cmd, version_info, description))
                

                if "3.6." in version_info:
                    status = "✅ IDEAL para TERL"
                elif "3.9." in version_info:
                    status = "✅ IDEAL para ClassifyTE"
                elif any(v in version_info for v in ["3.7.", "3.8."]):
                    status = "✅ COMPATÍVEL com ambos"
                elif "3.10." in version_info or "3.11." in version_info:
                    status = "⚠️ Muito novo para TERL"
                else:
                    status = "❓ Verificar compatibilidade"
                
                click.echo(f"{status}")
                click.echo(f"   Comando: {py_cmd}")
                click.echo(f"   Versão: {version_info}")  
                click.echo(f"   Uso: {description}")
                click.echo("")
                
        except FileNotFoundError:
            continue
    
    if not found_versions:
        click.echo("❌ Nenhuma versão Python encontrada!")
        click.echo("\n💡 Instale Python:")
        click.echo("   Ubuntu: sudo apt-get install python3.6 python3.9")
        click.echo("   CentOS: sudo yum install python36 python39")
        click.echo("   macOS: brew install python@3.6 python@3.9")
    else:
        click.echo(f"📋 RESUMO: {len(found_versions)} versões encontradas")
        

        has_terl_python = any("3.6." in version for _, version, _ in found_versions)
        has_classifyte_python = any("3.9." in version for _, version, _ in found_versions)
        
        click.echo(f"   TERL (Python 3.6): {'✅ OK' if has_terl_python else '❌ FALTANDO'}")
        click.echo(f"   ClassifyTE (Python 3.9): {'✅ OK' if has_classifyte_python else '❌ FALTANDO'}")
        
        if not has_terl_python:
            click.echo("\n💡 Para instalar Python 3.6 (TERL):")
            click.echo("   Ubuntu: sudo apt-get install python3.6 python3.6-venv python3.6-dev")
            click.echo("   Ou use pyenv: pyenv install 3.6.15")
            
        if not has_classifyte_python:
            click.echo("\n💡 Para instalar Python 3.9 (ClassifyTE):")
            click.echo("   Ubuntu: sudo apt-get install python3.9 python3.9-venv python3.9-dev")
            click.echo("   Ou use pyenv: pyenv install 3.9.18")

@env_commands.command('info')
def info_envs():
    """Mostrar informações detalhadas sobre os ambientes específicos"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    click.echo("📋 INFORMAÇÕES DOS AMBIENTES ESPECÍFICOS")
    click.echo("=" * 45)
    click.echo("")
    click.echo("🔬 TERL (Transposable Element Ranker and Locator)")
    click.echo("   • Python necessário: 3.6")
    click.echo("   • Motivo: Desenvolvido originalmente em Python 3.6")
    click.echo("   • Versões fixas: numpy==1.18.1, tensorflow==2.4.0, etc.")
    click.echo("   • Ambiente: terl_env_py36")
    click.echo("")
    click.echo("🔬 CLASSIFYTE (Hierarchical Classification)")  
    click.echo("   • Python necessário: 3.9")
    click.echo("   • Motivo: Melhor compatibilidade com bibliotecas modernas")
    click.echo("   • Versões flexíveis: numpy>=1.19.0, etc.")
    click.echo("   • Ambiente: classifyte_env_py39")
    click.echo("")
    click.echo("💡 Para verificar se as versões Python estão disponíveis:")
    click.echo("   python3.6 --version  # Para TERL")
    click.echo("   python3.9 --version  # Para ClassifyTE")