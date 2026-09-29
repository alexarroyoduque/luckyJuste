# luckyJuste

A patch that makes **Luck (LCK)** affect enemy item drop rates in *Castlevania: Harmony of Dissonance* (Game Boy Advance).

## How to apply the patch

1. Get a clean USA ROM of *Castlevania: Harmony of Dissonance*.
2. [Download luckyJuste.ips](./luckyJuste.ips).
3. [Apply the IPS patch](https://www.romhacking.net/patch/).

The patch is made for this ROM:

```text
Database match: Castlevania - Harmony of Dissonance (USA)
Database: No-Intro: Game Boy Advance (v. 20210227-023848)
File/ROM SHA-1: B90DA0D9BE0B3A0893CD9E2C399056BCF9579E21
```

## What does the patch do?

### Luck equipment

Equipment that increases LCK now also increases enemy item drop rates.

Juste's natural LCK does **not** affect drop rates. Juste starts with 25 LCK at level 1 and naturally gains 1 LCK per level, so the patch removes this natural Luck before calculating the drop bonus:

```text
EXTRA_LCK = (LCK_ATTR - level - 24)
```

To make Luck-focused equipment more useful, the resulting value receives a **1.25× multiplier with integer truncation**:

```text
EXTRA_DROP = EXTRA_LCK + floor(EXTRA_LCK / 4)
```

This is equivalent to approximately:

```text
EXTRA_DROP = EXTRA_LCK × 1.25
```

### Drop calculation

The game generates a random value between `0` and `1023`.

An item drops when:

```text
RNG < BASE_DROP_RATE + EXTRA_DROP
```

The Luck bonus is applied equally to both the normal and rare item drop thresholds.

### Drop order

Each enemy can have a normal item and a rare item.

As in the original game, the **rare item is checked first**. If the rare item drops, the normal item is not evaluated.

### Rare Ring

The **Rare Ring now grants +24 LCK**, which is visible in Juste's stats.

With the patch formula:

```text
EXTRA_LCK = 24
EXTRA_DROP = 24 + floor(24 / 4)
EXTRA_DROP = 30
```

Therefore, the Rare Ring adds **+30 to both item drop thresholds**.

This replaces the original hidden Rare Ring behavior with the new global LCK system.

The Rare Ghost calculation itself is not modified by the patch. Because the Rare Ring now provides +24 LCK, however, equipping it can also contribute to mechanics that use Juste's LCK.

## How does the original game work?

In the original game, **LCK does not affect enemy item drop rates**.

Each enemy has a fixed base drop value for its normal item and another for its rare item.

The **Rare Ring** is handled separately by the original drop routine:

* Rare item: **+16** to the drop threshold.
* Normal item: **+32** to the drop threshold.

These bonuses are hidden and do not modify Juste's displayed LCK.

The game generates a random value between `0` and `1023`. The item drops when the generated value is below the corresponding drop threshold.

The rare item is evaluated first. If it drops, the normal item is not evaluated.

### Rare Ghost

In the original game, LCK is also used by the **Rare Ghost** spawn mechanic.

With less than 80 LCK, the Rare Ghost has a base spawn chance of `1/64` (about `1.56%`). Starting at 80 LCK, additional Luck adds extra `1/64` attempts to the internal calculation:

```text
LCK < 80  -> 1 attempt
LCK 80-89 -> 2 attempts
LCK 90-99 -> 3 attempts
...
```

Because these are additional independent attempts rather than a simple percentage addition, the effective probabilities are approximately:

```text
1 attempt  -> 1.56%
2 attempts -> 3.10%
3 attempts -> 4.61%
```

## Credits
- AlexArroyoDuque
- [Marc Robledo, RomPatcher](https://github.com/marcrobledo/RomPatcher.js)
- [LagoLunatic, DSVania Edit creator](https://www.romhacking.net/community/4318)
- [RomHacking](https://www.romhacking.net)
