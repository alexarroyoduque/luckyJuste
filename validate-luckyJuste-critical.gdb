# luckyJuste critical linear stub 132 bytes -- generic passive trace
# Verified addresses from critical-linear-stub.o (offset 0x087FFD00).
# No hardcoded bonus coefficient or phases. Every tenth impact forces primary crit.
# The equipment item IDs are not decoded: LCK and Platinum flag are observed.
# To prove same-LCK equipment equivalence, change gear in-game and compare logs.
# Start in a fresh GDB session after connecting to mGBA:
#   set architecture armv4t
#   set arm force-mode thumb
#   source validate-luckyJuste-critical.gdb
# End: Ctrl+C ; set logging enabled off
set pagination off
set confirm off
set logging file luckyJuste-critical-validation.log
set logging overwrite on
set logging redirect off
set logging enabled on

set $n=0
set $ret=0
set $dmg=0
set $secondary=0
set $old_secondary=0
set $last_lck=-1
set $last_level=-1
set $last_plat=-1
set $atk=0
set $plat=0
set $x=0
set $threshold=0
set $natural=0
set $used=0
set $primary=0
set $secondary_seen=0
set $secondary_success=0
set $result=0
set $before=0
set $violations=0
set $forced=0
set $forced_plat=0

printf "\n=== luckyJuste critical | generic linear-stub trace ===\n"
printf "Address map: entry=0x087FFD00 threshold=0x087FFD2A primary_cmp=0x087FFD38 secondary_start=0x087FFD54 secondary_mask=0x087FFD58\n"
printf "No assumed ratio. Every 10th hit forces primary RNG=0. Log keeps natural RNG.\n"
printf "No phase labels needed. Equip/desequip gear normally.\n"

break *0x087FFD00
commands
 silent
 set $n=$n+1
 set $atk=$r0
 set $level=*(unsigned char*)0x0201877c
 set $luck=*(unsigned short*)0x02018558
 set $x=(int)$luck-(int)$level-24
 if $x<0
   set $x=0
 end
 set $plat=(*(unsigned int*)0x02018528 & 0x80)
 set $secondary_seen=0
 set $secondary_success=0
 if $luck!=$last_lck || $level!=$last_level || $plat!=$last_plat
   printf "[CHANGE] hit=%u level=%u total_lck=%u equipment_lck=%d platinum_bit=0x%x\n",$n,$level,$luck,$x,$plat
 end
 set $last_lck=$luck
 set $last_level=$level
 set $last_plat=$plat
 printf "[ENTRY %u] attack_id=%u level=%u total_lck=%u equipment_lck=%d platinum=0x%x\n",$n,$atk,$level,$luck,$x,$plat
 continue
end

break *0x087FFD2A
commands
 silent
 set $threshold=$r6
 printf "[THRESH %u] threshold=%u bonus_units=%d equipment_lck=%d\n",$n,$r6,(int)$r6-4096,$x
 continue
end

break *0x087FFD38
commands
 silent
 set $natural=$r0
 if ($n%10)==0
   set $r0=0
   set $forced=$forced+1
   if $plat!=0
     set $forced_plat=$forced_plat+1
   end
 end
 set $used=$r0
 set $primary=($used<$r6)
 printf "[PRIMARY %u] natural=%u used=%u threshold=%u success=%u forced=%u platinum=0x%x attack_id=%u\n",$n,$natural,$used,$r6,$primary,(($n%10)==0),$plat,$atk
 continue
end

# New secondary RNG call, only after failed primary + eligible Platinum.
break *0x087FFD54
commands
 silent
 set $secondary=$secondary+1
 set $secondary_seen=1
 printf "[SECOND_START %u] platinum=0x%x attack_id=%u primary_success=%u\n",$n,$plat,$atk,$primary
 if $primary!=0 || $plat==0 || $atk<2 || $atk>5
   set $violations=$violations+1
   printf "[FAIL] unexpected second roll\n"
 end
 continue
end

# Mask has already been applied at +0x58, result in r0.
break *0x087FFD5A
commands
 silent
 set $secondary_success=($r0==0)
 printf "[SECOND_MASKED %u] masked=0x%x success=%u\n",$n,$r0,$secondary_success
 continue
end

break *0x080312D4
commands
 silent
 set $ret=$ret+1
 set $result=$r0
 set $before=$r6
 printf "[RETURN %u] critical=%u primary=%u second_used=%u second_success=%u damage_before=%u\n",$n,$result,$primary,$secondary_seen,$secondary_success,$before
 if $result!=($primary || $secondary_success)
   set $violations=$violations+1
   printf "[FAIL] critical result inconsistent\n"
 end
 if $primary && $secondary_seen
   set $violations=$violations+1
   printf "[FAIL] second roll after primary critical\n"
 end
 if !$primary && $plat!=0 && $atk>=2 && $atk<=5 && !$secondary_seen
   set $violations=$violations+1
   printf "[FAIL] eligible second roll missing\n"
 end
 continue
end

break *0x080312DC
commands
 silent
 set $dmg=$dmg+1
 printf "[DAMAGE %u] before=%u after=%u critical=%u\n",$n,$before,$r6,$result
 if ($result && $r6!=($before*2)) || (!$result && $r6!=$before)
   set $violations=$violations+1
   printf "[FAIL] damage inconsistent\n"
 end
 printf "[SUMMARY] hits=%u returns=%u damages=%u forced=%u forced_with_platinum=%u new_second=%u old_second=%u violations=%u\n",$n,$ret,$dmg,$forced,$forced_plat,$secondary,$old_secondary,$violations
 continue
end

# This is the old SECOND roll in the vanilla critical routine.
# It must remain unused: the new stub handles Platinum's second roll.
break *0x08077CE0
commands
 silent
 set $old_secondary=$old_secondary+1
 set $violations=$violations+1
 printf "[FAIL] OLD VANILLA SECOND ROLL REACHED count=%u\n",$old_secondary
 continue
end

printf "[READY] Play freely. Finish with Ctrl+C then set logging enabled off.\n"
continue
