"""
==========================================================================
 FASE 5 DEL COMPILADOR: MÁQUINA VIRTUAL
==========================================================================
 Base: máquina virtual educativa del docente (sus 4 TODO vienen resueltos).
 Ampliada por: Celso Otoniel Hernández - Carné 2400455

 ¿QUÉ HACE ESTE ARCHIVO?
   EJECUTA las instrucciones TAC una por una, como un procesador:
     - self.tac       la lista de instrucciones (el "programa")
     - self.ip        el número de la instrucción que toca ejecutar
     - self.memoria   el valor de cada variable y temporal
     - self.etiquetas dónde está cada LABEL, para poder saltar
   El ciclo de ejecutar() es: leer instrucción -> ejecutarla -> avanzar
   (o saltar a una etiqueta con JMP / JMP_FALSE).

 VALORES (base del docente + [EXTENSIÓN])
   enteros, comparaciones como 1/0                      (base)
   decimales (float), cadenas (str), booleanos como 1/0 [EXTENSIÓN]

 INSTRUCCIONES NUEVAS DE MI EXTENSIÓN
   y, o                  operadores lógicos
   NO, NEG               'no' y menos unario
   READ                  'leer': pide un dato por teclado
   PARAM, CALL,          funciones: argumentos, llamada,
   GET_PARAM, RETURN     lectura de parámetros y retorno

 ERRORES DE EJECUCIÓN (solo se pueden detectar al correr el programa)
   ZeroDivisionError  división entre cero
   RuntimeError       límite de pasos (ciclo infinito), demasiadas
                      llamadas anidadas, función sin retornar valor
   ValueError         'leer' recibe un dato que no es del tipo esperado
==========================================================================
"""
import re
from typing import Any, Callable, Dict, List, Optional
from intermediate.tac import Instruccion

OPERADORES = {'+', '-', '*', '/', '==', '!=', '<', '>', '<=', '>=',
              'y', 'o'}                                   # [EXTENSIÓN] y, o
UNARIOS = {'NO', 'NEG'}                                   # [EXTENSIÓN]

ENTERO = re.compile(r'-?\d+$')
DECIMAL = re.compile(r'-?\d+\.\d+$')                      # [EXTENSIÓN]
LIMITE_LLAMADAS = 500                                     # [EXTENSIÓN]


