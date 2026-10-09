# luckyJuste — Critical Hit Patch

**Juego:** Castlevania: Harmony of Dissonance (USA, GBA)  
**Script de referencia (actual):** `apply-luckyJuste-critical-0.15.py` — versión `1.0.0`  
**Estado:** fórmula y flujo principal validados en mGBA/GDB; prueba prolongada de estabilidad y compatibilidad con otros parches aún recomendable.  
**Ámbito:** documentación del **parche de críticos**, no del parche de drops.

## 1. Objetivo y comportamiento

Reemplazar por completo la decisión de críticos original de Juste por una fórmula que premie:

- La **suerte proporcionada por equipamiento**, calculada a partir de LCK total, nivel y suerte base.
- La **ventaja de nivel de Juste sobre el enemigo golpeado**, con un máximo del 4 % adicional.

Se mantiene el RNG original, el daño crítico `×2` y la probabilidad base equivalente al **6,25 %**. Se eliminan las comprobaciones especiales vanilla de Lucky Charm y Lucky Ring y la segunda tirada asociada al Platinum Tip. Los objetos de suerte solo contribuyen mediante el atributo LCK que aportan.

**No confundir:** los porcentajes son probabilidades absolutas añadidas a la base, no multiplicadores relativos.

## 2. Fórmula exacta implementada

El juego compara una tirada entera de 16 bits con un **threshold** entero. La implementación real usa aritmética entera y coeficientes aproximados:

```python
equipment_luck = max(0, LCK_ATTR - JusteLevel - 24)
level_diff = max(0, JusteLevel - EnemyLevel)
level_bonus = min(4, level_diff // 10)
threshold = min(65536, 4096 + equipment_luck * 98 + level_bonus * 655)
critical = (original_RNG() & 0xFFFF) < threshold
```

| Sumando | Cálculo interno | Equivalencia |
|---|---|---|
| Base | `4096` | `4096/65536 × 100 = 6,25 %` |
| Suerte equipada | `equipment_luck × 98` | `98/65536 × 100 ≈ 0,1495361 %` por LCK |
| Diferencia de nivel | `level_bonus × 655` | `655/65536 × 100 ≈ 0,9994507 %` por tramo |
| Límite | `min(65536, total)` | Máximo teórico 100 % |

**Aclaración de unidades:** `0,15 %` es el incremento porcentual *objetivo* por punto de LCK. El ejecutable usa **98 unidades de threshold por punto**, equivalentes a aproximadamente **0,1495361 %**. No se multiplica `4096 × 0,15`. Análogamente, `655` aproxima un 1 %.

### 2.1 Suerte equipada

```text
EQUIPMENT_LUCK = max(0, LCK_ATTR - JusteLevel - 24)
```

- `LCK_ATTR`: suerte efectiva total de Juste.
- `JusteLevel`: nivel actual de Juste.
- `24`: componente fijo del modelo de suerte base usado por el proyecto.
- El `max(0, ...)` evita que una modificación inconsistente de estadísticas genere un bonus negativo.

Ejemplo: nivel 1 y LCK 55 → `55 − 1 − 24 = 30` de suerte equipada → `30 × 98 = 2940` unidades → aproximadamente `4,4861 %` añadido.

### 2.2 Ventaja de nivel

```text
LEVEL_DIFF = max(0, JusteLevel - EnemyLevel)
LEVEL_BONUS = min(4, LEVEL_DIFF // 10)
```

| Ventaja de nivel | Tramos | Incremento interno |
|---:|---:|---:|
| 0–9 | 0 | 0 |
| 10–19 | 1 | 655 |
| 20–29 | 2 | 1310 |
| 30–39 | 3 | 1965 |
| 40 o más | 4 | 2620 |

Si el enemigo es de igual o mayor nivel, el bonus es cero; nunca se penaliza la probabilidad base. El máximo añadido por esta mecánica es aproximadamente `3,9978 %`.

### 2.3 Tirada y resultado

```text
roll = original_RNG() & 0xFFFF   # rango 0..65535
critical = roll < threshold      # comparación estricta, sin igualdad
```

Si `roll == threshold`, **no** hay crítico. Si la función devuelve `1`, la rutina vanilla de daño duplica el daño. Si devuelve `0`, mantiene el daño normal.

La probabilidad exacta, bajo la hipótesis usual de distribución uniforme del RNG en esos 16 bits, es:

```text
P(Critical) = threshold / 65536 × 100 %
```

## 3. Ejemplos de cálculo y pruebas realizadas

