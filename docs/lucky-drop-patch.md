# luckyJuste — referencia técnica del parche de LCK y drops

**Juego:** Castlevania: Harmony of Dissonance (GBA, USA)  
**Estado:** en desarrollo; lógica de umbrales y generación de ambos objetos verificada mediante GDB/mGBA en los escenarios descritos.  
**Fuente de implementación:** `apply-luckyJuste-drop.py` adjunto.  
**Alcance:** exclusivamente caída de objetos.

> **PARA FUTURAS IA / MANTENEDORES — LEER PRIMERO:** El script adjunto es la fuente de verdad para los bytes y offsets. El bonus de drop es **LCK de equipo ×1**, no ×1,20; Rare Ring da **+22 LCK**, no +24. Los retornos THUMB correctos son **0x0803146B** y **0x080314B7** (PC efectivo 0x0803146A y 0x080314B6). Retornar a 0x08031460/0x080314AA reintroduce los bonus vanilla (+16/+32). Las pruebas de nivel 13 usaron ajustes manuales de RAM; no confundirlas con una subida de nivel real. La estabilidad prolongada no se ha confirmado.

## 1. Objetivo y contrato funcional

El juego evalúa primero el **Drop 2 (raro)** y, si no obtiene ese objeto, evalúa el **Drop 1 (normal)**. luckyJuste conserva ese orden y los datos base de los enemigos, pero hace que **solo la LCK adicional del equipamiento** aumente los umbrales de ambos drops. Sustituye la comprobación especial vanilla del Rare Ring por una regla general para cualquier equipo que sume LCK.

```text
NATURAL_LCK    = level + 24
EQUIPMENT_LCK  = TOTAL_LCK - NATURAL_LCK
EXTRA_DROP     = EQUIPMENT_LCK           # factor exacto x1.00
DROP2_THRESHOLD = DROP2_BASE + EXTRA_DROP
DROP1_THRESHOLD = DROP1_BASE + EXTRA_DROP
```

La implementación no limita `EQUIPMENT_LCK` a cero. **Precondición práctica:** `TOTAL_LCK >= level + 24`. Si se viola (por ejemplo, al alterar solo el nivel en GDB), la resta THUMB puede desbordar; esto es una limitación conocida, no un comportamiento deseado. No modificar silenciosamente esta lógica sin analizar y probar sus efectos.

La estadística natural aumenta con el nivel y se descuenta. El Rare Ring aporta +22 LCK a la estadística real del personaje; Lucky Charm aportó +10 LCK en la prueba realizada. El parche no inspecciona los IDs de estos objetos al calcular drops: lee la LCK total.

## 2. Mapa de memoria y offsets exactos

| Recurso | Dirección GBA/RAM | Offset ROM | Descripción |
|---|---|---|---|
| LCK total | `0x02018558` | — | `uint16` en EWRAM |
| Nivel | `0x0201877C` | — | `uint8` en EWRAM |
| Punto de inyección Drop 2 | `0x08031456` | `0x031456` | Sustituye 10 bytes |
| Punto de inyección Drop 1 | `0x080314A0` | `0x0314A0` | Sustituye 10 bytes |
| Stub Drop 2 | `0x087FFF80` | `0x7FFF80` | 52 bytes |
| Stub Drop 1 | `0x087FFFC0` | `0x7FFFC0` | 52 bytes |
| Rare Ring, estructura | `0x084B2C0C` | `0x4B2C0C` | Byte de LCK en `+9` |
| Rare Ring, byte LCK | `0x084B2C15` | `0x4B2C15` | Escribir `22` = `0x16` |
| Retorno Drop 2 (literal THUMB) | `0x0803146B` | — | Ejecuta desde `0x0803146A` |
| Retorno Drop 1 (literal THUMB) | `0x080314B7` | — | Ejecuta desde `0x080314B6` |

Los stubs ocupan `0x7FFF80..0x7FFFB3` y `0x7FFFC0..0x7FFFF3`, sin solapamiento. Cada uno contiene 40 bytes de instrucciones/relleno y tres literales de 4 bytes en `+0x28`, `+0x2C` y `+0x30`.

### Bytes originales verificados por el script

```text
Drop 2 @ 0x031456: 79 20 F8 F7 40 F9 00 28 04 D0
Drop 1 @ 0x0314A0: 79 20 F8 F7 1B F9 00 28 05 D0
Comparación Drop 2 @ 0x03146A: B4 42 0F D2
Comparación Drop 1 @ 0x0314B6: 39 89 B4 42 15 D2
```