class MaquinaVirtual:
    def __init__(self, tac: List[Instruccion],
                 entrada: Optional[Callable[[str], str]] = None):
        self.tac = list(tac)
        self.memoria: Dict[str, Any] = {}
        self.ip = 0
        self.salidas: List[Any] = []
        self.etiquetas: Dict[str, int] = {}
        # [EXTENSIÓN] De dónde lee 'leer' (por defecto, el teclado).
        # Las pruebas pasan aquí una función con respuestas fijas.
        self.entrada = entrada or input
        # [EXTENSIÓN] Funciones: argumentos pendientes y pila de llamadas.
        self.params_pendientes: List[Any] = []
        self.pila_llamadas: List[Dict[str, Any]] = []
        for i, (op, _a1, _a2, res) in enumerate(self.tac):
            if op == 'LABEL':
                if not res or res in self.etiquetas:
                    raise ValueError(f'[Error VM] Etiqueta repetida o vacia: {res!r}')
                self.etiquetas[res] = i

    # ------------------------------------------------------------------
    # Lectura y escritura de valores
    # ------------------------------------------------------------------
    def obtener_val(self, arg: Optional[str]) -> Any:
        """Lee una constante o una variable/temporal que ya tenga valor."""
        if arg is None:
            raise ValueError('[Error VM] Falta operando obligatorio.')
        if ENTERO.match(arg):
            return int(arg)
        if DECIMAL.match(arg):                          # [EXTENSIÓN] 3.14
            return float(arg)
        if len(arg) >= 2 and arg[0] == arg[-1] == '"':  # [EXTENSIÓN] "texto"
            return arg[1:-1]
        # [EXTENSIÓN] Dentro de una función se busca primero en sus
        # variables locales (parámetros, temporales) y luego en las globales.
        if self.pila_llamadas and arg in self.pila_llamadas[-1]['locales']:
            return self.pila_llamadas[-1]['locales'][arg]
        if arg not in self.memoria:
            raise NameError(f"[Error VM] Variable/temporal '{arg}' sin valor.")
        return self.memoria[arg]

    def guardar(self, destino: str, valor: Any) -> None:
        """[EXTENSIÓN] Guarda un valor respetando las variables locales.

        Fuera de una función todo va a la memoria global (igual que la base).
        Dentro de una función: si es una variable global que ya existe se
        actualiza esa; si no (parámetros, temporales, variables nuevas),
        queda local a esa llamada. Así la recursión no mezcla valores.
        """
        if self.pila_llamadas:
            locales = self.pila_llamadas[-1]['locales']
            if destino in locales or destino not in self.memoria:
                locales[destino] = valor
                return
        self.memoria[destino] = valor

    # EJEMPLO RESUELTO (docente): instruccion de asignacion.
    def instruccion_asignar(self, fuente: Optional[str], destino: Optional[str]):
        if not destino:
            raise ValueError('[Error VM] ASSIGN sin destino.')
        self.guardar(destino, self.obtener_val(fuente))

    # ------------------------------------------------------------------
    # Ciclo principal
    # ------------------------------------------------------------------
    def ejecutar(self, max_pasos: int = 10000) -> List[Any]:
        if max_pasos < 1:
            raise ValueError('max_pasos debe ser al menos 1.')
        pasos = 0
        while 0 <= self.ip < len(self.tac):
            if pasos >= max_pasos:
                raise RuntimeError(
                    f'[Limite de ejecucion] Se superaron {max_pasos} pasos. '
                    'Revisa la condicion de while o incrementa el limite.'
                )
            op, arg1, arg2, res = self.tac[self.ip]
            pasos += 1
            if op == 'ASSIGN':
                self.instruccion_asignar(arg1, res)
            elif op in OPERADORES:
                self.instruccion_operacion(op, arg1, arg2, res)
            elif op == 'PRINT':
                self.instruccion_imprimir(arg1)
            elif op == 'JMP':
                self.instruccion_salto(res)
            elif op == 'JMP_FALSE':
                self.instruccion_salto_condicional(arg1, res)
            elif op == 'LABEL':
                pass  # Las etiquetas marcan posiciones, no realizan operaciones.
            # ---------- [EXTENSIÓN] ----------
            elif op in UNARIOS:
                self.instruccion_unaria(op, arg1, res)
            elif op == 'READ':
                self.instruccion_leer(arg1, res)
            elif op == 'PARAM':
                self.params_pendientes.append(self.obtener_val(arg1))
            elif op == 'CALL':
                self.instruccion_llamar(arg1, arg2, res)
            elif op == 'GET_PARAM':
                # El parámetro SIEMPRE es local, aunque exista una global igual.
                llamada = self.pila_llamadas[-1]
                llamada['locales'][res] = llamada['argumentos'][int(arg1)]
            elif op == 'RETURN':
                self.instruccion_retornar(arg1)
            else:
                raise NotImplementedError(
                    f"[Error VM] Instruccion '{op}' no soportada. "
                    'Agrega tu extension a OPERADORES o a ejecutar().'
                )
            # Los saltos ubican ip en la etiqueta y este incremento entra en
            # la instruccion inmediatamente posterior a LABEL.
            self.ip += 1
        return self.salidas

    def _ubicacion_etiqueta(self, etiqueta: Optional[str]) -> int:
        if etiqueta not in self.etiquetas:
            raise ValueError(f"[Error VM] Etiqueta de salto desconocida: {etiqueta!r}")
        return self.etiquetas[etiqueta]

    # ------------------------------------------------------------------
    # Los 4 métodos del docente (ampliados donde dice [EXTENSIÓN])
    # ------------------------------------------------------------------
    def instruccion_operacion(self, op: str, arg1: Optional[str],
                             arg2: Optional[str], res: Optional[str]) -> None:
        if not res:
            raise ValueError('[Error VM] Operacion sin destino.')
        a = self.obtener_val(arg1)
        b = self.obtener_val(arg2)
        if op == '+': valor = a + b          # con dos cadenas, las une [EXTENSIÓN]
        elif op == '-': valor = a - b
        elif op == '*': valor = a * b
        elif op == '/':
            if b == 0:
                raise ZeroDivisionError('[Error VM] Division entre cero.')
            # Base: entero / entero = división entera (10 / 3 = 3).
            # [EXTENSIÓN] si hay un decimal, división normal (7.5 / 2 = 3.75).
            valor = a // b if isinstance(a, int) and isinstance(b, int) else a / b
        elif op == '==': valor = int(a == b)
        elif op == '!=': valor = int(a != b)
        elif op == '<': valor = int(a < b)
        elif op == '>': valor = int(a > b)
        elif op == '<=': valor = int(a <= b)
        elif op == '>=': valor = int(a >= b)
        # [EXTENSIÓN] Evaluación directa (sin cortocircuito): los dos lados
        # ya fueron calculados antes de llegar aquí.
        elif op == 'y': valor = int(bool(a) and bool(b))
        elif op == 'o': valor = int(bool(a) or bool(b))
        else: raise NotImplementedError(f'[Error VM] Operador {op} sin ejecucion.')
        self.guardar(res, valor)

    def instruccion_imprimir(self, fuente: Optional[str]) -> None:
        valor = self.obtener_val(fuente)
        self.salidas.append(valor)
        print(f'>> SALIDA: {valor}')

    def instruccion_salto(self, etiqueta: Optional[str]) -> None:
        self.ip = self._ubicacion_etiqueta(etiqueta)

    def instruccion_salto_condicional(self, condicion: Optional[str],
                                     etiqueta: Optional[str]) -> None:
        if self.obtener_val(condicion) == 0:
            self.ip = self._ubicacion_etiqueta(etiqueta)

    # ==================================================================
    # [EXTENSIÓN PERSONAL] Instrucciones nuevas
    # ==================================================================
    def instruccion_unaria(self, op: str, arg: Optional[str], res: Optional[str]) -> None:
        valor = self.obtener_val(arg)
        self.guardar(res, int(not valor) if op == 'NO' else -valor)

    def instruccion_leer(self, tipo: Optional[str], destino: Optional[str]) -> None:
        """'leer x;' pide el dato y lo convierte al tipo de la variable."""
        texto = self.entrada(f'<< ENTRADA ({destino}, {tipo}): ').strip()
        try:
            if tipo == 'entero':
                valor = int(texto)
            elif tipo == 'decimal':
                valor = float(texto)
            elif tipo == 'booleano':
                if texto not in ('verdadero', 'falso'):
                    raise ValueError
                valor = int(texto == 'verdadero')
            else:
                valor = texto
        except ValueError:
            raise ValueError(
                f"[Error VM] 'leer {destino}' esperaba un valor {tipo} "
                f"y recibio '{texto}'."
            ) from None
        self.guardar(destino, valor)

    def instruccion_llamar(self, nombre: Optional[str], cantidad: Optional[str],
                           destino: Optional[str]) -> None:
        """CALL: toma los argumentos, guarda a dónde volver y salta a la función."""
        if len(self.pila_llamadas) >= LIMITE_LLAMADAS:
            raise RuntimeError(
                f'[Error VM] Mas de {LIMITE_LLAMADAS} llamadas anidadas: '
                'revisa si la recursion tiene un caso base.'
            )
        n = int(cantidad)
        argumentos = self.params_pendientes[len(self.params_pendientes) - n:] if n else []
        del self.params_pendientes[len(self.params_pendientes) - n:]
        self.pila_llamadas.append({
            'funcion': nombre,
            'volver_a': self.ip,      # al terminar, sigue después del CALL
            'destino': destino,       # dónde guardar el resultado
            'argumentos': argumentos,
            'locales': {},
        })
        self.ip = self._ubicacion_etiqueta(f'@F_{nombre}')

    def instruccion_retornar(self, fuente: Optional[str]) -> None:
        """RETURN: calcula el valor, cierra la llamada y vuelve a quien llamó."""
        if not self.pila_llamadas:
            raise RuntimeError('[Error VM] RETURN fuera de una funcion.')
        if fuente is None:
            raise RuntimeError(
                f"[Error VM] La funcion '{self.pila_llamadas[-1]['funcion']}' "
                'termino sin retornar un valor.'
            )
        valor = self.obtener_val(fuente)
        llamada = self.pila_llamadas.pop()
        self.ip = llamada['volver_a']
        self.guardar(llamada['destino'], valor)