| Caso | Nivel Juste | Nivel enemigo | LCK total | LCK equipo | Bonus nivel | Threshold | Probabilidad aprox. |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base, Armor Knight | 1 | 4 | 25 | 0 | 0 | 4096 | 6,25 % |
| Lucky Charm + Lucky Ring, Armor Knight (v1.1.0, calculado) | 1 | 4 | 55 | 30 | 0 | 7036 | 10,7363 % |
| Truco nivel 50 sin ajustar LCK, Armor Knight | 50 | 4 | 55 | 0 | 4 | 6716 | 10,2478 % |
| Nivel 50 + LCK ajustada a 104, Armor Knight (v1.1.0, validado) | 50 | 4 | 104 | 30 | 4 | 9656 | 14,7339 % |

**Precaución con trucos:** el código `3201877C 0032` pone el nivel a 50, pero no actualiza automáticamente la LCK. Durante las pruebas, el nivel cambió a 50 mientras LCK permaneció en 55, haciendo que `EQUIPMENT_LUCK = max(0,55−50−24)=0`. Para comprobar los tres sumandos se fijó LCK a 104.

## 4. Direcciones de memoria y código

### 4.1 RAM y datos del enemigo

| Elemento | Dirección / acceso | Tipo |
|---|---|---|
| Nivel de Juste | `0x0201877C` | `uint8` |
| LCK efectiva de Juste | `0x02018558` | `uint16` |
| STR efectiva (usada en el estudio vanilla, no en la fórmula nueva) | `0x02018552` | `uint16` |
| Puntero a base DNA enemigos | `*(uint32*)0x03002B10` | `uint32` |
| ID enemigo en entidad RAM | `*(uint8*)(EnemyEntity + 0x3E)` | `uint8` |
| Tamaño de entrada DNA | `0x24` = 36 bytes | constante |
| Nivel en entrada DNA | `*(uint8*)(EnemyDNA + 0x10)` | `uint8` |
| Threshold vanilla | `0x02018524` | `uint32` |
| Flags vanilla (incl. Platinum Tip) | `0x02018528` | `uint32` |

**Fórmula de acceso al nivel del enemigo:**

```c
uint8_t enemy_id = *(uint8_t *)(enemy_entity + 0x3E);
uint32_t dna_base = *(uint32_t *)0x03002B10;
uint8_t enemy_level = *(uint8_t *)(dna_base + enemy_id * 36 + 0x10);
```

La dirección `0x03002B10` contiene **un puntero**, no la primera entrada DNA. El nivel del enemigo se obtiene de la **entidad que está recibiendo ese impacto**, no de una dirección fija por enemigo.

### 4.2 Confirmación con dos enemigos

Se validó el acceso desde el contexto de la rutina de daño `0x0803124C`:

| Enemigo | Enemy ID (`entity+0x3E`) | DNA base | Dirección DNA | Nivel leído |
|---|---:|---|---|---:|
| Armor Knight | `8` | `0x080C7E38` | `0x080C7F58` | **4** |
| White Dragon | `13` | `0x080C7E38` | `0x080C800C` | **6** |

Para White Dragon, el log de GDB fue:

```gdb
break *0x0803124C
continue
set $enemy_id = *(unsigned char*)($r0 + 0x3E)
set $dna_base = *(unsigned int*)0x03002B10
set $dna = $dna_base + $enemy_id * 36
p/u $enemy_id
p/x $dna
p/u *(unsigned char*)($dna + 0x10)
```

Resultados:

```text
enemy_id = 13
dna = 0x080C800C
EnemyLevel = 6
```

Para Armor Knight se observó `enemy_id = 8`, `dna = 0x080C7F58` y nivel `4`.

**Esto resuelve la duda histórica sobre el nivel del enemigo en el impacto.** El campo `entity+0x3E` no contiene el nivel: contiene el ID usado para localizar su entrada DNA.

### 4.3 Direcciones de código

| Función / punto | Dirección |
|---|---|
| Entrada rutina de daño | `0x0803124C` |
| Preparación del argumento al crítico | `0x080312CE` |
| Llamada al crítico | `0x080312D0` |
| Retorno y duplicación del daño | `0x080312D4`–`0x080312DA` |
| Entrada original de crítico (sustituida por trampolín) | `0x08077CAC` |
| Nueva rutina THUMB | `0x087FFD00` |
| Threshold final calculado en `r6` | `0x087FFD62` |
| Comparación final RNG vs. threshold | `0x087FFD70` |
| Rama que devuelve crítico | `0x087FFD78` |
| Retorno del stub | `0x087FFD7A` |
| RNG original | `0x08000A78` |
| Segunda tirada vanilla de Platinum Tip (ya no alcanzada) | `0x08077CE0` |

