"""
Wrapper de Compatibilidade para Inpactor2.

Executa o código original do Inpactor2 em ambientes modernos 
sem modificar o arquivo fonte.

Funcionalidades do Wrapper:
1. Monkey Patching: Intercepta `tf.keras.models.load_model` para forçar `compile=False`,
   evitando erros de desserialização do otimizador (ExponentialDecay) no TF 2.8+.
2. Contexto de Arquivo: Simula a variável `__file__` e ajusta o diretório de trabalho
   para que o script encontre seus pesos e datasets relativos corretamente.
3. Multiprocessing: Executa o script no namespace `globals()` para garantir que 
   funções internas sejam serializáveis (pickle) durante o processamento paralelo.
"""

import sys
import os
import tensorflow as tf
from pathlib import Path


_original_load_model = tf.keras.models.load_model

def _patched_load_model(*args, **kwargs):
   
    if 'compile' not in kwargs:
        kwargs['compile'] = False
    return _original_load_model(*args, **kwargs)

tf.keras.models.load_model = _patched_load_model


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python inpactor_wrapper.py <caminho_inpactor2.py> [argumentos...]")
        sys.exit(1)

    real_script_path = str(Path(sys.argv[1]).resolve())
    sys.argv.pop(0) 
    script_dir = os.path.dirname(real_script_path)
    
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

     
    os.chdir(script_dir)

    print(f"🔧 [WRAPPER] Executando {real_script_path}")
    print(f"🔧 [WRAPPER] CWD ajustado para: {os.getcwd()}")

    
    try:
        with open(real_script_path, 'r') as f:
            code = compile(f.read(), real_script_path, 'exec')
            global_namespace = globals()
            global_namespace['__file__'] = real_script_path
            global_namespace['__name__'] = '__main__'
            exec(code, global_namespace)
            
    except Exception as e:
        if isinstance(e, SystemExit):
            raise
        print(f"❌ [WRAPPER] Erro ao executar o script original: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)