import click


from commands.environment import env_commands
from commands.main import validate, run
from commands.mapping import map_labels
from commands.evaluation import evaluate_metrics
from commands.comparison import compare
from commands.utilities import diagnose, info, clean, examples, quickstart

@click.group()
@click.version_option(version='5.0.1')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def cli(ctx, verbose):
    """
    TE Evaluation Tool v5.0 - Ferramenta padronizada para avaliação de 
    classificadores de elementos transponíveis com métricas completas
    """
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if verbose:
        click.echo("🔧 Modo verboso ativado")


cli.add_command(env_commands)
cli.add_command(validate)
cli.add_command(run)
cli.add_command(map_labels)
cli.add_command(evaluate_metrics)
cli.add_command(compare)
cli.add_command(diagnose)
cli.add_command(info)
cli.add_command(clean)
cli.add_command(examples)
cli.add_command(quickstart)

if __name__ == '__main__':
    cli()