El script exige una ROM USA limpia de al menos `0x800000` bytes, comprueba esos bytes y exige `0xFF` en las zonas de inyección. Aborta si las comprobaciones fallan. **No aplicar sobre una ROM ya parcheada.**

## 3. Trampolines THUMB e implementación del stub

Los puntos de inyección tienen distinta alineación; cada trampoline mide exactamente 10 bytes. Se carga una dirección con bit 0 activado y se salta con `bx r0`.

```asm
; Drop 2, offset % 4 == 2
nop
ldr r0, [pc, #0]
bx  r0
.word 0x087FFF81

; Drop 1, offset % 4 == 0
ldr r0, [pc, #0]
bx  r0
.word 0x087FFFC1
nop
```

La rutina inyectada es idéntica en ambas ramas salvo por la dirección de retorno:

```asm
+00  ldr  r0, [pc, #36]     ; literal LCK en +0x28
+02  ldrh r1, [r0]          ; TOTAL_LCK
+04  ldr  r0, [pc, #36]     ; literal nivel en +0x2C
+06  ldrb r0, [r0]          ; level
+08  subs r1, r1, r0
+0A  subs r1, #24            ; EQUIPMENT_LCK
+0C  adds r6, r6, r1        ; bonus x1 al umbral base
+0E  ldr  r0, [pc, #32]     ; literal retorno en +0x30
+10  bx   r0
+12..+27  nop                ; relleno
+28  .word 0x02018558
+2C  .word 0x0201877C
+30  .word RETURN_ADDRESS
```

**Bytes decisivos:** `76 18` (`adds r6,r6,r1`) y `08 48` (`ldr r0,[pc,#32]` desde `+0x0E`). La instrucción de carga del retorno debe apuntar al literal `+0x30`, no a la dirección de nivel `+0x2C`; un desplazamiento erróneo puede bloquear el juego.

### Por qué son imprescindibles los retornos corregidos

```asm
; Drop 2 — retorno CORRECTO
0x0803146A: cmp r4, r6
0x0803146C: bcs 0x0803148E

; Drop 1 — retorno CORRECTO
0x080314B6: ldrh r1, [r7, #8]
0x080314B8: cmp r4, r6
0x080314BA: bcs 0x080314E8
```

**No regresar** a `0x08031460` ni `0x080314AA`: esas rutas vanilla ejecutan respectivamente `adds r0,#16` y `adds r0,#32`, duplicando el beneficio del Rare Ring después del bonus de LCK. El código original de comparación y las bifurcaciones de éxito/fracaso se conservan al volver a `0x0803146A` y `0x080314B6`.

## 4. Probabilidades y ejemplo reproducible: Armor Knight

El RNG de cada tirada se compara con un umbral sobre 1024 valores (`0..1023`): éxito si `r4 < threshold`. En el rango de umbrales relevante, `P(tirada) = threshold/1024`. Cada unidad añadida equivale a `0,09765625` puntos porcentuales absolutos.

**Armor Knight (Enemy ID `0x08`, estructura `0x080C7F58`):** Drop 2 = Field Armor, base 8 (`[r7+0x13]`); Drop 1 = Potion, base 16 (`[r7+0x12]`).

| Equipo/LCK adicional | Umbral raro | Prob. tirada rara | Umbral normal | Prob. tirada normal |
|---|---:|---:|---:|---:|
| Sin LCK adicional, +0 | 8 | 0,78125 % | 16 | 1,5625 % |
| Lucky Charm, +10 | 18 | 1,7578125 % | 26 | 2,5390625 % |
| Rare Ring, +22 | 30 | 2,9296875 % | 38 | 3,7109375 % |

El Drop 2 tiene prioridad. La probabilidad **efectiva por muerte** del Drop 1 es `(1 - P2) × P1`, no simplemente `P1`. Los valores de la tabla son probabilidades de cada comparación individual.

## 5. Pruebas GDB/mGBA REALIZADAS: evidencia y alcance

Conexión típica:

```bash
arm-none-eabi-gdb \
  -ex "target remote localhost:2345" \
  -ex "set architecture armv4t" \
  -ex "set arm force-mode thumb"
```

Puntos útiles del parche **actual**:

```gdb
break *0x087FFF8C    # Drop 2: suma adds r6,r6,r1
break *0x087FFFCC    # Drop 1: suma adds r6,r6,r1
break *0x0803146A    # Drop 2: comparación final
break *0x080314B8    # Drop 1: comparación final
```

