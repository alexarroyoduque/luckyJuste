# Estudio técnico del sistema de drops y del Rare Ring en Castlevania: Harmony of Dissonance (GBA)

Este documento recopila el análisis realizado mediante **DSVania Editor**, desensamblado THUMB y depuración con **GDB/mGBA** sobre el sistema de caída de objetos (*drops*) de *Castlevania: Harmony of Dissonance* (USA).

El objetivo es documentar qué datos intervienen en una tirada de drop, en qué orden se evalúan los dos objetos de un enemigo y cuál es el comportamiento real del **Rare Ring** en la ROM original.

> **Alcance:** las conclusiones sobre direcciones, registros y bonus del Rare Ring se apoyan en el desensamblado y en las pruebas GDB recogidas durante el estudio. Las probabilidades porcentuales se derivan del espacio RNG de 1024 valores observado en estas rutinas.

---

## 1. Sujeto de prueba: Armor Knight (enemigo `0x08`)

Para seguir la lógica de memoria se utilizó **Armor Knight** como enemigo de referencia.

### 1.1 Datos extraídos con DSVania Editor

| Campo | Valor |
|---|---|
| ID de enemigo | `0x08` |
| Dirección base en ROM | `0x080C7F58` |
| HP | `0x0020` = 32 |
| EXP | `0x000B` = 11 |
| Nivel | `0x04` = 4 |
| Ataque | `0x000A` = 10 |
| Defensa | `0x14` = 20 |
| Create Code | `0x08091C0D` |
| Update Code | `0x08091C99` |
| Debilidad observada | Thunder |

### 1.2 Drops del Armor Knight

| Drop | Objeto | Tipo | Valor base | Probabilidad base |
|---|---|---:|---:|---:|
| Drop 1 (normal) | Potion | `0x03` | `0x10` = 16 | `16 / 1024 = 1.5625%` |
| Drop 2 (raro) | Field Armor | `0x05` | `0x08` = 8 | `8 / 1024 = 0.78125%` |

Estas probabilidades representan los umbrales base observados en la estructura del enemigo. El Rare Ring puede modificar temporalmente el umbral utilizado por la comparación, sin modificar el byte almacenado en la estructura.

---

## 2. Estructura de datos del enemigo en ROM

Cada entrada de enemigo analizada ocupa `0x24` bytes (36 bytes).

| Offset | Tamaño | Descripción | Armor Knight (`0x080C7F58`) |
|---|---:|---|---|
| `0x00` | 4 | Create Code Pointer | `0x08091C0D` |
| `0x04` | 4 | Update Code Pointer | `0x08091C99` |
| `0x08` | 1 | ID Drop 1 | `0x00` (Potion) |
| `0x09` | 1 | Tipo Drop 1 | `0x03` |
| `0x0A` | 1 | ID Drop 2 | `0x02` (Field Armor) |
| `0x0B` | 1 | Tipo Drop 2 | `0x05` |
| `0x0C` | 2 | HP máximo | `0x0020` |
| `0x0E` | 2 | EXP | `0x000B` |
| `0x10` | 1 | Nivel | `0x04` |
| `0x11` | 1 | Defensa | `0x14` |
| `0x12` | 1 | **Umbral base Drop 1** | `0x10` = 16 |
| `0x13` | 1 | **Umbral base Drop 2** | `0x08` = 8 |
| `0x14` | 2 | Ataque | `0x000A` |
| `0x20` | 1 | Bitfield de resistencias | — |
| `0x21` | 1 | Bitfield de debilidades | Thunder activo |

Para Armor Knight:

```text
Drop 1: 0x080C7F58 + 0x12 = 0x080C7F6A
Drop 2: 0x080C7F58 + 0x13 = 0x080C7F6B
```

Durante las pruebas, estas direcciones de ROM pudieron utilizarse como puntos de observación para localizar la rutina que consume los valores de drop.

> En las observaciones realizadas, la rutina lee los valores de drop desde la estructura estática en ROM en el momento de evaluar la muerte del enemigo.

---

## 3. Modelo de probabilidad observado

Las rutinas transforman la salida del RNG mediante desplazamientos y terminan comparando un valor contenido en `r4` contra un umbral.

En las rutas estudiadas, el espacio efectivo de la tirada es de **1024 valores posibles (`0–1023`)**. Por tanto, para un umbral `T` dentro de ese intervalo:

```text
éxito si RNG < T
```

y:

```text
P(drop) = T / 1024
```

Por ello, un punto añadido al umbral equivale a:

```text
1 / 1024 = 0.09765625 puntos porcentuales
```

Ejemplos:

| Incremento del umbral | Incremento absoluto |
|---:|---:|
| `+1` | `+0.09765625 pp` |
| `+8` | `+0.78125 pp` |
| `+16` | `+1.5625 pp` |
| `+32` | `+3.125 pp` |

> Estos valores son incrementos **absolutos en puntos porcentuales** mientras el umbral permanezca dentro del rango relevante de la comparación. No deben confundirse con incrementos porcentuales relativos respecto a la probabilidad base.

---

## 4. Orden de evaluación de los drops

El análisis de la rutina muestra que el juego evalúa primero **Drop 2 (raro)** y, si este no produce un objeto, continúa con **Drop 1 (normal)**.

### 4.1 Drop 2 primero

La lectura del umbral de Drop 2 aparece en:

```asm
0x0803144C: ldrb  r6, [r7, #19]     ; offset 0x13
```

Para Armor Knight:

```text
r6 = 8
```

Si la comprobación de Drop 2 tiene éxito, la ejecución sigue la ruta que genera ese objeto y no continúa con la evaluación normal de Drop 1.

### 4.2 Drop 1 después

La evaluación del Drop 1 comienza posteriormente:

```asm
0x08031496: ldrb  r6, [r7, #18]     ; offset 0x12
```

Para Armor Knight:

```text
r6 = 16
```

Por tanto, los dos drops **no son dos tiradas independientes que puedan producir simultáneamente ambos objetos en una misma muerte**: Drop 2 tiene prioridad y Drop 1 se evalúa cuando la ruta anterior no ha producido el objeto raro.

---

## 5. Rutina vanilla de Drop 2 (raro)

Fragmento relevante de la ROM original:

```asm
0x08031448: cmp   r0, #0
0x0803144A: beq.n 0x0803148E
0x0803144C: ldrb  r6, [r7, #19]     ; umbral base Drop 2
0x0803144E: bl    0x08000A78        ; RNG
0x08031452: lsls  r0, r0, #18
0x08031454: lsrs  r4, r0, #22
0x08031456: movs  r0, #121          ; Rare Ring = 0x79
0x08031458: bl    0x080296DC
0x0803145C: cmp   r0, #0
0x0803145E: beq.n 0x0803146A

; Rare Ring equipado
0x08031460: adds  r0, r6, #0
0x08031462: adds  r0, #16
0x08031464: cmp   r4, r0
0x08031466: bcc.n 0x0803146E

; Rare Ring no equipado
0x0803146A: cmp   r4, r6
```

Esto demuestra que la ROM original **sí comprueba el Rare Ring para Drop 2**.

Con el anillo equipado:

```text
umbral_raro = drop_base + 16
```

Sin el anillo:

```text
umbral_raro = drop_base
```

---

## 6. Rutina vanilla de Drop 1 (normal)

Fragmento relevante:

```asm
0x0803148E: ldrh  r0, [r7, #8]
0x08031490: adds  r1, r0, #0
0x08031492: cmp   r1, #0
0x08031494: beq.n 0x080314E8
0x08031496: ldrb  r6, [r7, #18]     ; umbral base Drop 1
0x08031498: bl    0x08000A78        ; RNG
0x0803149C: lsls  r0, r0, #20
0x0803149E: lsrs  r4, r0, #22
0x080314A0: movs  r0, #121          ; Rare Ring = 0x79
0x080314A2: bl    0x080296DC
0x080314A6: cmp   r0, #0
0x080314A8: beq.n 0x080314B6

; Rare Ring equipado
0x080314AA: adds  r0, r6, #0
0x080314AC: adds  r0, #32
0x080314AE: cmp   r4, r0
0x080314B0: bcc.n 0x080314BC

; Rare Ring no equipado
0x080314B6: ldrh  r1, [r7, #8]
0x080314B8: cmp   r4, r6
```

Con el anillo equipado:

```text
umbral_normal = drop_base + 32
```

Sin el anillo:

```text
umbral_normal = drop_base
```

---

## 7. Comportamiento vanilla del Rare Ring

El Rare Ring tiene un comportamiento **asimétrico** entre ambos tipos de drop:

| Tipo | Sin Rare Ring | Con Rare Ring | Bonus |
|---|---|---|---:|
| Drop 2 — raro | `drop_base` | `drop_base + 16` | **+16** |
| Drop 1 — normal | `drop_base` | `drop_base + 32` | **+32** |

Para Armor Knight, esto implica:

### Field Armor — Drop 2

```text
Base:       8 / 1024  = 0.78125%
Rare Ring: 24 / 1024  = 2.34375%
```

Incremento absoluto:

