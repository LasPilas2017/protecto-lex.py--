"""Pruebas de TAC y máquina virtual para MI EXTENSIÓN PERSONAL (entrega final).

No modifica test_tac_vm.py del docente. Ejecutar con:
    python -m unittest pruebas.test_tac_vm_extension -v
"""
import unittest
from contextlib import redirect_stdout
from io import StringIO

from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.analizador import AnalizadorSemantico
from intermediate.tac import GeneradorTAC
from vm.maquina_virtual import MaquinaVirtual


def compilar(codigo):
    """Prepara un programa válido y lo convierte a instrucciones TAC."""
    arbol = Parser(Lexer(codigo).analizar()).parsear()
    AnalizadorSemantico().analizar(arbol)
    return GeneradorTAC().generar(arbol)


def correr(codigo, entradas=(), max_pasos=10000):
    """Compila y ejecuta; 'entradas' son las respuestas para 'leer'."""
    tac = compilar(codigo)
    respuestas = iter(entradas)
    vm = MaquinaVirtual(tac, entrada=lambda _mensaje: next(respuestas))
    with redirect_stdout(StringIO()):
        salidas = vm.ejecutar(max_pasos=max_pasos)
    return tac, vm, salidas


def ops(tac):
    """Extrae los nombres de operación para facilitar las comprobaciones."""
    return [i[0] for i in tac]


class TestTACExtension(unittest.TestCase):
    """Comprueba cómo las funciones añadidas se representan en el TAC."""
    def test_literales_en_tac(self):
        tac = compilar('decimal d = 3.14; cadena c = "hola"; booleano b = verdadero;')
        self.assertEqual(tac, [('ASSIGN', '3.14', None, 'd'),
                               ('ASSIGN', '"hola"', None, 'c'),
                               ('ASSIGN', '1', None, 'b')])

    def test_si_sino_usa_dos_etiquetas(self):
        tac = compilar('si (1 < 2) { imprimir(1); } sino { imprimir(2); }')
        self.assertEqual(ops(tac), ['<', 'JMP_FALSE', 'PRINT', 'JMP', 'LABEL', 'PRINT', 'LABEL'])

    def test_parar_y_continuar_son_saltos(self):
        tac = compilar('mientras (verdadero) { continuar; parar; }')
        inicio, fin = tac[0][3], tac[-1][3]
        self.assertIn(('JMP', None, None, inicio), tac)   # continuar
        self.assertIn(('JMP', None, None, fin), tac)      # parar

    def test_operadores_unarios(self):
        tac = compilar('booleano b = no falso; entero n = -5;')
        self.assertEqual(ops(tac), ['NO', 'ASSIGN', 'NEG', 'ASSIGN'])

    def test_leer_guarda_el_tipo(self):
        tac = compilar('decimal nota = 0; leer nota;')
        self.assertEqual(tac[-1], ('READ', 'decimal', None, 'nota'))

    def test_funcion_y_llamada(self):
        tac = compilar('funcion entero doble(entero n) { retornar n * 2; } entero r = doble(4);')
        self.assertEqual(ops(tac), ['JMP', 'LABEL', 'GET_PARAM', '*', 'RETURN', 'RETURN',
                                    'LABEL', 'PARAM', 'CALL', 'ASSIGN'])
        self.assertEqual(tac[1], ('LABEL', None, None, '@F_doble'))

    def test_comentarios_no_generan_tac(self):
        self.assertEqual(compilar('// nada\nentero x = 1; /* nada */'),
                         [('ASSIGN', '1', None, 'x')])


