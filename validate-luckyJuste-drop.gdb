set pagination off
set confirm off
set logging file luckyJuste-drop-validation.log
set logging overwrite on
set logging enabled on
delete breakpoints
printf "=== luckyJuste generic trace: no multiplier assumptions ===\n"
break *0x087FFE80
commands
silent
printf "[rare-entry] level=%u lck=%u base=%u roll=%u\n", *(unsigned char*)0x0201877C, *(unsigned short*)0x02018558, $r6, $r4
continue
end
break *0x087FFE98
commands
silent
printf "[rare-before] bonus=%u base=%u roll=%u\n", $r1, $r6, $r4
continue
end
break *0x087FFE9A
commands
silent
printf "[rare-after] threshold=%u roll=%u\n", $r6, $r4
continue
end
break *0x08031464
commands
silent
printf "[rare-special] final=%u pre_special=%u delta=%d roll=%u\n", $r0, $r6, (int)$r0-(int)$r6, $r4
continue
end
break *0x0803146A
commands
silent
printf "[rare-plain] final=%u roll=%u\n", $r6, $r4
continue
end
break *0x087FFF00
commands
silent
printf "[normal-entry] level=%u lck=%u base=%u roll=%u\n", *(unsigned char*)0x0201877C, *(unsigned short*)0x02018558, $r6, $r4
continue
end
break *0x087FFF18
commands
silent
printf "[normal-before] bonus=%u base=%u roll=%u\n", $r1, $r6, $r4
continue
end
break *0x087FFF1A
commands
silent
printf "[normal-after] threshold=%u roll=%u\n", $r6, $r4
continue
end
break *0x080314AE
commands
silent
printf "[normal-special] final=%u pre_special=%u delta=%d roll=%u\n", $r0, $r6, (int)$r0-(int)$r6, $r4
continue
end
break *0x080314B8
commands
silent
printf "[normal-plain] final=%u roll=%u\n", $r6, $r4
continue
end
printf "Capture active. Ctrl+C to stop; set logging enabled off to close log.\n"
continue
