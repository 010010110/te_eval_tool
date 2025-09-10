import click
import sys

try:
    from lib.env_manager import EnvironmentManager
except ImportError:
    print("⚠️ env_manager.py não encontrado. Alguns recursos podem não funcionar.")
    EnvironmentManager = None

@click.group('env')
def env_commands():
    """Comandos para gerenciamento de ambientes virtuais"""
    pass

@env_commands.command('setup')
@click.option('--model', type=click.Choice(['classifyte', 'terl', 'all']), default='all', help='Modelo específico ou todos')
def setup_envs(model):
    """Configurar ambientes virtuais para modelos"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    
    if model == 'all':
        click.echo("🚀 Configurando ambientes para todos os modelos...")
        env_manager.setup_all_environments()
    else:
        click.echo(f"🚀 Configurando ambiente para {model}...")
        try:
            env_manager.create_environment(model)
            click.echo(f"✅ Ambiente {model} configurado com sucesso!")
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

@env_commands.command('clean')
@click.confirmation_option(prompt='Tem certeza que deseja remover todos os ambientes?')
def clean_envs():
    """Remover todos os ambientes virtuais"""
    
    if not EnvironmentManager:
        click.echo("❌ EnvironmentManager não disponível")
        sys.exit(1)
    
    env_manager = EnvironmentManager()
    env_manager.clean_environments()