class TestVMExtension(unittest.TestCase):
    """Revisa los resultados al ejecutar las funciones nuevas del lenguaje."""
    def test_decimales(self):
        _t, vm, salidas = correr('decimal d = 7.5 / 2; decimal e = 1 + 2.5; imprimir(d); imprimir(e);')
        self.assertEqual(salidas, [3.75, 3.5])

    def test_entero_entre_entero_sigue_siendo_division_entera(self):
        self.assertEqual(correr('imprimir(7 / 2); imprimir(7.0 / 2);')[2], [3, 3.5])

    def test_entero_guardado_en_decimal(self):
        _t, vm, _s = correr('decimal d = 5;')
        self.assertEqual(vm.memoria['d'], 5)

    def test_cadenas(self):
        _t, _vm, salidas = correr('cadena s = "Hola " + "Ana"; imprimir(s); imprimir(s == "Hola Ana");')
        self.assertEqual(salidas, ['Hola Ana', 1])

    def test_logicos(self):
        _t, _vm, salidas = correr('entero x = 5; imprimir(x > 1 y no (x == 3)); '
                                  'imprimir(falso o falso); imprimir(verdadero o falso);')
        self.assertEqual(salidas, [1, 0, 1])

    def test_menos_unario(self):
        self.assertEqual(correr('entero x = 4; imprimir(-x + 1);')[2], [-3])

    def test_sino_si(self):
        codigo = ('entero n = {}; si (n >= 61) {{ imprimir("A"); }} '
                  'sino si (n >= 50) {{ imprimir("R"); }} sino {{ imprimir("F"); }}')
        self.assertEqual(correr(codigo.format(80))[2], ['A'])
        self.assertEqual(correr(codigo.format(55))[2], ['R'])
        self.assertEqual(correr(codigo.format(10))[2], ['F'])

    def test_parar_y_continuar(self):
        _t, vm, salidas = correr('entero i = 0; mientras (verdadero) { i = i + 1; '
                                 'si (i == 2) { continuar; } si (i > 4) { parar; } imprimir(i); }')
        self.assertEqual(salidas, [1, 3, 4])
        self.assertEqual(vm.memoria['i'], 5)

    def test_leer_convierte_al_tipo(self):
        _t, vm, salidas = correr('decimal nota = 0; leer nota; imprimir(nota * 2);', ['43.5'])
        self.assertEqual(salidas, [87.0])
        _t, vm, _s = correr('booleano b = falso; leer b;', ['verdadero'])
        self.assertEqual(vm.memoria['b'], 1)
        _t, vm, _s = correr('cadena c = ""; leer c;', ['Celso'])
        self.assertEqual(vm.memoria['c'], 'Celso')

    def test_funcion_simple(self):
        self.assertEqual(correr('funcion entero doble(entero n) { retornar n * 2; } '
                                'imprimir(doble(21));')[2], [42])

    def test_funcion_con_varios_parametros(self):
        self.assertEqual(correr('funcion decimal prom(decimal a, decimal b) { retornar (a + b) / 2.0; } '
                                'imprimir(prom(80, 95.5));')[2], [87.75])

    def test_recursion(self):
        codigo = ('funcion entero fact(entero n) { si (n <= 1) { retornar 1; } '
                  'retornar n * fact(n - 1); } imprimir(fact(5));')
        self.assertEqual(correr(codigo)[2], [120])

    def test_parametro_no_cambia_la_global(self):
        _t, vm, salidas = correr('entero n = 100; funcion entero f(entero n) { retornar n + 1; } '
                                 'imprimir(f(1)); imprimir(n);')
        self.assertEqual(salidas, [2, 100])

    def test_funcion_puede_cambiar_una_global(self):
        _t, vm, _s = correr('entero total = 0; funcion entero sumar(entero v) '
                            '{ total = total + v; retornar total; } entero r = sumar(5); r = sumar(2);')
        self.assertEqual(vm.memoria['total'], 7)

    def test_llamada_dentro_de_argumento(self):
        codigo = ('funcion entero doble(entero n) { retornar n * 2; } '
                  'funcion entero suma(entero a, entero b) { retornar a + b; } '
                  'imprimir(suma(doble(3), doble(4)));')
        self.assertEqual(correr(codigo)[2], [14])

    def test_programa_de_demostracion(self):
        with open('pruebas/40_final_extension.txt', encoding='utf-8') as f:
            _t, _vm, salidas = correr(f.read())
        self.assertEqual(salidas, ['Hola Ana', 1, 3, 4, 'Aprobado', 1, 87.75, 120, 3, 3.5])


class TestErroresEjecucionExtension(unittest.TestCase):
    """Comprueba errores que solo aparecen cuando el programa está corriendo."""
    def test_division_cero_con_z(self):
        # Equivalente a pruebas/19 del docente, con 'z' porque 'y' es reservada.
        with self.assertRaises(ZeroDivisionError):
            correr('entero x = 10; entero z = 0; imprimir(x / z);')

    def test_division_cero_decimal(self):
        with self.assertRaises(ZeroDivisionError):
            correr('decimal a = 5.0; decimal b = 0.0; imprimir(a / b);')

    def test_leer_tipo_incorrecto(self):
        with self.assertRaises(ValueError):
            correr('entero edad = 0; leer edad;', ['veinte'])
        with self.assertRaises(ValueError):
            correr('booleano b = falso; leer b;', ['si'])

    def test_recursion_sin_caso_base(self):
        with self.assertRaises(RuntimeError):
            correr('funcion entero f(entero n) { retornar f(n + 1); } imprimir(f(1));',
                   max_pasos=1000000)

    def test_funcion_sin_retornar(self):
        with self.assertRaises(RuntimeError):
            correr('funcion entero f(entero n) { si (n > 5) { retornar 1; } } imprimir(f(1));')

    def test_limite_de_pasos_con_mientras_verdadero(self):
        with self.assertRaises(RuntimeError):
            correr('mientras (verdadero) { imprimir(1); }', max_pasos=30)

    def test_error_semantico_de_extension_bloquea_tac(self):
        with self.assertRaises(ValueError):
            compilar('parar;')


if __name__ == '__main__':
    unittest.main()
