import click
import sys
from pathlib import Path

try:
    from lib.fasta_label_mapper import FASTALabelMapper
except ImportError:
    FASTALabelMapper = None

@click.command('map-labels')
@click.option('--fasta', required=True, type=click.Path(exists=True), 
              help='Arquivo FASTA com headers estruturados')
@click.option('--predictions', type=click.Path(exists=True), 
              help='Arquivo CSV de predições para adicionar labels')
@click.option('--output', help='Arquivo de saída (opcional)')
@click.option('--validate-only', is_flag=True, help='Apenas validar mapeamentos')
@click.option('--tree-file', default='src/nodes/tree.txt', help='Arquivo de hierarquia')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def map_labels(ctx, fasta, predictions, output, validate_only, tree_file, verbose):
    """Mapear headers FASTA para códigos hierárquicos"""
    
    if not FASTALabelMapper:
        click.echo("❌ FASTALabelMapper não disponível")
        sys.exit(1)
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    click.echo(f"🏷️  Mapeando labels de: {fasta}")
    
    try:
        mapper = FASTALabelMapper(tree_file=tree_file)
        
        if validate_only:
            mapper.validate_mapping(fasta)
        
        elif predictions:
            click.echo(f"📄 Adicionando labels a: {predictions}")
            mapper.add_actual_labels_to_predictions(predictions, fasta, output)
            
        else:
            output_file = output if output else f"{Path(fasta).stem}_mappings.csv"
            mappings_df = mapper.process_fasta_file(fasta, output_file)
            
            click.echo(f"\n📊 Resumo dos mapeamentos:")
            click.echo(f"   Total: {len(mappings_df)}")
            click.echo(f"   Sucessos: {mappings_df['mapping_success'].sum()}")
            click.echo(f"   Falhas: {(~mappings_df['mapping_success']).sum()}")
        
        click.echo("✅ Mapeamento concluído!")
        
    except Exception as e:
        click.echo(f"❌ Erro no mapeamento: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)