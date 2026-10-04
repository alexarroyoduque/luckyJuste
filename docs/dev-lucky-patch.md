# luckyJuste — documentación técnica del parche de LCK y drops

**Juego:** Castlevania: Harmony of Dissonance (GBA - USA)

## 1. Objetivo y comportamiento

`luckyJuste` modifica globalmente las dos ramas de caída de objetos para que la **LCK adicional procedente del equipamiento** aumente el umbral de drop. La LCK natural asociada al nivel de Juste se descuenta antes de calcular el bonus.

La versión documentada aquí corresponde al script `apply-luckyJuste-1.20.py` (versión `1.0.2`). El Rare Ring pasa a otorgar `+24 LCK`.

La rutina vanilla de drops no usa LCK directamente: comprueba de forma especial el Rare Ring y suma `+16` al Drop 2 y `+32` al Drop 1. El parche sustituye esa excepción por una regla general basada en la LCK de equipamiento.

## 2. Direcciones y puntos de parcheo

| Recurso | Dirección GBA | Offset ROM | Descripción |
|---|---:|---:|---|
| LCK actual de Juste | `0x02018558` | — | EWRAM, lectura `uint16` |
| Nivel de Juste | `0x0201877C` | — | EWRAM, lectura `uint8` |
| Drop 2 (raro) | `0x08031456` | `0x031456` | Inicio de los 10 bytes sustituidos |
| Drop 1 (normal) | `0x080314A0` | `0x0314A0` | Inicio de los 10 bytes sustituidos |
| Stub Drop 2 | `0x087FFF80` | `0x7FFF80` | Rutina inyectada |
| Stub Drop 1 | `0x087FFFC0` | `0x7FFFC0` | Rutina inyectada |
| Rare Ring | `0x084B2C0C` | `0x4B2C0C` | Estructura del ítem |
| Luck Stat Rare Ring | — | `0x4B2C15` | Byte `+9`, escrito como `24` (`0x18`) |

Cada stub reserva `0x34` bytes (**52 bytes**). Las zonas `0x7FFF80–0x7FFFB3` y `0x7FFFC0–0x7FFFF3` no se solapan. El script exige que estén rellenas de `0xFF` antes de escribir.

Los bytes vanilla que se esperan en los puntos de inyección son:

```text
Drop 2 @ 0x031456: 79 20 F8 F7 40 F9 00 28 04 D0
Drop 1 @ 0x0314A0: 79 20 F8 F7 1B F9 00 28 05 D0
```

Si no coinciden, el script aborta para evitar aplicar el parche sobre una ROM incorrecta o ya modificada.

## 3. Separación de LCK natural y LCK de equipamiento

Juste comienza en nivel 1 con 25 LCK y su LCK natural aumenta en un punto por nivel. El parche modela esa parte como:

```text
BASE_LUCK = level + 24
EQUIPMENT_LUCK = TOTAL_LUCK - BASE_LUCK
```

En la implementación:

```text
extra_lck = LCK_ATTR - level - 24
```

Por tanto, sin equipo que aporte LCK:

```text
TOTAL_LUCK = level + 24
extra_lck  = 0
```

> La implementación actual no hace clamp a cero. Presupone `TOTAL_LUCK >= level + 24`. Si existiera equipo que redujera la LCK total por debajo de la natural, la resta unsigned podría producir un valor no deseado.

## 4. Fórmula de bonus de drop

La versión actual aproxima **×1,20** mediante operaciones especialmente baratas en ARM7TDMI/THUMB:

```text
extra_drop = extra_lck
           + (extra_lck >> 3)
           + (extra_lck >> 4)
           + (extra_lck >> 6)

drop_threshold = base_drop + extra_drop
```

El factor binario nominal es:

```text
1 + 1/8 + 1/16 + 1/64 = 1.203125
```

Por tanto, se utiliza **×1,203125 nominal como aproximación eficiente a ×1,20**. La expresión exacta ejecutada con enteros es:

```text
extra_drop = x + floor(x/8) + floor(x/16) + floor(x/64)
```

Los tres desplazamientos truncan de forma independiente. Por ello, no debe describirse en general como `floor(x * 1.203125)`: ambas expresiones pueden diferir para determinados valores de `x`.

Ejemplos:

| `x` = LCK de equipo | `x>>3` | `x>>4` | `x>>6` | `extra_drop` |
|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 | 0 |
| 8 | 1 | 0 | 0 | 9 |
| 16 | 2 | 1 | 0 | 19 |
| 24 | 3 | 1 | 0 | **28** |
| 32 | 4 | 2 | 0 | 38 |
| 64 | 8 | 4 | 1 | 77 |

## 5. Conversión a probabilidad

La rutina vanilla trabaja con un espacio efectivo de `1024` resultados (`0..1023`). Para un umbral `T`:

```text
éxito si RNG < T
P = T / 1024
```

Cada unidad añadida al umbral equivale a:

```text
1 / 1024 = 0.09765625 puntos porcentuales
```

