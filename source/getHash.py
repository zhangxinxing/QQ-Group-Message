#!/usr/bin/env python
# -*- coding: UTF-8 -*-


def getHashCode(b, j):
    """
    get the hash num to achieve the grouplist info (record:gcode)

    source function:
        http://0.web.qstatic.com/webqqpic/pubapps/0/50/eqq.all.js
    source function definition:
        P=function(b,j)
    
    Args:
         b : real QQ num
         j : ptwebqq (get it by cookies)

    Returns:
         string : hashValue

    Raises:
         No raises

    Author:
         zhang

    Date:
         2015-7-31
    """
    a = [0,0,0,0]
    for i in range(0,len(j)):
        a[i%4] ^= ord(j[i])

    w = ["EC","OK"]
    d = [0,0,0,0]

    d[0] = int(b) >> 24 & 255 ^ ord(w[0][0])
    d[1] = int(b) >> 16 & 255 ^ ord(w[0][1])
    d[2] = int(b) >> 8 & 255 ^ ord(w[1][0])
    d[3] = int(b) & 255 ^ ord(w[1][1])

    w = [0,0,0,0,0,0,0,0]

    for i in range(0,8):
        if i%2 == 0:
            w[i] = a[i>>1]
        else:
            w[i] = d[i>>1]
    a = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]
    d = ""

    for i in range(0,len(w)):
        d += a[w[i]>>4&15]
        d += a[w[i]&15]

    return d
    

if __name__ == "__main__":

    b = "1958317603"
    j = "8bb6208103fb248b333db1a17c7c688297379b614f6e48123cbee0d5d6a53160"
    #j = "rr"
    hashV = getHashCode(b,j)
    print hashV
