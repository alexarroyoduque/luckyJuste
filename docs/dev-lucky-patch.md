# Parche Global de Suerte de Equipamiento (LCK Drop Scaling)

**Juego:** Castlevania: Harmony of Dissonance (GBA - USA)

**Descripción:** Modificación global del sistema de drops que añade al umbral de caída únicamente la Suerte (LCK) adicional de Juste procedente del equipamiento. La suerte natural asociada a su nivel se descuenta y la LCK adicional de equipamiento se escala con un multiplicador ×1,25 implementado mediante aritmética entera con truncado.

## 1. Posiciones de Memoria Clave

| Recurso / Función | Dirección GBA | Offset ROM | Valor / Tipo | Descripción |
|---|---|---|---|---|
| Suerte actual de Juste (LCK) | `0x02018558` | — | EWRAM (`uint16`) | Dirección que almacena la Suerte actual, incluido el efecto del equipamiento. |
| Nivel de Juste | `0x0201877C` | — | EWRAM (`uint8`) | Dirección que almacena el nivel actual. |
| Drop 2 (Objeto Raro) | `0x08031456` | `0x031456` | Código THUMB | Punto de inyección del trampoline para objetos raros. |
| Drop 1 (Objeto Normal) | `0x080314A0` | `0x0314A0` | Código THUMB | Punto de inyección del trampoline para objetos normales. `0x03149E` corresponde a la instrucción anterior y no debe sobrescribirse. |
| Stub Drop 2 | `0x087FFF80` | `0x7FFF80` | Código THUMB | Rutina inyectada para el drop raro. |
| Stub Drop 1 | `0x087FFFC0` | `0x7FFFC0` | Código THUMB | Rutina inyectada para el drop normal. |

Las rutinas ampliadas ocupan 36 bytes cada una. Se alojan en espacio libre al final de la ROM: Drop 2 en `0x7FFF80` y Drop 1 en `0x7FFFC0`. El script comprueba previamente que las zonas destinadas a los stubs contienen `0xFF`.

## 2. Cálculo de Probabilidad

El parche separa primero la LCK natural de Juste de la LCK obtenida mediante equipamiento:

```text
extra_lck = LCK - level - 24
```

Juste comienza en nivel 1 con 25 puntos de LCK y obtiene 1 punto natural de LCK por nivel. Por tanto:

```text
natural_LCK = level + 24
extra_lck   = total_LCK - natural_LCK
```

A continuación se aplica un multiplicador **×1,25 con truncado entero**:

Formula completa: `EXTRA_DROP = (LCK_ATTR - level - 24)*ratio`

```text
extra_drop = extra_lck + (extra_lck >> 2)
```

El desplazamiento `>> 2` equivale a una división entera entre 4:

```text
extra_drop = extra_lck + floor(extra_lck / 4)
```

Por tanto, la fórmula completa es:

```text
extra_lck  = LCK - level - 24
extra_drop = extra_lck + floor(extra_lck / 4)
```

Esto implementa aproximadamente:

```text
extra_drop = floor(extra_lck × 1.25)
```

sin utilizar coma flotante ni una multiplicación general en ARM7TDMI.

Ejemplos:

| LCK adicional | `LCK >> 2` | `extra_drop` |
|---:|---:|---:|
| 0 | 0 | 0 |
| 4 | 1 | 5 |
| 8 | 2 | 10 |
| 16 | 4 | 20 |
| 24 | 6 | 30 |
| 32 | 8 | 40 |

El umbral usado por la rutina pasa a ser conceptualmente:

$$\text{Éxito} \iff \text{RNG} < (\text{Probabilidad Base} + \text{extra\_drop})$$

Si la tirada está en el rango `0..1023`, cada unidad de `extra_drop` representa `1/1024` del espacio de resultados.

> **Importante:** la versión actual no aplica un clamp a cero. Se asume que `LCK >= level + 24`. Si existiera equipamiento capaz de reducir la LCK total por debajo de la LCK natural, sería recomendable añadir una protección equivalente a `max(0, LCK - level - 24)` antes de aplicar el multiplicador.

## 3. Pruebas de Validación en GDB

El objetivo de estas pruebas es comprobar dinámicamente que:

1. la LCK natural se elimina mediante `LCK - level - 24`;
2. el Rare Ring aporta `+24 LCK`;
3. el multiplicador ×1,25 transforma esos 24 puntos en `+30` de `extra_drop`;
4. el mismo bonus se aplica correctamente a Drop 2 y Drop 1.

Conexión de ejemplo:

```bash
arm-none-eabi-gdb \
  -ex "target remote localhost:2345" \
  -ex "set architecture armv4t" \
  -ex "set arm force-mode thumb"
```

### 3.1 Breakpoints del multiplicador

Para observar el cálculo `extra_lck + (extra_lck >> 2)` se utilizaron:

```text
Drop raro:   0x087FFF8E
Drop normal: 0x087FFFCE
```

En ambos puntos, la instrucción actual es:

```asm
lsrs r0, r0, #2
```

y `r1` ya contiene la LCK adicional calculada.

### 3.2 Validación del Drop 2 — raro

Con el Rare Ring equipado:

```gdb
break *0x087FFF8E
continue
```

Valores observados al alcanzar el breakpoint:

```text
r6 = 8
r1 = 24
PC = 0x087FFF8E: lsrs r0, r0, #2
```

Esto confirma que antes del multiplicador:

```text
extra_lck = 24
```

Ejecutando una instrucción:

```gdb
si
p/u $r0
x/i $pc
```

Resultado observado:

```text
r0 = 6
PC = 0x087FFF90: adds r1, r1, r0
```

Por tanto:

```text
24 >> 2 = 6
```

Ejecutando la suma:

```gdb
si
p/u $r1
x/i $pc
```

Resultado observado:

```text
r1 = 30
PC = 0x087FFF92: adds r6, r6, r1
```

Por tanto:

```text
extra_drop = 24 + 6 = 30
```

Finalmente:

```gdb
set $drop_before = $r6
si
p/u $r6
p/d $r6 - $drop_before
```

Resultado observado:

```text
r6 = 38
r6 - drop_before = 30
```

La rama rara queda validada:

```text
Drop 2 base = 8
extra_lck   = 24
extra_drop  = 30
umbral final = 8 + 30 = 38
```

### 3.3 Validación del Drop 1 — normal

Con el Rare Ring equipado:

```gdb
break *0x087FFFCE
continue
```

Valores observados:

```text
r6 = 16
r1 = 24
PC = 0x087FFFCE: lsrs r0, r0, #2
```

Después del desplazamiento:

```text
r0 = 6
PC = 0x087FFFD0: adds r1, r1, r0
```

Después de la suma:

```text
r1 = 30
PC = 0x087FFFD2: adds r6, r6, r1
```

Finalmente se guardó el umbral base y se ejecutó la suma:

```gdb
set $drop_before = $r6
si
p/u $r6
p/d $r6 - $drop_before
```

Resultado observado:

```text
r6 = 46
r6 - drop_before = 30
```

La rama normal queda validada:

```text
Drop 1 base = 16
extra_lck   = 24
extra_drop  = 30
umbral final = 16 + 30 = 46
```

### 3.4 Resultado experimental

| Drop | Umbral base (`r6`) | LCK adicional (`r1`) | `>> 2` | `extra_drop` | Umbral final |
|---|---:|---:|---:|---:|---:|
| Drop 2 — raro | 8 | 24 | 6 | **30** | **38** |
| Drop 1 — normal | 16 | 24 | 6 | **30** | **46** |

Las dos ramas confirman dinámicamente la fórmula:

```text
extra_lck  = 24
extra_drop = 24 + (24 >> 2)
           = 24 + 6
           = 30
```

### 3.5 Prueba sin equipamiento de LCK

La comprobación complementaria consiste en ejecutar el parche sin ningún objeto que aporte LCK.

A nivel 1:

```text
LCK       = 25
level     = 1
extra_lck = 25 - 1 - 24 = 0
extra_drop = 0 + (0 >> 2) = 0
```

Por tanto, el umbral debe permanecer sin cambios.

A cualquier otro nivel `N`, si Juste únicamente posee su LCK natural:

```text
LCK = N + 24

extra_lck = (N + 24) - N - 24 = 0
```

El multiplicador no altera este resultado:

```text
extra_drop = 0 + (0 >> 2) = 0
```

## 4. Modificación del Rare Ring (ID 121 / `0x79`)

### 4.1 Comportamiento original vs. nuevo comportamiento

