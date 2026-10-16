# luckyJuste — referencia técnica del parche de LCK y drops

**Juego:** Castlevania: Harmony of Dissonance (GBA, USA)  
**Estado:** en desarrollo; cálculos y ramas de drop contrastados con GDB/mGBA en los escenarios enumerados.  
**Ámbito:** exclusivamente caída de objetos; no modificar críticos ni otros sistemas.  
**Implementación de referencia actual:** `apply-luckyJuste-drop.py` (ratio ×0,50), contrastada con el desensamblado y las capturas GDB. **Validador reutilizable:** `validate-luckyJuste-drop.gdb`.

> **LEER PRIMERO — PARA FUTURAS IA / MANTENEDORES:** El ratio de referencia actual es **×0,50**, con `EXTRA_DROP = max(0, TOTAL_LCK - level - 24) >> 1`. El **Rare Ring no aporta LCK** y conserva los bonus vanilla **+16 raro / +32 normal**, acumulables con el bonus de suerte equipada. **Conservar estadísticas originales del anillo**. Los stubs actuales están en `0x087FFE80` y `0x087FFF00`; el logger `validate-luckyJuste-drop.gdb` registra datos sin imponer un ratio. La experiencia normal, la estabilidad prolongada y los drops exitosos del parche ×0,50 no quedan demostrados por las trazas de umbrales.
## 1. Contrato funcional y fórmula exacta

El motor comprueba primero **Drop 2 (raro)** y, si no lo obtiene, evalúa **Drop 1 (normal)**. La modificación añade un bonus de LCK del equipamiento a ambos umbrales, sin cambiar el orden, el RNG, los valores base de los enemigos ni la comprobación especial vanilla del Rare Ring.

```python
natural_lck = level + 24
equipment_lck = max(0, total_lck - natural_lck)
extra_drop = equipment_lck // 2
rare_threshold = rare_base + extra_drop + (16 if rare_ring_equipped else 0)
normal_threshold = normal_base + extra_drop + (32 if rare_ring_equipped else 0)
```

La implementación THUMB **×0,50** usa `lsrs r1,r1,#1` en `0x087FFE90` (raro) y `0x087FFF10` (normal). Para +10 LCK: `10 >> 1 = 5`. Se trunca a entero; no se multiplica el umbral base ni la probabilidad total.

La protección observada pone a cero la LCK de equipamiento cuando la resta resulta negativa. Esto se confirmó en GDB con nivel 13 artificial, LCK total 35: el bonus en `r1` fue 0. Esta protección no equivale a una auditoría de todos los extremos de aritmética.

**Rare Ring:** sus estadísticas originales permanecen intactas. Su bonus especial original se conserva mediante la llamada de comprobación de equipo `0x080296DC` y el retorno a las ramas vanilla. Si Lucky Charm aporta +10 LCK, el extra de fórmula ×0,50 es +5 y, con ambos equipados, se obtiene `base + 5 + 16` (raro) y `base + 5 + 32` (normal).

## 2. Mapa de memoria, puntos de inyección y referencias

| Elemento | Dirección GBA/RAM | Offset ROM / notas |
|---|---|---|
| LCK total | `0x02018558` | `uint16`, EWRAM |
| Nivel Juste | `0x0201877C` | `uint8`, EWRAM |
| Inyección Drop 2 | `0x08031456` | `0x031456`, 10 bytes |
| Inyección Drop 1 | `0x080314A0` | `0x0314A0`, 10 bytes |
| Stub Drop 2 observado | `0x087FFE80` | offset `0x7FFE80` |
| Stub Drop 1 observado | `0x087FFF00` | offset `0x7FFF00` |
| Función vanilla comprobación de equipo | `0x080296DC` | entrada THUMB `0x080296DD` |
| Drop 2, comparación con anillo | `0x08031464` | `cmp r4,r0`; umbral = `r6+16` |
| Drop 2, comparación sin anillo | `0x0803146A` | `cmp r4,r6` |
| Drop 1, comparación con anillo | `0x080314AE` | `cmp r4,r0`; umbral = `r6+32` |
| Drop 1, comparación sin anillo | `0x080314B8` | `cmp r4,r6` |
| Armor Knight (ID `0x08`) | `0x080C7F58` | umbral normal `[+0x12]=16`, raro `[+0x13]=8`, EXP=11 |

Los trampolines observados apuntan a `0x087FFE81` (raro; literal en `0x0803145C`) y `0x087FFF01` (normal; literal en `0x080314A4`). Los bytes interpretados como instrucciones ARM/VFP dentro de estos literales son **datos**, no instrucciones a ejecutar.

**Bytes vanilla de los puntos de parcheo** (del estudio técnico):

