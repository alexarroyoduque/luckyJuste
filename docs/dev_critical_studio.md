# Estudio técnico del sistema de golpes críticos en Castlevania: Harmony of Dissonance

**Juego:** Castlevania: Harmony of Dissonance (GBA - USA)

**Estado del estudio:** Concluido con alta confianza mediante análisis estático de ROM y validación dinámica con GDB/mGBA.

## 1. Objetivo

Este documento recopila el análisis realizado mediante **desensamblado THUMB, inspección estática de la ROM y depuración con GDB/mGBA** sobre el sistema de golpes críticos de *Castlevania: Harmony of Dissonance*.

El objetivo inicial era comprobar la fórmula atribuida a Schlave:

```text
Critical Chance (%) = STR * EnemyLevel / EnemyMaxHP
```

El análisis permitió localizar la rutina que decide el crítico, reconstruir sus dos vías de éxito y validar dinámicamente tanto la comparación principal como los efectos especiales de Lucky Charm, Lucky Ring y Platinum Tip. El estudio distingue entre:

- la estadística **LCK**;
- efectos específicos de determinados objetos;
- la probabilidad base de crítico;
- una segunda oportunidad especial ligada a ciertas condiciones del ataque/equipamiento.

La conclusión principal es que **la estadística LCK no se consulta para calcular el crítico**. Sin embargo, la ROM contiene efectos de crítico hardcodeados para ciertos objetos concretos, lo que puede haber contribuido históricamente a la percepción de que “Luck aumenta los críticos”.

---

## 2. Condiciones iniciales de prueba

Se utilizó **Armor Knight** como enemigo de referencia.

| Parámetro | Valor |
|---|---:|
| Enemy ID | `0x08` |
| Dirección base ROM | `0x080C7F58` |
| HP máximo | `32` (`0x20`) |
| Nivel | `4` |
| Defensa | `20` |
| EXP | `11` |

Condiciones iniciales de Juste:

```text
Level = 1
STR   = 30
```

El daño normal observado contra Armor Knight fue:

```text
10
```

Durante las pruebas se observó también un crítico natural de:

```text
20
```

Esto proporcionó la primera evidencia experimental de:

```text
Critical Damage = Normal Damage * 2
```

---

## 3. Hipótesis inicial: fórmula de Schlave

Con:

```text
STR          = 30
Enemy Level  = 4
Enemy Max HP = 32
```

la fórmula atribuida a Schlave predice:

```text
30 * 4 / 32 = 3.75%
```

El análisis se inició para comprobar si la rutina real utilizaba STR, nivel del enemigo y HP máximo o si generaba una probabilidad distinta.

La evidencia reunida durante el estudio no respalda esa fórmula como descripción de la comprobación principal de crítico.

---

## 4. Identificación del STR efectivo de Juste

Se utilizó temporalmente un truco que establece STR en `999`.

Búsqueda en EWRAM:

```gdb
find /h 0x02000000, 0x02040000, 999
```

Resultado:

```text
0x02018552
```

Con el truco activo:

```gdb
p/u *(unsigned short*)0x02018552
```

Resultado:

```text
999
```

Tras desactivar el truco:

```text
30
```

Por tanto:

```text
STR efectivo de Juste = uint16 @ 0x02018552
```

Esta dirección se utilizó para comprobar posteriormente que modificar STR no altera el threshold principal de crítico.

---

## 5. Localización de la rutina de daño

Un read-watchpoint sobre STR condujo a la rutina de daño alrededor de `0x0803124C`.

Fragmento decisivo:

```asm
0x080312CE: adds    r0, r7, #0
0x080312D0: bl      0x08077CAC
0x080312D4: adds    r3, r0, #0
0x080312D6: cmp     r3, #0
0x080312D8: beq.n   0x080312DC
0x080312DA: lsls    r6, r6, #1
```

La función:

```text
0x08077CAC
```

devuelve la condición de crítico.

Si devuelve cero:

```text
golpe normal
```

Si devuelve un valor distinto de cero:

```asm
lsls r6, r6, #1
```

por lo que:

```text
critical_damage = normal_damage * 2
```

La observación experimental `10 -> 20` coincide exactamente con esta lógica.

---

## 6. Rutina que decide el crítico

La función comienza en:

```text
0x08077CAC
```

Fragmento principal:

