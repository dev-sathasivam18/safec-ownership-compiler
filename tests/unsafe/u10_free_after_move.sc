// expect: use-after-move
void consume(own int* q) {
    free(q);
}
int main() {
    own int* p = alloc(4);
    consume(p);
    free(p);
    return 0;
}