```text
Drop 2 @ 0x031456: 79 20 F8 F7 40 F9 00 28 04 D0
Drop 1 @ 0x0314A0: 79 20 F8 F7 1B F9 00 28 05 D0
```

**No reutilizar los retornos de la implementación ×1** (`0x0803146B` y `0x080314B7`) como si fueran los únicos retornos del nuevo diseño: la variante vigente tiene dos rutas de salida por stub, una para el anillo y otra sin él. **Nunca retornar a una instrucción situada dentro de los diez bytes sobrescritos**.

## 3. Desensamblado y disposición del parche ×0,50 (referencia actual)

### 3.1 Drop 2 (raro), stub `0x087FFE80`

```asm
0x087FFE80: ldr  r0, [pc,#44]   ; literal LCK en 0x087FFEB0
0x087FFE82: ldrh r1, [r0]
0x087FFE84: ldr  r0, [pc,#44]   ; nivel en 0x087FFEB4
0x087FFE86: ldrb r0, [r0]
0x087FFE88: subs r1, r1, r0
0x087FFE8A: subs r1, #24
0x087FFE8C: bpl  0x087FFE90
0x087FFE8E: movs r1, #0
0x087FFE90: lsrs r1, r1, #1 ; floor(LCK_equipo / 2)
0x087FFE92: nop
0x087FFE94: nop
0x087FFE96: nop
0x087FFE98: adds r6, r6, r1  ; aplica bonus ×0,50
0x087FFE9A: movs r0, #121   ; ID de Rare Ring en la comprobación vanilla
0x087FFE9C: ldr  r2, [pc,#28]
0x087FFE9E: mov  lr, r2
0x087FFEA0: ldr  r3, [pc,#20]
0x087FFEA2: bx   r3         ; llama a comprobación original
0x087FFEA4: cmp  r0, #0
0x087FFEA6: beq  0x087FFEAC
0x087FFEA8: ldr  r0, [pc,#20]
0x087FFEAA: bx   r0         ; ruta con anillo
0x087FFEAC: ldr  r0, [pc,#20]
0x087FFEAE: bx   r0         ; ruta sin anillo
```

Literales confirmados por GDB:

```text
0x087FFEB0 = 0x02018558  ; LCK
0x087FFEB4 = 0x0201877C  ; nivel
0x087FFEB8 = 0x080296DD  ; función de comprobación
0x087FFEBC = 0x087FFEA5  ; retorno de la llamada al stub
0x087FFEC0 = 0x08031461  ; ruta vanilla CON anillo, PC efectivo 0x08031460
0x087FFEC4 = 0x0803146B  ; ruta vanilla SIN anillo, PC efectivo 0x0803146A
```

**Validación de retorno sin anillo:** GDB mostró `r0=0` en `0x087FFEA4`, siguió `beq` hacia `0x087FFEAC`, cargó `0x0803146B` y `bx r0` aterrizó en `0x0803146A` con `r6=8` cuando no había LCK extra.

### 3.2 Drop 1 (normal), stub `0x087FFF00`

El cálculo inicial es análogo al Drop 2, con `lsrs r1,r1,#1` en `0x087FFF10` y `nop` en `0x087FFF12`, `0x087FFF14`, `0x087FFF16`. Direcciones observadas:

```text
0x087FFF00 entrada de stub
0x087FFF18 adds r6,r6,r1  ; aplica bonus ×0,50
0x087FFF1A movs r0,#121
0x087FFF24 cmp r0,#0      ; después de volver de comprobación de equipo
0x087FFF26 beq 0x087FFF2C
0x087FFF28 ldr r0,[pc,#20] ; salida con anillo
0x087FFF2A bx r0
0x087FFF2C ldr r0,[pc,#20] ; salida sin anillo
0x087FFF2E bx r0
```

Literales confirmados:

```text
0x087FFF30 = 0x02018558
0x087FFF34 = 0x0201877C
0x087FFF38 = 0x080296DD
0x087FFF3C = 0x087FFF25
0x087FFF40 = 0x080314AB  ; ruta CON anillo, PC efectivo 0x080314AA
0x087FFF44 = 0x080314B7  ; ruta SIN anillo, PC efectivo 0x080314B6
```

**Validación de retorno sin anillo:** GDB mostró `r0=0`, `r6=16`, luego `bx r0` aterrizó en `0x080314B6`, seguido de `cmp r4,r6` en `0x080314B8`.

**Nota para mantener compatibilidad:** el `r6` ya aumentado por la fórmula llega a la rama original; cuando el anillo está equipado, la ROM calcula un segundo umbral temporal en `r0` sumando 16/32. No reemplazar esta comparación por la ruta sin anillo o se perdería el bonus especial.

## 4. Modelo de probabilidades y Armor Knight

