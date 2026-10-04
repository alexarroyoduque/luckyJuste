# luckyJuste

A patch that makes **Luck (LCK)** affect enemy item drop rates in *Castlevania: Harmony of Dissonance* (Game Boy Advance).

In the original game, **LCK has no effect on enemy item drop rates**. Equipping Luck-boosting gear does not improve your chances of getting normal or rare item drops.

**luckyJuste fixes this by making LCK gained from equipment increase the drop rate of both normal and rare items**, while excluding the LCK Juste naturally gains from leveling.

[Drop calculator](https://harmony-of-dissonance-drop.web.app/).

## How to apply

1. Get a clean USA ROM of *Castlevania: Harmony of Dissonance*.
2. [Download luckyJuste.ips](./luckyJuste.ips).
3. [Apply the IPS patch](https://www.romhacking.net/patch/).

Compatible ROM:

```text
Castlevania - Harmony of Dissonance (USA)
SHA-1: B90DA0D9BE0B3A0893CD9E2C399056BCF9579E21
```

## What does it change?

In the original game, enemy drop rates use fixed values. The Rare Ring is handled as a special case, providing a hidden `+16` bonus to rare drops and `+32` to normal drops.

With luckyJuste, **LCK gained from equipment increases both normal and rare item drop rates**.

Juste's natural LCK from leveling is excluded:

```text
EXTRA_LCK = LCK_ATTR - level - 24
```

Luck equipment receives an efficient approximation of a **1.20× scaling bonus** using integer arithmetic:

```text
EXTRA_DROP = EXTRA_LCK
           + floor(EXTRA_LCK / 8)
           + floor(EXTRA_LCK / 16)
           + floor(EXTRA_LCK / 64)
```

The nominal binary factor is `1.203125×`. Each division is truncated independently.

The final drop check becomes:

```text
RNG < BASE_DROP_RATE + EXTRA_DROP
```

The game uses an RNG range of `0–1023`, so each point added to the drop threshold represents `1/1024` of the probability space. As in the original game, the rare item is checked first. If it drops, the normal item is not evaluated.

### Rare Ring

The **Rare Ring now grants +24 LCK**, visible in Juste's stats.

With the patch formula:

```text
24 LCK -> 24 + 3 + 1 + 0 = +28 drop threshold
```

This bonus applies to both normal and rare items, replacing the original hidden Rare Ring behavior with the global LCK system.

### Rare Ghost

The patch does **not** modify the Rare Ghost routine.

Rare Ghost already uses LCK in the original game, so the Rare Ring's new `+24 LCK` can also improve its spawn rolls when it crosses the relevant LCK thresholds.

## Credits

* AlexArroyoDuque
* [Marc Robledo — RomPatcher.js](https://github.com/marcrobledo/RomPatcher.js)
* [LagoLunatic — DSVania Editor](https://www.romhacking.net/community/4318)
* [Zach Keene — Level stats](https://gamefaqs.gamespot.com/gba/554981-castlevania-harmony-of-dissonance/faqs/17440)
* [Romhacking.net](https://www.romhacking.net)
