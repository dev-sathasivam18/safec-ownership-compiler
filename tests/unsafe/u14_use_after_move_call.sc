// expect: use-after-move
void destroy(own int* q) {
    free(q);
}
int main() {
    own int* p = alloc(4);
    destroy(p);
    *p = 1;
    return 0;
}
