"""
==========================================================================
 FASE 4 DEL COMPILADOR: GENERADOR DE CÓDIGO INTERMEDIO (TAC)
==========================================================================
 Autor: Celso Otoniel Hernández - Carné 2400455
 Curso: Compiladores - USPG

 ¿QUÉ HACE ESTE ARCHIVO?
   Recorre el AST (ya validado por la semántica) y lo traduce a
   instrucciones de TRES DIRECCIONES: cada instrucción hace UNA sola
   operación con a lo más dos operandos y un destino.

   Formato:  (operacion, argumento1, argumento2, destino)

   Ejemplo:  entero x = 5 + 3 * 2;
     ('*', '3', '2', '@t1')        @t1 = 3 * 2
     ('+', '5', '@t1', '@t2')      @t2 = 5 + @t1
     ('ASSIGN', '@t2', None, 'x')  x = @t2

 NOMBRES INTERNOS
   Temporales: @t1, @t2, ...   Etiquetas: @L1, @L2, ...
   Empiezan con @ para que nunca choquen con una variable del programa.

 ¿QUÉ ES MÍO?
   - TODO 1 a 5 del docente (Asignacion, Imprimir, Si, Mientras, evaluar_expr).
   - Las instrucciones de mi EXTENSIÓN PERSONAL, marcadas con [EXTENSIÓN].

 CÓMO SE ESCRIBEN LOS LITERALES EN EL TAC
   entero   -> '5'          decimal -> '3.14'
   cadena   -> '"hola"'     (con comillas, así la VM sabe que es texto)
   booleano -> '1' o '0'    (igual que las comparaciones del docente)
==========================================================================
"""
from typing import Dict, List, Optional, Tuple
from arbol_ast.nodos import (
    NodoAST, Programa, Declaracion, Asignacion, Numero, Identificador,
    OpBinaria, Imprimir, Si, Mientras,
    # Nodos de mi extensión personal
    Decimal, Cadena, Booleano, OpUnaria, Leer, Parar, Continuar,
    Funcion, Retornar, LlamadaFuncion,
)

Instruccion = Tuple[str, Optional[str], Optional[str], Optional[str]]