Por tanto, `+24 LCK` de equipo produce `extra_drop = 28`, equivalente a un incremento absoluto de:

```text
28 / 1024 = 2.734375 puntos porcentuales
```

El mismo `extra_drop` se suma a Drop 2 y Drop 1. La probabilidad global de Drop 1 por muerte sigue condicionada al fallo previo de Drop 2.

## 6. Rare Ring: vanilla frente al parche

En la ROM original:

```text
Drop 2 (raro):   base + 16
Drop 1 (normal): base + 32
```

El parche reemplaza las instrucciones que realizaban esa comprobación especial y modifica el byte de LCK del Rare Ring para que otorgue `+24 LCK`. Con la fórmula actual:

```text
extra_lck  = 24
extra_drop = 24 + (24 >> 3) + (24 >> 4) + (24 >> 6)
           = 24 + 3 + 1 + 0
           = 28
```

Por tanto:

| Sistema | Drop 2 | Drop 1 |
|---|---:|---:|
| Vanilla + Rare Ring | `base + 16` | `base + 32` |
| luckyJuste actual + Rare Ring | **`base + 28`** | **`base + 28`** |

El diseño queda casi centrado entre los dos bonus vanilla y, además, extiende el efecto a cualquier pieza que aporte LCK. Como efecto secundario deliberado, el `+24 LCK` del Rare Ring modifica la estadística real de Juste y puede afectar a otras mecánicas vanilla que consulten LCK.

## 7. Trampolines THUMB

En cada punto se sustituyen exactamente 10 bytes por un trampoline que carga la dirección del stub y salta mediante `bx r0`. El bit 0 de la dirección destino se fija a `1` para indicar ejecución THUMB.

Los dos puntos de parcheo tienen distinta alineación, por lo que el script genera dos disposiciones posibles para mantener el literal de 32 bits alineado a 4 bytes:

```asm
; patch_offset % 4 == 2
nop
ldr r0, [pc, #0]
bx  r0
.word target

; patch_offset % 4 == 0
ldr r0, [pc, #0]
bx  r0
.word target
nop
```

Esto evita el problema de un `LDR` literal desalineado, que podría interpretar incorrectamente la dirección de salto.

Las direcciones de retorno son:

```text
Drop 2: 0x08031461
Drop 1: 0x080314AB
```

Incluyen el bit THUMB.

## 8. Rutina inyectada

Pseudocódigo:

```text
extra_lck = *(uint16*)0x02018558
extra_lck -= *(uint8*)0x0201877C
extra_lck -= 24

original = extra_lck
extra_lck += original >> 3
extra_lck += original >> 4
extra_lck += original >> 6

r6 += extra_lck
return
```

Assembly equivalente:

```asm
ldr  r0, =0x02018558
ldrh r1, [r0]
ldr  r0, =0x0201877C
ldrb r0, [r0]
subs r1, r1, r0
subs r1, #24
movs r2, r1
movs r0, r2
lsrs r0, r0, #3
adds r1, r1, r0
movs r0, r2
lsrs r0, r0, #4
adds r1, r1, r0
movs r0, r2
lsrs r0, r0, #6
adds r1, r1, r0
adds r6, r6, r1
ldr  r0, =return_addr
bx   r0
```

`r2` conserva el `extra_lck` original para que los tres shifts se calculen sobre `x`, no sobre el acumulador ya incrementado. El código termina con un `nop` de alineación antes de los tres literales de 32 bits.

## 9. Layout de los stubs y breakpoints útiles

Cada stub contiene 40 bytes de código/padding y 12 bytes de literales, totalizando **52 bytes (`0x34`)**.

| Operación | Drop 2 | Drop 1 |
|---|---:|---:|
| Entrada stub | `0x087FFF80` | `0x087FFFC0` |
| `lsrs r0,#3` | `0x087FFF90` | `0x087FFFD0` |
| primera suma | `0x087FFF92` | `0x087FFFD2` |
| `lsrs r0,#4` | `0x087FFF96` | `0x087FFFD6` |
| segunda suma | `0x087FFF98` | `0x087FFFD8` |
| `lsrs r0,#6` | `0x087FFF9C` | `0x087FFFDC` |
| tercera suma | `0x087FFF9E` | `0x087FFFDE` |
| `adds r6,r6,r1` | `0x087FFFA0` | `0x087FFFE0` |

Los literales empiezan en `+0x28`: LCK en `+0x28`, nivel en `+0x2C` y dirección de retorno en `+0x30`.

## 10. Pruebas y verificaciones automáticas del script

Antes de escribir, el script verifica:

1. que la ROM tenga al menos `0x800000` bytes;
2. que los 10 bytes originales de Drop 2 coincidan exactamente;
3. que los 10 bytes originales de Drop 1 coincidan exactamente;
4. que los 52 bytes reservados para cada stub sean `0xFF`;
5. que cada trampoline mida exactamente 10 bytes;
6. que cada stub mida exactamente `0x34` bytes.

