typedef struct Node {
    struct Node *next;
    struct List *list;
} Node;

typedef struct List {
    Node *head;
} List;

/* insere o no no inicio da lista */
void func_001109C0(Node *node, List *list) {
    node->list = list;
    node->next = list->head;
    list->head = node;
}