**Nota:** `0x080314B6` es el retorno que ejecuta `ldrh r1,[r7,#8]`; en `0x080314B8`, `r1` ya puede haber sido sobrescrito con el identificador del objeto y **no representa la LCK extra**. Observar `r1` en el stub o en Drop 2 para medir el bonus. No reutilizar direcciones internas de una rutina antigua con desplazamientos/multiplicador.

### 5.1 Rare Ring, nivel 1

Lecturas reales: `TOTAL_LCK=47`, `level=1`, `47-1-24=22`. En el stub de Drop 2 se observó `r1=22`, `r6=8`, y tras `adds r6,r6,r1`, `r6=30`. La carga de retorno dio `r0=0x0803146B`; `bx r0` condujo a `0x0803146A`, `cmp r4,r6`. En Drop 1 se observó `r1=22`, `r6=16`, después `r6=38`, retorno `0x080314B7` y comparación en `0x080314B8`. **Validado:** +22 en ambas ramas, sin +16/+32 adicionales.

### 5.2 Sin equipamiento que aporte LCK

A nivel 1 se observó `TOTAL_LCK=25`, `level=1`, bonus 0 y `r6=16` en la comparación normal. Posteriormente se simuló nivel 13 con `TOTAL_LCK=37`, `level=13` y bonus 0; se observó `r1=0`, `r6=8` en Drop 2 y `r6=16` en Drop 1. **Validado:** la LCK natural se descuenta en ambos umbrales en estas condiciones.

### 5.3 Rare Ring con nivel 13 simulado

Se ajustaron manualmente `level=13` y `TOTAL_LCK=59` para representar LCK natural 37 + Rare Ring 22. La fórmula devolvió 22. En Drop 2 se observó `r1=22`, `r6=30` (`r4=633`); en Drop 1 `r6=38` (`r4=291`). **Validado para RAM preparada manualmente**, no como prueba de recálculo de estadísticas por subida de nivel real.

### 5.4 Lucky Charm (+10 LCK), nivel 13 simulado

Al equipar Lucky Charm después de cambiar el nivel mediante GDB, el juego mostró `TOTAL_LCK=35` y `level=13`, es decir `extra_lck=-2`. Esto se explica por estadísticas desincronizadas: `25` de LCK natural correspondiente a nivel 1 + `10` del objeto, aunque el byte de nivel se había puesto a 13. Se ajustó manualmente `TOTAL_LCK=47` para representar 37+10; se comprobó `extra_lck=10`. Después se observó:

```text
Drop 2: r1=10, r6=18, r4=565, pc=0x0803146A, cmp r4,r6
Drop 1: r6=26, r4=420, pc=0x080314B8, cmp r4,r6
```

**Validado:** la LCK adicional de otro objeto distinto del Rare Ring modifica ambos umbrales exactamente en +10. **No validado:** actualización automática del nivel/estadísticas tras subir de nivel de forma natural.

### 5.5 Drops exitosos forzados

Se forzó `r4=0` en la comparación rara (`0x0803146A`) con un umbral positivo: el usuario confirmó que apareció Field Armor. Para la ruta normal se forzó primero el fallo del raro con `r4=1023` y luego `r4=0` en `0x080314B8`: el usuario confirmó que apareció Potion. **Validado:** ambos caminos pueden generar el objeto esperado. Estas pruebas forzaron el RNG; no miden frecuencias estadísticas reales.

### 5.6 Estado de las comprobaciones

| Comprobación | Estado |
|---|---|
| Fórmula ×1 y Rare Ring +22 | Confirmado por código y GDB |
| Exclusión de LCK natural en nivel 1 y nivel 13 simulado | Confirmado por GDB |
| Bonus de Lucky Charm +10 en ambos drops | Confirmado por GDB con RAM ajustada |
| Ausencia de bonus vanilla duplicados | Confirmado por flujo de retorno y comparaciones |
| Generación de Field Armor y Potion | Confirmado por el usuario con RNG forzado |
| Subida de nivel **real** y recálculo de LCK | Pendiente |
| Estabilidad prolongada, guardado/carga, varios enemigos | Pendiente de confirmación |
| Equipamiento que disminuya LCK / protección de underflow | Pendiente de análisis y posible corrección |
| Pruebas de probabilidades mediante muestreo masivo | No realizadas |

## 6. Procedimiento mínimo para reproducir pruebas

**Antes:** cargar la ROM parcheada generada desde ROM limpia, guardar copia del save y utilizar Armor Knight. Detener la ejecución con GDB antes de inspeccionar RAM. Si se ha modificado el nivel artificialmente, **no asumir** que la LCK total se recalculará sola.