En estas rutas el RNG efectivo tiene 1024 valores (`0..1023`); éxito si `roll < threshold`. La probabilidad por tirada es `threshold/1024` para umbrales dentro de rango. Drop 1 solo se intenta si Drop 2 no produce objeto.

| Equipo | Bonus LCK | Drop raro: umbral | Drop normal: umbral |
|---|---:|---:|---:|
| Sin LCK extra ni anillo | 0 | 8 | 16 |
| Lucky Charm (+10 LCK) | 5 | 13 | 21 |
| Rare Ring solo (sin LCK extra) | 0 | 24 | 48 |
| Lucky Charm + Rare Ring | 5 | 29 | 53 |

Con ambos equipados, `P(Field Armor) = 29/1024 ≈ 2,8320 %`. `P(Potion | falló raro) = 53/1024 ≈ 5,1758 %`. La probabilidad efectiva de Potion por muerte es `(1 - 29/1024) * (53/1024) ≈ 5,0292 %`.

## 5. Registro de pruebas GDB y alcance

Las pruebas del parche actual se registraron con Lucky Charm (+10 LCK) y con Lucky Charm combinado con Rare Ring. El registro automatizado confirma los umbrales de ambas rutas; no mide por sí mismo experiencia, estabilidad prolongada ni generación efectiva de objetos.

### 5.1 Captura automatizada ×0,50 — evidencia observada

En `luckyJuste-drop-validation.log` se registraron **cuatro muertes** de Armor Knight, las primeras tres con Lucky Charm (+10 LCK) y la última con Lucky Charm y Rare Ring. Nivel 1, LCK total 35, suerte equipada 10, bonus calculado `r1=5`. Las cuatro tiradas raras y las cuatro normales llegaron a las comparaciones previstas:

| Muerte | Equipo | Umbral raro | Umbral normal | Ruta |
|---|---|---:|---:|---|
| 1 | Lucky Charm | 13 | 21 | Sin anillo |
| 2 | Lucky Charm | 13 | 21 | Sin anillo |
| 3 | Lucky Charm | 13 | 21 | Sin anillo |
| 4 | Lucky Charm + Rare Ring | 29 | 53 | Con anillo |

En la cuarta muerte el log registró `special_delta=16` en raro y `special_delta=32` en normal. **Validado:** fórmula ×0,50 y suma con los bonus originales del anillo en esas ocho comparaciones. **No validado por ese log:** aparición efectiva de objetos, EXP por muerte, estabilidad prolongada, ratio para valores de LCK distintos de 10 o subida de nivel real.

### 5.2 Validador genérico `validate-luckyJuste-drop.gdb`

El archivo **no codifica el ratio ni umbrales esperados**. Lee nivel y LCK al entrar en cada stub, registra `r1` antes de sumar, `r6` después de sumar, `r4` (RNG), y distingue comparaciones normales (`r6`) y especiales (`r0`, diferencia `r0-r6`). Permite cambiar equipo entre muertes, pero **no identifica los nombres de los objetos**: anotar el orden de equipamiento.

Uso en GDB, con mGBA conectado y detenido:

```gdb
source validate-luckyJuste-drop.gdb
# Equipar o cambiar objetos en mGBA y derrotar enemigos.
# Para terminar: Ctrl+C
set logging enabled off
```

Se genera `luckyJuste-drop-validation.log` en el directorio de trabajo de GDB; el archivo se **sobrescribe** al iniciar otra captura. El script instala diez breakpoints con comandos silenciosos y `continue` automático. Para interpretar el log, indicar **qué ratio se pretende probar** y cuándo cambió el equipo; contrastar `bonus` con `floor(max(0,LCK_total-level-24) × ratio)`, `after=base+bonus` y, en la ruta especial, `final=after+16` (raro) o `final=after+32` (normal).

**Límite de compatibilidad:** es genérico respecto del **ratio**, pero NO respecto del **layout binario**. Usa `0x087FFE80`, `0x087FFE98`, `0x087FFE9A`, `0x087FFF00`, `0x087FFF18`, `0x087FFF1A`, y las cuatro comparaciones vanilla `0x08031464`, `0x0803146A`, `0x080314AE`, `0x080314B8`. Si una futura modificación desplaza estas instrucciones, actualizar los breakpoints. No es un verificador de EXP, aparición de objetos o ausencia de bloqueos.

## 6. Procedimiento GDB para futuras comprobaciones

