import click
import sys
import subprocess

try:
    from lib.env_manager import EnvironmentManager
except ImportError:
    EnvironmentManager = None

@click.group('env')
def env_commands():
    """Comandos para gerenciamento de ambientes virtuais específicos por modelo"""
    pass

@env_commands.command('setup')
@click.option('--model', type=click.Choice(['classifyte', 'terl', 'yoro', 'inpactor2', 'all']), default='all',
              help='Modelo específico ou todos')
def setup_envs(model):
    """
    Configurar ambientes virtuais com versões Python específicas.
    """
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    
    if model == 'all':
        click.echo("🚀 Configurando TODOS os ambientes...")
        click.echo("   • TERL: Python 3.9 (Requerimentos específicos)")
        click.echo("   • ClassifyTE: Python 3.9 (Bibliotecas padrão)")
        click.echo("   • YORO: Python 3.9 (TensorFlow 2.8)")
        click.echo("   • Inpactor2: Python 3.9 (TensorFlow, BioPython, etc)")
        click.echo("")
        env_manager.setup_all_environments()
    else:
        click.echo(f"🚀 Configurando ambiente {model.upper()}...")
        
        try:
            env_manager.create_environment(model)
            click.echo(f"✅ Ambiente {model} configurado com sucesso!")
            
            click.echo(f"\n🧪 Verificando ambiente {model}...")
            # Verifica se o python do ambiente responde
            python_path = env_manager.get_python_path(model)
            result = subprocess.run([python_path, "--version"], capture_output=True, text=True)
            
            if result.returncode == 0:
                click.echo(f"✅ Python acessível: {result.stdout.strip()}")
            else:
                click.echo(f"⚠️ Ambiente criado, mas Python retornou erro.")
                    
        except Exception as e:
            click.echo(f"❌ Erro: {str(e)}")
            sys.exit(1)

@env_commands.command('list')
def list_envs():
    """Listar ambientes disponíveis"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    env_manager.list_environments()

@env_commands.command('verify')
@click.option('--model', type=click.Choice(['classifyte', 'terl', 'yoro', 'inpactor2', 'all']), default='all',
              help='Verificar modelo específico ou todos')
def verify_envs(model):
    """Verificar se ambientes estão funcionando corretamente"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    
    if model == 'all':
        models_to_verify = ['terl', 'classifyte', 'yoro', 'inpactor2']
    else:
        models_to_verify = [model]
    
    all_good = True
    
    for model_name in models_to_verify:
        try:
            click.echo(f"\n🧪 Verificando {model_name.upper()}...")
            
            # Verificação simples: tentar chamar o python do ambiente
            try:
                python_path = env_manager.get_python_path(model_name)
                res = subprocess.run([python_path, "--version"], capture_output=True, text=True)
                if res.returncode == 0:
                    click.echo(f"✅ {model_name.upper()}: OK ({res.stdout.strip()})")
                else:
                    click.echo(f"❌ {model_name.upper()}: Falha ao executar python")
                    all_good = False
            except Exception as e:
                click.echo(f"❌ {model_name.upper()}: Ambiente não encontrado ou quebrado")
                all_good = False
                
        except Exception as e:
            click.echo(f"❌ {model_name.upper()}: Erro - {str(e)}")
            all_good = False
    
    if all_good:
        click.echo(f"\n🎉 Todos os ambientes verificados estão funcionais!")
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

@env_commands.command('info')
def info_envs():
    """Mostrar informações detalhadas sobre os ambientes"""
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        return

    click.echo("📋 INFORMAÇÕES DOS AMBIENTES")
    click.echo("=" * 45)
    # Apenas um display estático informativo
    click.echo("Os ambientes são criados em src/model_envs/ e isolam as dependências.")
    click.echo("Use 'env setup' para criá-los baseado no env_manager.py")