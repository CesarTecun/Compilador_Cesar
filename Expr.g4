grammar Expr;

// ==============================================================
// LEXER REGLAS
// ==============================================================

// Palabras clave
PROGRAMA: [Pp][Rr][Oo][Gg][Rr][Aa][Mm][Aa];
INICIO: [Ii][Nn][Ii][Cc][Ii][Oo];
FIN: [Ff][Ii][Nn];
SI: [Ss][Ii];
SINO: [Ss][Ii][Nn][Oo];
PARA: [Pp][Aa][Rr][Aa];
MIENTRAS: [Mm][Ii][Ee][Nn][Tt][Rr][Aa][Ss];
HACER: [Hh][Aa][Cc][Ee][Rr];
RET: [Rr][Ee][Tt];
PINTAR: [Pp][Ii][Nn][Tt][Aa][Rr];


// Tipos de datos
ENTERO: [Ee][Nn][Tt][Ee][Rr][Oo];
DECIMAL: [Dd][Ee][Cc][Ii][Mm][Aa][Ll];
BOOL: [Bb][Oo][Oo][Ll];
CADENA: [Cc][Aa][Dd][Ee][Nn][Aa];
VOID: [Vv][Oo][Ii][Dd];
VAR: [Vv][Aa][Rr]; // Nueva palabra reservada para declaraciones inferidas


// Literales
NUMERO: [0-9]+ ('.' [0-9]+)?;
BOOL_LIT: 'verdad' | 'falso';
TEXTO: '"' ( ~["\\\r\n] | '\\' . )* '"';

// Identificadores
ID: [a-zA-Z][a-zA-Z0-9_]*;

// Operadores y símbolos
ASIGN: '=';
POTENCIA: '^';
IGUAL: '==';
DIF: '!=';
MEN_IGUAL: '<=';
MAY_IGUAL: '>=';
MENOR: '<';
MAYOR: '>';
Y: '&&';
O: '||';
NOT: '!';
SUMA: '+';
RESTA: '-';
MULT: '*';
DIV: '/';
MOD: '%';

PAR_IZQ: '(';
PAR_DER: ')';
LLAVE_IZQ: '{';
LLAVE_DER: '}';
PUNTOCOMA: ';';
COMA: ',';

// Espacios y comentarios
WS: [ \t\r\n]+ -> skip;
COMENTARIO: '//' ~[\r\n]* -> skip;
COMENT_BLOQUE: '/*' .*? '*/' -> skip;

// ==============================================================
// PARSER REGLAS
// ==============================================================

prog
    : PROGRAMA ID LLAVE_IZQ 
        ( 
            declaracion_global* funciones? bloque_programa 
            | declaracion_global* bloque_programa funciones? 
        ) 
      LLAVE_DER EOF
    ;

declaracion
    : tipo ID (ASIGN expr)? PUNTOCOMA       #declaracionSimple
    | VAR ID (ASIGN expr)? PUNTOCOMA          #declaracionInferida
    ;


declaracion_global
    : tipo ID (ASIGN expr)? PUNTOCOMA   #declaracionGlobalSimple
    ;


funciones
    : 'funciones' LLAVE_IZQ funcion* LLAVE_DER
    ;

bloque_programa
    : INICIO bloque FIN
    ;

bloque
    : LLAVE_IZQ sentencia* LLAVE_DER
    ;

funcion
    : (tipo | VOID) ID PAR_IZQ params PAR_DER bloque  #funcionDef
    ;

params
    : param (COMA param)*     #parametros
    | /* vacío */             #sinParametros
    ;

param
    : tipo ID                  #paramSimple
    ;

sentencia
    : declaracion                                                          #declaracionSentencia
    | expr PUNTOCOMA                                                       #exprSentencia
    | bloque                                                               #bloqueSentencia
    | SI PAR_IZQ expr PAR_DER sentencia (SINO sentencia)?                  #siSentencia
    | PARA PAR_IZQ (declaracion | expr PUNTOCOMA) expr? PUNTOCOMA expr? PAR_DER sentencia  #paraSentencia
    | MIENTRAS PAR_IZQ expr PAR_DER sentencia                              #mientrasSentencia
    | HACER sentencia MIENTRAS PAR_IZQ expr PAR_DER PUNTOCOMA              #hacerMientrasSentencia
    | RET expr? PUNTOCOMA                                                  #retornarSentencia
    | PINTAR PAR_IZQ args? PAR_DER PUNTOCOMA                               #pintarSentencia
    ;

// ---------------------------------------------------------------------
// Nueva estructura para las expresiones (operaciones con precedencia)
// ---------------------------------------------------------------------

expr 
    : asignacion
    ;

asignacion
    : ID ASIGN asignacion          #asignacionExp
    | logicaOr                   #soloExp
    ;

logicaOr
    : logicaOr O logicaAnd       #opLogicaOR
    | logicaAnd                  #soloLogicaAnd
    ;

logicaAnd
    : logicaAnd Y igualdad       #opLogicaAND
    | igualdad                   #soloIgualdad
    ;

igualdad
    : igualdad (IGUAL | DIF) comparacion   #opIgualdadDiferencia
    | comparacion                         #soloComparacion
    ;

comparacion
    : comparacion (MENOR | MAYOR | MEN_IGUAL | MAY_IGUAL) suma   #opComparacion
    | suma                                                    #soloSuma
    ;

suma
    : suma (SUMA | RESTA) mult     #opSumaResta
    | mult                         #soloMult
    ;

mult
    : mult (MULT | DIV | MOD) potencia   #opMultDiv
    | potencia                     #soloPotencia
    ;

potencia
    : unario POTENCIA potencia     #opPotencia
    | unario                       #soloUnario
    ;

unario
    : NOT unario                   #opUnarioNot
    | SUMA unario                  #opUnarioPositivo
    | RESTA unario                 #opUnarioNegativo
    | llamada                      #llamadaUnaria
    ;

llamada
    : primary (PAR_IZQ args? PAR_DER)*   #llamadaFuncion
    ;

primary
    : PAR_IZQ expr PAR_DER         #parentesis
    | NUMERO                       #numero
    | BOOL_LIT                     #booleano
    | TEXTO                        #texto
    | ID                           #variable
    ;

args
    : expr (COMA expr)*            #argumentos
    ;

tipo
    : ENTERO    #tipoEntero
    | DECIMAL   #tipoDecimal
    | BOOL      #tipoBool
    | CADENA    #tipoCadena
    | VOID      #tipoVoid
    ;