```asm
0x08077CAC: push    {r4, r5, lr}
0x08077CAE: lsls    r0, r0, #16
0x08077CB0: lsrs    r5, r0, #16
0x08077CB2: movs    r4, #0

0x08077CB4: bl      0x08000A78
0x08077CB8: ldr     r1, [pc, #60]
0x08077CBA: ands    r1, r0
0x08077CBC: ldr     r0, [pc, #60]
0x08077CBE: ldr     r2, [r0, #0]
0x08077CC0: ldr     r3, [pc, #60]
0x08077CC2: adds    r0, r2, r3
0x08077CC4: ldr     r0, [r0, #0]
0x08077CC6: cmp     r1, r0
0x08077CC8: bcs.n   0x08077CCC
0x08077CCA: movs    r4, #1
```

Literales:

```gdb
x/5wx 0x08077CF8
```

Resultado:

```text
0x08077CF8: 0x0000FFFF
0x08077CFC: 0x08494580
0x08077D00: 0x00018524
0x08077D04: 0x00018528
0x08077D08: 0x0000F003
```

Puntero base:

```gdb
x/wx 0x08494580
```

Resultado:

```text
0x08494580: 0x02000000
```

Por tanto:

```text
CRIT_THRESHOLD = uint32 @ 0x02018524
CRIT_FLAGS     = uint32 @ 0x02018528
```

---

## 7. Comprobación principal de crítico

La función llama al RNG:

```asm
bl 0x08000A78
```

y aplica:

```text
RNG & 0xFFFF
```

La lógica observada es:

```text
roll = RNG & 0xFFFF

if roll < CRIT_THRESHOLD:
    critical = 1
else:
    critical = 0
```

El threshold base observado fue:

```text
CRIT_THRESHOLD = 4096 = 0x1000
```

Como `roll` toma valores de `0` a `65535`, existen exactamente `65536` resultados posibles.

Por tanto:

```text
P(main critical) = CRIT_THRESHOLD / 65536
```

Con threshold base:

```text
4096 / 65536 = 6.25%
```

Resultado:

```text
Base critical chance = 6.25%
```

---

## 8. Validación directa del rango RNG

Se colocó un breakpoint antes del `AND`:

```gdb
break *0x08077CBA
```

Ejemplo observado:

```text
RNG completo = 0x91E69467
máscara      = 0x0000FFFF
```

Después de:

```asm
ands r1, r0
```

se obtuvo:

```text
r1 = 0x9467 = 37991
```

Por tanto:

```text
0x91E69467 & 0x0000FFFF = 0x9467
```

Esto valida directamente que la tirada principal utiliza los **16 bits bajos del RNG**, es decir:

```text
0..65535
```

y por tanto:

```text
65536 resultados posibles
```

---

## 9. Validación dinámica de la comparación principal

Breakpoint:

```gdb
break *0x08077CC6
```

Ejemplo observado:

```text
r1 = 54677 = 0xD595
r0 = 4096  = 0x1000
```

Normalmente:

```text
54677 < 4096 -> falso
```

Se forzó:

```gdb
set $r1 = 0
continue
```

Como:

```text
0 < 4096
```

el golpe resultante fue observado como **Critical**.

Esto demuestra que `0x08077CC6` controla efectivamente la decisión principal de crítico.

---

## 10. Validación del threshold en RAM

Lectura directa:

```gdb
p/u *(unsigned int*)0x02018524
```

Resultado:

```text
4096
```

Se comprobó además:

```text
STR 30  -> CRIT_THRESHOLD = 4096
STR 999 -> CRIT_THRESHOLD = 4096
STR 30  -> CRIT_THRESHOLD = 4096
```

También se probó un nivel extremadamente alto de Juste:

```text
Juste Level = 153
CRIT_THRESHOLD = 4096
```

y varios enemigos distintos:

```text
CRIT_THRESHOLD = 4096
```

Por tanto, bajo las condiciones probadas, el threshold principal no depende de:

- STR;
- nivel de Juste;
- nivel del enemigo;
- HP máximo del enemigo.

---

## 11. Validación forzada del threshold

Se modificó temporalmente:

```gdb
set *(unsigned int*)0x02018524 = 65536
```

Como:

```text
roll = RNG & 0xFFFF
```

el máximo posible es `65535`.

Por tanto:

```text
roll < 65536
```

siempre es cierto.

Al continuar, el golpe fue observado como **Critical**.

Esto valida experimentalmente que:

```text
0x02018524 = threshold usado por la comprobación principal
```

Restauración:

```gdb
set *(unsigned int*)0x02018524 = 4096
```

---

## 12. Inicialización del threshold principal

El análisis estático de la ROM permitió localizar la rutina que inicializa `0x02018524`. Sus resultados fueron posteriormente confirmados de forma dinámica con GDB.

La inicialización base construye:

```text
0x1000 = 4096
```

que corresponde a:

```text
6.25%
```

La misma rutina contiene comprobaciones específicas de determinados objetos equipados y puede aumentar ese threshold.

### 12.1 Distinción fundamental: LCK vs. objetos concretos

La rutina de críticos **no consulta la estadística LCK**.

No existe en esta lógica una operación equivalente a:

```text
critical_chance = f(LCK)
```

Sin embargo, determinados objetos concretos contienen efectos hardcodeados sobre el threshold.

Esto significa:

```text
LCK como estadística -> no interviene directamente

objeto específico    -> puede tener un efecto especial de crítico
```

Por tanto, equipar un objeto que además otorgue LCK no implica que el bonus crítico proceda de LCK.

---

## 13. Bonuses hardcodeados de Lucky Charm y Lucky Ring

El análisis estático identificó dos comprobaciones específicas de equipo en la inicialización del threshold principal; los valores resultantes fueron posteriormente confirmados de forma dinámica con GDB:

```text
ID 0x6E -> Lucky Charm
ID 0x77 -> Lucky Ring
```

### 13.1 Lucky Charm

Cuando está equipado, añade:

```text
+1024 al threshold
```

Por tanto:

```text
4096 + 1024 = 5120
```

y:

```text
5120 / 65536 = 7.8125%
```

Es decir:

```text
Lucky Charm:
6.25% -> 7.8125%
```

Incremento absoluto:

```text
+1.5625%
```

### 13.2 Lucky Ring

Cuando está equipado, añade:

```text
+2048 al threshold
```

Por tanto:

```text
4096 + 2048 = 6144
```

y:

```text
6144 / 65536 = 9.375%
```

Es decir:

```text
Lucky Ring:
6.25% -> 9.375%
```

Incremento absoluto:

```text
+3.125%
```

### 13.3 Ambos efectos

Si ambos bonuses se aplican simultáneamente:

```text
4096 + 1024 + 2048 = 7168
```

y:

```text
7168 / 65536 = 10.9375%
```

### 13.4 Interpretación correcta

Lucky Charm y Lucky Ring son objetos asociados a LCK, pero la rutina no calcula el crítico a partir de la estadística LCK.

Los efectos están implementados como excepciones específicas:

```text
Lucky Charm equipado -> bonus fijo
Lucky Ring equipado  -> bonus fijo
```

Por tanto:

```text
LCK no controla los críticos
```

aunque estos objetos concretos sí pueden aumentar la probabilidad de crítico por código especial.

---

## 14. Validación dinámica de Lucky Charm y Lucky Ring

Las comprobaciones específicas encontradas mediante análisis estático se verificaron equipando y desequipando los objetos y leyendo directamente:

```gdb
p/u *(unsigned int*)0x02018524
p/x *(unsigned int*)0x02018528
```

Resultados observados:

| Configuración | `0x02018524` | Probabilidad principal |
|---|---:|---:|
| Sin Lucky Charm/Ring | `4096` | `6.25%` |
| Lucky Charm | `5120` | `7.8125%` |
| Lucky Ring | `6144` | `9.375%` |
| Lucky Charm + Lucky Ring | `7168` | `10.9375%` |

Por tanto, queda validado dinámicamente:

```text
Lucky Charm -> +1024 threshold -> +1.5625%
Lucky Ring  -> +2048 threshold -> +3.125%
```

La prueba individual con Lucky Ring produjo explícitamente:

```text
0x02018524 = 6144
```

y la combinación Lucky Charm + Lucky Ring produjo:

```text
0x02018524 = 7168
```

Estos resultados coinciden exactamente con el análisis estático de la rutina de inicialización.


## 14A. Comparación con la fórmula atribuida a Schlave

Para Armor Knight bajo las condiciones iniciales:

```text
STR          = 30
Enemy Level  = 4
Enemy Max HP = 32
```

Schlave predice:

```text
30 * 4 / 32 = 3.75%
```

La comprobación principal base observada es:

```text
4096 / 65536 = 6.25%
```

Además:

```text
STR 30  -> 4096
STR 999 -> 4096

Level 1   -> 4096
Level 153 -> 4096

Armor Knight -> 4096
otros enemigos -> 4096
```

Por tanto, la fórmula atribuida a Schlave **no describe la comprobación principal identificada**.

La evidencia disponible indica que aquella fórmula era una hipótesis experimental, no una reconstrucción del código interno.

---

## 15. Segunda vía de crítico

Después de la comprobación principal aparece:

```asm
0x08077CCC: subs    r0, r5, #2
0x08077CCE: cmp     r0, #3
0x08077CD0: bhi.n   0x08077CF0

0x08077CD2: ldr     r1, [pc, #48]
0x08077CD4: adds    r0, r2, r1
0x08077CD6: ldr     r0, [r0, #0]

0x08077CD8: movs    r1, #128
0x08077CDA: ands    r0, r1
0x08077CDC: cmp     r0, #0
0x08077CDE: beq.n   0x08077CF0

0x08077CE0: bl      0x08000A78
0x08077CE4: ldr     r1, [pc, #32]
0x08077CE6: ands    r1, r0
0x08077CE8: cmp     r1, #0
0x08077CEA: bne.n   0x08077CF0

0x08077CEC: movs    r0, #1
0x08077CEE: orrs    r4, r0
```

La segunda vía requiere dos condiciones previas:

```text
2 <= r5 <= 5
```

y:

```text
(CRIT_FLAGS & 0x80) != 0
```

donde:

```text
CRIT_FLAGS = uint32 @ 0x02018528
```

---

## 16. Significado de `r5`

Durante un impacto se observó:

```text
r5 = 3
```

El valor procede del byte:

```text
[r8 + 3]
```

de una estructura temporal del ataque.

Ejemplo observado:

```text
r8 = 0x03007E94

+00: 02
+01: 00
+02: 00
+03: 03   <- valor que llega a r5
+04: 00
+05: 04
+06: 00
+07: 02
```

El análisis cruzado con los IDs de ataque indica que `r5` corresponde al **Attack ID**.

Valores relevantes para Juste:

```text
0x02 -> ataque aéreo de látigo
0x03 -> ataque normal de látigo
```

La segunda vía acepta:

```text
Attack ID 2..5
```

Por tanto, está restringida a determinados tipos de impacto y no es una segunda tirada universal para todos los ataques del juego.

---

## 17. Significado de `0x02018528` y del bit `0x80`

Durante las pruebas normales:

```text
0x02018528 = 0x02
```

y:

```text
0x02 & 0x80 = 0
```

por lo que la segunda tirada no se ejecutaba.

Se forzó temporalmente:

```gdb
set *(unsigned int*)0x02018528 = 0x82
```

Esto conserva el bit `0x02` y añade:

```text
0x80
```

Con `0x82`, la ejecución alcanzó inmediatamente la segunda llamada al RNG.

Por tanto, se validó dinámicamente que:

```text
bit 0x80 -> habilita la segunda vía
```

El análisis estático de la ROM muestra que este campo se construye a partir de propiedades del **Whip Item** equipado.

La identificación del bit `0x80` con **Platinum Tip** fue confirmada también dinámicamente. Con Platinum Tip equipado se ejecutó:

```gdb
p/x (*(unsigned int*)0x02018528) & 0x80
```

Resultado:

```text
0x80
```

Por tanto, Platinum Tip activa efectivamente el bit que habilita esta segunda vía, y la condición funcional puede expresarse como:

```text
ataque compatible (Attack ID 2..5)
+
Platinum Tip equipado
```

---

## 18. Probabilidad de la segunda tirada

Cuando las condiciones anteriores se cumplen, el juego realiza:

```text
(RNG & 0xF003) == 0
```

La máscara:

```text
0xF003
```

selecciona seis bits:

```text
0xF000 -> 4 bits
0x0003 -> 2 bits
```

Total:

```text
6 bits
```

Para que el resultado sea cero, los seis bits seleccionados deben valer cero simultáneamente.

Por tanto:

```text
P(second check) = 1 / 2^6
                = 1 / 64
                = 1.5625%
```

---

## 19. Validación dinámica de la segunda tirada

Se forzó:

```text
0x02018528 = 0x82
```

y se colocó breakpoint en:

```text
0x08077CE4
```

Ejemplo observado:

```text
RNG  = 0xC31FAFB3
MASK = 0x0000F003
```

Después del `AND`:

```text
0xC31FAFB3 & 0x0000F003 = 0xA003
```

Como:

```text
0xA003 != 0
```

la segunda comprobación falló en ese caso.

La prueba confirma dinámicamente la operación:

```text
(RNG & 0xF003) == 0
```

Después del experimento se restauró:

```gdb
set *(unsigned int*)0x02018528 = 2
```

---

## 20. Probabilidad combinada con la segunda vía

La segunda comprobación es una oportunidad adicional.

Si la probabilidad principal es:

```text
P1
```

y la segunda vía está habilitada:

```text
P2 = 1.5625%
```

la probabilidad total es:

```text
P(total) = 1 - (1 - P1) * (1 - P2)
```

No debe calcularse simplemente sumando ambas probabilidades porque ambas tiradas pueden acertar en el mismo impacto.

### 20.1 Base + Platinum Tip

```text
P1 = 6.25%
P2 = 1.5625%
```

Entonces:

```text
P(total) = 1 - (1 - 0.0625) * (1 - 0.015625)
         = 7.71484375%
```

Resultado:

```text
Base + Platinum Tip = ~7.7148%
```

### 20.2 Tabla de combinaciones

| Configuración | Probabilidad aproximada |
|---|---:|
| Base | `6.25%` |
| Platinum Tip | `7.7148%` |
| Lucky Charm | `7.8125%` |
| Lucky Ring | `9.375%` |
| Lucky Charm + Lucky Ring | `10.9375%` |
| Lucky Charm + Platinum Tip | `9.2529%` |
| Lucky Ring + Platinum Tip | `10.7910%` |
| Lucky Charm + Lucky Ring + Platinum Tip | `12.3291%` |

Los valores con Platinum Tip suponen un ataque cuyo `Attack ID` cumpla la condición `2..5`.

---

## 21. LCK y críticos: conclusión precisa

La conclusión correcta no es simplemente:

```text
"Luck affects criticals"
```

ni tampoco:

```text
"Luck-related equipment never affects criticals"
```

La distinción correcta es:

### La estadística LCK

```text
No se consulta en la rutina de crítico analizada.
```

Por tanto:

```text
más LCK por sí sola no implica más críticos
```

### Lucky Charm y Lucky Ring

Estos objetos tienen:

```text
efectos hardcodeados específicos sobre CRIT_THRESHOLD
```

independientemente de que también otorguen LCK.

### Platinum Tip

No modifica el threshold principal.

En determinadas clases de ataque habilita una:

```text
segunda tirada independiente de 1.5625%
```

---

## 22. Comandos GDB principales utilizados

### Identificación de STR

```gdb
find /h 0x02000000, 0x02040000, 999
p/u *(unsigned short*)0x02018552
```

### Rutina de daño

```gdb
disassemble 0x08031220, 0x08031320
```

### Rutina de crítico

```gdb
disassemble 0x08077CAC, 0x08077D40
```

### Literales

```gdb
x/5wx 0x08077CF8
x/wx 0x08494580
```

### Threshold principal

```gdb
p/u *(unsigned int*)0x02018524
```

### Flags de crítico

```gdb
p/x *(unsigned int*)0x02018528
```

### Breakpoint de comparación principal

```gdb
break *0x08077CC6
continue
```

### Inspección

```gdb
p/u $r1
p/u $r0
p/x $r1
p/x $r0
```

### Forzar crítico principal

```gdb
set $r1 = 0
continue
```

### Forzar threshold del 100%

```gdb
set *(unsigned int*)0x02018524 = 65536
continue
```

Restaurar:

```gdb
set *(unsigned int*)0x02018524 = 4096
```

### Activar experimentalmente la segunda vía

```gdb
set *(unsigned int*)0x02018528 = 0x82
```

Restaurar:

```gdb
set *(unsigned int*)0x02018528 = 2
```

### Inspeccionar estructura temporal del ataque