Si cualquiera de estas condiciones falla, el parche aborta con una excepción en lugar de escribir parcialmente sobre una ROM inesperada.

Ejecución:

```bash
python apply-luckyJuste-1.20.py
```

Salida esperada relevante:

```text
[+] Reading original ROM: rom-harmony-usa.gba
[+] DROP 2 -> stub 0x7FFF80 / GBA 0x087FFF81
[+] DROP 1 -> stub 0x7FFFC0 / GBA 0x087FFFC1
[+] Rare Ring: +24 LCK (offset 0x4B2C15)
[OK] Patched ROM: 'rom-harmony-usa-luckyJuste-1.0.2.gba'
```

## 11. Validación con GDB/mGBA

Conexión típica:

```bash
arm-none-eabi-gdb \
  -ex "target remote localhost:2345" \
  -ex "set architecture armv4t" \
  -ex "set arm force-mode thumb"
```

### 11.1 Caso de control: sin LCK de equipamiento

A nivel 1, sin equipo de LCK:

```text
TOTAL_LUCK = 25
level      = 1
extra_lck  = 25 - 1 - 24 = 0
extra_drop = 0
```

El valor de `r6` debe permanecer igual después de `adds r6,r6,r1`. El mismo razonamiento vale a nivel `N` cuando `TOTAL_LUCK = N + 24`.

### 11.2 Rare Ring (+24 LCK)

El resultado esperado antes de sumar a `r6` es:

```text
extra_lck = 24
24 >> 3   = 3
24 >> 4   = 1
24 >> 6   = 0
extra_drop = 28
```

Breakpoints recomendados:

```gdb
# Drop 2
break *0x087FFF90   # >> 3
break *0x087FFF96   # >> 4
break *0x087FFF9C   # >> 6
break *0x087FFFA0   # suma final a r6

# Drop 1
break *0x087FFFD0   # >> 3
break *0x087FFFD6   # >> 4
break *0x087FFFDC   # >> 6
break *0x087FFFE0   # suma final a r6
```

En el primer shift, `r1` y `r2` deben valer `24`. Después de `>>3`, `r0` debe valer `3`; después de `>>4`, `1`; después de `>>6`, `0`; y antes de la suma final, `r1` debe valer `28`.

Para registrar el incremento final:

```gdb
set $drop_before = $r6
si
p/u $r6
p/d $r6 - $drop_before
```

El resultado esperado es `+28`.

### 11.3 Armor Knight como caso reproducible

Umbrales vanilla usados en el estudio:

```text
Drop 2 — Field Armor: 8
Drop 1 — Potion:      16
```

Con Rare Ring y el parche actual, los resultados esperados son:

```text
Drop 2: 8  + 28 = 36  -> 36/1024 = 3.515625%
Drop 1: 16 + 28 = 44  -> 44/1024 = 4.296875% (tirada individual)
```

La probabilidad global del Potion por muerte es:

```text
P(Drop 1) = (1 - 36/1024) * (44/1024)
          ≈ 4.145813%
```

### 11.4 Estado de la evidencia

Las pruebas GDB históricas con `24 >> 2 = 6`, `extra_drop = 30`, `8 -> 38` y `16 -> 46` corresponden a la versión anterior **×1,25**. Validan la arquitectura general del parche y la separación `LCK - level - 24`, pero no son una validación dinámica de esta versión.

La versión actual **aprox. ×1,20** debe validarse observando en ejecución `3`, `1`, `0`, `28`, `36` y `44`. Hasta realizar esa sesión GDB, esos valores se documentan como resultados esperados derivados directamente del código del script.

## 12. Comparación matemática y de balance

Para `+24 LCK`:

| Sistema | Bonus Drop 2 | Bonus Drop 1 |
|---|---:|---:|
| Rare Ring vanilla | +16 | +32 |
| luckyJuste anterior ×1,25 | +30 | +30 |
| luckyJuste actual aprox. ×1,20 | **+28** | **+28** |

La versión actual usa un factor binario nominal ×1,203125, muy próximo a ×1,20, manteniendo una implementación barata para ARM7TDMI: tres desplazamientos y tres sumas sobre el valor base, sin división general ni coma flotante.

## 13. Resumen de la fórmula implementada

```text
BASE_LUCK      = level + 24
EQUIPMENT_LUCK = TOTAL_LUCK - BASE_LUCK

EXTRA_DROP = EQUIPMENT_LUCK
           + floor(EQUIPMENT_LUCK / 8)
           + floor(EQUIPMENT_LUCK / 16)
           + floor(EQUIPMENT_LUCK / 64)

DROP_THRESHOLD = BASE_DROP + EXTRA_DROP
P(tirada)      = DROP_THRESHOLD / 1024
```

Para el Rare Ring:

```text
EQUIPMENT_LUCK = 24
EXTRA_DROP     = 28
```

Esta es la fórmula de referencia para documentar y probar `apply-luckyJuste-1.20.py` / luckyJuste `1.0.2`.