class GeneradorTAC:
    def __init__(self):
        self.instrucciones: List[Instruccion] = []
        self.conteo_temp = 0
        self.conteo_etiquetas = 0
        # [EXTENSIÓN] Pila de ciclos abiertos: (etiqueta_inicio, etiqueta_fin).
        # 'parar' salta al fin del ciclo más cercano; 'continuar', al inicio.
        self.ciclos: List[Tuple[str, str]] = []
        # [EXTENSIÓN] Tipo de cada variable, para que 'leer' sepa cómo
        # convertir lo que escribe el usuario.
        self.tipos: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Infraestructura (YA IMPLEMENTADA por el docente)
    # ------------------------------------------------------------------
    def nuevo_temp(self) -> str:
        self.conteo_temp += 1
        return f'@t{self.conteo_temp}'

    def nueva_etiqueta(self) -> str:
        self.conteo_etiquetas += 1
        return f'@L{self.conteo_etiquetas}'

    def emitir(self, op: str, arg1: Optional[str] = None,
               arg2: Optional[str] = None, res: Optional[str] = None) -> None:
        self.instrucciones.append((op, arg1, arg2, res))

    def generar(self, nodo: NodoAST) -> List[Instruccion]:
        """Visita un nodo y acumula instrucciones; devolver no implica reiniciar."""
        metodo = f'generar_{type(nodo).__name__}'
        visitante = getattr(self, metodo, self.error_generico)
        visitante(nodo)
        return self.instrucciones

    def error_generico(self, nodo: NodoAST):
        raise NotImplementedError(
            f'No existe generacion TAC para {type(nodo).__name__}. '
            'Adapta tu extension personal.'
        )

    def generar_Programa(self, nodo: Programa) -> None:
        for sentencia in nodo.sentencias:
            self.generar(sentencia)

    # EJEMPLO RESUELTO DEL DOCENTE (yo solo agregué el registro del tipo).
    def generar_Declaracion(self, nodo: Declaracion) -> None:
        fuente = self.evaluar_expr(nodo.expr)
        self.emitir('ASSIGN', fuente, None, nodo.id)
        self.tipos[nodo.id] = nodo.tipo   # [EXTENSIÓN] para 'leer'

    # ------------------------------------------------------------------
    # Auxiliar propio
    # ------------------------------------------------------------------
    def generar_bloque(self, sentencias: List[NodoAST]) -> None:
        for sentencia in sentencias:
            self.generar(sentencia)

    # ==================================================================
    # TODO TAC 1 - ASIGNACIÓN
    #   x = expr;   ->   (calcular expr) + ('ASSIGN', fuente, None, 'x')
    # ==================================================================
    def generar_Asignacion(self, nodo: Asignacion) -> None:
        fuente = self.evaluar_expr(nodo.expr)
        self.emitir('ASSIGN', fuente, None, nodo.id)

    # ==================================================================
    # TODO TAC 2 - IMPRIMIR
    #   imprimir(expr);   ->   (calcular expr) + ('PRINT', fuente, None, None)
    # ==================================================================
    def generar_Imprimir(self, nodo: Imprimir) -> None:
        fuente = self.evaluar_expr(nodo.expr)
        self.emitir('PRINT', fuente, None, None)

    # ==================================================================
    # TODO TAC 3 - SI  (con la rama 'sino' de mi extensión)
    #
    #   Sin sino:                    Con sino [EXTENSIÓN]:
    #     cond                         cond
    #     JMP_FALSE cond -> FIN        JMP_FALSE cond -> SINO
    #     bloque verdadero             bloque verdadero
    #     LABEL FIN                    JMP -> FIN
    #                                  LABEL SINO
    #                                  bloque sino
    #                                  LABEL FIN
    # ==================================================================
    def generar_Si(self, nodo: Si) -> None:
        condicion = self.evaluar_expr(nodo.condicion)
        if nodo.bloque_f is None:
            fin = self.nueva_etiqueta()
            self.emitir('JMP_FALSE', condicion, None, fin)
            self.generar_bloque(nodo.bloque_v)
            self.emitir('LABEL', None, None, fin)
            return
        # [EXTENSIÓN] 'sino': si la condición es falsa se salta a la rama
        # sino; si era verdadera, al terminar se salta sobre ella.
        # Un 'sino si' es simplemente otro Si dentro de bloque_f.
        etiqueta_sino = self.nueva_etiqueta()
        fin = self.nueva_etiqueta()
        self.emitir('JMP_FALSE', condicion, None, etiqueta_sino)
        self.generar_bloque(nodo.bloque_v)
        self.emitir('JMP', None, None, fin)
        self.emitir('LABEL', None, None, etiqueta_sino)
        self.generar_bloque(nodo.bloque_f)
        self.emitir('LABEL', None, None, fin)

    # ==================================================================
    # TODO TAC 4 - MIENTRAS
    #     LABEL INICIO
    #     cond                 <- se recalcula en CADA vuelta
    #     JMP_FALSE cond -> FIN
    #     bloque
    #     JMP -> INICIO
    #     LABEL FIN
    # ==================================================================
    def generar_Mientras(self, nodo: Mientras) -> None:
        inicio = self.nueva_etiqueta()
        fin = self.nueva_etiqueta()
        self.emitir('LABEL', None, None, inicio)
        condicion = self.evaluar_expr(nodo.condicion)
        self.emitir('JMP_FALSE', condicion, None, fin)
        self.ciclos.append((inicio, fin))       # [EXTENSIÓN] parar/continuar
        try:
            self.generar_bloque(nodo.bloque)
        finally:
            self.ciclos.pop()
        self.emitir('JMP', None, None, inicio)
        self.emitir('LABEL', None, None, fin)

    # ==================================================================
    # TODO TAC 5 - EVALUAR EXPRESIÓN
    #   Devuelve DÓNDE quedó el resultado: un literal, una variable o un
    #   temporal nuevo. Las subexpresiones se emiten primero (recursión),
    #   por eso en 5 + 3 * 2 el '*' sale antes que el '+'.
    # ==================================================================
    def evaluar_expr(self, nodo: NodoAST) -> str:
        if isinstance(nodo, Numero):
            return str(nodo.valor)
        if isinstance(nodo, Identificador):
            return nodo.nombre
        if isinstance(nodo, OpBinaria):
            izq = self.evaluar_expr(nodo.izq)
            der = self.evaluar_expr(nodo.der)
            temp = self.nuevo_temp()
            self.emitir(nodo.op, izq, der, temp)
            return temp

        # ---------- [EXTENSIÓN] literales nuevos ----------
        if isinstance(nodo, Decimal):
            texto = repr(nodo.valor)            # '3.14'
            return texto if 'e' not in texto else format(nodo.valor, 'f')
        if isinstance(nodo, Cadena):
            return f'"{nodo.valor}"'            # '"hola"'
        if isinstance(nodo, Booleano):
            return '1' if nodo.valor else '0'

        # ---------- [EXTENSIÓN] operadores de un solo valor ----------
        if isinstance(nodo, OpUnaria):
            valor = self.evaluar_expr(nodo.expr)
            temp = self.nuevo_temp()
            self.emitir('NO' if nodo.op == 'no' else 'NEG', valor, None, temp)
            return temp

        # ---------- [EXTENSIÓN] llamada a función como expresión ----------
        if isinstance(nodo, LlamadaFuncion):
            return self.emitir_llamada(nodo)

        raise NotImplementedError(
            f'No existe evaluacion TAC para la expresion {type(nodo).__name__}.'
        )

    # ==================================================================
    # [EXTENSIÓN PERSONAL] leer, parar, continuar
    # ==================================================================
    def generar_Leer(self, nodo: Leer) -> None:
        # ('READ', tipo, None, variable): la VM pide el dato por teclado y
        # lo convierte al tipo de la variable.
        self.emitir('READ', self.tipos.get(nodo.id, 'cadena'), None, nodo.id)

    def generar_Parar(self, nodo: Parar) -> None:
        # 'parar' = salto al final del ciclo más cercano.
        _inicio, fin = self.ciclos[-1]
        self.emitir('JMP', None, None, fin)

    def generar_Continuar(self, nodo: Continuar) -> None:
        # 'continuar' = salto al inicio, donde se vuelve a evaluar la condición.
        inicio, _fin = self.ciclos[-1]
        self.emitir('JMP', None, None, inicio)

    # ==================================================================
    # [EXTENSIÓN PERSONAL] Funciones
    #
    #   funcion entero doble(entero n) { retornar n * 2; }
    #
    #     JMP -> @L1                     el programa principal se la salta
    #     LABEL @F_doble                 aquí entra cada llamada
    #     GET_PARAM 0 -> n               copia el argumento 0 en 'n'
    #     *  n, 2 -> @t1
    #     RETURN @t1
    #     RETURN None                    por si el cuerpo termina sin retornar
    #     LABEL @L1
    #
    #   entero r = doble(21);
    #     PARAM 21
    #     CALL doble, 1 -> @t2           1 = cantidad de argumentos
    #     ASSIGN @t2 -> r
    # ==================================================================
    def generar_Funcion(self, nodo: Funcion) -> None:
        saltar = self.nueva_etiqueta()
        self.emitir('JMP', None, None, saltar)
        self.emitir('LABEL', None, None, f'@F_{nodo.nombre}')
        tipos_afuera, ciclos_afuera = dict(self.tipos), self.ciclos
        self.ciclos = []
        for i, parametro in enumerate(nodo.parametros):
            self.emitir('GET_PARAM', str(i), None, parametro.nombre)
            self.tipos[parametro.nombre] = parametro.tipo
        try:
            self.generar_bloque(nodo.cuerpo)
        finally:
            self.tipos, self.ciclos = tipos_afuera, ciclos_afuera
        self.emitir('RETURN', None, None, None)
        self.emitir('LABEL', None, None, saltar)

    def generar_Retornar(self, nodo: Retornar) -> None:
        valor = self.evaluar_expr(nodo.expr) if nodo.expr is not None else None
        self.emitir('RETURN', valor, None, None)

    def emitir_llamada(self, nodo: LlamadaFuncion) -> str:
        # Primero se calculan TODOS los argumentos y después se apilan,
        # para que una llamada dentro de un argumento no los mezcle.
        valores = [self.evaluar_expr(arg) for arg in nodo.argumentos]
        for valor in valores:
            self.emitir('PARAM', valor, None, None)
        temp = self.nuevo_temp()
        self.emitir('CALL', nodo.nombre, str(len(valores)), temp)
        return temp

    def generar_LlamadaFuncion(self, nodo: LlamadaFuncion) -> None:
        # Llamada usada como sentencia: f(1); (el resultado se descarta)
        self.emitir_llamada(nodo)
