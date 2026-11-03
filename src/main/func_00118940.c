typedef struct Block {
    int unk0;
    char *end;
    int used;
} Block;

typedef struct Cursor {
    Block *block;
    int free;
} Cursor;

void func_00118940(Cursor *cur, Block *blk) {
    cur->block = blk;
    cur->free = (blk->end - (char *)blk) - blk->used;
}
