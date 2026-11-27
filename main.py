
"""
==========================================================================
 MAIN.PY: PUNTO DE ENTRADA DEL COMPILADOR
==========================================================================
 Autor: Celso Otoniel Hernández - Carné 2400455

 Une las cinco fases en orden:

   código fuente (.txt)
        |
        v
   FASE 1: Lexer  (lexer/lexer.py)    -> lista de tokens
        |
        v
   FASE 2: Parser (parser/parser.py)  -> AST (arbol_ast/nodos.py)
        |
        v
   FASE 3: Semántica (semantic/analizador.py) -> tabla de símbolos
        |
        v
   FASE 4: TAC (intermediate/tac.py)  -> instrucciones de tres direcciones
        |
        v
   FASE 5: Máquina virtual (vm/maquina_virtual.py) -> ejecuta y muestra salidas

 Uso:  python main.py pruebas/40_final_extension.txt
       python main.py --solo-lexer     archivo.txt   (Fase 1)
       python main.py --solo-parser    archivo.txt   (Fases 1-2)
       python main.py --solo-semantica archivo.txt   (Fases 1-3)
       python main.py --solo-tac       archivo.txt   (Fases 1-4)
       python main.py archivo.txt --limite-pasos 50
==========================================================================
"""
import argparse
from pathlib import Path
from lexer.lexer import Lexer          # FASE 1: mi analizador léxico
from parser.parser import Parser       # FASE 2: mi analizador sintáctico
from semantic.analizador import AnalizadorSemantico  # FASE 3: mi analizador semántico
from intermediate.tac import GeneradorTAC          # FASE 4: código intermedio
from vm.maquina_virtual import MaquinaVirtual     # FASE 5: máquina virtual
from arbol_ast.imprimir_arbol import arbol_texto  # dibuja el AST en consola

BASE_DIR = Path(__file__).resolve().parent
MOSTRAR_REPR = False


def analizar_lexico(codigo):
    """Muestra los tokens que se encontraron y los devuelve para la fase siguiente."""
    print('\n=== FASE 1 - ANALISIS LEXICO (lexer/lexer.py) ===')
    tokens = Lexer(codigo).analizar()
    for token in tokens:
        print(' ', token)
    return tokens


def analizar_sintactico(tokens):
    """Construye el árbol del programa y lo presenta de forma legible."""
    print('\n=== FASE 2 - ANALISIS SINTACTICO (parser/parser.py) ===')
    arbol = Parser(tokens).parsear()
    print('Analisis sintactico correcto. AST generado:\n')
    print(arbol_texto(arbol))
    if MOSTRAR_REPR:
        print('\nAST (representacion de Python):')
        print(arbol)
    return arbol


def imprimir_tabla_simbolos(semantico):
    """Muestra la tabla de símbolos como tabla de texto."""
    filas = [(nombre, 'variable', tipo) for nombre, tipo in semantico.tabla_simbolos.items()]
    for nombre, (retorno, params) in semantico.tabla_funciones.items():
        firma = f"{retorno} ({', '.join(params) or 'sin parametros'})"
        filas.append((nombre, 'funcion', firma))
    if not filas:
        print('  (vacia)')
        return
    ancho = [max(len(f[i]) for f in filas + [('Nombre', 'Categoria', 'Tipo')]) for i in range(3)]
    linea = '  +' + '+'.join('-' * (a + 2) for a in ancho) + '+'
    fmt = '  | ' + ' | '.join('{:<' + str(a) + '}' for a in ancho) + ' |'
    print(linea)
    print(fmt.format('Nombre', 'Categoria', 'Tipo'))
    print(linea)
    for f in filas:
        print(fmt.format(*f))
    print(linea)


def analizar_semantica(arbol):
    """Comprueba el significado del programa y enseña los nombres registrados."""
    print('\n=== FASE 3 - ANALISIS SEMANTICO (semantic/analizador.py) ===')
    semantico = AnalizadorSemantico()
    semantico.analizar(arbol)
    print('Analisis semantico correcto.')
    print('Tabla de simbolos:', semantico.tabla_simbolos)
    if semantico.tabla_funciones:
        print('Tabla de funciones:', semantico.tabla_funciones)
    print()
    imprimir_tabla_simbolos(semantico)
    return semantico


