



#these are the same!
register = 39
turn_on = (40959 << 8) & 0xFFFF

#test = int(turn_on, base=16)
#print(test)
register = 39
regnum = register | 0x80



data = (3840 << 8) & 0xFFFF #this is just fucking zero brooooo


msb = int(hex(data)[2:4], base=16)
lsb = 0 #int(hex(data)[4:6], base=16)
split = [msb, lsb]
#
turn_on_packet = bytes([regnum, split[0], split[1], 0])
a = bytes([144, 255, 0, 0])
b = bytes([167, 0, 0, 0])



RegNum = 16
regnum_write = RegNum | 0x80
regnum_read = RegNum


print(a)

print(read_if_on)