```gdb
# Conexión típica: arm-none-eabi-gdb -ex "target remote localhost:2345"
set architecture armv4t
set arm force-mode thumb

# Nivel y LCK
p/d *(unsigned char*)0x0201877C
p/d *(unsigned short*)0x02018558
p/d *(unsigned short*)0x02018558 - *(unsigned char*)0x0201877C - 24

# Bonus de LCK antes de sumar
break *0x087FFE98   # Drop 2, r1=bonus, r6=base
break *0x087FFF18   # Drop 1, r1=bonus, r6=base

# Comparaciones finales sin anillo
break *0x0803146A
break *0x080314B8

# Comparaciones finales con anillo
break *0x08031464  # r0=r6+16
break *0x080314AE  # r0=r6+32

continue
# En el breakpoint relevante:
info registers r0 r1 r2 r4 r6 pc
x/5i $pc
```

Para nivel 13 **simulado** con Lucky Charm: fijar `level=13` (si se desea) y poner `TOTAL_LCK=47` **al detenerse en `0x087FFE80` o `0x087FFF00`**, justo antes de la lectura. No modificar `r1` si se pretende validar el cálculo. Para Rare Ring solo, `TOTAL_LCK=37` en nivel 13 simulado.

Para comprobar drops exitosos en esta variante, usar los puntos de comparación correspondientes al equipo: con anillo `0x08031464` / `0x080314AE` (`cmp r4,r0`); sin anillo `0x0803146A` / `0x080314B8` (`cmp r4,r6`). Forzar `r4=0` en la comparación deseada; para llegar a Drop 1, forzar primero fallo del raro (`r4=1023`). Registrar objeto generado y ausencia de efectos secundarios. **Estas pruebas siguen pendientes para el parche actual.**

## 7. Precauciones técnicas para mantenimiento

1. **No regresar dentro del tramo sobrescrito.** No regresar a direcciones dentro de los trampolines de 10 bytes: se podrían ejecutar literales como instrucciones y alterar el flujo.
2. **Alineación THUMB y literales PC-relative.** Comprobar con desensamblado cada `ldr` y la palabra que carga, incluida la dirección de retorno. Los destinos de `bx` deben tener bit THUMB activado.
3. **Conservación de `lr` y registros.** Al llamar a la comprobación vanilla de equipo, verificar el retorno al stub y el destino final. No considerar correcto un script solo porque el Python compile.
4. **No confundir rutas del anillo.** En la variante vigente hay que volver a `0x08031460`/`0x080314AA` **si el anillo está equipado** para conservar +16/+32; y a `0x0803146A`/`0x080314B6` **si no lo está**. La instrucción de `adds r6,r6,r1` ya añadió el bonus LCK antes de la bifurcación.
5. **Conservar la estadística original del Rare Ring.** El anillo no suma LCK: aplica sus bonus especiales a los umbrales de drop.
6. **Registro `r1` después del retorno.** Puede estar sobrescrito por el juego (`0x300` en comparaciones normales). Para leer el bonus observar `0x087FFE98` o `0x087FFF18`.
7. **LCK artificialmente desincronizada.** Cambiar el nivel por GDB no recalcula de forma fiable el atributo. El clamp a cero impide un bonus negativo en el caso observado; no equivale a validar una subida real de nivel.
8. **EXP y estabilidad:** comprobar que Armor Knight concede 11 EXP y que no aparecen bloqueos durante el juego real.
9. **No extrapolar compatibilidad con otros parches.** Revisar solapamiento de offsets, región de ROM, hash, espacio libre, registros y estado de las banderas antes de combinar modificaciones.

## 8. Pruebas pendientes (prioridad)

1. **EXP y estabilidad:** desde partida normal y ROM generada con el script actual, matar varios Armor Knight, confirmar 11 EXP por enemigo, recoger objetos, cambiar de salas y comprobar que no se congela.
2. **Generación de drops con ×0,50:** forzar Field Armor y Potion con GDB y verificar que aparecen correctamente.
3. **Subida de nivel real:** comprobar `TOTAL_LCK - level - 24` antes y después sin manipular RAM; repetir ambos umbrales.
4. **Equipo combinado y cambios de equipo sin GDB:** alternar Lucky Charm y Rare Ring y verificar recalculado estable.
5. **Casos límite:** LCK adicional 0, 1, 2, 3, 4, valores elevados, estados que reducen LCK y posible overflow de aritmética de 16 bits.
6. **Balance estadístico:** si se necesita, muestrear muchas muertes y distinguir probabilidad por tirada de probabilidad efectiva por muerte.

## 9. Convenciones de archivos y estado del desarrollo

El script de referencia utiliza estas variables (el nombre de salida incluye el ratio):

```python
version = "1.0.0"
original_rom = "rom-harmony-usa.gba"
patched_rom = f"rom-harmony-usa-luckyJuste-drop-{version}.gba"
```

El número es una variable técnica; **no implica lanzamiento**. La fuente de verdad de una futura modificación deben ser el script efectivamente aplicado y su desensamblado, más las observaciones GDB reproducibles.