```gdb
p/u $r5
p/x $r8
x/16bx $r8
```

---

## 23. Resultados confirmados

El estudio permite establecer:

1. La rutina de daño llama a `0x08077CAC` para decidir el crítico.
2. Un resultado distinto de cero duplica el daño mediante `lsls r6, r6, #1`.
3. Se observó experimentalmente `10 -> 20`.
4. La comprobación principal utiliza `RNG & 0xFFFF`.
5. Existen `65536` resultados posibles en esa tirada.
6. El threshold principal se lee de `0x02018524`.
7. El threshold base es `4096`.
8. La probabilidad base es `6.25%`.
9. Forzar `r1 = 0` produjo crítico.
10. Forzar threshold `65536` produjo crítico.
11. STR `30 -> 999` no modificó el threshold.
12. Juste Level `1 -> 153` no modificó el threshold.
13. Cambiar de enemigo no modificó el threshold base observado.
14. La fórmula atribuida a Schlave no describe esta comprobación principal.
15. La estadística LCK no se consulta en la rutina de críticos analizada.
16. Lucky Charm y Lucky Ring tienen bonuses hardcodeados sobre el threshold principal.
17. Lucky Charm añade `1024`, llevando la probabilidad principal a `7.8125%`; este valor fue confirmado dinámicamente (`5120`).
18. Lucky Ring añade `2048`, llevando la probabilidad principal a `9.375%`; este valor fue confirmado dinámicamente (`6144`).
19. La segunda vía requiere `Attack ID 2..5`.
20. También requiere el bit `0x80` de `0x02018528`.
21. Ese bit corresponde a una propiedad del Platinum Tip y su activación (`0x80`) fue confirmada dinámicamente con el objeto equipado.
22. La segunda vía utiliza `(RNG & 0xF003) == 0`.
23. Su probabilidad es `1/64 = 1.5625%`.
24. La probabilidad total cuando ambas vías están habilitadas debe calcularse como dos oportunidades independientes.

---

## 24. Estado del estudio

La lógica de probabilidad de crítico de Juste puede considerarse **resuelta con alta confianza para las rutas estudiadas**, al estar respaldada por desensamblado, análisis estático de ROM y validación dinámica con GDB.

La fórmula conceptual queda:

```text
1. Construir CRIT_THRESHOLD principal.

2. Primera tirada:
   roll1 = RNG & 0xFFFF

   if roll1 < CRIT_THRESHOLD:
       critical = true

3. Si el ataque es compatible y está activa la propiedad 0x80:
   roll2 = RNG & 0xF003

   if roll2 == 0:
       critical = true

4. Si critical:
   damage *= 2
```

Con configuración base:

```text
CRIT_THRESHOLD = 4096
P(main) = 6.25%
```

El estudio ya no necesita asumir que STR, nivel, Enemy HP o LCK formen parte de una fórmula general de crítico.

---

## 25. Conclusión

La rutina vanilla de críticos de *Harmony of Dissonance* no utiliza la fórmula atribuida históricamente a Schlave.

La comprobación principal utiliza un RNG de 16 bits:

```text
critical if (RNG & 0xFFFF) < CRIT_THRESHOLD
```

con:

```text
CRIT_THRESHOLD base = 4096
```

lo que produce:

```text
6.25%
```

El daño crítico es:

```text
normal_damage * 2
```

La estadística LCK no se consulta para calcular el crítico.

No obstante, existen efectos especiales hardcodeados:

```text
Lucky Charm -> aumenta CRIT_THRESHOLD
Lucky Ring  -> aumenta CRIT_THRESHOLD
Platinum Tip -> habilita una segunda oportunidad de crítico
```

La segunda vía usa:

```text
(RNG & 0xF003) == 0
```

y tiene:

```text
1.5625%
```

de probabilidad cuando sus condiciones de activación se cumplen.

Esto explica por qué observaciones históricas podían sugerir relaciones entre “suerte”, equipo y críticos aunque la estadística LCK propiamente dicha no forme parte de la fórmula.

Las comprobaciones finales con GDB confirmaron los thresholds `4096`, `5120`, `6144` y `7168` para las configuraciones correspondientes, así como la activación del bit `0x80` con Platinum Tip. Con estas validaciones, el estudio de la lógica vanilla de críticos de Juste se considera concluido con alta confianza.