## 5. Arquitectura del parche e integración

El script aplica **tres modificaciones** a una ROM USA limpia:

| ROM offset | Dirección GBA | Cambio |
|---|---|---|
| `0x0312CE` | `0x080312CE` | Sustituye `mov r0,r7` por `mov r0,r9` |
| `0x077CAC` | `0x08077CAC` | Sustituye 8 bytes por un trampolín THUMB |
| `0x7FFD00` | `0x087FFD00` | Inserta stub THUMB de `0x98` (152) bytes |

En la llamada original, `r9` conserva el puntero a la entidad del enemigo. El parche hace que `r0` reciba ese puntero antes de llamar a la rutina de críticos, manteniendo la instrucción `BL` del caller. El stub recibe así `EnemyEntity` y puede leer el ID y nivel del enemigo.

El trampolín es:

```asm
ldr r3, [pc, #0]
bx  r3
.word 0x087FFD01   ; bit THUMB activo
```

El código nuevo se compiló para **ARM7TDMI / Thumb-1 (armv4t)**; no requiere Thumb-2. Utiliza el RNG original y devuelve `r0 = 0` o `r0 = 1`. Preserva registros callee-saved mediante `push/pop`.

**Integración con el parche de drops:** el script de críticos exige una ROM USA **limpia** con SHA-1 exacto, y no puede aplicarse sin más sobre una ROM ya parcheada. Para fusionar ambos cambios hay que revisar colisiones de offsets, adaptar la verificación del origen y reservar regiones libres distintas. No asumir que ejecutar los dos scripts en serie funciona.

## 6. Restricciones de ROM y reproducibilidad

El script de referencia exige:

```text
ROM original: rom-harmony-usa.gba
Tamaño:       0x800000 bytes
SHA-1:        b90da0d9be0b3a0893cd9e2c399056bcf9579e21
Salida:       rom-harmony-usa-luckyJuste-critical-1.1.0.gba
```

Comprueba los bytes originales del caller, la entrada vanilla de críticos y que el espacio reservado para el stub esté relleno de `0xFF`. Si alguna comprobación falla, se aborta en vez de parchear a ciegas.

Ejecutar desde la carpeta que contiene el script y la ROM limpia:

```sh
python3 apply-luckyJuste-critical-0.15.py
```

Para reproducir v1.0.0 se utiliza su script anterior; no confundir las dos versiones. El script no acepta argumentos CLI: los nombres de ROM están definidos al principio del archivo.

**Importante para ajustes futuros:** el código THUMB está embebido como `STUB = bytes.fromhex(...)`. Cambiar únicamente el comentario de la fórmula **no cambia** el ejecutable. Si se alteran instrucciones, constantes o la longitud, hay que recompilar/reensamblar el stub, revisar literales y offsets PC-relativos, y actualizar las verificaciones y documentación.

## 7. Qué se ha validado con GDB

### 7.1 Entrada al stub

```gdb
break *0x087FFD00
continue
info registers
x/24i $pc
```

Se confirmó la entrada al stub con `r0` apuntando a la entidad golpeada y retorno previsto al caller `0x080312D4`.

### 7.2 Threshold calculado

```gdb
break *0x087FFD62
continue
p/u $r6
p/u $r5
p/u $r7
p/u $r3
```

En este punto:

- `r6` = threshold **final**.
- `r5` = nivel de Juste.
- `r7` = diferencia positiva de niveles (sin dividir entre 10).
- `r3` = bonus por nivel **ya multiplicado por 655**.

Resultados de **v1.1.0** observados en GDB:

```text
Nivel 50, LCK 25:      r6=6716, r5=50, r7=46, r3=2620
Nivel 50, LCK 104:     r6=9656, r5=50, r7=46, r3=2620
```

Para comparación histórica, en **v1.0.0** se habían observado `4096` (base), `7246` (30 LCK equipada, sin bonus de nivel), `6716` (solo bonus de nivel) y `9866` (ambos bonuses). Los valores `7246` y `9866` **no corresponden a v1.1.0**.

### 7.3 Comparación y crítico forzado

```gdb
break *0x087FFD70
continue
p/u $r0
p/u $r6
set $r0 = 0
```

Para validar paso a paso:

```gdb
si
si
si
```

La ruta observada fue:

```text
0x087FFD70  cmp r0,r6
0x087FFD72  bcc 0x087FFD78
0x087FFD78  movs r0,#1
0x087FFD7A  pop {r4,r5,r6,r7,pc}
0x080312D4  caller original
```

Se confirmó en GDB:

```text
r0 = 1  -> resultado crítico
r3 = 1  -> caller reconoce crítico
r6 = 10 -> 20 tras ejecutar lsls r6,r6,#1
```

La prueba inversa `set $r0 = $r6` produjo golpe **normal**: la comparación es estricta (`<`, no `<=`).

**Visualización:** en la prueba el jugador descubrió que era necesario activar la **reliquia de visualización de daño** para ver el número de daño/crítico en pantalla. La ausencia de ese indicador no implica por sí sola que la lógica falle; GDB permitió validar la duplicación directamente.

### 7.4 Excepciones vanilla eliminadas

- **Lucky Charm y Lucky Ring:** en v1.0.0 se comprobó que los 30 puntos de LCK equipada producían `4096 + 30×105 = 7246`, sin los bonuses vanilla `1024` y `2048`. En v1.1.0 el valor correspondiente sería `4096 + 30×98 = 7036`; **esta combinación concreta a nivel 1 no se ha repetido en GDB**, aunque sí se validó `×98` con LCK total 104 y nivel 50.
- **Platinum Tip:** en v1.1.0, equipado Platinum Tip, se colocó `break *0x08077CE0` (segunda tirada vanilla) y se golpeó sin que GDB se detuviera. Esto es coherente con el desvío completo al nuevo stub, aunque un breakpoint que no salta por sí solo no demuestra exhaustivamente todas las rutas de ataque.

### 7.5 Batería de pruebas específica de v1.1.0 (ratio 0,15 %)

**Escenario:** Juste nivel 50 mediante truco `3201877C 0032`, con atributos todavía equivalentes a nivel 1, frente a Armor Knight nivel 4. El nivel enemigo fue recuperado mediante el acceso DNA documentado anteriormente.

**Prueba A — bonus de nivel, sin suerte efectiva:**

```text
JusteLevel=50; EnemyLevel=4; LCK_ATTR=25
EquipmentLuck=max(0,25-50-24)=0
LevelDiff=46; LevelBonus=4
Threshold=4096+0*98+4*655=6716
GDB: r6=6716, r5=50, r7=46, r3=2620
```

**Prueba B — coeficiente 98 y suma de bonuses:**

Se intentó fijar `LCK_ATTR=104` entre ataques, pero el juego recalculó la estadística y volvió a `25`. La solución reproducible fue detenerse **en la entrada del stub** y modificar la LCK justo antes de su lectura:

```gdb
break *0x087FFD00
break *0x087FFD62
continue
# Cuando se detenga en 0x087FFD00:
set *(unsigned short*)0x02018558 = 104
continue
# Cuando se detenga en 0x087FFD62:
p/u $r6
p/u $r5
p/u $r7
p/u $r3
```

Resultado:

```text
EquipmentLuck=max(0,104-50-24)=30
LevelBonus=4
Threshold=4096+30*98+4*655=9656

GDB: r6=9656, r5=50, r7=46, r3=2620
```

La probabilidad correspondiente es `9656/65536 × 100 ≈ 14,7339 %`.

**Prueba C — decisión crítica:** con breakpoint en `0x087FFD70`, se forzó `set $r0 = 0` antes de la comparación. Se observó un crítico en pantalla con la reliquia de visualización del daño activada.

**Prueba D — límite estricto:** en `0x087FFD70`, se forzó `set $r0 = $r6`. Se observó un golpe **normal**, como exige `roll < threshold`.

**Prueba E — eliminación de Platinum Tip:** equipado Platinum Tip, se puso `break *0x08077CE0` y se realizaron impactos; GDB **no se detuvo** en la antigua segunda tirada.

**Alcance de las pruebas:** los valores y resultados anteriores fueron observados en v1.1.0. No se ha comunicado todavía el resultado de una sesión prolongada de estabilidad ni una integración probada con el parche de drops.

### 7.6 Qué sigue pendiente de probar exhaustivamente

Aunque las rutas críticas y sus cálculos fueron validados, se recomienda todavía:

1. Sesión prolongada de juego con múltiples enemigos, salas, equipamiento y tipos de ataque.
2. Prueba explícita de casos extremos: nivel inferior, diferencia exactamente 9/10/39/40, LCK equipo 0 y máximo previsto 79.
3. Comprobar la ROM final **combinada** con el parche de drops, no solo la ROM de críticos aislada.
4. Revisar comportamientos especiales de jefes y entidades que no usen el esquema DNA normal antes de afirmar compatibilidad universal.