```text
+16 / 1024 = +1.5625 puntos porcentuales
```

Incremento relativo respecto a la tasa base:

```text
(24 - 8) / 8 = +200%
```

La probabilidad final es tres veces la probabilidad base.

### Potion — Drop 1

Para la comparación concreta del Drop 1:

```text
Base:       16 / 1024 = 1.5625%
Rare Ring:  48 / 1024 = 4.6875%
```

Incremento absoluto:

```text
+32 / 1024 = +3.125 puntos porcentuales
```

Incremento relativo respecto a la tasa base de esa tirada:

```text
(48 - 16) / 16 = +200%
```

> La probabilidad global de obtener Potion por muerte no es simplemente `48/1024`, porque Drop 1 solo se evalúa después de que Drop 2 no haya producido su objeto. Véase la sección siguiente.

---

## 8. Probabilidad efectiva por muerte y prioridad de Drop 2

Dado que Drop 2 se evalúa primero, la probabilidad efectiva de Drop 1 depende también de que Drop 2 falle.

Si denominamos:

```text
P2 = probabilidad de éxito de Drop 2
P1 = probabilidad de éxito de la tirada de Drop 1
```

entonces:

```text
P(Drop 2 por muerte) = P2
P(Drop 1 por muerte) = (1 - P2) * P1
```

Para Armor Knight sin Rare Ring:

```text
P2 = 8 / 1024
P1 = 16 / 1024

P(Field Armor) = 8 / 1024
               = 0.78125%

P(Potion) = (1 - 8/1024) * (16/1024)
          = 1016/1024 * 16/1024
          ≈ 1.55029%
```

Con Rare Ring vanilla:

```text
P2 = 24 / 1024
P1 = 48 / 1024

P(Field Armor) = 24 / 1024
               = 2.34375%

P(Potion) = (1 - 24/1024) * (48/1024)
          = 1000/1024 * 48/1024
          ≈ 4.57764%
```

Esta distinción es importante: los valores `16/1024`, `48/1024`, etc. describen la **tirada individual** de Drop 1, mientras que su probabilidad final por muerte está condicionada por el resultado de Drop 2.

---

## 9. Validación dinámica del Rare Ring con GDB

Las siguientes pruebas se realizaron sobre la **ROM original sin modificar**.

### 9.1 Drop 2 — raro

Breakpoint:

```gdb
break *0x08031464
continue
```

Valores observados con Rare Ring equipado:

```text
r6 = 8
r0 = 24
r0 - r6 = 16
```

La instrucción actual era:

```asm
0x08031464: cmp r4, r0
```

Por tanto:

```text
24 - 8 = 16
```

La prueba confirma dinámicamente:

```text
Drop 2 + Rare Ring -> drop_base + 16
```

### 9.2 Drop 1 — normal

Breakpoint:

```gdb
break *0x080314AE
continue
```

Valores observados:

```text
r6 = 16
r0 = 48
r0 - r6 = 32
```

La instrucción actual era:

```asm
0x080314AE: cmp r4, r0
```

Por tanto:

```text
48 - 16 = 32
```

La prueba confirma dinámicamente:

```text
Drop 1 + Rare Ring -> drop_base + 32
```

### 9.3 Resumen experimental

| Tipo | `r6` | `r0` | `r0 - r6` |
|---|---:|---:|---:|
| Drop 2 — raro | 8 | 24 | **16** |
| Drop 1 — normal | 16 | 48 | **32** |

La evidencia dinámica coincide con el desensamblado de ambas ramas.

---

## 10. Qué representa realmente `r6`

Una observación importante para interpretar correctamente GDB:

`r6` contiene el **umbral base leído de la estructura del enemigo**.

El Rare Ring vanilla **no modifica `r6`**. Cuando está equipado, el juego construye temporalmente el umbral aumentado en `r0`:

```asm
adds r0, r6, #0
adds r0, #bonus
cmp  r4, r0
```

Por eso, comprobar únicamente `r6` no permite determinar si el Rare Ring está funcionando.

La prueba correcta es observar:

```gdb
p/u $r6
p/u $r0
p/d $r0 - $r6
```

en el punto de comparación correspondiente.

Esta distinción corrige una interpretación inicial del estudio en la que se había tomado la permanencia de `r6` en su valor base como evidencia de que el Rare Ring no afectaba a Drop 2.

---

## 11. Uso de DSVania Editor durante el análisis

DSVania Editor permitió identificar:

1. La dirección base de la estructura del Armor Knight (`0x080C7F58`).
2. Los offsets `0x12` y `0x13` correspondientes a los valores base de Drop 1 y Drop 2.
3. Los IDs y tipos de los objetos asociados.
4. Las direcciones concretas `0x080C7F6A` y `0x080C7F6B`, útiles para seguir cuándo el motor consume estos datos.