def generar_tac(arbol):
    """Convierte el árbol en instrucciones intermedias y las muestra."""
    print('\n=== FASE 4 - CODIGO INTERMEDIO TAC (intermediate/tac.py) ===')
    tac = GeneradorTAC().generar(arbol)
    print(f"{'#':>3} | {'op':<10} | {'arg1':<12} | {'arg2':<8} | res")
    print('-' * 52)
    for i, (op, arg1, arg2, res) in enumerate(tac):
        print(f'{i:03d} | {op:<10} | {str(arg1):<12} | {str(arg2):<8} | {str(res)}')
    return tac


def ejecutar_vm(tac, limite_pasos):
    """Ejecuta las instrucciones y presenta el estado final de la máquina."""
    print('\n=== FASE 5 - MAQUINA VIRTUAL (vm/maquina_virtual.py) ===')
    vm = MaquinaVirtual(tac)
    salidas = vm.ejecutar(max_pasos=limite_pasos)
    print('\nMemoria final:', {k: v for k, v in vm.memoria.items() if not k.startswith('@')})
    print('Salidas:', salidas)
    return vm


def main():
    """Lee las opciones, ejecuta las fases elegidas y comunica cualquier error."""
    argumentos = argparse.ArgumentParser(description='Compilador incremental completo')
    argumentos.add_argument('archivo', nargs='?', default='pruebas/01_basico_valido.txt')
    fases = argumentos.add_mutually_exclusive_group()
    fases.add_argument('--solo-lexer', action='store_true', help='Detener despues de la Fase 1.')
    fases.add_argument('--solo-parser', action='store_true', help='Detener despues de la Fase 2.')
    fases.add_argument('--solo-semantica', action='store_true', help='Detener despues de la Fase 3.')
    fases.add_argument('--solo-tac', action='store_true', help='Detener despues de la Fase 4.')
    argumentos.add_argument('--limite-pasos', type=int, default=10000,
                            help='Maximo de instrucciones de la VM (por defecto 10000).')
    argumentos.add_argument('--repr', action='store_true',
                            help='Ademas del arbol, imprime el AST con repr()')
    opciones = argumentos.parse_args()
    global MOSTRAR_REPR
    MOSTRAR_REPR = opciones.repr
    ruta = Path(opciones.archivo)
    if not ruta.is_absolute() and not ruta.exists():
        ruta = BASE_DIR / ruta
    try:
        codigo = ruta.read_text(encoding='utf-8')
    except OSError as error:
        print(f'No se pudo abrir el archivo: {error}')
        return 1
    print('=== MI COMPILADOR - ENTREGA FINAL (5 FASES) ===')
    print('\nCODIGO FUENTE:')
    print(codigo)
    try:
        tokens = analizar_lexico(codigo)
        if opciones.solo_lexer:
            print('\nEjecucion detenida despues del lexer.')
            return 0
        arbol = analizar_sintactico(tokens)
        if opciones.solo_parser:
            print('\nEjecucion detenida despues del parser.')
            return 0
        analizar_semantica(arbol)
        if opciones.solo_semantica:
            print('\nEjecucion detenida despues de la semantica.')
            return 0
        tac = generar_tac(arbol)
        if opciones.solo_tac:
            print('\nEjecucion detenida despues del TAC.')
            return 0
        ejecutar_vm(tac, opciones.limite_pasos)
        print('\nCompilacion y ejecucion completadas.')
        return 0
    except NotImplementedError as error:
        print(f'\n[IMPLEMENTACION PENDIENTE] {error}')
        return 2
    except (RuntimeError, SyntaxError, ValueError, NameError, TypeError,
            ZeroDivisionError) as error:
        print(f'\n{error}')
        return 1
    except EOFError:
        print("\n[Error VM] 'leer' no recibio ningun dato (entrada cerrada).")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
