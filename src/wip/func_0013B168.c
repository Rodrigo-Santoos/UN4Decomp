typedef struct Unk0013B168 {
    char pad0[0xC];
    int busy;      /* 0x0C */
    int state;     /* 0x10 */
    int mode;      /* 0x14 */
    int arg1;      /* 0x18 */
    int arg2;      /* 0x1C */
    int arg3;      /* 0x20 */
    int arg4;      /* 0x24 */
} Unk0013B168;

int func_0013B168(Unk0013B168 *obj, int arg1, int arg2, int arg3, int arg4) {
    if (obj->busy == 0) {
        obj->arg4 = arg4;
        obj->arg1 = arg1;
        obj->arg2 = arg2;
        obj->mode = 2;
        obj->arg3 = arg3;
        return 1;
    }
    return 0;
}