La combinación de editor de estructuras + watchpoints/breakpoints + desensamblado resultó más fiable que inferir el comportamiento únicamente a partir de los valores visibles en los registros.

---

## 12. Comandos GDB útiles

Conexión típica a mGBA:

```bash
arm-none-eabi-gdb \
  -ex "target remote localhost:2345" \
  -ex "set architecture armv4t" \
  -ex "set arm force-mode thumb"
```

Inspección:

```gdb
# Instrucción actual
x/i $pc

# Desensamblado alrededor del PC
disassemble $pc-0x10, $pc+0x10

# Registros
info registers

# Estructura apuntada por r7
x/9wx $r7

# Valores relevantes para la comparación
p/u $r4
p/u $r6
p/u $r0
```

Breakpoints principales:

```gdb
# Comparación Drop 2 con Rare Ring
break *0x08031464

# Comparación Drop 1 con Rare Ring
break *0x080314AE
```

Watchpoints utilizados durante el rastreo del Armor Knight:

```gdb
rwatch *0x080C7F6A    # valor Drop 1
rwatch *0x080C7F6B    # valor Drop 2
```

> Los watchpoints sirven para localizar cuándo se leen los datos. Para validar el bonus del Rare Ring es preferible detenerse directamente en las instrucciones `cmp` indicadas arriba.

---

## 13. Forzado de resultados durante depuración

Para pruebas controladas puede alterarse el estado de los registros antes de la comparación. Sin embargo, debe hacerse **después de que la rutina haya cargado/calculado el umbral que realmente utilizará**, porque instrucciones posteriores pueden sobrescribir `r0` o `r6`.

La forma más fiable es detenerse inmediatamente antes de la comparación y modificar el registro que participa en ella.

Por ejemplo, en la ruta con Rare Ring:

```gdb
break *0x08031464     # Drop 2
# o:
break *0x080314AE     # Drop 1
```

Una vez detenido, se puede inspeccionar `r4` y el umbral (`r0`) y establecer una relación que garantice éxito o fallo para comprobar el flujo de control.

Esto es más preciso que modificar indiscriminadamente `r6` y `r0` desde un watchpoint anterior.

---

## 14. Relación con el parche de LCK

El estudio vanilla establece una referencia importante para cualquier modificación posterior del sistema:

```text
Rare Ring original:
Drop 2 (raro)   -> +16 al umbral
Drop 1 (normal) -> +32 al umbral
```

Si un parche elimina la comprobación específica del Rare Ring y convierte el accesorio en `+16 LCK`, aplicando después esa LCK adicional por igual a ambos drops, el resultado pasa a ser:

```text
Parche con +16 LCK:
Drop 2 (raro)   -> +16
Drop 1 (normal) -> +16
```

Por tanto, ese diseño:

- conserva el efecto numérico vanilla del Rare Ring sobre Drop 2;
- reduce el efecto vanilla sobre Drop 1 de `+32` a `+16`;
- hace que el sistema dependa de una regla general de LCK en lugar de una excepción específica para el Rare Ring.

Esto no es necesariamente un error: es una **decisión de balance del parche**. Debe documentarse como una diferencia deliberada respecto a la ROM original.

---

## 15. Conclusiones

El análisis permite establecer los siguientes hechos para la ROM estudiada:

1. Los enemigos almacenan sus dos umbrales base de drop en los offsets `0x12` (Drop 1) y `0x13` (Drop 2) de su estructura.
2. Armor Knight utiliza `16` como umbral base para Potion y `8` para Field Armor.
3. El motor evalúa primero Drop 2 y después Drop 1 si la ruta del objeto raro no tiene éxito.
4. Las tiradas observadas utilizan un espacio efectivo de 1024 valores (`0–1023`).
5. El Rare Ring original se comprueba en **ambas** ramas.
6. En Drop 2, el Rare Ring añade **+16** al umbral.
7. En Drop 1, el Rare Ring añade **+32** al umbral.
8. El bonus se construye temporalmente en `r0`; `r6` conserva el umbral base.
9. Las pruebas GDB (`8 -> 24` y `16 -> 48`) confirman dinámicamente lo observado en el desensamblado.
10. Debido a la prioridad de Drop 2, la probabilidad efectiva por muerte de Drop 1 está condicionada al fallo de Drop 2.

Estas observaciones proporcionan una base reproducible para estudiar o modificar posteriormente la relación entre **LCK**, equipamiento y probabilidades de drop.