```gdb
# Verificar nivel, LCK total y bonus
p/d *(unsigned char*)0x0201877C
p/d *(unsigned short*)0x02018558
p/d *(unsigned short*)0x02018558 - *(unsigned char*)0x0201877C - 24

# Comprobar ambos umbrales
delete breakpoints
break *0x0803146A
break *0x080314B8
continue

# Al detenerse: comprobar r6, r4 y PC
info registers r1 r4 r6 pc
x/4i $pc
```

Para una prueba de **nivel 13 simulado**, sin equipo de LCK:

```gdb
set *(unsigned char*)0x0201877C = 13
set *(unsigned short*)0x02018558 = 37
```

Con Rare Ring como única fuente de LCK: `TOTAL_LCK=59`; con Lucky Charm como única fuente: `TOTAL_LCK=47`. Estos ajustes son solo para depuración; no guardar la partida como si se hubiera subido de nivel legítimamente.

Para forzar drops en Armor Knight:

```gdb
# En 0x0803146A: fuerza éxito del raro
set $r4 = 0
continue

# O, en otra muerte, en 0x0803146A fuerza fallo del raro
set $r4 = 1023
continue
# En 0x080314B8 fuerza éxito del normal
set $r4 = 0
continue
```

Si no se alcanza Drop 1, puede ser porque Drop 2 haya tenido éxito. No interpretar la ausencia de segundo breakpoint como un fallo sin verificar la rama tomada.

## 7. Riesgos, errores ya encontrados y precauciones para ajustes futuros

1. **Desalineación de literales THUMB:** los trampolines requieren direcciones literales alineadas a 4 bytes. No cambiar la disposición de 10 bytes sin revisar PC-relative `ldr`.
2. **Carga del retorno:** en el stub actual la instrucción correcta es `08 48` en `+0x0E`, que lee el literal en `+0x30`. Un desplazamiento erróneo puede provocar saltos inválidos y bloqueos.
3. **Bonus vanilla duplicado:** regresar a `0x08031460` o `0x080314AA` suma +16/+32 además del bonus por LCK. Usar retornos THUMB `0x0803146B` / `0x080314B7`.
4. **Registro `r1` sobrescrito:** en `0x080314B8` `r1` contiene otros datos (`0x300` en las pruebas), no la suerte; verificar `r6` o inspeccionar el stub antes del retorno.
5. **Underflow de LCK:** el código no tiene clamp a cero. En pruebas manuales se observó `TOTAL_LCK=35`, `level=13` y resta matemática `-2`. No ejecutar el parche en ese estado inconsistente como si fuera un escenario normal; evaluar protección si se desea admitir equipo con LCK negativa o estados alterados.
6. **Fuente de verdad:** consultar el Python adjunto para los bytes y tamaños. No copiar fórmulas ×1,20, Rare Ring +24 ni offsets internos de stubs anteriores.
7. **Separación de sistemas:** no tocar rutinas de daño crítico ni efectos de Platinum Tip; no forman parte de este parche.
8. **No confundir pruebas forzadas con probabilidad estadística:** las confirmaciones de Field Armor y Potion demuestran que los caminos funcionan, no que la distribución RNG esté empíricamente medida.

## 8. Próximas pruebas recomendadas

1. Subir de nivel **dentro del juego** y verificar que `TOTAL_LCK - level - 24` permanece igual con el mismo equipamiento.
2. Repetir el cálculo con dos objetos de LCK simultáneos, y tras equipar/desequipar sin editar RAM.
3. Jugar sin breakpoints durante 20–30 muertes, cambiar de salas, recoger objetos, guardar y recargar; registrar cualquier congelación.
4. Revisar si existe equipo o estado legítimo con `TOTAL_LCK < level+24`; decidir si hace falta clamp antes de modificar código.
5. Si se desea validar el balance, medir frecuencias de drops con muestras suficientes, diferenciando probabilidad por tirada y probabilidad efectiva por muerte.

## 9. Parámetros del script de trabajo

El script adjunto utiliza estos nombres, que deben mantenerse si se hacen ajustes futuros:

```python
version = "1.0.0"
original_rom = "rom-harmony-usa.gba"
patched_rom = f"rom-harmony-usa-luckyJuste-drop-{version}.gba"
```

La cadena anterior es un parámetro técnico del script; **el proyecto sigue en desarrollo**. No interpretar ese campo como evidencia de publicación.

**Resumen operativo:** dos stubs de 52 bytes, fórmula `r6 += TOTAL_LCK - level - 24`, Rare Ring +22, retornos a comparaciones sin bonus vanilla, pruebas GDB positivas para Rare Ring, Lucky Charm y ambos objetos generados; quedan pendientes nivel real, underflow y estabilidad prolongada.
