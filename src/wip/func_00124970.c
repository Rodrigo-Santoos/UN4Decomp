/* grava um inteiro de 32 bits em big-endian */
void func_00124970(unsigned int value, unsigned char *dst) {
    int i;
    int shift = 0;
    dst += 3;
    for (i = 4; i > 0; i--) {
        *dst-- = value >> shift;
        shift += 8;
    }
}