## 8. Guía de ajustes futuros

### 8.1 Cambiar el peso de la suerte

Coeficiente actual:

```text
98 unidades de threshold por LCK
≈ 0,1495361 % por punto
```

Para elegir otro incremento porcentual `p` por punto:

```text
COEF_LCK ≈ round(65536 * p / 100)
```

Ejemplos:

| Objetivo por LCK | Coeficiente entero aproximado |
|---:|---:|
| 0,10 % | 66 |
| 0,12 % | 79 |
| 0,15 % | 98 |
| 0,16 % | 105 |
| 0,20 % | 131 |

Estos cambios requieren reconstruir el código THUMB, no solo modificar la documentación.

### 8.2 Cambiar el bonus por nivel

Actualmente:

```text
1 tramo cada 10 niveles
máximo 4 tramos
655 unidades por tramo
```

Se puede cambiar el divisor (frecuencia), el máximo (techo) o el coeficiente (valor porcentual), pero hay que modificar el bloque de comparaciones THUMB alrededor de `0x087FFD2E`–`0x087FFD4A` y/o la constante `655`.

### 8.3 Cambiar la base

```text
BASE = 4096 = 6,25 %
```

Para otra base `b` expresada en porcentaje:

```text
BASE_THRESHOLD ≈ round(65536 * b / 100)
```

### 8.4 Modificar las excepciones vanilla

Actualmente **no** se conserva ningún bonus de críticos específico de Lucky Charm, Lucky Ring o Platinum Tip. Si se quisiera restaurar alguno, habría que diseñarlo expresamente en la nueva rutina; no basta con volver a escribir flags vanilla porque el stub ya no ejecuta la segunda vía original.

### 8.5 Comprobar el resultado tras cualquier cambio

Con el parche aplicado:

```gdb
break *0x087FFD62
break *0x087FFD70
```

Comprobar que el primer breakpoint presenta el threshold esperado y que el segundo compara la tirada RNG contra ese mismo threshold. Verificar al menos un crítico forzado y un golpe normal forzado. Si cambia la ubicación del stub, actualizar ambas direcciones.

## 9. Riesgos y notas técnicas

- **No parchear una ROM ya modificada** con este script sin adaptar y auditar la integración.
- Las direcciones documentadas corresponden a la **ROM USA concreta** verificada por SHA-1; no extrapolarlas a otras regiones/revisiones.
- El acceso a `EnemyLevel` mediante `EnemyEntity + 0x3E` fue contrastado con Armor Knight y White Dragon. Para entidades especiales debe revisarse si comparten la misma convención.
- Los porcentajes mostrados son equivalencias de un threshold entero: `98` y `655` son aproximaciones deliberadas.
- La fórmula de Schlave `STR × EnemyLevel / EnemyHP` **no se utiliza** en este parche.
- El umbral está limitado a `65536` para no exceder el rango completo de la tirada de 16 bits.
- El script de referencia todavía contiene un aviso textual de “experimental / not yet tested”; ese aviso refleja su estado **en el momento de creación**. Las pruebas dinámicas posteriores aquí recogidas sí se realizaron.

## 10. Resumen de referencia rápida

```text
JusteLevel       = *(uint8*)0x0201877C
LCK_ATTR         = *(uint16*)0x02018558
EnemyID          = *(uint8*)(EnemyEntity + 0x3E)
DNABase          = *(uint32*)0x03002B10
EnemyLevel       = *(uint8*)(DNABase + EnemyID*36 + 0x10)

EquipmentLuck    = max(0, LCK_ATTR - JusteLevel - 24)
LevelDiff        = max(0, JusteLevel - EnemyLevel)
LevelBonus       = min(4, LevelDiff // 10)

Threshold        = min(65536,
                       4096 + EquipmentLuck*98 + LevelBonus*655)

Critical         = (original_RNG() & 0xFFFF) < Threshold
CriticalDamage   = NormalDamage * 2
```

**Estado final v1.1.0:** coeficiente `98`, bonus de nivel, suma de componentes, crítico forzado y límite estricto del RNG validados con GDB. Se comprobó que el antiguo breakpoint de Platinum Tip no se alcanza en los impactos probados. La duplicación del daño se comprobó instrucción a instrucción en v1.0.0 y se observó el crítico visual en v1.1.0. Siguen recomendadas pruebas prolongadas de estabilidad y compatibilidad con el parche de drops.
