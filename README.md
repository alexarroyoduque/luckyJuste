# luckyJuste

In the original *Castlevania: Harmony of Dissonance* (Game Boy Advance), LCK has no effect on either mechanic, making Luck-boosting equipment largely ineffective.

**luckyJuste** fixes this by making LCK gained from equipment increase both normal and rare item drop rates, as well as critical hit chances. Only equipment bonuses count; LCK naturally gained through leveling is excluded.

[Drop calculator](https://harmony-of-dissonance-drop.web.app/).

## How to apply

There are two patches, you can use one of them or both.

1. Get a clean USA ROM of *Castlevania: Harmony of Dissonance*.
2. [Download luckyJuste-drop.ips](./luckyJuste-drop.ips).
3. [Download luckyJuste-critical.ips](./luckyJuste-critical.ips).
4. [Apply the IPS patch](https://www.romhacking.net/patch/).

```text
Database match: Castlevania - Harmony of Dissonance (USA)
Database: No-Intro: Game Boy Advance (v. 20210227-023848)
File/ROM SHA-1: B90DA0D9BE0B3A0893CD9E2C399056BCF9579E21
File/ROM CRC32: 88C1B562
```

## luckyJuste-drop

### What does it change?

In the original game, enemy drop rates use fixed values. The Rare Ring is handled as a special case, providing a hidden `+16` bonus to rare drops and `+32` to normal drops.

With luckyJuste, **LCK gained from equipment increases both normal and rare item drop rates**.

Juste's natural LCK from leveling is excluded:

```text
EQUIPMENT_LUCKY = (LCK_ATTR - level - 24) * ratio
```
ratio = `0.75`

The final drop check becomes:

```text
RNG < BASE_DROP_RATE + EXTRA_DROP
```

The game uses an RNG range of `0–1023`, so each point added to the drop threshold represents `1/1024` of the probability space. As in the original game, the rare item is checked first. If it drops, the normal item is not evaluated.

#### Rare Ring

The patch does **not** modify the Rare Ring hidden bonus.

#### Rare Ghost

The patch does **not** modify the Rare Ghost routine.

## luckyJuste-critical

### What does it change?

`CRITICAL_CHANCE = 6.25 + EQUIPMENT_LUCKY*0,15 + LEVEL_BONUS`

- The base chance is 4096/65536 = 6.25%, similar to the original game.
- The luck of the equip increases the critical chance.
- Each 10 level difference between Juste and its enemy adds 1% to the critical chance, up to a maximum of 4%.
- Only one roll is performed. In the original game, if Juste equips "Platinum Tip" a second random roll of 1/64 = 1.56% is performed.
- Why is the scaling factor 0.15? Because in the original game there is hidden behavior in how "Lucky Charm" and "Lucky Ring" increase critical chance. Through calculations, "Lucky Charm" which grants +10 luck and "Lucky Ring" which grants +20 luck achieve a hidden critical rate of 7168/65536 = 10.94% in the game. The 0.15 factor respects that hidden scaling but with the new system affects any item that grants luck.


## Credits

* AlexArroyoDuque
* -SuXei999- - testing and qualiy
* [Marc Robledo — RomPatcher.js](https://github.com/marcrobledo/RomPatcher.js)
* [LagoLunatic — DSVania Editor](https://www.romhacking.net/community/4318)
* [Zach Keene — Level stats](https://gamefaqs.gamespot.com/gba/554981-castlevania-harmony-of-dissonance/faqs/17440)
* [Romhacking.net](https://www.romhacking.net)
