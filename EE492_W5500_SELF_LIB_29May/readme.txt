In order to run iolibrary of w5500, we need to add following ZIP files as library to Arduino. In arduino IDE, there is an option about including library such as "add ZIP folder". 

1-socket lib
2-W5500
3-whizchip_conf lib

These libraries also added in include section of the code as follows:

#include <w5500.h>
#include <socket.h>
#include <wizchip_conf.h>