#### Comportamiento original

El código original comprueba el objeto con ID `121` (`0x79`, Rare Ring) en **ambas ramas de drop**.

En la rama de Drop 2 (objeto raro), el código original contiene el equivalente a:

```asm
movs r0, #0x79
bl   <comprobar objeto>
cmp  r0, #0
beq  <sin bonus>
movs r0, r6
adds r0, #16
cmp  r4, r0
```

Por tanto, el Rare Ring original añade **+16** al umbral de la rama de objeto raro.

En la rama de Drop 1 (objeto normal), el código equivalente es:

```asm
movs r0, #0x79
bl   <comprobar objeto>
cmp  r0, #0
beq  <sin bonus>
movs r0, r6
adds r0, #32
cmp  r4, r0
```

Por tanto, el Rare Ring original añade **+32** al umbral de la rama de objeto normal.

#### Por qué se modifica el Rare Ring

Los puntos de inyección del parche sustituyen precisamente las instrucciones que implementaban esa comprobación del Rare Ring. Para conservar un efecto de suerte asociado al objeto sin mantener una comprobación especial dentro de la rutina de drops, se modifica directamente su estadística de LCK.

#### Nuevo comportamiento

El atributo de estadísticas del Rare Ring se modifica para que otorgue:

```text
+24 LCK
```

La LCK total se almacena en `0x02018558`. Las nuevas rutinas calculan:

```text
extra_lck  = LCK - level - 24
extra_drop = extra_lck + (extra_lck >> 2)
```

A nivel 1:

```text
Sin Rare Ring:
LCK = 25
extra_lck = 25 - 1 - 24 = 0
extra_drop = 0

Con Rare Ring:
LCK = 49
extra_lck = 49 - 1 - 24 = 24
extra_drop = 24 + (24 >> 2)
           = 24 + 6
           = 30
```

El Rare Ring nuevo añade así **+30 al umbral efectivo de Drop 1 y Drop 2** mediante sus `+24 LCK` y el multiplicador ×1,25.

> **Cambio de balance respecto al juego original:** vanilla aplica `+16` al Drop 2 y `+32` al Drop 1. El nuevo sistema aplica `+30` a ambos. Por tanto, aumenta el efecto sobre el drop raro respecto a vanilla (`+16 → +30`) y reduce ligeramente el efecto sobre el drop normal (`+32 → +30`).

---

### 4.2 Datos de estructura de memoria (DSvania Editor)

Según la estructura identificada mediante DSvania Editor:

- **Puntero / dirección del Rare Ring:** `0x084B2C0C` (offset ROM `0x4B2C0C`).
- **Tamaño de la estructura del ítem:** 12 bytes (`0x0C`).
- **Campo modificado:** offset `+9` de la estructura (`Luck Stat`).
- **Ubicación exacta en ROM:** `0x4B2C0C + 9 = 0x4B2C15`.
- **Nuevo valor:** `24` (`0x18`).

## 5. Escalado y equivalencia matemática de la LCK adicional

El multiplicador no utiliza coma flotante. Para una cantidad `x` de LCK adicional:

```text
extra_drop = x + floor(x / 4)
```

Esto equivale a un ×1,25 truncado.

Si el RNG efectivo está en `0..1023`, cada unidad añadida al umbral equivale a:

$$\frac{1}{1024}\times100 = 0.09765625\text{ puntos porcentuales}$$

La relación entre LCK adicional y probabilidad deja de ser exactamente 1:1 debido al multiplicador.

        1  × 1.25 = 1.25  → 1
        2  × 1.25 = 2.50  → 2
        3  × 1.25 = 3.75  → 3
        4  × 1.25 = 5.00  → 5
        5  × 1.25 = 6.25  → 6

### 5.1 Tabla de impacto

| LCK adicional | `floor(LCK/4)` | `extra_drop` | Incremento absoluto del umbral |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 0 pp |
| 1 | 0 | 1 | 0.09765625 pp |
| 4 | 1 | 5 | 0.48828125 pp |
| 8 | 2 | 10 | 0.9765625 pp |
| 10 | 2 | 12 | 1.171875 pp |
| 16 | 4 | 20 | 1.953125 pp |
| **24 (Rare Ring)** | **6** | **30** | **2.9296875 pp** |
| 32 | 8 | 40 | 3.90625 pp |


La LCK natural de Juste no debe incluirse como LCK adicional porque queda anulada por `level + 24`.

A nivel 1:

| Estado | LCK total | `extra_lck` | `extra_drop` |
|---|---:|---:|---:|
| Sin equipo de LCK | 25 | 0 | 0 |
| Rare Ring (+24) | 49 | 24 | **30** |

---

## 6. Ejemplo práctico — Armor Knight

Para Armor Knight se utilizaron los siguientes umbrales base:

```text
Drop 2 — Field Armor: 8 / 1024
Drop 1 — Potion:     16 / 1024
```

### 6.1 Sin equipamiento de LCK

```text
extra_lck  = 0
extra_drop = 0

Drop 2: 8 + 0  = 8
Drop 1: 16 + 0 = 16
```

Tasas de las tiradas individuales:

```text
Drop 2: 8 / 1024  = 0.78125%
Drop 1: 16 / 1024 = 1.5625%
```

### 6.2 Con Rare Ring (+24 LCK)

El multiplicador produce:

```text
extra_lck  = 24
extra_drop = 24 + floor(24 / 4)
           = 24 + 6
           = 30
```

Por tanto:

```text
Drop 2: 8 + 30  = 38
Drop 1: 16 + 30 = 46
```

Tasas de las tiradas individuales:

$$P(\text{Drop 2}) = \frac{38}{1024} = 3.7109375\%$$

$$P(\text{Drop 1} \mid \text{se evalúa Drop 1}) = \frac{46}{1024} = 4.4921875\%$$

Incrementos absolutos respecto a las tiradas base:

```text
Drop 2: +30/1024 = +2.9296875 puntos porcentuales
Drop 1: +30/1024 = +2.9296875 puntos porcentuales
```

> **Nota:** Drop 2 se evalúa antes que Drop 1. Por ello, `46/1024` describe la probabilidad de éxito de la tirada de Drop 1 una vez alcanzada esa rama, no necesariamente la probabilidad global por muerte de obtener el objeto normal.

---

## 7. Comparación con el Rare Ring vanilla

Las pruebas realizadas previamente sobre la ROM original confirmaron:

| Sistema | Drop 2 — raro | Drop 1 — normal |
|---|---:|---:|
| Sin Rare Ring | base | base |
| Rare Ring vanilla | base +16 | base +32 |
| **Parche actual: Rare Ring +24 LCK, ×1,25** | **base +30** | **base +30** |

Para Armor Knight:

| Sistema | Field Armor | Potion (tirada individual) |
|---|---:|---:|
| Base | `8/1024` | `16/1024` |
| Rare Ring vanilla | `24/1024` | `48/1024` |
| **Parche actual** | **`38/1024`** | **`46/1024`** |

El nuevo diseño sustituye la excepción específica del Rare Ring por una regla general:

```text
LCK de equipamiento
        ↓
extra_lck = LCK - level - 24
        ↓
extra_drop = extra_lck + floor(extra_lck / 4)
        ↓
se añade el mismo extra_drop a ambos umbrales
```

Con `+24 LCK`, el Rare Ring queda muy próximo a su bonus vanilla del drop normal (`+30` frente a `+32`) y aumenta de forma más notable su efecto sobre el drop raro (`+30` frente a `+16`).

---

## 8. Estado de validación

La implementación actual ha sido comprobada dinámicamente con GDB usando Armor Knight y el Rare Ring equipado.

Resultados observados:

```text
DROP 2
r6 inicial = 8
extra_lck  = 24
24 >> 2    = 6
extra_drop = 30
r6 final   = 38

DROP 1
r6 inicial = 16
extra_lck  = 24
24 >> 2    = 6
extra_drop = 30
r6 final   = 46
```

Esto valida experimentalmente que:

1. el Rare Ring aporta `+24 LCK`;
2. el cálculo intermedio obtiene `extra_lck = 24`;
3. el desplazamiento `>> 2` produce `6`;
4. el multiplicador truncado produce `extra_drop = 30`;
5. Drop 2 pasa de `8` a `38`;
6. Drop 1 pasa de `16` a `46`.

La fórmula implementada y observada en ejecución es:

```text
extra_lck  = LCK_ATTR - level - 24
extra_drop = extra_lck + (extra_lck >> 2)
drop       = drop + extra_drop
```
